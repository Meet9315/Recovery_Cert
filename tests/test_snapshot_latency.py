import multiprocessing
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from prism_c.controller_benchmark import _fixture
from prism_c.profiles import DEFAULT_PROFILE
from prism_c.snapshot_latency import _arrival_reader, inflation_summary, latency_window, snapshot_latency, summarize


class SnapshotLatencyTests(unittest.TestCase):
    def test_missing_duplicate_and_failed_requests_cannot_be_sufficient(self):
        requests = [{"phase": phase, "request": i, "latency_ns": 20, "service_ns": 10,
                     "queue_delay_ns": 10, "scheduling_lateness_ns": 0,
                     "service_start_ns": 90, "end_ns": 110, "error": None}
                    for phase in (0, 1) for i in range(400)]
        observed = {"requests": requests, "errors": [], "fallback_times_ns": [95]}
        result = summarize(observed, 100)
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["loaded_reads_ending_after_restoration"], 400)
        self.assertEqual(result["fallback_count"], 1)
        requests[-1] = {**requests[-1], "request": 0}
        self.assertFalse(summarize(observed, 100)["healthy"])
        requests[-1] = {**requests[-1], "request": 399, "error": "busy"}
        self.assertFalse(summarize(observed, 100)["sufficient"])
        requests.pop()
        self.assertFalse(summarize(observed, 100)["healthy"])

    def test_actual_fixed_arrivals_queue_during_writer_and_drain_after_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _, _, _ = _fixture(Path(tmp) / "store", 2, DEFAULT_PROFILE, False, 101, "conventional_cached")
            ctx = multiprocessing.get_context("spawn")
            origins = ctx.Array("q", [0, 0])
            ready, control_go, control_done, load_go, arrivals_done, abort = (ctx.Event() for _ in range(6))
            receive, send = ctx.Pipe(duplex=False)
            child = ctx.Process(target=_arrival_reader, args=(str(store.root), "read", origins, ready, control_go,
                                control_done, load_go, arrivals_done, abort, send, 8, 100))
            child.start()
            send.close()
            try:
                self.assertTrue(ready.wait(10))
                origins[0] = time.perf_counter_ns()
                control_go.set()
                self.assertTrue(control_done.wait(10))
                with store._transaction():
                    origins[1] = time.perf_counter_ns()
                    load_go.set()
                    # All eight are offered independently while the first read blocks.
                    self.assertTrue(arrivals_done.wait(10))
                    stop = time.perf_counter_ns()
                self.assertTrue(receive.poll(10))
                result = summarize(receive.recv(), stop, 8)
                child.join(10)
                self.assertEqual(child.exitcode, 0)
                self.assertTrue(result["healthy"])
                self.assertEqual(result["loaded_reads_ending_after_restoration"], 8)
                self.assertGreaterEqual(result["loaded_reads_starting_service_after_restoration"], 7)
                loaded = [r for r in result["requests"] if r["phase"] == 1]
                self.assertEqual([r["arrival_ns"] for r in loaded], [origins[1] + i * 10_000_000 for i in range(8)])
                self.assertTrue(all(r["latency_ns"] >= r["service_ns"] for r in loaded))
            finally:
                abort.set()
                control_go.set()
                load_go.set()
                child.join(2)
                if child.is_alive():
                    child.terminate()
                    child.join(10)
                receive.close()

    def test_live_pair_uses_identical_backlog_and_preserves_phase_membership(self):
        cells = [latency_window(DEFAULT_PROFILE, False, 103, api, count=8, rate=100, groups=2)
                 for api in ("read", "read_snapshot")]
        self.assertEqual(cells[0]["initial_backlog"], cells[1]["initial_backlog"])
        for cell in cells:
            self.assertTrue(cell["foreground"]["healthy"])
            self.assertTrue(cell["completed_group_targets_and_all_readbacks_match"])
            self.assertEqual(len(cell["foreground"]["requests"]), 16)
            marks = cell["phase_marks"]
            idle = [r for r in cell["foreground"]["requests"] if r["phase"] == 0]
            self.assertLessEqual(max(r["end_ns"] for r in idle), marks["load_origin_ns"])
            self.assertEqual(cell["foreground"]["fallback_count"], 0)

    def test_failed_attempt_is_saved_and_large_inflation_does_not_pass_screen(self):
        with self.assertRaises(ValueError):
            snapshot_latency(runs=9)
        failed = {"foreground": {"sufficient": False, "errors": ["busy"]}}
        with patch("prism_c.snapshot_latency.warmup", return_value={"status": "completed"}), \
             patch("prism_c.snapshot_latency.latency_window", return_value=failed):
            report = snapshot_latency()
        self.assertEqual(report["status"], "failed")
        pair = report["configurations"][0]["pairs"][0]
        self.assertEqual(pair["status"], "failed")
        self.assertEqual(list(pair["attempts"].values()), [failed])
        self.assertFalse(report["research_gate_passed"])
        self.assertFalse(inflation_summary([1.5] * 10, 3)["upper_bound_at_most_1_05"])
