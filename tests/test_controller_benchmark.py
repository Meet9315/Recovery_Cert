"""Measurement integrity and real-storage coverage for the benchmark runner."""

import unittest

from prism_c.controller_benchmark import attempt, controller_benchmark, p99, summarize, MODES
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO


class ControllerBenchmarkTests(unittest.TestCase):
    def test_same_durable_witness_across_modes_and_profiles(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            records = [attempt(2, profile, False, 17, mode) for mode in MODES]
            self.assertEqual(len({record["witness_digest"] for record in records}), 1)
            for record in records:
                self.assertEqual(record["status"], "completed")
                self.assertGreater(record["restoration_wall_ns"], 0)
                self.assertEqual(record["worker_cpu_ns"], 0)
                self.assertEqual(record["reclaimed_extent_bytes"], 1024 if profile == DEFAULT_PROFILE else 2048)
                self.assertEqual(record["promoted_payload_bytes"], 1026 if profile == DEFAULT_PROFILE else 1028)
                self.assertLessEqual(record["peak_nonfree_bytes"], record["managed_capacity_bytes"])
                self.assertFalse(record["foreground"]["errors"])

    def test_worker_cpu_and_receipt_lookup_are_included(self):
        record = attempt(2, FOUR_PLUS_TWO, True, 23, "conventional_cached")
        self.assertGreater(record["worker_cpu_ns"], 0)
        self.assertEqual(record["total_cpu_ns"], record["controller_cpu_ns"] + record["worker_cpu_ns"])
        operations = [rpc["operation"] for rpc in record["worker_rpcs"]]
        self.assertEqual(operations.count("execute"), 6)  # Four stages plus two reclaims.
        self.assertEqual(operations.count("receipt"), 6)

    def test_small_latency_samples_and_zero_cpu_do_not_create_success(self):
        self.assertIsNone(p99(list(range(199))))
        self.assertEqual(p99(list(range(200))), 197)
        record = {"total_cpu_ns": 0, "restoration_wall_ns": 100,
                  "foreground": {"idle_p99_ns": None, "repair_p99_ns": None}}
        pairs = [{"modes": {mode: [record] for mode in MODES}} for _ in range(10)]
        result = summarize(pairs, 2, 1)
        self.assertFalse(result["total_cpu_ns"]["selective_vs_conventional_cached"]["available"])
        self.assertEqual(result["foreground_p99"]["status"], "insufficient")
        self.assertFalse(result["numerical_proxy_thresholds"]["total_cpu_ns"]["point_estimate_meets_proxy_threshold"])
        self.assertFalse(result["numerical_proxy_thresholds"]["foreground_p99"]["evaluated"])

    def test_registration_rejects_underpowered_run_count(self):
        with self.assertRaises(ValueError):
            controller_benchmark(runs=9)


if __name__ == "__main__":
    unittest.main()
