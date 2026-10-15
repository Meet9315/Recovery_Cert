"""Descriptive all-stratum summaries; no confidence interval or pass threshold."""

import json
from pathlib import Path
import statistics


def summarize(report):
    if not report["success"]:
        raise ValueError("Cannot summarize an incomplete pilot as successful")
    configurations = {}
    for record in report["records"]:
        key = (record["profile"], record["unit"], record["groups"], record["extra"])
        configurations.setdefault(key, {}).setdefault(record["arm"], []).append(record)
    rows = []
    for key, arms in sorted(configurations.items()):
        row = dict(zip(("profile", "unit", "groups", "extra"), key))
        row["arms"] = {}
        for name, windows in sorted(arms.items()):
            def median(field):
                return statistics.median(w[field] for w in windows)
            phases = {}
            for w in windows:
                for phase in w["phases"]:
                    name_group = "actions" if phase["name"].startswith("action/") else phase["name"]
                    phases.setdefault(name_group, {}).setdefault(w["pair"], 0)
                    phases[name_group][w["pair"]] += phase["controller_thread_cpu_ns"]
            overlap = [sum(r["arrival_ns"] < w["restoration_stop_ns"] and r["service_start_ns"] > w["restoration_stop_ns"] for r in w["requests"]) for w in windows]
            row["arms"][name] = {"windows": len(windows), "controller_cpu_median_ms": median("controller_thread_cpu_ns") / 1e6,
                                  "restoration_wall_median_ms": median("restoration_wall_ns") / 1e6,
                                  "stage_bytes_median": median("committed_stage_bytes"),
                                  "empirical_window_p99_median_ms": statistics.median(w["foreground"]["p99_latency_ns"] for w in windows) / 1e6,
                                  "arriving_before_restoration_per_window": [w["foreground"]["arrived_before_restoration"] for w in windows],
                                  "arriving_before_but_serviced_after_restoration_per_window": overlap,
                                  "phase_cpu_median_ms": {p: statistics.median(v.values()) / 1e6 for p, v in phases.items()}}
        effects = [e for e in report["summary"]["effects"] if (e["profile"], e["unit"], e["groups"], e["extra"]) == key]
        row["joint_repeat_cpu_ratios"] = [e["identical_joint_repeat_cpu_ratio"] for e in effects]
        row["joint_vs_restricted_control_cpu_percent_by_set"] = [e["joint_vs_control_cpu_percent"] for e in effects]
        rows.append(row)
    return {"scope": "All eight strata, descriptive medians/two per-set observations only; no confirmatory performance claim",
            "configurations": rows, "confirmation_sample_floor_met": report["summary"]["confirmation_sample_floor_met"],
            "five_percent_foreground_gate_evaluated": False, "patent_rating_changed": False}


def main():
    root = Path(__file__).resolve().parents[1] / "evidence/results"
    output = {}
    for name in ("zoned-cost-e17.json", "zoned-cost-e17-sequential.json"):
        output[name] = summarize(json.loads((root / name).read_text(encoding="utf-8")))
    path = root / "zoned-cost-e17-summary.json"
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(path))


if __name__ == "__main__":
    main()
