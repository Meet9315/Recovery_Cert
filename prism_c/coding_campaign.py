"""Reproducible 4+2 field, codec and finite repair evidence."""

from dataclasses import replace
import itertools
import random

from .baseline import conventional_plan
from .checker import check, replay
from .coding import encode, gf_mul, recover
from .coding_oracle import MATRIX, determinant, multiply, oracle_encode, oracle_recover
from .model import Rejected, SearchStatus, Slot, State, Stripe, plan, transition
from .profiles import FOUR_PLUS_TWO
from .selective import ContinuationCache, WholeSuffixCache


def run_coding_campaign(seed=20261012):
    products = 0
    for left in range(256):
        for right in range(256):
            if gf_mul(left, right) != multiply(left, right):
                raise AssertionError("GF product differs from polynomial oracle")
            products += 1
    selected = tuple(itertools.combinations(range(6), 4))
    minors = [{"rows": rows, "determinant": determinant(tuple(MATRIX[row] for row in rows))}
              for rows in selected]
    if any(minor["determinant"] == 0 for minor in minors):
        raise AssertionError("4+2 generator is not MDS")
    rng = random.Random(seed)
    lengths = (0, 1, 3, 4, 5, 15, 16, 17, 63, 255, 256, 513)
    reconstructions = 0
    for length in lengths:
        data = rng.randbytes(length)
        encoded = encode(data, FOUR_PLUS_TWO)
        if encoded != oracle_encode(data):
            raise AssertionError("4+2 encode differs from oracle")
        for rows in selected:
            available = {row: encoded[row] for row in rows}
            content, regenerated = recover(available, length, FOUR_PLUS_TWO)
            if content != data or regenerated != encoded or oracle_recover(available, length) != data:
                raise AssertionError("4+2 reconstruction differs from independent oracle")
            reconstructions += 1
    cases = feasible = actions = comparisons = stale_checks = 0
    states = set()
    for rows in selected:
        for eligible in (("X",), ("Y",), ("X", "Y")):
            for retired in itertools.product((False, True), repeat=2):
                for failures in ((), ("X",), ("Y",), ("X", "Y")):
                    slots = tuple(Slot(f"source-{i}", f"D{i}", "LIVE", "A", row, 1)
                                  for i, row in enumerate(rows))
                    slots += tuple(Slot(domain, domain, "RETIRED" if old else "FREE")
                                   for domain, old in zip(("X", "Y"), retired))
                    state = State((Stripe("A", ("D0", "D1", "D2", "D3") + eligible, FOUR_PLUS_TWO),),
                                  slots, failures)
                    states.add(state.fingerprint())
                    # Independent capacity oracle: two missing rows require
                    # both distinct online eligible destination domains.
                    expected = len(eligible) == 2 and not failures
                    witness = conventional_plan(state)
                    candidate = plan(state, max_states=2000, max_steps=10)
                    if candidate.status == SearchStatus.UNKNOWN:
                        raise AssertionError("Registered finite model budget exhausted")
                    if (witness is not None) != expected or (candidate.status == SearchStatus.FOUND) != expected:
                        raise AssertionError("4+2 scheduler/planner differs from assignment oracle")
                    cases += 1
                    if not expected:
                        continue
                    feasible += 1
                    check(state, witness)
                    check(state, candidate.witness)
                    caches = [ContinuationCache.build(state, witness), WholeSuffixCache.build(state, witness)]
                    for cursor, action in enumerate(witness.actions):
                        terminal = replay(state, witness.actions[cursor:])
                        for cache in caches:
                            if cache.validate(state, witness, cursor) != terminal:
                                raise AssertionError("4+2 cached/full suffix disagreement")
                            comparisons += 1
                        stale = replace(action, incarnation=action.incarnation + 99)
                        for validator in (transition, lambda s, a: replay(s, (a,), False)):
                            try:
                                validator(state, stale)
                            except Rejected:
                                stale_checks += 1
                            else:
                                raise AssertionError("Stale 4+2 allocation accepted")
                        following = replay(state, (action,), False)
                        if following != transition(state, action):
                            raise AssertionError("4+2 independent transition disagreement")
                        for cache in caches:
                            cache.advance(state, following, action)
                        state = following
                        states.add(state.fingerprint())
                        actions += 1
                    if not state.target():
                        raise AssertionError("4+2 completed state is not restored")
    return {"profile": FOUR_PLUS_TWO, "seed": seed, "field_products_checked": products,
            "generator_minors": minors, "data_lengths": lengths, "codec_vectors": len(lengths),
            "four_row_reconstructions": reconstructions, "finite_repair_cases": cases,
            "feasible_repair_cases": feasible, "infeasible_repair_cases": cases - feasible,
            "distinct_states_visited": len(states), "validated_actions": actions,
            "cached_full_suffix_comparisons": comparisons, "stale_incarnation_checks": stale_checks,
            "observed_disagreements": 0,
            "scope": "All 15 four-row subsets, two unit destinations, eligibility/offline/retired flags; not general concurrency or hardware proof"}
