"""Audit saved E18 observations without treating an interrupted run as complete."""

import json
from collections import Counter
from pathlib import Path

from prism_c.coding import digest
from prism_c.zoned_cost import foreground_summary
from prism_c.zoned_measure import load_calibration, quality


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evidence/results"
SOURCE = "e8ad2dba831f17749b0f8d27e5a32e63b1e9889a"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    verification = read(RESULTS / "verification-e18.json")
    windows_ci = read(RESULTS / "verification-e18-ci-windows.json")
    ci = read(RESULTS / "ci-e18.json")
    hashes = verification["environment"]["source_sha256"]
    assert verification["success"] and windows_ci["success"]
    assert (verification["test_methods"], verification["subtests"]) == (213, 501)
    assert hashes == windows_ci["environment"]["source_sha256"]
    actual = {p.relative_to(ROOT).as_posix() for folder in ("prism_c", "tests") for p in (ROOT / folder).glob("*.py")}
    assert actual == set(hashes) and len(hashes) == 73
    assert all(digest((ROOT / name).read_bytes()) == sha for name, sha in hashes.items())
    old = read(RESULTS / "verification-e17.json")["environment"]["source_sha256"]
    assert len(old) == 71 and all(hashes[name] == sha for name, sha in old.items())
    assert ci["head_sha"] == SOURCE and ci["conclusion"] == "success"
    assert set(ci["jobs"].values()) == {"success"}
    folder = RESULTS / "e18-characterization"
    assert not (folder / "manifest.json").exists(), "Use the final-manifest audit for a completed run"
    checkpoints = sorted((folder / "checkpoints").glob("checkpoint-*.json"))
    checkpoint = read(checkpoints[-1])
    calibration, calibration_sha = load_calibration(RESULTS / "e18-calibration/manifest.json", checkpoint["environment"])
    assert checkpoint["calibration_sha256"] == calibration_sha
    assert checkpoint["selections"] == calibration["selections"]
    documents = {"profile": read(RESULTS / "e18-profile/manifest.json"),
                 "calibration": calibration, "characterization": checkpoint}
    counts, requests, strata = {}, {}, Counter()
    for phase, document in documents.items():
        phase_dir = RESULTS / f"e18-{phase}"
        assert document["environment"]["git_head"] == SOURCE
        assert document["environment"]["source_sha256"] == hashes
        assert document["environment"]["protocol_sha256"] == digest((ROOT / "experiments/zoned_measurement_protocol.md").read_bytes())
        if phase != "characterization":
            assert document["success"]
        assert not document["candidate_mechanism_present"]
        assert not document["original_prism_gate_evaluated"] and not document["patent_rating_changed"]
        refs = document["records"]
        assert len({r["file"] for r in refs}) == len(refs)
        assert {r["file"] for r in refs} == {p.relative_to(phase_dir).as_posix() for p in (phase_dir / "windows").glob("*.json")}
        requests[phase] = 0
        for ref in refs:
            raw = (phase_dir / ref["file"]).read_bytes()
            assert digest(raw) == ref["sha256"]
            record = json.loads(raw)
            assert record["success"]
            for key in ("profile", "extra", "arm", "unit", "groups", "success", "committed_stage_bytes", "initial_sha256"):
                assert record[key] == ref[key]
            if phase != "profile":
                assert quality(record) == ref["quality"] and ref["quality"]["adequate"]
                assert foreground_summary(record["requests"], 1200, record["restoration_stop_ns"]) == record["foreground"]
                assert record["foreground"]["p99_latency_ns"] == ref["p99_ns"]
                for key in ("object_sha256", "controller_thread_cpu_ns", "restoration_wall_ns"):
                    assert record[key] == ref[key]
                assert sum(r["stage_bytes"] for r in record["receipts"]) == record["committed_stage_bytes"]
                assert len(record["receipts"]) == len(record["witness"]["actions"])
                requests[phase] += len(record["requests"])
                if phase == "characterization":
                    strata[f"{ref['profile']} spare={ref['extra']}"] += 1
        counts[phase] = len(refs)
    assert counts == {"profile": 8, "calibration": 24, "characterization": 64}
    assert requests["characterization"] == 76800
    # Every saved checkpoint must be a prefix of the final retained checkpoint.
    for path in checkpoints:
        earlier = read(path)["records"]
        assert earlier == checkpoint["records"][:len(earlier)]
    report = {"date": "2026-10-16", "source_commit": SOURCE,
              "saved_observation_integrity": "PASS", "full_campaign_complete": False,
              "status": "INTERRUPTED; final manifest absent; process no longer running; cause unknown",
              "latest_checkpoint": checkpoints[-1].relative_to(ROOT).as_posix(),
              "latest_checkpoint_sha256": digest(checkpoints[-1].read_bytes()),
              "matching_source_test_hashes": len(hashes), "unchanged_e17_source_test_files": len(old),
              "windows": counts, "requests": requests, "characterization_windows_by_configuration": dict(strata),
              "remaining_registered_windows": 56, "all_saved_timing_windows_adequate": True,
              "repeatability_screen_evaluated": False, "original_prism_gate_evaluated": False,
              "patent_readiness": 55, "audit_script_sha256": digest(Path(__file__).read_bytes())}
    (RESULTS / "e18-checkpoint-audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
