"""Diagnostic process pulses; gaps indicate observation delay, not its cause."""

import os
import threading
import time

PERIOD_NS = 50_000_000
GAP_NS = 500_000_000


def pulse_report(samples, start_ns=None, end_ns=None):
    gaps = []
    for left, right in zip(samples, samples[1:]):
        if start_ns is not None and right["monotonic_ns"] < start_ns:
            continue
        if end_ns is not None and left["monotonic_ns"] > end_ns:
            continue
        gap = right["monotonic_ns"] - left["monotonic_ns"]
        if gap >= GAP_NS:
            gaps.append({"start_ns": left["monotonic_ns"], "end_ns": right["monotonic_ns"],
                         "monotonic_gap_ns": gap, "wall_delta_ns": right["wall_ns"] - left["wall_ns"],
                         "process_cpu_delta_ns": right["process_cpu_ns"] - left["process_cpu_ns"]})
    return {"samples": samples, "period_ns": PERIOD_NS, "gap_threshold_ns": GAP_NS,
            "gaps": gaps, "gap_flagged": bool(gaps), "cause_identified": False,
            "observation_start_ns": start_ns, "observation_end_ns": end_ns}


class Pulse:
    def __init__(self):
        self.samples, self.stop_event = [], threading.Event()
        self.thread = None

    def sample(self):
        self.samples.append({"monotonic_ns": time.perf_counter_ns(), "wall_ns": time.time_ns(),
                             "process_cpu_ns": time.process_time_ns(), "pid": os.getpid()})

    def start(self):
        self.sample()
        def collect():
            while not self.stop_event.wait(PERIOD_NS / 1e9):
                self.sample()
        self.thread = threading.Thread(target=collect, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.stop_event.set()
        self.thread.join(5)
        if self.thread.is_alive():
            raise RuntimeError("Liveness pulse did not stop")
        self.sample()

    def __enter__(self):
        return self.start()

    def __exit__(self, *error):
        self.stop()

    def report(self, start_ns=None, end_ns=None):
        return pulse_report(self.samples, start_ns, end_ns)
