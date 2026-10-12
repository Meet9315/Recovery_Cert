"""Seeded finite model traces. Reports repeated cases honestly."""

from dataclasses import replace
import itertools
import random

from .baseline import conventional_plan
from .checker import check, replay
from .model import Action, Rejected, Slot, State, Stripe, transition
from .selective import ContinuationCache


def run_campaign(count: int = 10_000, seed: int = 20261011) -> dict:
    if count < 1:
        raise ValueError("Trace count must be positive")
    rng = random.Random(seed)
    domains = ("X", "Y", "Z")
    eligible = [subset for n in range(1, 4) for subset in itertools.combinations(domains, n)]
    identities = set()
    visited = set()
    feasible = 0
    infeasible = 0
    mutations = 0
    executed_actions = 0
    selective_reuse = 0
    for _ in range(count):
        left, right = rng.choice(eligible), rng.choice(eligible)
        offline = tuple(d for d in domains if rng.randrange(4) == 0)
        slots = tuple(Slot(f"{name}{row}", domain, "LIVE", name, row, 1)
                      for name in ("A", "B") for row, domain in enumerate(("S", "T")))
        slots += tuple(Slot(d, d, "RETIRED" if rng.randrange(2) else "FREE") for d in domains)
        state = State((Stripe("A", ("S", "T") + left), Stripe("B", ("S", "T") + right)), slots, offline)
        identities.add(state.fingerprint())
        visited.add(state.fingerprint())
        oracle = any(a != b and a not in offline and b not in offline for a in left for b in right)
        witness = conventional_plan(state)
        if (witness is not None) != oracle:
            raise AssertionError("Conventional matching disagrees with independent assignment enumeration")
        if witness is None:
            infeasible += 1
            continue
        feasible += 1
        check(state, witness)
        cache = ContinuationCache.build(state, witness)
        for cursor, action in enumerate(witness.actions):
            current = state
            reference_terminal = replay(current, witness.actions[cursor:])
            if cache.validate(current, witness, cursor) != reference_terminal:
                raise AssertionError("Selective suffix disagrees with full replay")
            selective_reuse += cache.last_stats["reused_components"]
            # Malformed generation is guaranteed invalid for this current slot.
            malformed = replace(action, incarnation=action.incarnation + 999)
            for validator in (transition, lambda s, a: replay(s, (a,), False)):
                try:
                    validator(current, malformed)
                except Rejected:
                    pass
                else:
                    raise AssertionError("Stale incarnation accepted")
            mutations += 1
            expected = replay(current, (action,), require_target=False)
            actual = transition(current, action)
            if actual != expected:
                raise AssertionError("Independent checker and planner transition disagree")
            cache.advance(current, actual, action)
            state = actual
            executed_actions += 1
            visited.add(state.fingerprint())
        if not state.target():
            raise AssertionError("Completed feasible trace does not meet target")
    return {"seed": seed, "traces": count, "unique_initial_configurations": len(identities),
            "unique_states_visited": len(visited), "feasible_traces": feasible,
            "infeasible_traces": infeasible, "validated_actions": executed_actions,
            "malformed_generation_checks": mutations * 2, "invariant_violations": 0,
            "selective_suffix_reference_comparisons": executed_actions,
            "selective_component_reuses": selective_reuse,
            "scope": "Two stripes; fixed 2-of-3 rows; three destination domains; capacity one per destination; "
                     "offline flags, retired slots and eligibility vary. Traces may repeat. "
                     "Matching-only feasibility oracle; no process or power faults in this model campaign."}
