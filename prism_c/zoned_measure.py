"""Scoped profiles, frozen workload calibration and matched baseline characterization."""

import argparse
import cProfile
import json
from pathlib import Path
import pstats
import random
import re
import statistics
import subprocess
import time

from .coding import digest
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from .zoned_cost import ARMS, compose_plan, cost_window, foreground_summary, workload
from .zoned_model import replay
from .zoned_store import ZonedFileStore


UNIT = 4096
GROUPS = (4, 6, 8)
COUNT = 1200
RATE = 500
CPU_FLOOR = 2_000_000_000
ARRIVAL_FLOOR = 1000
CALIBRATION_SETS = 2
MATCHED_SETS = 10
SEED = 20261018
CONFIGS = tuple((p, extra) for p in (DEFAULT_PROFILE, FOUR_PLUS_TWO) for extra in (False, True))
PROTOCOL = Path(__file__).resolve().parents[1] / "experiments/zoned_measurement_protocol.md"


def quality(record, *, expected=COUNT, cpu_floor=CPU_FLOOR, arrival_floor=ARRIVAL_FLOOR):
    rows = record.get("requests", [])
    complete = (record.get("success", False) and not record.get("errors") and len(rows) == expected
                and sorted(r["request"] for r in rows) == list(range(expected))
                and all(r["error"] is None and r["latency_ns"] == r["end_ns"] - r["arrival_ns"]
                        and r["service_ns"] == r["end_ns"] - r["service_start_ns"]
                        and r["latency_ns"] >= r["service_ns"] >= 0 for r in rows))
    stop = record.get("restoration_stop_ns", 0)
    scheduled = sum(r["arrival_ns"] < stop for r in rows)
    enqueued = sum(r["enqueue_ns"] < stop for r in rows)
    cpu = record.get("controller_thread_cpu_ns", 0)
    return {"collection_integrity": bool(complete), "controller_cpu_floor_met": cpu >= cpu_floor,
            "scheduled_before_restoration": scheduled, "enqueued_before_restoration": enqueued,
            "cpu_floor_ns": cpu_floor, "arrival_floor": arrival_floor,
            "adequate": bool(complete and cpu >= cpu_floor and min(scheduled, enqueued) >= arrival_floor)}


def group_passes(refs):
    keys = [(r["pair"], r["arm"]) for r in refs]
    return (len(keys) == CALIBRATION_SETS * len(ARMS)
            and set(keys) == {(i, arm) for i in range(CALIBRATION_SETS) for arm in ARMS}
            and all(r["quality"]["adequate"] for r in refs))


def profile_category(filename, name):
    path = filename.replace("\\", "/")
    base = path.rsplit("/", 1)[-1]
    if base == "coding.py":
        return "coding"
    if "sqlite3" in name:
        return "sqlite"
    if "HASH" in name or "sha256" in name:
        return "hashing"
    if "_io." in name or "io.open" in name or "fsync" in name:
        return "file_io"
    if "/json/" in path or base in ("dataclasses.py", "copy.py"):
        return "serialization"
    if base in ("zoned_model.py", "zoned_oracle.py"):
        return "model_validation"
    if base == "zoned_baseline.py":
        return "planning"
    if base == "zoned_store.py":
        return "authority"
    return "runtime_other"


def profiled_call(function):
    # Default elapsed profiling avoids assigning individual tiny calls the
    # coarse Windows thread-CPU ticks observed in E17. Phase CPU stays separate.
    profiler = cProfile.Profile()
    start, cpu = time.perf_counter_ns(), time.thread_time_ns()
    error, value = None, None
    try:
        value = profiler.runcall(function)
    except Exception as problem:
        error = repr(problem)
    finally:
        profiler.disable()
    elapsed, used = time.perf_counter_ns()-start, time.thread_time_ns()-cpu
    functions, categories = [], {}
    for (filename, line, name), (primitive, calls, own, total, _) in pstats.Stats(profiler).stats.items():
        category = profile_category(filename, name)
        own_ns = round(own * 1e9)
        categories[category] = categories.get(category, 0) + own_ns
        functions.append({"file": filename.replace("\\", "/"), "line": line, "function": name,
                          "category": category, "calls": calls, "primitive_calls": primitive,
                          "exclusive_elapsed_ns": own_ns, "inclusive_elapsed_ns": round(total * 1e9)})
    functions.sort(key=lambda r: (-r["exclusive_elapsed_ns"], r["file"], r["line"], r["function"]))
    return value, {"wall_ns": elapsed, "thread_cpu_ns": used, "exclusive_categories_elapsed_ns": categories,
                   "functions": functions, "timer": "cProfile default elapsed timer", "error": error,
                   "instrumented_diagnostic_only": True,
                   "inclusive_values_overlap": True, "profile_is_not_uninstrumented_benchmark": True}


def profile_route(root, profile, extra, arm, unit=UNIT, groups=4):
    record = {"profile": profile, "extra": extra, "arm": arm, "unit": unit, "groups": groups,
              "success": False, "phases": {}, "foreground_present": False, "comparison_effect_claimed": False}
    try:
        initial, parts, contents = workload(profile, unit, groups, extra)
        store = ZonedFileStore.create(root, initial, contents, unit)
        fence = store.takeover()
        def capture(name, function):
            value, result = profiled_call(function)
            record["phases"][name] = result
            if result["error"]:
                raise RuntimeError(result["error"])
            return value
        witness, scores = capture("planning", lambda: compose_plan(initial, parts, arm))
        capture("admission", lambda: store.admit(witness, fence))
        capture("actions", lambda: store.execute(fence))
        reopened = ZonedFileStore(root)
        if reopened.snapshot() != replay(initial, witness) or not reopened.audit()["target"]:
            raise AssertionError("Profile route lost its target")
        if any(reopened.read(name) != value for name, value in contents.items()):
            raise AssertionError("Profile route lost immutable bytes")
        record.update(success=True, committed_stage_bytes=sum(r["stage_bytes"] for r in reopened.receipts()),
                      initial_sha256=initial.fingerprint(), component_scores=scores)
    except Exception as error:
        record["error"] = repr(error)
    return record


def metadata():
    from .__main__ import environment
    result = environment()
    result.update(git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True,
                                                   cwd=PROTOCOL.parents[1]).strip(),
                  protocol_sha256=digest(PROTOCOL.read_bytes()),
                  clocks={name: vars(time.get_clock_info(name)) for name in ("thread_time", "perf_counter", "process_time")})
    return result


def save_json(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with path.open("xb") as out:
        out.write(raw)
    return digest(raw)


class Archive:
    def __init__(self, directory, phase):
        self.root = Path(directory).resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        (self.root / "windows").mkdir()
        (self.root / "checkpoints").mkdir()
        self.checkpoints = 0
        self.document = {"phase": phase, "environment": metadata(), "success": False,
                         "records": [], "seed": SEED, "unit": UNIT, "count": COUNT, "rate": RATE,
                         "candidate_mechanism_present": False, "original_prism_gate_evaluated": False,
                         "patent_rating_changed": False}
        self.checkpoint()

    def checkpoint(self):
        # Append-only evidence also works where sandbox policy denies renames.
        save_json(self.root / "checkpoints" / f"checkpoint-{self.checkpoints:04d}.json", self.document)
        self.checkpoints += 1

    def finish(self):
        return save_json(self.root / "manifest.json", self.document)

    def add(self, record, **extra):
        name = f"windows/window-{len(self.document['records']):04d}.json"
        sha = save_json(self.root / name, record)
        ref = {"file": name, "sha256": sha, **extra}
        for key in ("profile", "extra", "arm", "groups", "unit", "success", "committed_stage_bytes",
                    "initial_sha256", "object_sha256", "controller_thread_cpu_ns", "restoration_wall_ns"):
            if key in record:
                ref[key] = record[key]
        if "requests" in record:
            ref.update(quality=quality(record), p99_ns=record.get("foreground", {}).get("p99_latency_ns"))
        self.document["records"].append(ref)
        self.checkpoint()
        print(f"{self.document['phase']} window={len(self.document['records'])} arm={record.get('arm')} success={record.get('success')}", flush=True)
        if not record.get("success"):
            raise RuntimeError("Window failed; preserved its shard and all earlier observations")
        return ref


def calibrate(archive, root):
    rng, selections = random.Random(SEED), []
    for profile, extra in CONFIGS:
        selected = None
        for groups in GROUPS:
            attempts = []
            for pair in range(CALIBRATION_SETS):
                order = list(ARMS)
                rng.shuffle(order)
                for position, arm in enumerate(order):
                    record = cost_window(root / f"window-{len(archive.document['records'])}",
                                         profile, UNIT, groups, extra, arm, COUNT, RATE)
                    attempts.append(archive.add(record, pair=pair, order=order, position=position))
            if group_passes(attempts):
                selected = groups
                break
        selections.append({"profile": profile, "extra": extra, "groups": selected})
        archive.document["selections"] = selections
        archive.checkpoint()
    archive.document["selection_complete"] = all(s["groups"] is not None for s in selections)
    archive.document["success"] = True  # Collection success is distinct from workload adequacy.


def load_calibration(path, expected_environment):
    path = Path(path).resolve()
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("phase") != "calibrate" or not document.get("success") or not document.get("selection_complete"):
        raise ValueError("Calibration is incomplete or insufficient")
    for key in ("source_sha256", "protocol_sha256", "git_head"):
        if document["environment"][key] != expected_environment[key]:
            raise ValueError("Calibration source/protocol changed")
    refs = document["records"]
    if len({r["file"] for r in refs}) != len(refs):
        raise ValueError("Duplicate calibration shard")
    for ref in refs:
        if not re.fullmatch(r"windows/window-\d{4}\.json", ref["file"]):
            raise ValueError("Invalid calibration shard path")
        raw = (path.parent / ref["file"]).read_bytes()
        if digest(raw) != ref["sha256"] or quality(json.loads(raw)) != ref["quality"]:
            raise ValueError("Calibration shard digest/quality changed")
        record = json.loads(raw)
        for key in ("profile", "extra", "groups", "arm", "unit"):
            if record[key] != ref[key]:
                raise ValueError("Calibration shard identity changed")
    selections = document["selections"]
    if len(selections) != len(CONFIGS) or {(s["profile"], s["extra"]) for s in selections} != set(CONFIGS):
        raise ValueError("Calibration configuration coverage differs")
    expected_records = 0
    for selected in selections:
        chosen = selected["groups"]
        if chosen not in GROUPS:
            raise ValueError("Undeclared calibration workload")
        expected_records += (GROUPS.index(chosen)+1) * CALIBRATION_SETS * len(ARMS)
        for groups in GROUPS[:GROUPS.index(chosen)+1]:
            attempts = [r for r in refs if (r["profile"], r["extra"], r["groups"]) == (selected["profile"], selected["extra"], groups)]
            if len(attempts) != CALIBRATION_SETS * len(ARMS) or group_passes(attempts) != (groups == chosen):
                raise ValueError("Calibration skipped/selected an invalid workload")
    if len(refs) != expected_records:
        raise ValueError("Calibration contains undeclared extra observations")
    return document, digest(path.read_bytes())


def bootstrap(values, seed, resamples=5000):
    if not values:
        raise ValueError("No complete matched observations")
    rng = random.Random(seed)
    draws = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(resamples))
    return {"values": values, "mean": statistics.mean(values),
            "paired_bootstrap_95_percent_interval": [draws[int(.025*resamples)], draws[int(.975*resamples)-1]],
            "resamples": resamples, "scope": "Percentile resampling of observed matched sets; host dependence not removed"}


def summarize(refs, selections, matched_sets=MATCHED_SETS):
    expected = {(s["profile"], s["extra"], s["groups"], i, arm)
                for s in selections for i in range(matched_sets) for arm in ARMS}
    keys = [(r["profile"], r["extra"], r["groups"], r["pair"], r["arm"]) for r in refs]
    complete = len(keys) == len(expected) and set(keys) == expected and all(r["success"] for r in refs)
    result = {"complete": complete, "adequate": complete and all(r["quality"]["adequate"] for r in refs),
              "original_prism_gate_evaluated": False, "patent_rating_changed": False, "configurations": []}
    if not complete:
        return result
    for index, selected in enumerate(selections):
        matching = [r for r in refs if (r["profile"], r["extra"], r["groups"]) == (selected["profile"], selected["extra"], selected["groups"])]
        sets = [{r["arm"]: r for r in matching if r["pair"] == i} for i in range(matched_sets)]
        for arms in sets:
            if len({r["initial_sha256"] for r in arms.values()}) != 1 or len({json.dumps(r["object_sha256"], sort_keys=True) for r in arms.values()}) != 1:
                raise ValueError("Matched arm inputs differ")
            if arms["joint"]["committed_stage_bytes"] != arms["joint_repeat"]["committed_stage_bytes"]:
                raise ValueError("Identical joint work differs")
        row = {**selected, "matched_sets": matched_sets,
               "adequate": all(r["quality"]["adequate"] for r in matching), "comparisons": {}}
        for other in ("joint_repeat", "separated"):
            metrics = {}
            for metric in ("controller_thread_cpu_ns", "restoration_wall_ns", "p99_ns"):
                if any(min(arms[other][metric], arms["joint"][metric]) <= 0 for arms in sets):
                    raise ValueError("Unresolved comparison counter")
                values = [arms["joint"][metric] / arms[other][metric] for arms in sets]
                metrics[metric + "_ratio"] = bootstrap(values, SEED + index)
            row["comparisons"][other] = metrics
        interval = row["comparisons"]["joint_repeat"]["p99_ns_ratio"]["paired_bootstrap_95_percent_interval"]
        row["identical_software_p99_5pct_repeatability_screen"] = (
            interval[0] >= .95 and interval[1] <= 1.05 if row["adequate"] and matched_sets >= 10 else None)
        result["configurations"].append(row)
    return result


def confirm(archive, root, calibration_path):
    calibration, calibration_sha = load_calibration(calibration_path, archive.document["environment"])
    selections = calibration["selections"]
    archive.document.update(calibration_sha256=calibration_sha, selections=selections, matched_sets=MATCHED_SETS)
    archive.checkpoint()
    rng = random.Random(SEED + 1)
    for selected in selections:
        for pair in range(MATCHED_SETS):
            order = list(ARMS)
            rng.shuffle(order)
            for position, arm in enumerate(order):
                record = cost_window(root / f"window-{len(archive.document['records'])}",
                                     selected["profile"], UNIT, selected["groups"], selected["extra"], arm, COUNT, RATE)
                archive.add(record, pair=pair, order=order, position=position)
    archive.document["summary"] = summarize(archive.document["records"], selections)
    archive.document["success"] = archive.document["summary"]["complete"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("profile", "calibrate", "confirm"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--calibration")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if root.exists() or Path(args.output).exists() or args.phase == "confirm" and not args.calibration:
        raise ValueError("Fresh root/output required; confirmation also needs frozen calibration")
    root.mkdir(parents=True)
    archive = Archive(args.output, args.phase)
    try:
        if args.phase == "profile":
            for profile, extra in CONFIGS:
                for arm in ("joint", "separated"):
                    archive.add(profile_route(root / f"store-{len(archive.document['records'])}", profile, extra, arm))
            archive.document["success"] = True
        elif args.phase == "calibrate":
            calibrate(archive, root)
        else:
            confirm(archive, root, args.calibration)
    except Exception as error:
        archive.document["error"] = repr(error)
    archive.checkpoint()
    archive.finish()
    print(json.dumps({k: v for k, v in archive.document.items() if k not in ("environment", "records", "summary")}, indent=2))
    return 0 if archive.document["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
