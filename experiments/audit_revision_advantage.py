"""Untimed paired work-retention gate against a conventional partial replanner."""

import argparse
from collections import Counter
import hashlib
from pathlib import Path
import subprocess
import tempfile
import traceback

from prism_c.__main__ import environment, write_report
from prism_c.partial_campaign import run_partial_campaign
from prism_c.revision_demo import revision_demo


def metrics(report):
    identity = report["successor"]["id"]
    actions = [e["detail"]["action"] for e in report["events"]
               if e["kind"] == "step" and e["detail"]["plan"] == identity]
    stages = [a for a in actions if a["kind"] == "stage"]
    initial_staged = [s for s in report["initial"]["slots"] if s["status"] == "STAGED"]
    discarded = {a["slot"] for a in actions if a["kind"] == "abandon"}
    # The fixture explicitly fixes the extent size and original object sizes.
    fragment_size = 513 if report["profile"] == "xor-2+1-v1" else 257
    return {"witness_digest": report["witness"]["digest"], "committed_actions": actions,
            "action_counts": dict(Counter(a["kind"] for a in actions)),
            "retained_staged_rows": sum(s["key"] not in discarded for s in initial_staged),
            "committed_stage_extent_bytes": len(stages) * 1024,
            "committed_stage_row_bytes": len(stages) * fragment_size,
            "offline_charged_bytes": report["ledger_final"]["X"]["bytes"]["RETIRED"],
            "terminal_snapshot": report["audit"]["snapshot"],
            "exact_readback": all(report["readback_matches"].values())}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="evidence/results/revision-advantage-milestone-11.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    protocol = root / "experiments/revision_protocol.md"
    report = {"environment": environment(), "status": "collecting", "pairs": [],
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "timing_claimed": False, "patent_rating_changed": False}
    try:
        report["partial_campaign"] = run_partial_campaign()
        for profile in ("2+1", "4+2"):
            for workers in (False, True):
                for seed in range(20261012, 20261015):
                    pair = {"profile": profile, "workers": workers, "seed": seed, "runs": {}}
                    report["pairs"].append(pair)
                    order = ("conventional_cached", "selective")
                    if seed % 2:
                        order = tuple(reversed(order))
                    pair["order"] = order
                    for mode in order:
                        with tempfile.TemporaryDirectory(prefix="prism-revision-gate-") as tmp:
                            result = revision_demo(Path(tmp) / "store", profile, workers, mode, seed)
                            pair["runs"][mode] = {"metrics": metrics(result), "raw": result}
                        write_report(args.report, report)
                    left = pair["runs"]["conventional_cached"]["metrics"]
                    right = pair["runs"]["selective"]["metrics"]
                    pair["equal_capability_and_work"] = left == right
                    print(f"{profile} workers={workers} seed={seed}: equal={left == right}", flush=True)
        report["status"] = "completed"
        report["summary"] = {"pairs": len(report["pairs"]), "stores": len(report["pairs"]) * 2,
            "equal_pairs": sum(p["equal_capability_and_work"] for p in report["pairs"]),
            "differentiating_work_retention_found": any(not p["equal_capability_and_work"] for p in report["pairs"]),
            "performance_confirmation_authorized_by_gate": False}
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        raise
    finally:
        write_report(args.report, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
