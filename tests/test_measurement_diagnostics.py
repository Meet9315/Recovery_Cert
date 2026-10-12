"""Sampling boundaries, errors, nested attribution and actual durable repair."""

import multiprocessing
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from prism_c.controller_benchmark import _fixture
from prism_c.cpu_attribution import LogicalSpans, logical_spans
from prism_c.measurement_diagnostics import _window_reader, cpu_profile, diagnostics, foreground_summary, window
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.selective import ContinuationCache
from prism_c import storage


class MeasurementDiagnosticsTests(unittest.TestCase):
    def test_failed_cpu_collection_preserves_prior_window_and_failure_context(self):
        cell = {"initial_backlog": "fixture", "foreground": {"healthy": True}}
        checkpoints = []
        with patch("prism_c.measurement_diagnostics.window", return_value=cell), \
             patch("prism_c.measurement_diagnostics.cpu_profile", side_effect=RuntimeError("interrupted")):
            report = diagnostics(checkpoint=lambda r: checkpoints.append((r["status"], len(r["windows"]))))
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["windows"], [cell])
        self.assertEqual(report["cpu_profiles"], [])
        self.assertEqual(report["active_cell"]["phase"], "cpu_profile")
        self.assertIn("interrupted", report["error"])
        self.assertEqual(checkpoints, [("running", 1), ("failed", 1)])

    def test_late_loaded_reads_and_errors_are_not_discarded(self):
        requests = [{"phase_at_start": phase, "latency_ns": 10, "end_ns": 50, "error": None}
                    for phase in (0, 1) for _ in range(200)]
        requests.append({"phase_at_start": 1, "latency_ns": 1000, "end_ns": 150, "error": None})
        result = foreground_summary({"requests": requests, "errors": []}, 100)
        self.assertEqual(result["loaded_successes"], 201)
        self.assertEqual(result["loaded_reads_ending_after_restoration"], 1)
        self.assertEqual(result["status"], "sufficient")
        self.assertFalse(result["research_threshold_evaluated"])
        requests.append({"phase_at_start": 1, "latency_ns": 3000, "end_ns": 200, "error": "timeout"})
        failed = foreground_summary({"requests": requests, "errors": ["timeout"]}, 100)
        self.assertEqual(failed["status"], "failed")
        self.assertIsNone(failed["loaded_p99_ns"])
        self.assertEqual(len(failed["requests"]), 402)

    def test_nested_spans_count_only_outer_interval_and_restore_on_error(self):
        times = iter((10, 50))
        spans = LogicalSpans(clock=lambda: next(times))
        inner = spans.wrap("inner", lambda: 7)
        outer = spans.wrap("outer", lambda: inner())
        self.assertEqual(outer(), 7)
        self.assertEqual(spans.report()["outer_cpu_ns"], 40)
        self.assertEqual(spans.records["inner"]["calls"], 1)
        self.assertEqual(spans.records["inner"]["outer_calls"], 0)
        original_build = ContinuationCache.__dict__["build"]
        original_replay = storage.replay
        with self.assertRaises(ValueError):
            with logical_spans():
                self.assertIsNot(storage.replay, original_replay)
                raise ValueError("intentional interruption")
        self.assertIs(ContinuationCache.__dict__["build"], original_build)
        self.assertIs(storage.replay, original_replay)

    def test_live_control_pause_and_scoped_repair_readback(self):
        result = window(DEFAULT_PROFILE, False, 5, "shadow", groups=1, target_reads=1,
                        control_min=0.03, control_cap=1, load_min=0.001, load_cap=2)
        marks = result["phase_marks"]
        idle = [r for r in result["foreground"]["requests"] if r["phase_at_start"] == 0]
        loaded = [r for r in result["foreground"]["requests"] if r["phase_at_start"] == 1]
        self.assertTrue(idle)
        self.assertTrue(loaded)
        self.assertLessEqual(max(r["end_ns"] for r in idle), marks["load_start_ns"])
        self.assertTrue(all(marks["load_start_ns"] <= r["start_ns"] <= marks["load_stop_ns"] for r in loaded))
        self.assertTrue(result["completed_group_targets_and_all_readbacks_match"])
        self.assertEqual(len(result["completed_groups"]), 1)
        self.assertTrue(result["foreground"]["healthy"])

    def test_real_blocked_read_finishing_after_stop_is_drained(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _, _, _ = _fixture(Path(tmp) / "store", 2, DEFAULT_PROFILE, False, 7, "full")
            ctx = multiprocessing.get_context("spawn")
            phase, counts, failures = ctx.Value("i", 0), ctx.Array("q", [0, 0]), ctx.Value("i", 0)
            ready, begin, paused, resume = (ctx.Event() for _ in range(4))
            inflight = ctx.Value("i", -2)
            receive, send = ctx.Pipe(duplex=False)
            reader = ctx.Process(target=_window_reader, args=(str(store.root), phase, counts, failures, ready, begin, paused, resume, send, inflight))
            reader.start()
            send.close()
            try:
                self.assertTrue(ready.wait(10))
                phase.value = -1
                begin.set()
                self.assertTrue(paused.wait(10))
                with store._transaction():
                    phase.value = 1
                    resume.set()
                    deadline = time.perf_counter() + 3
                    while inflight.value != 1 and time.perf_counter() < deadline:
                        time.sleep(0.001)
                    self.assertEqual(inflight.value, 1)
                    with phase.get_lock():
                        stop = time.perf_counter_ns()
                        phase.value = 2
                self.assertTrue(receive.poll(10))
                observed = receive.recv()
                reader.join(10)
                self.assertEqual(reader.exitcode, 0)
                result = foreground_summary(observed, stop)
                self.assertEqual(result["loaded_successes"], 1)
                self.assertEqual(result["loaded_reads_ending_after_restoration"], 1)
                self.assertTrue(result["healthy"])
            finally:
                phase.value = 2
                begin.set()
                resume.set()
                reader.join(2)
                if reader.is_alive():
                    reader.terminate()
                    reader.join(10)
                receive.close()

    def test_controller_exclusive_costs_and_logical_subset_have_no_double_count(self):
        # Short Windows process-CPU intervals may quantize to zero. Verify
        # instrumentation still counts its calls under that exact condition.
        with patch("prism_c.cpu_attribution.LogicalSpans",
                   side_effect=lambda: LogicalSpans(clock=lambda: 0)):
            result = cpu_profile(DEFAULT_PROFILE, False, 11, "selective")
        profile = result["controller_profile"]
        self.assertEqual(sum(profile["exclusive_categories_cpu_ns"].values()),
                         sum(entry["exclusive_cpu_ns"] for entry in profile["functions"]))
        self.assertEqual(result["logical_verification_subset"]["outer_cpu_ns"], 0)
        self.assertGreater(sum(record["outer_calls"] for record in
                               result["logical_verification_subset"]["apis"].values()), 0)
        self.assertLessEqual(result["logical_verification_subset"]["outer_cpu_ns"], result["controller_cpu_ns"])
        self.assertTrue(any(entry["file"] == "prism_c/coding.py" and entry["function"] == "recover" for entry in profile["functions"]))
        self.assertEqual(result["worker_process_cpu_ns"], 0)

    def test_worker_handler_profiles_include_receipt_verification(self):
        result = cpu_profile(FOUR_PLUS_TWO, True, 13, "conventional_cached")
        self.assertEqual(len(result["worker_rpcs"]), 12)
        self.assertEqual(sum(rpc["process_cpu_ns"] for rpc in result["worker_rpcs"]), result["worker_process_cpu_ns"])
        for rpc in result["worker_rpcs"]:
            self.assertTrue(any(entry["file"] == "prism_c/worker.py" and entry["function"] == "handle"
                                for entry in rpc["handler_profile"]["functions"]))


if __name__ == "__main__":
    unittest.main()
