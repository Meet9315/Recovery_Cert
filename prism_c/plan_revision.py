"""Checked, idempotent successor plans with atomic resource transfer."""

from dataclasses import asdict
import hashlib
import json
import uuid

from .checker import check
from .coding import digest
from .model import Rejected, Witness
from .scope import PlanScope


REVISION_SCHEMA = """CREATE TABLE IF NOT EXISTS plan_revisions(
 plan TEXT PRIMARY KEY, parent TEXT NOT NULL, revision INTEGER NOT NULL,
 request TEXT NOT NULL UNIQUE, request_digest TEXT NOT NULL)"""


class PlanRevision:
    def _revision_scope(self, db, plan_id, destinations, fence):
        self._fence(db, fence)
        parent = db.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
        if parent is None or parent["status"] != "ACTIVE" or parent["fence"] != fence:
            raise Rejected("Revision needs an active owned parent")
        old_scope = self._scope(db, plan_id)
        if old_scope is None:
            raise Rejected("Revision currently requires an explicitly scoped plan")
        self._check_claims(db, old_scope, plan_id)
        state = self._snapshot(db)
        scope = PlanScope.derive(state, old_scope.stripes, tuple(sorted(set(old_scope.slots) | set(destinations))))
        for key in scope.slots:
            owner = db.execute("SELECT plan FROM slot_claims WHERE slot=?", (key,)).fetchone()
            if owner and owner["plan"] != plan_id:
                raise Rejected("Revision destination belongs to another active plan")
        return parent, scope, scope.project(state)

    def revision_snapshot(self, plan_id, destinations, fence):
        """Plan outside the writer lock; installation rechecks this fingerprint."""
        with self._transaction() as db:
            return self._revision_scope(db, plan_id, destinations, fence)[2]

    def _verify_staged(self, db, snapshot, abandoned=()):
        for slot in snapshot.slots:
            if slot.status != "STAGED" or slot.domain in snapshot.offline or slot.key in abandoned:
                continue
            spec = db.execute("SELECT * FROM stripes WHERE name=?", (slot.stripe,)).fetchone()
            record = db.execute("SELECT * FROM slots WHERE key=?", (slot.key,)).fetchone()
            raw = self._io(db, record)
            row_digest = digest(raw[:spec["fragment_size"]])
            if (row_digest != record["digest"] or row_digest != json.loads(spec["row_digests"])[slot.row]
                    or any(raw[spec["fragment_size"]:])):
                raise Rejected("Retained staged bytes or padding do not match immutable row identity")

    def revise(self, plan_id, witness, destinations, fence, request_id, expected_digest, fault=None):
        """Return a new plan identity; the old identity can never mutate it.

        Duplicate requests return their committed successor only for the exact
        same payload and a current authority fence. Revoke is durable outside
        the authority DB: a precommit crash may leave the old plan fail-closed
        until this request is retried or a fenced successor prepares new work.
        """
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 128:
            raise Rejected("Revision needs a bounded nonempty request identity")
        targets = tuple(sorted(set(destinations)))
        payload = {"parent": plan_id, "witness": witness.digest(), "destinations": targets,
                   "expected_parent_digest": expected_digest}
        request_digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        def hit(point):
            if fault:
                fault(point)
        with self._transaction() as db:
            self._fence(db, fence)
            prior = db.execute("SELECT * FROM plan_revisions WHERE request=?", (request_id,)).fetchone()
            if prior:
                if prior["request_digest"] != request_digest:
                    raise Rejected("Revision request identity reused with changed payload")
                return prior["plan"]
            parent, scope, snapshot = self._revision_scope(db, plan_id, targets, fence)
            old_witness = Witness.from_dict(json.loads(parent["witness"]))
            if old_witness.digest() != expected_digest:
                raise Rejected("Parent witness identity changed")
            final = check(snapshot, witness)
            if any(s.status in {"RESERVED", "STAGED"} for s in final.slots):
                raise Rejected("Revision terminal cannot leave unowned partial allocations")
            for spec in snapshot.stripes:
                self._valid_rows(db, spec.name)
            abandoned = {a.slot for a in witness.actions if a.kind == "abandon"}
            self._verify_staged(db, snapshot, abandoned)
            cache = None if self.validation_mode == "full" else self.cache_type.build(snapshot, witness)
            hit("after_revision_validation")
            self._revoke_intents(db, plan_id)
            hit("after_revision_revoke")
            identifier = uuid.uuid4().hex
            lineage = db.execute("SELECT revision FROM plan_revisions WHERE plan=?", (plan_id,)).fetchone()
            revision = (lineage["revision"] if lineage else 0) + 1
            db.execute("UPDATE plans SET status='SUPERSEDED' WHERE id=?", (plan_id,))
            db.execute("INSERT INTO plans VALUES (?,?,0,?,?)", (identifier, json.dumps(witness.to_dict()),
                       "ACTIVE" if witness.actions else "DONE", fence))
            db.execute("INSERT INTO plan_revisions VALUES (?,?,?,?,?)",
                       (identifier, plan_id, revision, request_id, request_digest))
            db.execute("INSERT INTO plan_scopes VALUES (?,?,?)",
                       (identifier, json.dumps(scope.stripes), json.dumps(scope.slots)))
            self._release_claims(db, plan_id)
            if witness.actions:
                for name in scope.stripes:
                    db.execute("INSERT INTO stripe_claims VALUES (?,?)", (name, identifier))
                for key in scope.slots:
                    db.execute("INSERT INTO slot_claims VALUES (?,?)", (key, identifier))
                for key in {a.slot for a in witness.actions if a.kind == "reserve"}:
                    db.execute("INSERT INTO holds VALUES (?,?)", (key, identifier))
                for slot in snapshot.slots:
                    if slot.status == "LIVE":
                        db.execute("INSERT INTO pins VALUES (?,?,?)", (slot.key, identifier, slot.incarnation))
            db.execute("DELETE FROM validation_cache WHERE plan=?", (plan_id,))
            if cache:
                db.execute("INSERT INTO validation_cache VALUES (?,?)",
                           (identifier, cache.to_json(self._get(db, "incarnation"))))
            self._event(db, "revise", {"parent": plan_id, "plan": identifier, "revision": revision,
                "request": request_id, "old_witness": expected_digest, "witness": witness.digest(),
                "scope": asdict(scope), "retained_staged_slots": [s.key for s in snapshot.slots if s.status == "STAGED" and s.key not in abandoned],
                "retained_reserved_slots": [s.key for s in snapshot.slots if s.status == "RESERVED" and s.key not in abandoned]})
            hit("before_revision_commit")
        hit("after_revision_commit")
        return identifier
