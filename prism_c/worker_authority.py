"""Two-phase stage/reclaim integration; logical metadata stays charged in flight."""

import base64
from dataclasses import asdict
import json
import uuid

from .checker import replay
from .coding import digest, recover
from .model import Rejected, Witness
from . import worker


class WorkerRetry(Exception):
    """The cursor moved from a metadata action to a worker action."""


class WorkerAuthority:
    def _workers_enabled(self, db):
        return self._get(db, "io_mode") == "workers"

    def enable_workers(self, fence):
        with self._transaction() as db:
            self._fence(db, fence)
            if db.execute("SELECT 1 FROM plans LIMIT 1").fetchone():
                raise Rejected("Enable workers after fixture import and before any admission")
            for index, domain in enumerate(self._get(db, "domains")):
                count = db.execute("SELECT COUNT(*) FROM slots WHERE domain=?", (domain,)).fetchone()[0]
                worker.initialize(self.root, index, self._get(db, "incarnation"), fence,
                                  self._get(db, "slot_size"), count)
                worker.rpc(self.root, index, "fence", fence=fence)
            db.execute("UPDATE settings SET value=? WHERE key='io_mode'", (json.dumps("workers"),))
            self._event(db, "workers_enabled", {"domains": self._get(db, "domains")})

    def _worker_fence_all(self, db, fence):
        if self._workers_enabled(db):
            for index, _ in enumerate(self._get(db, "domains")):
                worker.rpc(self.root, index, "fence", fence=fence)

    def _revoke_intents(self, db, plan_id):
        for pending in db.execute("SELECT * FROM worker_intents WHERE plan=? AND status='PREPARED'", (plan_id,)):
            command = json.loads(pending["command"])
            worker.rpc(self.root, command["worker"], "revoke", token=pending["token"])
        db.execute("UPDATE worker_intents SET status='REVOKED' WHERE plan=? AND status='PREPARED'", (plan_id,))

    def prepare_worker_step(self, plan_id, fence, step_id=None):
        with self._transaction() as db:
            self._fence(db, fence)
            if not self._workers_enabled(db):
                raise Rejected("Storage workers are not enabled")
            record = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
            if record is None or record["status"] != "ACTIVE" or record["fence"] != fence:
                raise Rejected("Worker preparation needs an active owned plan")
            cursor = record["cursor"]
            if step_id is not None and step_id != cursor:
                raise Rejected("Worker preparation needs current step identity")
            witness = Witness.from_dict(json.loads(record["witness"]))
            current = self._snapshot(db)
            scope = self._scope(db, plan_id)
            if scope is not None:
                self._check_claims(db, scope, plan_id)
                current = scope.project(current)
            if cursor == 0 and current.fingerprint() != witness.initial:
                raise Rejected("Worker initial snapshot conflict")
            final = replay(current, witness.actions[cursor:])
            if final.fingerprint() != witness.terminal:
                raise Rejected("Worker suffix cannot reach committed target")
            for stripe in current.stripes:
                self._valid_rows(db, stripe.name)
            action = witness.actions[cursor]
            if action.kind not in ("stage", "reclaim"):
                raise Rejected("Only stage/reclaim need physical worker intents")
            replay(current, (action,), require_target=False)
            if action.kind == "reclaim" and db.execute("SELECT 1 FROM pins WHERE slot=?", (action.slot,)).fetchone():
                raise Rejected("Cannot authorize reclamation of a pinned slot")
            slot = dict(db.execute("SELECT * FROM slots WHERE key=?", (action.slot,)).fetchone())
            old = db.execute("SELECT * FROM worker_intents WHERE plan=? AND status='PREPARED'", (plan_id,)).fetchone()
            if old is not None:
                previous = json.loads(old["command"])
                if (previous["cursor"] == cursor and previous["fence"] == fence
                        and previous["state"] == current.fingerprint()):
                    return {"token": old["token"], "command": previous}
                self._revoke_intents(db, plan_id)
            payload = b""
            if action.kind == "stage":
                spec, rows = self._valid_rows(db, action.stripe)
                payload = recover(rows, spec["length"], spec["profile"])[1][action.row]
            command = {"store": self._get(db, "incarnation"), "plan": plan_id, "cursor": cursor,
                       "fence": fence, "witness": witness.digest(), "state": current.fingerprint(),
                       "worker": self._get(db, "domains").index(slot["domain"]), "kind": action.kind,
                       "action": asdict(action), "slot": slot,
                       "payload": base64.b64encode(payload).decode("ascii")}
            token = uuid.uuid4().hex
            db.execute("INSERT INTO worker_intents VALUES (?,?,?,'PREPARED')",
                       (token, plan_id, worker.canonical(command)))
            self._event(db, "worker_prepared", {"token": token, "plan": plan_id, "cursor": cursor,
                                               "kind": action.kind, "slot": slot["key"]})
            return {"token": token, "command": command}

    def execute_worker_intent(self, token):
        with self._transaction() as db:
            row = db.execute("SELECT command FROM worker_intents WHERE token=?", (token,)).fetchone()
            if row is None:
                raise Rejected("Unknown worker intent")
            command = json.loads(row[0])
        # No authority write transaction is held while this process does I/O.
        return worker.rpc(self.root, command["worker"], "execute", token=token)

    def complete_worker_step(self, receipt, fence, fault=None):
        if not isinstance(receipt, dict):
            raise Rejected("Malformed worker receipt")
        with self._transaction() as db:
            self._fence(db, fence)
            row = db.execute("SELECT command FROM worker_intents WHERE token=?", (receipt.get("token"),)).fetchone()
            if row is None:
                raise Rejected("Unknown receipt intent")
            command = json.loads(row[0])
            if receipt.get("fence") != fence or receipt.get("plan") != command["plan"]:
                raise Rejected("Delayed receipt belongs to a stale fence or plan")
        return self.step(command["plan"], fence, command["cursor"], fault, _receipt=receipt)

    def _accept_worker_receipt(self, db, receipt, plan_id, cursor, witness, current, action, slot, payload):
        row = db.execute("SELECT * FROM worker_intents WHERE token=?", (receipt.get("token"),)).fetchone()
        if row is None or row["status"] != "PREPARED" or row["plan"] != plan_id:
            raise Rejected("Receipt does not own an active intent")
        command = json.loads(row["command"])
        if (command["cursor"] != cursor or command["fence"] != self._get(db, "fence")
                or command["witness"] != witness.digest() or command["state"] != current.fingerprint()
                or command["action"] != asdict(action) or command["slot"] != dict(slot)
                or base64.b64decode(command["payload"], validate=True) != payload):
            raise Rejected("Receipt context or allocation incarnation changed")
        durable = worker.rpc(self.root, command["worker"], "receipt", token=receipt["token"])
        if durable != receipt:
            raise Rejected("Receipt was altered or not durably acknowledged")
        raw = self._io(db, slot)
        expected = payload.ljust(self._get(db, "slot_size"), b"\x00")
        if raw != expected or digest(raw) != receipt["physical_digest"]:
            raise Rejected("Worker bytes do not match acknowledgement")
        db.execute("UPDATE worker_intents SET status='APPLIED' WHERE token=?", (receipt["token"],))
        self._event(db, "worker_ack", {"token": receipt["token"], "receipt": receipt})

    def _maybe_worker_step(self, plan_id, fence, step_id, fault):
        with self._transaction() as db:
            if not self._workers_enabled(db):
                return None
            record = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
            if record is None or record["status"] != "ACTIVE":
                return None
            cursor = record["cursor"]
            if step_id is not None and step_id != cursor:
                return None
            witness = Witness.from_dict(json.loads(record["witness"]))
            if witness.actions[cursor].kind not in ("stage", "reclaim"):
                return None
        try:
            intent = self.prepare_worker_step(plan_id, fence, step_id)
            if fault:
                fault("after_worker_prepare")
            receipt = self.execute_worker_intent(intent["token"])
            if fault:
                fault("after_worker_receipt")
            return self.complete_worker_step(receipt, fence, fault)
        except Rejected:
            # Another controller may have completed this identical step while
            # the worker request was queued. A stale fence/cancel never becomes
            # a successful duplicate acknowledgement.
            with self._transaction() as db:
                self._fence(db, fence)
                latest = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
                if latest and latest["status"] != "CANCELED" and latest["cursor"] > cursor:
                    return {"status": "ALREADY_APPLIED", "cursor": latest["cursor"]}
            raise
