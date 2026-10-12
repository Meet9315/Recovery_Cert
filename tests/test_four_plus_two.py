"""Coding, policy, durable storage, mixed profiles and upgrade evidence."""

from contextlib import closing
from dataclasses import replace
import itertools
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from prism_c.baseline import conventional_plan
from prism_c.checker import check, replay
from prism_c.coding import encode, recover
from prism_c.coding_oracle import oracle_encode, oracle_recover
from prism_c.model import Action, Rejected, SearchStatus, State, Stripe, Witness, plan, transition
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.selective import ContinuationCache, WholeSuffixCache, state_from_dict
from prism_c.storage import Authority
from tests.test_storage import make_store

CONTENT = bytes(range(256)) + b"odd 4+2 object with trailing zero\x00"


def make_42_store(root, rows=(0, 1, 2, 3), workers=False, garbage=False, mixed=False):
    capacities = {f"D{i}": 2 if mixed else 1 for i in range(4)}
    capacities.update(X=1, Y=1)
    if mixed:
        capacities["Z"] = 1
    store = Authority.create(root, capacities, 128)
    fence = store.takeover()
    store.bootstrap("A", CONTENT, {row: f"D{i}" for i, row in enumerate(rows)},
                    ("D0", "D1", "D2", "D3", "X", "Y"), fence, FOUR_PLUS_TWO)
    if mixed:
        store.bootstrap("B", b"legacy 2+1 stripe", {0: "D0", 1: "D1"}, ("D0", "D1", "Z"), fence)
    if garbage:
        store.seed_retired("X", fence)
    if workers:
        store.enable_workers(fence)
    return store, fence


class FourPlusTwoTests(unittest.TestCase):
    def test_all_four_row_subsets_match_independent_codec_oracle(self):
        for data in (b"", b"x", b"odd object\x00", bytes(range(256)), CONTENT):
            encoded = encode(data, FOUR_PLUS_TWO)
            self.assertEqual(encoded, oracle_encode(data))
            for selected in itertools.combinations(range(6), 4):
                with self.subTest(length=len(data), rows=selected):
                    rows = {row: encoded[row] for row in selected}
                    content, rebuilt = recover(rows, len(data), FOUR_PLUS_TWO)
                    self.assertEqual(content, data)
                    self.assertEqual(rebuilt, encoded)
                    self.assertEqual(oracle_recover(rows, len(data)), data)

    def test_codec_rejects_invalid_rows_lengths_padding_and_extra_inconsistency(self):
        encoded = encode(b"test", FOUR_PLUS_TWO)
        valid = {row: encoded[row] for row in range(4)}
        cases = [(dict(list(valid.items())[:3]), 4), ({**valid, 6: b"x"}, 4),
                 ({**{row: value for row, value in valid.items() if row != 1}, True: b"x"}, 4), ({**valid, 0: b""}, 4),
                 ({**valid, 0: b"longer"}, 4), (valid, -1), (valid, 5),
                 (valid, True), (valid, 3), ({**valid, 4: bytes([encoded[4][0] ^ 1])}, 4)]
        for rows, length in cases:
            with self.subTest(rows=rows, length=length), self.assertRaises(Rejected):
                recover(rows, length, FOUR_PLUS_TWO)
        with self.assertRaises(Rejected):
            encode(b"data", "arbitrary-profile")

    def test_restoration_from_each_of_fifteen_initial_row_subsets(self):
        for rows in itertools.combinations(range(6), 4):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_42_store(Path(tmp) / "store", rows)
                self.assertEqual(store.read("A"), CONTENT)
                witness = conventional_plan(store.snapshot())
                self.assertEqual(len(witness.actions), 6)
                store.admit(witness, fence, "A")
                store.execute("A", fence)
                reopened = Authority(store.root)
                self.assertTrue(reopened.audit()["target"])
                self.assertEqual(reopened.read("A"), CONTENT)
                self.assertEqual({slot.row for slot in reopened.snapshot().slots if slot.status == "LIVE"}, set(range(6)))

    def test_local_and_worker_restoration_in_all_validation_modes(self):
        for mode, workers in itertools.product(("conventional_cached", "full", "selective", "shadow"), (False, True)):
            with self.subTest(mode=mode, workers=workers), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_42_store(Path(tmp) / "store", (0, 2, 4, 5), workers, garbage=True)
                store = Authority(store.root, mode)
                witness = conventional_plan(store.snapshot_for(("A",), ("X:0", "Y:0")))
                store.admit_scoped(witness, ("A",), ("X:0", "Y:0"), fence, "A")
                store.execute("A", fence)
                self.assertTrue(store.audit()["target"])
                self.assertEqual(store.read("A"), CONTENT)
                receipts = [event for event in store.events() if event["kind"] == "worker_ack"]
                self.assertEqual(len(receipts), 3 if workers else 0)

    def test_profile_floor_target_and_invalid_reservation_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _ = make_42_store(Path(tmp) / "store")
            state = store.snapshot()
            self.assertFalse(state.target())
            slot = next(slot for slot in state.slots if slot.status == "LIVE")
            retirement = Action("retire", slot.key, "A", slot.row, slot.incarnation)
            for validator in (transition, lambda s, a: replay(s, (a,), False)):
                with self.assertRaises(Rejected):
                    validator(state, retirement)
                for row in (-1, 6, True):
                    with self.subTest(row=row), self.assertRaises(Rejected):
                        validator(state, Action("reserve", "X:0", "A", row, 0))
            self.assertEqual(plan(state, max_states=1).status, SearchStatus.UNKNOWN)
            result = plan(state)
            self.assertEqual(result.status, SearchStatus.FOUND)
            self.assertTrue(check(state, result.witness).target())

    def test_any_two_domain_erasures_recover_but_three_fail(self):
        domains = ("D0", "D1", "D2", "D3", "X", "Y")
        for offline in itertools.combinations(domains, 2):
            with self.subTest(offline=offline), tempfile.TemporaryDirectory() as tmp:
                store = Authority.create(Path(tmp) / "store", {domain: 1 for domain in domains}, 128)
                fence = store.takeover()
                store.bootstrap("A", CONTENT, dict(enumerate(domains)), domains, fence, FOUR_PLUS_TWO)
                for domain in offline:
                    store.set_offline(domain, fence)
                self.assertEqual(store.read("A"), CONTENT)
                self.assertFalse(store.audit()["target"])
                store.set_offline(next(domain for domain in domains if domain not in offline), fence)
                with self.assertRaises(Rejected):
                    store.read("A")

    def test_mixed_profile_scopes_complete_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence = make_42_store(Path(tmp) / "store", (0, 2, 4, 5), workers=True, mixed=True)
            for name, slots in (("A", ("X:0", "Y:0")), ("B", ("Z:0",))):
                store.admit_scoped(conventional_plan(store.snapshot_for((name,), slots)), (name,), slots, fence, name)
            store.execute("B", fence)
            self.assertFalse(store.audit()["target"])
            store.execute("A", fence)
            self.assertTrue(store.audit()["target"])
            self.assertEqual(store.read("A"), CONTENT)
            self.assertEqual(store.read("B"), b"legacy 2+1 stripe")
            self.assertEqual({stripe.profile for stripe in store.snapshot().stripes}, {DEFAULT_PROFILE, FOUR_PLUS_TWO})

    def test_profile_change_invalidates_witness_and_both_caches(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _ = make_42_store(Path(tmp) / "store")
            state = store.snapshot()
            witness = conventional_plan(state)
            changed = replace(state, stripes=(replace(state.stripes[0], profile=DEFAULT_PROFILE),))
            self.assertNotEqual(changed.fingerprint(), state.fingerprint())
            with self.assertRaises(Rejected):
                check(changed, witness)
            for kind in (ContinuationCache, WholeSuffixCache):
                cache = kind.build(state, witness)
                restored = kind.from_json(cache.to_json("authority"), witness, 0, "authority")
                self.assertEqual(restored.validate(state, witness, 0), check(state, witness))
                with self.assertRaises(Rejected):
                    restored.validate(changed, witness, 0)

    def test_historical_witness_fingerprint_and_active_store_migration(self):
        root = Path(__file__).resolve().parent.parent
        historical = json.loads((root / "evidence/results/demo-milestone-02.json").read_text())
        state = state_from_dict(historical["initial"])
        witness = Witness.from_dict(historical["witness"])
        self.assertEqual(state.fingerprint(), witness.initial)
        self.assertTrue(check(state, witness).target())
        with tempfile.TemporaryDirectory() as tmp:
            store, fence = make_store(Path(tmp) / "store")
            store.enable_workers(fence)
            identifier = store.admit(conventional_plan(store.snapshot()), fence, "legacy")
            store.step(identifier, fence)
            pending = store.prepare_worker_step(identifier, fence)
            with closing(sqlite3.connect(store.db_path)) as db, db:
                db.execute("ALTER TABLE stripes DROP COLUMN profile")
                raw = db.execute("SELECT value FROM validation_cache WHERE plan=?", (identifier,)).fetchone()[0]
                def strip_profile(value):
                    if isinstance(value, dict):
                        return {key: strip_profile(item) for key, item in value.items() if key != "profile"}
                    if isinstance(value, list):
                        return [strip_profile(item) for item in value]
                    return value
                db.execute("UPDATE validation_cache SET value=? WHERE plan=?",
                           (json.dumps(strip_profile(json.loads(raw))), identifier))
            reopened = Authority(store.root)
            receipt = reopened.execute_worker_intent(pending["token"])
            reopened.complete_worker_step(receipt, fence)
            event = next(event for event in reversed(reopened.events()) if event["kind"] == "step")
            self.assertFalse(event["detail"]["validation"]["cache_rebuilt"])
            reopened.execute(identifier, fence)
            self.assertTrue(reopened.audit()["target"])

    def test_four_plus_two_worker_and_controller_process_exit_recovery(self):
        cases = (("controller", "after_worker_receipt"), ("controller", "before_commit"),
                 ("worker", "after_worker_fsync"), ("worker", "after_worker_commit"))
        for who, point in cases:
            with self.subTest(who=who, point=point), tempfile.TemporaryDirectory() as tmp:
                store, fence = make_42_store(Path(tmp) / "store", (0, 2, 4, 5), workers=True)
                store.admit_scoped(conventional_plan(store.snapshot_for(("A",), ("X:0", "Y:0"))),
                                   ("A",), ("X:0", "Y:0"), fence, "A")
                store.step("A", fence)
                if who == "controller":
                    command = [sys.executable, "-m", "prism_c.fault_worker", str(store.root), "A", str(fence), "1", point]
                    child = subprocess.run(command, capture_output=True, text=True, timeout=20)
                else:
                    intent = store.prepare_worker_step("A", fence)
                    command = [sys.executable, "-m", "prism_c.worker", str(store.root), str(intent["command"]["worker"])]
                    child = subprocess.run(command, input=json.dumps({"operation": "execute", "token": intent["token"],
                                           "fault_point": point}), capture_output=True, text=True, timeout=20)
                self.assertEqual(child.returncode, 77, child.stderr)
                reopened = Authority(store.root)
                self.assertEqual(reopened.plan_info("A")["cursor"], 1)
                self.assertEqual(reopened.ledger()["X"]["bytes"]["RESERVED"], 128)
                reopened.execute("A", reopened.takeover())
                self.assertTrue(reopened.audit()["target"])
                self.assertEqual(reopened.read("A"), CONTENT)

    def test_corrupted_four_plus_two_source_is_never_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence = make_42_store(Path(tmp) / "store", (0, 2, 4, 5))
            witness = conventional_plan(store.snapshot())
            with (store.root / "pool-0.bin").open("r+b") as handle:
                handle.write(b"corrupt source")
            with self.assertRaises(Rejected):
                store.read("A")
            with self.assertRaises(Rejected):
                store.admit(witness, fence)
            self.assertEqual(store.active_plans(), [])


if __name__ == "__main__":
    unittest.main()
