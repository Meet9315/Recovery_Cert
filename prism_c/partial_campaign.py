"""Small exhaustive partial-allocation matrix, with an independent BFS oracle."""

from itertools import product

from .checker import check, replay
from .model import SearchStatus, Slot, State, Stripe, transition
from .partial_recovery import conventional_partial_plan, partial_oracle
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES


def run_partial_campaign():
    cases = []
    for profile, status, fallback, failed in product(
            (DEFAULT_PROFILE, FOUR_PLUS_TWO), ("FREE", "RETIRED", "RESERVED", "STAGED", "LIVE"),
            (False, True), (False, True)):
        missing = PROFILES[profile].total_rows - 1
        sources = tuple(f"S{i}" for i in range(missing))
        spec = Stripe("A", sources + ("X",) + (("Z",) if fallback else ()), profile)
        allocated = status in {"RESERVED", "STAGED", "LIVE"}
        slots = tuple(Slot(f"{d}:0", d, "LIVE", "A", row, 1) for row, d in enumerate(sources))
        slots += (Slot("X:0", "X", status, "A" if allocated else "", missing if allocated else -1,
                       0 if status == "FREE" else 1), Slot("Z:0", "Z"))
        state = State((spec,), slots, ("X",) if failed else ())
        matched = conventional_partial_plan(state, 3000)
        oracle = partial_oracle(state, 3000, 12)
        if matched.status != oracle.status or oracle.status == SearchStatus.UNKNOWN:
            raise AssertionError(f"Partial feasibility mismatch: {profile, status, fallback, failed}")
        if matched.witness:
            final = check(state, matched.witness)
            model = state
            for action in matched.witness.actions:
                model = transition(model, action)
            if model != final or model != replay(state, matched.witness.actions):
                raise AssertionError("Partial model and independent checker disagree")
        cases.append({"profile": profile, "initial_destination_status": status,
                      "fallback_eligible": fallback, "destination_offline": failed,
                      "status": matched.status.value, "matching_states": matched.explored,
                      "oracle_states": oracle.explored,
                      "matching_actions": len(matched.witness.actions) if matched.witness else None,
                      "oracle_actions": len(oracle.witness.actions) if oracle.witness else None})
    return {"configurations": len(cases), "cases": cases, "disagreements": 0,
            "unknown": 0, "scope": "Exhaustive 40-case single-stripe matrix; not all partial-recovery states",
            "optimality_claimed": False}
