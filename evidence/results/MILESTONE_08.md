# Milestone 8: authenticated snapshot reads and fixed-arrival latency

12 October 2026. Added opt-in `Authority.read_snapshot(name)` alongside the unchanged serialized `read` default. The operation uses a committed SQLite metadata snapshot and the same physical source/reconstruction checks. Any reconstruction rejection closes that snapshot before one serialized fallback. A documented continuation completed forty pairs across four configurations. Snapshot reads improved loaded p99 in three configurations, but none met the 5% own-control foreground condition. Full verification passed 120 methods and 296 subtests.

## Implementation and safety

The [read contract](../../spec/snapshot_reads.md) explains the immutable identity and physical-byte race boundary. SQLite WAL snapshot isolation is a conventional facility; it does not version external pool bytes. Every successful read retains expected row/slot digest checks, coherent reconstruction, padding, regenerated-row identities and the original content digest. The operation observes the online/offline state of its committed snapshot. It makes no mutable-content or latest-placement promise.

An actual test pauses a snapshot read before reading a LIVE parity extent, then retires and durably reclaims that slot through a checked repair witness. The old snapshot's physical bytes fail authenticity; the read closes that snapshot and obtains the original content through the unchanged serialized path. Persistent source corruption and content-identity mismatch still reject. Other database/I/O errors propagate, and there is no unbounded retry. Tests also prove read-only connection enforcement, writer-lock overlap, committed offline-state handling, exact bytes through both profiles and both local/worker execution paths.

Repair admission, per-step physical checks, claims, fences, promotion, worker receipts, reclamation and the capacity ledger are unchanged. No schema or durable protocol migration is introduced. Serialized reads and conventional caching remain defaults. Short read transactions can retain WAL history and still compete for CPU/disk. Initialization still acquires the writer lock for additive migration; a fallback can block with the existing ten-second SQLite busy timeout.

## Registered comparison

The [fixed-arrival protocol](../../experiments/snapshot_latency_protocol.md), code and integrity tests were frozen before measurement in commit [fe1790eca5049e53dbcf5b8f2e36da737f088971](https://github.com/Meet9315/Recovery_Cert/commit/fe1790eca5049e53dbcf5b8f2e36da737f088971). The [raw paired report](snapshot-latency-milestone-08.json) checkpoints every completed API attempt and pair, including requests, failed outcomes, source/protocol hashes, seeds/orders, group witnesses, control/load/drain durations and fallback calls. Previous milestone protocols and results remain unchanged.

Protocol SHA-256: `62d092f4a40ba9c398388ae17480737489bd342a551a9a39e2718144b373876c`. The saved 33 source/test hashes and protocol hash match the frozen Git content.

The original campaign stopped after **35 completed pairs**, with `OSError(22, 'Invalid argument')` during finalization of its next pair. It saved **72 healthy windows**, including two windows in that failed pair. Its exact exception location is unavailable, and console output is only one possible cause. That raw report retains its failed status unchanged. The [continuation supplement](../../experiments/snapshot_latency_continuation_protocol.md) and helper were frozen in commit [9d4b26af4fd5e4ff3437c8f9fe77bed190b9d0dd](https://github.com/Meet9315/Recovery_Cert/commit/9d4b26af4fd5e4ff3437c8f9fe77bed190b9d0dd), together with the original failed report and three continuation integrity tests.

The separate [completion report](snapshot-latency-completion-milestone-08.json) references the original by canonical JSON hash, retains its 35 completed pairs and recollects both APIs for the failed pair onward. All original 33 production/test hashes match; the new environment records 34 files, including the additional continuation test. The helper's own hash matches the frozen code. Supplement SHA-256: `0da4bf759fb5eb34f9ecb6d8c7210f0c8c8b04310db85d00f84384dd9954d8a8`. No original extreme-delay pair is removed. The five new pairs completed with no read or telemetry errors after two separate warm-ups. This is a supplemented collection after interruption, not an uninterrupted original confirmation.

Both APIs use the **same conventional_cached controller**. Four configurations cover both coding profiles and local/worker paths; each has ten independently seeded pairs with randomized API order. Each fresh store has the same 64-group backlog and unrelated foreground object. Fixed arrivals offer 400 requests per phase at 100 Hz independently of read completion. All control requests drain before repair starts. All loaded requests remain in the report even if service starts or ends after restoration. End-to-end p99 includes scheduling and queuing; service p99 is separate.

The earlier closed-loop diagnostics are a different workload and must not be substituted for this confirmation. Early groups reclaim both destination slots; later backlog groups use free slots. Group counts can differ under the arrival-based stopping rule. This is a read-latency experiment; its group timing/counts do not establish paired CPU/restoration effects or selective-continuation superiority.

## Results and interpretation

The analyzed set contains **40 pairs, 80 healthy sufficient windows, 64,000 requests and 330 completed two-stripe repair groups**. Each window retained all 400 control and 400 loaded arrivals. All reopened content, completed targets, backlog safety floors and capacity checks passed. **4,470 loaded calls ended after restoration; 4,422 started service after restoration**. No snapshot fallback was needed for the unrelated foreground object; the actual retire/reclaim test separately checks fallback. The two saved windows from the failed original pair remain available but are excluded from the completed-pair analysis; their recollected counterparts are included. Thus the raw evidence preserves 82 measured windows, with 80 in the supplemented paired set. Original warm-ups (eight) and continuation warm-ups (two) are separate.

Positive reduction means snapshot loaded p99 was lower than serialized loaded p99. Intervals are the predeclared 2,000-resample bootstrap intervals of paired percent changes or mean loaded/control ratios. The foreground screen requires the snapshot ratio's upper bound to be at most **1.05**. No configuration passes.

| Coding/path | Mean paired p99 reduction % | 95% interval % | Serialized mean inflation | Snapshot mean inflation | Snapshot 95% ratio interval | 5% screen |
|---|---:|---|---:|---:|---|---|
| 2+1 local | -764.40 | [-2,250.05, 19.91] | 85.46 | 115.75 | [73.23, 164.88] | Not met |
| 2+1 workers | 92.32 | [90.41, 94.13] | 66.59 | 6.85 | [5.99, 7.81] | Not met |
| 4+2 local | 66.71 | [57.34, 75.76] | 55.99 | 30.81 | [19.19, 44.59] | Not met |
| 4+2 workers | 92.47 | [89.76, 94.67] | 68.10 | 5.83 | [4.40, 7.38] | Not met |

The first row is unstable and does not establish a slowdown magnitude or improvement. An early local 2+1 snapshot window recorded an approximately 187-second interruption across the repair group, a read in service and the arrival producer. Its loaded p99 is approximately 190 seconds and its loaded phase lasted approximately 191 seconds. The admitted group finishes under the registered rule; all 400 arrivals and readbacks were retained successfully afterward. Its paired percent change is approximately -7,380.8%, strongly influencing the mean/interval. The precise cause is not identified from the saved data. These simultaneous delays limit attribution to the API, and that completed pair remains included rather than being silently replaced or removed. Other requests also have substantial queue delay. Host scheduling/liveness and CPU/disk interference remain material measurement limits; the intervals do not control those effects or provide tail-SLO proof.

Improvement against serialized reads alone cannot meet the original foreground condition. The protocol reports each API's own loaded/control inflation and a narrow screen requiring its mean-ratio upper 95% bound to be at most 1.05. It does not declare the overall research gate passed. This conventional snapshot-read optimization applies equally to the competent baseline and does not establish an inventive advantage. The earlier 53/100 assessment and conditional 73/100 target remain unchanged.

## Correctness and next work

The [full verification report](verification-milestone-08.json) passed **120 test methods and 296 subtests**, with no failures/errors and all 37 actual process-exit regression cases retained. All 34 source/test hashes match the completion report and current files; the separately recorded helper/supplement hashes match their frozen Git version. Thirteen new integrity tests cover source/coding authenticity, real writer-lock overlap, committed offline-state handling, an actual retirement/reclamation race, no write permission on snapshot connections, fixed arrivals while a read is blocked, post-restoration queue draining, source/request integrity on continuation, and simulated console-output failure without a false research pass.

The separate 10,000-trace legacy campaign again covered 2,479 initial configurations, 3,772 visited states, 46,282 validated actions/cache-reference comparisons and 92,564 malformed-generation checks, with zero observed invariant violations. The independent 4+2 campaign again checked 65,536 field products, 15 nonzero reconstruction minors, 180 reconstructions and 720 finite repair cases, with 840 cache/reference comparisons, 840 stale-incarnation checks and zero disagreement. These retain their finite/local scope, without general concurrency, power-loss or novelty proof.

Next, investigate repeated coding work: `_valid_rows` already reconstructs and authenticates content, and both read APIs reconstruct the same in-memory rows again for their return value. Any optimization should reuse that authenticated result while retaining every row/identity check and should receive a fresh registered comparison. Include host-liveness monitoring and report interruptions explicitly. Any future selective-versus-conventional controller comparison must provide the same read optimization to both controllers. Fault/retry and scoped-contention performance remain pending.

## Reproduce

```powershell
python -m prism_c snapshot-latency --report evidence/results/snapshot-latency-new.json --runs 10 --seed 20261012
python -m experiments.complete_snapshot_latency --original evidence/results/snapshot-latency-milestone-08.json --report evidence/results/snapshot-latency-completion-new.json
python -m prism_c verify --report evidence/results/verification-milestone-08-new.json --traces 10000 --seed 20261011
```

Run the manual measurement on its own; do not run regressions concurrently. CI runs its sampling/safety tests, not the full performance campaign. Fault/retry performance, scoped contention, independent hardware, authenticated remote daemons and priority/inventorship review remain pending.
