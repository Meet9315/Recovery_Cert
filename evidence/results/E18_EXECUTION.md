# E18: scoped diagnosis and calibrated baseline characterization

15–16 October 2026. Next engineering step after E17's insufficient pilot. Implements scoped profiling, actual-enqueue/CPU calibration and a registered ten-matched-set campaign for each of four profile/headroom configurations. **Characterization completed through the declared two-session continuation.** The interruption record below remains historical evidence. This characterizes conventional controllers; no new candidate mechanism is present. Patent readiness remains the previously assessed **55/100**.

Source/protocol freeze: [`e8ad2dba831f17749b0f8d27e5a32e63b1e9889a`](https://github.com/Meet9315/Recovery_Cert/commit/e8ad2dba831f17749b0f8d27e5a32e63b1e9889a). [Protocol](../../experiments/zoned_measurement_protocol.md). All E16/E17 runtime modules/tests and old raw reports remain unchanged; only the new measurement module/test and subsequent result/analysis prose are added.

## Delivery and evidence boundaries

| Stage | Required evidence | Current status |
|---|---|---|
| Correctness | Full regression, 10000 traces and Ubuntu/Windows source CI | PASS: 213 methods/501 subtests; 73 matching source/test hashes |
| Scoped profiles | Eight stores; separate planning/admission/action function profiles and exact readback | PASS: all eight exact targets/readbacks |
| Calibration | First passing 4/6/8-group workload for each profile/headroom configuration; both complete three-arm sets retained | PASS: 24 windows/28800 requests; four groups selected in every configuration |
| Characterization | Ten sets/configuration, 120 windows, 144000 reads with adequate CPU/actual arrival counts | PASS integrity/adequacy: 120 windows/144000 reads across two declared sessions |
| Repeatability | Ten paired joint/identical-repeat p99 observations and predeclared interval screen | Established in spare-headroom configurations only; both tight configurations fail the screen |
| Native/external/filing | Device status/reset/power-loss evidence, external reproduction and actual human records | Pending outside this delivery |

Eight focused methods pass, covering real profiled bytes, phase failures, complete request identities and actual enqueues, full candidate selection, changed calibration shards/source, matched inputs/duplicate arms, counters and CLI finalization after both success/failure. Development reproduced a Windows sandbox restriction on file rename in its temporary directory; evidence now uses immutable numbered checkpoints and one final manifest. No earlier evidence or registered failure is discarded.

[Full local verification](verification-e18.json) passes 213 methods/501 subtests with 10000 traces and all existing campaigns, no errors/failures. [Source CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38773608364) passes Ubuntu/Windows; [record](ci-e18.json), [Windows artifact](verification-e18-ci-windows.json). All 73 source/test byte hashes match local/Windows verification; all 71 E17 files remain unchanged. [Collection context](E18_COLLECTION_CONTEXT.md) records that local verification/Ubuntu CI preceded profiles while remote Windows verification finished, and all source checks passed before calibration/characterization.

Scoped profiles use instrumented **elapsed** time by function/category, with whole-phase thread CPU separately; elapsed includes waits/scheduling and inclusive values overlap. These are diagnostic profiles without foreground, not production CPU shares or a speed comparison. The uninstrumented E17 collector is reused for all calibrated/timed windows.

[Profile manifest](e18-profile/manifest.json) records eight successful stores. Coding is the largest recorded exclusive elapsed category in the action phase of every profile; model validation is largest in every planning profile. The profiler favors neither a new candidate nor a proposed optimization: it only identifies recorded hot paths, with instrumentation overhead and no foreground present. Calibration remains a separate uninstrumented collection.

Calibration demands at least **2 seconds controller CPU** and **1000 actual enqueues plus scheduled arrivals before restoration**, with all **1200 offered reads at 500 Hz** completed correctly. Select the first passing group count after **all six windows** pass. Preserve inadequate candidates. Confirmation validates exact source/protocol/Git identity and calibration shard digests, freezes that workload and does not resize after seeing comparative outcomes.

[Calibration manifest](e18-calibration/manifest.json): all four profile/headroom configurations select **four groups**, with 24 healthy windows/28800 requests and no insufficient candidate. The lowest controller CPU is **2.390625 seconds**; all 1200 actual enqueues precede restoration in each window. The manifest and all immutable shard digests are validated by characterization before it starts. No group count or arrival rate is changed during characterization.

All measured workload classes, parity/losses, delayed completions and identical-software variation remain. Per-set ratios and 5000-resample matched-set percentile intervals are conditional on the observed host/run conditions, not a universal performance guarantee. A successful collector or adequate sample does not establish the original 20%-CPU/5%-foreground research target: joint/repeat is identical software, and joint/separated compares conventional scheduling with a restricted control.

## Interruption observed on 16 October

This subsection records the pre-continuation state; the completed delivery is below.

The process is no longer running and no `e18-characterization/manifest.json` exists. The last console line reports window 64 successful. The latest immutable checkpoint, `checkpoint-0065.json`, contains **64 windows/76,800 requests**: 30 windows for 2+1 without spare headroom, 30 for 2+1 with spare headroom, and four for 4+2 without spare headroom. The remaining 56 registered windows are absent. The next runtime store, if present, is not a saved successful observation. The cause of termination is unknown; there is no recorded final collector failure to attribute to storage correctness.

The [partial integrity audit](e18-checkpoint-audit.json), reproducible with `python -m analysis.check_e18_checkpoint`, checks all saved profile/calibration/characterization shard digests, source/protocol bindings, calibration selection, immutable checkpoint prefixes, request quality, latency summaries and receipt arithmetic. All 64 saved characterization windows meet the registered CPU/actual-arrival floors. This is a saved-observation integrity pass, **not** a completed characterization or repeatability pass. Local/Windows verification still matches all 73 source/test files, with all 71 E17 files unchanged.

No partial campaign confidence intervals or final ratio claims are published. `analysis/summarize_zoned_measurement.py` and `analysis/check_zoned_measurement.py` are prepared final-manifest helpers, not completed-run evidence; they have not yet been exercised on a complete E18 campaign. A continuation must first declare how interruption, preserved ordering, host/session changes and the unfinished store are handled, or register a complete fresh campaign while preserving this attempt. Do not silently fill gaps, replace observations or fabricate a final manifest.

Native ZNS reset acknowledgement, device identity/power loss, external reproduction and unknown inventor/priority facts remain unresolved. The [next engineering plan](../../RCSD_PRISM_C_Next_Engineering_Tasks.md) specifies an unimplemented shared codec optimization; observed coding/model-validation hot paths do not establish a new inventive mechanism.

## Completed continuation and complete results

The [amendment](../../experiments/e18_continuation_protocol.md) was committed/pushed before collection. The helper verified the exact 64-window prefix, seeded order, all closed shards and frozen runtime/test/protocol/calibration identities, then collected only the remaining 56 windows in fresh runtime stores. The original incomplete store was not reused. The original archive environment remains its creation snapshot; the final manifest separately records the actual continuation environment and Git HEAD at start, `a5f3df9aa2dbc2e0fbfd94bdf6dc309074288a0d`, plus helper/amendment digests and prefix anchor. Later prose/analysis commits did not change runtime/test bytes.

[Final manifest](e18-characterization/manifest.json), [all-stratum derived summary](e18-summary.json), [independent recomputation audit](e18-evidence-check.json). All 120 windows/144000 requests are healthy and meet the registered floors. All 64 original records remain byte/digest-identical. Source verification/CI matches all 73 files, and all 71 E17 runtime/test files remain unchanged at collection. The audit recomputes every shard, request summary, receipt arithmetic, calibration selection, full seeded schedule, matched bootstrap results and local document links.

| Profile | Spare | Joint / separated median CPU ms | Joint / separated median wall ms | Joint / separated median window p99 ms | Joint/repeat p99 mean-ratio 95% interval | 5% repeatability |
|---|---|---:|---:|---:|---|---|
| 2+1 | No | 2445.31 / 4078.12 | 3906.1 / 6883.9 | 9447.50 / 11460.56 | [0.9034, 1.0036] | NOT ESTABLISHED |
| 2+1 | Yes | 2593.75 / 2757.81 | 3381.5 / 3524.8 | 9843.36 / 10254.39 | [0.9680, 1.0301] | Established |
| 4+2 | No | 5476.56 / 9296.88 | 6329.9 / 10739.5 | 14037.01 / 17831.20 | [0.9410, 1.0476] | NOT ESTABLISHED |
| 4+2 | Yes | 6453.12 / 8101.56 | 7433.6 / 8857.7 | 15003.83 / 16443.96 | [0.9723, 1.0394] | Established |

Tight routes commit 16384 stage bytes for joint/repeat versus 32768 for separated; spare routes all commit 16384. Full raw per-set ratios, repeat-arm medians and intervals remain in the summary. Ratios are defined joint/other; lower can reflect a conventional scheduling benefit. Spare work parity does not imply identical instruction cost. Foreground p99 includes all offered reads and delayed completions; it is not a repair-only service-time percentile.

Collection spans two host sessions, including a split matched set in tight 4+2. Resampling does not remove session or scheduling dependence. No comparisons were dropped for looking unfavorable. Two repeatability failures limit small-effect precision. Joint versus separated tests conventional scheduling; joint versus repeat tests identical software. **No original PRISM candidate gate, native/power-loss gate or novelty/score increase is established.** Final-manifest helpers were exercised successfully on this complete dataset before changing runtime source for E19.
