"""Benchmark-only worker telemetry, including an intentional lost acknowledgement."""

import json
import os
from pathlib import Path
import sys
import time

from .model import Rejected
from .worker import canonical, handle


def main():
    request = json.load(sys.stdin)
    record = {"pid": os.getpid(), "operation": request["operation"], "worker": int(sys.argv[2]),
              "fault_point": request.get("fault_point"), "exit_code": 0}
    try:
        value = handle(sys.argv[1], int(sys.argv[2]), request)
        if request.get("fault_point") == "after_worker_commit":
            record["exit_code"] = 77
            record["cpu_ns"] = time.process_time_ns()
            Path(sys.argv[3]).write_text(canonical(record), encoding="utf-8")
            os._exit(77)
        result = {"value": value}
    except (Rejected, ValueError, KeyError) as error:
        record["error"] = str(error)
        result = {"error": str(error)}
    record["cpu_ns"] = time.process_time_ns()
    Path(sys.argv[3]).write_text(canonical(record), encoding="utf-8")
    print(canonical(result))


if __name__ == "__main__":
    main()
