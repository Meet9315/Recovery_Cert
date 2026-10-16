"""All-stratum descriptive E18 report; bootstrap decisions come from frozen code."""

import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[1] / "evidence/results"


def build_summary():
    manifests = {phase: json.loads((ROOT/f"e18-{phase}/manifest.json").read_text(encoding="utf-8"))
                 for phase in ("profile", "calibration", "characterization")}
    if not all(m["success"] for m in manifests.values()):
        raise ValueError("Incomplete/failed experiment cannot become a completed summary")
    diagnosis = []
    for ref in manifests["profile"]["records"]:
        record = json.loads((ROOT/"e18-profile"/ref["file"]).read_text(encoding="utf-8"))
        phases = {}
        for phase, data in record["phases"].items():
            categories = data["exclusive_categories_elapsed_ns"]
            total = sum(categories.values())
            phases[phase] = {"wall_ms": data["wall_ns"]/1e6, "whole_phase_thread_cpu_ms": data["thread_cpu_ns"]/1e6,
                             "exclusive_elapsed_categories_ms": {k: v/1e6 for k, v in categories.items()},
                             "exclusive_elapsed_category_percent": {k: 100*v/total for k, v in categories.items()},
                             "coding_function_calls": {f["function"]: f["calls"] for f in data["functions"]
                                 if f["file"].endswith("/coding.py") and f["function"] in ("gf_mul", "combine", "recover")}}
        diagnosis.append({**{k: record[k] for k in ("profile", "extra", "arm", "unit", "groups")},
                          "phases": phases, "instrumented_elapsed_not_cpu_share": True})
    calibration, characterization = manifests["calibration"], manifests["characterization"]
    rows = []
    for result in characterization["summary"]["configurations"]:
        matching = [r for r in characterization["records"] if (r["profile"], r["extra"], r["groups"]) ==
                    (result["profile"], result["extra"], result["groups"])]
        row = {k: result[k] for k in ("profile", "extra", "groups", "matched_sets", "adequate",
                                      "identical_software_p99_5pct_repeatability_screen")}
        row["comparisons"] = result["comparisons"]
        row["arms"] = {}
        for arm in ("joint", "joint_repeat", "separated"):
            refs = [r for r in matching if r["arm"] == arm]
            row["arms"][arm] = {"windows": len(refs), "controller_cpu_median_ms": statistics.median(r["controller_thread_cpu_ns"] for r in refs)/1e6,
                                 "restoration_wall_median_ms": statistics.median(r["restoration_wall_ns"] for r in refs)/1e6,
                                 "empirical_window_p99_median_ms": statistics.median(r["p99_ns"] for r in refs)/1e6,
                                 "stage_bytes_median": statistics.median(r["committed_stage_bytes"] for r in refs),
                                 "minimum_controller_cpu_ms": min(r["controller_thread_cpu_ns"] for r in refs)/1e6,
                                 "minimum_enqueued_before_restoration": min(r["quality"]["enqueued_before_restoration"] for r in refs),
                                 "insufficient_windows": sum(not r["quality"]["adequate"] for r in refs)}
        rows.append(row)
    return {"source_commit": characterization["environment"]["git_head"], "profiles": diagnosis,
            "calibration_windows": len(calibration["records"]), "selections": calibration["selections"],
            "characterization_windows": len(characterization["records"]),
            "offered_characterization_requests": len(characterization["records"])*characterization["count"],
            "characterization_adequate": characterization["summary"]["adequate"],
            "configurations": rows, "original_prism_gate_evaluated": False, "patent_rating_changed": False,
            "collection_sessions": 2 if "continuation" in characterization else 1,
            "continuation": characterization.get("continuation"),
            "scope": "All four fixed configurations. Profile elapsed shares include instrumentation/waits. Ten-set ratio intervals remain conditional on observed host conditions; the two-session continuation does not remove session confounding."}


def main():
    summary = build_summary()
    (ROOT/"e18-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    for row in summary["configurations"]:
        print(json.dumps({k: v for k, v in row.items() if k not in ("arms", "comparisons")}))
        for arm, data in row["arms"].items():
            print(arm, json.dumps(data))
        print("paired ratios", json.dumps(row["comparisons"]))


if __name__ == "__main__":
    main()
