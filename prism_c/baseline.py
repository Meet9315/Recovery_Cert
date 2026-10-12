"""Conventional capacity-aware repair scheduler with complete revalidation.

The matching construction is independent of the BFS planner. It solves the
supported fixed-eligibility, repair-only fixture after reclaiming retired slots.
It is a baseline, not a deliberately greedy controller.
"""

from .checker import replay
from .model import Action, Rejected, State, Witness


def conventional_plan(state: State) -> Witness | None:
    prefix = tuple(Action("reclaim", s.key, s.stripe, s.row, s.incarnation)
                   for s in state.slots if s.status == "RETIRED" and s.domain not in state.offline)
    cleaned = replay(state, prefix, require_target=False)
    # Initial staged/reserved data is outside this matching baseline's scope.
    if any(s.status in {"RESERVED", "STAGED"} for s in cleaned.slots):
        raise Rejected("Baseline requires a quiescent initial snapshot")
    tasks = [(p, row) for p in cleaned.stripes for row in range(p.code.total_rows)
             if not any(s.stripe == p.name and s.row == row and s.status == "LIVE"
                        and s.domain not in cleaned.offline for s in cleaned.slots)]
    free = [s for s in cleaned.slots if s.status == "FREE" and s.domain not in cleaned.offline]
    assignment = []

    def match(index, used, domains):
        if index == len(tasks):
            return True
        spec, row = tasks[index]
        occupied = {s.domain for s in cleaned.slots if s.stripe == spec.name and s.status == "LIVE"}
        for slot in free:
            if (slot.key in used or slot.domain not in spec.eligible or slot.domain in occupied
                    or (spec.name, slot.domain) in domains):
                continue
            assignment.append((spec, row, slot))
            if match(index + 1, used | {slot.key}, domains | {(spec.name, slot.domain)}):
                return True
            assignment.pop()
        return False

    if not match(0, set(), set()):
        return None
    actions = list(prefix)
    for spec, row, slot in assignment:
        actions.extend((Action("reserve", slot.key, spec.name, row, slot.incarnation),
                        Action("stage", slot.key, spec.name, row, slot.incarnation + 1),
                        Action("promote", slot.key, spec.name, row, slot.incarnation + 1)))
    final = replay(state, tuple(actions))
    return Witness(state.fingerprint(), tuple(actions), final.fingerprint())
