"""Registered paired fault/retry and independent-controller comparison."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import traceback
from unittest.mock import patch

from . import worker
from .baseline import conventional_plan
from .controller_benchmark import FOREGROUND, _effect, _fixture
from .liveness import Pulse
from .model import Rejected
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from .read_reuse import progress
from .storage import Authority

MODES = ("conventional_cached", "selective")
SCENARIOS = ("lost_receipt_retry", "scoped_contention")
PROTOCOL = Path(__file__).resolve().parent.parent / "experiments/fault_contention_protocol.md"


@contextmanager
def measured_rpc(directory):
    records = []
    def call(root, index, operation, **values):
        diagnostic = Path(directory) / f"rpc-{len(records):04d}.json"
        child = subprocess.run([sys.executable, "-m", "prism_c.fault_measured_worker",
                                str(root), str(index), str(diagnostic)],
                               input=worker.canonical({"operation": operation, **values}),
                               text=True, capture_output=True, timeout=40)
        record = json.loads(diagnostic.read_text(encoding="utf-8")) if diagnostic.exists() else {
            "operation": operation, "worker": index, "telemetry_missing": True}
        records.append({**record, "observed_exit_code": child.returncode, "stderr": child.stderr})
        if child.returncode:
            raise Rejected(f"Measured worker exit {child.returncode}")
        result = json.loads(child.stdout)
        if "error" in result:
            raise Rejected(result["error"])
        return result["value"]
    with patch.object(worker, "rpc", call):
        yield records


def run_controller(root, mode, fence, plans, fault, directory):
    directory = Path(directory)
    output = {"pid": os.getpid(), "mode": mode, "plans": plans, "status": "running",
              "faults": [], "foreground_content_checks": 0, "step_intervals": []}
    store = Authority(root, mode)
    pulse = Pulse().start()
    directory.joinpath("ready").write_text("ready", encoding="utf-8")
    deadline = time.monotonic() + 30
    while not directory.parent.joinpath("go").exists():
        if time.monotonic() > deadline:
            raise TimeoutError("Controller start barrier expired")
        time.sleep(0.002)
    cpu, start = time.process_time_ns(), time.perf_counter_ns()
    with measured_rpc(directory) as records:
        try:
            for plan in plans:
                while store.plan_info(plan)["status"] == "ACTIVE":
                    info = store.plan_info(plan)
                    kind = json.loads(info["witness"])["actions"][info["cursor"]]["kind"]
                    step_start = time.perf_counter_ns()
                    if fault and not output["faults"] and kind == "stage":
                        intent = store.prepare_worker_step(plan, fence)
                        before = store.ledger()
                        try:
                            worker.rpc(root, intent["command"]["worker"], "execute",
                                       token=intent["token"], fault_point="after_worker_commit")
                        except Rejected:
                            if records[-1].get("observed_exit_code") != 77:
                                raise
                        else:
                            raise AssertionError("Requested worker exit did not occur")
                        interrupted = store.plan_info(plan)
                        after = store.ledger()
                        if interrupted["cursor"] != info["cursor"] or before != after:
                            raise AssertionError("Lost acknowledgement advanced cursor or released charge")
                        reused = store.prepare_worker_step(plan, fence)
                        if reused["token"] != intent["token"]:
                            raise AssertionError("Same-epoch retry replaced its prepared intent")
                        durable = worker.rpc(root, intent["command"]["worker"], "receipt", token=intent["token"])
                        receipt = store.execute_worker_intent(intent["token"])
                        if durable != receipt:
                            raise AssertionError("Retry did not return the committed receipt")
                        store.complete_worker_step(receipt, fence)
                        output["faults"].append({"point": "after_worker_commit", "exit_code": 77,
                            "cursor_before": info["cursor"], "cursor_after_exit": interrupted["cursor"],
                            "ledger_before": before, "ledger_after_exit": after,
                            "same_token": True, "same_durable_receipt": True,
                            "retry_completed_ns": time.perf_counter_ns()})
                    else:
                        store.step(plan, fence)
                    output["step_intervals"].append({"plan": plan, "kind": kind,
                        "start_ns": step_start, "end_ns": time.perf_counter_ns()})
                    if store.read_snapshot("foreground") != FOREGROUND:
                        raise AssertionError("Authenticated foreground content differs")
                    output["foreground_content_checks"] += 1
            if bool(output["faults"]) != fault:
                raise AssertionError("Fault count differs from registration")
            output["status"] = "completed"
        except Exception:
            output["status"], output["error"] = "failed", traceback.format_exc()
        finally:
            end = time.perf_counter_ns()
            pulse.stop()
            output.update(controller_cpu_ns=time.process_time_ns() - cpu, start_ns=start, end_ns=end,
                          liveness=pulse.report(start, end), worker_rpcs=records)
    directory.joinpath("result.json").write_text(json.dumps(output), encoding="utf-8")
    return 0 if output["status"] == "completed" else 1


def attempt(profile, scenario, seed, mode):
    output = {"profile": profile, "scenario": scenario, "seed": seed, "mode": mode, "status": "running"}
    with tempfile.TemporaryDirectory(prefix="prism-fault-contention-") as tmp:
        base = Path(tmp)
        children = []
        try:
            store, fence, contents, capacity = _fixture(base / "store", 2, profile, True, seed, mode)
            witnesses = []
            for index in range(2):
                name = f"stripe-{index:02d}"
                destinations = (f"X:{index}",) if profile == DEFAULT_PROFILE else (f"X:{index}", f"Y:{index}")
                witness = conventional_plan(store.snapshot_for((name,), destinations))
                if witness is None:
                    raise AssertionError("Registered fixture infeasible")
                store.admit_scoped(witness, (name,), destinations, fence, name)
                witnesses.append(witness.digest())
            output.update(witness_digests=witnesses, initial_ledger=store.ledger(), managed_capacity_bytes=capacity)
            groups = [["stripe-00", "stripe-01"]] if scenario == "lost_receipt_retry" else [["stripe-00"], ["stripe-01"]]
            for index, plans in enumerate(groups):
                directory = base / f"controller-{index}"
                directory.mkdir()
                request = [str(store.root), mode, fence, plans, scenario == "lost_receipt_retry", str(directory)]
                child = subprocess.Popen([sys.executable, "-m", "prism_c.fault_contention", "--controller", json.dumps(request)],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                children.append((child, directory))
            deadline = time.monotonic() + 30
            while not all(directory.joinpath("ready").exists() for _, directory in children):
                if time.monotonic() > deadline or any(child.poll() is not None for child, _ in children):
                    raise RuntimeError("Independent controller failed before start barrier")
                time.sleep(0.002)
            with Pulse() as pulse:
                cpu, start = time.process_time_ns(), time.perf_counter_ns()
                base.joinpath("go").write_text("go", encoding="utf-8")
                raw = []
                for child, directory in children:
                    stdout, stderr = child.communicate(timeout=90)
                    result = json.loads(directory.joinpath("result.json").read_text(encoding="utf-8")) if directory.joinpath("result.json").exists() else {}
                    raw.append({**result, "exit_code": child.returncode, "stdout": stdout, "stderr": stderr})
                end = time.perf_counter_ns()
                parent_cpu = time.process_time_ns() - cpu
            output.update(controllers=raw, parent_cpu_ns=parent_cpu, restoration_wall_ns=end - start,
                          liveness=pulse.report(start, end))
            if any(r.get("status") != "completed" or r["exit_code"] for r in raw):
                raise AssertionError("Controller failed; raw results retained")
            rpcs = [rpc for controller in raw for rpc in controller["worker_rpcs"]]
            output["controller_step_intervals_overlap"] = len(raw) == 2 and any(
                max(a["start_ns"], b["start_ns"]) < min(a["end_ns"], b["end_ns"])
                for a in raw[0]["step_intervals"] for b in raw[1]["step_intervals"])
            if any("cpu_ns" not in r for r in rpcs):
                raise AssertionError("Worker CPU telemetry missing; no sample discarded")
            output.update(total_cpu_ns=parent_cpu + sum(r["controller_cpu_ns"] for r in raw) + sum(r["cpu_ns"] for r in rpcs),
                          actual_worker_exits=sum(r["observed_exit_code"] == 77 for r in rpcs),
                          foreground_content_checks=sum(r["foreground_content_checks"] for r in raw))
            if output["actual_worker_exits"] != (1 if scenario == "lost_receipt_retry" else 0):
                raise AssertionError("Unexpected worker exit count")
            reopened = Authority(store.root, mode)
            audit = reopened.audit()
            if not audit["target"] or reopened.active_plans():
                raise AssertionError("Repair incomplete")
            if any(reopened.read_snapshot(name) != content for name, content in contents.items()):
                raise AssertionError("Reopened content differs")
            ledger = reopened.ledger()
            if sum(sum(d["bytes"].values()) for d in ledger.values()) != capacity:
                raise AssertionError("Managed capacity differs")
            output.update(status="completed", final_ledger=ledger, terminal=audit["snapshot"])
        except Exception:
            output.update(status="failed", error=traceback.format_exc())
        finally:
            for child, directory in children:
                if child.poll() is None:
                    child.kill()
                if output["status"] == "failed" and "controllers" not in output:
                    stdout, stderr = child.communicate(timeout=10)
                    output.setdefault("failed_children", []).append({"exit_code": child.returncode,
                        "stdout": stdout, "stderr": stderr,
                        "result": directory.joinpath("result.json").read_text(encoding="utf-8") if directory.joinpath("result.json").exists() else None})
                elif child.stdout and not child.stdout.closed:
                    child.communicate(timeout=10)
    return output


def fault_contention_benchmark(runs=10, seed=20261012, checkpoint=None):
    if runs < 10:
        raise ValueError("Registration requires at least ten paired runs")
    report = {"protocol_version": 1, "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              "seed": seed, "runs_per_configuration": runs, "configurations": [], "status": "running",
              "controller_target_established": False, "patent_rating_changed": False,
              "foreground_latency_gate": "not evaluated; content probes are not a latency comparison"}
    rng = random.Random(seed)
    try:
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for scenario in SCENARIOS:
                config = {"profile": profile, "scenario": scenario, "warmups": [], "runs": []}
                report["configurations"].append(config)
                for mode in MODES:
                    sample = attempt(profile, scenario, seed - 1, mode)
                    config["warmups"].append(sample)
                    if sample["status"] != "completed":
                        raise RuntimeError("Warmup failed; retained")
                    if checkpoint:
                        checkpoint(report)
                for index in range(runs):
                    order = list(MODES)
                    rng.shuffle(order)
                    pair = {"index": index, "seed": seed + index, "order": order, "modes": {}}
                    config["runs"].append(pair)
                    for mode in order:
                        pair["modes"][mode] = attempt(profile, scenario, seed + index, mode)
                        if checkpoint:
                            checkpoint(report)
                        if pair["modes"][mode]["status"] != "completed":
                            raise RuntimeError("Attempt failed; no pair omitted or replaced")
                    if pair["modes"][MODES[0]]["witness_digests"] != pair["modes"][MODES[1]]["witness_digests"]:
                        raise AssertionError("Paired witnesses differ")
                    progress(report, f"{profile} {scenario}: pair {index + 1}/{runs} completed")
                config["summary"] = {metric: _effect([p["modes"]["selective"][metric] for p in config["runs"]],
                    [p["modes"]["conventional_cached"][metric] for p in config["runs"]], seed)
                    for metric in ("total_cpu_ns", "restoration_wall_ns")}
                config["proxy_thresholds"] = {metric: {"target_percent_reduction": threshold,
                    "lower_interval_meets": config["summary"][metric]["available"] and config["summary"][metric]["bootstrap_95_percent_interval"][0] >= threshold}
                    for metric, threshold in (("total_cpu_ns", 20), ("restoration_wall_ns", 10))}
        report["status"] = "completed"
    except Exception:
        report.update(status="failed", error=traceback.format_exc())
    if checkpoint:
        checkpoint(report)
    return report


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--controller":
        raise SystemExit(run_controller(*json.loads(sys.argv[2])))
    raise SystemExit("Use python -m prism_c fault-contention-benchmark")
