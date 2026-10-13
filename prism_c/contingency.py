"""Finite robust root search and exact-snapshot cached fallback policies."""

from collections import deque
from dataclasses import asdict, dataclass, replace
import hashlib
import json

from .checker import check
from .contingency_check import check_policy
from .min_work import conventional_min_work_plan
from .model import Action, Rejected, SearchStatus, State, Witness, transition, validate_state


@dataclass(frozen=True)
class FailureBranch:
    cursor: int
    domain: str
    witness: Witness


@dataclass(frozen=True)
class ContingencyPolicy:
    initial: str
    fault_domains: tuple[str, ...]
    nominal: Witness
    branches: tuple[FailureBranch, ...]
    version: int = 1

    def digest(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()

    def to_dict(self):
        return {"initial": self.initial, "fault_domains": self.fault_domains, "version": self.version,
                "nominal": self.nominal.to_dict(), "branches": [
                    {"cursor": b.cursor, "domain": b.domain, "witness": b.witness.to_dict()} for b in self.branches],
                "digest": self.digest()}

    @classmethod
    def from_dict(cls, value):
        policy = cls(value["initial"], tuple(value["fault_domains"]), Witness.from_dict(value["nominal"]),
                     tuple(FailureBranch(b["cursor"], b["domain"], Witness.from_dict(b["witness"]))
                           for b in value["branches"]), value["version"])
        if policy.digest() != value["digest"]:
            raise Rejected("Contingency policy digest mismatch")
        return policy


@dataclass(frozen=True)
class PolicyResult:
    status: SearchStatus
    policy: ContingencyPolicy | None
    explored: int
    branch_checks: int
    reason: str


def _actions(state, initial):
    for slot in state.slots:
        origin = initial[slot.key]
        if slot.status == "FREE" and slot.incarnation == origin.incarnation:
            for spec in state.stripes:
                for row in range(spec.code.total_rows):
                    yield Action("reserve", slot.key, spec.name, row, slot.incarnation)
        following = {"RESERVED": "stage", "STAGED": "promote", "RETIRED": "reclaim"}
        if slot.status in following:
            yield Action(following[slot.status], slot.key, slot.stripe, slot.row, slot.incarnation)
        if slot.incarnation == origin.incarnation and (
                slot.status in {"RESERVED", "STAGED"} and origin.status in {"RESERVED", "STAGED"}
                or slot.status == "LIVE" and slot.domain in state.offline):
            yield Action("abandon", slot.key, slot.stripe, slot.row, slot.incarnation)


def _domains(state, domains):
    validate_state(state)
    result = tuple(sorted(domains))
    if (not result or len(set(result)) != len(result)
            or not set(result) <= {s.domain for s in state.slots} - set(state.offline)):
        raise Rejected("Failure set must name distinct known online scoped domains")
    if state.target():
        raise Rejected("Policy requires a degraded initial repair state")
    return result


def plan_contingency(initial, fault_domains, max_states=5000, branch_budget=20000, max_branch_checks=50000):
    """Find a root safe against one fault at every precompletion boundary.

    Branch budget UNKNOWN cannot prove a root impossible. FOUND certifies
    feasibility, not global robust minimum work, capacity or verification CPU.
    """
    domains = _domains(initial, fault_domains)
    if max_states < 1 or branch_budget < 1 or max_branch_checks < 1:
        return PolicyResult(SearchStatus.UNKNOWN, None, 0, 0, "Policy budget exhausted")
    origins = {s.key: s for s in initial.slots}
    queue, seen = deque([(initial, ())]), {initial}
    cached, explored, branch_checks, uncertain = {}, 0, 0, False
    while queue:
        current, path = queue.popleft()
        if explored >= max_states:
            return PolicyResult(SearchStatus.UNKNOWN, None, explored, branch_checks, "Nominal-state budget exhausted")
        explored += 1
        if current.target() and not any(s.status in {"RESERVED", "STAGED"} for s in current.slots):
            nominal = Witness(initial.fingerprint(), path, current.fingerprint())
            prefix, branches = initial, []
            for cursor, action in enumerate(path):
                branches.extend(FailureBranch(cursor, domain, cached[prefix][domain]) for domain in domains)
                prefix = transition(prefix, action)
            policy = ContingencyPolicy(initial.fingerprint(), domains, nominal, tuple(branches))
            check_policy(initial, policy)
            return PolicyResult(SearchStatus.FOUND, policy, explored, branch_checks, "All precompletion fault branches checked")
        fallbacks, safe = {}, True
        for domain in domains:
            if branch_checks >= max_branch_checks:
                return PolicyResult(SearchStatus.UNKNOWN, None, explored, branch_checks, "Failure-check budget exhausted")
            branch_checks += 1
            failed = replace(current, offline=tuple(sorted(set(current.offline) | {domain})))
            try:
                result = conventional_min_work_plan(failed, branch_budget)
            except Rejected:
                safe = False
                break
            if result.status != SearchStatus.FOUND:
                uncertain |= result.status == SearchStatus.UNKNOWN
                safe = False
                break
            fallbacks[domain] = result.witness
        if not safe:
            continue
        cached[current] = fallbacks
        for action in _actions(current, origins):
            try:
                after = transition(current, action)
            except Rejected:
                continue
            if after not in seen:
                seen.add(after)
                queue.append((after, path + (action,)))
    return PolicyResult(SearchStatus.UNKNOWN if uncertain else SearchStatus.INFEASIBLE, None, explored, branch_checks,
                        "Unresolved branch search" if uncertain else "Finite robust root grammar exhausted")


def select_branch(policy, cursor, domain, actual):
    branch = next((b for b in policy.branches if (b.cursor, b.domain) == (cursor, domain)), None)
    if branch is None or actual.fingerprint() != branch.witness.initial:
        raise Rejected("Failure branch key or complete current snapshot does not match")
    return branch.witness


def conventional_cached_branches(initial, nominal, fault_domains, branch_budget=20000):
    """Ordinary cached alternatives on the identical nominal schedule.

    This comparator gets the same held resources, declared fault set, complete
    prefix coverage and minimum-work fallback planner. It is not forced to
    replan online after a fault. Returned data is trusted in-memory controller
    state, not a durable independently enforced admission record.
    """
    domains = _domains(initial, fault_domains)
    check(initial, nominal)
    current, table = initial, {}
    for cursor, action in enumerate(nominal.actions):
        for domain in domains:
            failed = replace(current, offline=tuple(sorted(set(current.offline) | {domain})))
            try:
                result = conventional_min_work_plan(failed, branch_budget)
            except Rejected:
                return SearchStatus.INFEASIBLE, None
            if result.status != SearchStatus.FOUND:
                return result.status, None
            table[cursor, domain] = result.witness
        current = transition(current, action)
    return SearchStatus.FOUND, table


def select_cached_branch(table, cursor, domain, actual):
    witness = table.get((cursor, domain))
    if witness is None or witness.initial != actual.fingerprint():
        raise Rejected("Conventional cached branch key/snapshot mismatch")
    return witness
