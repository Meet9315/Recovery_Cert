# Serialized zoned-file store contract, version 1

14 October 2026. Implements E16-A/B/C's bounded local embodiment on the [R15 nominal model](zoned_joint_model.md). Opt-in module `prism_c.zoned_store`; no old slot-store migration or default change. This contract covers trusted cooperating local processes and actual process termination, not native ZNS compatibility, storage-agent fencing, kernel crashes or power loss.

## Persistent scope and files

`ZonedFileStore.create(root, initial, contents, unit=64)` requires a nonexistent root and a protected, settled model state. It never erases an existing root. All bootstrap code rows have exactly one unit; profiles are versioned 2+1 XOR and 4+2 P/Q. Arbitrary zone identities are hashed into controlled `zones/<sha256>.bin` filenames. Retired holes remain physical bytes until whole-zone reset. FINISHED tails remain unavailable even when the backing file is shorter than capacity.

Separate `zoned.sqlite3`, WAL, synchronous FULL. Schema: singleton `authority(id=1, document JSON)` and `receipts(cursor primary key, document JSON)`. Format `prism-zoned-file-v1`; unknown versions are rejected. Authority contains store UUID, unit, complete nominal state, immutable object manifests, owner fence, one installed witness, cursor, pending intent and quarantine reason. The state persists extents/references, logical append positions, capacities, phases/finished tails, external holds, reservations, incarnations and open/active budgets. Actual file length is independently inspected, not guessed from the nominal position.

Manifest: content epoch 1, coding profile, length, content SHA-256 and all code-row SHA-256 digests. No original plaintext is kept as a recovery fallback. Objects are immutable; mutable epochs are not exposed. Creation is offline bootstrap; an interruption during creation may leave an unusable root which cannot be silently reused. Creation/directory durability is not certified.

## Authority and retention

Every API byte read, preparation, physical append/reset and metadata publication uses a SQLite `BEGIN IMMEDIATE` transaction. Only one writer transaction can hold the byte-operation authority. The byte-I/O transaction rechecks the current fence before issuing filesystem operations and stays held until commit/rollback. Source rows cannot retire, reset or change their manifest during that I/O through this API. Fixed existing pins/grants/holds remain in force; the model forbids retiring referenced extents and resetting retained extents. This serialization is the retention mechanism for synchronous reads and reconstruction; it is not a new asynchronous source-grant implementation.

`takeover()` increments a persisted owner fence. It waits for any in-flight file transaction. An actor paused after preparation but before I/O must acquire a new transaction and is rejected if fenced out. The new owner can reconcile the same pending operation. Concurrent callers may help the same cursor; receipt lookup binds completion to the originally requested cursor. There are no already-issued asynchronous device commands that can arrive after takeover in this embodiment.

One immutable whole-scope witness may be installed per fresh store. Admission replays its exact initial fingerprint/zone incarnations and complete target using the nominal model, inspects settled geometry and authenticates all online LIVE rows. No external mutation, dynamic grant, plan replacement or raw reset API is exposed. Cancellation is deliberately not exposed: a future cancellation protocol must first reconcile/drain the prepared operation, then retain all materialized/staged/retired allocations until safe cleanup. No cancellation-liveness result is claimed here.

## Append protocol and uncertain completion

1. A previously committed `reserve` owns the destination unit. Preparation checks the next witness action, current geometry, all online LIVE source-row digests, reconstructed object digest and regenerated row digests. A durable intent is committed before byte I/O.
2. Intent identity includes store UUID, cursor, exact prestate fingerprint and full action with zone incarnation. It additionally records the expected physical position, immutable epoch and expected row digest. Reconciliation rechecks these bindings and the current fence.
3. At the expected end, write exactly one unit sequentially, never into a retired hole. Two half writes with synchronization at each boundary provide a real partial-write fault point. All compared routes use this identical implementation. Reconstruct from authenticated LIVE source files, never from a saved original object.
4. A full already-materialized matching unit is synchronized and adopted without another append. A partial, overlong or invalid full pending append quarantines the entire store. The intent, reservation and cursor remain retained; bytes are not truncated/rewound. Allocation is blocked on subsequent calls and the ledger reports zero appendable units throughout quarantine. Healthy authenticated object reads remain available. Recovery does not promise eventual repair of quarantined stores.
5. Authenticate the materialized unit after synchronization. Commit allocation/state, unique receipt and incremented cursor atomically; clear the pending intent only in that commit. Promotion separately authenticates the staged unit before LIVE publication. I/O exceptions leave the committed pending intent for later inspection.

The ledger charges the maximum of nominal extent/hold/reservation allocations and rounded physical consumption. Pending valid full writes never double-charge the same reserved unit. A geometry mismatch also suppresses reported free space in the affected zone before reconciliation. Overcapacity corruption is reported through physical/charged counts, not normalized into fake free space. `audit()` may reject an uncertain geometry; rejection is not evidence of a completed plan.

## Whole-zone reset protocol

`reset_request` commits RESETTING only after the complete extent closure is RETIRED with zero pins/grants, no reservations and no external holds. Previous open/active tokens and all logical allocations remain charged. The next `reset_ack` creates a distinct durable physical-reset intent under the same identity/position checks. Whole-file truncation plus fsync emulates a zone reset; it is never used to undo an uncertain append.

Only an exact old length or zero length is admissible during this pending reset. Zero length plus the saved matching operation is reconciled as an already-performed reset under the exclusive file-authority assumption. The acknowledgement transaction clears extents, releases tokens and advances incarnation together with receipt/cursor. An old duplicate cursor returns its old receipt; it cannot truncate the new incarnation. No general inference that any empty file confirms any stale reset is allowed.

## APIs, accounting and limits

`admit`, `advance(fence, expected_cursor=None)`, `execute`, `takeover`, `snapshot`, `read`, `ledger`, `receipts`, `audit`. Diagnostic hooks expose real prepare/I/O/commit boundaries; `prism_c.zoned_fault` uses `os._exit(86)`. Receipts count committed stage bytes, including relocation/repair alike. For normal campaign routes each stage performs exactly one unit of new file writes; bootstrap bytes are excluded. Receipts alone are not a complete I/O-cost measurement during faults, nor a timing measure of SQLite, fsync, metadata, reads or retries.

All authority actors and files are trusted; direct administrator writes in tests deliberately simulate corruption. Store IDs, digests and fences are local consistency bindings, not signatures or adversarial filesystem access control. Multiple zones on one local filesystem are simulated domains. A replay/model reference is independent at the transition/search level; it is not an independent filesystem implementation.

SQLite documents [single-writer transactions and BEGIN IMMEDIATE](https://www.sqlite.org/lang_transaction.html) and [synchronous modes](https://www.sqlite.org/pragma.html#pragma_synchronous). File fsync ordering is requested; actual hardware/OS synchronization guarantees, directory entry persistence, torn metadata, power loss and real reset acknowledgement require separate platform evidence. No device write-pointer query, native zone report, native error status, external reproduction or full-cost foreground result is implemented.

Readiness remains the previously assessed **55/100**. This conventional engineering embodiment establishes no new novelty or inventive-step result.
