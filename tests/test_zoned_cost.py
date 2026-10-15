from pathlib import Path
import tempfile
import unittest

from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.zoned_cost import (ARMS, compose_plan, cost_window, foreground_summary,
                                paired_summary, workload)
from prism_c.zoned_model import goal, replay


class ZonedCostTests(unittest.TestCase):
    def test_disjoint_plans_share_tokens_preserve_foreground_and_reach_full_target(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for extra in (False, True):
                with self.subTest(profile=profile, extra=extra):
                    initial, parts, contents = workload(profile, 64, 2, extra)
                    self.assertEqual(len(contents), 3)
                    self.assertEqual(len(set(contents.values())), 3)
                    for arm in ARMS:
                        witness, scores = compose_plan(initial, parts, arm)
                        terminal = replay(initial, witness)
                        self.assertTrue(goal(terminal))
                        self.assertFalse(any(z.uses_open() for z in terminal.zones))
                        self.assertLessEqual(sum(z.uses_active() for z in terminal.zones), 2)
                        expected_stages = 4 if arm == "separated" and not extra else 2
                        self.assertEqual(sum(score[0] for score in scores), expected_stages)
                        self.assertFalse(any(a.zone.startswith("foreground/") for a in witness.actions))

    def test_real_window_retains_every_offered_read_and_full_controller_phases(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = cost_window(Path(tmp) / "store", DEFAULT_PROFILE, 64, 1, False, "joint", 16, 1000)
            self.assertTrue(result["success"], result["errors"])
            self.assertEqual(sorted(r["request"] for r in result["requests"]), list(range(16)))
            self.assertEqual(result["committed_stage_bytes"], 64)
            self.assertTrue(result["foreground"]["healthy"])
            self.assertFalse(result["foreground"]["p99_sample_floor_met"])
            phases = {r["name"] for r in result["phases"]}
            self.assertTrue({"bootstrap", "snapshot", "planning", "admission", "post_verification"} <= phases)
            self.assertTrue(any(name.endswith("/reset_ack") for name in phases))
            self.assertGreater(result["restoration_wall_ns"], 0)
            self.assertTrue(all(r["latency_ns"] >= r["service_ns"] >= 0 for r in result["requests"]))

    def test_latency_summary_retains_boundary_reads_and_rejects_missing_duplicate_or_failed(self):
        records = [{"request": i, "arrival_ns": i, "enqueue_ns": i+1, "service_start_ns": 20+i,
                    "end_ns": 40+i, "latency_ns": 40, "service_ns": 20, "error": None} for i in range(3)]
        summary = foreground_summary(records, 3, 10)
        self.assertTrue(summary["healthy"])
        self.assertEqual(summary["ending_after_restoration"], 3)
        self.assertEqual(summary["starting_after_restoration"], 3)
        self.assertEqual(summary["p99_latency_ns"], 40)
        self.assertFalse(summary["p99_sample_floor_met"])
        for invalid in (records[:-1], records[:2] + records[:1], records[:2] + [{**records[2], "error": "failed"}]):
            with self.subTest(invalid=invalid):
                result = foreground_summary(invalid, 3, 10)
                self.assertFalse(result["healthy"])
                self.assertIsNone(result["p99_latency_ns"])

    def test_pair_completeness_cannot_hide_duplicate_arms_or_small_p99_sample(self):
        records = []
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for unit, groups in ((64, 1), (4096, 4)):
                for extra in (False, True):
                    for arm in ARMS:
                        records.append({"profile": profile, "unit": unit, "groups": groups, "extra": extra,
                                        "pair": 0, "arm": arm, "success": True, "initial_sha256": "same",
                                        "object_sha256": {"object": "same"}, "committed_stage_bytes": 64,
                                        "controller_thread_cpu_ns": 100000000, "cpu_floor_met": True,
                                        "foreground": {"p99_sample_floor_met": False}})
        result = paired_summary(records, 1)
        self.assertTrue(result["all_declared_pairs_collected"])
        self.assertFalse(result["confirmation_sample_floor_met"])
        self.assertFalse(result["five_percent_foreground_gate_evaluated"])
        self.assertFalse(paired_summary(records + records[:1], 1)["all_declared_pairs_collected"])
        self.assertFalse(paired_summary(records[:-1], 1)["all_declared_pairs_collected"])

    def test_bad_workload_or_existing_root_cannot_destroy_old_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "existing"
            root.mkdir()
            marker = root / "keep.txt"
            marker.write_text("keep")
            result = cost_window(root, DEFAULT_PROFILE, 64, 1, False, "joint", 2, 1000)
            self.assertFalse(result["success"])
            self.assertEqual(marker.read_text(), "keep")
            self.assertEqual(list(root.iterdir()), [marker])
            with self.assertRaises(ValueError):
                cost_window(Path(tmp)/"bad", DEFAULT_PROFILE, 64, 1, False, "joint", 0, 100)
            with self.assertRaises(ValueError):
                workload(DEFAULT_PROFILE, 1, 1, False)
            with self.assertRaises(ValueError):
                compose_plan(None, [], "unknown")


if __name__ == "__main__":
    unittest.main()
