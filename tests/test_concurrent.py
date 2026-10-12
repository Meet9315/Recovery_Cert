"""Conflict, isolation, race and restart evidence for whole-stripe scopes."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from itertools import combinations
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest

from prism_c.baseline import conventional_plan
from prism_c.model import Rejected, Slot
from prism_c.scope import PlanScope
from prism_c.storage import Authority
from tests.test_storage import make_store


class ConcurrentPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "store"
        self.store, self.fence = make_store(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def admit(self, name, destination, authority=None):
        authority = authority or self.store
        state = authority.snapshot_for((name,), (destination,))
        return authority.admit_scoped(conventional_plan(state), (name,), (destination,),
                                      self.fence, name)

    def pair(self, authority=None):
        return self.admit("A", "Y:0", authority), self.admit("B", "X:0", authority)

    def sql(self, statement, parameters=()):
        # Administrative mutation is used only to inject failures, never to
        # authorize work or construct an allegedly valid production state.
        with closing(sqlite3.connect(self.store.db_path)) as db:
            db.execute(statement, parameters)
            db.commit()

    def test_scope_derives_complete_membership_and_rejects_bad_selection(self):
        state = self.store.snapshot()
        scope = PlanScope.derive(state, ("A",), ("Y:0",))
        self.assertEqual(scope.slots, ("S:0", "T:0", "Y:0"))
        self.assertTrue(scope.compatible(PlanScope.derive(state, ("B",), ("X:0",))))
        for names, slots in [((), ()), (("A", "A"), ()), (("unknown",), ()),
                             (("A",), ("missing",)), (("A",), ("Y:0", "Y:0")),
                             (("A",), ("S:1",))]:
            with self.subTest(names=names, slots=slots), self.assertRaises(Rejected):
                PlanScope.derive(state, names, slots)
        phantom = replace(state, slots=state.slots + (Slot("phantom", "Y", "RETIRED", "A"),))
        with self.assertRaises(Rejected):
            scope.project(phantom)
        with self.assertRaises(Rejected):
            scope.project(replace(state, stripes=state.stripes + (state.stripes[0],)))

    def test_disjoint_admission_progress_and_readback_all_validation_modes(self):
        for mode in ("conventional_cached", "full", "selective", "shadow"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_store(Path(tmp) / "store")
                store = Authority(store.root, mode)
                plans = []
                for name, dest in (("A", "Y:0"), ("B", "X:0")):
                    witness = conventional_plan(store.snapshot_for((name,), (dest,)))
                    plans.append(store.admit_scoped(witness, (name,), (dest,), fence, name))
                self.assertEqual(len(store.active_plans()), 2)
                self.assertEqual(store.ledger()["X"]["slots"]["FREE"], 0)
                self.assertEqual(store.ledger()["Y"]["slots"]["FREE"], 0)
                for _ in range(3):
                    for identifier in plans:
                        store.step(identifier, fence)
                        store.audit()
                reopened = Authority(store.root, mode)
                self.assertTrue(reopened.audit()["target"])
                self.assertEqual(reopened.read("A"), b"immutable object A with an odd length!")
                self.assertEqual(reopened.read("B"), b"immutable object B")
                self.assertEqual(reopened.active_plans(), [])
                for event in reopened.events():
                    if event["kind"] == "step" and mode != "full":
                        self.assertEqual(event["detail"]["validation"]["replayed_actions"], 0)

    def test_conflicting_stripe_or_destination_rolls_back_all_claims(self):
        self.admit("A", "Y:0")
        for name, dest in (("A", "X:0"), ("B", "Y:0")):
            state = self.store.snapshot_for((name,), (dest,))
            before = self.store.snapshot()
            with self.subTest(name=name), self.assertRaises(Rejected):
                self.store.admit_scoped(conventional_plan(state), (name,), (dest,), self.fence)
            self.assertEqual(before, self.store.snapshot())
            self.assertEqual(len(self.store.active_plans()), 1)
        # Rejected B admission did not leak B's source or X claims.
        self.admit("B", "X:0")

    def test_full_and_scoped_admissions_exclude_each_other(self):
        full = conventional_plan(self.store.snapshot())
        self.admit("A", "Y:0")
        with self.assertRaises(Rejected):
            self.store.admit(full, self.fence)
        self.store.cancel("A", self.fence)
        self.store.admit(full, self.fence, "full")
        with self.assertRaises(Rejected):
            self.admit("B", "X:0")
        self.store.execute("full", self.fence)

    def test_every_order_preserving_two_plan_interleaving(self):
        # Exhaustive only for this fixture: choose A's three steps among six.
        schedules = list(combinations(range(6), 3))
        self.assertEqual(len(schedules), 20)
        for positions in schedules:
            with self.subTest(a_positions=positions), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_store(Path(tmp) / "store")
                for name, dest in (("A", "Y:0"), ("B", "X:0")):
                    store.admit_scoped(conventional_plan(store.snapshot_for((name,), (dest,))),
                                       (name,), (dest,), fence, name)
                for index in range(6):
                    store.step("A" if index in positions else "B", fence)
                    store.audit()
                    for domain in store.ledger().values():
                        self.assertEqual(sum(domain["bytes"].values()),
                                         sum(domain["slots"].values()) * 128)
                self.assertTrue(store.audit()["target"])

    def test_simultaneous_admissions_and_duplicate_step_races(self):
        barrier = threading.Barrier(2)
        def admit(name, dest):
            worker = Authority(self.root)
            witness = conventional_plan(worker.snapshot_for((name,), (dest,)))
            barrier.wait(timeout=5)
            return worker.admit_scoped(witness, (name,), (dest,), self.fence, name)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(admit, "A", "Y:0"), pool.submit(admit, "B", "X:0")]
            self.assertCountEqual([future.result() for future in futures], ["A", "B"])
            outcomes = list(pool.map(lambda _: Authority(self.root).step("A", self.fence, 0)["status"], range(2)))
            self.assertCountEqual(outcomes, ["APPLIED", "ALREADY_APPLIED"])
            completed = [pool.submit(Authority(self.root).execute, name, self.fence) for name in ("A", "B")]
            for future in completed:
                future.result()
        self.assertTrue(self.store.audit()["target"])

    def test_simultaneous_conflicting_admission_has_single_winner(self):
        barrier = threading.Barrier(2)
        def attempt(name):
            worker = Authority(self.root)
            witness = conventional_plan(worker.snapshot_for((name,), ("X:0",)))
            barrier.wait(timeout=5)
            try:
                return worker.admit_scoped(witness, (name,), ("X:0",), self.fence, name)
            except Rejected:
                return "REJECTED"
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, ("A", "B")))
        self.assertEqual(outcomes.count("REJECTED"), 1)
        self.assertEqual(len(self.store.active_plans()), 1)
        self.store.execute(next(x for x in outcomes if x != "REJECTED"), self.fence)
        self.store.audit()

    def test_cancel_and_cleanup_do_not_retire_or_invalidate_other_plan(self):
        self.pair()
        for _ in range(2):
            self.store.step("A", self.fence)
            self.store.step("B", self.fence)
        before_b = self.store.snapshot_for(("B",), ("X:0",))
        self.store.cancel("A", self.fence)
        retired = next(s for s in self.store.snapshot().slots if s.key == "Y:0")
        self.assertEqual(retired.status, "RETIRED")
        self.assertEqual(self.store.ledger()["Y"]["bytes"]["RETIRED"], 128)
        self.assertEqual(before_b, self.store.snapshot_for(("B",), ("X:0",)))
        self.store.cleanup(retired.key, retired.incarnation, self.fence)
        self.assertEqual(self.store.ledger()["Y"]["bytes"]["FREE"], 128)
        self.store.execute("B", self.fence)
        self.assertEqual(self.store.plan_info("B")["status"], "DONE")
        self.assertFalse(self.store.audit()["target"])
        # Canceled allocations may subsequently be repaired by a fresh plan.
        witness = conventional_plan(self.store.snapshot_for(("A",), ("Y:0",)))
        self.store.admit_scoped(witness, ("A",), ("Y:0",), self.fence, "A-retry")
        self.store.execute("A-retry", self.fence)
        self.assertTrue(self.store.audit()["target"])

    def test_completion_releases_only_own_claims(self):
        self.pair()
        self.store.execute("A", self.fence)
        self.assertEqual([p["id"] for p in self.store.active_plans()], ["B"])
        self.assertEqual(self.store.ledger()["X"]["bytes"]["RESERVED"], 128)
        with self.assertRaises(Rejected):
            self.admit("B", "X:0")
        done = conventional_plan(self.store.snapshot_for(("A",), ("Y:0",)))
        self.store.admit_scoped(done, ("A",), ("Y:0",), self.fence, "A-empty")
        self.assertEqual(self.store.plan_info("A-empty")["status"], "DONE")
        self.store.execute("B", self.fence)
        self.assertTrue(self.store.audit()["target"])

    def test_missing_claim_and_phantom_membership_fail_before_io(self):
        self.pair()
        self.sql("DELETE FROM slot_claims WHERE slot='S:0'")
        with self.assertRaises(Rejected):
            self.store.step("A", self.fence)
        self.store.execute("B", self.fence)
        self.sql("INSERT INTO slot_claims VALUES ('S:0','A')")
        self.sql("INSERT INTO slots VALUES ('phantom','Y',0,'RETIRED','A',-1,0,'')")
        with self.assertRaises(Rejected):
            self.store.step("A", self.fence)
        self.assertEqual(self.store.plan_info("A")["cursor"], 0)

    def test_unrelated_destination_failure_does_not_block_other_scope(self):
        self.pair()
        self.store.set_offline("X", self.fence)
        with self.assertRaises(Rejected):
            self.store.step("B", self.fence)
        self.store.execute("A", self.fence)
        self.assertEqual(self.store.plan_info("B")["cursor"], 0)
        self.store.audit()

    def test_shared_source_domain_failure_blocks_both_scopes(self):
        self.pair()
        self.store.set_offline("S", self.fence)
        for name in ("A", "B"):
            with self.subTest(name=name), self.assertRaises(Rejected):
                self.store.step(name, self.fence)
            self.assertEqual(self.store.plan_info(name)["cursor"], 0)

    def test_takeover_fences_all_active_plans_without_losing_claims(self):
        self.pair()
        fence = self.store.takeover()
        for name in ("A", "B"):
            with self.subTest(name=name), self.assertRaises(Rejected):
                self.store.step(name, self.fence)
            self.store.execute(name, fence)
        self.assertTrue(self.store.audit()["target"])

    def test_claimed_retired_destination_cannot_be_cleaned_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence = make_store(Path(tmp) / "store", garbage=True)
            witness = conventional_plan(store.snapshot_for(("B",), ("X:0",)))
            store.admit_scoped(witness, ("B",), ("X:0",), fence, "B")
            retired = next(s for s in store.snapshot().slots if s.key == "X:0")
            with self.assertRaises(Rejected):
                store.cleanup(retired.key, retired.incarnation, fence)
            store.step("B", fence)  # physical acknowledgement of reclamation
            self.assertEqual(store.ledger()["X"]["bytes"]["FREE"], 0)
            self.assertEqual(store.ledger()["X"]["bytes"]["RESERVED"], 128)
            store.execute("B", fence)
            store.audit()

    def test_process_exit_in_one_plan_preserves_other_plan(self):
        for mode in ("conventional_cached", "shadow"):
            for point in ("after_stage_fsync", "before_commit", "after_commit"):
                with self.subTest(mode=mode, point=point), tempfile.TemporaryDirectory() as tmp:
                    store, fence = make_store(Path(tmp) / "store")
                    store = Authority(store.root, mode)
                    for name, dest in (("A", "Y:0"), ("B", "X:0")):
                        store.admit_scoped(conventional_plan(store.snapshot_for((name,), (dest,))),
                                           (name,), (dest,), fence, name)
                    store.step("A", fence)
                    store.step("B", fence)
                    before_b = store.snapshot_for(("B",), ("X:0",))
                    process = subprocess.run([sys.executable, "-m", "prism_c.fault_worker", str(store.root),
                                              "A", str(fence), "1", point, "--validation-mode", mode],
                                             capture_output=True, text=True, timeout=20)
                    self.assertEqual(process.returncode, 77, process.stderr)
                    reopened = Authority(store.root, mode)
                    self.assertEqual(before_b, reopened.snapshot_for(("B",), ("X:0",)))
                    self.assertEqual(reopened.plan_info("B")["cursor"], 1)
                    self.assertEqual(reopened.plan_info("A")["cursor"], 2 if point == "after_commit" else 1)
                    fence = reopened.takeover()
                    reopened.execute("B", fence)
                    reopened.execute("A", fence)
                    self.assertTrue(reopened.audit()["target"])
    def test_independent_controller_processes_finish_both_plans(self):
        self.pair()
        commands = [[sys.executable, "-m", "prism_c", "resume", "--root", str(self.root),
                     "--plan", name, "--fence", str(self.fence)] for name in ("A", "B")]
        processes = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True) for command in commands]
        try:
            for process in processes:
                stdout, stderr = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, stderr + stdout)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        self.assertTrue(self.store.audit()["target"])
        self.assertEqual(self.store.active_plans(), [])

    def test_reclaim_process_exit_preserves_other_plan_claims(self):
        for mode in ("conventional_cached", "shadow"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_store(Path(tmp) / "store", garbage=True)
                store = Authority(store.root, mode)
                for name, dest in (("A", "Y:0"), ("B", "X:0")):
                    store.admit_scoped(conventional_plan(store.snapshot_for((name,), (dest,))),
                                       (name,), (dest,), fence, name)
                process = subprocess.run([sys.executable, "-m", "prism_c.fault_worker", str(store.root),
                                          "B", str(fence), "0", "after_reclaim_fsync",
                                          "--validation-mode", mode],
                                         capture_output=True, text=True, timeout=20)
                self.assertEqual(process.returncode, 77, process.stderr)
                reopened = Authority(store.root, mode)
                self.assertEqual(reopened.ledger()["X"]["bytes"]["RETIRED"], 128)
                self.assertEqual(reopened.plan_info("B")["cursor"], 0)
                fence = reopened.takeover()
                reopened.execute("A", fence)
                reopened.execute("B", fence)
                self.assertTrue(reopened.audit()["target"])

    def test_migration_of_existing_full_store_active_plan(self):
        self.store.admit(conventional_plan(self.store.snapshot()), self.fence, "legacy")
        self.store.step("legacy", self.fence)
        # Simulate the pre-scoping schema with its already durable plan/holds.
        for table in ("plan_scopes", "stripe_claims", "slot_claims"):
            self.sql(f"DROP TABLE {table}")
        reopened = Authority(self.root)
        with self.assertRaises(Rejected):
            self.admit("B", "X:0", reopened)
        reopened.execute("legacy", self.fence)
        self.assertTrue(reopened.audit()["target"])


if __name__ == "__main__":
    unittest.main()
