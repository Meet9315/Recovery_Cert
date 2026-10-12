# Registered authenticated read-result reuse comparison

Version 1 — 12 October 2026. Freeze source, integrity tests and this protocol before outcomes. Preserve all milestone 6–8 protocols and reports, including the interrupted campaign. Do not reuse historical timing data as a new-code control.

## Implemented change and comparator

The common validator reads authentic LIVE rows, reconstructs the content, checks coding consistency/padding, compares original content digest and every regenerated row digest, then returns that authenticated immutable byte string. `_valid_rows` keeps its prior two-item interface for repair/worker/audit callers. Both public read APIs return the authenticated result directly. No cross-request byte cache, removed check, new pin, metadata/receipt format or changed fallback policy is introduced.

The benchmark-only redundant comparator reconstructs a second time from the validated in-memory rows, using the same current validator, read transaction type and snapshot-to-serialized fallback. It is installed only on a disposable foreground/read-fixture instance; the production class is not patched. This isolates the removed decode sequence with a common current repair controller. It is a mechanism comparator, not a separate frozen historical installation, selective-continuation benchmark or production baseline weakened to favour reuse. The common validator has a small extra helper frame relative to the historical code; that frame and all authenticity checks are shared.

## CPU confirmation

Eight configurations: both 2+1/4+2 **read-object** profiles, serialized/snapshot APIs, and 512/65,537-byte objects. Each pair uses two fresh identical fully protected stores, seeded content, distinct row domains and the same slot size `max(1024, ceil(length / data_rows))`. There is no repair/foreground process in this CPU experiment. Fixture creation, source/byte audits, reconstruction probes, pulse thread startup/stop and report processing are outside batch timing. Each correct byte comparison inside a read batch is timed.

For each configuration, warm both variants equally with one read. Outside timing, count real production `recover` calls: redundant=two and reuse=one per successful read. Calibrate reuse on a separate immutable store, starting at one read and doubling to at most 4,096 reads until process CPU reaches 200 ms. Retain all attempts. Freeze that repetition count for both variants and all ten pairs in the configuration. A measured batch must complete all exact-content reads and have at least 50 ms process CPU; unresolved CPU or any read/integrity error makes the campaign unsuccessful. Fresh paired stores contain the same content and model fingerprint. Independently reopen and check target/readback, no active plans and conserved capacity after each batch.

Use ten independently seeded pairs per configuration with saved randomized variant order. The primary metric is batch process CPU at identical repetition count; save per-read CPU and wall time too. Compare reuse with redundant using every paired percent reduction `100 * (redundant - reuse) / redundant`, its mean and a 2,000-resample deterministic pair bootstrap 95% percentile interval. No original 20% verification-CPU research decision is made: these are ordinary read-service costs, not isolated continuation verification or complete controller CPU. Preserve all eight configurations, including zero/negative or mixed effects.

## Liveness observations

A diagnostic thread samples process CPU, monotonic time, wall-clock time and PID approximately every 50 ms. Retain all raw samples and intervals whose monotonic gap is at least **500 ms** and overlaps the measured phase. Stop with a final sample so a delayed last interval remains visible. Flagged gaps stay in data and summaries; no favourable-only removal, replacement or recomputed unflagged subset is allowed. A gap records observation delay and does not identify suspension, CPU/GIL contention, I/O, clock behaviour or any other cause. No observed gap is not proof of an uninterrupted host. Pulse overhead during the measured phase is included equally in both variants.

## Monitored foreground diagnostics

Collect eight single windows: both **repair** profiles, local/worker paths and redundant/reuse read variants, using snapshot reads under the same conventional cached repair controller. The unrelated foreground object retains its default 2+1 profile and prior bytes. Reuse the 64-group backlog and fixed 400 control/400 loaded arrivals at 100 Hz from milestone 8. Randomize variant order; use identical seeded initial backlogs across each variant pair. All control reads drain before load; every offered loaded request remains included even if service starts/ends after restoration. Preserve all requests, scheduling/queue/service/end-to-end costs, stopping and drain times, fallback counts and post-run content/target/capacity audits.

Monitor both controller and reader processes with the same pulse policy from initialization-ready through request drain; classify gaps overlapping the control/load/drain window. Save phase origins/boundaries. These are **single diagnostic windows**, not a ten-pair foreground confirmation: do not calculate comparative p99 confidence intervals, evaluate the 5% foreground condition or claim a completed latency/research gate. Their purpose is to check collection integrity and show remaining queue/service interference after the read change. Future confirmation must give the same read improvement to both competent conventional and selective controllers.

## Failure, provenance and interpretation

Record protocol/source SHA-256, seed/order, all calibration/measured/diagnostic attempts, actual clocks and pulse records. Checkpoint after each attempted batch/window. Preserve error, traceback and measurement/checkpoint phase on failure. Console-output `OSError` is saved as nonfatal telemetry; measurement, integrity, file/checkpoint or process failures remain fatal. Never overwrite the historical original/continuation reports.

Correctness tests retain source corruption, content identity, generated missing-row identity, extra-row consistency, padding/length/profile, read-only snapshot enforcement, committed offline state, actual retire/reclaim fallback, worker/fence/receipt/process-exit and coding-oracle coverage. No remote daemon, independent device, power-loss, mutable-content, selective-mode inventive advantage or patentability rating follows from this conventional coding-work reuse.
