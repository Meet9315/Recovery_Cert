"""Recompute E19 microbenchmark/calibration/characterization evidence integrity."""

import json
from pathlib import Path
import random
import statistics

from prism_c.coding import digest
from prism_c.zoned_cost import foreground_summary
from prism_c import zoned_measure as measure


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "evidence/results"


def read(path):
    return json.loads(path.read_bytes())


def main():
    measure.PROTOCOL = ROOT/"experiments/codec_optimization_protocol.md"
    measure.GROUPS = (4, 6, 8, 12, 16)
    verification = read(RESULTS/"verification-e19.json")
    ci_verification = read(RESULTS/"verification-e19-ci-windows.json")
    ci = read(RESULTS/"ci-e19.json")
    hashes = verification["environment"]["source_sha256"]
    assert verification["success"] and ci_verification["success"]
    assert (verification["test_methods"], verification["subtests"]) == (218, 687)
    assert ci["conclusion"] == "success" and set(ci["jobs"].values()) == {"success"}
    assert hashes == ci_verification["environment"]["source_sha256"] and len(hashes) == 74
    actual = {p.relative_to(ROOT).as_posix() for folder in ("prism_c", "tests") for p in (ROOT/folder).glob("*.py")}
    assert actual == set(hashes)
    assert all(digest((ROOT/name).read_bytes()) == sha for name, sha in hashes.items())
    historical = read(RESULTS/"verification-e18.json")["environment"]["source_sha256"]
    assert [p for p in historical if historical[p] != hashes[p]] == ["prism_c/coding.py"]
    batches = read(RESULTS/"codec-batches-e19-r2.json")
    assert batches["success"] and batches["environment"]["source_sha256"] == hashes
    assert batches["historical_codec_sha256"] == historical["prism_c/coding.py"]
    assert batches["protocol_sha256"] == digest(measure.PROTOCOL.read_bytes())
    assert batches["helper_sha256"] == digest((ROOT/"analysis/codec_benchmark.py").read_bytes())
    assert batches["correction_sha256"] == digest((ROOT/"experiments/codec_micro_correction.md").read_bytes())
    assert batches["batch_operations"] == 100 and batches["matched_sets"] == 12
    assert batches["translation_table_payload_bytes"] == 65536
    assert all(len(v) == 5 for v in batches["cold"].values())
    rng, micro_rows = random.Random(20261016), []
    expected_configs = [(p, u, op) for p in ("xor-2+1-v1", "pq-4+2-gf256-v1") for u in (64, 4096) for op in ("encode", "recover")]
    assert [(r["profile"], r["unit"], r["operation"]) for r in batches["configurations"]] == expected_configs
    for config in batches["configurations"]:
        k = 2 if config["profile"] == "xor-2+1-v1" else 4
        data = random.Random(20261016+config["unit"]).randbytes(k*config["unit"]-1)
        assert config["actual_row_bytes"] == config["unit"]
        assert config["input_length"] == len(data) and config["input_sha256"] == digest(data)
        assert len(config["sets"]) == 12
        for pair, record in enumerate(config["sets"]):
            order = ["historical", "optimized"]
            rng.shuffle(order)
            assert record["pair"] == pair and record["order"] == order and set(record["arms"]) == set(order)
            assert all(value >= 0 for arm in record["arms"].values() for value in arm.values())
        for metric in ("thread_cpu_ns", "wall_ns"):
            ratios = [s["arms"]["optimized"][metric]/s["arms"]["historical"][metric] for s in config["sets"]
                      if min(s["arms"][a][metric] for a in ("historical", "optimized")) > 0]
            expected = measure.bootstrap(ratios, 20261016) if len(ratios) == 12 else {"status": "INSUFFICIENT_CLOCK_RESOLUTION", "positive_pairs": len(ratios)}
            assert expected == config["comparisons"][metric]
            for arm in ("historical", "optimized"):
                assert config["medians_ms"][arm][metric] == statistics.median(s["arms"][arm][metric] for s in config["sets"])/1e6
        micro_rows.append({k: config[k] for k in ("profile", "unit", "operation", "comparisons", "medians_ms")})
    calibration = read(RESULTS/"e19-calibration/manifest.json")
    confirmation = read(RESULTS/"e19-characterization/manifest.json")
    assert calibration["environment"]["git_head"] == confirmation["environment"]["git_head"]
    workload, sha = measure.load_calibration(RESULTS/"e19-calibration/manifest.json", confirmation["environment"])
    assert sha == confirmation["calibration_sha256"] and workload["selections"] == confirmation["selections"]
    counts = {}
    for phase, document in (("calibration", calibration), ("characterization", confirmation)):
        assert document["success"] and document["environment"]["source_sha256"] == hashes
        assert document["environment"]["protocol_sha256"] == digest(measure.PROTOCOL.read_bytes())
        assert document["environment"]["collector_driver_sha256"] == digest((ROOT/"analysis/measure_optimized_codec.py").read_bytes())
        folder = RESULTS/f"e19-{phase}"
        assert {r["file"] for r in document["records"]} == {p.relative_to(folder).as_posix() for p in (folder/"windows").glob("*.json")}
        for ref in document["records"]:
            raw = (folder/ref["file"]).read_bytes()
            assert digest(raw) == ref["sha256"]
            record = json.loads(raw)
            assert measure.quality(record) == ref["quality"] and ref["quality"]["collection_integrity"]
            assert foreground_summary(record["requests"], 1200, record["restoration_stop_ns"]) == record["foreground"]
            assert record["foreground"]["p99_latency_ns"] == ref["p99_ns"]
            for key in ("profile", "extra", "arm", "unit", "groups", "initial_sha256", "object_sha256", "committed_stage_bytes", "controller_thread_cpu_ns", "restoration_wall_ns"):
                assert record[key] == ref[key]
            assert sum(r["stage_bytes"] for r in record["receipts"]) == record["committed_stage_bytes"]
        counts[phase] = {"windows": len(document["records"]), "requests": sum(len(read(folder/ref["file"])["requests"]) for ref in document["records"]),
                         "inadequate_windows": sum(not r["quality"]["adequate"] for r in document["records"])}
    assert measure.summarize(confirmation["records"], confirmation["selections"]) == confirmation["summary"]
    assert confirmation["summary"]["complete"] and counts["characterization"]["windows"] == 120
    from analysis.continue_e18 import schedule
    assert all(all(ref[key] == value for key, value in entry.items()) for ref, entry in zip(confirmation["records"], schedule(confirmation["selections"])))
    summary = {"date": "2026-10-16", "source_ci_commit": ci["source_commit"], "collection_git_head": confirmation["environment"]["git_head"],
               "matching_source_test_hashes": 74, "only_changed_e18_runtime_file": "prism_c/coding.py", "success": True,
               "counts": counts, "selected_workloads": confirmation["selections"], "microbenchmark": micro_rows,
               "cold_module_median_wall_ms": {k: statistics.median(x["wall_ns"] for x in v)/1e6 for k, v in batches["cold"].items()},
               "controller_summary": confirmation["summary"], "original_prism_gate_evaluated": False,
               "patent_readiness": 55, "audit_script_sha256": digest(Path(__file__).read_bytes())}
    with (RESULTS/"e19-evidence-check.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("microbenchmark", "controller_summary")}, indent=2))


if __name__ == "__main__":
    main()
