"""Documented continuation; the original measurement implementation is unchanged."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import traceback

from prism_c.__main__ import environment, write_report
from prism_c.benchmark import paired_effect
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.snapshot_latency import APIS, PROTOCOL, inflation_summary, latency_window, warmup

ROOT = Path(__file__).resolve().parent.parent
SUPPLEMENT = ROOT / "experiments/snapshot_latency_continuation_protocol.md"


def canonical_sha256(report):
    return hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_pair(pair, profile, workers, run, seed, order):
    if pair["run"] != run or pair["seed"] != seed + run or pair["order"] != order or set(pair["attempts"]) != set(APIS):
        raise ValueError("Retained pair identity/order differs from registration")
    fingerprints = set()
    for api, window in pair["attempts"].items():
        fg = window["foreground"]
        if (window["api"], window["profile"], window["storage_workers"], window["seed"]) != (api, profile, workers, seed + run):
            raise ValueError("Retained window identity differs")
        if not fg["healthy"] or not fg["sufficient"] or fg["errors"] or not window["completed_group_targets_and_all_readbacks_match"]:
            raise ValueError("Retained window did not pass integrity")
        for phase, name in ((0, "control"), (1, "loaded")):
            rows = [r for r in fg["requests"] if r["phase"] == phase]
            if len(rows) != 400 or sorted(r["request"] for r in rows) != list(range(400)) or any(r["error"] for r in rows):
                raise ValueError("Retained window has missing/failed/duplicate requests")
            if fg[name]["successes"] != 400 or fg[name]["p99_ns"] is None:
                raise ValueError("Retained window has insufficient metrics")
        fingerprints.add(window["initial_backlog"])
    if len(fingerprints) != 1:
        raise ValueError("Retained initial stores differ")


def load_original(path):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if report["status"] != "failed" or report["runs"] < 10:
        raise ValueError("Continuation requires the preserved failed registered campaign")
    if hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() != report["protocol_sha256"]:
        raise ValueError("Original protocol changed")
    for name, expected in report["environment"]["source_sha256"].items():
        target = (ROOT / name).resolve()
        if not target.is_relative_to(ROOT) or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            raise ValueError("Originally recorded source changed: " + name)
    return report


def complete(original, checkpoint=None):
    report = {"status": "running", "original_campaign_status": original["status"],
              "original_error": original.get("error"), "original_active_attempt": original.get("active_attempt"),
              "original_canonical_json_sha256": canonical_sha256(original),
              "original_environment": original["environment"], "environment": environment(),
              "original_protocol_sha256": original["protocol_sha256"],
              "supplement_protocol_sha256": hashlib.sha256(SUPPLEMENT.read_bytes()).hexdigest(),
              "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "supplemented_collection": True, "uninterrupted_original_confirmation": False,
              "seed": original["seed"], "runs": original["runs"], "configurations": [], "warmups": [],
              "telemetry_errors": [], "selective_advantage_established": False,
              "research_gate_passed": False, "patent_rating_changed": False}
    rng = random.Random(original["seed"])
    def save():
        if checkpoint:
            checkpoint(report)
    try:
        index = 0
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                prior = original["configurations"][index] if index < len(original["configurations"]) else {"pairs": []}
                if prior["pairs"] and (prior["profile"], prior["storage_workers"]) != (profile, workers):
                    raise ValueError("Original configuration order differs")
                cfg = {"profile": profile, "storage_workers": workers, "pairs": []}
                report["configurations"].append(cfg)
                usable, warmed = [], False
                for run in range(original["runs"]):
                    order = list(APIS)
                    rng.shuffle(order)
                    old_pair = next((p for p in prior["pairs"] if p["run"] == run), None)
                    report["active_attempt"] = {"configuration": index, "run": run, "phase": "retained_validation"}
                    if old_pair and old_pair["status"] == "completed":
                        validate_pair(old_pair, profile, workers, run, original["seed"], order)
                        cfg["pairs"].append({"run": run, "status": "completed", "retained_original_pair": True,
                                             "original_configuration_index": index})
                        usable.append(old_pair)
                    else:
                        if not warmed:
                            report["active_attempt"]["phase"] = "warmup"
                            for api in APIS:
                                report["warmups"].append(warmup(profile, workers, original["seed"], api))
                            warmed = True
                        pair = {"run": run, "seed": original["seed"] + run, "order": order,
                                "attempts": {}, "status": "running", "retained_original_pair": False}
                        cfg["pairs"].append(pair)
                        for api in order:
                            report["active_attempt"].update(phase="window", api=api)
                            pair["attempts"][api] = latency_window(profile, workers, original["seed"] + run, api)
                            report["active_attempt"]["phase"] = "checkpoint"
                            save()
                        validate_pair(pair, profile, workers, run, original["seed"], order)
                        pair["status"] = "completed"
                        usable.append(pair)
                        report["active_attempt"]["phase"] = "checkpoint"
                        save()
                        try:
                            print(f"Snapshot continuation: {profile}, workers={workers}, pair={run + 1}/{original['runs']}", flush=True)
                        except OSError as error:
                            report["telemetry_errors"].append(repr(error))
                    report["active_attempt"]["phase"] = "analysis"
                before = [p["attempts"]["read"]["foreground"]["loaded"]["p99_ns"] for p in usable]
                after = [p["attempts"]["read_snapshot"]["foreground"]["loaded"]["p99_ns"] for p in usable]
                effect = paired_effect(after, before, original["seed"])
                effect["mean_percent_p99_reduction"] = effect.pop("mean_percent_cpu_reduction")
                cfg["snapshot_vs_serialized_loaded_p99"] = effect
                cfg["inflation"] = {api: inflation_summary([p["attempts"][api]["foreground"]["loaded_control_p99_ratio"]
                                                            for p in usable], original["seed"]) for api in APIS}
                index += 1
        report["status"] = "completed"
        report.pop("active_attempt", None)
    except Exception as error:
        report["status"], report["error"], report["traceback"] = "failed", repr(error), traceback.format_exc()
    save()
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    if Path(args.original).resolve() == Path(args.report).resolve():
        raise ValueError("Continuation must not overwrite the original report")
    original = load_original(args.original)
    def checkpoint(report):
        write_report(args.report, {"original_report": Path(args.original).resolve().relative_to(ROOT).as_posix(), **report})
    result = complete(original, checkpoint)
    try:
        print(json.dumps({"status": result["status"], "report": str(Path(args.report).resolve())}))
    except OSError as error:
        result["telemetry_errors"].append(repr(error))
        checkpoint(result)
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
