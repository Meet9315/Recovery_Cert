"""Registered foreground collection and CPU-attribution diagnostics."""

from contextlib import contextmanager
import hashlib
import json
import multiprocessing
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from .baseline import conventional_plan
from .controller_benchmark import FOREGROUND, MODES, _fixture, p99
from .cpu_attribution import logical_spans, new_profiler, profile_report
from .model import Rejected
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from .storage import Authority
from . import worker

PROTOCOL = Path(__file__).resolve().parent.parent / "experiments/measurement_diagnostics_protocol.md"
BACKLOG = 64


def _window_reader(root, phase, counts, failures, ready, begin, paused, resume, output, inflight):
    records, errors = [], []
    try:
        store = Authority(root)
        ready.set()
        begin.wait(20)
        while True:
            with phase.get_lock():
                current = phase.value
                start = time.perf_counter_ns()
                if current in (0, 1):
                    inflight.value = current
            if current == 2:
                break
            if current == -1:
                paused.set()
                resume.wait(20)
                continue
            error = None
            try:
                if store.read("foreground") != FOREGROUND:
                    raise AssertionError("Foreground bytes differ")
            except Exception as problem:
                error = repr(problem)
                errors.append(error)
                with failures.get_lock():
                    failures.value += 1
            end = time.perf_counter_ns()
            record = {"request": len(records), "phase_at_start": current, "phase_at_end": phase.value,
                      "start_ns": start, "end_ns": end, "latency_ns": end - start, "error": error}
            records.append(record)
            inflight.value = -2
            if error is None:
                with counts.get_lock():
                    counts[current] += 1
            time.sleep(max(0, (2_000_000 - (end - start)) / 1e9))
    except Exception as problem:
        errors.append(repr(problem))
        with failures.get_lock():
            failures.value += 1
        ready.set()
    output.send({"requests": records, "errors": errors, "process_cpu_ns": time.process_time_ns()})
    output.close()


def foreground_summary(observations, load_stop_ns):
    requests = observations["requests"]
    idle = [r["latency_ns"] for r in requests if r["phase_at_start"] == 0 and r["error"] is None]
    loaded = [r["latency_ns"] for r in requests if r["phase_at_start"] == 1 and r["error"] is None]
    idle_p99, loaded_p99 = p99(idle), p99(loaded)
    healthy = not observations["errors"] and all(r["error"] is None for r in requests)
    sufficient = healthy and idle_p99 is not None and loaded_p99 is not None
    return {**observations, "healthy": healthy, "status": "sufficient" if sufficient else "insufficient" if healthy else "failed",
            "idle_successes": len(idle), "loaded_successes": len(loaded),
            "loaded_reads_ending_after_restoration": sum(r["phase_at_start"] == 1 and r["end_ns"] > load_stop_ns for r in requests),
            "idle_p99_ns": idle_p99 if healthy else None, "loaded_p99_ns": loaded_p99 if healthy else None,
            "loaded_control_p99_ratio": loaded_p99 / idle_p99 if sufficient else None,
            "research_threshold_evaluated": False}


def _backlog_fixture(root, profile, workers, seed, mode, groups):
    initial_rows = (0, 1) if profile == DEFAULT_PROFILE else (0, 2, 4, 5)
    sources = tuple(f"D{i}" for i in range(len(initial_rows)))
    destinations = ("X",) if profile == DEFAULT_PROFILE else ("X", "Y")
    count = 2 * groups
    capacities = {domain: count for domain in sources + destinations}
    capacities.update(F0=1, F1=1, F2=1)
    store = Authority.create(root, capacities, 1024)
    store = Authority(root, mode)
    fence = store.takeover()
    contents = {"foreground": FOREGROUND}
    store.bootstrap("foreground", FOREGROUND, {0: "F0", 1: "F1", 2: "F2"}, ("F0", "F1", "F2"), fence)
    rng, queue = random.Random(seed), []
    for group in range(groups):
        names = tuple(f"group-{group:02d}-{i}" for i in range(2))
        for name in names:
            contents[name] = rng.randbytes(1025)
            store.bootstrap(name, contents[name], dict(zip(initial_rows, sources)), sources + destinations, fence, profile)
        queue.append((names, tuple(f"{domain}:{position}" for domain in destinations for position in (2 * group, 2 * group + 1))))
    # The domain's first half is retired, matching the API's deterministic
    # first-free seeding policy. Early groups therefore reclaim both slots.
    for domain in destinations:
        for _ in range(count // 2):
            store.seed_retired(domain, fence)
    if workers:
        store.enable_workers(fence)
    return store, fence, contents, queue, sum(capacities.values()) * 1024


def window(profile, workers, seed, mode, *, groups=BACKLOG, target_reads=400,
           control_min=2.0, control_cap=10.0, load_min=4.0, load_cap=20.0):
    if groups < 1 or target_reads < 1 or min(control_min, load_min) < 0 or control_cap < control_min or load_cap < load_min:
        raise ValueError("Invalid diagnostic window budget")
    with tempfile.TemporaryDirectory(prefix="prism-window-") as tmp:
        setup = time.perf_counter_ns()
        store, fence, contents, queue, capacity = _backlog_fixture(Path(tmp) / "store", profile, workers, seed, mode, groups)
        setup_ns, initial = time.perf_counter_ns() - setup, store.snapshot().fingerprint()
        context = multiprocessing.get_context("spawn")
        phase, counts, failures = context.Value("i", 0), context.Array("q", [0, 0]), context.Value("i", 0)
        inflight = context.Value("i", -2)
        ready, begin, paused, resume = (context.Event() for _ in range(4))
        receive, send = context.Pipe(duplex=False)
        reader = context.Process(target=_window_reader, args=(str(store.root), phase, counts, failures, ready, begin, paused, resume, send, inflight))
        reader.start()
        send.close()
        completed, reason = [], "minimum_duration_and_sample_target"
        try:
            if not ready.wait(20):
                raise RuntimeError("Window reader did not start")
            control_start = time.perf_counter_ns()
            begin.set()
            while not failures.value:
                elapsed = (time.perf_counter_ns() - control_start) / 1e9
                if elapsed >= control_cap or elapsed >= control_min and counts[0] >= target_reads:
                    break
                time.sleep(0.01)
            with phase.get_lock():
                phase.value = -1
            if not failures.value and not paused.wait(20):
                raise RuntimeError("Reader failed to drain the control phase")
            control_end = time.perf_counter_ns()
            with phase.get_lock():
                load_start = time.perf_counter_ns()
                phase.value = 1
            resume.set()
            for group, (names, destinations) in enumerate(queue):
                elapsed = (time.perf_counter_ns() - load_start) / 1e9
                if failures.value:
                    reason = "foreground_error"
                    break
                if elapsed >= load_cap:
                    reason = "load_deadline"
                    break
                if elapsed >= load_min and counts[1] >= target_reads:
                    break
                started = time.perf_counter_ns()
                state = store.snapshot_for(names, destinations)
                witness = conventional_plan(state)
                if witness is None:
                    raise AssertionError("Backlog group unexpectedly infeasible")
                store.admit_scoped(witness, names, destinations, fence, f"group-{group}")
                store.execute(f"group-{group}", fence)
                completed.append({"group": group, "stripes": names, "destinations": destinations,
                                  "witness_digest": witness.digest(), "wall_ns": time.perf_counter_ns() - started,
                                  "steps": len(witness.actions)})
            else:
                reason = "backlog_exhausted"
            with phase.get_lock():
                load_stop = time.perf_counter_ns()
                phase.value = 2
            if not receive.poll(20):
                raise RuntimeError("Reader did not drain its final request")
            observations = receive.recv()
            drain_end = time.perf_counter_ns()
            reader.join(20)
            if reader.is_alive() or reader.exitcode != 0:
                raise RuntimeError("Reader process did not exit cleanly")
            reopened = Authority(store.root)
            audit = reopened.audit()  # Safety throughout the untouched backlog, not global target.
            if reopened.active_plans() or any(reopened.read(name) != data for name, data in contents.items()):
                raise AssertionError("Backlog or completed-group bytes differ")
            if any(not reopened.snapshot_for(tuple(group["stripes"]), tuple(group["destinations"])).target() for group in completed):
                raise AssertionError("A completed group missed its target")
            ledger = reopened.ledger()
            if sum(sum(domain["bytes"].values()) for domain in ledger.values()) != capacity:
                raise AssertionError("Backlog capacity was not conserved")
            return {"profile": profile, "storage_workers": workers, "mode": mode, "seed": seed,
                    "fixture_wall_ns": setup_ns, "initial_backlog": initial, "backlog_groups": groups,
                    "completed_groups": completed, "stop_reason": reason, "target_reads": target_reads,
                    "control_wall_ns": control_end - control_start, "load_wall_ns": load_stop - load_start,
                    "drain_wall_ns": drain_end - load_stop,
                    "phase_marks": {"control_start_ns": control_start, "control_end_ns": control_end,
                                    "load_start_ns": load_start, "load_stop_ns": load_stop},
                    "foreground": foreground_summary(observations, load_stop),
                    "audit": audit, "managed_capacity_bytes": capacity,
                    "completed_group_targets_and_all_readbacks_match": True}
        finally:
            with phase.get_lock():
                phase.value = 2
            begin.set()
            resume.set()
            reader.join(2)
            if reader.is_alive():
                reader.terminate()
                reader.join(10)
            receive.close()


@contextmanager
def profiled_rpc():
    records = []
    def call(root, index, operation, **values):
        child = subprocess.run([sys.executable, "-m", "prism_c.measured_worker", str(Path(root).resolve()), str(index)],
                               input=worker.canonical({"operation": operation, "benchmark_profile": True, **values}),
                               text=True, capture_output=True, timeout=40)
        if child.returncode:
            raise Rejected("Profiled worker failed: " + child.stderr[-400:])
        envelope = json.loads(child.stdout)
        if "error" in envelope:
            raise Rejected(envelope["error"])
        records.append({"operation": operation, "worker": index, "process_cpu_ns": envelope["benchmark_cpu_ns"],
                        "handler_profile": envelope["benchmark_profile"]})
        return envelope["value"]
    with patch.object(worker, "rpc", call):
        yield records


def cpu_profile(profile, workers, seed, mode):
    with tempfile.TemporaryDirectory(prefix="prism-profile-") as tmp:
        store, fence, contents, capacity = _fixture(Path(tmp) / "store", 2, profile, workers, seed, mode)
        profiler = new_profiler()
        with logical_spans() as spans, profiled_rpc() as rpcs:
            cpu, wall = time.process_time_ns(), time.perf_counter_ns()
            profiler.enable()
            try:
                witness = conventional_plan(store.snapshot())
                if witness is None:
                    raise AssertionError("CPU fixture unexpectedly infeasible")
                store.admit(witness, fence, "profile")
                for cursor in range(len(witness.actions) + 1):
                    if sum(sum(d["bytes"].values()) for d in store.ledger().values()) != capacity:
                        raise AssertionError("Profile fixture capacity changed")
                    if cursor < len(witness.actions):
                        store.step("profile", fence, cursor)
            finally:
                profiler.disable()
            cpu_ns, wall_ns = time.process_time_ns() - cpu, time.perf_counter_ns() - wall
        reopened = Authority(store.root)
        if not reopened.audit()["target"] or reopened.active_plans() or any(reopened.read(name) != data for name, data in contents.items()):
            raise AssertionError("Profile fixture did not restore original content")
        worker_ns = sum(rpc["process_cpu_ns"] for rpc in rpcs)
        return {"profile": profile, "storage_workers": workers, "mode": mode, "seed": seed,
                "witness_digest": witness.digest(), "steps": len(witness.actions), "status": "completed",
                "controller_cpu_ns": cpu_ns, "worker_process_cpu_ns": worker_ns,
                "combined_instrumented_cpu_ns": cpu_ns + worker_ns, "wall_ns": wall_ns,
                "logical_verification_subset": spans.report(), "controller_profile": profile_report(profiler),
                "worker_rpcs": rpcs, "not_a_performance_confirmation": True}


def diagnostics(seed=20261012, checkpoint=None):
    report = {"protocol_version": 1, "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "seed": seed, "windows": [], "cpu_profiles": [], "status": "running",
              "paired_effects_computed": False, "controller_target_established": False, "patent_rating_changed": False,
              "clock": {name: vars(time.get_clock_info(name)) for name in ("process_time", "perf_counter")}}
    try:
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                fingerprints, witnesses = set(), set()
                for mode in MODES:
                    report["active_cell"] = {"profile": profile, "storage_workers": workers, "mode": mode,
                                             "phase": "foreground_window"}
                    cell = window(profile, workers, seed, mode)
                    report["windows"].append(cell)
                    fingerprints.add(cell["initial_backlog"])
                    if checkpoint:
                        checkpoint(report)
                    if not cell["foreground"]["healthy"]:
                        raise RuntimeError("Foreground observations contain errors")
                    report["active_cell"]["phase"] = "cpu_profile"
                    profile_cell = cpu_profile(profile, workers, seed, mode)
                    report["cpu_profiles"].append(profile_cell)
                    witnesses.add(profile_cell["witness_digest"])
                    if checkpoint:
                        checkpoint(report)
                    print(f"Measurement diagnostics: {profile}, workers={workers}, mode={mode}; idle={cell['foreground']['idle_successes']}, loaded={cell['foreground']['loaded_successes']}", flush=True)
                if len(fingerprints) != 1 or len(witnesses) != 1:
                    raise AssertionError("Modes did not use identical backlogs/profile witnesses")
        report["status"] = "completed"
        report.pop("active_cell", None)
    except Exception as error:
        report["status"], report["error"] = "failed", repr(error)
    if checkpoint:
        checkpoint(report)
    return report
