"""Registered read-CPU comparison and monitored foreground diagnostics."""

import hashlib
import json
from pathlib import Path
import random
import tempfile
import time
import traceback
from unittest.mock import patch

from . import storage
from .benchmark import paired_effect
from .liveness import Pulse
from .model import Rejected, profile_spec
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from .snapshot_latency import latency_window

VARIANTS = ("redundant", "reuse")
APIS = ("read", "read_snapshot")
PROTOCOL = Path(__file__).resolve().parent.parent / "experiments/read_reuse_protocol.md"
CALIBRATION_CPU_NS = 200_000_000
MIN_CPU_NS = 50_000_000


def redundant_reads(store):
    """Benchmark-only former decode sequence; no production class mutation."""
    def read(name):
        with store._transaction() as db:
            spec, rows = store._valid_rows(db, name)
            return storage.recover(rows, spec["length"], spec["profile"])[0]
    def snapshot(name):
        try:
            with store._read_transaction() as db:
                spec, rows = store._valid_rows(db, name)
                return storage.recover(rows, spec["length"], spec["profile"])[0]
        except Rejected:
            return store.read(name)
    store.read, store.read_snapshot = read, snapshot
    return store


def read_fixture(root, profile, length, seed):
    code = profile_spec(profile)
    size = max(1024, (length + code.data_rows - 1) // code.data_rows)
    domains = tuple(f"D{i}" for i in range(code.total_rows))
    store = storage.Authority.create(root, dict.fromkeys(domains, 1), size)
    content = random.Random(seed).randbytes(length)
    store.bootstrap("object", content, dict(enumerate(domains)), domains, store.takeover(), profile)
    return store, content, code.total_rows * size


def reconstruction_probe(store, api, content):
    # Outside timing: establish decode counts without charging instrumentation.
    recover, calls = storage.recover, []
    def counted(*args, **kwargs):
        calls.append(1)
        return recover(*args, **kwargs)
    with patch.object(storage, "recover", counted):
        if getattr(store, api)("object") != content:
            raise AssertionError("Decode probe returned different bytes")
    return len(calls)


def read_batch(store, api, content, repetitions):
    completed, error = 0, None
    with Pulse() as pulse:
        cpu, wall = time.process_time_ns(), time.perf_counter_ns()
        try:
            for _ in range(repetitions):
                if getattr(store, api)("object") != content:
                    raise AssertionError("Timed read returned different bytes")
                completed += 1
        except Exception as problem:
            error = repr(problem)
        cpu_ns, end = time.process_time_ns() - cpu, time.perf_counter_ns()
    return {"status": "failed" if error else "completed", "error": error,
            "repetitions": repetitions, "reads_completed": completed, "batch_cpu_ns": cpu_ns,
            "batch_wall_ns": end - wall, "cpu_per_read_ns": cpu_ns / repetitions,
            "wall_per_read_ns": (end - wall) / repetitions,
            "timer_resolved": cpu_ns >= MIN_CPU_NS,
            "liveness": pulse.report(wall, end)}


def require_batch(result):
    if result["status"] != "completed" or result["reads_completed"] != result["repetitions"]:
        raise RuntimeError("Read batch failed: " + str(result["error"]))
    if not result["timer_resolved"]:
        raise RuntimeError("Paired batch CPU is below the predeclared timer minimum")


def progress(report, message):
    try:
        print(message, flush=True)
    except OSError as error:
        report["telemetry_errors"].append(repr(error))


def read_reuse_benchmark(runs=10, seed=20261012, checkpoint=None):
    if runs < 10:
        raise ValueError("Read CPU confirmation requires at least ten paired runs")
    report = {"protocol_version": 1, "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "seed": seed, "runs": runs, "status": "running", "cpu_configurations": [],
              "foreground_diagnostics": [], "telemetry_errors": [],
              "research_gate_passed": False, "selective_advantage_established": False, "patent_rating_changed": False,
              "clock": {name: vars(time.get_clock_info(name)) for name in ("process_time", "perf_counter")}}
    rng = random.Random(seed)
    def save():
        if checkpoint:
            checkpoint(report)
    try:
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for api in APIS:
                for length in (512, 65537):
                    cfg = {"profile": profile, "api": api, "length": length,
                           "calibration": [], "pairs": [], "warmups": []}
                    report["cpu_configurations"].append(cfg)
                    report["active_attempt"] = {"profile": profile, "api": api, "length": length, "phase": "calibration"}
                    with tempfile.TemporaryDirectory(prefix="prism-read-calibration-") as tmp:
                        store, content, _ = read_fixture(Path(tmp) / "store", profile, length, seed)
                        for variant in VARIANTS:
                            warm = redundant_reads(storage.Authority(store.root)) if variant == "redundant" else storage.Authority(store.root)
                            cfg["warmups"].append({"variant": variant, "reconstruction_calls": reconstruction_probe(warm, api, content)})
                        repetitions = 1
                        while repetitions <= 4096:
                            result = read_batch(store, api, content, repetitions)
                            cfg["calibration"].append(result)
                            if result["status"] != "completed":
                                raise RuntimeError("Read calibration failed")
                            if result["batch_cpu_ns"] >= CALIBRATION_CPU_NS:
                                break
                            repetitions *= 2
                        else:
                            raise RuntimeError("CPU timer calibration exhausted the 4096-read budget")
                    cfg["batch_repetitions"] = repetitions
                    report["active_attempt"]["phase"] = "checkpoint"
                    save()
                    for run in range(runs):
                        order = list(VARIANTS)
                        rng.shuffle(order)
                        pair = {"run": run, "seed": seed + run, "order": order, "attempts": {}, "status": "running"}
                        cfg["pairs"].append(pair)
                        with tempfile.TemporaryDirectory(prefix="prism-read-pair-") as tmp:
                            fingerprints = set()
                            for variant in order:
                                report["active_attempt"].update(run=run, variant=variant, phase="read_batch")
                                store, content, capacity = read_fixture(Path(tmp) / variant, profile, length, seed + run)
                                fingerprints.add(store.snapshot().fingerprint())
                                if variant == "redundant":
                                    redundant_reads(store)
                                calls = reconstruction_probe(store, api, content)
                                expected_calls = 2 if variant == "redundant" else 1
                                if calls != expected_calls:
                                    raise AssertionError("Decode-sequence comparator differs from registration")
                                result = read_batch(store, api, content, repetitions)
                                pair["attempts"][variant] = {"reconstruction_calls_per_read": calls, **result}
                                report["active_attempt"]["phase"] = "checkpoint"
                                save()
                                require_batch(result)
                                report["active_attempt"]["phase"] = "post_batch_audit"
                                reopened = storage.Authority(store.root)
                                if not reopened.audit()["target"] or reopened.read("object") != content or reopened.active_plans():
                                    raise AssertionError("Read fixture integrity differs after batch")
                                if sum(sum(d["bytes"].values()) for d in reopened.ledger().values()) != capacity:
                                    raise AssertionError("Read fixture capacity changed")
                            if len(fingerprints) != 1:
                                raise AssertionError("Paired read fixtures differ")
                        pair["status"] = "completed"
                        report["active_attempt"]["phase"] = "checkpoint"
                        save()
                    report["active_attempt"]["phase"] = "analysis"
                    old = [p["attempts"]["redundant"]["batch_cpu_ns"] for p in cfg["pairs"]]
                    new = [p["attempts"]["reuse"]["batch_cpu_ns"] for p in cfg["pairs"]]
                    cfg["reuse_vs_redundant_cpu"] = paired_effect(new, old, seed)
                    cfg["liveness_flagged"] = any(a["liveness"]["gap_flagged"] for p in cfg["pairs"] for a in p["attempts"].values())
                    progress(report, f"Read CPU: {profile}, api={api}, bytes={length}; {runs} pairs completed")
        diagnostic_rng = random.Random(seed ^ 0xABC)
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                order = list(VARIANTS)
                diagnostic_rng.shuffle(order)
                cell = {"repair_profile": profile, "storage_workers": workers, "order": order,
                        "attempts": {}, "paired_confirmation": False}
                report["foreground_diagnostics"].append(cell)
                for variant in order:
                    report["active_attempt"] = {"profile": profile, "workers": workers, "variant": variant, "phase": "foreground_diagnostic"}
                    attempt = latency_window(profile, workers, seed + 1000, "read_snapshot", variant=variant, monitored=True)
                    cell["attempts"][variant] = attempt
                    report["active_attempt"]["phase"] = "checkpoint"
                    save()
                    report["active_attempt"]["phase"] = "foreground_integrity"
                    if not attempt["foreground"]["sufficient"]:
                        raise RuntimeError("Foreground diagnostic contains failed/missing reads")
                if len({a["initial_backlog"] for a in cell["attempts"].values()}) != 1:
                    raise AssertionError("Foreground diagnostic backlogs differ")
                progress(report, f"Monitored foreground: {profile}, workers={workers}; both variants completed")
        report["status"] = "completed"
        report.pop("active_attempt", None)
    except Exception as error:
        report["status"], report["error"], report["traceback"] = "failed", repr(error), traceback.format_exc()
    save()
    return report
