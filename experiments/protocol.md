# Experiment protocol: initial correctness milestone

Version 1 — 11 October 2026. No performance acceptance result is claimed.

## Evidence collected now

Unit/integration test methods; independently enumerated small eligibility configurations; subprocess interruption boundaries; content readback after restart; ledger conservation; and seeded model campaign with unique configuration counts. Reports include source SHA-256 values and runtime/platform versions.

The campaign varies two stripes, three eligible destination labels, online/offline flags and pre-existing retired slots. It uses the conventional scheduler and compares each transition with an independent replay implementation. It does not test all possible concurrency interleavings or assert novelty over the baseline. Repeated seeded cases are counted separately from unique configurations.

## Performance protocol pending

Before selective reuse or larger-scale evaluation, freeze the primary workloads, controller baseline, resource budgets and confidence-interval methodology from the execution plan. Include all planner/validation/retry/reconciliation cost. The initial full-revalidation implementation cannot meet or demonstrate the selective-reuse CPU target by construction.

Proposed later targets remain 20% verification CPU improvement over a competent baseline, a preselected practical secondary metric, equivalent safety, and at most 5% p99 foreground impact. These are engineering goals, not legal criteria. No threshold is considered met until reproducible comparative results exist.

## Milestone 2 logical validation comparison (registered before measurement)

Use groups of 2, 8 and 16 stripes. Each stripe initially has two live source rows on S/T and its own one-slot repair destination, with half the destinations retired. The same validated action sequence is supplied to all implementations. Ten paired runs use a seeded random mode order to reduce order bias. Measure process CPU nanoseconds for admission plus all logical step validation and advancement; also report preparation and step totals separately. Test no background mutations and one diagnostic annotation between each step. Annotations are deliberately non-authoritative and are ignored by all modes. Related mutation rejection is tested separately and never counted as successful repair performance.

Modes: full suffix replay; selective component certificates; a conventional exact-state guarded suffix cache. The conventional cache checks the full current state against its expected state and reuses the already validated terminal result when unchanged, advancing only after independent current-step checking. This is a capable standard caching comparator, not an unsafe or deliberately weak baseline. Include that cache's construction/guard cost too.

Report raw paired run totals, medians, paired percentage changes and bootstrap 95% confidence intervals of the mean paired percentage change with a fixed seed. This microbenchmark excludes SQLite persistence/serialization and physical byte checks, so it cannot establish the overall 20% controller target, foreground latency or practical secondary effect. Do not claim an improvement over the conventional cached mode if only full replay is slower. Any slowdown is a reportable result.

Timer calibration correction, made before comparison results: on this Windows runtime a short sequence can register zero process CPU time. Batch repeated identical sequences until the conventional cached batch records at least 50 ms of CPU, then use that same repetition count for all three modes in that configuration. Exclude calibration from comparisons and record its values and batch size. The primary outer batch timer includes verification/harness overhead; per-sequence CPU is batch CPU divided by repetitions. Record batch wall time too. Single-sequence preparation/step timers remain descriptive and may be quantized; do not use them alone for effect claims.

Protocol version 2 confirmation: preserve the first comparison as `selective-benchmark-exploratory.json`. It showed component caching slower than the conventional cache. Deploy the conventional whole-suffix cache as the default and use its actual implementation in the confirmation benchmark. Re-materialize equal snapshot records on every step in all modes, including that common construction cost; this avoids object-identity shortcuts unrepresentative of fresh database reads. Report the revision explicitly. No success threshold or selected workload changed in response to the initial result.

## Milestone 3 scoped-concurrency correctness

Two immutable stripes begin with two valid rows on S/T, using distinct fixed source slots in those shared domains. Each stripe claims a separate X/Y destination. Enumerate all 20 order-preserving interleavings of their reserve/stage/promote sequences in actual durable stores, auditing safety and content after every step. This is exhaustive for that two-plan, six-action fixture only. Check equivalent restoration in full, conventional cached, selective and shadow modes; test transactional shared-stripe/shared-slot rejection, duplicate-step races, completion/cancellation isolation, unclaimed cleanup, phantom membership, missing claims, relevant/unrelated domain failure and global takeover.

Run two local controller processes against the same authority. Separately interrupt one plan during staging or reclamation while the other remains active, reopen under a new fence and finish both. Include an additive-migration test for an active legacy full-store plan. The persistent concurrent demonstration uses a retired destination to exercise claim protection before and after physical reclamation, checks full-reference agreement in shadow mode and validates original bytes after reopening.

The existing 10,000-trace seeded campaign still measures the previously stated sequential finite-model scope. Its counts must not be presented as 10,000 concurrent schedules. No performance comparison or success threshold changes in this milestone. Scoped claims are a conventional mechanism; compatible concurrency does not by itself establish novelty, parallel storage throughput or the conditional patentability target.

## Milestone 4 storage-worker correctness

Enable trusted local per-domain storage processes after fixture import. Use the same scoped A/B fixture, with and without an initially retired destination. Check full, conventional cached, selective and shadow restoration. Pause one domain worker while another plan completes to establish that repair I/O holds no authority writer transaction. Check cancellation and takeover drain barriers, durable fence regression rejection, grant revocation across slot reuse, duplicate stage controllers, unchanged scoped receipts under unrelated progress, altered/forged receipts and physical corruption rejection.

Interrupt the physical worker before I/O, after fsync and after worker-journal commit; retain charged allocation metadata and reconcile on same-epoch retry. Interrupt the controller after intent commit, after receipt reply, before authority commit and after authority commit; transfer to a new fence and restore both objects. Preserve the prior 26 interruption cases as regressions. Count these seven new cases separately from model traces. No real power-loss or independent-device experiment is implied.

The persistent worker demonstration records separate worker PIDs, stage/reclaim receipts, physical digests and both original content readbacks. Preparation performs full suffix replay, completion performs configured replay/cache guards, and receipt/payload/source verification adds work. No controller-level performance or patentability gate is passed by process separation or these correctness checks.

## Milestone 5 versioned 4+2 correctness

Use the fixed systematic P/Q profile in the coding contract. Compare every byte-pair field multiplication against an independent polynomial oracle (65,536 products), all 15 four-row generator determinants against zero, and production/oracle encoding and reconstruction on 12 seeded lengths including empty, padded and multi-byte content (180 selections). The oracle has its own literal matrix and polynomial/cofactor arithmetic, without importing production profiles or coding helpers.

Enumerate all 15 initial four-row subsets, three destination-eligibility choices, four retired/free destination patterns and four destination-offline patterns: 720 finite repair cases. Compare bounded BFS and conventional scheduling with the independent two-destination capacity condition; no budget-exhausted case may be treated as infeasible. For feasible cases, compare production transitions, both cache classes and independent suffix replay, and reject stale allocation incarnations. This finite campaign does not enumerate general concurrent states.

Restore real bytes from each initial four-row subset in durable stores. Test local and worker paths in all four validation modes, mixed-profile concurrent scopes, all 15 two-domain failure combinations, corrupted sources, malformed/padded rows, profile downgrade rejection, historical witness replay and additive migration while a legacy worker intent is pending. Add four actual controller/worker process-exit boundaries for the 4+2 fixture. Preserve prior tests as regressions.

The persistent mixed-profile demonstration starts the 4+2 stripe with rows 0, 2, 4 and 5, restores missing data rows 1 and 3 through workers, reclaims a retired destination and independently completes a default 2+1 stripe. Record receipts and original content readback after reopening. No performance threshold or patentability rating is changed by these correctness results.

## Milestone 6 local controller comparison

The separately frozen [controller protocol](controller_protocol.md) extends measurement to real durable stores, physical reconstruction/checks and worker RPCs, with a concurrent foreground reader and no-repair controls. Its versioned SHA-256 is saved with raw paired data. It retains the capable conventional cached baseline and unchanged research thresholds. This reduced no-fault/reclamation suite does not complete the original verification-CPU, saturation, fault-performance or independent-hardware research evaluation.
