"""Conventional A* joint planner and a deliberately restricted separated control."""

from dataclasses import dataclass
import heapq
from itertools import count

from .model import SearchStatus
from .zoned_model import ZWitness, goal, protected, successors, validate


@dataclass(frozen=True)
class ZResult:
    status: SearchStatus
    witness: ZWitness | None
    score: tuple[int, int] | None
    explored: int


def lower_bound(state):
    # Staging already written requires no further host write to be promoted.
    missing = 0
    for spec in state.stripes:
        available = {e.row for z in state.zones if z.domain not in state.offline
                     for e in z.extents if e.stripe == spec.name and e.status in ("LIVE", "STAGED")}
        missing += spec.code.total_rows - len(available)
    return missing


def conventional_zoned_plan(initial, max_states=20000, *, repair=True, preserve=(), use_bound=True):
    validate(initial)
    if type(max_states) is not int or max_states < 0:
        raise ValueError("Invalid exploration budget")
    if not protected(initial):
        return ZResult(SearchStatus.INFEASIBLE, None, None, 0)
    if repair and any(len(set(p.eligible) - set(initial.offline)) < p.code.total_rows for p in initial.stripes):
        return ZResult(SearchStatus.INFEASIBLE, None, None, 0)
    # Static pins/grants cannot be drained by this grammar.
    for name, units in initial.reclaim:
        zone = next(z for z in initial.zones if z.name == name)
        if zone.appendable() < units and (zone.external_hold or any(e.pins or e.grants for e in zone.extents)):
            return ZResult(SearchStatus.INFEASIBLE, None, None, 0)
    def permitted(state):
        live = {(e.stripe, e.row) for z in state.zones if z.domain not in state.offline
                for e in z.extents if e.status == "LIVE"}
        return set(preserve) <= live
    if not permitted(initial):
        return ZResult(SearchStatus.INFEASIBLE, None, None, 0)
    serial = count()
    best = {initial.key(): (0, 0)}
    heap = [(lower_bound(initial) if use_bound and repair else 0, 0, next(serial), (0, 0), initial, ())]
    explored = 0
    while heap:
        _, _, _, cost, state, actions = heapq.heappop(heap)
        if best.get(state.key()) != cost:
            continue
        if explored >= max_states:
            return ZResult(SearchStatus.UNKNOWN, None, None, explored)
        explored += 1
        if goal(state, repair):
            return ZResult(SearchStatus.FOUND, ZWitness(initial.fingerprint(), actions), cost, explored)
        for action, after in successors(state):
            if not permitted(after):
                continue
            value = cost[0] + int(action.kind == "stage"), cost[1] + 1
            key = after.key()
            if key in best and best[key] <= value:
                continue
            best[key] = value
            estimate = value[0] + (lower_bound(after) if use_bound and repair else 0)
            heapq.heappush(heap, (estimate, value[1], next(serial), value, after, actions + (action,)))
    return ZResult(SearchStatus.INFEASIBLE, None, None, explored)


def separated_gc_plan(initial, max_states=20000):
    """Control: GC keeps every initially live row, then repairs; not primary B2."""
    preserve = tuple(sorted({(e.stripe, e.row) for z in initial.zones if z.domain not in initial.offline
                             for e in z.extents if e.status == "LIVE"}))
    first = conventional_zoned_plan(initial, max_states, repair=False, preserve=preserve, use_bound=False)
    if first.status != SearchStatus.FOUND:
        return first
    from .zoned_model import step
    middle = initial
    for action in first.witness.actions:
        middle = step(middle, action)
    second = conventional_zoned_plan(middle, max_states - first.explored)
    if second.status != SearchStatus.FOUND:
        return ZResult(second.status, None, None, first.explored + second.explored)
    actions = first.witness.actions + second.witness.actions
    return ZResult(SearchStatus.FOUND, ZWitness(initial.fingerprint(), actions),
                   (first.score[0] + second.score[0], len(actions)), first.explored + second.explored)
