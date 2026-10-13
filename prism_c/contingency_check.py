"""Independent complete-coverage replay of a one-failure continuation policy."""

from dataclasses import replace

from .checker import check, replay
from .model import Rejected


def check_policy(initial, policy):
    """No planner, optimizer or model transition implementation is imported."""
    if type(policy.version) is not int or policy.version != 1 or policy.initial != initial.fingerprint():
        raise Rejected("Contingency policy version/snapshot mismatch")
    if any(type(s.incarnation) is not int or s.incarnation < 0 for s in initial.slots):
        raise Rejected("Malformed initial allocation generation")
    domains = {s.domain for s in initial.slots} - set(initial.offline)
    if (not policy.fault_domains or tuple(sorted(set(policy.fault_domains))) != policy.fault_domains
            or not set(policy.fault_domains) <= domains):
        raise Rejected("Failure set must name distinct known online scoped domains")
    if initial.target() or not policy.nominal.actions:
        raise Rejected("Contingency policy needs a nonempty degraded repair window")

    def route(state, witness):
        if type(witness.version) is not int or witness.version != 1:
            raise Rejected("Malformed route version")
        final = check(state, witness)
        origins = {s.key: s for s in state.slots}
        current = state
        for action in witness.actions:
            slot = next((s for s in current.slots if s.key == action.slot), None)
            if slot is None or action.kind not in {"reserve", "stage", "promote", "reclaim", "abandon"}:
                raise Rejected("Route is outside the finite nonmigration grammar")
            origin = origins[slot.key]
            if action.kind == "reserve" and slot.incarnation != origin.incarnation:
                raise Rejected("Route acquires a slot more than once beyond its initial incarnation")
            if action.kind == "abandon" and not (
                    slot.incarnation == origin.incarnation and
                    (origin.status in {"RESERVED", "STAGED"} or slot.domain in current.offline and slot.status == "LIVE")):
                raise Rejected("Route abandons a new allocation")
            current = replay(current, (action,), False)
        if any(s.status in {"RESERVED", "STAGED"} for s in final.slots):
            raise Rejected("Policy terminal leaves partial allocations")
        return final

    nominal_final = route(initial, policy.nominal)
    if any(type(b.cursor) is not int or not isinstance(b.domain, str) for b in policy.branches):
        raise Rejected("Malformed branch identity")
    table = {(b.cursor, b.domain): b.witness for b in policy.branches}
    expected = {(cursor, domain) for cursor in range(len(policy.nominal.actions)) for domain in policy.fault_domains}
    if len(table) != len(policy.branches) or set(table) != expected:
        raise Rejected("Failure-branch coverage omitted, duplicated or extended")
    prefix, states, checked_actions = initial, [], len(policy.nominal.actions)
    for cursor, action in enumerate(policy.nominal.actions):
        if prefix.target() and not any(s.status in {"RESERVED", "STAGED"} for s in prefix.slots):
            raise Rejected("Nominal route continues after restoration completion")
        states.append(prefix)
        for domain in policy.fault_domains:
            failed = replace(prefix, offline=tuple(sorted(set(prefix.offline) | {domain})))
            # Even an empty branch must satisfy the decoding floor immediately
            # after the fault, before any repair action can restore redundancy.
            replay(failed, (), False)
            branch = table[cursor, domain]
            route(failed, branch)
            checked_actions += len(branch.actions)
        prefix = replay(prefix, (action,), False)
    return {"branch_count": len(table), "checked_actions": checked_actions,
            "nominal_terminal": nominal_final.fingerprint(), "prefixes": tuple(states),
            "scope": "One declared online domain failure before nominal completion; atomic action boundaries"}
