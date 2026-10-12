# Selective continuation validation, version 1

## Dependency units

A validated suffix is partitioned into independent components. A component owns a stripe's policy, all slots currently assigned to that stripe, all slots touched by its remaining actions, and the online/offline state of those domains. Stripes are merged when an action slot is associated with more than one stripe. Anonymous reclamation and untouched capacity belong to components too. Consequently all slots and stripes are covered exactly once.

Coverage is derived internally from the current snapshot and suffix; a controller cannot supply an incomplete list. Each validation recomputes membership. An inserted reservation for a stripe or a slot reassigned between stripes changes coverage and causes a full rebuild. Component projections include all allocation fields and incarnations, so absence predicates are covered through complete membership comparisons rather than event notifications. This implementation scans membership; it does not introduce a writer-maintained index.

## Reuse rule

Each trusted cached component binds its projected starting state, ordered remaining actions and checked projected terminal state. If coverage, start projection and actions match, reuse that result. Otherwise replay that component independently. Merge component results and compare the complete terminal fingerprint with the witness commitment. An unrelated operational annotation is excluded from the logical state and cannot change authority, allocation, policy or bytes.

The current action is independently replayed before storage I/O. On successful commit, update that component's starting state and remove its first remaining action; its suffix certificate remains valid by the already-checked transition. Cache cursor, manifest/slot transition and plan cursor are persisted together. Reopening can reuse the trusted durable cache. Absent, malformed, wrong-version or wrong-binding caches cause complete rebuild. The database is trusted; administrative modifications of cached conclusions are outside the fault model.

Source-content validation, receipts, fencing, pins, holds and reclamation I/O checks are unchanged and are never bypassed by this logical cache. SQLite still serializes each command and its physical I/O. Cache reuse alone is not permission for multiple concurrent continuations. The separate [scope and claim rules](concurrent_plans.md) authorize compatible plans. For those plans, the complete snapshot passed to this cache is the authority-derived projection with all scoped members and claimed destinations. Membership and complete claim ownership are checked before cache validation. All four validation modes use that same scope, so conventional scoped caching remains the capable comparator.

The default runtime mode uses a conventional exact-state guarded whole-suffix certificate. The component cache remains an explicit experimental mode because initial comparison showed its overhead exceeded that conventional cache. Switching modes rebuilds incompatible cache representations from complete reference validation. Shadow mode uses component caching and also executes full replay to detect disagreement.

## Reference and measurement

In opt-in worker mode, preparation performs complete remaining-suffix validation before persisting its intent. Completion uses the configured validation mode again, plus current source and receipt/physical checks. This additional preparation work is not included in the earlier logical benchmark and must be charged in future controller comparisons. See [storage-worker protocol](storage_workers.md).

Full mode replays the whole suffix. Selective mode checks components, and replays changed components. Tests compare outcomes under relevant state/policy/membership mutations, untouched-capacity changes, wrong generations and restarts. The benchmark measures total logical validation CPU, including admission, cache construction, membership/projection comparisons, component merges, terminal binding, current-step checking and advancement. It does not measure storage throughput or foreground p99, and does not satisfy the full project's comparative-performance gate.
