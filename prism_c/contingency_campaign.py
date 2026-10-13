"""Registered finite one-additional-failure feasibility and parity matrix."""

from dataclasses import asdict, replace
from itertools import product

from .checker import check, replay
from .contingency import (conventional_cached_branches, plan_contingency, select_branch,
                         select_cached_branch)
from .contingency_check import check_policy
from .contingency_reference import contingency_oracle
from .min_work import work_score
from .model import SearchStatus, Slot, State, Stripe
from .profiles import FOUR_PLUS_TWO


def contingency_state(live=5, x_slots=1, y_slots=1, retired=False):
    sources = tuple(f"D{i}" for i in range(live))
    destinations = (("X",) if x_slots else ()) + (("Y",) if y_slots else ())
    spec = Stripe("A", sources + destinations, FOUR_PLUS_TWO)
    slots = tuple(Slot(f"{d}:0", d, "LIVE", "A", row, 1) for row, d in enumerate(sources))
    slots += tuple(Slot(f"{d}:{i}", d, "RETIRED" if retired else "FREE", incarnation=int(retired))
                   for d, n in (("X", x_slots), ("Y", y_slots)) for i in range(n))
    return State((spec,), slots)


def run_contingency_campaign(include_policies=False):
    records, comparisons, found = [], 0, 0
    for live, x, y, retired, scope in product((4, 5), range(3), range(3), (False, True), ("source-D0", "all")):
        initial = contingency_state(live, x, y, retired)
        faults = ("D0",) if scope == "source-D0" else tuple(sorted({s.domain for s in initial.slots}))
        result = plan_contingency(initial, faults)
        oracle = contingency_oracle(initial, faults)
        # For this matrix: at boundary zero a source failure leaves live-1
        # rows. Restoration needs two distinct spare domains when live=5.
        expected = live == 5 and x > 0 and y > 0
        if (result.status != oracle.status or result.status == SearchStatus.UNKNOWN
                or (result.status == SearchStatus.FOUND) != expected):
            raise AssertionError(f"Contingency feasibility mismatch: {live,x,y,retired,scope}")
        row = {"live_rows": live, "x_slots": x, "y_slots": y, "retired": retired,
               "fault_scope": scope, "fault_domains": faults, "initial": asdict(initial),
               "status": result.status.value, "oracle_status": oracle.status.value,
               "nominal_states": result.explored, "branch_searches": result.branch_checks,
               "oracle_states": oracle.explored, "reason": result.reason}
        if result.policy:
            found += 1
            policy = result.policy
            independent = check_policy(initial, policy)
            baseline_status, table = conventional_cached_branches(initial, policy.nominal, faults)
            if baseline_status != SearchStatus.FOUND:
                raise AssertionError("Conventional controller cannot cache identical feasible alternatives")
            prefix, branches = initial, []
            for cursor, action in enumerate(policy.nominal.actions):
                for domain in faults:
                    failed = replace(prefix, offline=tuple(sorted(set(prefix.offline) | {domain})))
                    candidate = select_branch(policy, cursor, domain, failed)
                    conventional = select_cached_branch(table, cursor, domain, failed)
                    if candidate != conventional or check(failed, candidate) != check(failed, conventional):
                        raise AssertionError("Cached branch capability/work disagreement")
                    comparisons += 1
                    branches.append({"cursor": cursor, "domain": domain, "initial": failed.fingerprint(),
                                     "work": work_score(candidate), "terminal": candidate.terminal,
                                     "equal_witness": True, "online_replanning_calls": {"policy": 0, "conventional": 0}})
                prefix = replay(prefix, (action,), False)
            row.update(branch_count=independent["branch_count"], branches=branches,
                       checked_actions=independent["checked_actions"], nominal=policy.nominal.to_dict(),
                       policy_digest=policy.digest(), conventional_parity=True)
            if include_policies:
                row["policy"] = policy.to_dict()
        records.append(row)
    positive = contingency_state()
    faults = tuple(sorted({s.domain for s in positive.slots}))
    limits = []
    for label, kwargs in (("nominal", {"max_states": 1}), ("branch", {"branch_budget": 1}),
                          ("coverage", {"max_branch_checks": 1})):
        result = plan_contingency(positive, faults, **kwargs)
        if result.status != SearchStatus.UNKNOWN or result.policy is not None:
            raise AssertionError("Budget exhaustion yielded an admitted policy or false infeasibility")
        limits.append({"budget": label, "status": result.status.value, "policy_present": False})
    return {"configurations": len(records), "found": found, "infeasible": len(records) - found,
            "unknown_in_matrix": 0, "budget_probes": limits, "branch_comparisons": comparisons,
            "disagreements": 0, "cases": records, "selective_advantage_found": False,
            "scope": "Single 4+2 stripe; 4/5 live rows; 0/1/2 slots in each of X/Y; free/retired; one declared fault"}
