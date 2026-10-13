"""Reproducible bounded contingency gate and guarded actual-byte smoke results."""

import hashlib
from pathlib import Path
import subprocess
import tempfile

from .__main__ import environment
from .contingency_campaign import run_contingency_campaign
from .contingency_demo import contingency_demo


def contingency_evidence():
    root = Path(__file__).resolve().parent.parent
    protocol = root / "experiments/contingency_protocol.md"
    report = {"environment": environment(),
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "finite": run_contingency_campaign(include_policies=True), "smoke_pairs": [],
              "timing_claimed": False, "patent_rating_changed": False}
    for workers in (False, True):
        for domain in ("D0", "X"):
            pair = {"workers": workers, "fault_domain": domain, "cursor": 2, "runs": {}}
            for mode, selector in (("conventional_cached", "conventional"), ("selective", "policy")):
                with tempfile.TemporaryDirectory(prefix="prism-contingency-") as tmp:
                    raw = contingency_demo(Path(tmp) / "store", workers, mode, domain, 2, selector)
                pair["runs"][mode] = raw
            reference = pair["runs"]["conventional_cached"]
            candidate = pair["runs"]["selective"]
            fields = ("branch", "branch_work", "failed_snapshot", "ledger_final", "audit", "readback_matches",
                      "online_replanning_calls", "branch_coverage")
            pair["equal_work_and_capability"] = all(reference[field] == candidate[field] for field in fields)
            if not pair["equal_work_and_capability"]:
                raise AssertionError("Actual cached fallback controllers differ on matched data")
            report["smoke_pairs"].append(pair)
    finite = report["finite"]
    report["summary"] = {"finite_configurations": finite["configurations"],
                         "feasible": finite["found"], "infeasible": finite["infeasible"],
                         "equal_cached_branches": finite["branch_comparisons"],
                         "budget_unknown_probes": len(finite["budget_probes"]),
                         "smoke_pairs": len(report["smoke_pairs"]), "smoke_stores": len(report["smoke_pairs"]) * 2,
                         "selective_advantage_found": False, "durable_policy_admission_implemented": False,
                         "gate_decision": "One-fault feasibility established for stated finite cases; conventional cached alternatives match. No distinguishing mechanism found."}
    report["status"] = "completed"
    return report
