"""Opt-in serialized zoned-file emulator; process recovery, not device durability."""

from contextlib import contextmanager
from dataclasses import asdict
import json
import os
from pathlib import Path
import sqlite3
import uuid

from .coding import digest, encode, recover
from .model import Rejected
from .zoned_model import (ZAction, ZExtent, ZStripe, ZZone, ZonedState, ZWitness,
                          goal, protected, replay, step, validate)


FORMAT = "prism-zoned-file-v1"


def state_from_dict(value):
    stripes = tuple(ZStripe(**{**s, "eligible": tuple(s["eligible"])}) for s in value["stripes"])
    zones = tuple(ZZone(**{**z, "extents": tuple(ZExtent(**e) for e in z["extents"]),
                          "reservation": tuple(z["reservation"]) if z["reservation"] else None})
                  for z in value["zones"])
    return ZonedState(stripes, zones, tuple(tuple(r) for r in value["reclaim"]),
                      tuple(value["offline"]), value["max_open"], value["max_active"])


def witness_from_dict(value):
    return ZWitness(value["initial"], tuple(ZAction(**a) for a in value["actions"]))


class _Uncertain(Rejected):
    pass


class ZonedFileStore:
    """One immutable scope and one installed plan per fresh store. No async I/O/cancel API.

    Every byte read/write holds BEGIN IMMEDIATE. Prepared operations are durable
    before file I/O; takeover invalidates an old actor before its next transaction.
    Public calls close every SQLite handle, including on Windows and exceptions.
    """

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.db_path = self.root / "zoned.sqlite3"
        if not self.db_path.is_file():
            raise Rejected("Not a zoned-file store")
        with self._transaction() as db:
            document = self._load(db)
            if document.get("format") != FORMAT:
                raise Rejected("Unsupported zoned-file format")
            validate(state_from_dict(document["state"]))

    @classmethod
    def create(cls, root, initial, contents, unit=64):
        validate(initial)
        if not protected(initial) or any(z.phase == "RESETTING" or z.reservation for z in initial.zones):
            raise Rejected("Bootstrap requires protected, settled initial state")
        if type(unit) is not int or unit < 2 or set(contents) != {s.name for s in initial.stripes}:
            raise Rejected("Invalid unit/content scope")
        manifests, encoded = {}, {}
        for spec in initial.stripes:
            data = contents[spec.name]
            rows = encode(data, spec.profile)
            if any(len(row) != unit for row in rows):
                raise Rejected("Every bootstrap code row must occupy exactly one unit")
            encoded[spec.name] = rows
            manifests[spec.name] = {"epoch": 1, "profile": spec.profile, "length": len(data),
                                    "sha256": digest(data), "rows": [digest(row) for row in rows]}
        root = Path(root).resolve()
        # Never reset or repurpose an existing directory, even if apparently empty.
        root.mkdir(parents=True, exist_ok=False)
        (root / "zones").mkdir()
        for zone in initial.zones:
            path = root / "zones" / (digest(zone.name.encode("utf-8")) + ".bin")
            with path.open("xb") as handle:
                for extent in zone.extents:
                    handle.write(encoded[extent.stripe][extent.row] if extent.stripe else bytes([165]) * unit)
                handle.flush()
                os.fsync(handle.fileno())
        db = sqlite3.connect(root / "zoned.sqlite3", isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            db.execute("CREATE TABLE authority (id INTEGER PRIMARY KEY CHECK(id=1), document TEXT NOT NULL)")
            db.execute("CREATE TABLE receipts (cursor INTEGER PRIMARY KEY, document TEXT NOT NULL)")
            document = {"format": FORMAT, "store_id": uuid.uuid4().hex, "unit": unit,
                        "state": asdict(initial), "manifests": manifests, "fence": 0,
                        "plan": None, "cursor": 0, "pending": None, "quarantine": None}
            db.execute("INSERT INTO authority VALUES (1, ?)", (json.dumps(document, sort_keys=True),))
            db.commit()
        finally:
            db.close()
        return cls(root)

    @contextmanager
    def _transaction(self):
        # mode=rw prevents accidental creation on a misspelled root.
        db = sqlite3.connect(self.db_path.as_uri() + "?mode=rw", uri=True,
                             isolation_level=None, timeout=30)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _load(db):
        return json.loads(db.execute("SELECT document FROM authority WHERE id=1").fetchone()[0])

    @staticmethod
    def _save(db, document):
        db.execute("UPDATE authority SET document=? WHERE id=1", (json.dumps(document, sort_keys=True),))

    @staticmethod
    def _check(document, fence):
        if type(fence) is not int or fence != document["fence"] or fence < 1:
            raise Rejected("Stale authority fence")
        if document["quarantine"]:
            raise Rejected("Store is quarantined: " + document["quarantine"])

    def zone_path(self, name):
        return self.root / "zones" / (digest(name.encode("utf-8")) + ".bin")

    def takeover(self):
        with self._transaction() as db:
            document = self._load(db)
            document["fence"] += 1
            self._save(db, document)
            return document["fence"]

    def info(self):
        with self._transaction() as db:
            return self._load(db)

    def snapshot(self):
        return state_from_dict(self.info()["state"])

    def _fragment(self, document, zone, offset, extent):
        with self.zone_path(zone.name).open("rb") as handle:
            handle.seek(offset * document["unit"])
            fragment = handle.read(document["unit"])
        expected = document["manifests"][extent.stripe]["rows"][extent.row]
        if len(fragment) != document["unit"] or digest(fragment) != expected:
            raise Rejected("Unauthentic fragment: " + zone.name)
        return fragment

    def _read(self, document, state, name):
        manifest = document["manifests"][name]
        rows = {}
        for zone in state.zones:
            if zone.domain in state.offline:
                continue
            for offset, extent in enumerate(zone.extents):
                if extent.status == "LIVE" and extent.stripe == name:
                    rows[extent.row] = self._fragment(document, zone, offset, extent)
        data, regenerated = recover(rows, manifest["length"], manifest["profile"])
        if digest(data) != manifest["sha256"] or [digest(row) for row in regenerated] != manifest["rows"]:
            raise Rejected("Immutable object/row commitment mismatch")
        return data, regenerated

    def _read_all(self, document, state):
        return {spec.name: self._read(document, state, spec.name) for spec in state.stripes}

    def read(self, name):
        with self._transaction() as db:
            document = self._load(db)
            # Quarantine blocks allocation, not authenticated reads of healthy rows.
            return self._read(document, state_from_dict(document["state"]), name)[0]

    def _geometry(self, document, state, pending=None):
        unit = document["unit"]
        for zone in state.zones:
            size = self.zone_path(zone.name).stat().st_size
            expected = len(zone.extents) * unit
            if pending and pending["action"]["zone"] == zone.name:
                kind = pending["action"]["kind"]
                allowed = (expected, expected + unit) if kind == "stage" else (expected, 0)
            else:
                allowed = (expected,)
            if size not in allowed:
                raise _Uncertain(f"Unexpected physical length in {zone.name}: {size}, expected {allowed}")

    def admit(self, witness, fence):
        with self._transaction() as db:
            document = self._load(db)
            self._check(document, fence)
            if document["plan"] is not None:
                raise Rejected("Fresh stores accept only one immutable plan")
            state = state_from_dict(document["state"])
            replay(state, witness)
            self._geometry(document, state)
            self._read_all(document, state)
            # Bootstrap staging is authenticated on adoption, never presumed valid.
            document["plan"] = witness.to_dict()
            self._save(db, document)

    @staticmethod
    def _hook(hook, kind, boundary):
        if hook:
            hook(kind, boundary)

    def advance(self, fence, expected_cursor=None, hook=None):
        """Apply one saved action. Duplicate cursor returns its durable receipt.

        hook is a diagnostic callback, not a storage worker. It may kill the
        process at real journal/file/commit boundaries. No public raw reset API.
        """
        physical = False
        with self._transaction() as db:
            document = self._load(db)
            self._check(document, fence)
            if document["plan"] is None:
                raise Rejected("No installed plan")
            cursor = document["cursor"]
            if expected_cursor is not None:
                if type(expected_cursor) is not int or expected_cursor < 0 or expected_cursor > cursor:
                    raise Rejected("Invalid/out-of-order cursor")
                if expected_cursor < cursor:
                    receipt = json.loads(db.execute("SELECT document FROM receipts WHERE cursor=?",
                                                    (expected_cursor,)).fetchone()[0])
                    return {"status": "ALREADY_APPLIED", "receipt": receipt}
            actions = document["plan"]["actions"]
            if cursor == len(actions):
                return {"status": "DONE", "cursor": cursor}
            action = ZAction(**actions[cursor])
            kind = action.kind
            state = state_from_dict(document["state"])
            after = step(state, action)
            physical = kind in ("stage", "reset_ack")
            if document["pending"] is None:
                self._geometry(document, state)
                decoded = self._read_all(document, state)
                if kind == "promote":
                    zone = next(z for z in state.zones if z.name == action.zone)
                    self._fragment(document, zone, action.offset, zone.extents[action.offset])
                if physical:
                    zone = next(z for z in state.zones if z.name == action.zone)
                    identity = {"store": document["store_id"], "cursor": cursor,
                                "before": state.fingerprint(), "action": asdict(action)}
                    intent = {**identity, "id": digest(json.dumps(identity, sort_keys=True).encode()),
                              "expected_size": len(zone.extents) * document["unit"]}
                    if kind == "stage":
                        manifest = document["manifests"][action.stripe]
                        intent.update(epoch=manifest["epoch"], row_sha256=manifest["rows"][action.row])
                        if digest(decoded[action.stripe][1][action.row]) != intent["row_sha256"]:
                            raise Rejected("Stage identity mismatch")
                    self._hook(hook, kind, "before_prepare")
                    document["pending"] = intent
                    self._save(db, document)
                else:
                    self._hook(hook, kind, "before_commit")
                    self._commit_action(db, document, action, after, None)
        if not physical:
            self._hook(hook, kind, "after_commit")
            return {"status": "APPLIED", "cursor": cursor + 1}
        self._hook(hook, kind, "after_prepare")
        return self._apply_prepared(fence, cursor, hook)

    def _commit_action(self, db, document, action, after, intent):
        # Authenticate all surviving LIVE rows against the immutable manifest.
        self._read_all(document, after)
        receipt = {"store": document["store_id"], "cursor": document["cursor"],
                   "action": asdict(action), "operation": intent["id"] if intent else None,
                   "stage_bytes": document["unit"] if action.kind == "stage" else 0,
                   "after": after.fingerprint(), "fence": document["fence"]}
        db.execute("INSERT INTO receipts VALUES (?, ?)", (document["cursor"], json.dumps(receipt, sort_keys=True)))
        document["state"] = asdict(after)
        document["cursor"] += 1
        document["pending"] = None
        self._save(db, document)

    def _apply_prepared(self, fence, expected_cursor, hook):
        failure = None
        with self._transaction() as db:
            document = self._load(db)
            self._check(document, fence)
            if document["cursor"] > expected_cursor:
                receipt = json.loads(db.execute("SELECT document FROM receipts WHERE cursor=?",
                                                (expected_cursor,)).fetchone()[0])
                return {"status": "ALREADY_APPLIED", "receipt": receipt}
            if document["cursor"] != expected_cursor:
                raise Rejected("Prepared cursor changed")
            intent = document["pending"]
            if intent is None:
                # Another call already reconciled the saved operation.
                return {"status": "ALREADY_APPLIED", "cursor": document["cursor"]}
            action = ZAction(**intent["action"])
            state = state_from_dict(document["state"])
            if (intent["store"] != document["store_id"] or intent["cursor"] != document["cursor"]
                    or intent["before"] != state.fingerprint()
                    or intent["action"] != document["plan"]["actions"][document["cursor"]]):
                raise Rejected("Stale or altered intent binding")
            after = step(state, action)
            zone = next(z for z in state.zones if z.name == action.zone)
            kind = action.kind
            identity = {key: intent[key] for key in ("store", "cursor", "before", "action")}
            if (kind not in ("stage", "reset_ack")
                    or intent["expected_size"] != len(zone.extents) * document["unit"]
                    or intent["id"] != digest(json.dumps(identity, sort_keys=True).encode())):
                raise Rejected("Altered operation identity/position")
            try:
                self._geometry(document, state, intent)
                decoded = self._read_all(document, state)
                self._hook(hook, kind, "before_io")
                with self.zone_path(zone.name).open("r+b") as handle:
                    handle.seek(0, os.SEEK_END)
                    size = handle.tell()
                    if kind == "stage":
                        manifest = document["manifests"][action.stripe]
                        if intent["epoch"] != manifest["epoch"] or intent["row_sha256"] != manifest["rows"][action.row]:
                            raise Rejected("Stale immutable row identity")
                        payload = decoded[action.stripe][1][action.row]
                        if size == intent["expected_size"]:
                            split = len(payload) // 2
                            if handle.write(payload[:split]) != split:
                                raise OSError("Short first append")
                            handle.flush()
                            os.fsync(handle.fileno())
                            self._hook(hook, kind, "half_io")
                            if handle.write(payload[split:]) != len(payload) - split:
                                raise OSError("Short second append")
                        else:
                            handle.seek(intent["expected_size"])
                            if handle.read(document["unit"]) != payload:
                                raise _Uncertain("Uncertain append contains invalid bytes: " + zone.name)
                    elif kind == "reset_ack":
                        # This is whole-zone reset emulation, never append rollback.
                        if size:
                            handle.truncate(0)
                    else:
                        raise Rejected("Unknown physical intent")
                    handle.flush()
                    os.fsync(handle.fileno())
                self._hook(hook, kind, "after_io")
                if kind == "stage":
                    with self.zone_path(zone.name).open("rb") as handle:
                        handle.seek(intent["expected_size"])
                        if handle.read(document["unit"]) != payload:
                            raise _Uncertain("Append authentication failed: " + zone.name)
                self._hook(hook, kind, "before_commit")
                self._commit_action(db, document, action, after, intent)
            except _Uncertain as error:
                failure = str(error)
                document["quarantine"] = failure
                self._save(db, document)
        if failure:
            raise Rejected("Store quarantined; no capacity released: " + failure)
        self._hook(hook, kind, "after_commit")
        return {"status": "APPLIED", "cursor": document["cursor"]}

    def execute(self, fence, hook=None):
        while self.advance(fence, hook=hook)["status"] != "DONE":
            pass

    def receipts(self):
        with self._transaction() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT document FROM receipts ORDER BY cursor")]

    def ledger(self):
        with self._transaction() as db:
            document = self._load(db)
            state = state_from_dict(document["state"])
            result = {}
            for zone in state.zones:
                physical = self.zone_path(zone.name).stat().st_size
                allocated = len(zone.extents) + zone.external_hold + int(zone.reservation is not None)
                charged = max(allocated, (physical + document["unit"] - 1) // document["unit"])
                # Geometry mismatch blocks reported free capacity even before reconciliation.
                mismatch = physical != len(zone.extents) * document["unit"]
                free = (min(zone.appendable(), max(0, zone.capacity - charged))
                        if not document["quarantine"] and not mismatch else 0)
                result[zone.name] = {"capacity_units": zone.capacity, "charged_units": charged,
                                     "physical_bytes": physical, "appendable_units": free,
                                     "retired_units": sum(e.status == "RETIRED" for e in zone.extents),
                                     "reserved_units": int(zone.reservation is not None),
                                     "external_hold_units": zone.external_hold,
                                     "stranded_tail_units": (zone.capacity - len(zone.extents)
                                         if zone.phase == "FINISHED" or zone.phase == "RESETTING"
                                         and zone.reset_prior == "FINISHED" else 0),
                                     "open_token": zone.uses_open(), "active_token": zone.uses_active(),
                                     "incarnation": zone.incarnation, "phase": zone.phase}
            return result

    def audit(self):
        with self._transaction() as db:
            document = self._load(db)
            state = state_from_dict(document["state"])
            validate(state)
            self._read_all(document, state)
            self._geometry(document, state, document["pending"])
            rows = db.execute("SELECT cursor FROM receipts ORDER BY cursor").fetchall()
            if [row[0] for row in rows] != list(range(document["cursor"])):
                raise Rejected("Receipt/cursor mismatch")
            return {"target": goal(state), "protected": protected(state), "cursor": document["cursor"],
                    "pending": document["pending"] is not None, "quarantined": bool(document["quarantine"])}
