# Milestone 2: Selective validation and conventional-cache comparison

Date: 11 October 2026.

## Outcome

Selective component validation is implemented and passes the declared correctness checks. It does **not** beat the conventional guarded cache on the measured workloads. The runtime therefore defaults to the conventional cache; component caching remains an explicit experimental mode. This milestone does not establish the conditional patent target or the overall controller performance target.

## Implementation

- Derive complete stripe/slot membership internally, including future action destinations and anonymous reclamation.
- Merge dependencies when different stripes use the same action slot.
- Reuse a checked component suffix only when its projected start, membership and remaining actions match.
- Replay changed components; rebuild when membership or cache representation is incompatible.
- Bind persisted evidence to witness digest, cursor, authority incarnation and checker version.
- Commit evidence advancement with the plan cursor and allocation/manifest update.
- Retain source-byte validation, staged receipts, pins, holds, current-step replay and fencing.
- Provide full, conventional cached, selective and shadow modes. Shadow also performs full replay at each step.

The terminal fingerprint remains exact: a policy change that leaves decoding safe can still invalidate the committed witness. Membership is scanned, not backed by a new writer-maintained dependency index. One group plan is still serialized.

## Correctness evidence

See [verification-milestone-02.json](verification-milestone-02.json) and [demo-milestone-02.json](demo-milestone-02.json).

| Check | Result |
|---|---|
| Test methods | 52 passed |
| Reported subtests | 95 |
| Actual subprocess interruption cases | 18, including three selective-cache/cursor interruption cases |
| Seeded traces | 10,000 |
| Distinct initial configurations | 2,479 |
| Distinct visited model states | 3,772 |
| Selective/full suffix comparisons | 46,282, no disagreement |
| Cached component reuses in campaign | 138,846 |
| Malformed-generation checks | 92,564 |
| Observed invariant violations | 0 |
| Real-byte shadow demonstration | Both original objects recovered; full-reference agreement at each step |

The mutation tests cover source/destination changes, offline domains, policy changes, phantom membership, inserted capacity, stale incarnations, omitted cache coverage, incompatible cache versions, missing cache, mode switching and corrupted source bytes. Tests do not prove all possible interleavings or hardware faults.

## Logical CPU comparison

The [registered protocol](../../experiments/protocol.md) compares identical continuations across three modes. [selective-benchmark.json](selective-benchmark.json) preserves ten paired runs per configuration, raw batched CPU/wall measurements, preparation/step measurements, source hashes and bootstrap intervals.

Confirmation protocol version 2 uses freshly reconstructed equal snapshots at every step and the deployed cache classes. Batch repetition counts are calibrated to at least 50 ms of conventional-cache CPU because this Windows CPU clock quantizes short operations. The outer timer includes common harness/readback overhead. The earlier simpler implementation is preserved in [selective-benchmark-exploratory.json](selective-benchmark-exploratory.json); it is not combined with confirmation results.

| Stripes | Diagnostic annotations | Median full CPU ms/sequence | Median selective CPU ms/sequence | Median conventional cached CPU ms/sequence | Mean paired selective CPU reduction vs full | Mean paired selective CPU overhead vs cached |
|---|---|---:|---:|---:|---:|---:|
| 2 | No | 1.465 | 2.197 | 1.221 | -47.4% | +98.2% |
| 2 | Yes | 1.709 | 2.197 | 1.343 | -35.4% | +64.2% |
| 8 | No | 31.250 | 23.438 | 15.625 | +10.0% | +83.0% |
| 8 | Yes | 27.344 | 25.391 | 13.672 | +4.6% | +79.4% |
| 16 | No | 171.875 | 93.750 | 54.688 | +42.5% | +84.8% |
| 16 | Yes | 175.781 | 93.750 | 54.688 | +43.3% | +70.1% |

Mean paired percentage changes are computed for each run before averaging; they are not ratios of table medians. A negative reduction denotes a slowdown. Diagnostic annotations affect neither state nor authority and are processed equally by all modes; they do not demonstrate useful locality under concurrent repair.

At 16 stripes without annotations, the bootstrap 95% interval for reduction against full replay was 39.7%–44.9%, while selective overhead against the conventional cache was 72.9%–98.6%. At 8 stripes the reduction intervals against full replay included zero. These are indicative single-machine estimates from ten paired batches with coarse CPU quantization, not deployment-wide confidence claims.

## Interpretation and next hypothesis

Avoiding repeated full suffix replay reduces work for larger groups. Conventional caching already obtains that benefit more cheaply when the state follows one serialized continuation. Component partitioning, full membership scans, witness hashing and terminal merging add overhead without demonstrating a compensating advantage here.

The proposed 20% target against a capable baseline is **not met**. Physical I/O, SQLite cache persistence, serialization, source checks, foreground latency and practical temporary-space/restoration effects are not measured in this microbenchmark. No controller-level performance claim follows.

The next engineering hypothesis is compatible concurrent continuation scopes: can independent plans proceed safely without whole-group exclusion, and does that create a useful advantage beyond standard scoped reservations/caching? That requires a new specification and equally capable baseline before another performance claim. It is not an established inventive contribution.

The earlier patentability assessment remains unchanged. Correctness progress improves implementation evidence, but these comparisons do not establish novelty or inventive step.
