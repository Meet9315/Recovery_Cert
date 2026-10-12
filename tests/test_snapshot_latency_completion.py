import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.complete_snapshot_latency import ROOT, canonical_sha256, complete, load_original, validate_pair


class SnapshotContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((ROOT / "evidence/results/snapshot-latency-milestone-08.json").read_text())

    def test_original_source_mismatch_is_rejected_and_json_hash_ignores_layout(self):
        source = copy.deepcopy({key: self.original[key] for key in ("status", "runs", "protocol_sha256", "environment")})
        source["environment"]["source_sha256"]["prism_c/storage.py"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "failed.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source changed"):
                load_original(path)
        self.assertEqual(canonical_sha256({"a": 1, "b": [2]}), canonical_sha256(json.loads('{ "b": [2], "a": 1 }')))

    def test_retained_pair_identity_and_request_completeness_are_enforced(self):
        cfg = self.original["configurations"][0]
        pair = copy.deepcopy(cfg["pairs"][0])
        validate_pair(pair, cfg["profile"], cfg["storage_workers"], 0, self.original["seed"], pair["order"])
        pair["attempts"]["read"]["foreground"]["requests"].pop()
        with self.assertRaisesRegex(ValueError, "requests"):
            validate_pair(pair, cfg["profile"], cfg["storage_workers"], 0, self.original["seed"], pair["order"])

    def test_continuation_retains_only_completed_pairs_and_survives_console_errors(self):
        failed_pair = self.original["configurations"][-1]["pairs"][-1]
        calls = []
        def collect(profile, workers, seed, api):
            calls.append((profile, workers, seed, api))
            window = copy.deepcopy(failed_pair["attempts"][api])
            window["seed"] = seed
            return window
        with patch("experiments.complete_snapshot_latency.latency_window", side_effect=collect), \
             patch("experiments.complete_snapshot_latency.warmup", return_value={"status": "completed"}), \
             patch("builtins.print", side_effect=OSError(22, "console unavailable")):
            report = complete(self.original)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(len(calls), 10)
        self.assertTrue(all(workers and seed >= self.original["seed"] + 5 for _, workers, seed, _ in calls))
        pairs = [p for cfg in report["configurations"] for p in cfg["pairs"]]
        self.assertEqual(len(pairs), 40)
        self.assertEqual(sum(p["retained_original_pair"] for p in pairs), 35)
        self.assertEqual(len(report["telemetry_errors"]), 5)
        self.assertEqual(report["original_campaign_status"], "failed")
        self.assertFalse(report["uninterrupted_original_confirmation"])
        self.assertFalse(report["research_gate_passed"])
