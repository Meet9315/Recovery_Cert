"""Conventional partial-state matching and a separately searched finite oracle."""

from collections import deque

from .checker import check, replay
from .model import Action, Rejected, SearchResult, SearchStatus, Witness, transition, validate_state


def conventional_partial_plan(state, max_states=20_000):
    """First feasible assignment, preferring already staged/reserved rows.

    Pending allocations may be discarded if retaining them blocks completion.
    This is not an optimality claim. Budget exhaustion is UNKNOWN.
    """
    validate_state(state)
    if max_states < 1:
        return SearchResult(SearchStatus.UNKNOWN, None, 0, "Assignment budget exhausted")
    live = [s for s in state.slots if s.status == "LIVE" and s.domain not in state.offline]
    tasks = [(p, row) for p in state.stripes for row in range(p.code.total_rows)
             if not any(s.stripe == p.name and s.row == row for s in live)]
    candidates = [s for s in state.slots if s.domain not in state.offline and s.status != "LIVE"]
    assignment, explored, exhausted = [], 0, False
    def matches(slot, spec, row):
        return slot.status in {"RESERVED", "STAGED"} and (slot.stripe, slot.row) == (spec.name, row)
    def match(index, used, domains):
        nonlocal explored, exhausted
        if explored >= max_states:
            exhausted = True
            return False
        explored += 1
        if index == len(tasks):
            return True
        spec, row = tasks[index]
        occupied = {s.domain for s in live if s.stripe == spec.name}
        ordered = sorted(candidates, key=lambda s: (
            0 if matches(s, spec, row) and s.status == "STAGED" else
            1 if matches(s, spec, row) else 2 if s.status == "FREE" else 3, s.key))
        for slot in ordered:
            if (slot.key in used or slot.domain not in spec.eligible or slot.domain in occupied
                    or (spec.name, slot.domain) in domains):
                continue
            assignment.append((spec, row, slot))
            if match(index + 1, used | {slot.key}, domains | {(spec.name, slot.domain)}):
                return True
            assignment.pop()
            if exhausted:
                return False
        return False
    if not match(0, set(), set()):
        return SearchResult(SearchStatus.UNKNOWN if exhausted else SearchStatus.INFEASIBLE, None, explored,
                            "Assignment budget exhausted" if exhausted else "Partial assignment exhausted")
    witness = assignment_witness(state, assignment)
    return SearchResult(SearchStatus.FOUND, witness, explored, "Checked partial-state assignment")


def assignment_witness(state, assignment):
    """Materialize an assignment; independent replay checks its complete route."""
    retained = {slot.key for spec, row, slot in assignment
                if slot.status in {"RESERVED", "STAGED"} and (slot.stripe, slot.row) == (spec.name, row)}
    actions = [Action("abandon", s.key, s.stripe, s.row, s.incarnation) for s in state.slots
               if (s.status in {"RESERVED", "STAGED"} and s.key not in retained
                   or s.status == "LIVE" and s.domain in state.offline)]
    current = replay(state, tuple(actions), require_target=False)
    for spec, row, original in assignment:
        slot = next(s for s in current.slots if s.key == original.key)
        steps = []
        if slot.status == "RETIRED":
            steps.append(Action("reclaim", slot.key, slot.stripe, slot.row, slot.incarnation))
        if slot.status in {"FREE", "RETIRED"}:
            steps.append(Action("reserve", slot.key, spec.name, row, slot.incarnation))
            steps.append(Action("stage", slot.key, spec.name, row, slot.incarnation + 1))
            steps.append(Action("promote", slot.key, spec.name, row, slot.incarnation + 1))
        elif slot.status == "RESERVED":
            steps.extend((Action("stage", slot.key, spec.name, row, slot.incarnation),
                          Action("promote", slot.key, spec.name, row, slot.incarnation)))
        elif slot.status == "STAGED":
            steps.append(Action("promote", slot.key, spec.name, row, slot.incarnation))
        current = replay(current, tuple(steps), require_target=False)
        actions.extend(steps)
    witness = Witness(state.fingerprint(), tuple(actions), current.fingerprint())
    check(state, witness)
    return witness


def partial_oracle(state, max_states=20_000, max_steps=20):
    """Shortest-action BFS in a stated finite grammar, independent of matching.

    Each slot may be acquired at most once beyond its initial incarnation;
    only initial pending allocations and initial offline LIVE rows can be
    abandoned. New promoted LIVE rows are not migrated or retired.
    """
    validate_state(state)
    if max_states < 1 or max_steps < 0:
        return SearchResult(SearchStatus.UNKNOWN, None, 0, "Oracle budget exhausted")
    initial = {s.key: s for s in state.slots}
    queue, seen, explored, cutoff = deque([(state, ())]), {state}, 0, False
    while queue:
        current, path = queue.popleft()
        if explored >= max_states:
            return SearchResult(SearchStatus.UNKNOWN, None, explored, "Oracle state budget exhausted")
        explored += 1
        if current.target() and not any(s.status in {"RESERVED", "STAGED"} for s in current.slots):
            witness = Witness(state.fingerprint(), path, current.fingerprint())
            check(state, witness)
            return SearchResult(SearchStatus.FOUND, witness, explored, "Finite shortest-action oracle")
        candidates = []
        for slot in current.slots:
            origin = initial[slot.key]
            if slot.status == "FREE" and slot.incarnation == origin.incarnation:
                candidates.extend(Action("reserve", slot.key, spec.name, row, slot.incarnation)
                                  for spec in current.stripes for row in range(spec.code.total_rows))
            if slot.status in {"RESERVED", "STAGED", "RETIRED"}:
                kind = {"RESERVED": "stage", "STAGED": "promote", "RETIRED": "reclaim"}[slot.status]
                candidates.append(Action(kind, slot.key, slot.stripe, slot.row, slot.incarnation))
            if (slot.incarnation == origin.incarnation and
                    (slot.status in {"RESERVED", "STAGED"} and origin.status in {"RESERVED", "STAGED"}
                     or slot.status == "LIVE" and slot.domain in current.offline)):
                candidates.append(Action("abandon", slot.key, slot.stripe, slot.row, slot.incarnation))
        for action in candidates:
            try:
                after = transition(current, action)
            except Rejected:
                continue
            if after in seen:
                continue
            if len(path) >= max_steps:
                cutoff = True
                continue
            seen.add(after)
            queue.append((after, path + (action,)))
    return SearchResult(SearchStatus.UNKNOWN if cutoff else SearchStatus.INFEASIBLE, None, explored,
                        "Oracle depth budget exhausted" if cutoff else "Finite partial-state grammar exhausted")
