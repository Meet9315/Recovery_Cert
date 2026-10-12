"""Diagnostic CPU profiles and non-overlapping logical verification spans."""

from contextlib import contextmanager, ExitStack
import cProfile
from functools import wraps
from pathlib import Path
import pstats
import time
from unittest.mock import patch


def category(filename, name):
    path = filename.replace("\\", "/")
    base = path.rsplit("/", 1)[-1]
    if base == "checker.py":
        return "logical_replay"
    if base == "selective.py":
        return "continuation_certificates"
    if base in ("model.py", "scope.py"):
        return "state_and_scope"
    if base == "coding.py":
        return "coding"
    if filename == "~":
        if "sqlite3" in name:
            return "sqlite"
        if "HASH" in name or "sha256" in name:
            return "hashing"
        if "_io." in name or "fsync" in name or "io.open" in name:
            return "file_io"
        if "_winapi" in name or "waitpid" in name:
            return "worker_transport"
    if "/json/" in path or base in ("dataclasses.py", "copy.py"):
        return "serialization_and_materialization"
    if base == "subprocess.py":
        return "worker_transport"
    if base == "worker.py":
        return "worker_authorization"
    if base == "worker_authority.py":
        return "worker_control"
    if base == "storage.py":
        return "source_integrity" if name == "_valid_rows" else "authority_orchestration"
    if base == "baseline.py":
        return "scheduler"
    if base in ("cpu_attribution.py", "measurement_diagnostics.py"):
        return "diagnostic_harness"
    return "runtime_other"


def profile_report(profiler):
    entries, totals = [], {}
    root = Path(__file__).resolve().parent.parent
    for (filename, line, name), (primitive, calls, exclusive, inclusive, _) in pstats.Stats(profiler).stats.items():
        group = category(filename, name)
        # Integer nanoseconds are explanatory profiler values, not timer precision.
        self_ns, inclusive_ns = round(exclusive * 1e9), round(inclusive * 1e9)
        totals[group] = totals.get(group, 0) + self_ns
        try:
            display = Path(filename).resolve().relative_to(root).as_posix()
        except ValueError:
            display = filename
        entries.append({"file": display, "line": line, "function": name, "category": group,
                        "primitive_calls": primitive, "total_calls": calls,
                        "exclusive_cpu_ns": self_ns, "inclusive_cpu_ns": inclusive_ns})
    entries.sort(key=lambda item: (-item["exclusive_cpu_ns"], item["file"], item["line"], item["function"]))
    return {"exclusive_categories_cpu_ns": totals, "total_exclusive_cpu_ns": sum(totals.values()),
            "functions": entries, "timer": "time.process_time", "inclusive_costs_overlap": True,
            "instrumentation_overhead_included": True}


class LogicalSpans:
    """Single-controller-thread diagnostic: only outermost intervals are added."""
    def __init__(self, clock=time.process_time_ns):
        self.clock, self.depth, self.records = clock, 0, {}

    def wrap(self, label, function):
        @wraps(function)
        def measured(*args, **kwargs):
            record = self.records.setdefault(label, {"calls": 0, "outer_calls": 0, "outer_cpu_ns": 0})
            record["calls"] += 1
            outer = self.depth == 0
            start = self.clock() if outer else None
            self.depth += 1
            try:
                return function(*args, **kwargs)
            finally:
                self.depth -= 1
                if outer:
                    record["outer_calls"] += 1
                    record["outer_cpu_ns"] += self.clock() - start
        return measured

    def report(self):
        return {"apis": self.records, "outer_cpu_ns": sum(r["outer_cpu_ns"] for r in self.records.values()),
                "nested_intervals_added": False,
                "scope": "Logical replay/certificates, state/witness commitments, claims/fence checking; physical checks excluded"}


@contextmanager
def logical_spans():
    from . import checker, selective, storage, worker_authority
    from .model import State, Witness
    spans = LogicalSpans()
    with ExitStack() as stack:
        for module in (checker, selective, storage, worker_authority):
            for name in ("check", "replay"):
                if hasattr(module, name):
                    stack.enter_context(patch.object(module, name, spans.wrap(f"{module.__name__}.{name}", getattr(module, name))))
        for kind, names in ((selective.ContinuationCache, ("build", "from_json", "to_json", "validate", "advance")),
                            (selective.WholeSuffixCache, ("build", "from_json", "to_json", "validate", "advance")),
                            (State, ("fingerprint",)), (Witness, ("digest", "from_dict")),
                            (storage.Authority, ("_check_claims", "_fence"))):
            for name in names:
                descriptor = kind.__dict__[name]
                if isinstance(descriptor, classmethod):
                    replacement = classmethod(spans.wrap(f"{kind.__name__}.{name}", descriptor.__func__))
                else:
                    replacement = spans.wrap(f"{kind.__name__}.{name}", descriptor)
                stack.enter_context(patch.object(kind, name, replacement))
        yield spans


def new_profiler():
    return cProfile.Profile(timer=time.process_time)
