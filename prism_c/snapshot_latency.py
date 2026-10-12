"""Paired fixed-arrival foreground comparison, with all queued reads retained."""

import hashlib
import multiprocessing
from pathlib import Path
import queue
import random
import statistics
import tempfile
import threading
import time

from .baseline import conventional_plan
from .benchmark import paired_effect
from .controller_benchmark import FOREGROUND, _fixture, p99
from .measurement_diagnostics import _backlog_fixture
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from .storage import Authority

PROTOCOL = Path(__file__).resolve().parent.parent / "experiments/snapshot_latency_protocol.md"
APIS = ("read", "read_snapshot")


def _arrival_reader(root, api, origins, ready, control_go, control_done, load_go, arrivals_done, abort, output,
                    count=400, rate=100):
    records, errors, fallbacks = [], [], []
    work, service = queue.Queue(maxsize=count), None
    try:
        store = Authority(root)
        original_read = store.read
        if api == "read_snapshot":
            def fallback(name):
                fallbacks.append(time.perf_counter_ns())
                return original_read(name)
            store.read = fallback
        operation = getattr(store, api)
        def consume():
            while True:
                item = work.get()
                try:
                    if item is None:
                        return
                    phase, index, arrival, enqueue = item
                    start, error = time.perf_counter_ns(), None
                    try:
                        if operation("foreground") != FOREGROUND:
                            raise AssertionError("Foreground immutable bytes differ")
                    except Exception as problem:
                        error = repr(problem)
                        errors.append(error)
                    end = time.perf_counter_ns()
                    records.append({"phase": phase, "request": index, "arrival_ns": arrival,
                                    "enqueue_ns": enqueue, "service_start_ns": start, "end_ns": end,
                                    "scheduling_lateness_ns": enqueue - arrival,
                                    "queue_delay_ns": start - arrival, "service_ns": end - start,
                                    "latency_ns": end - arrival, "error": error})
                finally:
                    work.task_done()
        service = threading.Thread(target=consume, daemon=True)
        service.start()
        ready.set()
        for phase, go in ((0, control_go), (1, load_go)):
            if not go.wait(60) or abort.is_set():
                raise RuntimeError("Arrival phase was not started")
            origin = origins[phase]
            for index in range(count):
                if abort.is_set():
                    raise RuntimeError("Arrival collection aborted")
                arrival = origin + round(index * 1e9 / rate)
                time.sleep(max(0, (arrival - time.perf_counter_ns()) / 1e9))
                work.put((phase, index, arrival, time.perf_counter_ns()))
            if phase == 1:
                arrivals_done.set()
            work.join()
            if phase == 0:
                control_done.set()
        work.put(None)
        service.join(10)
        if service.is_alive():
            raise RuntimeError("Read service did not stop")
    except Exception as problem:
        errors.append(repr(problem))
        ready.set()
        control_done.set()
        arrivals_done.set()
    output.send({"requests": records, "errors": errors, "fallback_times_ns": fallbacks,
                 "process_cpu_ns": time.process_time_ns()})
    output.close()


def summarize(observations, stop_ns, expected=400):
    result = {**observations, "loaded_reads_ending_after_restoration": 0,
              "loaded_reads_starting_service_after_restoration": 0}
    healthy = not observations["errors"] and all(r["error"] is None for r in observations["requests"])
    for phase, name in ((0, "control"), (1, "loaded")):
        rows = [r for r in observations["requests"] if r["phase"] == phase]
        # Exactly the offered request identities, including calls completing late.
        complete = len(rows) == expected and sorted(r["request"] for r in rows) == list(range(expected))
        healthy = healthy and complete
        successes = [r for r in rows if r["error"] is None]
        result[name] = {"offered_and_completed": len(rows), "successes": len(successes),
                        "p99_ns": p99([r["latency_ns"] for r in successes]),
                        "service_p99_ns": p99([r["service_ns"] for r in successes]),
                        "queue_delay_p99_ns": p99([r["queue_delay_ns"] for r in successes]),
                        "scheduling_lateness_p99_ns": p99([r["scheduling_lateness_ns"] for r in successes])}
        if phase == 1:
            result["loaded_reads_ending_after_restoration"] = sum(r["end_ns"] > stop_ns for r in rows)
            result["loaded_reads_starting_service_after_restoration"] = sum(r["service_start_ns"] > stop_ns for r in rows)
    sufficient = healthy and all(result[name]["p99_ns"] is not None for name in ("control", "loaded"))
    result.update(healthy=healthy, sufficient=sufficient, fallback_count=len(observations["fallback_times_ns"]))
    result["loaded_control_p99_ratio"] = result["loaded"]["p99_ns"] / result["control"]["p99_ns"] if sufficient else None
    return result


def latency_window(profile, workers, seed, api, *, count=400, rate=100, groups=64):
    if api not in APIS or count < 1 or rate <= 0 or groups < 1:
        raise ValueError("Invalid fixed-arrival workload")
    with tempfile.TemporaryDirectory(prefix="prism-arrivals-") as tmp:
        setup = time.perf_counter_ns()
        store, fence, contents, backlog, capacity = _backlog_fixture(Path(tmp) / "store", profile, workers,
                                                                   seed, "conventional_cached", groups)
        initial, setup_ns = store.snapshot().fingerprint(), time.perf_counter_ns() - setup
        ctx = multiprocessing.get_context("spawn")
        origins = ctx.Array("q", [0, 0])
        ready, control_go, control_done, load_go, arrivals_done, abort = (ctx.Event() for _ in range(6))
        receive, send = ctx.Pipe(duplex=False)
        reader = ctx.Process(target=_arrival_reader, args=(str(store.root), api, origins, ready, control_go,
                             control_done, load_go, arrivals_done, abort, send, count, rate))
        reader.start()
        send.close()
        completed = []
        try:
            if not ready.wait(20):
                raise RuntimeError("Arrival reader failed to start")
            origins[0] = time.perf_counter_ns()
            control_go.set()
            if not control_done.wait(60):
                raise RuntimeError("Control arrivals did not drain")
            control_end = time.perf_counter_ns()
            origins[1] = time.perf_counter_ns()
            load_go.set()
            for group, (names, destinations) in enumerate(backlog):
                if arrivals_done.is_set():
                    break
                if (time.perf_counter_ns() - origins[1]) > 20_000_000_000:
                    raise RuntimeError("Repair deadline preceded all offered arrivals")
                started = time.perf_counter_ns()
                witness = conventional_plan(store.snapshot_for(names, destinations))
                if witness is None:
                    raise AssertionError("Prepared group unexpectedly infeasible")
                store.admit_scoped(witness, names, destinations, fence, f"group-{group}")
                store.execute(f"group-{group}", fence)
                completed.append({"group": group, "stripes": names, "destinations": destinations,
                                  "witness_digest": witness.digest(), "steps": len(witness.actions),
                                  "wall_ns": time.perf_counter_ns() - started})
            if not arrivals_done.is_set() or not completed:
                raise RuntimeError("Insufficient repair backlog or failed arrival startup")
            load_stop = time.perf_counter_ns()
            if not receive.poll(60):
                raise RuntimeError("Loaded requests did not drain")
            observations = receive.recv()
            drain_end = time.perf_counter_ns()
            reader.join(10)
            if reader.is_alive() or reader.exitcode != 0:
                raise RuntimeError("Arrival reader did not exit cleanly")
            reopened = Authority(store.root)
            audit = reopened.audit()
            if reopened.active_plans() or any(reopened.read(name) != value for name, value in contents.items()):
                raise AssertionError("Original backlog bytes or completed plans differ")
            if any(not reopened.snapshot_for(tuple(g["stripes"]), tuple(g["destinations"])).target() for g in completed):
                raise AssertionError("Completed scope did not reach target")
            if sum(sum(d["bytes"].values()) for d in reopened.ledger().values()) != capacity:
                raise AssertionError("Managed capacity changed")
            foreground = summarize(observations, load_stop, count)
            return {"api": api, "profile": profile, "storage_workers": workers, "seed": seed,
                    "initial_backlog": initial, "fixture_wall_ns": setup_ns, "completed_groups": completed,
                    "phase_marks": {"control_origin_ns": origins[0], "control_end_ns": control_end,
                                    "load_origin_ns": origins[1], "load_stop_ns": load_stop},
                    "control_wall_ns": control_end - origins[0], "load_wall_ns": load_stop - origins[1],
                    "drain_wall_ns": drain_end - load_stop, "arrival_rate": rate, "offered_per_phase": count,
                    "foreground": foreground, "audit": audit, "managed_capacity_bytes": capacity,
                    "completed_group_targets_and_all_readbacks_match": True}
        finally:
            abort.set()
            control_go.set()
            load_go.set()
            reader.join(2)
            if reader.is_alive():
                reader.terminate()
                reader.join(10)
            receive.close()


def inflation_summary(ratios, seed):
    rng = random.Random(seed)
    samples = sorted(statistics.mean(rng.choices(ratios, k=len(ratios))) for _ in range(2000))
    interval = [samples[49], samples[1949]]
    return {"mean_ratio": statistics.mean(ratios), "bootstrap_95_percent_interval": interval,
            "ratios": ratios, "upper_bound_at_most_1_05": interval[1] <= 1.05}


def warmup(profile, workers, seed, api):
    with tempfile.TemporaryDirectory(prefix="prism-arrival-warmup-") as tmp:
        store, fence, contents, _ = _fixture(Path(tmp) / "store", 2, profile, workers, seed, "conventional_cached")
        store.execute(store.admit(conventional_plan(store.snapshot()), fence), fence)
        if any(getattr(store, api)(name) != data for name, data in contents.items()) or not store.audit()["target"]:
            raise AssertionError("Latency warm-up integrity failed")
    return {"api": api, "profile": profile, "storage_workers": workers, "status": "completed"}


def snapshot_latency(runs=10, seed=20261012, checkpoint=None):
    if runs < 10:
        raise ValueError("Confirmation requires at least ten independent paired runs")
    report = {"protocol_version": 1, "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "seed": seed, "runs": runs, "status": "running", "warmups": [], "configurations": [],
              "selective_advantage_established": False, "research_gate_passed": False, "patent_rating_changed": False,
              "clock": {name: vars(time.get_clock_info(name)) for name in ("process_time", "perf_counter")}}
    rng = random.Random(seed)
    try:
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                cfg = {"profile": profile, "storage_workers": workers, "pairs": []}
                report["configurations"].append(cfg)
                for api in APIS:
                    report["active_attempt"] = {"profile": profile, "workers": workers, "api": api, "phase": "warmup"}
                    report["warmups"].append(warmup(profile, workers, seed, api))
                for run in range(runs):
                    order = list(APIS)
                    rng.shuffle(order)
                    pair = {"run": run, "seed": seed + run, "order": order, "attempts": {}, "status": "running"}
                    cfg["pairs"].append(pair)
                    for api in order:
                        report["active_attempt"] = {"profile": profile, "workers": workers, "api": api, "run": run, "phase": "window"}
                        attempt = latency_window(profile, workers, seed + run, api)
                        pair["attempts"][api] = attempt
                        if checkpoint:
                            checkpoint(report)
                        if not attempt["foreground"]["sufficient"]:
                            raise RuntimeError("Paired window contains failed/missing/insufficient requests")
                    if pair["attempts"]["read"]["initial_backlog"] != pair["attempts"]["read_snapshot"]["initial_backlog"]:
                        raise AssertionError("Paired initial stores differ")
                    pair["status"] = "completed"
                    if checkpoint:
                        checkpoint(report)
                    print(f"Snapshot latency: {profile}, workers={workers}, pair={run + 1}/{runs}", flush=True)
                before = [p["attempts"]["read"]["foreground"]["loaded"]["p99_ns"] for p in cfg["pairs"]]
                after = [p["attempts"]["read_snapshot"]["foreground"]["loaded"]["p99_ns"] for p in cfg["pairs"]]
                effect = paired_effect(after, before, seed)
                effect["mean_percent_p99_reduction"] = effect.pop("mean_percent_cpu_reduction")
                cfg["snapshot_vs_serialized_loaded_p99"] = effect
                cfg["inflation"] = {api: inflation_summary([p["attempts"][api]["foreground"]["loaded_control_p99_ratio"]
                                                            for p in cfg["pairs"]], seed) for api in APIS}
        report["status"] = "completed"
        report.pop("active_attempt", None)
    except Exception as error:
        report["status"], report["error"] = "failed", repr(error)
        if report["configurations"] and report["configurations"][-1]["pairs"]:
            pair = report["configurations"][-1]["pairs"][-1]
            pair["status"], pair["error"] = "failed", repr(error)
    if checkpoint:
        checkpoint(report)
    return report
