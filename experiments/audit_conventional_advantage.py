"""Untimed mechanism audit: determine whether suffix replay is avoidable.

Uses the independent checker and real authority APIs. This is not another
performance experiment and does not change production authority or caches.
"""

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import traceback
from unittest.mock import patch

from prism_c.__main__ import environment, write_report
from prism_c.baseline import conventional_plan
from prism_c.checker import replay
from prism_c.controller_benchmark import _fixture
from prism_c.model import Rejected, Slot, State, Stripe, fixture
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.selective import ContinuationCache, WholeSuffixCache
from prism_c.storage import Authority
from prism_c import worker_authority


def logical_case(profile, count):
    sources = ("D0", "D1") if profile == DEFAULT_PROFILE else ("D0", "D1", "D2", "D3")
    rows = (0, 1) if profile == DEFAULT_PROFILE else (0, 2, 4, 5)
    destinations = ("X",) if profile == DEFAULT_PROFILE else ("X", "Y")
    stripes = tuple(Stripe(f"stripe-{i}", sources + destinations, profile) for i in range(count))
    slots = tuple(Slot(f"{domain}:{i}", domain, "LIVE", spec.name, row, 1)
                  for i, spec in enumerate(stripes) for domain, row in zip(sources, rows))
    slots += tuple(Slot(f"{domain}:{i}", domain, "RETIRED" if i < count // 2 else "FREE",
                        incarnation=1 if i < count // 2 else 0)
                   for domain in destinations for i in range(count))
    state = State(stripes, slots)
    witness = conventional_plan(state)
    if witness is None:
        raise AssertionError("Audit fixture infeasible")
    caches = {"conventional_cached": WholeSuffixCache.build(state, witness),
              "selective": ContinuationCache.build(state, witness)}
    records = []
    for cursor, action in enumerate(witness.actions):
        # Fresh equal records avoid object-identity shortcuts.
        before = replace(state, stripes=tuple(replace(s) for s in state.stripes),
                         slots=tuple(replace(s) for s in state.slots))
        reference = replay(before, witness.actions[cursor:])
        row = {"cursor": cursor, "action": action.kind, "modes": {}}
        after = replay(before, (action,), require_target=False)
        for mode, cache in caches.items():
            if cache.validate(before, witness, cursor) != reference:
                raise AssertionError("Cache disagrees with independent suffix replay")
            row["modes"][mode] = dict(cache.last_stats)
            cache.advance(before, after, action)
        records.append(row)
        state = after
    if not state.target() or state.fingerprint() != witness.terminal:
        raise AssertionError("Audit terminal differs")
    return {"profile": profile, "stripes": count, "steps": records,
            "conventional_guard_hits": sum(r["modes"]["conventional_cached"]["guard_reused"] for r in records),
            "conventional_replayed_suffix_actions": sum(r["modes"]["conventional_cached"]["replayed_actions"] for r in records),
            "selective_replayed_suffix_actions": sum(r["modes"]["selective"]["replayed_actions"] for r in records),
            "terminal_matches_reference": True}


def admit_pair(store, fence, profile):
    for index in range(2):
        name = f"stripe-{index:02d}"
        destinations = (f"X:{index}",) if profile == DEFAULT_PROFILE else (f"X:{index}", f"Y:{index}")
        witness = conventional_plan(store.snapshot_for((name,), destinations))
        store.admit_scoped(witness, (name,), destinations, fence, name)


def durable_case(profile, workers, mode, seed):
    with tempfile.TemporaryDirectory(prefix="prism-advantage-audit-") as tmp:
        store, fence, contents, _ = _fixture(Path(tmp) / "store", 2, profile, workers, seed, mode)
        admit_pair(store, fence, profile)
        store.set_offline("F0", fence)  # Outside both scopes; foreground remains decodable, degraded.
        preparation = []
        original = worker_authority.replay
        def observed(state, actions, require_target=True):
            if require_target:
                preparation.append({"suffix_actions": len(actions), "state": state.fingerprint()})
            return original(state, actions, require_target)
        records, transferred = [], False
        with patch.object(worker_authority, "replay", observed):
            while store.active_plans():
                for plan in ("stripe-00", "stripe-01"):
                    if store.plan_info(plan)["status"] != "ACTIVE":
                        continue
                    store.annotate("audit", "annotation outside logical authority", fence)
                    store.step(plan, fence)
                    step = [event["detail"] for event in store.events() if event["kind"] == "step"][-1]
                    records.append({"plan": plan, "cursor": step["step"], "action": step["action"]["kind"],
                                    "validation": step["validation"]})
                    if not transferred:
                        fence = store.takeover()
                        store = Authority(store.root, mode)
                        transferred = True
        snapshot = store.snapshot_for(("stripe-00", "stripe-01"), ())
        if not snapshot.target() or store.active_plans():
            raise AssertionError("Selected scopes did not restore")
        if any(store.read_snapshot(name) != content for name, content in contents.items()):
            raise AssertionError("Authenticated content differs")
        return {"profile": profile, "workers": workers, "mode": mode, "seed": seed,
                "annotations": len(records), "outside_scope_offline_domain": "F0", "takeover_and_reopen": transferred,
                "steps": records, "worker_preparation_suffix_calls": preparation,
                "selected_scopes_restored": True, "all_contents_match": True,
                "whole_store_target": store.audit()["target"],
                "whole_store_target_explanation": "F0 belongs to unrelated foreground stripe; its outage deliberately leaves that stripe degraded"}


def failure_case(profile, mode, seed):
    with tempfile.TemporaryDirectory(prefix="prism-advantage-failure-") as tmp:
        store, fence, contents, _ = _fixture(Path(tmp) / "store", 2, profile, False, seed, mode)
        admit_pair(store, fence, profile)
        store.step("stripe-00", fence)  # Reclaim first retired destination.
        before = store.plan_info("stripe-00")["cursor"]
        store.set_offline("X", fence)  # Still decodable, but committed destination is unavailable.
        try:
            store.step("stripe-00", fence)
        except Rejected as error:
            reason = str(error)
        else:
            raise AssertionError("Failed destination unexpectedly authorized continuation")
        after = store.plan_info("stripe-00")["cursor"]
        if before != after or store.read_snapshot("stripe-00") != contents["stripe-00"]:
            raise AssertionError("Failed continuation changed cursor or original bytes")
        return {"profile": profile, "mode": mode, "event": "in-scope destination X offline",
                "rejected": True, "reason": reason, "cursor_before": before, "cursor_after": after,
                "original_content_still_decodable": True}


def benign_policy_case():
    state = fixture(reclamation=True)
    witness = conventional_plan(state)
    state = replay(state, witness.actions[:1], require_target=False)
    changed = replace(state, stripes=(state.stripes[0], replace(state.stripes[1],
                      eligible=state.stripes[1].eligible + ("EXTRA",))))
    terminal = replay(changed, witness.actions[1:])
    results = {}
    for mode, kind in (("conventional_cached", WholeSuffixCache), ("selective", ContinuationCache)):
        cache = kind.build(state, witness, 1)
        try:
            cache.validate(changed, witness, 1)
        except Rejected as error:
            results[mode] = {"rejected": True, "reason": str(error), "stats": dict(cache.last_stats)}
        else:
            raise AssertionError("Changed policy bypassed exact terminal commitment")
    return {"event": "Expand B eligibility; no placements or bytes changed",
            "independent_suffix_replay_reaches_target": terminal.target(),
            "exact_terminal_commitment_differs": terminal.fingerprint() != witness.terminal,
            "scope": "Logical mutation probe; production has no eligibility-update API",
            "modes": results}


def audit(seed=20261012, checkpoint=None):
    report = {"status": "running", "kind": "untimed mechanism audit, not a performance campaign",
              "environment": environment(), "seed": seed,
              "production_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "logical_cases": [], "durable_cases": [], "destination_failure_cases": [],
              "performance_advantage_established": False, "patent_rating_changed": False}
    def save():
        if checkpoint:
            checkpoint(report)
    try:
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for count in (2, 8, 16):
                report["logical_cases"].append(logical_case(profile, count))
                save()
            for workers in (False, True):
                for mode in ("conventional_cached", "selective"):
                    report["durable_cases"].append(durable_case(profile, workers, mode, seed))
                    save()
            for mode in ("conventional_cached", "selective"):
                report["destination_failure_cases"].append(failure_case(profile, mode, seed))
                save()
        report["benign_policy_case"] = benign_policy_case()
        report["summary"] = {
            "logical_steps": sum(len(c["steps"]) for c in report["logical_cases"]),
            "conventional_logical_guard_hits": sum(c["conventional_guard_hits"] for c in report["logical_cases"]),
            "conventional_logical_suffix_actions_replayed": sum(c["conventional_replayed_suffix_actions"] for c in report["logical_cases"]),
            "selective_logical_suffix_actions_replayed": sum(c["selective_replayed_suffix_actions"] for c in report["logical_cases"]),
            "durable_steps": sum(len(c["steps"]) for c in report["durable_cases"]),
            "conventional_durable_guard_hits": sum(s["validation"].get("guard_reused", False)
                for c in report["durable_cases"] if c["mode"] == "conventional_cached" for s in c["steps"]),
            "durable_suffix_actions_replayed_at_completion": sum(s["validation"]["replayed_actions"]
                for c in report["durable_cases"] for s in c["steps"]),
            "worker_preparation_full_suffix_calls": sum(len(c["worker_preparation_suffix_calls"]) for c in report["durable_cases"])}
        report["status"] = "completed"
    except Exception:
        report.update(status="failed", error=traceback.format_exc())
    save()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="evidence/results/conventional-advantage-audit.json")
    parser.add_argument("--seed", type=int, default=20261012)
    args = parser.parse_args()
    result = audit(args.seed, lambda value: write_report(args.report, value))
    print(json.dumps({"report": str(Path(args.report).resolve()), "status": result["status"],
                      "summary": result.get("summary"), "error": result.get("error")}, indent=2))
    raise SystemExit(0 if result["status"] == "completed" else 1)
