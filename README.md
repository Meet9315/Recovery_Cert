# RCSD-PRISM-C research prototype

A runnable local prototype of reservation-backed repair continuations and acknowledged storage reclamation. Python 3.11 or later; standard library only. No installation or network access is required.

## Run

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
```

The demo root must be new or empty. Existing stores are never reset by the demo. Choose a new root name for another run. `verify` uses disposable temporary stores and preserves the report, test details, source hashes and model campaign counts.

To resume an interrupted plan: `python -m prism_c resume --root <store-directory> --plan <plan-id> --takeover`. This advances the owner fence, invalidating older controllers. `cancel` accepts the same arguments and leaves materialized partial writes charged until reclamation; cancellation does not immediately free their capacity.

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

## Scope

This is a trusted local single-authority embodiment. Domain labels are simulated. Slot reclamation means the managed extent has been durably overwritten and may be reused by this allocator; no filesystem unlink/free-space inference is used. The default local mode keeps storage I/O inside the metadata writer transaction. Opt-in workers perform stage/reclaim I/O outside it using checked intents, worker-side fencing and revocation. Source validation, promotion, fixture import and explicit cleanup retain the local authority path.

Witnesses bind the complete terminal state of their admitted scope. Selective mode reuses validated component suffixes when their full projected dependencies and membership are unchanged. Related changes are replayed; coverage changes cause rebuilding. Exact terminal binding still rejects even otherwise-safe policy changes. Physical source checks are performed on every step. See [selective validation specification](spec/selective_validation.md).

The logical benchmark compares full replay, component caching and a conventional exact-state guarded cache, including cache preparation and advancement. Results from this limited in-memory test cannot establish storage throughput or the project's overall CPU/latency targets. Network storage daemons, controller-level 4+2 performance, independent device failures and power-loss testing remain future work. No new patentability score follows from these tests.

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

## Repository verification

GitHub Actions runs the correctness/process-fault suite, 1,000 seeded model traces and the independent 4+2 campaign on Ubuntu and Windows with Python 3.11, and saves its verification report. The 4+2 campaign checks all 65,536 field products, 15 reconstruction subsets and 720 finite repair cases. The local milestone reports retain the larger 10,000-trace campaign. Runtime databases, worker secrets, byte pools, temporary extraction files and generated caches are excluded from version control; project source, specifications, disclosure/review documents and saved evidence reports are included.

The first comparison found component caching slower than the conventional guarded cache, despite savings against full replay in larger groups. The confirmation comparison uses fresh snapshot records and the deployed cache implementations. See [milestone 2 results](evidence/results/MILESTONE_02.md) for the measured scope and interpretation.

See [PROGRESS.md](PROGRESS.md), [implementation scope](spec/implementation_scope.md), [execution plan](RCSD_PRISM_C_Conditional_Target_Execution_Plan.md) and [proposed disclosure](RCSD_PRISM_C_Proposed_Invention_Disclosure.md).
