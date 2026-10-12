"""Registered logical-validation comparison, including a capable cached baseline."""

from dataclasses import replace
import random
import statistics
import time

from .baseline import conventional_plan
from .checker import check, replay
from .model import Rejected, Slot, State, Stripe
from .selective import ContinuationCache, WholeSuffixCache


def workload(count):
    stripes = tuple(Stripe(f"stripe-{i:02d}", ("S", "T", f"R{i:02d}")) for i in range(count))
    slots = tuple(Slot(f"{spec.name}/{row}", domain, "LIVE", spec.name, row, 1)
                  for spec in stripes for row, domain in enumerate(("S", "T")))
    slots += tuple(Slot(f"R{i:02d}", f"R{i:02d}", "RETIRED" if i % 2 else "FREE") for i in range(count))
    state = State(stripes, slots)
    return state, conventional_plan(state)


def run_mode(initial, witness, mode, annotations):
    started = time.process_time_ns()
    cache = None
    if mode == "selective":
        cache = ContinuationCache.build(initial, witness)
    elif mode == "conventional_cached":
        cache = WholeSuffixCache.build(initial, witness)
    else:
        check(initial, witness)
    preparation = time.process_time_ns() - started
    step_started = time.process_time_ns()
    state = initial
    reused = replayed = 0
    diagnostic_log = []
    for cursor, action in enumerate(witness.actions):
        # Re-materialize equal records, like a fresh authoritative DB snapshot;
        # do not let the conventional guard profit from identical object aliases.
        state = replace(state, stripes=tuple(replace(s) for s in state.stripes),
                        slots=tuple(replace(s) for s in state.slots),
                        offline=tuple(d for d in state.offline))
        if annotations:
            diagnostic_log.append({"step": cursor, "message": "non-authoritative note"})
        if mode == "full":
            final = replay(state, witness.actions[cursor:])
            if final.fingerprint() != witness.terminal:
                raise Rejected("Full reference terminal mismatch")
            replayed += len(witness.actions) - cursor
        else:
            final = cache.validate(state, witness, cursor)
            if mode == "selective":
                reused += cache.last_stats["reused_components"]
                replayed += cache.last_stats["replayed_actions"]
        after = replay(state, (action,), False)
        if mode == "selective":
            cache.advance(state, after, action)
        elif mode == "conventional_cached":
            cache.advance(state, after, action)
        state = after
    step_cpu = time.process_time_ns() - step_started
    # Verification outside timed interval: identical terminal authority for all modes.
    if state.fingerprint() != witness.terminal or not state.target():
        raise AssertionError("Benchmark reached incorrect target")
    return {"mode": mode, "preparation_cpu_ns": preparation, "step_cpu_ns": step_cpu,
            "total_cpu_ns": preparation + step_cpu, "replayed_suffix_actions": replayed,
            "reused_components": reused, "steps": len(witness.actions), "annotations": len(diagnostic_log)}


def paired_effect(left, right, seed):
    """Positive percent means left uses less CPU than right."""
    effects = [100 * (b - a) / b for a, b in zip(left, right)]
    rng = random.Random(seed)
    boot = sorted(statistics.mean(rng.choices(effects, k=len(effects))) for _ in range(2000))
    return {"mean_percent_cpu_reduction": statistics.mean(effects),
            "bootstrap_95_percent_interval": [boot[49], boot[1949]], "paired_percent_changes": effects}


def run_batch(initial, witness, mode, annotations, repetitions):
    started = time.process_time_ns()
    wall = time.perf_counter_ns()
    prep = steps = 0
    for _ in range(repetitions):
        result = run_mode(initial, witness, mode, annotations)
        prep += result["preparation_cpu_ns"]
        steps += result["step_cpu_ns"]
    total = time.process_time_ns() - started
    elapsed = time.perf_counter_ns() - wall
    # Outer timer is primary: Windows process CPU clocks can quantize a
    # single short sequence to zero. Include harness/readback overhead too.
    return {**result, "batch_repetitions": repetitions, "batch_total_cpu_ns": total,
            "batch_wall_ns": elapsed, "total_cpu_ns": total / repetitions,
            "preparation_cpu_ns": prep / repetitions, "step_cpu_ns": steps / repetitions}


def benchmark(runs=10, seed=20261011):
    if runs < 10:
        raise ValueError("Registered comparison requires at least ten paired runs")
    rng = random.Random(seed)
    reports = []
    for count in (2, 8, 16):
        initial, witness = workload(count)
        for annotations in (False, True):
            records = []
            # Warm each code path equally; warm-ups excluded and disclosed.
            for mode in ("full", "selective", "conventional_cached"):
                run_mode(initial, witness, mode, annotations)
            repetitions = 1
            while True:
                calibration = run_batch(initial, witness, "conventional_cached", annotations, repetitions)
                if calibration["batch_total_cpu_ns"] >= 50_000_000:
                    break
                repetitions *= 2
                if repetitions > 8192:
                    raise RuntimeError("CPU timer could not resolve the calibration batch")
            for run in range(runs):
                order = ["full", "selective", "conventional_cached"]
                rng.shuffle(order)
                records.append({"run": run, "order": order,
                                "modes": {m: run_batch(initial, witness, m, annotations, repetitions) for m in order}})
            totals = {mode: [r["modes"][mode]["total_cpu_ns"] for r in records]
                      for mode in ("full", "selective", "conventional_cached")}
            reports.append({"stripes": count, "annotations": annotations, "batch_repetitions": repetitions,
                "calibration": calibration, "runs": records,
                "median_total_cpu_ns": {m: statistics.median(v) for m, v in totals.items()},
                "selective_vs_full": paired_effect(totals["selective"], totals["full"], seed),
                "selective_vs_conventional_cached": paired_effect(totals["selective"],
                                                                    totals["conventional_cached"], seed)})
    return {"seed": seed, "paired_runs_per_configuration": runs, "configurations": reports,
            "protocol_version": 2,
            "scope": "Logical in-memory validation only, including admission/cache construction and all guards; "
                     "one warm-up per mode per configuration; CPU process time; no byte I/O, SQLite, "
                     "serialization, related faults, foreground load or independent failure domains. "
                     "Fresh equal snapshot records constructed each step; exact deployed cache classes used.",
            "controller_target_established": False, "patent_rating_changed": False}
