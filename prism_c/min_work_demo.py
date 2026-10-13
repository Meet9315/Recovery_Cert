"""A first-feasible counterexample with real retained bytes and a failed destination."""

from dataclasses import asdict
import random

from .baseline import conventional_plan
from .checker import replay
from .controller_benchmark import FOREGROUND
from .min_work import conventional_min_work_plan, work_score
from .model import SearchStatus, Witness
from .partial_recovery import conventional_partial_plan
from .profiles import DEFAULT_PROFILE
from .storage import Authority


def min_work_fixture(root, profile=DEFAULT_PROFILE, workers=False, mode="conventional_cached", seed=20261013):
    sources = ("D0", "D1") if profile == DEFAULT_PROFILE else ("D0", "D1", "D2", "D3")
    rows = (0, 1) if profile == DEFAULT_PROFILE else (0, 2, 4, 5)
    initial_destinations = ("X", "Z") if profile == DEFAULT_PROFILE else ("P", "Q", "X", "Z")
    capacities = {domain: 2 for domain in sources}
    capacities.update({domain: 1 for domain in initial_destinations + ("Y", "W", "F0", "F1", "F2")})
    store = Authority.create(root, capacities, 1024)
    store = Authority(root, mode)
    fence = store.takeover()
    rng = random.Random(seed)
    contents = {"A": rng.randbytes(1025), "B": rng.randbytes(1025), "foreground": FOREGROUND}
    a_extra = ("P",) if profile != DEFAULT_PROFILE else ()
    b_extra = ("Q",) if profile != DEFAULT_PROFILE else ()
    store.bootstrap("A", contents["A"], dict(zip(rows, sources)), sources + a_extra + ("X", "Y", "Z"), fence, profile)
    store.bootstrap("B", contents["B"], dict(zip(rows, sources)), sources + b_extra + ("X", "W"), fence, profile)
    store.bootstrap("foreground", FOREGROUND, {0: "F0", 1: "F1", 2: "F2"}, ("F0", "F1", "F2"), fence)
    store.seed_retired("Y", fence)
    if workers:
        store.enable_workers(fence)
    targets = tuple(f"{d}:0" for d in initial_destinations)
    initial = store.snapshot_for(("A", "B"), targets)
    ordinary = conventional_plan(initial)
    stages = [a for a in ordinary.actions if a.kind == "stage"]
    kept = next(a for a in stages if a.slot == "X:0" and a.stripe == "B")
    actions = tuple(a for a in ordinary.actions if a.kind == "reserve")
    actions += (kept,) + tuple(a for a in stages if a != kept)
    actions += tuple(a for a in ordinary.actions if a.kind == "promote")
    parent = Witness(initial.fingerprint(), actions, replay(initial, actions).fingerprint())
    store.admit_scoped(parent, ("A", "B"), targets, fence, "initial")
    for _ in range(sum(a.kind == "reserve" for a in actions) + 1):
        store.step("initial", fence)
    store.set_offline("Z", fence)
    return store, fence, contents, parent, targets + ("Y:0", "W:0")


def min_work_demo(root, profile=DEFAULT_PROFILE, workers=False, mode="conventional_cached",
                  planner="min-work", seed=20261013):
    store, fence, contents, parent, targets = min_work_fixture(root, profile, workers, mode, seed)
    initial = store.revision_snapshot("initial", targets, fence)
    first = conventional_partial_plan(initial)
    minimum = conventional_min_work_plan(initial)
    chosen = minimum if planner == "min-work" else first
    if chosen.status != SearchStatus.FOUND:
        raise AssertionError(chosen.reason)
    identifier = store.revise("initial", chosen.witness, targets, fence, "min-work-demo", parent.digest())
    trace = []
    while store.plan_info(identifier)["status"] == "ACTIVE":
        trace.append({"step": store.step(identifier, fence), "ledger": store.ledger()})
    matches = {name: store.read_snapshot(name) == data for name, data in contents.items()}
    if not all(matches.values()) or not store.audit()["target"] or store.active_plans():
        raise AssertionError("Minimum-work revision failed exact restoration")
    steps = [e["detail"]["action"] for e in store.events() if e["kind"] == "step"
             and e["detail"]["plan"] == identifier]
    actual = sum(a["kind"] == "stage" for a in steps), len(steps)
    if actual != work_score(chosen.witness):
        raise AssertionError("Executed work differs from planned objective")
    if store.ledger()["Z"]["bytes"]["RETIRED"] != 1024:
        raise AssertionError("Failed extent was released")
    return {"profile": profile, "workers": workers, "validation_mode": mode, "planner": planner,
            "initial": asdict(initial), "parent_witness": parent.to_dict(), "witness": chosen.witness.to_dict(),
            "first_feasible_score": work_score(first.witness), "minimum_work_score": work_score(minimum.witness),
            "executed_score": actual, "executed_actions": steps, "assignment_states": minimum.explored,
            "successor": store.plan_info(identifier), "trace": trace, "events": store.events(),
            "audit": store.audit(), "ledger_final": store.ledger(), "readback_matches": matches,
            "committed_stage_extent_bytes": actual[0] * 1024, "timing_claimed": False,
            "patent_rating_changed": False, "selective_advantage_claimed": False}
