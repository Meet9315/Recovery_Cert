# E17: zoned controller-path costs and foreground collector

15 October 2026. Implemented the next measurement step after E16: full deployed controller-path timings and fixed-arrival foreground diagnostics, using the same serialized file adapter. [Registered protocol](../../experiments/zoned_cost_protocol.md), [collection context](E17_COLLECTION_CONTEXT.md), [source](https://github.com/Meet9315/Recovery_Cert/commit/d87264102c2f66569cb7a1fe6a3306ef056e7558).

Three conventional arms: joint minimum-stage scheduling, identical joint repeat, restricted GC-first. Eight configurations cover both coding profiles, `(64-byte units, one repair group)` and `(4096-byte units, four groups)`, with/without spare headroom. Each group retains its active token after completion; explicit closes release the one shared open token while preserving appendable tails. Equal budgets apply to all arms. No exact global minimum-action or latency optimum is asserted.

The collector measures bootstrap/takeover separately, then the complete loaded path from snapshot through all planning/admission/action/terminal cursor calls. It records per-phase/controller thread CPU and wall time, whole-process CPU separately, fixed-arrival request identities, queued/service/end-to-end times, every boundary read, committed repair/relocation bytes and separate post-verification cost. It verifies exact object/foreground bytes, terminal replay and receipts. CPU intervals overlap by design and must not be summed as disjoint partitions; filesystem/device write amplification is not measured.

Five new focused methods pass, including real timing/file/read collection, shared token composition, missing/duplicate/error request rejection, identical-arm pairing and existing-root protection. Development caught an invalid naive concatenation that retained too many open/active zones; corrected before source freeze. The original E16 path assertion is corrected without changing the file adapter's behavior, and its failed CI is retained.

## Collection status

The [first pilot](zoned-cost-e17.json) and [sequential follow-up](zoned-cost-e17-sequential.json) each complete **16 matched sets/48 fresh windows/19,200 offered reads**, with no collection/integrity failure: **96 windows/38,400 retained requests** in total. The first overlaps local verification; its timings are not isolated controller effects. The second starts only after all local correctness tasks and the first pilot finish. Neither guarantees an otherwise idle host. [Context](E17_COLLECTION_CONTEXT.md), [all-stratum descriptive summary](zoned-cost-e17-summary.json).

[Full exact-source local verification](verification-e17.json) passes **205 methods/501 subtests**, no failures/errors, with 10,000 traces and all existing campaigns. [Source CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38768388390) passes Ubuntu/Windows; [CI record](ci-e17.json). All 71 source/test byte hashes in the downloaded Windows artifact match corrected-source local file collection. The source/protocol stay frozen throughout timing collection; later analysis scripts and prose are not runtime modifications.

## Sequential pilot observations

All values below are descriptive medians of **two** windows per arm/configuration. J = conventional joint, C = restricted separated control. CPU is controller-thread CPU, wall is the entire restoration interval, and foreground p99 is the median of the two empirical window p99 values. All times are milliseconds. The identical-joint repeat and every per-set effect remain in the raw/summary reports; they are not hidden to favor either arm.

| Code; row bytes/groups | Extra spare | Stage bytes J / C | CPU ms J / C | Wall ms J / C | Foreground p99 ms J / C |
|---|---|---:|---:|---:|---:|
| 2+1; 64/1 | No | 64 / 128 | 164.1 / 257.8 | 368.6 / 554.8 | 77.1 / 141.0 |
| 2+1; 64/1 | Yes | 64 / 64 | 195.3 / 265.6 | 375.7 / 468.3 | 99.8 / 274.7 |
| 2+1; 4096/4 | No | 16384 / 32768 | 2468.8 / 4195.3 | 5158.6 / 5890.1 | 1565.7 / 4443.9 |
| 2+1; 4096/4 | Yes | 16384 / 16384 | 2726.6 / 2867.2 | 4278.6 / 3570.0 | 2777.3 / 3384.6 |
| 4+2; 64/1 | No | 64 / 128 | 179.7 / 390.6 | 336.3 / 746.7 | 65.2 / 178.4 |
| 4+2; 64/1 | Yes | 64 / 64 | 570.3 / 1046.9 | 753.5 / 1375.9 | 416.0 / 868.5 |
| 4+2; 4096/4 | No | 16384 / 32768 | 5632.8 / 9078.1 | 6177.3 / 10388.8 | 6080.3 / 9329.6 |
| 4+2; 4096/4 | Yes | 16384 / 16384 | 6492.2 / 8218.8 | 8177.5 / 9077.4 | 6895.0 / 8520.4 |

Important negative/parity observations are retained: all spare-headroom strata write the same stage bytes, and **large 2+1 with a spare takes 4278.6 ms joint versus 3570.0 ms separated** in these two-window medians. No universal elapsed-time improvement is established. Even identical joint repeats have per-set CPU ratios ranging **0.588 to 1.625**. The sequential saved whole-controller CPU totals are all multiples of **15.625 ms**; fine relative differences in small windows are not reliable merely because the 50-ms minimum passes. This does not identify the cause of the variation.

The recorded action phases are the largest controller-CPU category in all four larger strata. Planning is also substantial for spare-headroom 4+2 (median 1671.9 ms versus 4718.8 ms in actions). These phase boundaries do not isolate decoding, SQLite or lock wait; add diagnostic spans before assigning a cause or implementing an optimization.

Only **23–400 requests per sequential window arrive before restoration**, never the required 1,000. All 400 still drain and remain counted. Both pilots report `confirmation_sample_floor_met=false` and `five_percent_foreground_gate_evaluated=false`. No confidence interval or original performance-gate pass is claimed.

The [reproducible summary script](../../analysis/summarize_zoned_cost.py) preserves every stratum. Run `python -m analysis.summarize_zoned_cost` and `python -m analysis.check_zoned_delivery` from the repository to recompute descriptive summaries and evidence integrity. [Integrity record](e17-evidence-check.json).

Final integrity check: **71 runtime source/test hashes** match both pilots, corrected file collection, local verification, Windows CI and current files; all **65 R15 files** remain unchanged. Both protocol hashes, raw/derived arithmetic, request identities and local documentation links pass. Analysis scripts carry their own digests in the check record and are separate from frozen runtime modules/tests. The original E16 raw reports and initial failed path CI remain preserved.

## Boundaries and next work

This delivers E16-E measurement instrumentation and a registered diagnostic pilot, not the complete confirmatory E16-E gate. Two sets and 400 arrivals cannot meet the declared ten-set/1,000-during-restoration p99 floors. Empirical p99 and per-set costs are descriptive. No 20% candidate-CPU or 5% foreground condition is evaluated; no patent-score change follows. Current assessed readiness stays **55/100**.

Next: calibrate CPU precision and a realistic longer repair backlog, collect scoped action/planner attribution, and register an adequately sampled comparison before confirmation. Preserve the observed parity/loss and identical-joint repeat behavior. [Specific next tasks](../../RCSD_PRISM_C_Next_Engineering_Tasks.md). Any proposed ordinary optimization must be supplied to the capable conventional controller too, checked against E16's identity/uncertainty rules and compared with full validation. Native device/emulator hooks, uncertain device status, directory/power-loss evidence, external reproduction and human filing facts remain pending under E16-F and the original filing-evidence plan.
