"""Physical worker boundary, receipts, cancellation races and process faults."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest

from prism_c.baseline import conventional_plan
from prism_c.model import Rejected
from prism_c.storage import Authority
from prism_c import worker
from tests.test_storage import make_store


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "store"
        self.store, self.fence = make_store(self.root)
        self.store.enable_workers(self.fence)

    def tearDown(self):
        self.temp.cleanup()

    def pair(self):
        for name, destination in (("A", "Y:0"), ("B", "X:0")):
            witness = conventional_plan(self.store.snapshot_for((name,), (destination,)))
            self.store.admit_scoped(witness, (name,), (destination,), self.fence, name)

    def prepare_stage(self):
        self.pair()
        self.store.step("A", self.fence)
        return self.store.prepare_worker_step("A", self.fence)

    def test_scoped_worker_restoration_all_validation_modes(self):
        for mode in ("conventional_cached", "full", "selective", "shadow"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_store(Path(tmp) / "store", garbage=True)
                store.enable_workers(fence)
                store = Authority(store.root, mode)
                for name, destination in (("A", "Y:0"), ("B", "X:0")):
                    store.admit_scoped(conventional_plan(store.snapshot_for((name,), (destination,))),
                                       (name,), (destination,), fence, name)
                for name in ("A", "B", "B", "A", "B", "A", "B"):
                    store.step(name, fence)
                    store.audit()
                self.assertTrue(store.audit()["target"])
                self.assertEqual(store.read("A"), b"immutable object A with an odd length!")
                self.assertEqual(store.read("B"), b"immutable object B")
                receipts = [event["detail"]["receipt"] for event in store.events() if event["kind"] == "worker_ack"]
                self.assertEqual(len(receipts), 3)
                self.assertTrue(all(receipt["worker_pid"] != os.getpid() for receipt in receipts))

    def test_prepared_and_physically_written_capacity_stays_charged(self):
        intent = self.prepare_stage()
        self.assertEqual(self.store.ledger()["Y"]["bytes"]["RESERVED"], 128)
        self.assertEqual(self.store.plan_info("A")["cursor"], 1)
        receipt = self.store.execute_worker_intent(intent["token"])
        self.assertEqual(self.store.ledger()["Y"]["bytes"]["RESERVED"], 128)
        self.assertEqual(self.store.plan_info("A")["cursor"], 1)
        self.store.complete_worker_step(receipt, self.fence)
        self.assertEqual(self.store.ledger()["Y"]["bytes"]["STAGED"], 128)
        self.store.execute("A", self.fence)
        self.store.execute("B", self.fence)

    def test_worker_duplicate_execution_and_receipt_completion_are_idempotent(self):
        intent = self.prepare_stage()
        first = self.store.execute_worker_intent(intent["token"])
        second = self.store.execute_worker_intent(intent["token"])
        self.assertEqual(first, second)
        self.store.complete_worker_step(first, self.fence)
        self.assertEqual(self.store.complete_worker_step(first, self.fence)["status"], "ALREADY_APPLIED")
        self.assertEqual(self.store.plan_info("A")["cursor"], 2)

    def test_forged_or_corrupted_acknowledgement_cannot_commit(self):
        intent = self.prepare_stage()
        receipt = self.store.execute_worker_intent(intent["token"])
        for key, value in (("signature", "forged"), ("physical_digest", "bad"),
                           ("incarnation", 999), ("plan", "B"), ("token", "unknown")):
            with self.subTest(key=key), self.assertRaises(Rejected):
                self.store.complete_worker_step({**receipt, key: value}, self.fence)
        self.assertEqual(self.store.plan_info("A")["cursor"], 1)
        with (self.root / "pool-3.bin").open("r+b") as pool:
            pool.write(b"CORRUPT")
        with self.assertRaises(Rejected):
            self.store.complete_worker_step(receipt, self.fence)
        with self.assertRaises(Rejected):
            self.store.execute_worker_intent(intent["token"])

    def test_takeover_rejects_old_commands_and_delayed_receipts(self):
        intent = self.prepare_stage()
        receipt = self.store.execute_worker_intent(intent["token"])
        fence = self.store.takeover()
        with self.assertRaises(Rejected):
            self.store.execute_worker_intent(intent["token"])
        with self.assertRaises(Rejected):
            self.store.complete_worker_step(receipt, fence)
        with self.assertRaises(Rejected):
            self.store.complete_worker_step(receipt, self.fence)
        restarted = Authority(self.root)
        restarted.execute("A", fence)
        restarted.execute("B", fence)
        self.assertTrue(restarted.audit()["target"])

    def test_cancel_revokes_grant_before_reclaim_and_slot_reuse(self):
        intent = self.prepare_stage()
        receipt = self.store.execute_worker_intent(intent["token"])
        self.store.cancel("A", self.fence)
        retired = next(slot for slot in self.store.snapshot().slots if slot.key == "Y:0")
        self.store.cleanup(retired.key, retired.incarnation, self.fence)
        witness = conventional_plan(self.store.snapshot_for(("A",), ("Y:0",)))
        self.store.admit_scoped(witness, ("A",), ("Y:0",), self.fence, "A-new")
        self.store.step("A-new", self.fence)
        before = (self.root / "pool-3.bin").read_bytes()
        with self.assertRaises(Rejected):
            self.store.execute_worker_intent(intent["token"])
        with self.assertRaises(Rejected):
            self.store.complete_worker_step(receipt, self.fence)
        self.assertEqual(before, (self.root / "pool-3.bin").read_bytes())
        self.store.execute("A-new", self.fence)
        self.store.execute("B", self.fence)
        self.assertTrue(self.store.audit()["target"])

    def test_unrelated_plan_progress_does_not_invalidate_pending_receipt(self):
        intent = self.prepare_stage()
        self.store.execute("B", self.fence)
        receipt = self.store.execute_worker_intent(intent["token"])
        self.store.complete_worker_step(receipt, self.fence)
        self.store.execute("A", self.fence)
        self.assertTrue(self.store.audit()["target"])

    def test_worker_io_does_not_hold_authority_write_transaction(self):
        intent = self.prepare_stage()
        inside = threading.Event()
        release = threading.Event()
        def pause(point):
            if point == "before_worker_io":
                inside.set()
                if not release.wait(15):
                    raise RuntimeError("Worker was not released")
        with ThreadPoolExecutor(max_workers=2) as pool:
            physical = pool.submit(worker.handle, self.root, intent["command"]["worker"],
                                   {"operation": "execute", "token": intent["token"]}, pause)
            try:
                self.assertTrue(inside.wait(5))
                # This commits while the separate worker database lock is held.
                other = pool.submit(Authority(self.root).execute, "B", self.fence)
                other.result(timeout=10)
                self.assertEqual(self.store.plan_info("B")["status"], "DONE")
            finally:
                release.set()
            self.store.complete_worker_step(physical.result(), self.fence)
        self.store.execute("A", self.fence)

    def test_cancel_waits_for_inflight_worker_and_revokes_waiting_commands(self):
        intent = self.prepare_stage()
        inside = threading.Event()
        release = threading.Event()
        cancel_started = threading.Event()
        def pause(point):
            if point == "before_worker_io":
                inside.set()
                if not release.wait(15):
                    raise RuntimeError("Worker was not released")
        def cancel():
            cancel_started.set()
            Authority(self.root).cancel("A", self.fence)
        with ThreadPoolExecutor(max_workers=2) as pool:
            physical = pool.submit(worker.handle, self.root, intent["command"]["worker"],
                                   {"operation": "execute", "token": intent["token"]}, pause)
            try:
                self.assertTrue(inside.wait(5))
                canceled = pool.submit(cancel)
                self.assertTrue(cancel_started.wait(5))
                self.assertFalse(canceled.done())
            finally:
                release.set()
            physical.result(timeout=10)
            canceled.result(timeout=10)
        with self.assertRaises(Rejected):
            self.store.execute_worker_intent(intent["token"])
        self.assertEqual(self.store.plan_info("A")["status"], "CANCELED")
        self.store.execute("B", self.fence)
        self.store.audit()

    def test_reclaim_ack_does_not_release_capacity_before_manifest_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence = make_store(Path(tmp) / "store", garbage=True)
            store.enable_workers(fence)
            store.admit_scoped(conventional_plan(store.snapshot_for(("B",), ("X:0",))),
                               ("B",), ("X:0",), fence, "B")
            intent = store.prepare_worker_step("B", fence)
            receipt = store.execute_worker_intent(intent["token"])
            self.assertEqual(store.ledger()["X"]["bytes"]["RETIRED"], 128)
            store.complete_worker_step(receipt, fence)
            self.assertEqual(store.ledger()["X"]["bytes"]["FREE"], 0)
            self.assertEqual(store.ledger()["X"]["bytes"]["RESERVED"], 128)
            store.execute("B", fence)

    def test_worker_process_exit_retries_or_reconciles_durable_receipt(self):
        for point in ("before_worker_io", "after_worker_fsync", "after_worker_commit"):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_store(Path(tmp) / "store")
                store.enable_workers(fence)
                store.admit_scoped(conventional_plan(store.snapshot_for(("A",), ("Y:0",))),
                                   ("A",), ("Y:0",), fence, "A")
                store.step("A", fence)
                intent = store.prepare_worker_step("A", fence)
                command = {"operation": "execute", "token": intent["token"], "fault_point": point}
                child = subprocess.run([sys.executable, "-m", "prism_c.worker", str(store.root),
                                        str(intent["command"]["worker"])], input=json.dumps(command),
                                       capture_output=True, text=True, timeout=20)
                self.assertEqual(child.returncode, 77, child.stderr)
                reopened = Authority(store.root)
                self.assertEqual(reopened.plan_info("A")["cursor"], 1)
                self.assertEqual(reopened.ledger()["Y"]["bytes"]["RESERVED"], 128)
                # Same-epoch retry reconciles the worker journal when present.
                receipt = reopened.execute_worker_intent(intent["token"])
                reopened.complete_worker_step(receipt, fence)
                reopened.execute("A", fence)
                reopened.audit()

    def test_controller_exit_at_two_phase_boundaries_then_takeover(self):
        for point in ("after_worker_prepare", "after_worker_receipt", "before_commit", "after_commit"):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_store(Path(tmp) / "store")
                store.enable_workers(fence)
                for name, destination in (("A", "Y:0"), ("B", "X:0")):
                    store.admit_scoped(conventional_plan(store.snapshot_for((name,), (destination,))),
                                       (name,), (destination,), fence, name)
                store.step("A", fence)
                child = subprocess.run([sys.executable, "-m", "prism_c.fault_worker", str(store.root),
                                        "A", str(fence), "1", point], capture_output=True, timeout=20)
                self.assertEqual(child.returncode, 77, child.stderr.decode())
                reopened = Authority(store.root)
                self.assertEqual(reopened.plan_info("A")["cursor"], 2 if point == "after_commit" else 1)
                fence = reopened.takeover()
                reopened.execute("B", fence)
                reopened.execute("A", fence)
                self.assertTrue(reopened.audit()["target"])

    def test_worker_fence_is_durable_and_cannot_regress(self):
        fence = self.store.takeover()
        with self.assertRaises(Rejected):
            worker.rpc(self.root, 0, "fence", fence=self.fence)
        self.assertEqual(worker.rpc(self.root, 0, "fence", fence=fence)["fence"], fence)

    def test_duplicate_stage_controllers_only_commit_once(self):
        self.prepare_stage()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: Authority(self.root).step("A", self.fence, 1), range(2)))
        self.assertCountEqual([result["status"] for result in outcomes], ["APPLIED", "ALREADY_APPLIED"])
        self.assertEqual(self.store.plan_info("A")["cursor"], 2)
        self.assertEqual(len([event for event in self.store.events() if event["kind"] == "worker_ack"]), 1)

    def test_takeover_waits_for_inflight_worker_before_publishing_fence(self):
        intent = self.prepare_stage()
        inside = threading.Event()
        release = threading.Event()
        takeover_started = threading.Event()
        def pause(point):
            if point == "before_worker_io":
                inside.set()
                if not release.wait(15):
                    raise RuntimeError("Worker was not released")
        def takeover():
            takeover_started.set()
            return Authority(self.root).takeover()
        with ThreadPoolExecutor(max_workers=2) as pool:
            physical = pool.submit(worker.handle, self.root, intent["command"]["worker"],
                                   {"operation": "execute", "token": intent["token"]}, pause)
            try:
                self.assertTrue(inside.wait(5))
                successor = pool.submit(takeover)
                self.assertTrue(takeover_started.wait(5))
                self.assertFalse(successor.done())
            finally:
                release.set()
            receipt = physical.result(timeout=10)
            fence = successor.result(timeout=10)
        with self.assertRaises(Rejected):
            self.store.complete_worker_step(receipt, fence)
        self.store.execute("A", fence)
        self.store.execute("B", fence)
        self.assertTrue(self.store.audit()["target"])


if __name__ == "__main__":
    unittest.main()
