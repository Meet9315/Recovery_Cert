import unittest
from unittest.mock import patch

from prism_c.fault_contention import attempt, fault_contention_benchmark
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO


class FaultContentionTests(unittest.TestCase):
    def test_committed_receipt_process_exit_retry_both_profiles_and_modes(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for mode in ("conventional_cached", "selective"):
                with self.subTest(profile=profile, mode=mode):
                    result = attempt(profile, "lost_receipt_retry", 913, mode)
                    self.assertEqual(result["status"], "completed", result.get("error", result))
                    self.assertEqual(result["actual_worker_exits"], 1)
                    fault = result["controllers"][0]["faults"][0]
                    self.assertEqual(fault["ledger_before"], fault["ledger_after_exit"])
                    self.assertTrue(fault["same_token"] and fault["same_durable_receipt"])
                    self.assertGreater(result["total_cpu_ns"], 0)

    def test_independent_controllers_restore_disjoint_scopes_both_profiles(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for mode in ("conventional_cached", "selective"):
                with self.subTest(profile=profile, mode=mode):
                    result = attempt(profile, "scoped_contention", 914, mode)
                    self.assertEqual(result["status"], "completed", result.get("error", result))
                    self.assertEqual(len({c["pid"] for c in result["controllers"]}), 2)
                    self.assertEqual(result["actual_worker_exits"], 0)
                    self.assertTrue(all(c["step_intervals"] for c in result["controllers"]))

    def test_registration_and_failed_attempt_are_retained(self):
        with self.assertRaises(ValueError):
            fault_contention_benchmark(runs=9)
        failed = {"status": "failed", "error": "retained failure"}
        saved = []
        with patch("prism_c.fault_contention.attempt", return_value=failed):
            result = fault_contention_benchmark(checkpoint=lambda report: saved.append(report["status"]))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["configurations"][0]["warmups"], [failed])
        self.assertEqual(saved[-1], "failed")
        self.assertFalse(result["controller_target_established"])
