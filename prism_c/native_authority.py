"""Serialized SQLite authority bound to one live native-emulator session.

Device-session loss fails closed; power-loss/session-recreation recovery is not
supported. Native commands are drained and fenced by the session supervisor.
"""

from contextlib import closing, contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import socket
import sqlite3
import uuid

from .coding import digest, encode, recover
from .model import Rejected
from .zoned_model import goal, protected, replay, step, validate
from .zoned_store import state_from_dict, witness_from_dict


FORMAT = "prism-native-session-v1"
PHYSICAL = {"open", "close", "finish", "stage", "reset_ack"}


class Uncertain(Rejected):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class NativeClient:
    def __init__(self, descriptor, expected=None):
        self.descriptor = str(Path(descriptor).resolve())
        self.connection = json.loads(Path(descriptor).read_text())
        self.store = None
        self.binding = {k: self.connection[k] for k in ("session", "serial", "namespaces", "boot_id")}
        if expected is not None and self.binding != expected:
            raise Rejected("Native session identity changed; no device operation allowed")

    def call(self, op, fence, **arguments):
        request = {"session": self.binding["session"], "token": self.connection["token"],
                   "op": op, "fence": fence, "store": self.store, **arguments}
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as channel:
                channel.settimeout(20)
                channel.connect(self.connection["socket"])
                channel.sendall((canonical(request)+"\n").encode())
                with channel.makefile("rb") as stream:
                    raw = stream.readline(100000)
            response = json.loads(raw)
        except (OSError, ValueError) as error:
            raise Uncertain("Native session unavailable or outcome uncertain") from error
        if response.get("session") != self.binding["session"] or not response.get("success"):
            raise Uncertain("Native session/fence rejected: " + str(response.get("error")))
        return response.get("result")


class NativeAuthority:
    """One immutable scope/plan, trusted local clients, native session continuity."""

    def __init__(self, root, client=None):
        self.root = Path(root).resolve()
        self.db_path = self.root / "native.sqlite3"
        if not self.db_path.is_file():
            raise Rejected("Not a native authority")
        with self.transaction() as db:
            document = self.load(db)
            if document["format"] != FORMAT or document["bootstrap"] != "COMPLETE":
                raise Rejected("Unsupported or incomplete native bootstrap")
            validate(state_from_dict(document["state"]))
        self.client = client or NativeClient(document["descriptor"], document["binding"])
        if self.client.binding != document["binding"]:
            raise Rejected("Native device binding changed")
        if self.client.store is not None and self.client.store != document["store"]:
            raise Rejected("Native client is bound to another authority")
        self.client.store = document["store"]

    @classmethod
    def create(cls, root, initial, contents, descriptor):
        validate(initial)
        if (not protected(initial) or initial.offline or set(contents) != {s.name for s in initial.stripes}
                or any(z.phase not in ("EMPTY", "FULL") or z.reservation for z in initial.zones)):
            raise Rejected("Invalid immutable native bootstrap")
        client = NativeClient(descriptor)
        if {n: v["capacity_units"] for n, v in client.binding["namespaces"].items()} != {z.name: z.capacity for z in initial.zones}:
            raise Rejected("Native physical capacity binding differs from model")
        manifests, encoded = {}, {}
        for spec in initial.stripes:
            data = contents[spec.name]
            rows = encode(data, spec.profile)
            if any(len(row) != 4096 for row in rows):
                raise Rejected("Native prototype uses exactly 4096-byte code rows")
            encoded[spec.name] = rows
            manifests[spec.name] = {"epoch": 1, "profile": spec.profile, "length": len(data),
                                    "sha256": digest(data), "rows": [digest(row) for row in rows]}
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=False)
        db_path = root / "native.sqlite3"
        document = {"format": FORMAT, "bootstrap": "INCOMPLETE", "store": uuid.uuid4().hex,
                    "descriptor": client.descriptor, "binding": client.binding,
                    "state": asdict(initial), "manifests": manifests, "fence": 0,
                    "plan": None, "cursor": 0, "pending": None, "quarantine": None}
        with closing(sqlite3.connect(db_path)) as db, db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE authority (id INTEGER PRIMARY KEY CHECK(id=1), document TEXT NOT NULL)")
            db.execute("CREATE TABLE receipts (cursor INTEGER PRIMARY KEY, document TEXT NOT NULL)")
            db.execute("INSERT INTO authority VALUES(1,?)", (canonical(document),))
        client.store = document["store"]
        client.call("bind", 0)
        # Offline bootstrap is deliberately not resumable after interruption.
        for zone in initial.zones:
            observed = client.call("report", 0, zone=zone.name)
            if observed["condition"] != 1 or observed["wp_lba"] != 0:
                raise Rejected("Bootstrap requires a new empty namespace")
            for offset, extent in enumerate(zone.extents):
                payload = encoded[extent.stripe][extent.row] if extent.stripe else bytes([165])*4096
                client.call("write", 0, zone=zone.name, offset=offset*4096, payload=payload.hex(), operation="bootstrap")
            client.call("flush", 0, zone=zone.name)
        document["bootstrap"] = "COMPLETE"
        with closing(sqlite3.connect(db_path)) as db, db:
            db.execute("PRAGMA synchronous=FULL")
            cls.save(db, document)
        authority = cls(root, client)
        authority.audit()
        return authority

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.db_path.as_uri()+"?mode=rw", uri=True, timeout=30, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.execute("COMMIT")
        except Uncertain as error:
            if db.in_transaction:
                db.execute("ROLLBACK")
            # Preserve the previously committed intent/fence; uncertainty must
            # not publish the failed transaction or expose capacity as free.
            db.execute("BEGIN IMMEDIATE")
            document = self.load(db)
            document["quarantine"] = str(error)
            self.save(db, document)
            db.execute("COMMIT")
            raise
        except BaseException:
            if db.in_transaction:
                db.execute("ROLLBACK")
            raise
        finally:
            db.close()

    @staticmethod
    def load(db):
        return json.loads(db.execute("SELECT document FROM authority WHERE id=1").fetchone()[0])

    @staticmethod
    def save(db, document):
        db.execute("UPDATE authority SET document=? WHERE id=1", (canonical(document),))

    def check(self, document, fence):
        if (document["format"] != FORMAT or document["bootstrap"] != "COMPLETE"
                or document["binding"] != self.client.binding or document["store"] != self.client.store):
            raise Rejected("Native authority/session binding changed")
        if type(fence) is not int or document["fence"] != fence:
            raise Rejected("Stale native authority fence")
        if document["quarantine"]:
            raise Rejected("Native store quarantined: "+document["quarantine"])

    def takeover(self):
        with self.transaction() as db:
            document = self.load(db)
            self.check(document, document["fence"])
            fence = document["fence"] + 1
            # The supervisor serially drains prior commands, advances its fence,
            # then rejects any late old-fence request before submitting device I/O.
            self.client.call("fence", fence)
            document["fence"] = fence
            self.save(db, document)
        return fence

    def info(self):
        with self.transaction() as db:
            return self.load(db)

    def snapshot(self):
        return state_from_dict(self.info()["state"])

    @staticmethod
    def matches(zone, observed):
        phase = zone.reset_prior if zone.phase == "RESETTING" else zone.phase
        conditions = {"EMPTY": (1,), "OPEN": (2, 3), "CLOSED": (4,), "FULL": (14,), "FINISHED": (14,)}
        return (observed["type"] == 2 and observed["start_lba"] == 0 and observed["reported_zones"] == 1
                and observed["capacity_lba"] == zone.capacity*8
                and observed["condition"] in conditions[phase]
                and (phase in ("FULL", "FINISHED") or observed["wp_lba"] == len(zone.extents)*8))

    def reports(self, document):
        state = state_from_dict(document["state"])
        pending = document["pending"]
        if pending:
            action = witness_from_dict(document["plan"]).actions[document["cursor"]]
            if action.kind not in PHYSICAL or pending != self.intent(document, state, action):
                raise Rejected("Native pending identity changed")
            following = step(state, action)
        else:
            following = state
        reports = {}
        for zone, after in zip(state.zones, following.zones):
            observed = self.client.call("report", document["fence"], zone=zone.name)
            if not self.matches(zone, observed) and not (pending and self.matches(after, observed)):
                raise Uncertain("Native geometry/uncertain partial outcome: "+zone.name)
            reports[zone.name] = observed
        return reports

    def decoded(self, document, state):
        result = {}
        for spec in state.stripes:
            manifest, rows = document["manifests"][spec.name], {}
            for zone in state.zones:
                if zone.domain in state.offline:
                    continue
                for offset, extent in enumerate(zone.extents):
                    if extent.status == "LIVE" and extent.stripe == spec.name:
                        payload = bytes.fromhex(self.client.call("read", document["fence"], zone=zone.name, offset=offset*4096, length=4096))
                        if digest(payload) != manifest["rows"][extent.row]:
                            raise Uncertain("Native source row authentication failure")
                        rows[extent.row] = payload
            try:
                data, regenerated = recover(rows, manifest["length"], spec.profile)
            except Rejected as error:
                raise Uncertain("Native code rows do not reconstruct consistently") from error
            if digest(data) != manifest["sha256"] or [digest(row) for row in regenerated] != manifest["rows"]:
                raise Uncertain("Native object/regenerated-row identity failure")
            result[spec.name] = data, regenerated
        return result

    def read(self, name):
        with self.transaction() as db:
            document = self.load(db)
            self.check(document, document["fence"])
            self.reports(document)
            return self.decoded(document, state_from_dict(document["state"]))[name][0]

    def admit(self, witness, fence):
        with self.transaction() as db:
            document = self.load(db)
            self.check(document, fence)
            state = state_from_dict(document["state"])
            if document["plan"] is not None or witness.initial != state.fingerprint() or not goal(replay(state, witness)):
                raise Rejected("Native plan is stale, already installed or incomplete")
            self.reports(document)
            self.decoded(document, state)
            document["plan"] = witness.to_dict()
            self.save(db, document)

    @staticmethod
    def hook(function, kind, boundary):
        if function:
            function(kind, boundary)

    @staticmethod
    def intent(document, state, action):
        binding = {"store": document["store"], "cursor": document["cursor"], "before": state.fingerprint(),
                   "action": asdict(action), "session": document["binding"]["session"]}
        if action.kind == "stage":
            manifest = document["manifests"][action.stripe]
            binding.update(epoch=manifest["epoch"], row_sha256=manifest["rows"][action.row])
        return {**binding, "id": digest(canonical(binding).encode())}

    def commit(self, db, document, action, following, operation):
        receipt = {"cursor": document["cursor"], "action": asdict(action), "operation": operation,
                   "stage_bytes": 4096 if action.kind == "stage" else 0}
        db.execute("INSERT INTO receipts VALUES(?,?)", (document["cursor"], canonical(receipt)))
        document.update(state=asdict(following), cursor=document["cursor"]+1, pending=None)
        self.save(db, document)

    def advance(self, fence, expected_cursor=None, hook=None):
        if expected_cursor is not None and (type(expected_cursor) is not int or expected_cursor < 0):
            raise Rejected("Invalid native cursor")
        with self.transaction() as db:
            document = self.load(db)
            self.check(document, fence)
            cursor = document["cursor"]
            if expected_cursor is not None and expected_cursor < cursor:
                row = db.execute("SELECT document FROM receipts WHERE cursor=?", (expected_cursor,)).fetchone()
                if row is None:
                    raise Rejected("Unknown old native cursor")
                return {"status": "ALREADY_APPLIED", "receipt": json.loads(row[0])}
            if expected_cursor is not None and expected_cursor != cursor:
                raise Rejected("Future native cursor")
            if document["plan"] is None:
                raise Rejected("No native plan")
            actions = witness_from_dict(document["plan"]).actions
            if cursor == len(actions):
                return {"status": "DONE", "cursor": cursor}
            action, state = actions[cursor], state_from_dict(document["state"])
            if document["pending"] is None:
                self.reports(document)
                self.decoded(document, state)
                following = step(state, action)
                if action.kind not in PHYSICAL:
                    if action.kind == "promote":
                        zone = next(z for z in state.zones if z.name == action.zone)
                        extent = zone.extents[action.offset]
                        payload = bytes.fromhex(self.client.call("read", fence, zone=zone.name, offset=action.offset*4096, length=4096))
                        if digest(payload) != document["manifests"][extent.stripe]["rows"][extent.row]:
                            raise Rejected("Unverified native staged row")
                    self.hook(hook, action.kind, "before_commit")
                    self.commit(db, document, action, following, None)
                    local = True
                else:
                    self.hook(hook, action.kind, "before_prepare")
                    document["pending"] = self.intent(document, state, action)
                    self.save(db, document)
                    local = False
            else:
                local = False
        if local:
            self.hook(hook, action.kind, "after_commit")
            return {"status": "APPLIED", "cursor": cursor+1}
        self.hook(hook, action.kind, "after_prepare")
        failure = None
        with self.transaction() as db:
            document = self.load(db)
            self.check(document, fence)
            if document["cursor"] != cursor:
                return {"status": "ALREADY_APPLIED", "cursor": document["cursor"]}
            state = state_from_dict(document["state"])
            action = witness_from_dict(document["plan"]).actions[cursor]
            pending = document["pending"]
            if pending != self.intent(document, state, action):
                raise Rejected("Native intent identity changed")
            following = step(state, action)
            zone = next(z for z in state.zones if z.name == action.zone)
            target = next(z for z in following.zones if z.name == action.zone)
            try:
                observed = self.reports(document)[zone.name]
                decoded = self.decoded(document, state)
                self.hook(hook, action.kind, "before_io")
                if action.kind == "stage":
                    payload = decoded[action.stripe][1][action.row]
                    position = len(zone.extents)*4096
                    if self.matches(zone, observed):
                        self.client.call("write", fence, zone=zone.name, offset=position, payload=payload[:2048].hex(), operation=pending["id"])
                        self.client.call("flush", fence, zone=zone.name)
                        self.hook(hook, action.kind, "half_io")
                        self.client.call("write", fence, zone=zone.name, offset=position+2048, payload=payload[2048:].hex(), operation=pending["id"])
                    actual = bytes.fromhex(self.client.call("read", fence, zone=zone.name, offset=position, length=4096))
                    if actual != payload:
                        raise Uncertain("Native completed append does not authenticate")
                elif not self.matches(target, observed):
                    self.client.call("manage", fence, zone=zone.name,
                                     action={"open": 3, "close": 1, "finish": 2, "reset_ack": 4}[action.kind], operation=pending["id"])
                self.client.call("flush", fence, zone=zone.name)
                self.hook(hook, action.kind, "after_io")
                final_report = self.client.call("report", fence, zone=zone.name)
                if not self.matches(target, final_report):
                    raise Uncertain("Native physical acknowledgement differs from target")
                self.hook(hook, action.kind, "before_commit")
                self.commit(db, document, action, following, pending["id"])
            except Uncertain as error:
                failure = str(error)
                document["quarantine"] = failure
                self.save(db, document)
        if failure:
            raise Rejected("Native store quarantined; no capacity released: "+failure)
        self.hook(hook, action.kind, "after_commit")
        return {"status": "APPLIED", "cursor": cursor+1}

    def execute(self, fence, hook=None):
        while self.advance(fence, hook=hook)["status"] != "DONE":
            pass

    def receipts(self):
        with self.transaction() as db:
            return [json.loads(row[0]) for row in db.execute("SELECT document FROM receipts ORDER BY cursor")]

    def ledger(self):
        with self.transaction() as db:
            document = self.load(db)
            state = state_from_dict(document["state"])
            result = {}
            for zone in state.zones:
                try:
                    observed = self.client.call("report", document["fence"], zone=zone.name)
                    occupied = zone.capacity if observed["condition"] == 14 else (observed["wp_lba"]+7)//8
                    available = not document["quarantine"] and not document["pending"] and self.matches(zone, observed)
                    native_condition = observed["condition"]
                    open_token = zone.uses_open() or native_condition in (2, 3)
                    active_token = zone.uses_active() or native_condition in (2, 3, 4)
                except Uncertain:
                    occupied, available = zone.capacity, False
                    native_condition, open_token, active_token = None, True, True
                charged = max(occupied, len(zone.extents)+zone.external_hold+int(zone.reservation is not None))
                result[zone.name] = {"capacity_units": zone.capacity, "charged_units": charged,
                                     "appendable_units": min(zone.appendable(), max(0, zone.capacity-charged)) if available else 0,
                                     "incarnation": zone.incarnation, "phase": zone.phase, "native_condition": native_condition,
                                     "open_token_charged": open_token, "active_token_charged": active_token,
                                     "native_resource_status": "KNOWN" if native_condition is not None else "UNKNOWN"}
            return result

    def audit(self):
        with self.transaction() as db:
            document = self.load(db)
            self.check(document, document["fence"])
            state = state_from_dict(document["state"])
            validate(state)
            self.reports(document)
            self.decoded(document, state)
            if [r[0] for r in db.execute("SELECT cursor FROM receipts ORDER BY cursor")] != list(range(document["cursor"])):
                raise Rejected("Native receipt/cursor mismatch")
            return {"target": goal(state), "protected": protected(state), "cursor": document["cursor"], "pending": document["pending"] is not None}
