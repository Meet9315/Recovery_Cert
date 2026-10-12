"""Matched interrupted-state fixture shared by demonstrations and comparisons."""

from pathlib import Path
import random

from .baseline import conventional_plan
from .checker import replay
from .controller_benchmark import FOREGROUND
from .model import Witness
from .profiles import DEFAULT_PROFILE
from .storage import Authority


def revision_fixture(root, profile=DEFAULT_PROFILE, workers=False, mode="conventional_cached", seed=20261012):
    sources = ("D0", "D1") if profile == DEFAULT_PROFILE else ("D0", "D1", "D2", "D3")
    rows = (0, 1) if profile == DEFAULT_PROFILE else (0, 2, 4, 5)
    destinations = ("X", "Y") if profile == DEFAULT_PROFILE else ("P", "Q", "X", "Y")
    capacities = {domain: 2 for domain in sources}
    capacities.update({domain: 1 for domain in destinations + ("Z", "F0", "F1", "F2")})
    store = Authority.create(Path(root), capacities, 1024)
    store = Authority(root, mode)
    fence = store.takeover()
    rng = random.Random(seed)
    contents = {"A": rng.randbytes(1025), "B": rng.randbytes(1025), "foreground": FOREGROUND}
    a_targets = ("Y",) if profile == DEFAULT_PROFILE else ("P", "Y")
    b_targets = ("X", "Z") if profile == DEFAULT_PROFILE else ("Q", "X", "Z")
    store.bootstrap("A", contents["A"], dict(zip(rows, sources)), sources + a_targets, fence, profile)
    store.bootstrap("B", contents["B"], dict(zip(rows, sources)), sources + b_targets, fence, profile)
    store.bootstrap("foreground", FOREGROUND, {0: "F0", 1: "F1", 2: "F2"}, ("F0", "F1", "F2"), fence)
    if workers:
        store.enable_workers(fence)
    targets = tuple(f"{domain}:0" for domain in destinations)
    initial = store.snapshot_for(("A", "B"), targets)
    ordinary = conventional_plan(initial)
    actions = tuple(a for kind in ("reserve", "stage", "promote") for a in ordinary.actions if a.kind == kind)
    witness = Witness(initial.fingerprint(), actions, replay(initial, actions).fingerprint())
    store.admit_scoped(witness, ("A", "B"), targets, fence, "initial")
    for _ in range(sum(a.kind == "reserve" for a in actions) + 1):
        store.step("initial", fence)
    retained = next(a.slot for a in actions if a.kind == "stage")
    return store, fence, contents, witness, retained, targets + ("Z:0",)
