import concurrent.futures
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path

from prism_c.baseline import conventional_plan
from prism_c.checker import replay
from prism_c.model import Action, Rejected, Witness
from prism_c.storage import Authority


def make_store(root, garbage=False):
    authority = Authority.create(root, {"S": 2, "T": 2, "X": 1, "Y": 1}, slot_size=128)
    fence = authority.takeover()
    authority.bootstrap("A", b"immutable object A with an odd length!", {0: "S", 1: "T"},
                        ("S", "T", "X", "Y"), fence)
    authority.bootstrap("B", b"immutable object B", {0: "S", 1: "T"}, ("S", "T", "X"), fence)
    if garbage:
        authority.seed_retired("X", fence)
    return authority, fence


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "store"
        self.store, self.fence = make_store(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def admit(self):
        return self.store.admit(conventional_plan(self.store.snapshot()), self.fence)

    def test_repair_real_bytes_and_read_after_restart(self):
        identifier = self.admit()
        self.store.execute(identifier, self.fence)
        restarted = Authority(self.root)
        self.assertTrue(restarted.audit()["target"])
        self.assertEqual(restarted.read("A"), b"immutable object A with an odd length!")
        self.assertEqual(restarted.read("B"), b"immutable object B")
        self.assertEqual(restarted.plan_info(identifier)["status"], "DONE")

    def test_holds_charge_available_capacity_before_steps(self):
        before = self.store.ledger()
        self.admit()
        after = self.store.ledger()
        self.assertEqual(before["X"]["bytes"]["FREE"], 128)
        self.assertEqual(after["X"]["bytes"]["FREE"], 0)
        self.assertEqual(after["X"]["bytes"]["RESERVED"], 128)
        self.assertEqual(sum(after["X"]["bytes"].values()), 128)

    def test_mutual_exclusion_blocks_competing_admission(self):
        witness = conventional_plan(self.store.snapshot())
        self.store.admit(witness, self.fence)
        with self.assertRaises(Rejected):
            self.store.admit(witness, self.fence)

    def test_takeover_fences_old_writes(self):
        identifier = self.admit()
        newer = self.store.takeover()
        before = self.store.snapshot()
        with self.assertRaises(Rejected):
            self.store.step(identifier, self.fence)
        self.assertEqual(before, self.store.snapshot())
        self.store.execute(identifier, newer)

    def test_duplicate_and_out_of_order_steps(self):
        identifier = self.admit()
        with self.assertRaises(Rejected):
            self.store.step(identifier, self.fence, 1)
        self.store.step(identifier, self.fence, 0)
        self.assertEqual(self.store.step(identifier, self.fence, 0)["status"], "ALREADY_APPLIED")
        self.store.execute(identifier, self.fence)

    def test_corrupt_staged_fragment_cannot_promote(self):
        identifier = self.admit()
        self.store.step(identifier, self.fence)
        self.store.step(identifier, self.fence)
        # Administrative byte mutation deliberately simulates corruption.
        with (self.root / "pool-3.bin").open("r+b") as handle:
            handle.write(b"WRONG BYTES")
        with self.assertRaises(Rejected):
            self.store.step(identifier, self.fence)
        self.assertEqual(self.store.plan_info(identifier)["cursor"], 2)

    def test_corrupt_live_source_prevents_admission(self):
        witness = conventional_plan(self.store.snapshot())
        with (self.root / "pool-0.bin").open("r+b") as handle:
            handle.write(b"WRONG SOURCE")
        with self.assertRaises(Rejected):
            self.store.admit(witness, self.fence)

    def test_cancel_charges_partial_staging_until_cleanup(self):
        identifier = self.admit()
        self.store.step(identifier, self.fence)
        self.store.step(identifier, self.fence)
        self.store.cancel(identifier, self.fence)
        retired = next(s for s in self.store.snapshot().slots if s.status == "RETIRED")
        self.assertEqual(self.store.ledger()[retired.domain]["bytes"]["RETIRED"], 128)
        with self.assertRaises(Rejected):
            self.store.step(identifier, self.fence)
        self.store.cleanup(retired.key, retired.incarnation, self.fence)
        self.assertEqual(self.store.ledger()[retired.domain]["bytes"]["FREE"], 128)
        self.store.audit()

    def test_stale_cleanup_cannot_erase_reallocated_slot(self):
        identifier = self.admit()
        self.store.step(identifier, self.fence)
        self.store.cancel(identifier, self.fence)
        retired = next(s for s in self.store.snapshot().slots if s.status == "RETIRED")
        self.store.cleanup(retired.key, retired.incarnation, self.fence)
        next_id = self.admit()
        self.store.step(next_id, self.fence)
        with self.assertRaises(Rejected):
            self.store.cleanup(retired.key, retired.incarnation, self.fence)
        self.store.execute(next_id, self.fence)
        self.store.audit()

    def test_domain_failure_invalidates_remaining_continuation(self):
        identifier = self.admit()
        self.store.set_offline("X", self.fence)
        with self.assertRaises(Rejected):
            self.store.step(identifier, self.fence)
        self.assertEqual(self.store.plan_info(identifier)["cursor"], 0)
        self.assertFalse(self.store.ledger()["X"]["online"])

    def test_concurrent_connections_cannot_apply_same_step_twice(self):
        identifier = self.admit()
        def attempt():
            return Authority(self.root).step(identifier, self.fence, 0)["status"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: attempt(), range(2)))
        self.assertCountEqual(outcomes, ["APPLIED", "ALREADY_APPLIED"])
        self.assertEqual(self.store.plan_info(identifier)["cursor"], 1)

    def test_takeover_serializes_with_stage_io(self):
        identifier = self.admit()
        self.store.step(identifier, self.fence)
        inside_transaction = threading.Event()
        release = threading.Event()
        takeover_attempted = threading.Event()

        def pause(point):
            if point == "after_validation":
                inside_transaction.set()
                if not release.wait(5):
                    raise RuntimeError("Test did not release stage transaction")

        def takeover():
            takeover_attempted.set()
            return Authority(self.root).takeover()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            staged = executor.submit(Authority(self.root).step, identifier, self.fence, None, pause)
            self.assertTrue(inside_transaction.wait(5))
            newer = executor.submit(takeover)
            try:
                self.assertTrue(takeover_attempted.wait(5))
                self.assertFalse(newer.done())
            finally:
                release.set()
            self.assertEqual(staged.result(timeout=5)["cursor"], 2)
            next_fence = newer.result(timeout=5)
        with self.assertRaises(Rejected):
            self.store.step(identifier, self.fence)
        self.store.execute(identifier, next_fence)
        self.assertTrue(self.store.audit()["target"])

    def test_stale_snapshot_admission_rejected(self):
        witness = conventional_plan(self.store.snapshot())
        self.store.seed_retired("X", self.fence)
        with self.assertRaises(Rejected):
            self.store.admit(witness, self.fence)

    def test_bootstrap_is_sealed_after_first_plan(self):
        self.admit()
        with self.assertRaises(Rejected):
            self.store.bootstrap("C", b"x", {0: "X", 1: "Y"}, ("X", "Y"), self.fence)

    def test_already_protected_empty_plan_releases_group(self):
        identifier = self.admit()
        self.store.execute(identifier, self.fence)
        empty = conventional_plan(self.store.snapshot())
        another = self.store.admit(empty, self.fence)
        self.assertEqual(self.store.plan_info(another)["status"], "DONE")
        self.assertEqual(self.store.step(another, self.fence)["status"], "DONE")
        self.store.admit(empty, self.fence)


class ProcessCrashTests(unittest.TestCase):
    def test_actual_process_exit_at_every_step_boundary(self):
        cases = [(0, "after_validation"), (0, "before_commit"), (0, "after_commit"),
                 (1, "after_validation"), (1, "after_stage_fsync"), (1, "before_commit"),
                 (1, "after_commit"), (2, "after_validation"), (2, "before_commit"),
                 (2, "after_commit")]
        for index, point in cases:
            with self.subTest(index=index, point=point), tempfile.TemporaryDirectory() as temporary:
                store, fence = make_store(Path(temporary) / "store")
                identifier = store.admit(conventional_plan(store.snapshot()), fence)
                for _ in range(index):
                    store.step(identifier, fence)
                child = subprocess.run([sys.executable, "-m", "prism_c.fault_worker", str(store.root),
                                        identifier, str(fence), str(index), point], capture_output=True)
                self.assertEqual(child.returncode, 77, child.stderr.decode())
                resumed = Authority(store.root)
                self.assertEqual(resumed.plan_info(identifier)["cursor"],
                                 index + (point == "after_commit"))
                resumed.audit()
                successor = resumed.takeover()
                resumed.execute(identifier, successor)
                self.assertTrue(resumed.audit()["target"])

    def test_reclaim_crash_retains_charge_until_committed_ack(self):
        for point in ("after_validation", "after_reclaim_fsync", "before_commit", "after_commit"):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as temporary:
                store, fence = make_store(Path(temporary) / "store", garbage=True)
                witness = conventional_plan(store.snapshot())
                self.assertEqual(witness.actions[0].kind, "reclaim")
                identifier = store.admit(witness, fence)
                child = subprocess.run([sys.executable, "-m", "prism_c.fault_worker", str(store.root),
                                        identifier, str(fence), "0", point], capture_output=True)
                self.assertEqual(child.returncode, 77, child.stderr.decode())
                resumed = Authority(store.root)
                expected = "FREE" if point == "after_commit" else "RETIRED"
                self.assertEqual(next(s for s in resumed.snapshot().slots if s.domain == "X").status, expected)
                # A released slot is still held for the continuation, not available to competitors.
                self.assertEqual(resumed.ledger()["X"]["bytes"]["FREE"], 0)
                resumed.execute(identifier, resumed.takeover())
                self.assertTrue(resumed.audit()["target"])

    def test_checked_live_retirement_restart_then_repair(self):
        with tempfile.TemporaryDirectory() as temporary:
            store, fence = make_store(Path(temporary) / "store")
            first = store.admit(conventional_plan(store.snapshot()), fence)
            store.execute(first, fence)
            initial = store.snapshot()
            slot = next(s for s in initial.slots if s.stripe == "A" and s.row == 2)
            actions = (Action("retire", slot.key, "A", 2, slot.incarnation),
                       Action("reclaim", slot.key, "A", 2, slot.incarnation),
                       Action("reserve", slot.key, "A", 2, slot.incarnation),
                       Action("stage", slot.key, "A", 2, slot.incarnation + 1),
                       Action("promote", slot.key, "A", 2, slot.incarnation + 1))
            final = replay(initial, actions)
            identifier = store.admit(Witness(initial.fingerprint(), actions, final.fingerprint()), fence)
            child = subprocess.run([sys.executable, "-m", "prism_c.fault_worker", str(store.root),
                                    identifier, str(fence), "0", "after_commit"], capture_output=True)
            self.assertEqual(child.returncode, 77, child.stderr.decode())
            store.audit()
            store.execute(identifier, store.takeover())
            self.assertTrue(store.audit()["target"])


if __name__ == "__main__":
    unittest.main()
