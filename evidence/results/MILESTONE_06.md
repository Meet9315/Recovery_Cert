# Milestone 6: actual durable controller comparison

Completed locally on 12 October 2026, Python 3.11.4 / SQLite 3.42.0 / Windows. The [raw report](controller-benchmark-milestone-06.json) records all eight configurations, **80 paired runs and 240 measured completed repair groups**, with zero failed attempts. All batch sizes calibrated to one attempt at the registered 50 ms CPU floor. Twenty-four warm-ups and eight calibration attempts are retained separately and excluded from comparisons. All 27 source/test hashes and the protocol hash match the measured checkout.

The [full regression report](verification-milestone-06.json) passed **100 test methods and 288 subtests**, with no failures/errors. It retains all 37 actual process-exit cases. The separate 10,000-trace legacy model and 720-case 4+2 campaigns again observed zero invariant violations/disagreements. All 27 source/test hashes match the benchmark versions and final checkout. Four new integrity methods check actual restoration across modes/profiles, child and receipt-lookup CPU accounting, insufficient samples, zero timers and the minimum run count. Performance outcomes are not asserted as correctness tests.

## Implemented experiment

The `controller-benchmark` CLI measures real storage execution with planning, admission, source reconstruction/checks, SQLite persistence, fsync, cache work, worker dispatch and durable receipt reconciliation. The comparator is the deployed conventional cached controller; full replay is an ablation. Both profiles, 2/8 repair stripes and local/worker paths form eight configurations with ten independently seeded paired runs each. Modes execute identical content, capacity, protection and conventional repair witnesses in freshly created stores, with randomized order.

The [protocol](../../experiments/controller_protocol.md) was frozen in commit [e9d84f3f83f222d5c5918f4e7562cd29df23823a](https://github.com/Meet9315/Recovery_Cert/commit/e9d84f3f83f222d5c5918f4e7562cd29df23823a), before comparison results were collected. Its SHA-256 is `c28484856ff83b4d35ab7c88e932b2c582891765d4b5c6fc15e16f8e89d97a0d`. A benchmark-only worker envelope records process CPU through durable handler completion without changing production receipts or authorization. Child output/teardown costs are excluded and disclosed; foreground reader CPU is separate.

Fixture creation, bootstrap, worker enabling and foreground startup/control are excluded. Timed operations include equal ledger observations after admission and every transition. Outside timing, every attempt checks original bytes after reopening, terminal safety and absence of active plans. Cross-mode witness digests must match. Calibration and warm-ups are retained separately. Exceptions preserve a failed partial report and stop the campaign; failed attempts cannot become completed repairs.

## Paired results

Each cell below is a mean within-run percentage reduction for selective versus the conventional cached baseline, followed by its seeded bootstrap 95% interval. Positive means selective uses less CPU or restores faster; negative means more CPU or slower restoration. These effects are not ratios of unpaired mode medians.

| Profile | Stripes | Path | CPU reduction % (95% interval) | Restoration reduction % (95% interval) |
|---|---:|---|---|---|
| 2+1 | 2 | Local | -4.78 (-34.38, 22.83) | -11.53 (-32.03, 6.21) |
| 2+1 | 2 | Workers | -4.99 (-13.84, 4.05) | -2.18 (-13.46, 7.68) |
| 2+1 | 8 | Local | -4.69 (-12.71, 3.36) | -6.30 (-16.64, 3.22) |
| 2+1 | 8 | Workers | 1.00 (-3.22, 4.96) | -0.62 (-3.14, 1.96) |
| 4+2 | 2 | Local | 3.82 (-7.31, 16.31) | -1.71 (-17.57, 12.03) |
| 4+2 | 2 | Workers | -1.82 (-5.61, 2.48) | 6.04 (0.78, 10.28) |
| 4+2 | 8 | Local | -4.81 (-8.20, -1.42) | 0.59 (-4.83, 5.83) |
| 4+2 | 8 | Workers | -1.39 (-3.67, 1.11) | -0.95 (-2.97, 1.34) |

Median controller-plus-worker CPU milliseconds per repaired stripe (warm-ups/calibration excluded):

| Profile | Stripes | Path | Conventional cached | Selective | Full replay |
|---|---:|---|---:|---:|---:|
| 2+1 | 2 | Local | 70.31 | 66.41 | 58.59 |
| 2+1 | 2 | Workers | 582.03 | 621.09 | 601.56 |
| 2+1 | 8 | Local | 96.68 | 95.70 | 89.84 |
| 2+1 | 8 | Workers | 642.58 | 625.98 | 621.09 |
| 4+2 | 2 | Local | 136.72 | 125.00 | 148.44 |
| 4+2 | 2 | Workers | 1,093.75 | 1,128.91 | 1,125.00 |
| 4+2 | 8 | Local | 226.56 | 236.33 | 227.54 |
| 4+2 | 8 | Workers | 1,284.18 | 1,300.78 | 1,287.11 |

None of the eight configurations meets even the point-estimate proxy threshold of 20% CPU reduction or 10% restoration improvement versus the capable baseline. The 4+2 local eight-stripe configuration uses 4.81% more CPU (slowdown interval 1.42%–8.20%). The small 4+2 worker configuration restores 6.04% faster on average, but its CPU estimate is a 1.82% increase and its restoration interval does not establish the required 10% improvement. All other CPU/restoration intervals include no effect. These findings do not demonstrate the overall research target.

No measured attempt has the registered minimum 200 foreground observations in both phases. Foreground p99 comparison is **insufficient in all eight configurations**, with zero threshold evaluations. The raw latencies and achieved sample counts remain available; absent adequate evidence is not reported as success. The full-replay ablation and all unfavourable workloads remain in the raw report.

## Reproduce and next work

```powershell
python -m prism_c controller-benchmark --report evidence/results/controller-benchmark-new.json --runs 10 --seed 20261012
python -m prism_c verify --report evidence/results/verification-milestone-06-new.json --traces 10000 --seed 20261011
```

The measured campaign took about 28 minutes on this machine; this is not a CI performance test. The comparison writes checkpoints after each complete pair and uses disposable temporary stores. CI runs the four new measurement-integrity tests and existing correctness campaigns, not the full performance campaign.

Next engineering task: register longer foreground control/repair windows with explicit boundary-spanning read accounting, profile verification and persistence costs separately, then add fault/retry and scoped-contention comparisons. Keep the same capable baseline and research thresholds. Optimizations require fresh registered confirmation; the present results must remain preserved.

## Interpretation limits

This is a local no-fault/reclamation experiment on simulated domains, not independent storage hardware. CPU is broad controller-plus-worker overhead, not isolated verification CPU or aggregate kernel/I/O resource accounting. Fixed 1,025-byte objects, Python GF arithmetic, repeated interpreter launches and serialized metadata/source checks limit extrapolation. Ten paired runs support descriptive seeded bootstrap intervals; timer quantization and host scheduling can produce wide intervals.

Foreground observations cover calls entirely within the registered control or repair window. Calls crossing phase boundaries are excluded, so these timings do not capture all boundary-spanning stalls or a fixed-arrival-rate workload. Sample adequacy alone would not remove that limitation. Insufficient p99 samples must not be relabelled as passing the 5% research threshold. A future latency protocol needs longer controls/repair windows and explicit accounting for calls completing after restoration.

The original G6 evaluation still needs isolated verification-CPU attribution, fault/retry/contention performance, adequate foreground latency evidence and broader workload/hardware evaluation. The competent baseline remains the default; the earlier 53/100 assessment and conditional 73/100 target are unchanged. Correctness or process separation alone earns no new novelty points.
