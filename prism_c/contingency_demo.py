"""Guarded smoke test using existing scoped claims and checked revisions.

This does not add a durable policy-admission API or a new production guarantee.
"""

from dataclasses import asdict
import random

from .contingency import (conventional_cached_branches, plan_contingency, select_branch,
                         select_cached_branch)
from .contingency_check import check_policy
from .controller_benchmark import FOREGROUND
from .min_work import work_score
from .model import Rejected, SearchStatus
from .profiles import FOUR_PLUS_TWO
from .storage import Authority


def contingency_demo(root, workers=False, mode="conventional_cached", domain="D0", cursor=2,
                     selector="policy", seed=20261013):
    capacities = {f"D{i}": 1 for i in range(5)}
    capacities.update(X=1, Y=1, F0=1, F1=1, F2=1)
    store = Authority.create(root, capacities, 1024)
    store = Authority(root, mode)
    fence = store.takeover()
    contents = {"A": random.Random(seed).randbytes(1025), "foreground": FOREGROUND}
    domains = tuple(f"D{i}" for i in range(5)) + ("X", "Y")
    store.bootstrap("A", contents["A"], {i: f"D{i}" for i in range(5)}, domains, fence, FOUR_PLUS_TWO)
    store.bootstrap("foreground", FOREGROUND, {0: "F0", 1: "F1", 2: "F2"}, ("F0", "F1", "F2"), fence)
    if workers:
        store.enable_workers(fence)
    targets = ("X:0", "Y:0")
    initial = store.snapshot_for(("A",), targets)
    result = plan_contingency(initial, domains)
    if result.status != SearchStatus.FOUND:
        raise AssertionError(result.reason)
    policy = result.policy
    checks = check_policy(initial, policy)
    status, conventional = conventional_cached_branches(initial, policy.nominal, domains)
    if status != SearchStatus.FOUND or not 0 <= cursor < len(policy.nominal.actions) or domain not in domains:
        raise Rejected("Smoke test needs a covered failure before nominal completion")
    store.admit_scoped(policy.nominal, ("A",), targets, fence, "root")
    # The unused spare is already exclusively claimed. An unrelated full
    # foreground witness cannot acquire it even before the first repair action.
    try:
        from .min_work import conventional_min_work_plan
        foreign = conventional_min_work_plan(store.snapshot_for(("foreground",), ("Y:0",))).witness
        store.admit_scoped(foreign, ("foreground",), ("Y:0",), fence, "steal-spare")
    except Rejected as error:
        rejected = str(error)
    else:
        raise AssertionError("Unrelated admission stole a held contingency spare")
    for _ in range(cursor):
        store.step("root", fence)
    store.set_offline(domain, fence)
    actual = store.revision_snapshot("root", targets, fence)
    witness = (select_branch(policy, cursor, domain, actual) if selector == "policy" else
               select_cached_branch(conventional, cursor, domain, actual))
    successor = store.revise("root", witness, targets, fence, "one-fault", policy.nominal.digest())
    store.execute(successor, fence)
    matches = {name: store.read_snapshot(name) == data for name, data in contents.items()}
    if not all(matches.values()) or not store.audit()["target"] or store.active_plans():
        raise AssertionError("Covered fault did not complete exact restoration")
    return {"scope": "Existing trusted local authority; client-checked policy; simulated domain failure",
            "workers": workers, "validation_mode": mode, "selector": selector,
            "failure": {"cursor": cursor, "domain": domain}, "policy": policy.to_dict(),
            "initial": asdict(initial), "failed_snapshot": asdict(actual), "branch": witness.to_dict(),
            "branch_work": work_score(witness), "branch_coverage": checks["branch_count"],
            "online_replanning_calls": 0, "spare_stealing_rejected": rejected,
            "audit": store.audit(), "ledger_final": store.ledger(), "events": store.events(),
            "readback_matches": matches, "durable_policy_admission_implemented": False,
            "patent_rating_changed": False, "performance_advantage_claimed": False}
