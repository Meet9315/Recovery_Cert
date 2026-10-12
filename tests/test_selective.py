from dataclasses import replace
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from prism_c.baseline import conventional_plan
from prism_c.benchmark import run_mode, workload
from prism_c.checker import replay
from prism_c.model import Action, Rejected, Slot, Witness, fixture
from prism_c.selective import ContinuationCache, partition
from prism_c.storage import Authority
from tests.test_storage import make_store


class SelectiveModelTests(unittest.TestCase):
    def prepare(self):
        state = fixture(reclamation=True)
        witness = conventional_plan(state)
        cache = ContinuationCache.build(state, witness)
        action = witness.actions[0]
        cache.validate(state, witness, 0)
        after = replay(state, (action,), False)
        cache.advance(state, after, action)
        return after, witness, cache

    def test_warm_cache_reuses_all_components(self):
        state, witness, cache = self.prepare()
        self.assertEqual(cache.validate(state, witness, 1), replay(state, witness.actions[1:]))
        self.assertEqual(cache.last_stats["replayed_actions"], 0)
        self.assertGreaterEqual(cache.last_stats["reused_components"], 2)

    def test_each_step_matches_complete_suffix(self):
        state = fixture(reclamation=True)
        witness = conventional_plan(state)
        cache = ContinuationCache.build(state, witness)
        for cursor, action in enumerate(witness.actions):
            self.assertEqual(cache.validate(state, witness, cursor), replay(state, witness.actions[cursor:]))
            after = replay(state, (action,), False)
            cache.advance(state, after, action)
            state = after
        self.assertTrue(state.target())

    def test_related_mutations_match_reference_rejection(self):
        state, witness, original = self.prepare()
        mutations = []
        for index, slot in enumerate(state.slots):
            for changed in (replace(slot, incarnation=slot.incarnation + 1),
                            replace(slot, status="RETIRED")):
                mutations.append(replace(state, slots=state.slots[:index] + (changed,) + state.slots[index + 1:]))
        mutations += [replace(state, offline=(domain,)) for domain in ("S", "T", "X", "Y")]
        mutations += [replace(state, stripes=(replace(state.stripes[0], eligible=("S", "T")), state.stripes[1]))]
        for changed in mutations:
            with self.subTest(mutation=changed):
                cache = ContinuationCache.from_json(original.to_json("authority"), witness, 1, "authority")
                def full():
                    final = replay(changed, witness.actions[1:])
                    if final.fingerprint() != witness.terminal:
                        raise Rejected("Changed terminal")
                    return final
                with self.assertRaises(Rejected):
                    full()
                with self.assertRaises(Rejected):
                    cache.validate(changed, witness, 1)

    def test_phantom_reservation_membership_rebuild(self):
        state, witness, cache = self.prepare()
        phantom = Slot("phantom", "Y", "RESERVED", "A", 2, 1)
        changed = replace(state, slots=state.slots + (phantom,))
        with self.assertRaises(Rejected):
            replay(changed, witness.actions[1:])
        with self.assertRaises(Rejected):
            cache.validate(changed, witness, 1)

    def test_changed_stripe_rechecked_while_other_stripe_reused(self):
        state, witness, cache = self.prepare()
        changed = replace(state, stripes=(state.stripes[0],
                           replace(state.stripes[1], eligible=state.stripes[1].eligible + ("EXTRA",))))
        # Replay is safe but the exact terminal commitment must still reject
        # policy changes. Only the changed policy component is replayed.
        with self.assertRaises(Rejected):
            cache.validate(changed, witness, 1)
        self.assertEqual(cache.last_stats["replayed_components"], 1)
        self.assertEqual(cache.last_stats["reused_components"], 1)

    def test_duplicate_slot_and_unknown_stripe_fail_closed(self):
        state, witness, cache = self.prepare()
        for changed in (replace(state, slots=state.slots + (state.slots[0],)),
                        replace(state, slots=state.slots + (Slot("bad", "X", "LIVE", "UNKNOWN", 2, 1),))):
            with self.subTest(changed=changed), self.assertRaises(Rejected):
                cache.validate(changed, witness, 1)

    def test_untouched_slot_is_covered(self):
        state, witness, cache = self.prepare()
        extra = Slot("unused", "Z")
        changed = replace(state, slots=state.slots + (extra,))
        with self.assertRaises(Rejected):
            cache.validate(changed, witness, 1)

    def test_coverage_cannot_be_omitted_from_cache(self):
        state, witness, cache = self.prepare()
        value = json.loads(cache.to_json("authority"))
        value["components"] = value["components"][:1]
        incomplete = ContinuationCache.from_json(json.dumps(value), witness, 1, "authority")
        self.assertEqual(incomplete.validate(state, witness, 1), replay(state, witness.actions[1:]))
        self.assertEqual(incomplete.last_stats["coverage_rebuilds"], 1)

    def test_cache_bound_to_witness_cursor_incarnation_version(self):
        _, witness, cache = self.prepare()
        original = json.loads(cache.to_json("authority"))
        for field, wrong in (("version", 99), ("incarnation", "old"),
                             ("cursor", 999), ("witness_digest", "forged")):
            with self.subTest(field=field), self.assertRaises(Rejected):
                ContinuationCache.from_json(json.dumps({**original, field: wrong}), witness, 1, "authority")

    def test_shared_action_slot_merges_dependency_groups(self):
        state = fixture()
        actions = (Action("reserve", "X0", "A", 2, 0), Action("reserve", "X0", "B", 2, 1))
        components = partition(state, actions)
        self.assertTrue(any({s.name for s in part.stripes} == {"A", "B"} for part, _ in components))

    def test_out_of_order_cache_advancement_rejected(self):
        state, witness, cache = self.prepare()
        with self.assertRaises(Rejected):
            cache.advance(state, state, witness.actions[-1])

    def test_benchmark_modes_preserve_identical_target(self):
        initial, witness = workload(2)
        for mode in ("full", "selective", "conventional_cached"):
            with self.subTest(mode=mode):
                result = run_mode(initial, witness, mode, annotations=True)
                self.assertEqual(result["steps"], len(witness.actions))
                self.assertEqual(result["annotations"], len(witness.actions))
                self.assertGreaterEqual(result["total_cpu_ns"], 0)


class SelectiveStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.store, self.fence = make_store(Path(self.temporary.name) / "store", garbage=True)
        self.store = Authority(self.store.root, validation_mode="selective")
        self.witness = conventional_plan(self.store.snapshot())
        self.identifier = self.store.admit(self.witness, self.fence)

    def tearDown(self):
        self.temporary.cleanup()

    def test_unrelated_annotation_reuses_certificates(self):
        self.store.step(self.identifier, self.fence)
        self.store.annotate("operator", "unrelated diagnostic note", self.fence)
        self.store.step(self.identifier, self.fence)
        stats = self.store.events()[-1]["detail"]["validation"]
        self.assertFalse(stats["cache_rebuilt"])
        self.assertEqual(stats["replayed_actions"], 0)
        self.assertGreater(stats["reused_components"], 0)

    def test_cache_persists_across_new_connection_and_takeover(self):
        self.store.step(self.identifier, self.fence)
        reopened = Authority(self.store.root, validation_mode="selective")
        new_fence = reopened.takeover()
        reopened.step(self.identifier, new_fence)
        stats = reopened.events()[-1]["detail"]["validation"]
        self.assertFalse(stats["cache_rebuilt"])
        reopened.execute(self.identifier, new_fence)
        self.assertTrue(reopened.audit()["target"])

    def test_missing_or_bad_cache_rebuilds_from_reference(self):
        for payload in (None, "broken-json", '{"version":99}'):
            with self.subTest(payload=payload):
                with closing(sqlite3.connect(self.store.db_path)) as db, db:
                    if payload is None:
                        db.execute("DELETE FROM validation_cache WHERE plan=?", (self.identifier,))
                    else:
                        db.execute("UPDATE validation_cache SET value=? WHERE plan=?", (payload, self.identifier))
                self.store.step(self.identifier, self.fence)
                stats = self.store.events()[-1]["detail"]["validation"]
                self.assertTrue(stats["cache_rebuilt"])

    def test_shadow_mode_matches_reference_in_durable_execution(self):
        shadow = Authority(self.store.root, validation_mode="shadow")
        shadow.execute(self.identifier, self.fence)
        self.assertTrue(shadow.audit()["target"])
        self.assertTrue(all(e["detail"]["validation"]["mode"] == "shadow"
                            for e in shadow.events() if e["kind"] == "step"))

    def test_full_mode_remains_available(self):
        reference = Authority(self.store.root, validation_mode="full")
        reference.execute(self.identifier, self.fence)
        self.assertTrue(reference.audit()["target"])

    def test_relevant_failure_blocks_cached_plan(self):
        self.store.step(self.identifier, self.fence)
        self.store.set_offline("X", self.fence)
        with self.assertRaises(Rejected):
            self.store.step(self.identifier, self.fence)
        self.assertEqual(self.store.plan_info(self.identifier)["cursor"], 1)

    def test_current_source_bytes_still_checked_with_warm_cache(self):
        self.store.step(self.identifier, self.fence)
        with (self.store.root / "pool-0.bin").open("r+b") as handle:
            handle.write(b"source corruption after cached validation")
        with self.assertRaises(Rejected):
            self.store.step(self.identifier, self.fence)
        self.assertEqual(self.store.plan_info(self.identifier)["cursor"], 1)

    def test_modes_can_switch_with_checked_cache_rebuild(self):
        for mode in ("conventional_cached", "full", "selective", "conventional_cached"):
            authority = Authority(self.store.root, validation_mode=mode)
            authority.step(self.identifier, self.fence)
            authority.audit()
        self.store.execute(self.identifier, self.fence)
        self.assertTrue(self.store.audit()["target"])

    def test_conventional_cache_rejects_relevant_change(self):
        conventional = Authority(self.store.root)
        conventional.step(self.identifier, self.fence)
        conventional.set_offline("X", self.fence)
        with self.assertRaises(Rejected):
            conventional.step(self.identifier, self.fence)

    def test_selective_cache_and_cursor_commit_atomically_on_process_exit(self):
        for point in ("after_stage_fsync", "before_commit", "after_commit"):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as temporary:
                initial, fence = make_store(Path(temporary) / "store")
                store = Authority(initial.root, validation_mode="selective")
                identifier = store.admit(conventional_plan(store.snapshot()), fence)
                store.step(identifier, fence)
                child = subprocess.run([sys.executable, "-m", "prism_c.fault_worker", str(store.root),
                    identifier, str(fence), "1", point, "--validation-mode", "selective"], capture_output=True)
                self.assertEqual(child.returncode, 77, child.stderr.decode())
                restarted = Authority(store.root, validation_mode="shadow")
                self.assertEqual(restarted.plan_info(identifier)["cursor"], 2 if point == "after_commit" else 1)
                restarted.execute(identifier, restarted.takeover())
                self.assertTrue(restarted.audit()["target"])


if __name__ == "__main__":
    unittest.main()
