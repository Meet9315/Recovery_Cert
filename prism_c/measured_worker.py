"""Benchmark-only worker envelope; durable commands/receipts are unchanged."""

import json
import sys
import time

from .model import Rejected
from .worker import canonical, handle


def main():
    request = json.load(sys.stdin)
    profiler = None
    if request.get("benchmark_profile"):
        from .cpu_attribution import new_profiler, profile_report
        profiler = new_profiler()
    try:
        if profiler is not None:
            profiler.enable()
        value = handle(sys.argv[1], int(sys.argv[2]), request)
    except (Rejected, ValueError, KeyError) as error:
        print(canonical({"error": str(error)}))
        return
    finally:
        if profiler is not None:
            profiler.disable()
    # Process CPU includes interpreter startup/imports and receipt commit;
    # output serialization/printing and teardown follow the observation.
    cpu_ns = time.process_time_ns()
    envelope = {"value": value, "benchmark_cpu_ns": cpu_ns}
    if profiler is not None:
        envelope["benchmark_profile"] = profile_report(profiler)
    print(canonical(envelope))


if __name__ == "__main__":
    main()
