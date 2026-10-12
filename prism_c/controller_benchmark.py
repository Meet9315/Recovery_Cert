"""Registered real-storage comparison; instrumentation is benchmark-local."""

from contextlib import contextmanager
import hashlib
import math
import multiprocessing
from pathlib import Path
import random
import statistics
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import json

from .baseline import conventional_plan
from .benchmark import paired_effect
from .coding import encode
from .model import Rejected
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from .storage import Authority
from . import worker

MODES = ("conventional_cached", "selective", "full")
FOREGROUND = b"foreground immutable object" * 19
PROTOCOL = Path(__file__).resolve().parent.parent / "experiments/controller_protocol.md"


def p99(values):
    if len(values) < 200:
        return None
    return sorted(values)[math.ceil(0.99 * len(values)) - 1]


def _reader(root, phase, ready, output):
    records = {"idle_latency_ns": [], "repair_latency_ns": [], "errors": []}
    try:
        store = Authority(root)
        ready.set()
        while phase.value != 2:
            current = phase.value
            start = time.perf_counter_ns()
            try:
                if store.read("foreground") != FOREGROUND:
                    raise AssertionError("Foreground bytes differ")
            except Exception as error:
                records["errors"].append(repr(error))
            elapsed = time.perf_counter_ns() - start
            if phase.value == current:
                records["idle_latency_ns" if current == 0 else "repair_latency_ns"].append(elapsed)
            time.sleep(max(0, (2_000_000 - elapsed) / 1e9))
    except Exception as error:
        records["errors"].append(repr(error))
        ready.set()
    records["process_cpu_ns"] = time.process_time_ns()
    output.send(records)
    output.close()


@contextmanager
def measured_rpc():
    records = []
    def call(root, index, operation, **values):
        child = subprocess.run([sys.executable, "-m", "prism_c.measured_worker", str(Path(root).resolve()), str(index)],
                               input=worker.canonical({"operation": operation, **values}), text=True,
                               capture_output=True, timeout=40)
        if child.returncode:
            raise Rejected("Measured worker failed: " + child.stderr[-400:])
        result = json.loads(child.stdout)
        if "error" in result:
            raise Rejected(result["error"])
        records.append({"operation": operation, "worker": index, "cpu_ns": result["benchmark_cpu_ns"]})
        return result["value"]
    with patch.object(worker, "rpc", call):
        yield records


def _fixture(root, count, profile, workers, seed, mode):
    sources = ("D0", "D1") if profile == DEFAULT_PROFILE else ("D0", "D1", "D2", "D3")
    initial_rows = (0, 1) if profile == DEFAULT_PROFILE else (0, 2, 4, 5)
    destinations = ("X",) if profile == DEFAULT_PROFILE else ("X", "Y")
    capacities = {domain: count for domain in sources + destinations}
    capacities.update(F0=1, F1=1, F2=1)
    store = Authority.create(root, capacities, 1024)
    store = Authority(root, mode)
    fence = store.takeover()
    contents = {"foreground": FOREGROUND}
    store.bootstrap("foreground", FOREGROUND, {0: "F0", 1: "F1", 2: "F2"}, ("F0", "F1", "F2"), fence)
    rng = random.Random(seed)
    for i in range(count):
        name = f"stripe-{i:02d}"
        contents[name] = rng.randbytes(1025)
        store.bootstrap(name, contents[name], dict(zip(initial_rows, sources)), sources + destinations, fence, profile)
    for domain in destinations:
        for _ in range(count // 2):
            store.seed_retired(domain, fence)
    if workers:
        store.enable_workers(fence)
    return store, fence, contents, sum(capacities.values()) * 1024


def attempt(count, profile, workers, seed, mode):
    with tempfile.TemporaryDirectory(prefix="prism-controller-") as tmp:
        setup = time.perf_counter_ns()
        store, fence, contents, capacity = _fixture(Path(tmp) / "store", count, profile, workers, seed, mode)
        setup_ns = time.perf_counter_ns() - setup
        context = multiprocessing.get_context("spawn")
        phase, ready = context.Value("i", 0), context.Event()
        receive, send = context.Pipe(duplex=False)
        reader = context.Process(target=_reader, args=(str(store.root), phase, ready, send))
        reader.start()
        send.close()
        try:
            if not ready.wait(20):
                raise RuntimeError("Foreground reader did not start")
            time.sleep(0.5)
            with measured_rpc() as rpc_records:
                phase.value = 1
                cpu, wall = time.process_time_ns(), time.perf_counter_ns()
                initial = store.snapshot()
                witness = conventional_plan(initial)
                if witness is None:
                    raise AssertionError("Registered workload unexpectedly infeasible")
                store.admit(witness, fence, "repair")
                peak = 0
                for cursor in range(len(witness.actions) + 1):
                    ledger = store.ledger()
                    total = sum(sum(domain["bytes"].values()) for domain in ledger.values())
                    if total != capacity:
                        raise AssertionError("Managed capacity was not conserved")
                    occupied = sum(sum(value for status, value in domain["bytes"].items() if status != "FREE")
                                   for domain in ledger.values())
                    peak = max(peak, occupied)
                    if cursor < len(witness.actions):
                        store.step("repair", fence, cursor)
                wall_ns = time.perf_counter_ns() - wall
                controller_ns = time.process_time_ns() - cpu
                phase.value = 2
            if not receive.poll(20):
                raise RuntimeError("Foreground reader did not return its observations")
            foreground = receive.recv()
            reader.join(20)
            if reader.is_alive() or reader.exitcode != 0 or foreground["errors"]:
                raise AssertionError("Foreground reader failed: " + repr(foreground["errors"]))
            reopened = Authority(store.root)
            audit = reopened.audit()
            if not audit["target"] or reopened.active_plans():
                raise AssertionError("Incomplete restoration")
            if any(reopened.read(name) != content for name, content in contents.items()):
                raise AssertionError("Reopened object differs")
            payload = sum(len(encode(contents[action.stripe], profile)[action.row])
                          for action in witness.actions if action.kind == "promote")
            worker_ns = sum(record["cpu_ns"] for record in rpc_records)
            return {"mode": mode, "seed": seed, "status": "completed", "fixture_wall_ns": setup_ns,
                    "controller_cpu_ns": controller_ns, "worker_cpu_ns": worker_ns,
                    "total_cpu_ns": controller_ns + worker_ns, "restoration_wall_ns": wall_ns,
                    "peak_nonfree_bytes": peak, "managed_capacity_bytes": capacity,
                    "promoted_payload_bytes": payload,
                    "reclaimed_extent_bytes": 1024 * sum(a.kind == "reclaim" for a in witness.actions),
                    "steps": len(witness.actions), "witness_digest": witness.digest(),
                    "terminal": audit["snapshot"], "worker_rpcs": rpc_records,
                    "foreground": {**foreground, "idle_p99_ns": p99(foreground["idle_latency_ns"]),
                                   "repair_p99_ns": p99(foreground["repair_latency_ns"])}}
        finally:
            phase.value = 2
            reader.join(2)
            if reader.is_alive():
                reader.terminate()
                reader.join(10)
            receive.close()


def _effect(left, right, seed):
    if any(value <= 0 for value in right):
        return {"available": False, "reason": "Zero baseline timer observation; no pair omitted"}
    effect = paired_effect(left, right, seed)
    return {"available": True, "mean_percent_reduction": effect["mean_percent_cpu_reduction"],
            "bootstrap_95_percent_interval": effect["bootstrap_95_percent_interval"],
            "paired_percent_changes": effect["paired_percent_changes"]}


def summarize(records, count, seed):
    summary = {}
    for metric in ("total_cpu_ns", "restoration_wall_ns"):
        values = {mode: [sum(a[metric] for a in pair["modes"][mode]) for pair in records] for mode in MODES}
        summary[metric] = {"median_per_stripe": {mode: statistics.median(
            value / (count * len(pair["modes"][mode])) for value, pair in zip(values[mode], records)) for mode in MODES},
            "selective_vs_conventional_cached": _effect(values["selective"], values["conventional_cached"], seed),
            "selective_vs_full": _effect(values["selective"], values["full"], seed)}
    samples = [a["foreground"] for pair in records for mode in MODES for a in pair["modes"][mode]]
    sufficient = all(sample["idle_p99_ns"] is not None and sample["repair_p99_ns"] is not None for sample in samples)
    summary["foreground_p99"] = {"status": "sufficient" if sufficient else "insufficient",
                                 "attempts": len(samples), "sufficient_attempts": sum(
                                     s["idle_p99_ns"] is not None and s["repair_p99_ns"] is not None for s in samples)}
    if sufficient:
        # Run-level means of per-attempt repair/control p99 ratios, paired across modes.
        ratios = {mode: [statistics.mean(a["foreground"]["repair_p99_ns"] / a["foreground"]["idle_p99_ns"]
                                         for a in pair["modes"][mode]) for pair in records] for mode in MODES}
        summary["foreground_p99"]["selective_vs_conventional_cached"] = _effect(
            ratios["selective"], ratios["conventional_cached"], seed)
    thresholds = {}
    for metric, target in (("total_cpu_ns", 20), ("restoration_wall_ns", 10)):
        effect = summary[metric]["selective_vs_conventional_cached"]
        thresholds[metric] = {"target_percent_reduction": target,
                              "point_estimate_meets_proxy_threshold": effect["available"] and effect["mean_percent_reduction"] >= target,
                              "interval_lower_bound_meets_proxy_threshold": effect["available"] and effect["bootstrap_95_percent_interval"][0] >= target}
    thresholds["foreground_p99"] = {"maximum_degradation_percent": 5, "evaluated": sufficient}
    if sufficient:
        effect = summary["foreground_p99"]["selective_vs_conventional_cached"]
        thresholds["foreground_p99"]["point_estimate_meets_threshold"] = effect["mean_percent_reduction"] >= -5
        thresholds["foreground_p99"]["interval_lower_bound_meets_threshold"] = effect["bootstrap_95_percent_interval"][0] >= -5
    summary["numerical_proxy_thresholds"] = thresholds
    return summary


def controller_benchmark(runs=10, seed=20261012, checkpoint=None):
    if runs < 10:
        raise ValueError("Registered controller comparison requires at least ten paired runs")
    report = {"protocol_version": 1, "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "seed": seed, "paired_runs_per_configuration": runs, "configurations": [],
              "status": "running", "controller_target_established": False, "patent_rating_changed": False}
    rng = random.Random(seed)
    try:
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for count in (2, 8):
                for workers in (False, True):
                    configuration = {"profile": profile, "stripes": count, "storage_workers": workers,
                                     "warmups": {}, "calibration": [], "runs": []}
                    report["configurations"].append(configuration)
                    for mode in MODES:
                        configuration["warmups"][mode] = attempt(count, profile, workers, seed, mode)
                    repetitions = 1
                    while True:
                        calibration = [attempt(count, profile, workers, seed, "conventional_cached") for _ in range(repetitions)]
                        configuration["calibration"].append(calibration)
                        if sum(a["total_cpu_ns"] for a in calibration) >= 50_000_000:
                            break
                        repetitions *= 2
                        if repetitions > 8:
                            raise RuntimeError("CPU calibration did not resolve within eight attempts")
                    configuration["batch_repetitions"] = repetitions
                    for run in range(runs):
                        seeds = [rng.randrange(2**63) for _ in range(repetitions)]
                        order = list(MODES)
                        rng.shuffle(order)
                        pair = {"run": run, "seeds": seeds, "order": order, "modes": {}}
                        configuration["runs"].append(pair)
                        for mode in order:
                            pair["modes"][mode] = []
                            for attempt_seed in seeds:
                                try:
                                    pair["modes"][mode].append(attempt(count, profile, workers, attempt_seed, mode))
                                except Exception as error:
                                    pair["modes"][mode].append({"status": "failed", "seed": attempt_seed, "error": repr(error)})
                                    raise
                        for replica in range(repetitions):
                            digests = {pair["modes"][mode][replica]["witness_digest"] for mode in MODES}
                            if len(digests) != 1:
                                raise AssertionError("Paired modes did not execute the same witness")
                        if checkpoint:
                            checkpoint(report)
                        print(f"Controller comparison: {profile}, {count} stripes, workers={workers}, pair {run + 1}/{runs}", flush=True)
                    configuration["summary"] = summarize(configuration["runs"], count, seed)
        report["status"] = "completed"
    except Exception as error:
        report["status"], report["error"] = "failed", repr(error)
        if checkpoint:
            checkpoint(report)
        raise
    if checkpoint:
        checkpoint(report)
    return report
