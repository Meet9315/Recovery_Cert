"""Recompute E18 shard/selection/statistics integrity against the frozen source."""

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

from prism_c.coding import digest
from prism_c.zoned_cost import foreground_summary
from prism_c.zoned_measure import CONFIGS, COUNT, load_calibration, quality, summarize


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evidence/results"
SOURCE = "e8ad2dba831f17749b0f8d27e5a32e63b1e9889a"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    documents = {phase: read(RESULTS / f"e18-{phase}/manifest.json") for phase in ("profile", "calibration", "characterization")}
    verification = read(RESULTS / "verification-e18.json")
    ci = read(RESULTS / "ci-e18.json")
    ci_verification = read(RESULTS / "verification-e18-ci-windows.json")
    previous = read(RESULTS / "verification-e17.json")
    hashes = verification["environment"]["source_sha256"]
    assert verification["success"] and ci_verification["success"]
    assert (verification["test_methods"], verification["subtests"]) == (213, 501)
    assert verification["failures"] == verification["errors"] == 0
    assert ci["head_sha"] == SOURCE and ci["conclusion"] == "success" and set(ci["jobs"].values()) == {"success"}
    assert hashes == ci_verification["environment"]["source_sha256"]
    actual = {p.relative_to(ROOT).as_posix() for folder in ("prism_c", "tests") for p in (ROOT/folder).glob("*.py")}
    assert actual == set(hashes)
    for path, sha in hashes.items():
        assert digest((ROOT/path).read_bytes()) == sha, path
    prior = previous["environment"]["source_sha256"]
    assert all(hashes[path] == sha for path, sha in prior.items())
    request_counts, window_counts = {}, {}
    profile_totals = []
    for phase, manifest in documents.items():
        folder = RESULTS / f"e18-{phase}"
        assert manifest["success"]
        assert manifest["environment"]["git_head"] == SOURCE
        assert manifest["environment"]["source_sha256"] == hashes
        assert manifest["environment"]["protocol_sha256"] == digest((ROOT/"experiments/zoned_measurement_protocol.md").read_bytes())
        assert not manifest["candidate_mechanism_present"] and not manifest["original_prism_gate_evaluated"] and not manifest["patent_rating_changed"]
        assert len({r["file"] for r in manifest["records"]}) == len(manifest["records"])
        windows = requests = 0
        for ref in manifest["records"]:
            assert re.fullmatch(r"windows/window-\d{4}\.json", ref["file"])
            raw = (folder/ref["file"]).read_bytes()
            assert digest(raw) == ref["sha256"]
            record = json.loads(raw)
            assert record["success"]
            for key in ("profile", "extra", "arm", "unit", "groups", "success", "committed_stage_bytes", "initial_sha256"):
                assert record[key] == ref[key]
            if phase == "profile":
                assert not record["foreground_present"] and not record["comparison_effect_claimed"]
                for item in record["phases"].values():
                    assert item["error"] is None and item["profile_is_not_uninstrumented_benchmark"]
                    assert sum(item["exclusive_categories_elapsed_ns"].values()) == sum(f["exclusive_elapsed_ns"] for f in item["functions"])
                profile_totals.append({key: record[key] for key in ("profile", "extra", "arm", "committed_stage_bytes")})
            else:
                assert ref["quality"] == quality(record)
                assert ref["quality"]["collection_integrity"]
                assert record["foreground"] == foreground_summary(record["requests"], COUNT, record["restoration_stop_ns"])
                assert ref["p99_ns"] == record["foreground"]["p99_latency_ns"]
                for key in ("object_sha256", "controller_thread_cpu_ns", "restoration_wall_ns"):
                    assert record[key] == ref[key]
                assert sum(r["stage_bytes"] for r in record["receipts"]) == record["committed_stage_bytes"]
                assert len(record["receipts"]) == len(record["witness"]["actions"])
                requests += len(record["requests"])
            windows += 1
        window_counts[phase], request_counts[phase] = windows, requests
    assert window_counts["profile"] == 8
    calibration, sha = load_calibration(RESULTS/"e18-calibration/manifest.json", documents["characterization"]["environment"])
    characterization = documents["characterization"]
    assert sha == characterization["calibration_sha256"]
    assert calibration["selections"] == characterization["selections"]
    assert summarize(characterization["records"], characterization["selections"]) == characterization["summary"]
    assert characterization["summary"]["complete"]
    assert window_counts["characterization"] == 120 and request_counts["characterization"] == 144000
    from analysis.summarize_zoned_measurement import build_summary
    assert build_summary() == read(RESULTS/"e18-summary.json")
    links = []
    generated = RESULTS / "e18-evidence-check.json"
    docs = list(ROOT.glob("*.md")) + list((ROOT/"spec").glob("*.md")) + list((ROOT/"experiments").glob("*.md")) + list((ROOT/"evidence").rglob("*.md"))
    for document in docs:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "app://", "codex://")):
                continue
            target = unquote(target.split("#")[0])
            if target:
                resolved = (document.parent/target).resolve()
                assert resolved == generated or resolved.exists(), (str(document), target)
                links.append((str(document.relative_to(ROOT)), target))
    summary = {"date": "2026-10-15", "source_commit": SOURCE, "matching_runtime_source_test_hashes": len(hashes),
               "unchanged_e17_runtime_test_files": len(prior), "protocol_hash_matches": True,
               "shard_digests_and_raw_derived_arithmetic": "PASS", "windows": window_counts,
               "requests": request_counts, "selected_workloads": calibration["selections"],
               "characterization_adequate": characterization["summary"]["adequate"],
               "identical_software_repeatability_screens": [{"profile": r["profile"], "extra": r["extra"],
                   "established": r["identical_software_p99_5pct_repeatability_screen"]} for r in characterization["summary"]["configurations"]],
               "local_links_checked": len(links), "broken_links": 0,
               "original_prism_gate_evaluated": False, "native_power_loss_durability_proven": False,
               "patent_readiness": 55, "audit_script_sha256": digest(Path(__file__).read_bytes())}
    summary["summary_script_sha256"] = digest((ROOT/"analysis/summarize_zoned_measurement.py").read_bytes())
    generated.write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    assert generated.exists()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
