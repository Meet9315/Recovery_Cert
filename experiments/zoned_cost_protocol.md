# E17 / E16-E cost and foreground instrumentation pilot

15 October 2026. Freeze this protocol and source before the diagnostic collection. This is the next engineering measurement step after E16 file correctness, not a surviving invention hypothesis. Prior R15/E16 stage outcomes are already known. A Windows CI path-alias test issue is corrected in the same new source revision; retain the original CI failure and reports.

## Purpose, arms and workloads

Run `python -m prism_c.zoned_cost --root <fresh-root> --report <fresh-report> --pairs 2 --count 400 --rate 100 --seed 20261015`.

Eight configurations: profiles 2+1/4+2; `(unit bytes, repair groups)` equal to `(64,1)` or `(4096,4)`; extra spare zone absent/present. Unit and group scaling are deliberately coupled, so their individual effects cannot be separated. Repair components have disjoint eligible domains and share a single authority, one open token and `groups` active tokens. Construct a conventional plan for each disjoint component and concatenate in order; close each terminal OPEN zone before the next component, preserving its tail and charging its active token. Include all component planning/replay/closure construction in timing and execute all closures as real saved actions. Complete global replay/admission checks the concatenated witness. These routes minimize component stage counts; redundant final closes mean no exact global minimum-action/latency claim. The foreground object is fully protected, pinned, 2+1 with two units of content and separate zones in the same authority. All profiles remain immutable and trusted.

Developmental checks caught a naive concatenation's open-token violation: closing frees the shared open token, while the active budget must still cover all retained partially written terminal zones. This was corrected before registration; no model budget is silently relaxed during a run and every arm receives the same declared budget.

Three arms receive identical content, state, geometry and foreground requests in fresh stores:

1. `joint`: conventional joint minimum-stage planner.
2. `joint_repeat`: identical joint software and capabilities, to expose run/order variability. It is not a new candidate implementation.
3. `separated`: the previously declared restricted GC-first control. The stronger joint arm remains the baseline for any future candidate.

Two seeded pairs/configuration, each with saved independently shuffled arm order: **16 matched sets / 48 fresh stores**. All configurations and effects, including losses/parity, must remain. No sign-based deletion, replacement or aggregation into a universal improvement claim. Abort/checkpoint on any collection/integrity failure; do not discard a failed attempt.

## Cost boundaries

Bootstrap file/SQLite creation and takeover are measured separately before the loaded phase. Initialize and warm the foreground reader outside the loaded phase. Set one monotonic origin, release fixed arrivals and immediately measure snapshot acquisition, every component planner, whole-scope admission, every saved action and terminal cursor check. Restoration ends after all target actions return and the final cursor check. That interval includes deployed authority locking, SQLite intent/receipt/state operations and commits, source authentication/reconstruction, file writes/resets/synchronization, actual code checks, per-action measurement/report bookkeeping and any foreground interference.

Save controller **thread** CPU and wall time for every phase and the whole restoration interval; save whole-process CPU over that same interval separately, including producer/reader threads. Do not call process CPU controller-only CPU. Reader thread CPU additionally covers its initialization, warm read, all offered requests and drain; it is not confined to the restoration interval and must not be added to the whole-process interval as a partition. Per-phase overhead and overlapping CPU intervals are not independent costs.

After all offered reads drain, measure full replay/target, exact object readback, receipt and ledger verification as a separate phase outside restoration timing. Save setup/verification costs rather than silently treating them as zero. Save committed stage bytes including relocation/repair, bootstrap bytes separately, exact work scores, witnesses and per-action receipts. SQLite/device write amplification, individual fsync durations and physical NAND bytes are not instrumented. The complete deployed controller path is timed; this is not a complete storage-stack byte-cost accounting.

## Fixed arrivals and boundary retention

One producer schedules exactly **400 arrivals at 100 Hz** per store from the shared origin. A separate consumer thread performs serialized authenticated reads against the same zoned authority. Each request stores identity, scheduled arrival, enqueue, service start, completion, scheduling/queue delay, service/end-to-end latency and error. Never omit an offered request that queues or starts/finishes after restoration. Save counts that arrive before restoration and start/end after it. All request identities must be present exactly once and bytes correct. No repair pacing/artificial delay is inserted just to fill a sample.

The producer, consumer and controller share the process/GIL/OS/filesystem. This is a local serialized contention diagnostic, not remote production workload isolation. Thread scheduling and lock fairness are costs/limitations of this embodiment. Large scheduling lateness remains visible and is not diagnosed as a host suspension or removed as an outlier. The diagnostic has no independent host-continuity guarantee.

## Interpretation and stop

Primary outputs are phase/full-controller timings, exact work and collection integrity. Save every joint-versus-restricted CPU observation and identical-joint repeat ratio by matched set, without selecting a best configuration or claiming statistical confidence from two pairs.

The pilot cannot pass the original 20% candidate-CPU or 5% foreground conditions. A p99 adequacy screen requires at least **1,000 requests arriving before restoration in each arm**, all retained through completion; CPU screen requires at least **50 ms controller thread CPU**; comparative confirmation requires at least **ten complete matched sets per configuration**. The 400-request/two-set pilot intentionally cannot meet the full screen. Save empirical p99 as descriptive data only. `five_percent_foreground_gate_evaluated` remains false even if a later larger diagnostic happens to meet these floors: confidence analysis, adequate backlog and a separately frozen confirmatory protocol would still be required.

On failure preserve checkpointed attempts, timings and errors and stop. On an insufficient sample report INSUFFICIENT, not improvement or safety failure. If independent decomposition/replay, bytes, receipts, request identities or allocation disagree, the correctness/collection gate fails and no cost-success conclusion is allowed. Recollect only under a documented new source/protocol with old reports preserved.

Record Git HEAD, protocol/source/test hashes, clock information, Python/SQLite/platform, seed/order and all windows. Rerun E16 correctness collection under this revision to preserve exact-source correspondence after the CI assertion fix; keep initial E16 reports immutable. Run full regression and source CI on Ubuntu/Windows. No new native/ZNS/power-loss, PRISM-specific advantage or patent-score change follows. This delivers E16-E instrumentation and a diagnostic pilot; confirmatory E16-E and native/external E16-F remain pending.
