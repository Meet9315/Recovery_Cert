from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prism_c.coding import digest
from prism_c.profiles import DEFAULT_PROFILE
from prism_c.zoned_cost import ARMS
from prism_c.zoned_measure import (Archive, CONFIGS, CPU_FLOOR, bootstrap, group_passes,
                                    load_calibration, main, profiled_call, profile_route, quality, summarize)


def sample(count=1200, cpu=CPU_FLOOR, stop=10000):
    return {"success": True, "errors": [], "controller_thread_cpu_ns": cpu,
            "restoration_stop_ns": stop, "requests": [
                {"request": i, "arrival_ns": i, "enqueue_ns": i+1, "service_start_ns": i+2,
                 "end_ns": i+3, "latency_ns": 3, "service_ns": 1, "error": None} for i in range(count)]}


def refs_for(selections, pairs=10):
    return [{**s, "unit": 4096, "pair": pair, "arm": arm, "success": True,
             "quality": {"adequate": True}, "initial_sha256": "identical", "object_sha256": {"object": "same"},
             "committed_stage_bytes": 64, "controller_thread_cpu_ns": 2000000000,
             "restoration_wall_ns": 3000000000, "p99_ns": 1000000000}
            for s in selections for pair in range(pairs) for arm in ARMS]


class ZonedMeasurementTests(unittest.TestCase):
    def test_quality_requires_real_enqueues_cpu_and_exact_request_identities(self):
        self.assertTrue(quality(sample())["adequate"])
        short = sample(cpu=CPU_FLOOR-1)
        self.assertFalse(quality(short)["adequate"])
        late = sample()
        for row in late["requests"][999:]:
            row["enqueue_ns"] = 20000
        self.assertEqual(quality(late)["scheduled_before_restoration"], 1200)
        self.assertEqual(quality(late)["enqueued_before_restoration"], 999)
        self.assertFalse(quality(late)["adequate"])
        for bad in (sample(count=1199), sample()):
            if len(bad["requests"]) == 1200:
                bad["requests"][-1]["request"] = 0
            self.assertFalse(quality(bad)["collection_integrity"])

    def test_candidate_requires_both_complete_sets_not_a_favorable_subset(self):
        refs = [{"pair": pair, "arm": arm, "quality": {"adequate": True}}
                for pair in range(2) for arm in ARMS]
        self.assertTrue(group_passes(refs))
        for bad in (refs[:-1], refs + refs[:1]):
            self.assertFalse(group_passes(bad))
        bad = deepcopy(refs)
        bad[-1]["quality"]["adequate"] = False
        self.assertFalse(group_passes(bad))

    def test_profile_real_bytes_and_separate_cpu_from_instrumented_elapsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = profile_route(Path(tmp)/"store", DEFAULT_PROFILE, False, "joint", unit=64, groups=1)
            self.assertTrue(result["success"], result.get("error"))
            self.assertEqual(result["committed_stage_bytes"], 64)
            self.assertFalse(result["foreground_present"])
            self.assertEqual(set(result["phases"]), {"planning", "admission", "actions"})
            for phase in result["phases"].values():
                self.assertIsNone(phase["error"])
                self.assertGreater(phase["wall_ns"], 0)
                self.assertEqual(sum(phase["exclusive_categories_elapsed_ns"].values()),
                                 sum(f["exclusive_elapsed_ns"] for f in phase["functions"]))

    def test_failed_profile_keeps_partial_statistics_and_releases_profiler(self):
        def fail():
            sum(range(100))
            raise RuntimeError("intentional profile failure")
        value, report = profiled_call(fail)
        self.assertIsNone(value)
        self.assertIn("intentional", report["error"])
        self.assertTrue(report["functions"])
        import sys
        self.assertIsNone(sys.getprofile())

    def test_complete_matching_and_identical_input_guards(self):
        selections = [{"profile": p, "extra": e, "groups": 4} for p, e in CONFIGS]
        refs = refs_for(selections)
        summary = summarize(refs, selections)
        self.assertTrue(summary["complete"])
        self.assertTrue(summary["adequate"])
        self.assertTrue(all(r["identical_software_p99_5pct_repeatability_screen"] for r in summary["configurations"]))
        self.assertFalse(summary["original_prism_gate_evaluated"])
        self.assertFalse(summarize(refs[:-1], selections)["complete"])
        self.assertFalse(summarize(refs+refs[:1], selections)["complete"])
        bad = deepcopy(refs)
        bad[0]["quality"]["adequate"] = False
        self.assertFalse(summarize(bad, selections)["adequate"])
        bad = deepcopy(refs)
        bad[0]["initial_sha256"] = "changed"
        with self.assertRaises(ValueError):
            summarize(bad, selections)

    def test_calibration_rejects_altered_shards_and_source_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Archive(Path(tmp)/"evidence", "calibrate")
            for profile, extra in CONFIGS:
                for pair in range(2):
                    for arm in ARMS:
                        record = {**sample(), "profile": profile, "extra": extra, "groups": 4, "unit": 4096,
                                  "arm": arm, "initial_sha256": "same", "object_sha256": {"object": "same"}}
                        archive.add(record, pair=pair)
            archive.document.update(success=True, selection_complete=True,
                                    selections=[{"profile": p, "extra": e, "groups": 4} for p, e in CONFIGS])
            archive.checkpoint()
            archive.finish()
            path = archive.root / "manifest.json"
            document, sha = load_calibration(path, archive.document["environment"])
            self.assertEqual(sha, digest(path.read_bytes()))
            wrong = {**archive.document["environment"], "git_head": "changed"}
            with self.assertRaisesRegex(ValueError, "source/protocol"):
                load_calibration(path, wrong)
            shard = archive.root / document["records"][0]["file"]
            shard.write_text("{}")
            with self.assertRaisesRegex(ValueError, "digest"):
                load_calibration(path, archive.document["environment"])
            with self.assertRaises(FileExistsError):
                Archive(archive.root, "calibrate")

    def test_bootstrap_is_reproducible_and_invalid_counters_cannot_pass(self):
        self.assertEqual(bootstrap([1.0]*10, 18)["paired_bootstrap_95_percent_interval"], [1.0, 1.0])
        self.assertEqual(bootstrap([.8, 1, 1.2], 18), bootstrap([.8, 1, 1.2], 18))
        with self.assertRaises(ValueError):
            bootstrap([], 18)
        selections = [{"profile": p, "extra": e, "groups": 4} for p, e in CONFIGS]
        bad = refs_for(selections)
        bad[1]["p99_ns"] = 0
        with self.assertRaisesRegex(ValueError, "counter"):
            summarize(bad, selections)

    def test_cli_final_manifest_is_written_after_success_or_failed_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            for succeeds in (True, False):
                output = Path(tmp) / str(succeeds) / "evidence"
                root = Path(tmp) / str(succeeds) / "store"
                def fake_profile(path, profile, extra, arm):
                    return {"success": succeeds, "profile": profile, "extra": extra, "arm": arm,
                            "groups": 4, "unit": 4096, "error": None if succeeds else "intentional"}
                argv = ["zoned_measure", "profile", "--root", str(root), "--output", str(output)]
                with patch("sys.argv", argv), patch("prism_c.zoned_measure.profile_route", fake_profile), redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), 0 if succeeds else 1)
                final = json.loads((output / "manifest.json").read_text())
                self.assertEqual(final["success"], succeeds)
                self.assertEqual(len(final["records"]), 8 if succeeds else 1)
                self.assertEqual(len(list((output/"checkpoints").glob("*.json"))), len(final["records"])+2)
                self.assertFalse((output / "manifest.pending").exists())


if __name__ == "__main__":
    unittest.main()
