"""Registered matched codec batches, exact historical baseline and cold execution."""

import argparse
import json
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time
import types

from prism_c import coding
from prism_c.__main__ import environment
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES
from prism_c.zoned_measure import bootstrap


ROOT = Path(__file__).resolve().parents[1]
OLD = "e8ad2dba831f17749b0f8d27e5a32e63b1e9889a"
SEED = 20261016
COLD = '''import json,sys,time
from pathlib import Path
from prism_c import model,profiles
source=compile(Path(sys.argv[1]).read_bytes(),sys.argv[1],"exec")
namespace={"__name__":"prism_c._cold_codec","__package__":"prism_c"}
wall,cpu=time.perf_counter_ns(),time.thread_time_ns()
exec(source,namespace)
print(json.dumps({"wall_ns":time.perf_counter_ns()-wall,"thread_cpu_ns":time.thread_time_ns()-cpu}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    root, report_path = Path(args.root), Path(args.report)
    if root.exists() or report_path.exists():
        raise ValueError("Fresh root/report required")
    root.mkdir(parents=True)
    baseline = subprocess.check_output(["git", "show", f"{OLD}:prism_c/coding.py"], cwd=ROOT)
    expected = json.loads((ROOT / "evidence/results/verification-e18.json").read_bytes())["environment"]["source_sha256"]["prism_c/coding.py"]
    if coding.digest(baseline) != expected:
        raise ValueError("Historical codec blob differs from verified source")
    baseline_path = root.resolve() / "historical_codec.py"
    baseline_path.write_bytes(baseline)
    legacy = types.ModuleType("prism_c._historical_codec")
    legacy.__package__ = "prism_c"
    exec(compile(baseline, str(baseline_path), "exec"), legacy.__dict__)
    if coding.digest(Path(coding.__file__).read_bytes()) == expected:
        raise ValueError("Optimized codec is not implemented")
    report = {"environment": environment(), "historical_source_commit": OLD,
              "historical_codec_sha256": expected, "protocol_sha256": coding.digest((ROOT / "experiments/codec_optimization_protocol.md").read_bytes()),
              "seed": SEED, "batch_operations": 100, "matched_sets": 12,
              "cold": {}, "configurations": [], "success": False,
              "candidate_mechanism_present": False, "patent_rating_changed": False,
              "helper_sha256": coding.digest(Path(__file__).read_bytes()),
              "correction_sha256": coding.digest((ROOT/"experiments/codec_micro_correction.md").read_bytes())}
    try:
        rng = random.Random(SEED)
        for name, path in (("historical", baseline_path), ("optimized", Path(coding.__file__).resolve())):
            report["cold"][name] = [json.loads(subprocess.check_output([sys.executable, "-c", COLD, str(path)], cwd=ROOT, text=True)) for _ in range(5)]
        report["translation_table_payload_bytes"] = sum(len(table) for table in coding._MUL_TABLES)
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for unit in (64, 4096):
                data = random.Random(SEED + unit).randbytes(PROFILES[profile].data_rows * unit - 1)
                encoded = legacy.encode(data, profile)
                if encoded != coding.encode(data, profile):
                    raise AssertionError("Encoding mismatch before timing")
                if any(len(row) != unit for row in encoded):
                    raise AssertionError("Encoded row size differs from declared unit")
                chosen = (1, 2) if profile == DEFAULT_PROFILE else (0, 2, 4, 5)
                rows = {index: encoded[index] for index in chosen}
                for operation in ("encode", "recover"):
                    expected_output = encoded if operation == "encode" else (data, encoded)
                    functions = {name: (lambda module=module: module.encode(data, profile)) if operation == "encode"
                                 else (lambda module=module: module.recover(rows, len(data), profile))
                                 for name, module in (("historical", legacy), ("optimized", coding))}
                    for function in functions.values():
                        if function() != expected_output:
                            raise AssertionError("Warmup mismatch")
                    config = {"profile": profile, "unit": unit, "operation": operation,
                              "input_sha256": coding.digest(data), "input_length": len(data),
                              "actual_row_bytes": len(encoded[0]), "basis": chosen, "sets": []}
                    report["configurations"].append(config)
                    for pair in range(12):
                        order = ["historical", "optimized"]
                        rng.shuffle(order)
                        record = {"pair": pair, "order": order, "arms": {}}
                        config["sets"].append(record)
                        for arm in order:
                            start, cpu = time.perf_counter_ns(), time.thread_time_ns()
                            for _ in range(100):
                                result = functions[arm]()
                            used, elapsed = time.thread_time_ns()-cpu, time.perf_counter_ns()-start
                            if result != expected_output:
                                raise AssertionError("Timed output differs")
                            record["arms"][arm] = {"thread_cpu_ns": used, "wall_ns": elapsed}
                    config["comparisons"] = {}
                    for metric in ("thread_cpu_ns", "wall_ns"):
                        ratios = [s["arms"]["optimized"][metric] / s["arms"]["historical"][metric]
                                  for s in config["sets"] if min(s["arms"][a][metric] for a in ("historical", "optimized")) > 0]
                        config["comparisons"][metric] = bootstrap(ratios, SEED) if len(ratios) == 12 else {"status": "INSUFFICIENT_CLOCK_RESOLUTION", "positive_pairs": len(ratios)}
                    config["medians_ms"] = {arm: {metric: statistics.median(s["arms"][arm][metric] for s in config["sets"])/1e6
                                                            for metric in ("thread_cpu_ns", "wall_ns")} for arm in ("historical", "optimized")}
                    print(profile, unit, operation, config["comparisons"], flush=True)
        report["success"] = True
    except Exception as error:
        report["error"] = repr(error)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if not report["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
