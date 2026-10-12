"""Reproducible CLI for demonstrations and correctness evidence."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sqlite3
import sys
import time
import unittest

from . import __version__
from .baseline import conventional_plan
from .benchmark import benchmark
from .campaign import run_campaign
from .coding_campaign import run_coding_campaign
from .checker import check
from .profiles import FOUR_PLUS_TWO
from .model import Rejected, SearchStatus, fixture, plan
from .storage import Authority


def write_report(path, report):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def environment():
    root = Path(__file__).resolve().parent.parent
    sources = {}
    for folder in ("prism_c", "tests"):
        for path in sorted((root / folder).glob("*.py")):
            sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"utc": datetime.now(timezone.utc).isoformat(), "version": __version__,
            "python": sys.version, "sqlite": sqlite3.sqlite_version,
            "platform": platform.platform(), "source_sha256": sources}


def demo(args):
    authority = Authority.create(args.root, {"S": 2, "T": 2, "X": 1, "Y": 1}, 128)
    authority = Authority(authority.root, validation_mode=args.validation_mode)
    fence = authority.takeover()
    contents = {"A": b"immutable object A with an odd length!", "B": b"immutable object B"}
    authority.bootstrap("A", contents["A"], {0: "S", 1: "T"}, ("S", "T", "X", "Y"), fence)
    authority.bootstrap("B", contents["B"], {0: "S", 1: "T"}, ("S", "T", "X"), fence)
    authority.seed_retired("X", fence)
    initial = authority.snapshot()
    candidate = plan(initial)
    if candidate.status != SearchStatus.FOUND:
        raise RuntimeError(candidate.reason)
    baseline = conventional_plan(initial)
    check(initial, candidate.witness)
    check(initial, baseline)
    initial_ledger = authority.ledger()
    identifier = authority.admit(candidate.witness, fence, "demo-plan")
    trace = [{"event": "admitted", "ledger": authority.ledger(), "state": asdict(authority.snapshot())}]
    while authority.plan_info(identifier)["status"] == "ACTIVE":
        result = authority.step(identifier, fence)
        trace.append({"event": "step", "result": result, "ledger": authority.ledger(),
                      "state": asdict(authority.snapshot())})
    reopened = Authority(authority.root)
    content_matches = {name: reopened.read(name) == content for name, content in contents.items()}
    if not all(content_matches.values()):
        raise AssertionError("Demonstration lost content")
    report = {"environment": environment(), "scope": "Local trusted single-authority prototype; simulated domains",
              "initial": asdict(initial), "initial_ledger": initial_ledger,
              "planner_states_explored": candidate.explored, "witness": candidate.witness.to_dict(),
              "conventional_baseline_witness": baseline.to_dict(), "trace": trace,
              "audit": reopened.audit(), "readback_matches": content_matches, "events": reopened.events(),
              "patent_rating_changed": False, "performance_advantage_claimed": False}
    write_report(args.report, report)
    print(json.dumps({"report": str(Path(args.report).resolve()), "audit": report["audit"],
                      "readback_matches": content_matches, "planner_states_explored": candidate.explored}, indent=2))


def concurrent_demo(args):
    authority = Authority.create(args.root, {"S": 2, "T": 2, "X": 1, "Y": 1}, 128)
    authority = Authority(authority.root, args.validation_mode)
    fence = authority.takeover()
    contents = {"A": b"immutable object A with an odd length!", "B": b"immutable object B"}
    authority.bootstrap("A", contents["A"], {0: "S", 1: "T"}, ("S", "T", "X", "Y"), fence)
    authority.bootstrap("B", contents["B"], {0: "S", 1: "T"}, ("S", "T", "X"), fence)
    authority.seed_retired("X", fence)
    initial = authority.snapshot()
    witnesses = {}
    if getattr(args, "storage_workers", False):
        authority.enable_workers(fence)
    for name, destination in (("A", "Y:0"), ("B", "X:0")):
        state = authority.snapshot_for((name,), (destination,))
        witness = conventional_plan(state)
        if witness is None:
            raise AssertionError("Demonstration scope unexpectedly infeasible")
        witnesses[name] = witness.to_dict()
        authority.admit_scoped(witness, (name,), (destination,), fence, name)
    admitted = {name: authority.plan_info(name) for name in contents}
    rejected = []
    candidate = conventional_plan(authority.snapshot_for(("A",), ("X:0",)))
    try:
        authority.admit_scoped(candidate, ("A",), ("X:0",), fence, "conflict")
    except Rejected as error:
        rejected.append({"operation": "conflicting admission", "reason": str(error)})
    else:
        raise AssertionError("Conflicting admission was accepted")
    retired = next(slot for slot in authority.snapshot().slots if slot.key == "X:0")
    try:
        authority.cleanup(retired.key, retired.incarnation, fence)
    except Rejected as error:
        rejected.append({"operation": "cleanup of claimed retired destination", "reason": str(error)})
    else:
        raise AssertionError("Claimed retired destination was externally reclaimed")
    trace = [{"event": "both admitted", "active_plans": [p["id"] for p in authority.active_plans()],
              "ledger": authority.ledger(), "state": asdict(authority.snapshot())}]
    # A: reserve/stage/promote; B: reclaim/reserve/stage/promote.
    schedule = ("A", "B", "B", "A", "B", "A", "B")
    for name in schedule:
        result = authority.step(name, fence)
        authority.audit()
        trace.append({"event": "step", "plan": name, "result": result,
                      "active_plans": [p["id"] for p in authority.active_plans()],
                      "ledger": authority.ledger(), "state": asdict(authority.snapshot())})
        authority = Authority(authority.root, args.validation_mode)
    matches = {name: authority.read(name) == data for name, data in contents.items()}
    audit = authority.audit()
    if not all(matches.values()) or not audit["target"] or authority.active_plans():
        raise AssertionError("Concurrent demonstration did not restore all original bytes")
    report = {"environment": environment(),
              "scope": ("Two disjoint whole-stripe continuations, local authority, separate repair-I/O processes"
                        if getattr(args, "storage_workers", False) else
                        "Two disjoint whole-stripe continuations, local serialized authority and byte I/O"),
              "validation_mode": args.validation_mode, "initial": asdict(initial),
              "admitted_plans": admitted, "conventional_scoped_witnesses": witnesses,
              "rejections": rejected, "schedule": schedule, "trace": trace,
              "audit": audit, "readback_matches": matches, "events": authority.events(),
              "patent_rating_changed": False, "performance_advantage_claimed": False,
              "independent_storage_agents_implemented": bool(getattr(args, "storage_workers", False)),
              "worker_receipts": [event["detail"]["receipt"] for event in authority.events()
                                  if event["kind"] == "worker_ack"]}
    write_report(args.report, report)
    print(json.dumps({"report": str(Path(args.report).resolve()), "audit": audit,
                      "readback_matches": matches, "rejected_conflicts": len(rejected)}, indent=2))


def four_plus_two_demo(args):
    capacities = {f"D{i}": 2 for i in range(4)}
    capacities.update(X=1, Y=1, Z=1)
    authority = Authority.create(args.root, capacities, 128)
    authority = Authority(authority.root, args.validation_mode)
    fence = authority.takeover()
    contents = {"A": bytes(range(256)) + b"4+2 mixed-profile demonstration\x00",
                "B": b"legacy 2+1 object"}
    authority.bootstrap("A", contents["A"], {0: "D0", 2: "D1", 4: "D2", 5: "D3"},
                        ("D0", "D1", "D2", "D3", "X", "Y"), fence, FOUR_PLUS_TWO)
    authority.bootstrap("B", contents["B"], {0: "D0", 1: "D1"}, ("D0", "D1", "Z"), fence)
    authority.seed_retired("X", fence)
    authority.enable_workers(fence)
    initial = authority.snapshot()
    witnesses = {}
    for name, destinations in (("A", ("X:0", "Y:0")), ("B", ("Z:0",))):
        state = authority.snapshot_for((name,), destinations)
        witness = conventional_plan(state)
        if witness is None:
            raise AssertionError("4+2 demonstration unexpectedly infeasible")
        check(state, witness)
        authority.admit_scoped(witness, (name,), destinations, fence, name)
        witnesses[name] = witness.to_dict()
    trace = [{"event": "admitted", "ledger": authority.ledger(), "state": asdict(authority.snapshot())}]
    # A repairs missing DATA rows 1 and 3 from authentic rows 0,2,4,5.
    schedule = ("A", "B", "A", "B", "A", "B", "A", "A", "A", "A")
    for name in schedule:
        result = authority.step(name, fence)
        authority.audit()
        trace.append({"event": "step", "plan": name, "result": result,
                      "ledger": authority.ledger(), "state": asdict(authority.snapshot())})
        authority = Authority(authority.root, args.validation_mode)
    matches = {name: authority.read(name) == data for name, data in contents.items()}
    audit = authority.audit()
    if not all(matches.values()) or not audit["target"] or authority.active_plans():
        raise AssertionError("4+2 mixed-profile demonstration lost data")
    report = {"environment": environment(), "scope": "Local mixed 4+2 and 2+1 scopes with separate repair workers",
              "profile": FOUR_PLUS_TWO, "initial_42_rows": [0, 2, 4, 5], "repaired_42_rows": [1, 3],
              "validation_mode": args.validation_mode, "initial": asdict(initial),
              "witnesses": witnesses, "schedule": schedule, "trace": trace,
              "audit": audit, "readback_matches": matches, "events": authority.events(),
              "worker_receipts": [event["detail"]["receipt"] for event in authority.events()
                                  if event["kind"] == "worker_ack"],
              "patent_rating_changed": False, "performance_advantage_claimed": False}
    write_report(args.report, report)
    print(json.dumps({"report": str(Path(args.report).resolve()), "audit": audit,
                      "readback_matches": matches, "repaired_42_rows": [1, 3]}, indent=2))


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.subtests = 0

    def startTest(self, test):
        self.started = time.perf_counter()
        self.subtest_failed = False
        super().startTest(test)

    def stopTest(self, test):
        failed = self.subtest_failed or any(t is test for t, _ in self.failures + self.errors)
        self.records.append({"test": test.id(), "seconds": time.perf_counter() - self.started,
                             "status": "FAIL" if failed else "PASS"})
        super().stopTest(test)

    def addSubTest(self, test, subtest, err):
        self.subtests += 1
        if err is not None:
            self.subtest_failed = True
            self.records.append({"subtest": str(subtest), "status": "FAIL", "error": str(err[1])})
        super().addSubTest(test, subtest, err)


def verify(args):
    root = Path(__file__).resolve().parent.parent
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), top_level_dir=str(root))
    started = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
    campaign = None
    campaign_error = None
    coding_campaign = None
    if result.wasSuccessful():
        try:
            campaign = run_campaign(args.traces, args.seed)
            coding_campaign = run_coding_campaign(args.seed)
        except Exception as error:
            campaign_error = repr(error)
    report = {"environment": environment(), "success": result.wasSuccessful() and campaign is not None and coding_campaign is not None,
              "test_methods": result.testsRun, "subtests": result.subtests,
              "failures": len(result.failures), "errors": len(result.errors), "tests": result.records,
              "campaign": campaign, "campaign_error": campaign_error,
              "coding_campaign": coding_campaign,
              "total_seconds": time.perf_counter() - started,
              "limitations": ["Finite-model correctness is not an unbounded proof",
                               "Process exits are not power-loss tests",
                               "No comparative performance or novelty result is established"]}
    write_report(args.report, report)
    print(json.dumps({"report": str(Path(args.report).resolve()), "success": report["success"],
                      "test_methods": result.testsRun, "campaign": campaign,
                      "coding_campaign": coding_campaign}, indent=2))
    return 0 if report["success"] else 1


def operate(args):
    authority = Authority(args.root, validation_mode=args.validation_mode)
    if args.command == "status":
        value = {"ledger": authority.ledger(), "state": asdict(authority.snapshot()),
                 "audit": authority.audit(),
                 "active_plans": [{k: p[k] for k in ("id", "cursor", "status", "fence")}
                                  for p in authority.active_plans()]}
        if args.plan:
            value["plan"] = authority.plan_info(args.plan)
    else:
        fence = authority.takeover() if args.takeover else args.fence
        if fence is None:
            raise ValueError("Specify --fence or --takeover")
        if args.command == "resume":
            authority.execute(args.plan, fence)
        else:
            authority.cancel(args.plan, fence)
        value = {"plan": authority.plan_info(args.plan), "fence": fence,
                 "ledger": authority.ledger(), "audit": authority.audit()}
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


def main():
    parser = argparse.ArgumentParser(prog="python -m prism_c")
    commands = parser.add_subparsers(dest="command", required=True)
    demonstration = commands.add_parser("demo", help="Run the real-byte reclamation/repair demonstration")
    demonstration.add_argument("--root", required=True, help="Empty directory for persistent prototype state")
    demonstration.add_argument("--report", default="evidence/results/demo.json")
    demonstration.add_argument("--validation-mode", default="conventional_cached",
                               choices=("conventional_cached", "selective", "full", "shadow"))
    concurrent = commands.add_parser("concurrent-demo", help="Demonstrate disjoint active plans and conflict rejection")
    concurrent.add_argument("--root", required=True, help="Empty directory for persistent prototype state")
    concurrent.add_argument("--report", default="evidence/results/concurrent-demo.json")
    concurrent.add_argument("--validation-mode", default="conventional_cached",
                            choices=("conventional_cached", "selective", "full", "shadow"))
    concurrent.add_argument("--storage-workers", action="store_true",
                            help="Run stage/reclaim in separate processes outside the authority writer transaction")
    larger = commands.add_parser("four-plus-two-demo", help="Restore missing data rows in a mixed-profile worker store")
    larger.add_argument("--root", required=True, help="New/empty directory for persistent state")
    larger.add_argument("--report", default="evidence/results/four-plus-two-demo.json")
    larger.add_argument("--validation-mode", default="conventional_cached",
                        choices=("conventional_cached", "selective", "full", "shadow"))
    validation = commands.add_parser("verify", help="Run unit/integration/crash tests and seeded model traces")
    validation.add_argument("--report", default="evidence/results/verification.json")
    validation.add_argument("--traces", type=int, default=10_000)
    validation.add_argument("--seed", type=int, default=20261011)
    status = commands.add_parser("status", help="Inspect an existing prototype store")
    status.add_argument("--root", required=True)
    status.add_argument("--plan")
    status.add_argument("--validation-mode", default="conventional_cached",
                        choices=("conventional_cached", "selective", "full", "shadow"))
    comparison = commands.add_parser("benchmark", help="Compare logical full/selective/conventional cached validation")
    comparison.add_argument("--report", default="evidence/results/selective-benchmark.json")
    comparison.add_argument("--runs", type=int, default=10)
    comparison.add_argument("--seed", type=int, default=20261011)
    for name in ("resume", "cancel"):
        operation = commands.add_parser(name, help=f"{name.capitalize()} an existing admitted plan")
        operation.add_argument("--root", required=True)
        operation.add_argument("--plan", required=True)
        operation.add_argument("--validation-mode", default="conventional_cached",
                               choices=("conventional_cached", "selective", "full", "shadow"))
        ownership = operation.add_mutually_exclusive_group(required=True)
        ownership.add_argument("--fence", type=int)
        ownership.add_argument("--takeover", action="store_true", help="Advance the owner fence before operation")
    args = parser.parse_args()
    if args.command == "demo":
        demo(args)
        return 0
    if args.command == "concurrent-demo":
        concurrent_demo(args)
        return 0
    if args.command == "four-plus-two-demo":
        four_plus_two_demo(args)
        return 0
    if args.command == "verify":
        return verify(args)
    if args.command == "benchmark":
        report = {"environment": environment(), **benchmark(args.runs, args.seed)}
        write_report(args.report, report)
        print(json.dumps({"report": str(Path(args.report).resolve()),
            "comparisons": [{"stripes": c["stripes"], "annotations": c["annotations"],
                             "selective_vs_full_percent": c["selective_vs_full"]["mean_percent_cpu_reduction"],
                             "selective_vs_cached_percent": c["selective_vs_conventional_cached"]["mean_percent_cpu_reduction"]}
                            for c in report["configurations"]]}, indent=2))
        return 0
    return operate(args)


if __name__ == "__main__":
    raise SystemExit(main())
