"""Independent finite feasibility game using replay and exhaustive assignment."""

from collections import deque
from dataclasses import replace
from itertools import permutations

from .checker import replay
from .model import Action, Rejected, SearchResult, SearchStatus, Witness


def failure_feasible(state, budget=10000):
    # No minimum-work objective, planner transitions or assignment bounds.
    replay(state, (), False)
    active = [s for s in state.slots if s.status == "LIVE" and s.domain not in state.offline]
    missing = [(spec, row) for spec in state.stripes for row in range(spec.code.total_rows)
               if not any(s.stripe == spec.name and s.row == row for s in active)]
    usable = [s for s in state.slots if s.domain not in state.offline and s.status != "LIVE"]
    if len(usable) < len(missing):
        return SearchStatus.INFEASIBLE
    examined = 0
    for selected in permutations(usable, len(missing)):
        if examined >= budget:
            return SearchStatus.UNKNOWN
        examined += 1
        occupied = {(s.stripe, s.domain) for s in active}
        feasible = True
        for (spec, _), slot in zip(missing, selected):
            if slot.domain not in spec.eligible or (spec.name, slot.domain) in occupied:
                feasible = False
                break
            occupied.add((spec.name, slot.domain))
        if feasible:
            return SearchStatus.FOUND
    return SearchStatus.INFEASIBLE


def contingency_oracle(initial, fault_domains, max_states=5000, assignment_budget=10000):
    replay(initial, (), False)
    faults = tuple(sorted(fault_domains))
    if (not faults or len(set(faults)) != len(faults) or initial.target()
            or not set(faults) <= {s.domain for s in initial.slots} - set(initial.offline)):
        raise Rejected("Invalid independent failure-game contract")
    if max_states < 1 or assignment_budget < 1:
        return SearchResult(SearchStatus.UNKNOWN, None, 0, "Reference game budget exhausted")
    origins = {s.key: s for s in initial.slots}
    frontier, visited = deque([(initial, ())]), {initial}
    examined, unresolved = 0, False
    while frontier:
        if examined >= max_states:
            return SearchResult(SearchStatus.UNKNOWN, None, examined, "Reference nominal budget exhausted")
        current, path = frontier.popleft()
        examined += 1
        if current.target() and not any(s.status in {"RESERVED", "STAGED"} for s in current.slots):
            witness = Witness(initial.fingerprint(), path, current.fingerprint())
            return SearchResult(SearchStatus.FOUND, witness, examined, "Independent finite one-fault feasibility game")
        safe = True
        for fault in faults:
            failed = replace(current, offline=tuple(sorted(set(current.offline) | {fault})))
            try:
                status = failure_feasible(failed, assignment_budget)
            except Rejected:
                status = SearchStatus.INFEASIBLE
            if status != SearchStatus.FOUND:
                unresolved |= status == SearchStatus.UNKNOWN
                safe = False
                break
        if not safe:
            continue
        moves = []
        for slot in current.slots:
            origin = origins[slot.key]
            if slot.status == "FREE" and slot.incarnation == origin.incarnation:
                moves += [Action("reserve", slot.key, spec.name, row, slot.incarnation)
                          for spec in current.stripes for row in range(spec.code.total_rows)]
            if slot.status == "RESERVED":
                moves.append(Action("stage", slot.key, slot.stripe, slot.row, slot.incarnation))
            if slot.status == "STAGED":
                moves.append(Action("promote", slot.key, slot.stripe, slot.row, slot.incarnation))
            if slot.status == "RETIRED":
                moves.append(Action("reclaim", slot.key, slot.stripe, slot.row, slot.incarnation))
            if slot.incarnation == origin.incarnation and (
                    slot.status in {"RESERVED", "STAGED"} and origin.status in {"RESERVED", "STAGED"}
                    or slot.status == "LIVE" and slot.domain in current.offline):
                moves.append(Action("abandon", slot.key, slot.stripe, slot.row, slot.incarnation))
        for action in moves:
            try:
                following = replay(current, (action,), False)
            except Rejected:
                continue
            if following not in visited:
                visited.add(following)
                frontier.append((following, path + (action,)))
    return SearchResult(SearchStatus.UNKNOWN if unresolved else SearchStatus.INFEASIBLE, None, examined,
                        "Reference unresolved assignment" if unresolved else "Independent finite game exhausted")
