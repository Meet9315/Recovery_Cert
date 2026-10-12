from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prism_c import storage
from prism_c.liveness import pulse_report
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.read_reuse import read_batch, read_fixture, read_reuse_benchmark, reconstruction_probe, redundant_reads, require_batch
from prism_c.snapshot_latency import latency_window


class ReadReuseBenchmarkTests(unittest.TestCase):
    def test_mechanism_comparator_preserves_class_and_counts_real_decodes(self):
        original = storage.Authority.read
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for api in ("read", "read_snapshot"):
                with self.subTest(profile=profile, api=api), tempfile.TemporaryDirectory() as tmp:
                    store, content, _ = read_fixture(Path(tmp) / "store", profile, 1025, 211)
                    old = redundant_reads(storage.Authority(store.root))
                    self.assertEqual(reconstruction_probe(old, api, content), 2)
                    self.assertEqual(reconstruction_probe(store, api, content), 1)
                    self.assertIs(storage.Authority.read, original)
                    self.assertEqual(getattr(storage.Authority(store.root), api)("object"), content)

    def test_pulse_gap_retains_clock_and_cpu_deltas_without_identifying_cause(self):
        samples = [{"monotonic_ns": 10, "wall_ns": 100, "process_cpu_ns": 0, "pid": 1},
                   {"monotonic_ns": 600_000_010, "wall_ns": 500_000_100, "process_cpu_ns": 5, "pid": 1}]
        report = pulse_report(samples, 20, 100)
        self.assertTrue(report["gap_flagged"])
        self.assertEqual(report["samples"], samples)
        self.assertEqual(report["gaps"][0]["monotonic_gap_ns"], 600_000_000)
        self.assertEqual(report["gaps"][0]["wall_delta_ns"], 500_000_000)
        self.assertEqual(report["gaps"][0]["process_cpu_delta_ns"], 5)
        self.assertFalse(report["cause_identified"])
        self.assertFalse(pulse_report(samples, 700_000_000, 800_000_000)["gap_flagged"])

    def test_failed_read_and_unresolved_cpu_cannot_pass_confirmation(self):
        class WrongBytes:
            def read(self, name):
                return b"different"
        result = read_batch(WrongBytes(), "read", b"expected", 2)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reads_completed"], 0)
        with self.assertRaises(RuntimeError):
            require_batch(result)
        with self.assertRaisesRegex(RuntimeError, "timer minimum"):
            require_batch({"status": "completed", "reads_completed": 2, "repetitions": 2, "timer_resolved": False})

    def test_live_monitoring_keeps_all_arrivals_and_both_process_pulses(self):
        for variant in ("redundant", "reuse"):
            with self.subTest(variant=variant):
                result = latency_window(DEFAULT_PROFILE, False, 212, "read_snapshot", count=8, groups=2,
                                        variant=variant, monitored=True)
                self.assertTrue(result["foreground"]["healthy"])
                self.assertEqual(len(result["foreground"]["requests"]), 16)
                self.assertTrue(result["completed_group_targets_and_all_readbacks_match"])
                for component in ("controller", "reader"):
                    self.assertGreaterEqual(len(result["liveness"][component]["samples"]), 2)
                    self.assertFalse(result["liveness"][component]["cause_identified"])
                parent = result["liveness"]["controller"]["samples"][0]["pid"]
                child = result["liveness"]["reader"]["samples"][0]["pid"]
                self.assertNotEqual(parent, child)

    def test_calibration_failure_is_preserved_with_traceback(self):
        with self.assertRaises(ValueError):
            read_reuse_benchmark(runs=9)
        with patch("prism_c.read_reuse.read_batch", return_value={"status": "failed", "error": "injected"}):
            report = read_reuse_benchmark()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["cpu_configurations"][0]["calibration"][0]["error"], "injected")
        self.assertEqual(report["active_attempt"]["phase"], "calibration")
        self.assertIn("RuntimeError", report["traceback"])
        self.assertFalse(report["research_gate_passed"])
