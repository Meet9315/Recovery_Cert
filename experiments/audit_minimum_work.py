"""Registered untimed comparison including a stronger cost-aware conventional baseline."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import traceback

from prism_c.__main__ import environment, write_report
from prism_c.min_work import min_work_oracle, work_score
from prism_c.min_work_campaign import run_min_work_campaign
from prism_c.min_work_demo import min_work_demo
from prism_c.model import SearchStatus
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.selective import state_from_dict


def metrics(report):
    return {"witness": report["witness"]["digest"], "work": report["executed_score"],
            "actions": report["executed_actions"], "stage_extent_bytes": report["committed_stage_extent_bytes"],
            "failed_charged_bytes": report["ledger_final"]["Z"]["bytes"]["RETIRED"],
            "readback": all(report["readback_matches"].values()), "terminal": report["audit"]["snapshot"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="evidence/results/minimum-work-milestone-12.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    protocol = root / "experiments/minimum_work_protocol.md"
    report = {"environment": environment(), "status": "collecting", "sets": [], "actual_fixture_oracles": [],
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "timing_claimed": False, "patent_rating_changed": False}
    try:
        report["finite_campaign"] = run_min_work_campaign()
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                for seed in range(20261013, 20261016):
                    item = {"profile": profile, "workers": workers, "seed": seed, "runs": {}}
                    report["sets"].append(item)
                    variants = [("first-feasible", "conventional_cached"), ("min-work", "conventional_cached"),
                                ("min-work", "selective")]
                    offset = seed % 3
                    variants = variants[offset:] + variants[:offset]
                    item["order"] = variants
                    for planner, mode in variants:
                        key = f"{planner}:{mode}"
                        with tempfile.TemporaryDirectory(prefix="prism-min-work-") as tmp:
                            raw = min_work_demo(Path(tmp) / "store", profile, workers, mode, planner, seed)
                            item["runs"][key] = {"metrics": metrics(raw), "raw": raw}
                        write_report(args.report, report)
                    prior = item["runs"]["first-feasible:conventional_cached"]["metrics"]
                    reference = item["runs"]["min-work:conventional_cached"]["metrics"]
                    candidate = item["runs"]["min-work:selective"]["metrics"]
                    item["stage_extent_reduction_vs_first_feasible"] = 1 - reference["stage_extent_bytes"] / prior["stage_extent_bytes"]
                    item["primary_baseline_parity"] = reference == candidate
                    if not workers and seed == 20261013:
                        raw = item["runs"]["min-work:conventional_cached"]["raw"]
                        result = min_work_oracle(state_from_dict(raw["initial"]), 100000)
                        oracle = {"profile": profile, "status": result.status.value, "explored": result.explored,
                                  "reason": result.reason, "score": work_score(result.witness) if result.witness else None,
                                  "witness": result.witness.to_dict() if result.witness else None}
                        if result.status == SearchStatus.FOUND and tuple(reference["work"]) != work_score(result.witness):
                            raise AssertionError("Actual fixture objective differs from independent oracle")
                        report["actual_fixture_oracles"].append(oracle)
                    print(f"{profile} workers={workers} seed={seed}: shared stage reduction={item['stage_extent_reduction_vs_first_feasible']:.0%}; primary parity={item['primary_baseline_parity']}", flush=True)
                    write_report(args.report, report)
        report["status"] = "completed"
        report["summary"] = {"matched_sets": len(report["sets"]), "stores": len(report["sets"]) * 3,
            "primary_parity_sets": sum(i["primary_baseline_parity"] for i in report["sets"]),
            "oracle_unresolved": sum(o["status"] != "FOUND" for o in report["actual_fixture_oracles"]),
            "selective_advantage_found": any(not i["primary_baseline_parity"] for i in report["sets"]),
            "performance_confirmation_gate_passed": False}
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        write_report(args.report, report)


if __name__ == "__main__":
    main()
