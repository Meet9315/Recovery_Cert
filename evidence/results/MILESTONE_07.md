# Milestone 7: foreground sampling and CPU attribution

12 October 2026. The collector now retains foreground calls that finish after repair stops, and separates the control phase from repair with a pause/drain acknowledgement. Twelve longer diagnostic windows all reached the 400-read collection target in both phases. Twelve separate CPU profiles expose function costs and a declared logical-verification subset. These are measurement diagnostics, not an independent paired confirmation, a performance target pass or new patentability evidence.

## Registration and integrity

The [protocol](../../experiments/measurement_diagnostics_protocol.md), runner and seven integrity tests were frozen in commit [8440bbf9e8c1c14e401a7e8328cd15a814591d82](https://github.com/Meet9315/Recovery_Cert/commit/8440bbf9e8c1c14e401a7e8328cd15a814591d82) before collecting outcomes. Protocol SHA-256: `ec3f28289609c9280d26d864c4acf2db4079e5699bd9f9017c80e2d4bc71d88a`. All 30 source/test hashes in the [raw report](measurement-diagnostics-milestone-07.json) match the registered code. The milestone 6 protocol and raw paired data are preserved unchanged.

All twelve windows completed without errors: **4,815 control reads, 6,036 loaded reads, 12 retained boundary reads**, and **67 completed two-stripe repair groups**. Every completed scope reached its restoration target, all original bytes matched after reopening, the untouched backlog retained its safety floor, and managed capacity was conserved. All windows stopped after satisfying minimum duration and sample targets; none exhausted the backlog or stopped at its deadline. All twelve CPU fixtures restored their original bytes and target. Worker profiles cover 54 RPCs, including execute and durable receipt lookup.

## Foreground observations

Times are milliseconds. Ratio is loaded p99 divided by that window's no-repair control p99. Each row is one closed-loop diagnostic window; **no confidence interval, mode comparison or 5% research-threshold decision is made**. Loaded request membership is determined by starting during repair, including calls ending after restoration. Every row retained one such boundary call.

| Coding/path | Mode | Control reads | Loaded reads | Groups | Control p99 ms | Loaded p99 ms | Ratio |
|---|---|---:|---:|---:|---:|---:|---:|
| 2+1 local | conventional_cached | 401 | 405 | 11 | 12.015 | 60.577 | 5.04 |
| 2+1 local | selective | 402 | 415 | 11 | 12.386 | 57.633 | 4.65 |
| 2+1 local | full | 402 | 436 | 12 | 18.304 | 57.987 | 3.17 |
| 2+1 workers | conventional_cached | 401 | 496 | 3 | 13.061 | 374.239 | 28.65 |
| 2+1 workers | selective | 401 | 544 | 3 | 17.831 | 335.656 | 18.82 |
| 2+1 workers | full | 401 | 546 | 3 | 11.511 | 346.296 | 30.08 |
| 4+2 local | conventional_cached | 401 | 405 | 7 | 13.957 | 90.768 | 6.50 |
| 4+2 local | selective | 401 | 421 | 6 | 14.862 | 84.867 | 5.71 |
| 4+2 local | full | 402 | 435 | 6 | 9.179 | 108.815 | 11.85 |
| 4+2 workers | conventional_cached | 401 | 408 | 1 | 12.966 | 278.998 | 21.52 |
| 4+2 workers | selective | 401 | 733 | 2 | 23.538 | 296.788 | 12.61 |
| 4+2 workers | full | 401 | 792 | 2 | 11.391 | 296.910 | 26.06 |

Control durations were 2.08–3.14 seconds; loaded durations were 5.07–11.82 seconds. Raw timestamps, final-request drain time, errors/outcomes, witness digests and group timings are retained. Loaded p99 was 3.17–30.08 times control in these observations. Foreground contention therefore remains a practical concern. Variable stopping rules produce different completed-group counts; these data must not be used as paired CPU/restoration effects or evidence that one mode has less latency than another.

The backlog has 64 two-stripe groups in shared domains. Its first half has retired destination slots, following deterministic first-free fixture seeding; early groups reclaim both destination slots. Its remaining half uses free slots. All groups completed in this run were in the first half. This differs from the single-group CPU fixture, which has one retired destination slot per destination domain. Setup and subsequent independent audits are outside measurement. The reader calls the real authority API on an unrelated fully protected object; it is closed-loop and cannot establish open-loop saturation or independent-device performance.

## Instrumented CPU observations

Each row is a separate single-group profile without a foreground process. Values are rounded milliseconds. Parent and whole-worker CPU are disjoint process totals; logical spans and coding self costs are **overlapping views of the parent total**, not additional costs to sum. Logical spans cover replay/certificates, state/witness commitments and claims/fence checking; physical checks and snapshot construction are excluded from that subset.

| Coding/path | Mode | Parent CPU ms | Whole-worker CPU ms | Logical subset ms | Coding self ms |
|---|---|---:|---:|---:|---:|
| 2+1 local | conventional_cached | 359.375 | 0 | 46.875 | 125.000 |
| 2+1 local | selective | 359.375 | 0 | 78.125 | 125.000 |
| 2+1 local | full | 265.625 | 0 | 78.125 | 93.750 |
| 2+1 workers | conventional_cached | 515.625 | 2,359.375 | 109.375 | 78.125 |
| 2+1 workers | selective | 609.375 | 2,015.625 | 62.500 | 125.000 |
| 2+1 workers | full | 562.500 | 2,765.625 | 15.625 | 140.625 |
| 4+2 local | conventional_cached | 796.875 | 0 | 62.500 | 281.250 |
| 4+2 local | selective | 750.000 | 0 | 109.375 | 281.250 |
| 4+2 local | full | 703.125 | 0 | 31.250 | 296.875 |
| 4+2 workers | conventional_cached | 1,265.625 | 4,156.250 | 156.250 | 453.125 |
| 4+2 workers | selective | 1,265.625 | 3,734.375 | 250.000 | 390.625 |
| 4+2 workers | full | 1,156.250 | 3,718.750 | 109.375 | 265.625 |

Coding and SQLite are prominent exclusive categories in these instrumented executions. Per-function call counts, exclusive and inclusive costs, exclusive category totals, all logical span calls and each worker-handler profile are saved. Each exclusive function cost is assigned once; nested span intervals are added only at the outermost level. Inclusive profiler costs overlap and must not be summed.

The observed CPU values are quantized in approximately 15.625 ms increments on this Windows machine. Individual small functions can receive zero or unstable costs despite finer reported nominal clock resolution. Profiling adds overhead. Whole-worker CPU includes startup/imports and instrumentation through handler completion, but excludes profile-report processing, output and teardown. These single profiles do not establish production cost shares, selective-mode savings, confidence intervals or the original isolated-verification-CPU target.

## Correctness verification

The [full verification report](verification-milestone-07.json) passed **107 test methods and 288 subtests**, with no failures/errors, retaining all 37 actual process-exit regression cases. Seven new integrity tests cover an actual SQLite-blocked read drained after the stop boundary, live control/load phase separation, exception-safe restoration of profiling wrappers, receipt lookup profiling, no nested double-counting and preserved failure context. All 30 source/test hashes match the registered diagnostic code and the measurement report.

The separate 10,000-trace legacy campaign again covered 2,479 initial configurations, 3,772 visited states, 46,282 validated actions/cache-reference comparisons, 92,564 malformed-generation checks and 138,846 component reuses with zero observed invariant violations. The independent 4+2 campaign checked all 65,536 field products, 15 nonzero reconstruction minors, 180 reconstructions and 720 finite repair cases (60 feasible, 660 infeasible), with 840 cache/reference comparisons and 840 stale-incarnation checks and zero observed disagreement. These counts retain their previous finite/local scope; they do not prove arbitrary concurrency, power-loss durability or novelty.

## Interpretation and next work

The sampling deficiency in milestone 6 is addressed for these longer diagnostic windows. Its original 80-pair comparison still reports insufficient foreground p99 and unmet CPU/restoration proxy targets; the two experiments have different workloads and must not be merged. Conventional caching remains the default. The earlier **53/100 assessment and conditional 73/100 target remain unchanged**; G2/G6 and novelty/inventive-step review remain unresolved.

Next, register independent paired foreground windows and strengthen the arrival workload. Investigate the authority transaction path and repeated physical reconstruction/checking identified by these diagnostics, preserving all safety checks and using fresh confirmation for any optimization. Fault/retry and scoped-contention comparisons remain pending. Authenticated remote workers, real device/host boundaries and the priority/inventorship records are separate unfinished work.

```powershell
python -m prism_c measurement-diagnostics --report evidence/results/measurement-diagnostics-new.json --seed 20261012
python -m prism_c verify --report evidence/results/verification-milestone-07-new.json --traces 10000 --seed 20261011
```
