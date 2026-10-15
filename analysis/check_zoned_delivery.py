"""Recompute E16/E17 evidence integrity, without rerunning runtime experiments."""

import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SOURCE = "d87264102c2f66569cb7a1fe6a3306ef056e7558"


def read(name):
    return json.loads((ROOT / "evidence/results" / name).read_text(encoding="utf-8"))


def main():
    comparison = read("zoned-file-e16-r2.json")
    verification = read("verification-e17.json")
    ci = read("ci-e17.json")
    pilots = [read(name) for name in ("zoned-cost-e17.json", "zoned-cost-e17-sequential.json")]
    hashes = comparison["environment"]["source_sha256"]
    actual_sources = {p.relative_to(ROOT).as_posix() for folder in ("prism_c", "tests") for p in (ROOT / folder).glob("*.py")}
    assert actual_sources == set(hashes)
    assert comparison["success"] and verification["success"]
    assert verification["failures"] == verification["errors"] == 0
    assert (verification["test_methods"], verification["subtests"]) == (205, 501)
    assert hashes == verification["environment"]["source_sha256"]
    for path, sha in hashes.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == sha, path
    prior = read("verification-r15.json")["environment"]["source_sha256"]
    assert all(hashes[path] == sha for path, sha in prior.items())
    first = read("zoned-file-e16.json")
    assert first["success"] and read("verification-e16.json")["success"]
    assert first["environment"]["source_sha256"] == read("verification-e16.json")["environment"]["source_sha256"]
    changed = [path for path, sha in first["environment"]["source_sha256"].items() if hashes[path] != sha]
    assert changed == ["tests/test_zoned_store.py"]
    assert read("ci-e16-initial.json")["conclusion"] == "failure"
    assert comparison["environment"]["git_head"] == ci["head_sha"] == SOURCE
    assert ci["conclusion"] == "success" and set(ci["jobs"].values()) == {"success"}
    ci_verification = read("verification-e17-ci-windows.json")
    assert ci_verification["success"] and ci_verification["environment"]["source_sha256"] == hashes
    assert (ci_verification["test_methods"], ci_verification["subtests"]) == (205, 501)
    assert comparison["environment"]["protocol_sha256"] == hashlib.sha256((ROOT / "experiments/zoned_file_protocol.md").read_bytes()).hexdigest()
    records = comparison["comparison_records"]
    found = [r for r in records if r["status"] == "FOUND"]
    assert len(records) == 32 and len(found) == 12
    assert len([r for r in records if r["status"] == "INFEASIBLE" and not r["physical_execution"]]) == 20
    assert all(r["physical_execution"] for r in found)
    prefixes = sum(r[m]["prefix_readbacks"] for r in found for m in ("joint", "control"))
    assert prefixes == comparison["comparison"]["prefix_readbacks"] == 280
    assert sum(r["stage_saving_vs_restricted_control"] for r in found) == 2
    for case in found:
        for mode in ("joint", "control"):
            route = case[mode]
            receipts = route["receipts"]
            assert [r["cursor"] for r in receipts] == list(range(len(receipts)))
            assert route["exact_contents"] and route["audit"]["target"]
            assert route["committed_stage_bytes"] == sum(r["stage_bytes"] for r in receipts)
            for prefix in route["trace"]:
                assert all(z["appendable_units"] <= z["capacity_units"] - z["charged_units"] for z in prefix["ledger"].values())
        sizes = [case[mode]["committed_stage_bytes"] for mode in ("joint", "control")]
        assert sizes == [64, 128] if case["stage_saving_vs_restricted_control"] else sizes[0] == sizes[1]
    faults = comparison["fault_records"]
    assert len(faults) == 32 and all(r["success"] and r["exit_code"] == 86 and r["stale_fence_rejected"] and r["exact_contents"] for r in faults)
    assert sum(r["expected"] == "recover" for r in faults) == 28
    for fault in faults:
        if fault["expected"] != "recover":
            assert fault["before_cursor"] == fault["final_cursor"] and fault["before_pending"]
            assert fault["final_ledger"]["A"]["physical_bytes"] == (32 if fault["expected"] == "partial" else 64)
            assert all(z["appendable_units"] == 0 for z in fault["final_ledger"].values())
            assert fault["quarantine_reason"]
        else:
            assert sum(r["stage_bytes"] for r in fault["receipts"]) == 64
            assert fault["final_ledger"]["A"]["incarnation"] == 2
    from prism_c.zoned_cost import foreground_summary, paired_summary
    from analysis.summarize_zoned_cost import summarize
    summaries = read("zoned-cost-e17-summary.json")
    requests = 0
    for pilot in pilots:
        assert pilot["success"] and len(pilot["records"]) == 48
        assert pilot["environment"]["git_head"] == SOURCE
        assert pilot["environment"]["source_sha256"] == hashes
        assert pilot["environment"]["protocol_sha256"] == hashlib.sha256((ROOT / "experiments/zoned_cost_protocol.md").read_bytes()).hexdigest()
        summary = paired_summary(pilot["records"], 2)
        assert summary == pilot["summary"]
        assert summary["all_declared_pairs_collected"] and not summary["confirmation_sample_floor_met"]
        assert not summary["five_percent_foreground_gate_evaluated"] and not summary["patent_advantage_claimed"]
        for window in pilot["records"]:
            rows = window["requests"]
            assert window["success"] and not window["errors"] and len(rows) == 400
            assert sorted(r["request"] for r in rows) == list(range(400))
            assert all(r["error"] is None and r["latency_ns"] >= r["service_ns"] >= 0 for r in rows)
            assert foreground_summary(rows, 400, window["restoration_stop_ns"]) == window["foreground"]
            assert all(r["latency_ns"] == r["end_ns"] - r["arrival_ns"] and r["service_ns"] == r["end_ns"] - r["service_start_ns"] for r in rows)
            assert window["committed_stage_bytes"] == window["unit"] * sum(a["kind"] == "stage" for a in window["witness"]["actions"])
            assert len(window["receipts"]) == len(window["witness"]["actions"])
            assert all(p["wall_ns"] >= 0 and p["controller_thread_cpu_ns"] >= 0 for p in window["phases"])
            requests += len(rows)
    for name, pilot in zip(("zoned-cost-e17.json", "zoned-cost-e17-sequential.json"), pilots):
        assert summarize(pilot) == summaries[name]
    links = []
    generated_record = ROOT / "evidence/results/e17-evidence-check.json"
    documents = list(ROOT.glob("*.md")) + list((ROOT / "spec").glob("*.md")) + list((ROOT / "experiments").glob("*.md")) + list((ROOT / "evidence").rglob("*.md"))
    for document in documents:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "app://", "codex://")):
                continue
            target = unquote(target.split("#")[0])
            if target:
                resolved = (document.parent / target).resolve()
                # This report's own link becomes valid when we write it below.
                assert resolved == generated_record or resolved.exists(), (str(document), target)
                links.append((str(document.relative_to(ROOT)), target))
    record = {"date": "2026-10-15", "source_commit": SOURCE,
              "matching_source_test_hashes": len(hashes), "unchanged_r15_source_test_files": len(prior),
              "initial_e16_only_changed_file": changed, "protocol_hashes_match": True,
              "matrix_and_fault_arithmetic": "PASS", "actual_route_stores": 24,
              "exact_file_prefix_readbacks": prefixes, "registered_exit_scenarios_per_collection": len(faults),
              "recovered_exit_outcomes": 28, "conservative_quarantine_outcomes": 4,
              "timing_pilots": len(pilots), "total_timing_windows": 96, "retained_offered_requests": requests,
              "local_links_checked": len(links), "broken_links": 0,
              "full_confirmatory_foreground_gate_passed": False, "native_power_loss_durability_proven": False,
              "invention_score_changed": False, "current_readiness": 55,
              "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    record["summary_script_sha256"] = hashlib.sha256((ROOT / "analysis/summarize_zoned_cost.py").read_bytes()).hexdigest()
    generated_record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    assert generated_record.exists()
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
