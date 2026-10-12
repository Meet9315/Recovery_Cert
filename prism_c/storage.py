"""Local durable authority and fixed-slot byte store.

Metadata mutations serialize with BEGIN IMMEDIATE. Local mode holds that lock
across I/O; opt-in repair workers use durable intents and receipt completion.
This is a trusted local research embodiment, not a distributed service.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import sqlite3
from typing import Callable
import uuid

from .checker import check, replay
from .coding import digest, encode, recover
from .model import Action, Rejected, Slot, State, Stripe, Witness, profile_spec
from .profiles import DEFAULT_PROFILE
from .selective import ContinuationCache, WholeSuffixCache
from .scope import PlanScope
from .worker_authority import WorkerAuthority, WorkerRetry


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stripes(
 name TEXT PRIMARY KEY, eligible TEXT NOT NULL, length INTEGER NOT NULL,
 content_digest TEXT NOT NULL, row_digests TEXT NOT NULL, fragment_size INTEGER NOT NULL,
 profile TEXT NOT NULL DEFAULT 'xor-2+1-v1');
CREATE TABLE IF NOT EXISTS slots(
 key TEXT PRIMARY KEY, domain TEXT NOT NULL, position INTEGER NOT NULL,
 status TEXT NOT NULL, stripe TEXT NOT NULL DEFAULT '', row INTEGER NOT NULL DEFAULT -1,
 incarnation INTEGER NOT NULL DEFAULT 0, digest TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS plans(
 id TEXT PRIMARY KEY, witness TEXT NOT NULL, cursor INTEGER NOT NULL,
 status TEXT NOT NULL, fence INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS holds(slot TEXT PRIMARY KEY, plan TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS pins(slot TEXT PRIMARY KEY, plan TEXT NOT NULL, incarnation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,
 kind TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS validation_cache(plan TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plan_scopes(plan TEXT PRIMARY KEY, stripes TEXT NOT NULL, slots TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stripe_claims(stripe TEXT PRIMARY KEY, plan TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS slot_claims(slot TEXT PRIMARY KEY, plan TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS worker_intents(token TEXT PRIMARY KEY, plan TEXT NOT NULL, command TEXT NOT NULL, status TEXT NOT NULL);
"""


class Authority(WorkerAuthority):
    def __init__(self, root: str | Path, validation_mode: str = "conventional_cached"):
        self.root = Path(root).resolve()
        self.db_path = self.root / "metadata.sqlite3"
        if not self.db_path.exists():
            raise Rejected("Authority has not been created")
        if validation_mode not in {"selective", "full", "shadow", "conventional_cached"}:
            raise ValueError("Validation mode must be selective, full, shadow or conventional_cached")
        self.validation_mode = validation_mode
        self.cache_type = WholeSuffixCache if validation_mode == "conventional_cached" else ContinuationCache
        # Additive migration for earlier stores; witness and slot schemas
        # remain unchanged. No reusable evidence is inferred from old data.
        with self._transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS validation_cache(plan TEXT PRIMARY KEY,value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS plan_scopes(plan TEXT PRIMARY KEY,stripes TEXT NOT NULL,slots TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS stripe_claims(stripe TEXT PRIMARY KEY,plan TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS slot_claims(slot TEXT PRIMARY KEY,plan TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS worker_intents(token TEXT PRIMARY KEY,plan TEXT NOT NULL,command TEXT NOT NULL,status TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO settings VALUES ('io_mode',?)", (json.dumps("local"),))
            if "profile" not in {row["name"] for row in db.execute("PRAGMA table_info(stripes)")}:
                db.execute("ALTER TABLE stripes ADD COLUMN profile TEXT NOT NULL DEFAULT 'xor-2+1-v1'")

    @classmethod
    def create(cls, root: str | Path, capacities: dict[str, int], slot_size: int = 4096) -> Authority:
        root = Path(root).resolve()
        if root.exists() and any(root.iterdir()):
            raise Rejected("Creation requires an empty directory")
        if not capacities or slot_size < 1 or any(count < 1 for count in capacities.values()):
            raise Rejected("Invalid managed capacity")
        root.mkdir(parents=True, exist_ok=True)
        # Numbered file paths prevent caller-provided names becoming filesystem paths.
        for index, (_, count) in enumerate(sorted(capacities.items())):
            with (root / f"pool-{index}.bin").open("xb") as handle:
                for _ in range(count):
                    handle.write(bytes(slot_size))
                handle.flush()
                os.fsync(handle.fileno())
        connection = sqlite3.connect(root / "metadata.sqlite3", isolation_level=None)
        try:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=FULL")
            connection.executescript(SCHEMA)
            connection.execute("BEGIN IMMEDIATE")
            for key, value in {"slot_size": slot_size, "fence": 0, "offline": [],
                               "domains": sorted(capacities), "incarnation": uuid.uuid4().hex}.items():
                connection.execute("INSERT INTO settings VALUES (?,?)", (key, json.dumps(value)))
            for domain, count in sorted(capacities.items()):
                for position in range(count):
                    connection.execute("INSERT INTO slots(key,domain,position,status) VALUES (?,?,?,'FREE')",
                                       (f"{domain}:{position}", domain, position))
            connection.commit()
        finally:
            connection.close()
        return cls(root)

    @contextmanager
    def _transaction(self):
        connection = sqlite3.connect(self.db_path, isolation_level=None, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _get(db, key):
        return json.loads(db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()[0])

    @staticmethod
    def _event(db, kind, detail):
        db.execute("INSERT INTO events(kind,detail) VALUES (?,?)", (kind, json.dumps(detail, sort_keys=True)))

    def _fence(self, db, fence):
        if fence != self._get(db, "fence"):
            raise Rejected("Stale controller fence")

    @staticmethod
    def _active(db):
        return db.execute("SELECT * FROM plans WHERE status='ACTIVE'").fetchone()

    @staticmethod
    def _exclusive_active(db):
        return db.execute("SELECT p.id FROM plans p LEFT JOIN plan_scopes s ON p.id=s.plan "
                          "WHERE p.status='ACTIVE' AND s.plan IS NULL LIMIT 1").fetchone()

    @staticmethod
    def _scope(db, plan_id):
        row = db.execute("SELECT * FROM plan_scopes WHERE plan=?", (plan_id,)).fetchone()
        return PlanScope(tuple(json.loads(row["stripes"])), tuple(json.loads(row["slots"]))) if row else None

    @staticmethod
    def _release_claims(db, plan_id):
        for table in ("stripe_claims", "slot_claims", "pins", "holds"):
            db.execute(f"DELETE FROM {table} WHERE plan=?", (plan_id,))

    @staticmethod
    def _check_claims(db, scope, plan_id):
        stripes = {r["stripe"] for r in db.execute("SELECT stripe FROM stripe_claims WHERE plan=?", (plan_id,))}
        slots = {r["slot"] for r in db.execute("SELECT slot FROM slot_claims WHERE plan=?", (plan_id,))}
        if stripes != set(scope.stripes) or slots != set(scope.slots):
            raise Rejected("Plan lost complete stripe/slot claims")

    def takeover(self) -> int:
        with self._transaction() as db:
            fence = self._get(db, "fence") + 1
            self._worker_fence_all(db, fence)
            db.execute("UPDATE settings SET value=? WHERE key='fence'", (json.dumps(fence),))
            db.execute("UPDATE plans SET fence=? WHERE status='ACTIVE'", (fence,))
            self._event(db, "takeover", {"fence": fence})
            return fence

    def _snapshot(self, db) -> State:
        stripes = tuple(Stripe(r["name"], tuple(json.loads(r["eligible"])), r["profile"])
                        for r in db.execute("SELECT * FROM stripes ORDER BY name"))
        slots = tuple(Slot(r["key"], r["domain"], r["status"], r["stripe"], r["row"], r["incarnation"])
                      for r in db.execute("SELECT * FROM slots ORDER BY key"))
        return State(stripes, slots, tuple(self._get(db, "offline")))

    def snapshot(self) -> State:
        with self._transaction() as db:
            return self._snapshot(db)

    def snapshot_for(self, stripes: tuple[str, ...], destinations: tuple[str, ...]) -> State:
        """Derive a whole-stripe snapshot; existing members cannot be omitted."""
        with self._transaction() as db:
            state = self._snapshot(db)
            return PlanScope.derive(state, stripes, destinations).project(state)

    def active_plans(self) -> list[dict]:
        with self._transaction() as db:
            return [dict(row) for row in db.execute("SELECT * FROM plans WHERE status='ACTIVE' ORDER BY id")]

    def _io(self, db, record, data: bytes | None = None) -> bytes:
        size = self._get(db, "slot_size")
        index = self._get(db, "domains").index(record["domain"])
        path = self.root / f"pool-{index}.bin"
        with path.open("r+b" if data is not None else "rb") as handle:
            handle.seek(record["position"] * size)
            if data is None:
                raw = handle.read(size)
                if len(raw) != size:
                    raise Rejected("Truncated managed pool")
                return raw
            if len(data) > size:
                raise Rejected("Fragment exceeds managed slot")
            handle.write(data.ljust(size, b"\x00"))
            handle.flush()
            os.fsync(handle.fileno())
            return data

    def bootstrap(self, name: str, data: bytes, placement: dict[int, str],
                  eligible: tuple[str, ...], fence: int, profile: str = DEFAULT_PROFILE) -> None:
        """Trusted initial fixture import, before any plan has been admitted."""
        code = profile_spec(profile)
        encoded = encode(data, profile)
        if (len(placement) < code.data_rows or any(type(row) is not int for row in placement)
                or not set(placement) <= set(range(code.total_rows))):
            raise Rejected("Initial stripe needs enough distinct rows for its coding profile")
        if len(set(placement.values())) != len(placement):
            raise Rejected("Initial fragments share a domain")
        with self._transaction() as db:
            self._fence(db, fence)
            if db.execute("SELECT 1 FROM plans LIMIT 1").fetchone():
                raise Rejected("Bootstrap is sealed after first admission")
            if not set(eligible) <= set(self._get(db, "domains")) or len(set(eligible)) != len(eligible):
                raise Rejected("Invalid eligibility domains")
            if any(domain not in eligible for domain in placement.values()):
                raise Rejected("Ineligible initial placement")
            if len(encoded[0]) > self._get(db, "slot_size"):
                raise Rejected("Content exceeds profile size")
            db.execute("INSERT INTO stripes(name,eligible,length,content_digest,row_digests,fragment_size,profile) "
                       "VALUES (?,?,?,?,?,?,?)", (name, json.dumps(eligible), len(data), digest(data),
                       json.dumps([digest(row) for row in encoded]), len(encoded[0]), profile))
            for row, domain in sorted(placement.items()):
                slot = db.execute("SELECT * FROM slots WHERE domain=? AND status='FREE' ORDER BY key LIMIT 1",
                                  (domain,)).fetchone()
                if slot is None:
                    raise Rejected("Insufficient bootstrap capacity")
                self._io(db, slot, encoded[row])
                db.execute("UPDATE slots SET status='LIVE',stripe=?,row=?,incarnation=incarnation+1,digest=? WHERE key=?",
                           (name, row, digest(encoded[row]), slot["key"]))
            self._event(db, "bootstrap", {"stripe": name, "content_digest": digest(data)})

    def seed_retired(self, domain: str, fence: int) -> None:
        """Allocate non-authoritative garbage for the reclamation fixture."""
        with self._transaction() as db:
            self._fence(db, fence)
            if db.execute("SELECT 1 FROM plans LIMIT 1").fetchone():
                raise Rejected("Fixture import is sealed")
            slot = db.execute("SELECT * FROM slots WHERE domain=? AND status='FREE' ORDER BY key LIMIT 1",
                              (domain,)).fetchone()
            if slot is None:
                raise Rejected("No garbage slot available")
            self._io(db, slot, b"retired fixture"[:self._get(db, "slot_size")])
            db.execute("UPDATE slots SET status='RETIRED',incarnation=incarnation+1 WHERE key=?", (slot["key"],))

    def _valid_rows(self, db, name: str) -> tuple[dict, dict[int, bytes]]:
        spec = db.execute("SELECT * FROM stripes WHERE name=?", (name,)).fetchone()
        if spec is None:
            raise Rejected("Unknown content identity")
        expected = json.loads(spec["row_digests"])
        code = profile_spec(spec["profile"])
        if len(expected) != code.total_rows:
            raise Rejected("Row digest count does not match coding profile")
        offline = self._get(db, "offline")
        rows = {}
        for record in db.execute("SELECT * FROM slots WHERE stripe=? AND status='LIVE'", (name,)):
            if record["domain"] in offline:
                continue
            if record["row"] not in range(code.total_rows):
                raise Rejected("Source row is outside its coding profile")
            raw = self._io(db, record)[:spec["fragment_size"]]
            if digest(raw) != expected[record["row"]] or digest(raw) != record["digest"]:
                raise Rejected("Live source digest mismatch")
            rows[record["row"]] = raw
        content, recovered = recover(rows, spec["length"], spec["profile"])
        if digest(content) != spec["content_digest"] or [digest(row) for row in recovered] != expected:
            raise Rejected("Source content identity mismatch")
        return dict(spec), rows

    def read(self, name: str) -> bytes:
        with self._transaction() as db:
            spec, rows = self._valid_rows(db, name)
            return recover(rows, spec["length"], spec["profile"])[0]

    def admit(self, witness: Witness, fence: int, plan_id: str | None = None) -> str:
        """Legacy full-store admission; mutually exclusive with scoped plans."""
        return self._admit(witness, fence, plan_id)

    def admit_scoped(self, witness: Witness, stripes: tuple[str, ...], destinations: tuple[str, ...],
                     fence: int, plan_id: str | None = None) -> str:
        return self._admit(witness, fence, plan_id, stripes, destinations)

    def _admit(self, witness, fence, plan_id, stripes=None, destinations=None):
        with self._transaction() as db:
            self._fence(db, fence)
            snapshot = self._snapshot(db)
            scope = None
            if stripes is None:
                if self._active(db):
                    raise Rejected("Full-store continuation conflicts with an active plan")
            else:
                if self._exclusive_active(db):
                    raise Rejected("Scoped continuation conflicts with a full-store plan")
                scope = PlanScope.derive(snapshot, stripes, destinations)
                snapshot = scope.project(snapshot)
            # Acquire all claims in the same admission transaction. No partial
            # holds survive a conflict or failed witness/content validation.
            for stripe in snapshot.stripes:
                if db.execute("SELECT 1 FROM stripe_claims WHERE stripe=?", (stripe.name,)).fetchone():
                    raise Rejected("Stripe is claimed by another continuation")
            for slot in snapshot.slots:
                if db.execute("SELECT 1 FROM slot_claims WHERE slot=?", (slot.key,)).fetchone():
                    raise Rejected("Slot is claimed by another continuation")
            cache = None
            if self.validation_mode == "full":
                check(snapshot, witness)
            else:
                cache = self.cache_type.build(snapshot, witness)
            for stripe in snapshot.stripes:
                self._valid_rows(db, stripe.name)
            identifier = plan_id or uuid.uuid4().hex
            db.execute("INSERT INTO plans VALUES (?,?,0,?,?)",
                       (identifier, json.dumps(witness.to_dict()),
                        "ACTIVE" if witness.actions else "DONE", fence))
            if scope is not None:
                db.execute("INSERT INTO plan_scopes VALUES (?,?,?)",
                           (identifier, json.dumps(scope.stripes), json.dumps(scope.slots)))
            if witness.actions:
                for stripe in snapshot.stripes:
                    db.execute("INSERT INTO stripe_claims VALUES (?,?)", (stripe.name, identifier))
                for slot in snapshot.slots:
                    db.execute("INSERT INTO slot_claims VALUES (?,?)", (slot.key, identifier))
            if cache is not None:
                db.execute("INSERT INTO validation_cache VALUES (?,?)",
                           (identifier, cache.to_json(self._get(db, "incarnation"))))
            # Scope claims remain after destination holds are materialized.
            # Retired destinations remain occupied until reclamation.
            for key in {a.slot for a in witness.actions if a.kind == "reserve"}:
                db.execute("INSERT INTO holds VALUES (?,?)", (key, identifier))
            for slot in snapshot.slots if witness.actions else ():
                if slot.status == "LIVE":
                    db.execute("INSERT INTO pins VALUES (?,?,?)", (slot.key, identifier, slot.incarnation))
            self._event(db, "admit", {"plan": identifier, "witness_digest": witness.digest(),
                                     "scope": asdict(scope) if scope else "FULL_STORE"})
            return identifier

    def plan_info(self, plan_id: str) -> dict:
        with self._transaction() as db:
            record = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
            if record is None:
                raise Rejected("Unknown plan")
            scope = self._scope(db, plan_id)
            return {**dict(record), "scope": asdict(scope) if scope else "FULL_STORE"}

    def step(self, plan_id: str, fence: int, step_id: int | None = None,
             fault: Callable[[str], None] | None = None, *, _receipt: dict | None = None) -> dict:
        if _receipt is None:
            while True:
                result = self._maybe_worker_step(plan_id, fence, step_id, fault)
                if result is not None:
                    return result
                try:
                    return self._local_step(plan_id, fence, step_id, fault)
                except WorkerRetry:
                    continue
        return self._local_step(plan_id, fence, step_id, fault, _receipt=_receipt)

    def _local_step(self, plan_id, fence, step_id=None, fault=None, *, _receipt=None):
        def hit(point):
            if fault:
                fault(point)

        with self._transaction() as db:
            self._fence(db, fence)
            record = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
            if record is None or record["fence"] != fence or record["status"] == "CANCELED":
                raise Rejected("Inactive or wrong-owner plan")
            witness = Witness.from_dict(json.loads(record["witness"]))
            cursor = record["cursor"]
            requested = cursor if step_id is None else step_id
            if requested < 0 or requested > cursor:
                raise Rejected("Out-of-order step")
            if requested < cursor:
                return {"status": "ALREADY_APPLIED", "cursor": cursor}
            if cursor == len(witness.actions):
                return {"status": "DONE", "cursor": cursor}
            if record["status"] != "ACTIVE":
                raise Rejected("Plan is not active")
            current = self._snapshot(db)
            scope = self._scope(db, plan_id)
            if scope is not None:
                self._check_claims(db, scope, plan_id)
                current = scope.project(current)
            if cursor == 0 and current.fingerprint() != witness.initial:
                raise Rejected("Initial snapshot conflict")
            cache = None
            if self.validation_mode == "full":
                final = replay(current, witness.actions[cursor:])
                if final.fingerprint() != witness.terminal:
                    raise Rejected("Remaining continuation does not reach committed target")
                validation = {"mode": "full", "replayed_actions": len(witness.actions) - cursor}
            else:
                cached = db.execute("SELECT value FROM validation_cache WHERE plan=?", (plan_id,)).fetchone()
                rebuilt = False
                try:
                    if cached is None:
                        raise Rejected("No cached evidence")
                    cache = self.cache_type.from_json(cached["value"], witness, cursor,
                                                      self._get(db, "incarnation"))
                except (Rejected, ValueError, KeyError, TypeError):
                    cache = self.cache_type.build(current, witness, cursor)
                    rebuilt = True
                construction = dict(cache.last_stats)
                final = cache.validate(current, witness, cursor)
                validation = {"mode": self.validation_mode, **cache.last_stats, "cache_rebuilt": rebuilt}
                if rebuilt:
                    validation["construction"] = construction
                if self.validation_mode == "shadow":
                    reference = replay(current, witness.actions[cursor:])
                    if reference != final or reference.fingerprint() != witness.terminal:
                        raise Rejected("Selective/reference disagreement")
            for stripe in current.stripes:
                self._valid_rows(db, stripe.name)
            action = witness.actions[cursor]
            if self._workers_enabled(db) and _receipt is None and action.kind in ("stage", "reclaim"):
                raise WorkerRetry()
            if _receipt is not None and action.kind not in ("stage", "reclaim"):
                raise Rejected("A worker receipt cannot authorize a metadata-only action")
            next_state = replay(current, (action,), require_target=False)
            if cache is not None:
                cache.advance(current, next_state, action)
            slot = db.execute("SELECT * FROM slots WHERE key=?", (action.slot,)).fetchone()
            expected_slot = next(s for s in next_state.slots if s.key == action.slot)
            hit("after_validation")
            receipt_digest = slot["digest"]
            if action.kind == "reserve":
                hold = db.execute("SELECT plan FROM holds WHERE slot=?", (action.slot,)).fetchone()
                if hold is None or hold["plan"] != plan_id:
                    raise Rejected("Missing enforceable destination hold")
                db.execute("DELETE FROM holds WHERE slot=?", (action.slot,))
            elif action.kind == "stage":
                spec, rows = self._valid_rows(db, action.stripe)
                rebuilt = recover(rows, spec["length"], spec["profile"])[1][action.row]
                if _receipt is None:
                    self._io(db, slot, rebuilt)
                else:
                    self._accept_worker_receipt(db, _receipt, plan_id, cursor, witness, current, action, slot, rebuilt)
                receipt_digest = digest(rebuilt)
                hit("after_stage_fsync")
            elif action.kind == "promote":
                spec = db.execute("SELECT * FROM stripes WHERE name=?", (action.stripe,)).fetchone()
                raw = self._io(db, slot)[:spec["fragment_size"]]
                if (digest(raw) != slot["digest"] or
                        digest(raw) != json.loads(spec["row_digests"])[action.row]):
                    raise Rejected("Invalid staged receipt or corrupted bytes")
            elif action.kind == "retire":
                # Pins owned by this same continuation are discharged only by
                # an independently checked safe retirement. No external delete API.
                db.execute("DELETE FROM pins WHERE slot=? AND plan=?", (action.slot, plan_id))
            elif action.kind == "reclaim":
                if db.execute("SELECT 1 FROM pins WHERE slot=?", (action.slot,)).fetchone():
                    raise Rejected("Cannot reclaim pinned incarnation")
                if _receipt is None:
                    self._io(db, slot, b"")
                else:
                    self._accept_worker_receipt(db, _receipt, plan_id, cursor, witness, current, action, slot, b"")
                receipt_digest = ""
                hit("after_reclaim_fsync")
            db.execute("UPDATE slots SET status=?,stripe=?,row=?,incarnation=?,digest=? WHERE key=?",
                       (expected_slot.status, expected_slot.stripe, expected_slot.row,
                        expected_slot.incarnation, receipt_digest, expected_slot.key))
            if action.kind == "promote":
                db.execute("INSERT INTO pins VALUES (?,?,?)",
                           (action.slot, plan_id, expected_slot.incarnation))
            done = cursor + 1 == len(witness.actions)
            db.execute("UPDATE plans SET cursor=?,status=? WHERE id=?",
                       (cursor + 1, "DONE" if done else "ACTIVE", plan_id))
            if cache is not None:
                db.execute("INSERT OR REPLACE INTO validation_cache VALUES (?,?)",
                           (plan_id, cache.to_json(self._get(db, "incarnation"))))
            if done:
                self._release_claims(db, plan_id)
            self._event(db, "step", {"plan": plan_id, "step": cursor, "action": asdict(action),
                                      "receipt_digest": receipt_digest, "validation": validation})
            hit("before_commit")
        hit("after_commit")
        return {"status": "DONE" if done else "APPLIED", "cursor": cursor + 1}

    def execute(self, plan_id: str, fence: int) -> None:
        while True:
            result = self.step(plan_id, fence)
            if result["status"] == "DONE":
                return

    def cancel(self, plan_id: str, fence: int) -> None:
        with self._transaction() as db:
            self._fence(db, fence)
            record = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
            if record is None or record["fence"] != fence:
                raise Rejected("Unknown or wrong-owner plan")
            if record["status"] != "ACTIVE":
                return
            self._revoke_intents(db, plan_id)
            # Partial writes remain charged RETIRED. They must be physically
            # reclaimed by a later checked continuation or explicit cleanup.
            scope = self._scope(db, plan_id)
            if scope is not None:
                self._check_claims(db, scope, plan_id)
                db.execute("UPDATE slots SET status='RETIRED' WHERE status IN ('RESERVED','STAGED') "
                           "AND key IN (SELECT slot FROM slot_claims WHERE plan=?)", (plan_id,))
            else:
                # Full-store legacy plan is exclusive; no other plan allocations
                # can exist. This also supports pre-migration active stores.
                db.execute("UPDATE slots SET status='RETIRED' WHERE status IN ('RESERVED','STAGED')")
            db.execute("UPDATE plans SET status='CANCELED' WHERE id=?", (plan_id,))
            self._release_claims(db, plan_id)
            db.execute("DELETE FROM validation_cache WHERE plan=?", (plan_id,))
            self._event(db, "cancel", {"plan": plan_id})

    def annotate(self, label: str, value: str, fence: int) -> None:
        """Operational annotation has no allocation, policy or content authority."""
        with self._transaction() as db:
            self._fence(db, fence)
            self._event(db, "annotation", {"label": label, "value": value})

    def cleanup(self, slot_key: str, incarnation: int, fence: int) -> None:
        with self._transaction() as db:
            self._fence(db, fence)
            if self._exclusive_active(db):
                raise Rejected("Cleanup must be part of the active full-store continuation")
            if db.execute("SELECT 1 FROM slot_claims WHERE slot=?", (slot_key,)).fetchone():
                raise Rejected("Cleanup cannot reclaim another plan's claimed slot")
            slot = db.execute("SELECT * FROM slots WHERE key=?", (slot_key,)).fetchone()
            if slot is None or slot["status"] != "RETIRED" or slot["incarnation"] != incarnation:
                raise Rejected("Cleanup requires exact retired incarnation")
            if slot["domain"] in self._get(db, "offline"):
                raise Rejected("Cannot reclaim offline storage")
            if db.execute("SELECT 1 FROM pins WHERE slot=?", (slot_key,)).fetchone():
                raise Rejected("Retired slot is pinned")
            self._io(db, slot, b"")
            db.execute("UPDATE slots SET status='FREE',stripe='',row=-1,digest='' WHERE key=?", (slot_key,))
            self._event(db, "cleanup", {"slot": slot_key, "incarnation": incarnation})

    def set_offline(self, domain: str, fence: int) -> None:
        with self._transaction() as db:
            self._fence(db, fence)
            if domain not in self._get(db, "domains"):
                raise Rejected("Unknown failure domain")
            offline = sorted(set(self._get(db, "offline")) | {domain})
            db.execute("UPDATE settings SET value=? WHERE key='offline'", (json.dumps(offline),))
            self._event(db, "offline", {"domain": domain})

    def ledger(self) -> dict:
        with self._transaction() as db:
            state = self._snapshot(db)
            counts = state.ledger()
            holds = {r["slot"] for r in db.execute("SELECT slot FROM holds UNION SELECT slot FROM slot_claims")}
            for slot in state.slots:
                if slot.status == "FREE" and slot.key in holds:
                    counts[slot.domain]["FREE"] -= 1
                    counts[slot.domain]["RESERVED"] += 1
            size = self._get(db, "slot_size")
            return {domain: {"online": domain not in state.offline,
                             "bytes": {status: count * size for status, count in values.items()},
                             "slots": values} for domain, values in counts.items()}

    def events(self) -> list[dict]:
        with self._transaction() as db:
            return [{"seq": r["seq"], "kind": r["kind"], "detail": json.loads(r["detail"])}
                    for r in db.execute("SELECT * FROM events ORDER BY seq")]

    def audit(self) -> dict:
        with self._transaction() as db:
            state = self._snapshot(db)
            replay(state, (), require_target=False)
            for spec in state.stripes:
                self._valid_rows(db, spec.name)
            for slot in db.execute("SELECT * FROM slots WHERE status='STAGED'"):
                spec = db.execute("SELECT * FROM stripes WHERE name=?", (slot["stripe"],)).fetchone()
                raw = self._io(db, slot)[:spec["fragment_size"]]
                if digest(raw) != slot["digest"] or digest(raw) != json.loads(spec["row_digests"])[slot["row"]]:
                    raise Rejected("Staged allocation failed audit")
            return {"snapshot": state.fingerprint(), "target": state.target(),
                    "stripes": len(state.stripes), "slots": len(state.slots)}
