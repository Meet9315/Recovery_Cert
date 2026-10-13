"""Conventional bounded minimum-stage assignment, plus an independent graph oracle."""

import heapq
from itertools import count

from .checker import check
from .model import Action, Rejected, SearchResult, SearchStatus, Witness, transition, validate_state
from .partial_recovery import assignment_witness


def work_score(witness):
    """Lexicographic committed stage count and action count; not total I/O/CPU."""
    return sum(a.kind == "stage" for a in witness.actions), len(witness.actions)


def conventional_min_work_plan(state, max_states=20000):
    """Minimize stage actions, then all actions, in fixed-online-LIVE assignment.

    Only completed search proves the optimum. On budget exhaustion return
    UNKNOWN without an installable proposal, even if an incumbent was found.
    """
    validate_state(state)
    live = [s for s in state.slots if s.status == "LIVE" and s.domain not in state.offline]
    tasks = [(p, row) for p in state.stripes for row in range(p.code.total_rows)
             if not any(s.stripe == p.name and s.row == row for s in live)]
    candidates = [s for s in state.slots if s.domain not in state.offline and s.status != "LIVE"]
    occupied = {p.name: {s.domain for s in live if s.stripe == p.name} for p in state.stripes}
    constant = sum(s.status in {"RESERVED", "STAGED"} or s.status == "LIVE" and s.domain in state.offline
                   for s in state.slots)
    best, best_score, explored, exhausted = None, None, 0, False
    assignment = []

    def cost(slot, spec, row):
        matched = slot.status in {"RESERVED", "STAGED"} and (slot.stripe, slot.row) == (spec.name, row)
        if matched:
            return (0, 0) if slot.status == "STAGED" else (1, 1)
        return 1, 3 if slot.status == "FREE" else 4

    def options(spec, row, used, domains):
        return sorted((s for s in candidates if s.key not in used and s.domain in spec.eligible
                       and s.domain not in occupied[spec.name] and (spec.name, s.domain) not in domains),
                      key=lambda s: (cost(s, spec, row), s.key))

    def search(index, used, domains, stages, actions):
        nonlocal best, best_score, explored, exhausted
        if exhausted:
            return
        if explored >= max_states:
            exhausted = True
            return
        explored += 1
        if index == len(tasks):
            score = stages, actions + constant
            if best_score is None or score < best_score:
                best, best_score = tuple(assignment), score
            return
        # Relax the remaining shared-slot/domain competition for a valid
        # optimistic bound. Never use an incumbent as an optimum certificate.
        bound_stages, bound_actions = stages, actions + constant
        for spec, row in tasks[index:]:
            available = options(spec, row, used, domains)
            if not available:
                return
            first_cost = cost(available[0], spec, row)
            bound_stages += first_cost[0]
            bound_actions += first_cost[1]
        if best_score is not None and (bound_stages, bound_actions) >= best_score:
            return
        spec, row = tasks[index]
        for slot in options(spec, row, used, domains):
            increment = cost(slot, spec, row)
            assignment.append((spec, row, slot))
            search(index + 1, used | {slot.key}, domains | {(spec.name, slot.domain)},
                   stages + increment[0], actions + increment[1])
            assignment.pop()
            if exhausted:
                return

    search(0, set(), set(), 0, 0)
    if exhausted:
        return SearchResult(SearchStatus.UNKNOWN, None, explored, "Minimum-work assignment budget exhausted")
    if best is None:
        return SearchResult(SearchStatus.INFEASIBLE, None, explored, "Fixed-LIVE assignment exhausted")
    witness = assignment_witness(state, best)
    if work_score(witness) != best_score:
        raise AssertionError("Assignment objective disagrees with checked witness work")
    return SearchResult(SearchStatus.FOUND, witness, explored, "Proven minimum stage/actions in fixed-LIVE assignment")


def min_work_oracle(state, max_states=100000):
    """Independent Dijkstra search: minimize stage/actions in the finite grammar.

    Initial pending allocations/offline LIVE rows can be abandoned. Each slot
    can be acquired only once beyond its initial incarnation; new LIVE rows
    cannot be retired/migrated. No assignment costs or pruning are imported.
    """
    validate_state(state)
    serial, explored = count(), 0
    initial = {s.key: s for s in state.slots}
    queue = [(0, 0, next(serial), state, ())]
    distances = {state: (0, 0)}
    while queue:
        stages, steps, _, current, path = heapq.heappop(queue)
        if distances[current] != (stages, steps):
            continue
        if explored >= max_states:
            return SearchResult(SearchStatus.UNKNOWN, None, explored, "Minimum-work oracle budget exhausted")
        explored += 1
        if current.target() and not any(s.status in {"RESERVED", "STAGED"} for s in current.slots):
            witness = Witness(state.fingerprint(), path, current.fingerprint())
            check(state, witness)
            return SearchResult(SearchStatus.FOUND, witness, explored, "Finite minimum-stage/action oracle")
        for slot in current.slots:
            origin = initial[slot.key]
            proposals = []
            if slot.status == "FREE" and slot.incarnation == origin.incarnation:
                proposals.extend(Action("reserve", slot.key, p.name, row, slot.incarnation)
                                 for p in current.stripes for row in range(p.code.total_rows))
            following = {"RESERVED": "stage", "STAGED": "promote", "RETIRED": "reclaim"}
            if slot.status in following:
                proposals.append(Action(following[slot.status], slot.key, slot.stripe, slot.row, slot.incarnation))
            if (slot.incarnation == origin.incarnation and
                    (slot.status in {"RESERVED", "STAGED"} and origin.status in {"RESERVED", "STAGED"}
                     or slot.status == "LIVE" and slot.domain in current.offline)):
                proposals.append(Action("abandon", slot.key, slot.stripe, slot.row, slot.incarnation))
            for action in proposals:
                try:
                    after = transition(current, action)
                except Rejected:
                    continue
                score = stages + int(action.kind == "stage"), steps + 1
                if after in distances and distances[after] <= score:
                    continue
                distances[after] = score
                heapq.heappush(queue, (*score, next(serial), after, path + (action,)))
    return SearchResult(SearchStatus.INFEASIBLE, None, explored, "Finite minimum-work grammar exhausted")
