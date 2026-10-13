"""Finite objective comparison against independent state-graph search."""

from itertools import product

from .min_work import conventional_min_work_plan, min_work_oracle, work_score
from .model import Slot, State, Stripe, SearchStatus
from .partial_recovery import conventional_partial_plan
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES


def cases():
    for a_domains, b_fallback, status, y_retired, failed in product(
            (("X",), ("Y",), ("X", "Y")), (False, True),
            ("FREE", "RETIRED", "RESERVED", "STAGED"), (False, True), (False, True)):
        allocated = status in {"RESERVED", "STAGED"}
        specs = (Stripe("A", ("S", "T") + a_domains),
                 Stripe("B", ("S", "T", "X") + (("W",) if b_fallback else ())))
        slots = tuple(Slot(f"{name}{row}", domain, "LIVE", name, row, 1)
                      for name in ("A", "B") for row, domain in enumerate(("S", "T")))
        slots += (Slot("X", "X", status, "B" if allocated else "", 2 if allocated else -1,
                       int(status != "FREE")),
                  Slot("Y", "Y", "RETIRED" if y_retired else "FREE", incarnation=int(y_retired)),
                  Slot("W", "W"))
        yield "two-stripe-2+1", State(specs, slots, ("X",) if failed else ())
    for profile, status, fallback, failed in product(
            (DEFAULT_PROFILE, FOUR_PLUS_TWO), ("FREE", "RETIRED", "RESERVED", "STAGED", "LIVE"),
            (False, True), (False, True)):
        missing = PROFILES[profile].total_rows - 1
        sources = tuple(f"S{i}" for i in range(missing))
        spec = Stripe("A", sources + ("X",) + (("Z",) if fallback else ()), profile)
        allocated = status in {"RESERVED", "STAGED", "LIVE"}
        slots = tuple(Slot(f"{d}:0", d, "LIVE", "A", row, 1) for row, d in enumerate(sources))
        slots += (Slot("X:0", "X", status, "A" if allocated else "", missing if allocated else -1,
                       int(status != "FREE")), Slot("Z:0", "Z"))
        yield "single-stripe", State((spec,), slots, ("X",) if failed else ())


def run_min_work_campaign():
    records = []
    for number, (family, state) in enumerate(cases()):
        result = conventional_min_work_plan(state, 20000)
        oracle = min_work_oracle(state, 20000)
        first = conventional_partial_plan(state)
        if result.status != oracle.status or result.status == SearchStatus.UNKNOWN:
            raise AssertionError(f"Minimum-work feasibility mismatch in case {number}")
        optimal = work_score(result.witness) if result.witness else None
        reference = work_score(oracle.witness) if oracle.witness else None
        prior = work_score(first.witness) if first.witness else None
        if optimal != reference or (optimal is not None and optimal > prior):
            raise AssertionError(f"Minimum-work objective mismatch in case {number}")
        records.append({"case": number, "family": family, "snapshot": state.fingerprint(),
                        "status": result.status.value, "minimum_work": optimal, "oracle_work": reference,
                        "first_feasible_work": prior, "assignment_states": result.explored,
                        "oracle_states": oracle.explored})
    return {"configurations": len(records), "cases": records, "disagreements": 0,
            "unknown": 0, "first_feasible_suboptimal_cases": sum(
                r["minimum_work"] is not None and r["minimum_work"] < r["first_feasible_work"] for r in records),
            "scope": "96 two-stripe 2+1 states plus 40 single-stripe states across both profiles; finite grammar"}
