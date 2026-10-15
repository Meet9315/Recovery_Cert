"""Full-path zoned-file cost/foreground diagnostic; no candidate patent advantage."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import queue
import random
import subprocess
import threading
import time

from .coding import digest
from .model import SearchStatus
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES
from .zoned_baseline import conventional_zoned_plan, separated_gc_plan
from .zoned_campaign import zoned_fixture
from .zoned_model import ZAction, ZExtent, ZStripe, ZZone, ZonedState, ZWitness, replay
from .zoned_store import ZonedFileStore


ARMS = ("joint", "joint_repeat", "separated")


def workload(profile, unit, groups, extra):
    """Disjoint components share one open token and groups active tokens."""
    if profile not in PROFILES or type(unit) is not int or unit < 2 or type(groups) is not int or groups < 1:
        raise ValueError("Invalid bounded workload")
    parts, stripes, zones, reclaim, contents = [], [], [], [], {}
    for group in range(groups):
        prefix = f"g{group}/"
        initial = zoned_fixture(profile, extra=extra)
        part = replace(initial,
                       stripes=tuple(replace(s, name=prefix+s.name, eligible=tuple(prefix+d for d in s.eligible)) for s in initial.stripes),
                       zones=tuple(replace(z, name=prefix+z.name, domain=prefix+z.domain,
                                           extents=tuple(replace(e, stripe=prefix+e.stripe) if e.stripe else e for e in z.extents)) for z in initial.zones),
                       reclaim=tuple((prefix+name, units) for name, units in initial.reclaim))
        parts.append(part)
        stripes.extend(part.stripes)
        zones.extend(part.zones)
        reclaim.extend(part.reclaim)
        for spec in part.stripes:
            contents[spec.name] = bytes((i + group + 17) % 251 for i in range(PROFILES[profile].data_rows * unit))
    foreground_domains = tuple(f"foreground/{i}" for i in range(3))
    stripes.append(ZStripe("foreground", foreground_domains))
    zones.extend(ZZone(name, name, 1, (ZExtent("LIVE", "foreground", row, pins=1),), "FULL")
                 for row, name in enumerate(foreground_domains))
    contents["foreground"] = bytes((i + 91) % 251 for i in range(2 * unit))
    return ZonedState(tuple(stripes), tuple(zones), tuple(reclaim), max_active=groups), parts, contents


def compose_plan(initial, parts, arm):
    if arm not in ARMS:
        raise ValueError("Unknown conventional comparison arm")
    actions, costs = [], []
    for part in parts:
        result = separated_gc_plan(part) if arm == "separated" else conventional_zoned_plan(part)
        if result.status != SearchStatus.FOUND:
            raise AssertionError("Declared disjoint component has no complete plan")
        actions.extend(result.witness.actions)
        # A completed tight component retains a partially written active zone.
        # Close it to release the shared open token; closing preserves its tail
        # and still charges one active token. Finishing would strand the goal.
        terminal = replay(part, result.witness)
        closures = [ZAction("close", z.name, z.incarnation) for z in terminal.zones if z.phase == "OPEN"]
        actions.extend(closures)
        costs.append((result.score[0], result.score[1] + len(closures)))
    return ZWitness(initial.fingerprint(), tuple(actions)), costs


def percentile99(values):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, (99 * len(ordered) + 99) // 100 - 1)]


def foreground_summary(records, expected, restoration_stop):
    complete = len(records) == expected and sorted(r["request"] for r in records) == list(range(expected))
    healthy = complete and all(r["error"] is None for r in records)
    overlap = [r for r in records if r["arrival_ns"] < restoration_stop]
    return {"offered": expected, "completed": len(records), "healthy": healthy,
            "p99_latency_ns": percentile99([r["latency_ns"] for r in records]) if healthy else None,
            "p99_service_ns": percentile99([r["service_ns"] for r in records]) if healthy else None,
            "arrived_before_restoration": len(overlap),
            "ending_after_restoration": sum(r["end_ns"] > restoration_stop for r in records),
            "starting_after_restoration": sum(r["service_start_ns"] > restoration_stop for r in records),
            "max_scheduling_lateness_ns": max((r["enqueue_ns"]-r["arrival_ns"] for r in records), default=None),
            "p99_sample_floor_met": healthy and len(overlap) >= 1000}


def cost_window(root, profile, unit, groups, extra, arm, count=400, rate=100):
    if type(count) is not int or count < 1 or not isinstance(rate, (int, float)) or not 0 < rate <= 10000:
        raise ValueError("Invalid fixed arrival schedule")
    if arm not in ARMS:
        raise ValueError("Unknown arm")
    record = {"root": str(Path(root).resolve()), "profile": profile, "unit": unit, "groups": groups,
              "extra": extra, "arm": arm, "success": False, "phases": [], "requests": [], "errors": []}
    def timed(name, function):
        start, cpu = time.perf_counter_ns(), time.thread_time_ns()
        try:
            return function()
        finally:
            record["phases"].append({"name": name, "wall_ns": time.perf_counter_ns()-start,
                                     "controller_thread_cpu_ns": time.thread_time_ns()-cpu})
    reader = producer = None
    work = queue.Queue(maxsize=count + 1)
    ready, go, abort = threading.Event(), threading.Event(), threading.Event()
    origin = [0]
    try:
        initial, parts, contents = workload(profile, unit, groups, extra)
        store = timed("bootstrap", lambda: ZonedFileStore.create(root, initial, contents, unit))
        fence = timed("takeover", store.takeover)

        def consume():
            cpu = time.thread_time_ns()
            try:
                foreground = ZonedFileStore(root)
                if foreground.read("foreground") != contents["foreground"]:
                    raise AssertionError("Foreground warm read mismatch")
                ready.set()
                while True:
                    item = work.get()
                    if item is None:
                        break
                    index, arrival, enqueue = item
                    start, error = time.perf_counter_ns(), None
                    try:
                        if foreground.read("foreground") != contents["foreground"]:
                            raise AssertionError("Foreground content mismatch")
                    except Exception as problem:
                        error = repr(problem)
                    end = time.perf_counter_ns()
                    record["requests"].append({"request": index, "arrival_ns": arrival, "enqueue_ns": enqueue,
                                               "service_start_ns": start, "end_ns": end, "latency_ns": end-arrival,
                                               "service_ns": end-start, "queue_delay_ns": start-arrival, "error": error})
            except Exception as problem:
                record["errors"].append(repr(problem))
                ready.set()
            finally:
                record["foreground_thread_cpu_ns"] = time.thread_time_ns()-cpu

        def offer():
            go.wait()
            try:
                for index in range(count):
                    arrival = origin[0] + round(index * 1e9 / rate)
                    if abort.wait(max(0, (arrival-time.perf_counter_ns()) / 1e9)):
                        return
                    work.put((index, arrival, time.perf_counter_ns()), timeout=30)
                work.put(None, timeout=30)
            except Exception as problem:
                record["errors"].append(repr(problem))

        reader = threading.Thread(target=consume, daemon=True)
        producer = threading.Thread(target=offer, daemon=True)
        reader.start()
        producer.start()
        if not ready.wait(15) or record["errors"]:
            raise RuntimeError("Foreground reader did not initialize")
        cpu, process_cpu = time.thread_time_ns(), time.process_time_ns()
        origin[0] = time.perf_counter_ns()
        go.set()
        snapshot = timed("snapshot", store.snapshot)
        if snapshot != initial:
            raise AssertionError("Seed scope changed")
        witness, scores = timed("planning", lambda: compose_plan(snapshot, parts, arm))
        timed("admission", lambda: store.admit(witness, fence))
        for cursor, action in enumerate(witness.actions):
            timed(f"action/{cursor}/{action.kind}", lambda cursor=cursor: store.advance(fence, cursor))
        timed("terminal_cursor_check", lambda: store.advance(fence, len(witness.actions)))
        stop = time.perf_counter_ns()
        record.update(origin_ns=origin[0], restoration_stop_ns=stop, restoration_wall_ns=stop-origin[0],
                      controller_thread_cpu_ns=time.thread_time_ns()-cpu,
                      whole_process_cpu_during_restoration_ns=time.process_time_ns()-process_cpu,
                      component_scores=scores, witness=witness.to_dict())
        # Drain all offered requests, including arrivals/service/completions after restoration.
        producer.join(60)
        reader.join(60)
        if producer.is_alive() or reader.is_alive():
            raise RuntimeError("Fixed-arrival workload did not fully drain")
        record["drain_stop_ns"] = time.perf_counter_ns()
        record["foreground"] = foreground_summary(record["requests"], count, stop)
        if not record["foreground"]["healthy"] or record["errors"]:
            raise AssertionError("Fixed-arrival collection dropped or failed a request")
        def verify():
            reopened = ZonedFileStore(root)
            if reopened.snapshot() != replay(initial, witness) or not reopened.audit()["target"]:
                raise AssertionError("Measured route differs from complete replay")
            if any(reopened.read(name) != data for name, data in contents.items()):
                raise AssertionError("Measured route lost immutable bytes")
            return reopened.receipts(), reopened.ledger()
        receipts, ledger = timed("post_verification", verify)
        record.update(receipts=receipts, final_ledger=ledger,
                      committed_stage_bytes=sum(r["stage_bytes"] for r in receipts),
                      seed_bytes_excluded=sum(len(z.extents) * unit for z in initial.zones),
                      cpu_floor_met=record["controller_thread_cpu_ns"] >= 50_000_000,
                      initial_sha256=initial.fingerprint(),
                      object_sha256={name: digest(data) for name, data in contents.items()}, success=True)
    except Exception as problem:
        record["errors"].append(repr(problem))
    finally:
        abort.set()
        go.set()
        if reader and reader.is_alive():
            try:
                work.put(None, timeout=1)
            except queue.Full:
                pass
        for thread in (producer, reader):
            if thread and thread.is_alive():
                thread.join(1)
        if any(t and t.is_alive() for t in (producer, reader)):
            record["success"] = False
            record["errors"].append("Diagnostic thread still alive; collection unsuccessful")
    return record


def paired_summary(records, pairs):
    groups, duplicate = {}, False
    for record in records:
        key = (record["profile"], record["unit"], record["groups"], record["extra"], record["pair"])
        arms = groups.setdefault(key, {})
        duplicate = duplicate or record["arm"] in arms
        arms[record["arm"]] = record
    complete = not duplicate and len(records) == 24 * pairs and all(set(arms) == set(ARMS) and all(r["success"] for r in arms.values()) for arms in groups.values())
    effects = []
    for key, arms in groups.items():
        if set(arms) != set(ARMS) or not all(r["success"] for r in arms.values()):
            continue
        a, repeat, control = (arms[arm] for arm in ARMS)
        if len({r["initial_sha256"] for r in arms.values()}) != 1 or len({json.dumps(r["object_sha256"], sort_keys=True) for r in arms.values()}) != 1:
            raise AssertionError("Matched arm inputs differ")
        if a["committed_stage_bytes"] != repeat["committed_stage_bytes"]:
            raise AssertionError("Identical joint software produced different work")
        effects.append({"profile": key[0], "unit": key[1], "groups": key[2], "extra": key[3], "pair": key[4],
                        "joint_vs_control_cpu_percent": 100 * (control["controller_thread_cpu_ns"]-a["controller_thread_cpu_ns"]) / control["controller_thread_cpu_ns"] if control["controller_thread_cpu_ns"] else None,
                        "identical_joint_repeat_cpu_ratio": repeat["controller_thread_cpu_ns"] / a["controller_thread_cpu_ns"] if a["controller_thread_cpu_ns"] else None,
                        "joint_control_stage_bytes": [a["committed_stage_bytes"], control["committed_stage_bytes"]],
                        "foreground_sample_floor_met_all_arms": all(r["foreground"]["p99_sample_floor_met"] for r in arms.values())})
    return {"complete_pairs": len(effects), "expected_pairs": 8 * pairs,
            "all_declared_pairs_collected": complete and len(effects) == 8 * pairs,
            "effects": effects, "confirmation_sample_floor_met": complete and pairs >= 10 and len(effects) == 8 * pairs and all(e["foreground_sample_floor_met_all_arms"] for e in effects) and all(r["cpu_floor_met"] for r in records),
            "five_percent_foreground_gate_evaluated": False, "patent_advantage_claimed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--pairs", type=int, default=2)
    parser.add_argument("--count", type=int, default=400)
    parser.add_argument("--rate", type=float, default=100)
    parser.add_argument("--seed", type=int, default=20261015)
    args = parser.parse_args()
    root, path = Path(args.root).resolve(), Path(args.report).resolve()
    if root.exists() or path.exists() or args.pairs < 1 or args.count < 1 or not 0 < args.rate <= 10000:
        raise ValueError("Use fresh paths and a valid workload")
    root.mkdir(parents=True)
    from .__main__ import environment
    project = Path(__file__).resolve().parents[1]
    metadata = environment()
    metadata.update(git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=project).strip(),
                    protocol_sha256=digest((project / "experiments/zoned_cost_protocol.md").read_bytes()),
                    clocks={name: vars(time.get_clock_info(name)) for name in ("perf_counter", "thread_time", "process_time")})
    result = {"environment": metadata, "success": False, "seed": args.seed, "pairs_per_configuration": args.pairs,
              "count_per_window": args.count, "arrival_rate_hz": args.rate, "records": [],
              "scope": "Diagnostic file-emulator full controller path; conventional scheduling and identical-software repeat; no confirmatory p99 or patent claim"}
    path.parent.mkdir(parents=True, exist_ok=True)
    def checkpoint():
        temp = path.with_name(path.name + ".pending")
        temp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp.replace(path)  # Only this invocation's task-owned report, never an old result.
    try:
        rng = random.Random(args.seed)
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for unit, groups in ((64, 1), (4096, 4)):
                for extra in (False, True):
                    for pair in range(args.pairs):
                        order = list(ARMS)
                        rng.shuffle(order)
                        for position, arm in enumerate(order):
                            window = cost_window(root / f"window-{len(result['records'])}", profile, unit, groups,
                                                 extra, arm, args.count, args.rate)
                            window.update(pair=pair, order=order, position=position)
                            result["records"].append(window)
                            checkpoint()
                            if not window["success"]:
                                raise RuntimeError("Diagnostic window failed; retained all attempted records")
        result["summary"] = paired_summary(result["records"], args.pairs)
        result["success"] = result["summary"]["all_declared_pairs_collected"]
    except Exception as problem:
        result["error"] = repr(problem)
    checkpoint()
    print(json.dumps({k: v for k, v in result.items() if k not in ("environment", "records", "summary")}, indent=2))
    if "summary" in result:
        print(json.dumps({k: v for k, v in result["summary"].items() if k != "effects"}, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
