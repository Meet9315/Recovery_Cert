# Milestone 9: authenticated read-result reuse

12 October 2026. Both read APIs now return the content already reconstructed and authenticated by the common validator. This removes a redundant decode without removing row, coding/padding, generated-row or content-identity checks. The registered 80-pair CPU comparison finds 44%–47% lower read CPU for 65,537-byte objects; 512-byte effects remain inconclusive. Eight monitored foreground windows completed, with no observed 500 ms pulse gaps. These single windows do not establish a foreground or overall research-gate pass. Full local verification passed 129 methods and 318 subtests.

## Implementation and safety

`_validated_content` contains the prior complete source validator and returns its authenticated immutable bytes along with metadata and live rows. `_valid_rows` retains its two-item interface for repair, worker preparation and audit. `read` and `read_snapshot` return the authenticated bytes directly. Snapshot reconstruction rejection still closes its transaction before one serialized fallback; other I/O/database errors propagate. Serialized reads and conventional caching remain defaults, and snapshot reads/workers remain opt-in.

No cross-request byte cache, removed physical check, changed row profile, migrated metadata, altered receipt, new source pin or relaxed repair authority is introduced. New tests cover missing-row identity checks before content return, authentic but inconsistent extra rows, empty/odd/65,537-byte contents, both coding profiles and read APIs. The prior actual retire/reclaim race and source/content corruption tests remain regressions. The source-I/O failure test now injects at `_io` rather than coupling it to the old validator helper name. See the [snapshot contract](../../spec/snapshot_reads.md).

The benchmark-only redundant comparator performs the former second decode using the same current validator, transaction and fallback policy, on a disposable instance. It does not patch the production class. Separate untimed probes observe two real reconstruction calls for redundant reads and one for reuse. This is a mechanism comparison with a common current validator, not a replay of a historical executable or a selective-continuation benchmark.

## Registration and provenance

The [protocol](../../experiments/read_reuse_protocol.md), implementation and eight new integrity tests were frozen in commit [1dca27fe3c192a74f6a9d244079597d839383da5](https://github.com/Meet9315/Recovery_Cert/commit/1dca27fe3c192a74f6a9d244079597d839383da5) before outcomes. Protocol SHA-256: `978ef4c51c6d0316d0a70585a712d01002171592cf55874d51230335b37081ab`. All 38 recorded source/test hashes in the [raw report](read-reuse-milestone-09.json) match that Git version. All historical milestone 6–8 protocols/data remain unchanged.

After measurement finished, only `tests/test_snapshot_latency.py` and `tests/test_read_reuse_benchmark.py` changed to correct a fast-host fixture problem; production/measurement source remains exactly the frozen version. The full verification report records the final test hashes separately. These test-only corrections did not enter or alter the completed timing data.

## CPU confirmation

Both read-object profiles, both APIs and 512/65,537-byte lengths give eight configurations, each with ten seeded pairs and randomized variant order. Each pair uses fresh identical fully protected stores. All 160 measured batches completed **2,640 exact-content reads** and passed independent reopened target/readback and capacity checks. Calibration retained 35 attempts; reuse reached at least 200 ms CPU before freezing the repetition count for both variants. All confirmation batches met the 50 ms CPU minimum. Sixteen configuration warm-up/probe reads and the per-attempt decode probes are outside measurement.

Positive reduction means reuse used less process CPU at the same read count. Intervals are the predeclared 2,000 pair-resample bootstrap 95% intervals. No original 20% continuation-verification CPU target is evaluated; these are ordinary read-service CPU costs, including file/SQLite work, content comparisons and pulse overhead within the batch.

| Read profile | API | Bytes | Reads/batch | Mean CPU reduction % | 95% interval % |
|---|---|---:|---:|---:|---|
| 2+1 | serialized | 512 | 64 | 0.95 | [-6.76, 8.92] |
| 2+1 | serialized | 65,537 | 8 | 44.05 | [41.15, 46.60] |
| 2+1 | snapshot | 512 | 16 | 10.04 | [-1.39, 21.16] |
| 2+1 | snapshot | 65,537 | 4 | 46.35 | [41.34, 51.88] |
| 4+2 | serialized | 512 | 16 | -4.68 | [-20.10, 8.67] |
| 4+2 | serialized | 65,537 | 4 | 45.17 | [41.80, 48.53] |
| 4+2 | snapshot | 512 | 16 | 4.91 | [-12.56, 22.15] |
| 4+2 | snapshot | 65,537 | 4 | 47.34 | [45.63, 49.21] |

Every large-object interval is above zero; every small-object interval spans zero. The negative small 4+2 serialized point estimate is preserved. The data support this local large-read improvement, not an all-size improvement, precise production cost share, selective-mode advantage or patentability increase. Process CPU remains quantized on this Windows environment; batching limits but does not remove quantization and execution variability.

## Monitored foreground diagnostics

One snapshot-read window per repair-profile/path/variant gives eight single observations. The foreground object retains its default 2+1 profile and prior bytes; **repair profile** below refers to background repair. Both variants use the same conventional cached controller, 64-group backlog and fixed 400 control/400 loaded arrivals at 100 Hz. All **6,400 offered reads**, including queued calls served after restoration, are retained. Twenty-eight two-stripe groups completed; all post-run scope targets, original bytes, backlog safety floors and capacity checks passed. No fallback/read/telemetry error occurred.

P99 values are milliseconds. No per-configuration p99 effect/interval or 5% foreground condition is evaluated from these single windows. Counts differ under the registered stopping rule; group timings are not paired restoration/CPU effects.

| Repair/path | Variant | Groups | Control p99 ms | Loaded p99 ms | Loaded/control ratio |
|---|---|---:|---:|---:|---:|
| 2+1 local | redundant | 6 | 20.395 | 2,175.868 | 106.69 |
| 2+1 local | reuse | 8 | 13.245 | 1,724.434 | 130.20 |
| 2+1 workers | redundant | 1 | 33.012 | 90.873 | 2.75 |
| 2+1 workers | reuse | 2 | 14.055 | 107.847 | 7.67 |
| 4+2 local | redundant | 5 | 31.419 | 941.958 | 29.98 |
| 4+2 local | reuse | 4 | 10.882 | 1,287.443 | 118.31 |
| 4+2 workers | redundant | 1 | 9.348 | 51.689 | 5.53 |
| 4+2 workers | reuse | 1 | 11.467 | 281.504 | 24.55 |

Five hundred loaded calls ended after restoration and 496 started service afterward. These remain loaded observations by arrival membership. Removing duplicate decoding does not remove foreground queuing or service variability. A faster control can also increase the loaded/control ratio; improvement in ordinary read CPU cannot establish the own-control foreground condition.

Controller and reader pulse threads save monotonic time, wall time, process CPU and PID roughly every 50 ms, including a final sample at drain/stop. All raw intervals and the predeclared overlapping-gap classification are retained. **No gap of at least 500 ms was observed** in calibration, measured CPU batches or foreground/controller pulse records. This does not prove uninterrupted host execution or identify the cause of remaining latency. Monitoring overhead is included equally during measured work; no flagged sample subset is removed or re-estimated. The original milestone 8 interruption remains historical evidence, not repaired by these new observations.

## Prior CI issue and verification

The [milestone 8 GitHub run](https://github.com/Meet9315/Recovery_Cert/actions/runs/38237145341) failed on Ubuntu in `test_live_pair_uses_identical_backlog_and_preserves_phase_membership`: the two-group test backlog finished before all eight scheduled arrivals were offered, and the collector correctly rejected insufficient repair load. The Windows matrix job was cancelled by fail-fast; no remote Windows success is claimed for that run.

The live pair and live-monitor tests now use the production-sized 64-group backlog, preserving the scheduled phase and all assertions. A new empty-backlog regression confirms that zero repair work still rejects and does not become idle padding. The ten-method focused collector/comparator suite passed after this correction.

The [full local verification](verification-milestone-09.json) passed **129 methods and 318 subtests**, with no failures/errors and all 37 actual process-exit regression cases retained. All 38 final source/test hashes match current files. Production/measurement hashes match the frozen timing report; only the two corrected test files differ. The separate 10,000-trace legacy campaign again covered 2,479 initial configurations, 3,772 states, 46,282 validated actions/cache-reference comparisons and 92,564 malformed-generation checks with zero violations. The independent 4+2 campaign again checked 65,536 field products, 15 nonzero generator minors, 180 reconstructions and 720 finite repair cases with 840 cache/reference comparisons, 840 stale-incarnation checks and zero disagreement. Scope remains finite/local; no power-loss, independent-device or novelty proof is inferred.

Fresh [milestone 9 CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38265616092) completed successfully on **Ubuntu and Windows** for implementation/results commit `e04b84aab6b69837ce9376ce3628c17ab0fb81c6`. Each job runs the correctness/process-fault suite, 1,000 legacy model traces and the independent coding campaign. This clears the earlier fast-host fixture failure while preserving its historical record. The manual timing campaign is not rerun by CI.

## Interpretation and next work

This is a conventional optimization available equally to conventional and selective controllers. The earlier **53/100 assessment and conditional 73/100 target remain unchanged**. G2/G6, inventive interaction, independent fault domains and priority/inventorship review remain unresolved. Historical unmet proxy/foreground targets are not relabelled as passes.

Next, register fault/retry and scoped-contention performance with identical read improvements on both capable controllers, retaining monitor data and actual error outcomes. A fresh paired foreground confirmation is still required; these eight single windows do not replace it. Investigate ordinary source-validation/authority costs while retaining all physical checks. Remote workers and independent-device/power-loss evidence remain separate work.

```powershell
python -m prism_c read-reuse-benchmark --report evidence/results/read-reuse-new.json --runs 10 --seed 20261012
python -m prism_c verify --report evidence/results/verification-milestone-09-new.json --traces 10000 --seed 20261011
```

Run performance collection on its own; CI runs integrity/correctness tests and finite campaigns rather than the manual timing campaign. Historical continuation commands require their frozen source version because their source-integrity guard deliberately rejects the new optimized code.
