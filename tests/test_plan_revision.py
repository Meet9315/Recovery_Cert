from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from prism_c.checker import check, replay
from prism_c.model import Action, Rejected, SearchStatus, Slot, State, Stripe, Witness, transition
from prism_c.partial_recovery import conventional_partial_plan, partial_oracle
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.revision_fixture import revision_fixture
from prism_c.storage import Authority
from prism_c import worker
from prism_c.partial_campaign import run_partial_campaign


class PartialRecoveryTests(unittest.TestCase):
    def test_finite_partial_matrix_agrees_with_independent_oracle(self):
        report = run_partial_campaign()
        self.assertEqual(report["configurations"], 40)
        self.assertEqual(report["unknown"], 0)
        self.assertEqual(report["disagreements"], 0)

    def test_partial_matching_preserves_staging_and_can_discard_blocking_work(self):
        state = State((Stripe("A", ("S", "T", "X", "Y")), Stripe("B", ("S", "T", "X"))),
                      tuple(Slot(f"{name}{row}", domain, "LIVE", name, row, 1)
                            for name in ("A", "B") for row, domain in enumerate(("S", "T"))) +
                      (Slot("X", "X", "STAGED", "A", 2, 1), Slot("Y", "Y")))
        result = conventional_partial_plan(state)
        oracle = partial_oracle(state, max_states=3000)
        self.assertEqual(result.status, SearchStatus.FOUND)
        self.assertEqual(oracle.status, SearchStatus.FOUND)
        self.assertTrue(check(state, result.witness).target())
        self.assertEqual(result.witness.actions[0].kind, "abandon")
        self.assertEqual(sum(a.kind == "stage" for a in result.witness.actions), 2)
        self.assertEqual(len(result.witness.actions), len(oracle.witness.actions))

    def test_budget_exhaustion_and_abandon_are_fail_closed(self):
        state = State((Stripe("A", ("S", "T", "X", "Z")),),
                      (Slot("S", "S", "LIVE", "A", 0, 1), Slot("T", "T", "LIVE", "A", 1, 1),
                       Slot("X", "X", "RESERVED", "A", 2, 1), Slot("Z", "Z")), ("X",))
        self.assertEqual(conventional_partial_plan(state, 0).status, SearchStatus.UNKNOWN)
        self.assertEqual(partial_oracle(state, 0).status, SearchStatus.UNKNOWN)
        result = conventional_partial_plan(state)
        self.assertTrue(check(state, result.witness).target())
        abandoned = transition(state, result.witness.actions[0])
        self.assertEqual(abandoned.ledger()["X"]["RETIRED"], 1)
        self.assertEqual(abandoned, replay(state, result.witness.actions[:1], False))
        for validator in (transition, lambda s, a: replay(s, (a,), False)):
            with self.assertRaises(Rejected):
                validator(state, Action("abandon", "S", "A", 0, 1))


class PlanRevisionTests(unittest.TestCase):
    def test_repeated_revision_lineage_and_foreign_destination_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence, _, parent, _, targets = self.fixture(tmp, workers=False)
            foreign = store.snapshot_for(("foreground",), ("Z:0",))
            actions = (Action("retire", "F2:0", "foreground", 2, 1),
                       Action("reclaim", "F2:0", "foreground", 2, 1),
                       Action("reserve", "F2:0", "foreground", 2, 1),
                       Action("stage", "F2:0", "foreground", 2, 2),
                       Action("promote", "F2:0", "foreground", 2, 2))
            witness = Witness(foreign.fingerprint(), actions, replay(foreign, actions).fingerprint())
            store.admit_scoped(witness, ("foreground",), ("Z:0",), fence, "other")
            store.set_offline("X", fence)
            with self.assertRaises(Rejected):
                store.revision_snapshot("initial", targets, fence)
            self.assertEqual(store.plan_info("initial")["status"], "ACTIVE")
            store.execute("other", fence)
            first = self.prepare(store, fence, targets)
            identifier = store.revise("initial", first, targets, fence, "first", parent.digest())
            second = conventional_partial_plan(store.revision_snapshot(identifier, targets, fence)).witness
            latest = store.revise(identifier, second, targets, fence, "second", first.digest())
            self.assertEqual(store.plan_info(latest)["lineage"]["revision"], 2)
            with self.assertRaises(Rejected):
                store.step(identifier, fence, 0)
            store.execute(latest, fence)
            self.assertTrue(store.audit()["target"])

    def test_cli_proposal_install_retry_resume_and_additive_migration(self):
        import contextlib
        import io
        from unittest.mock import patch
        from prism_c.__main__ import main
        with tempfile.TemporaryDirectory() as tmp:
            store, fence, _, _, _, targets = self.fixture(tmp, workers=False)
            with store._transaction() as db:
                db.execute("DROP TABLE plan_revisions")
            store = Authority(store.root)
            store.set_offline("X", fence)
            proposal = str(Path(tmp) / "proposal.json")
            def cli(arguments):
                output = io.StringIO()
                with patch.object(sys, "argv", ["prism_c", *arguments]), contextlib.redirect_stdout(output):
                    status = main()
                self.assertEqual(status, 0)
                return json.loads(output.getvalue())
            base = ["--root", str(store.root), "--plan", "initial", "--fence", str(fence)]
            cli(["replan", *base, "--report", proposal, "--destinations", *targets])
            install = ["revise", *base, "--proposal", proposal, "--request-id", "cli-request"]
            first = cli(install)
            self.assertEqual(cli(install)["successor"], first["successor"])
            cli(["resume", "--root", str(store.root), "--plan", first["successor"], "--fence", str(fence)])
            self.assertTrue(store.audit()["target"])

    def fixture(self, tmp, profile=DEFAULT_PROFILE, workers=True, mode="conventional_cached"):
        return revision_fixture(Path(tmp) / "store", profile, workers, mode, 332)

    def prepare(self, store, fence, targets):
        result = conventional_partial_plan(store.revision_snapshot("initial", targets, fence))
        self.assertEqual(result.status, SearchStatus.FOUND)
        return result.witness

    def test_preserve_bytes_charges_and_claims_both_profiles_modes_paths(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                for mode in ("conventional_cached", "selective", "full", "shadow"):
                    with self.subTest(profile=profile, workers=workers, mode=mode), tempfile.TemporaryDirectory() as tmp:
                        store, fence, contents, parent, kept, targets = self.fixture(tmp, profile, workers, mode)
                        old_slot = next(s for s in store.snapshot().slots if s.key == kept)
                        store.set_offline("X", fence)
                        witness = self.prepare(store, fence, targets)
                        self.assertNotIn(kept, [a.slot for a in witness.actions if a.kind == "stage"])
                        identifier = store.revise("initial", witness, targets, fence, "request-1", parent.digest())
                        self.assertEqual(store.revise("initial", witness, targets, fence, "request-1", parent.digest()), identifier)
                        self.assertEqual(store.plan_info("initial")["status"], "SUPERSEDED")
                        self.assertEqual(store.plan_info(identifier)["lineage"]["revision"], 1)
                        self.assertEqual(next(s for s in store.snapshot().slots if s.key == kept), old_slot)
                        with self.assertRaises(Rejected):
                            store.step("initial", fence)
                        store.execute(identifier, fence)
                        self.assertTrue(store.audit()["target"])
                        self.assertFalse(store.active_plans())
                        self.assertEqual(store.ledger()["X"]["bytes"]["RETIRED"], 1024)
                        self.assertTrue(all(store.read_snapshot(name) == data for name, data in contents.items()))

    def test_late_receipts_commands_and_changed_request_payload_rejected(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                store, fence, _, parent, _, targets = self.fixture(tmp, profile)
                intent = store.prepare_worker_step("initial", fence)
                receipt = store.execute_worker_intent(intent["token"])
                store.set_offline("X", fence)
                witness = self.prepare(store, fence, targets)
                identifier = store.revise("initial", witness, targets, fence, "request", parent.digest())
                for operation in (lambda: store.complete_worker_step(receipt, fence),
                                  lambda: store.execute_worker_intent(intent["token"]),
                                  lambda: store.revise("initial", witness, targets[:-1], fence, "request", parent.digest()),
                                  lambda: store.step("initial", fence, 0)):
                    with self.assertRaises(Rejected):
                        operation()
                self.assertEqual(store.plan_info(identifier)["cursor"], 0)
                store.execute(identifier, fence)

    def test_revision_waits_for_inflight_write_and_old_command_cannot_write_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence, _, parent, _, targets = self.fixture(tmp, FOUR_PLUS_TWO)
            intent = store.prepare_worker_step("initial", fence)
            entered, release, validated = threading.Event(), threading.Event(), threading.Event()
            def pause(point):
                if point == "before_worker_io":
                    entered.set()
                    if not release.wait(20):
                        raise RuntimeError("Paused worker not released")
            store.set_offline("X", fence)
            # Current next stage is on healthy Y, not failed X.
            witness = self.prepare(store, fence, targets)
            with ThreadPoolExecutor(max_workers=2) as pool:
                physical = pool.submit(worker.handle, store.root, intent["command"]["worker"],
                                       {"operation": "execute", "token": intent["token"]}, pause)
                self.assertTrue(entered.wait(10))
                revised = pool.submit(store.revise, "initial", witness, targets, fence, "waiting", parent.digest(),
                                      lambda point: validated.set() if point == "after_revision_validation" else None)
                try:
                    self.assertTrue(validated.wait(10))
                    self.assertFalse(revised.done())
                finally:
                    release.set()
                receipt = physical.result(20)
                identifier = revised.result(20)
            with self.assertRaises(Rejected):
                store.complete_worker_step(receipt, fence)
            with self.assertRaises(Rejected):
                store.execute_worker_intent(intent["token"])
            store.execute(identifier, fence)

    def test_conflicts_stale_snapshots_fences_and_corruption_leave_parent_owned(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence, _, parent, kept, targets = self.fixture(tmp)
            witness = self.prepare(store, fence, targets)
            store.set_offline("X", fence)
            with self.assertRaises(Rejected):
                store.revise("initial", witness, targets, fence, "stale", parent.digest())
            witness = self.prepare(store, fence, targets)
            with self.assertRaises(Rejected):
                store.revise("initial", witness, targets, fence, "wrong-parent", "bad")
            new_fence = store.takeover()
            with self.assertRaises(Rejected):
                store.revise("initial", witness, targets, fence, "old-owner", parent.digest())
            with store._transaction() as db:
                slot = db.execute("SELECT * FROM slots WHERE key=?", (kept,)).fetchone()
                store._io(db, slot, b"bad retained bytes")
            with self.assertRaises(Rejected):
                store.revise("initial", witness, targets, new_fence, "corrupt", parent.digest())
            self.assertEqual(store.plan_info("initial")["status"], "ACTIVE")
            self.assertEqual(len(store.active_plans()), 1)

    def test_concurrent_duplicate_revision_has_one_successor(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence, _, parent, _, targets = self.fixture(tmp)
            store.set_offline("X", fence)
            witness = self.prepare(store, fence, targets)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(Authority(store.root).revise, "initial", witness, targets, fence,
                                       "duplicate", parent.digest()) for _ in range(2)]
                identities = [f.result(20) for f in futures]
            self.assertEqual(identities[0], identities[1])
            self.assertEqual(len(store.active_plans()), 1)
            store.execute(identities[0], fence)

    def test_actual_process_exit_at_revision_boundaries_both_profiles_paths(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                for point in ("after_revision_validation", "after_revision_revoke", "before_revision_commit", "after_revision_commit"):
                    with self.subTest(profile=profile, workers=workers, point=point), tempfile.TemporaryDirectory() as tmp:
                        store, fence, contents, parent, _, targets = self.fixture(tmp, profile, workers)
                        pending = store.prepare_worker_step("initial", fence) if workers else None
                        store.set_offline("X", fence)
                        witness = self.prepare(store, fence, targets)
                        request = {"root": str(store.root), "mode": "conventional_cached", "parent": "initial",
                                   "witness": witness.to_dict(), "destinations": targets, "fence": fence,
                                   "request_id": "crash", "expected_digest": parent.digest(), "point": point}
                        child = subprocess.run([sys.executable, "-m", "prism_c.revision_fault"],
                                               input=json.dumps(request), text=True, capture_output=True, timeout=40)
                        self.assertEqual(child.returncode, 77, child.stderr)
                        restarted = Authority(store.root)
                        self.assertEqual(restarted.plan_info("initial")["status"],
                                         "SUPERSEDED" if point == "after_revision_commit" else "ACTIVE")
                        identifier = restarted.revise("initial", witness, targets, fence, "crash", parent.digest())
                        if pending:
                            with self.assertRaises(Rejected):
                                restarted.execute_worker_intent(pending["token"])
                        restarted.execute(identifier, fence)
                        self.assertTrue(restarted.audit()["target"])
                        self.assertTrue(all(restarted.read(name) == content for name, content in contents.items()))
