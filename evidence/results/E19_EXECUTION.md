# E19 shared conventional codec: implementation and complete measurements

16 October 2026. [Registered protocol](../../experiments/codec_optimization_protocol.md), [microbenchmark correction](../../experiments/codec_micro_correction.md), [complete evidence recomputation](e19-evidence-check.json). The shared codec optimization is implemented and verified. It establishes an ordinary engineering improvement, **not a distinguishing PRISM mechanism**. Readiness at this delivery stays 55/100.

Source CI commit [`e7fb8a6149cf7485bbb1539de9e2a17125b50ff7`](https://github.com/Meet9315/Recovery_Cert/commit/e7fb8a6149cf7485bbb1539de9e2a17125b50ff7). [Full local verification](verification-e19.json) passes **218 methods/687 subtests**, 10000 traces and all older campaigns; [Ubuntu/Windows CI](ci-e19.json) passes, with all **74 source/test hashes** matching the [Windows artifact](verification-e19-ci-windows.json). The only changed existing E18 runtime/test file is `prism_c/coding.py`; its new test module checks all 65536 field products through actual transforms, supported bases/redundant rows, zero/odd/padded/large data, corruption rejection, XOR and old-bytewise-encoded store compatibility.

The codec keeps exactly the same polynomial, generators, selected-basis order, row bytes and padding. Immutable translation tables, whole-buffer integer XOR and systematic identity-row reuse remove Python multiplication loops. All controller arms receive it. All content/row/regenerated-row checks, parity consistency and storage synchronization remain.

## Codec-only measurements

Both implementations receive the same deterministic input and parity-containing reconstruction basis; baseline bytes are loaded from the exact verified E18 Git blob. Twelve complete matched sets per eight configurations, randomized saved order, 100 operations/window. Five fresh processes per implementation measure module execution after common imports/compilation; this is not whole application startup.

The [first report](codec-batches-e19.json) is retained: its helper used `k*unit-3`, producing 63/4095-byte rows for 2+1 despite 64/4096 labels. Both arms still had identical bytes, but those labels were wrong. The [declared correction](../../experiments/codec_micro_correction.md) uses `k*unit-1`, asserts exact row sizes, records actual sizes/input/harness digests, and recollects every configuration in [report r2](codec-batches-e19-r2.json). No earlier result or unfavorable window was replaced.

| Profile | Actual row bytes | Encode optimized/old mean elapsed ratio | Recover optimized/old mean elapsed ratio |
|---|---:|---:|---:|
| 2+1 | 64 | 0.11452 | 0.22868 |
| 2+1 | 4096 | 0.00454 | 0.00748 |
| 4+2 | 64 | 0.07614 | 0.16762 |
| 4+2 | 4096 | 0.00520 | 0.00771 |

At 4096-byte rows this is approximately **99.2%–99.5% lower codec-batch elapsed time** on this host/run. All eight batch thread-CPU comparisons are **INSUFFICIENT_CLOCK_RESOLUTION**; zero counters are retained, not used in ratios. Full per-set elapsed ratios/5000-resample intervals are in r2. Cold module execution median rises from **0.1063 ms to 8.7696 ms**, and translation-table payload is **65536 bytes per interpreter** (not total process RSS). The warm speedup does not make initialization free or establish a full-controller/candidate speed ratio.

## Fresh complete-controller calibration and characterization

Collection Git HEAD is `d8dbf2b`; its 74 runtime/test bytes match the verified source. Only analysis/prose/evidence differs from the source CI revision. No local correctness, profile, microbenchmark or native emulator campaign overlaps a timed phase. Sequence: complete source verification/CI and native gate, initial microbenchmark, calibration, fixed-workload characterization, then corrected microbenchmark. Native journal drafts stay outside runtime/test discovery throughout.

[Calibration](e19-calibration/manifest.json) retains **60 windows/72000 reads**, including **25 inadequate windows**. First passing group counts are 12/8/6/4 below. No artificial recovery delay or favorable resizing is used. [Characterization](e19-characterization/manifest.json) completes **120 windows/144000 reads**; all are healthy/adequate, minimum controller CPU **2.109375 seconds**, and all **1200 actual enqueues** precede restoration in every window.

| Profile | Spare | Groups | Joint / separated median CPU ms | Joint / separated median window p99 ms | Joint/repeat p99 mean-ratio 95% interval | 5% repeatability |
|---|---|---:|---:|---:|---|---|
| 2+1 | No | 12 | 3796.88 / 6835.94 | 6587.49 / 11652.00 | [0.8354, 1.0599] | NOT ESTABLISHED |
| 2+1 | Yes | 8 | 2398.44 / 2812.50 | 4619.70 / 4990.11 | [0.9489, 1.0232] | NOT ESTABLISHED |
| 4+2 | No | 6 | 2257.81 / 3867.19 | 4459.61 / 6471.86 | [0.9544, 0.9958] | Established |
| 4+2 | Yes | 4 | 2437.50 / 4257.81 | 4504.82 / 6354.63 | [0.9791, 1.0277] | Established |

Tight joint/repeat stage work is one row/group versus two for the restricted control; spare work is equal. Larger newly calibrated group counts must not be treated as paired old/new controller workloads. Even the common four-group configuration is from separate host sessions, not a predeclared randomized cross-source comparison. Foreground p99 includes all offered reads, queueing and delayed completions.

The audit recomputes source/protocol/driver identities, both corrected microbenchmark inputs and matched orders, CPU-resolution rules/intervals/medians, every raw controller shard/request/receipt summary, full calibration selection and seeded 120-window schedule/bootstrap. Two repeatability failures remain. Conventional joint versus separated benefits and identical-software precision do not pass the original 20%-CPU/5%-foreground PRISM candidate gates. No native/power-loss/external reproduction result is inferred from E19.
