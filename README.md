# RCSD-PRISM-C research prototype

A runnable local prototype of reservation-backed repair continuations and acknowledged storage reclamation. Python 3.11 or later; standard library only. No installation or network access is required.

16 October delivery: [E19](evidence/results/E19_EXECUTION.md) implements a shared compatible codec optimization, with 218 methods/687 subtests and both-platform source CI passing. Corrected codec batches show large elapsed savings with cold initialization and CPU-clock limitations retained; all 120 freshly calibrated controller windows/144000 reads pass integrity/adequacy, while two repeatability screens fail. [E20](evidence/results/E20_EXECUTION.md) separately executes actual QEMU NVMe ZNS commands and eight exact codeword routes; that optional Linux emulator requires QEMU installation. Native persistent-authority/process-fault integration is the next opt-in gate. Neither result establishes a novel distinction or the 70+ target.

Current research decision (13 October 2026): [updated patent-readiness assessment](evidence/results/PATENT_REASSESSMENT_2026_10_13.md) is **55/100**, a subjective readiness rubric, not grant probability. The [redesign plan](RCSD_PRISM_C_Redesign_Plan.md) investigates joint repair and whole-zone reclamation after conventional controllers match the current tested hypotheses. Engineering implementation status is recorded below; the 73/75 patent targets remain conditional.

Execution update (14 October 2026): [R14-A results](evidence/results/R14_EXECUTION.md) reject the specified frontier as a distinguishing mechanism. The new in-memory diagnostic agrees with ordinary counters/full recomputation across 1,256 snapshots and 36,336 mutations; later conditional builds are gated out. Full local verification passes 170 methods/435 subtests and registered-source CI passes Ubuntu/Windows. Run the isolated screen with `python -m analysis.zoned_frontier_gate --report <fresh-report-path>`; it does not operate a zoned device or claim a patent advantage.

Engineering continuation (14 October 2026): [R15](evidence/results/R15_EXECUTION.md) implements the nominal joint zoned repair/GC model, conventional A* planner and independently implemented reference. All 32 cases agree; RAM byte replay has 280 exact readbacks. Full verification now passes 186 methods/452 subtests; source CI passes both platforms. Two small staged fixtures halve stage writes versus a restricted separated control; the joint conventional planner gets the benefit. This is a model/RAM extension, not a native/durable zoned adapter or new patent distinction.

E16 verified delivery (14–15 October 2026): opt-in [zoned-file adapter](spec/zoned_file_store.md) adds real codeword files, prepared append/reset intents, authenticated adoption, conservative quarantine, persistent receipts/cursor and serialized takeover. Corrected-source collection passes 24 real route stores/280 prefix reads and 32 exits (28 resumed, four quarantined); full verification passes **205 methods/501 subtests**, and CI passes Ubuntu/Windows. [Results](evidence/results/E16_EXECUTION.md) preserve the original Windows path assertion failure and its correction. No native/power-loss or patent-score claim.

E17 measurement delivery (15 October 2026): [cost/foreground collector](experiments/zoned_cost_protocol.md) measures the full deployed controller path and retains every fixed-arrival read, with identical-joint repeats exposing variability. Both diagnostic pilots pass integrity: **96 windows/38,400 reads**, including a separate sequential collection after local verification. [All-stratum results and limitations](evidence/results/E17_EXECUTION.md). Spare-headroom work parity and a joint elapsed-time loss are preserved. Two sets/400 arrivals do not establish the 5% p99 condition or a PRISM-specific advantage.

## Run

E18 completed (16 October 2026): all eight profiles, 24 calibration windows and **120 characterization windows/144000 reads** pass integrity and sampling floors. A [predeclared two-session continuation](experiments/e18_continuation_protocol.md) preserves the original interrupted prefix. Identical-software 5% p99 repeatability is established in two of four configurations; both failures and session confounding remain. Source verification/Ubuntu/Windows CI pass **213 methods/501 subtests** with 73 matching source/test hashes. [Results](evidence/results/E18_EXECUTION.md), [final audit](evidence/results/e18-evidence-check.json), [remaining work](PROGRESS.md). Conventional scheduling effects do not establish a PRISM candidate advantage or native/power-loss result.

From this workspace:

```powershell
python -m prism_c verify --report evidence/results/verification.json
python -m prism_c demo --root tmp/prototype-demo --report evidence/results/demo.json
python -m prism_c status --root tmp/prototype-demo --plan demo-plan
python -m prism_c benchmark --report evidence/results/selective-benchmark.json --runs 10
python -m prism_c demo --root tmp/prototype-selective-demo --report evidence/results/demo-selective.json --validation-mode shadow
python -m prism_c concurrent-demo --root tmp/concurrent-demo-new --report evidence/results/concurrent-demo-new.json --validation-mode shadow
python -m prism_c verify --report evidence/results/verification-milestone-03-new.json --traces 10000
python -m prism_c concurrent-demo --root tmp/worker-demo-new --report evidence/results/worker-demo-new.json --validation-mode shadow --storage-workers
python -m prism_c four-plus-two-demo --root tmp/four-plus-two-demo-new --report evidence/results/four-plus-two-demo-new.json --validation-mode shadow
python -m prism_c controller-benchmark --report evidence/results/controller-benchmark-new.json --runs 10 --seed 20261012
python -m prism_c measurement-diagnostics --report evidence/results/measurement-diagnostics-new.json --seed 20261012
python -m prism_c snapshot-latency --report evidence/results/snapshot-latency-new.json --runs 10 --seed 20261012
python -m prism_c read-reuse-benchmark --report evidence/results/read-reuse-new.json --runs 10 --seed 20261012
python -m prism_c revision-demo --root tmp/revision-demo-new --report evidence/results/revision-demo-new.json --profile 4+2 --storage-workers --validation-mode shadow
python -m prism_c minimum-work-demo --root tmp/minimum-work-new --report evidence/results/minimum-work-new.json --profile 4+2 --storage-workers --validation-mode shadow
python -m prism_c contingency-gate --report evidence/results/contingency-gate-new.json
python -m prism_c contingency-demo --root tmp/contingency-new --report evidence/results/contingency-demo-new.json --storage-workers --validation-mode shadow --fault-domain D0 --cursor 2
python -m prism_c.zoned_campaign --report evidence/results/zoned-joint-new.json
python -m prism_c.zoned_file_campaign --root tmp/zoned-file-new --report evidence/results/zoned-file-new.json
python -m prism_c.zoned_cost --root tmp/zoned-cost-new --report evidence/results/zoned-cost-new.json --pairs 2 --count 400 --rate 100 --seed 20261015
python -m prism_c.zoned_measure profile --root tmp/zoned-profile-new --output evidence/results/zoned-profile-new
python -m prism_c.zoned_measure calibrate --root tmp/zoned-calibration-new --output evidence/results/zoned-calibration-new
python -m prism_c.zoned_measure confirm --root tmp/zoned-characterization-new --output evidence/results/zoned-characterization-new --calibration evidence/results/zoned-calibration-new/manifest.json
```

The demo root must be new or empty. Existing stores are never reset by the demo. Choose a new root name for another run. `verify` uses disposable temporary stores and preserves the report, test details, source hashes and model campaign counts.

To resume an interrupted plan: `python -m prism_c resume --root <store-directory> --plan <plan-id> --takeover`. This advances the owner fence, invalidating older controllers. `cancel` accepts the same arguments and leaves materialized partial writes charged until reclamation; cancellation does not immediately free their capacity.

Those resume/cancel commands apply to slot stores. The separate zoned-file adapter uses `ZonedFileStore(root)`, `takeover()` and `execute(fence)`; it has no cancellation or asynchronous worker API. Its creation/campaign paths must be nonexistent. Read the [contract](spec/zoned_file_store.md) before interpreting pending intents, quarantine or simulated reset outcomes.

## Implemented

- Immutable finite slot state, bounded breadth-first repair planner and independent witness replay checker.
- Conventional capacity-aware matching baseline and an independent finite assignment oracle.
- Real immutable content using versioned 2+1 XOR and 4+2 GF(256) P/Q coding profiles, with an independent reconstruction oracle.
- Preallocated fixed-size byte pools; durable stage writes; checksum-checked promotion; reclaim acknowledgement before slot release.
- SQLite authority binding plan cursor, allocation transitions and manifest updates in one transaction.
- Multiple active plans with exclusive whole-stripe and slot claims; destination holds, source pins, monotonically fenced takeover, idempotent step replay and isolated cancellation cleanup. Full-store legacy plans remain exclusive.
- Actual subprocess exits at validation, staging, promotion and reclamation commit boundaries.
- Durable component certificates, internally derived membership coverage, changed-component replay and safe rebuild when cache evidence is absent or incompatible.
- Conventional cached, full, selective and shadow validation modes (`Authority(root, validation_mode="conventional_cached"|"full"|"selective"|"shadow")`). Shadow mode compares selective results with complete replay in every step. Default is conventional cached; component caching is experimental.
- Opt-in stage/reclaim storage processes with committed intents, per-domain durable fences, grant revocation barriers and checked durable receipts. Repair I/O runs outside the authority writer transaction.
- Conventional partial-state replanning and checked successor plans that retain authenticated staging, drain old worker grants, transfer complete claims and leave failed allocations charged. Includes saved CLI proposals, exact request retries, persistent lineage and an independent finite partial-recovery oracle.
- Opt-in conventional minimum-work partial planning: minimize committed stage actions, then all actions, within a bounded fixed-LIVE assignment. Exhausted optimization returns UNKNOWN without a proposal. `replan --planner min-work` exposes it; historical first-feasible planning remains the default. See the [objective/limits](spec/minimum_work.md).
- Finite one-additional-failure policy gate: complete cursor/domain alternatives, independent replay/feasibility checks and conventional cached alternatives with the same resources. Existing-API byte/claim smoke tests supplement the model; this does not implement a new durable policy-admission or in-flight-failure guarantee. See the [contract](spec/contingency_policy.md).

## Scope

This is a trusted local single-authority embodiment. Domain labels are simulated. Slot reclamation means the managed extent has been durably overwritten and may be reused by this allocator; no filesystem unlink/free-space inference is used. The default local mode keeps storage I/O inside the metadata writer transaction. Opt-in workers perform stage/reclaim I/O outside it using checked intents, worker-side fencing and revocation. Source validation, promotion, fixture import and explicit cleanup retain the local authority path.

Witnesses bind the complete terminal state of their admitted scope. Selective mode reuses validated component suffixes when their full projected dependencies and membership are unchanged. Related changes are replayed; coverage changes cause rebuilding. Exact terminal binding still rejects even otherwise-safe policy changes. Physical source checks are performed on every step. See [selective validation specification](spec/selective_validation.md).

The logical benchmark compares full replay, component caching and a conventional exact-state guarded cache, including cache preparation and advancement. Results from that in-memory test cannot establish storage throughput or the project's overall CPU/latency targets. The separate controller benchmark measures actual local persistence, reconstruction and worker RPC costs. Network storage daemons, independent device failures, power-loss testing and the complete research performance gate remain future work. No new patentability score follows from these tests.

## Coding profiles

Existing callers retain the default `xor-2+1-v1` profile. Import `FOUR_PLUS_TWO` from `prism_c.profiles` and pass `profile=FOUR_PLUS_TWO` to `Authority.bootstrap`, or use `encode(data, FOUR_PLUS_TWO)` and `recover(rows, original_length, FOUR_PLUS_TWO)` from `prism_c.coding`. A 4+2 stripe needs any four authentic rows for reconstruction and all six rows for the restoration target. Scoped plans support mixed profiles. Existing stores receive an additive profile-column migration; historical default-profile witnesses and pending worker intents remain valid.

The [coding contract](spec/coding_profiles.md) defines row coefficients, canonical padding, digest checks and compatibility. The new demonstration repairs missing data rows using parity, runs two mixed-profile plans through storage workers and checks original content after reopening.

## Concurrent scoped plans

`snapshot_for(stripes, destinations)` derives a snapshot with every current member of those whole stripes and the explicit destination slots. Supply a witness for that snapshot to `admit_scoped(witness, stripes, destinations, fence, plan_id)`. Each active scope claims all its stripes and slots until completion or cancellation. Plans with disjoint stripe and slot sets can coexist and use separate slots in the same domain. Shared stripes or destinations conflict; the admission transaction leaves no partial claims. Reads of immutable content remain available. Takeover changes the global fence for every active plan.

An active plan can finish while an unrelated stripe remains degraded. Cancellation retires only its own partial allocations; physical cleanup can proceed beside other scopes when the retired slot is unclaimed. Cache guards and terminal fingerprints apply to the complete admitted projection, so another plan's independent progress does not invalidate them. Claimed FREE slots count as reserved capacity. `status` reports all active plans, and `--plan` includes the selected plan's scope.

The [concurrent scope specification](spec/concurrent_plans.md) states the compatibility rule and fault boundaries. [Milestone 3 evidence](evidence/results/MILESTONE_03.md) records the earlier 70 passing test methods, all 20 interleavings of the two 3-step fixture, independent controller processes and eight additional process-exit cases. That milestone used the default serialized I/O path.

## Storage workers

For a prepared store, call `authority.enable_workers(fence)` before admitting its first plan. Normal `step`/`execute` then route stage/reclaim actions through separate processes. The CLI demonstration enables this with `--storage-workers`. Worker configuration persists across reopening and takeover; `resume` needs no extra mode flag.

Advanced callers can use `prepare_worker_step(plan, fence)`, `execute_worker_intent(token)` and `complete_worker_step(receipt, fence)` separately. Between these phases, capacity stays charged and the plan cursor remains unchanged. The authority commits the allocation transition only after rechecking the current continuation, exact command identity, durable worker receipt and physical bytes. Receipt corruption, revoked grants, stale incarnations and delayed receipts under a new fence reject. Cancellation drains/revokes affected work before releasing claims; takeover drains/fences each domain worker before publishing the new global epoch.

The [worker specification](spec/storage_workers.md) defines the lock order, failure/retry behaviour and reduced trust model. The processes operate on local files and have independent per-domain locks; they are not authenticated remote daemons or separate physical devices. Preparation currently performs full suffix replay. No worker throughput or CPU advantage is claimed. See [milestone 4 evidence](evidence/results/MILESTONE_04.md) and [PROGRESS.md](PROGRESS.md) for verification and pending work.

## Controller comparison

`controller-benchmark` runs eight registered configurations: both coding profiles, 2/8 repair stripes and local/worker paths. It uses ten seeded paired runs with randomized ordering of conventional cached, selective and full validation. Fresh stores have identical bytes, capacity, protection and conventional repair witnesses. Planning, admission, steps, persistence, source checks and worker reconciliation are timed; fixture creation and independent terminal/readback checks are excluded and disclosed. A benchmark-only envelope measures worker CPU without changing durable receipts or production worker commands.

The [registered protocol](experiments/controller_protocol.md) defines calibration, time-to-restoration as the secondary metric, capacity observations, concurrent foreground reads and interval analysis. The report preserves raw attempts, latencies, setup costs, child RPC measurements, paired effects and the protocol/source hashes. Foreground p99 needs at least 200 samples per phase per attempt; insufficient samples stay labelled. Failed comparisons preserve a partial report and exit unsuccessfully. This reduced local no-fault/reclamation suite does not establish the full G6 gate, isolated verification CPU, independent hardware or production throughput.

The [milestone 6 results](evidence/results/MILESTONE_06.md) retain all 80 paired runs and 240 measured completed repair groups. None of the eight configurations meets the CPU or restoration proxy targets versus conventional caching; foreground p99 is insufficient throughout. The four new regression tests check identical durable witnesses/readback across modes, child/receipt CPU accounting, sample inadequacy and zero-timer handling. The full performance campaign is a manual experiment; CI runs its integrity tests.

## Sampling and CPU diagnostics

`measurement-diagnostics` runs twelve longer foreground windows and twelve separate CPU profiles across both profiles, local/worker paths and all three comparison modes. A prepared backlog keeps repair work available while the reader seeks 400 successful observations per phase. Control reads finish before repair starts; loaded reads that finish after repair stops are drained and retained. The report saves every request's phase, timestamps, outcome and latency, sample sufficiency, actual durations and stopping reason. The windows use a closed-loop reader and remain single diagnostic observations; they do not evaluate the 5% foreground threshold or paired effects.

Separate process-CPU profiles retain every function's call counts and exclusive/inclusive costs, with exclusive category totals that count each function once. Nested spans identify a declared logical-verification subset without adding inner intervals again. Physical source, staged-byte and receipt checks remain outside that subset and visible in the profiler. Worker profiles include receipt lookup; whole-worker CPU is reported separately from controller CPU. Instrumentation and timer quantization affect these values, so they cannot establish production cost shares or speedups.

`python -m prism_c fault-contention-benchmark --runs 10 --seed 20261012 --report evidence/results/fault-contention-milestone-10.json` runs the [registered fault/contention protocol](experiments/fault_contention_protocol.md): both coding profiles, one actual worker exit after receipt commit with same-epoch retry, and two independent scoped controllers sharing the authority. Conventional caching and selective validation receive identical optimized snapshot content probes, bytes, slot capacity and witnesses. CPU includes every worker, including the intentional exit; raw controller intervals, exit outcomes, charges and liveness observations are retained. This comparison excludes setup/planning/admission and does not evaluate the foreground latency gate or represent host/power loss.

The [milestone 10 results](evidence/results/MILESTONE_10.md) preserve 40 completed pairs, 80 measured repair groups, 40 actual worker exits and 840 successful authenticated content probes. All 40 contention groups have overlapping controller repair intervals. No configuration meets the 20% CPU or 10% restoration proxy threshold; the complete controller and patentability targets remain unresolved. Eight warmups and all raw timing variation remain retained.

The subsequent [design-gap audit](evidence/results/DESIGN_GAP_AUDIT.md) explains why these successful traces provide no additional suffix-replay saving over the guarded conventional cache. Its untimed script checks 273 paired logical steps, eight real stores and relevant-change rejection; the recorded 132-method result describes that historical source. The interrupted-plan revision redesign is now implemented for both controller modes. See the [successor contract and CLI](spec/plan_revision.md) and [registered work-retention gate](experiments/revision_protocol.md). Retaining staging does not by itself establish an advantage over an equally capable conventional replanner.

[Milestone 11](evidence/results/MILESTONE_11.md) records 143 passing methods/360 subtests, 57 actual process-exit regression cases, independent partial-state/actual-fixture oracles and passing Ubuntu/Windows CI. All twelve paired work-retention comparisons are equal. The capability is useful shared recovery functionality; the hypothesis supplies no observed selective-mode distinction. The larger performance confirmation is gated out, and the patentability assessment is unchanged. [Primary-source mapping](evidence/results/REVISION_PRIOR_ART_REVIEW.md) separates the implemented combination from reservations, journals, reconfiguration, backfill and reconstruction already described elsewhere.

[Milestone 12](evidence/results/MILESTONE_12.md) fixes globally wasteful first-feasible assignment. Minimum-work planning saves one committed stage in both tested interrupted fixtures—50% for 2+1 and 25% for 4+2—relative to that weaker control. All 12 matched sets / 36 stores restore exact bytes; minimum-work conventional and selective modes perform identical work. The independent oracle agrees across 136 finite cases and both actual fixtures; full verification passes 150 methods/388 subtests. These operation-count savings are a shared conventional planner improvement, not a measured latency/CPU or novelty result. The primary comparator now includes cost-aware planning.

[Milestone 13](evidence/results/MILESTONE_13.md) completes the finite one-additional-failure gate: 16 feasible/56 infeasible cases, 224 equal cached alternatives and four equal actual-store pairs. Five LIVE 4+2 rows and two distinct spare domains support the registered source-failure property; inadequate rank or placement rejects. Conventional cached alternatives need no online replanning either, so no distinguishing advantage is established. Further durable integration is gated out; scores and performance thresholds are unchanged.

The [diagnostic protocol](experiments/measurement_diagnostics_protocol.md) preserves the earlier registered controller comparison and its results. CLI failure preserves a partial report and names the failed measurement cell. Correctness tests cover actual SQLite-blocked reads, phase separation, nested spans, worker receipt profiling and failure preservation. Longer sampling and attribution do not change the patentability assessment; independent paired confirmation and fault/contention comparisons remain pending.

The [milestone 7 results](evidence/results/MILESTONE_07.md) retain all twelve healthy windows and CPU profiles. Every window exceeded 400 reads in both phases; twelve reads ending after restoration were retained. Loaded p99 was 3.17–30.08 times control in these single observations, so foreground contention remains unresolved. The full correctness suite passed 107 methods and 288 subtests, with both finite campaigns reporting zero violations/disagreements. CPU quantization and profiler overhead prevent precise cost-share or speedup claims.

## Opt-in snapshot reads and paired latency

Call `Authority.read_snapshot(name)` to read immutable content from a committed metadata snapshot. SQLite WAL allows [simultaneous snapshot readers and a writer](https://www.sqlite.org/isolation.html); external pool bytes still require independent authenticity checks. This API performs the same row, regenerated-row, padding and original-content digest checks as `read`. If reconstruction rejects, it closes the snapshot and retries once through the existing serialized `read`. That handles placement/reclamation races without trusting stale physical bytes. Other database/I/O errors propagate. `read` remains the default; repair authority, workers, claims, fences and capacity accounting retain their existing paths. See the [snapshot-read contract](spec/snapshot_reads.md) for race, offline-state and fault limits.

`snapshot-latency` compares those two APIs under the same conventional cached controller. Four configurations cover both coding profiles and local/worker paths, with ten seeded pairs each and randomized API order. A fixed schedule offers 400 requests per phase at 100 Hz independently of completion. Every queued call remains in the report, including calls served after restoration. End-to-end latency includes scheduling and queue delay; service latency is reported separately. Complete no-repair drain precedes repair, and all loaded requests drain afterward.

The [registered paired protocol](experiments/snapshot_latency_protocol.md) preserves equal initial backlogs, all outcomes and source/protocol hashes. It reports paired loaded-p99 effects and each API's own loaded/control inflation. Improvement over serialized reads alone does not meet the original 5% foreground condition. This conventional database optimization applies equally to the baseline; it does not establish a selective-continuation advantage, overall research gate or new patentability rating. The manual confirmation campaign is separate from CI integrity tests.

The [milestone 8 results](evidence/results/MILESTONE_08.md) preserve the original campaign failure after 35 pairs and its separately registered continuation. The supplemented forty-pair set contains 80 windows and 64,000 successful requests. Snapshot reads reduced mean paired loaded p99 by about 92% in both worker configurations and 67% in local 4+2; local 2+1 remains inconclusive, including a retained approximately 187-second interruption. None met the own-control 5% condition. Serialized reads remain default. The [continuation protocol](experiments/snapshot_latency_continuation_protocol.md) documents provenance, all retained/unused windows and failure handling; no original data is overwritten.

Milestone 8 full verification passed 120 methods and 296 subtests, retaining 37 process-exit cases and both finite campaigns with zero observed violations/disagreements. The continuation helper's source hash is saved separately from the 34 package/test hashes, all matching their recorded versions.

## Authenticated read-result reuse

Both read APIs return the content already reconstructed and authenticated by the common validator. They keep all source/row, coding/padding, regenerated-row and content-identity checks; repair and worker callers retain their existing `_valid_rows` interface. Snapshot failure still closes its transaction before one serialized fallback. This removes a second decode of the same in-memory rows without a cross-request content cache. Serialized reads remain default.

`read-reuse-benchmark` compares the former redundant decode sequence with result reuse across both read APIs, both coding profiles and 512/65,537-byte objects: eight configurations with ten seeded pairs each. It calibrates batches for process CPU resolution and keeps all raw counts, attempts and intervals. Eight separate fixed-arrival foreground windows are diagnostics rather than paired foreground confirmation. CPU and foreground collectors retain process pulses, wall/monotonic/CPU timestamps and overlapping gaps of at least 500 ms; gaps do not identify their cause.

The [registered protocol](experiments/read_reuse_protocol.md) preserves every authenticity check and provides the same common validator/controller to both variants. The [milestone 9 results](evidence/results/MILESTONE_09.md) show 44%–47% less read CPU for large objects, while small-object intervals span zero. Every measured window passed its byte/target/capacity checks; no 500 ms pulse gap was observed. These read costs are not continuation-verification CPU, and the single foreground windows do not complete the research gate or increase the patentability assessment. The prior campaign failure and all historical reports remain preserved.

Local milestone 9 verification passed 129 methods and 318 subtests, with both finite campaigns observing zero violations/disagreements. Two short test backlogs were enlarged after measurement to fix a fast-Linux CI failure; an empty-backlog regression retains the collector's rejection policy. Fresh [Ubuntu and Windows CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38265616092) both passed. Measurement source is preserved in its frozen Git version, and the final verification records the corrected test hashes.

## Repository verification

GitHub Actions runs the correctness/process-fault suite, 1,000 seeded model traces and the independent 4+2 campaign on Ubuntu and Windows with Python 3.11, and saves its verification report. The 4+2 campaign checks all 65,536 field products, 15 reconstruction subsets and 720 finite repair cases. The local milestone reports retain the larger 10,000-trace campaign. Runtime databases, worker secrets, byte pools, temporary extraction files and generated caches are excluded from version control; project source, specifications, disclosure/review documents and saved evidence reports are included.

The first comparison found component caching slower than the conventional guarded cache, despite savings against full replay in larger groups. The confirmation comparison uses fresh snapshot records and the deployed cache implementations. See [milestone 2 results](evidence/results/MILESTONE_02.md) for the measured scope and interpretation.

See [PROGRESS.md](PROGRESS.md), [implementation scope](spec/implementation_scope.md), [execution plan](RCSD_PRISM_C_Conditional_Target_Execution_Plan.md) and [proposed disclosure](RCSD_PRISM_C_Proposed_Invention_Disclosure.md).
