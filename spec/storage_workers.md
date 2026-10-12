# Local storage-worker protocol

Version 1 — 12 October 2026. Opt-in trusted local embodiment, not a network service.

## State and authorization

The authority retains its SQLite WAL metadata, complete scope claims, witness cursor, source pins and destination holds. A separate worker SQLite database exists for each fixed domain pool. It stores the authority incarnation, pool dimensions, monotonically increasing fence, revoked grant tokens and durable signed receipts. Workers are launched as separate Python processes using JSON on stdin/stdout. They never request an authority writer transaction.

Enable workers with `enable_workers(fence)` after fixture import and before first plan admission. The local path remains the default. Reserve, promote and retire are authority metadata actions. Stage and plan reclamation use the two-phase path; bootstrap, source reads and explicit post-cancellation cleanup retain the local authority path. Simulated domain labels are not independent physical devices.

## Prepare, execute, complete

1. **Prepare:** inside an authority write transaction, validate the whole remaining scoped suffix, source bytes, claims, exact slot incarnation and action. Persist a unique grant token and immutable command. Bind store incarnation, global fence, plan/witness, cursor, full scoped starting fingerprint, original slot record, action, worker index and stage payload. Commit before dispatch. The manifest remains RESERVED or RETIRED and its capacity remains charged.
2. **Execute:** outside that authority transaction, a domain worker takes its own SQLite writer lock. Reject revoked grants, older fences, unknown/uncommitted intents, canceled plans, moved cursors, changed slot records and offline domains. Read one consistent committed authority snapshot through a read-only WAL connection and close it. Retain the worker lock during extent writing, flush/fsync and receipt commit. A stage writes the expected padded fragment; reclaim overwrites the full extent with zeros. The worker receipt binds the command digest, allocation incarnation, physical digest, worker PID and a local HMAC signature. Its secret never leaves the worker database.
3. **Complete:** take a new authority write transaction. Recheck ownership, scope, current sources and the complete remaining continuation. Match the original command against the current cursor/state/slot/action/payload. Compare the supplied receipt with the durable worker receipt and check the full extent bytes. Commit receipt consumption, slot category/manifest, cache and cursor together. No worker receipt alone makes data LIVE or capacity FREE.

Retries reuse the same committed grant when its epoch and scoped state match. A duplicate execution returns its durable receipt only after confirming its physical extent still matches; it does not silently repair acknowledged corruption. Completion is idempotent by plan step. Another disjoint scope can complete while this worker holds its own lock. Same-domain workers serialize on their domain database; different domains have independent locks. No throughput benefit is claimed from this design alone.

## Cancellation and takeover barriers

Cancellation holds the authority writer lock, takes each affected worker lock and durably revokes its outstanding grants before retiring partial allocations or releasing claims. A worker already in flight completes before the revocation barrier returns. A delayed or queued invocation cannot execute a revoked grant after slot cleanup/reallocation, even while cancellation metadata has not yet committed.

Takeover holds the authority writer lock and advances every worker fence before committing the new global epoch. Each worker fence update waits for that worker's in-flight I/O. Old commands cannot write after takeover returns, and old receipts cannot advance a plan under the new fence. A successor re-prepares with a new grant and revalidates its exact current state.

Lock order is authority writer -> worker writer for control barriers; a physical worker holds worker writer -> short **read-only** authority WAL snapshot. Workers never acquire the authority writer lock. The code uses WAL so that the read path does not wait for the metadata writer. Raw database/pool writers, worker control calls by untrusted users and network attackers remain outside this trusted local fault model.

## Interrupted operations

- Controller loss after preparation leaves occupied metadata and a durable grant.
- Worker loss before receipt commit leaves the old charged category, including after fsync. Re-execution writes the same exact bytes safely.
- Worker loss after receipt commit but before reply reconciles through its durable journal.
- Controller loss after receipt but before manifest commit leaves the receipt and old metadata; retry or a fenced successor revalidates and completes.
- Controller loss after manifest commit returns an idempotent step acknowledgement.
- Failure midway through a multi-worker fence/revocation barrier can advance some workers before authority rollback. This fails closed: those workers reject the old epoch/grant. Retrying takeover can finish the same epoch; cancellation can retry its revocations. Availability during worker loss is not guaranteed. No automatic timeout reuses charged capacity.

Process exits and Windows/Python fsync evidence do not prove power-loss durability, device/rack independence or Byzantine safety. This version deliberately performs full suffix validation during preparation, in addition to the configured completion checks; no cache CPU advantage is assumed. Network daemons, authentication across hosts, independent device-failure tests and the larger 4+2 profile remain pending.
