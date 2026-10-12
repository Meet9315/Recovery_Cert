"""Benchmark-only worker envelope; durable commands/receipts are unchanged."""

import json
import sys
import time

from .model import Rejected
from .worker import canonical, handle


def main():
    request = json.load(sys.stdin)
    try:
        value = handle(sys.argv[1], int(sys.argv[2]), request)
    except (Rejected, ValueError, KeyError) as error:
        print(canonical({"error": str(error)}))
        return
    # Process CPU includes interpreter startup/imports and receipt commit;
    # output serialization/printing and teardown follow the observation.
    print(canonical({"value": value, "benchmark_cpu_ns": time.process_time_ns()}))


if __name__ == "__main__":
    main()
