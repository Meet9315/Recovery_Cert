# Implemented embodiment and invariants

This specification accompanies the initial implementation. An implemented feature and its verification are tracked separately in PROGRESS.md.

## Model

Each storage slot is FREE, RESERVED, STAGED, LIVE or RETIRED. A slot incarnation changes on allocation. A reclaim acknowledgement makes a retired slot reusable only after the trusted worker has durably overwritten it. The model uses unit-sized slots; runtime slots have a configured byte size and remain preallocated.

Capacity is the number of slots in each category multiplied by slot size. Offline-domain capacity is reported separately and cannot be allocated. Physical disk space outside these managed files is not modelled. This is a managed allocation pool, not a claim about filesystem free-space accounting.

Content is immutable; each stripe names a fixed versioned 2+1 XOR or 4+2 GF(256) P/Q profile. Its data-row count (two or four) is the safety floor; its total row count (three or six) is the terminal target. Live rows must be distinct and on distinct online domains. Runtime requires exact precomputed row digests and reconstructs/checks the original content before accepting live source data. Model validity assumes authentic rows. Domain eligibility is immutable in this version. The [coding contract](coding_profiles.md) specifies encoding, profile binding and historical-store migration.

Transitions: reserve -> stage -> promote; live -> retire -> reclaim; reserved/staged -> cancellation retirement -> reclaim. Free capacity cannot be spent twice. A reservation already contains the capacity charge; staging changes categories. Retirement does not release capacity. Absent or corrupt bytes must never be promoted. Retirement of live data must preserve the current safety floor.

Milestone 11 adds independently checked `abandon` of an exact pending allocation or offline LIVE row to RETIRED. It performs no physical release. The [revision contract](plan_revision.md) adds conventional partial-state assignment and a fresh scoped successor witness, with authenticated retained staging, old worker-grant revocation, exact request retries and atomic claim transfer. Exact terminal binding remains; a changed state requires a newly checked commitment rather than ignoring fields in the old witness.

## Witness and authority

A witness binds a complete model snapshot, ordered transitions and terminal state through a digest. Its snapshot is either the full store or an authority-derived whole-stripe scope. An independent checker replays its transitions without invoking the planner. Admission rejects snapshot conflicts and malformed or incomplete witnesses. Runtime supports complete replay and selective component evidence reuse on every authoritative step. [Selective validation](selective_validation.md) defines coverage, current-state guards and cache advancement. Source bytes are never trusted through that cache.

One SQLite BEGIN IMMEDIATE transaction serializes metadata mutations, promotion, retirement and takeover. Default local mode retains slot I/O inside that transaction. Opt-in [storage workers](storage_workers.md) execute stage/reclaim outside it through committed intents, worker fences/revocations and checked receipt completion. Source reads, fixture import and explicit cancellation cleanup retain the local path. There is no network agent authorization, distributed consensus or independent hardware in this version. Trusted callers must use the provided API; administrators/raw disk writers are excluded.

Foreground `read` retains the serialized path. Opt-in [snapshot reads](snapshot_reads.md) use read-only committed metadata plus the same physical authenticity checks; failed reconstruction closes the snapshot before one serialized fallback. External bytes are not snapshot-versioned or pinned by that read, and content identities remain immutable. This conventional read optimization does not alter repair authority or its source checks.

Commands carry a monotonically increasing controller fence. Takeover increments it atomically for every active plan. Applied steps persist a cursor and are replayable by step identity. No automatic wall-clock expiry is used. Multiple admitted scoped continuations can coexist when their whole stripes and fixed slot sets are disjoint. All claims are acquired atomically and checked before each step; conflicting submissions acquire no partial resources. Complete membership is rechecked, and each scope must reach its own checked terminal target. A full-store legacy plan remains globally exclusive. [Concurrent plans](concurrent_plans.md) defines the reduced compatibility policy. Claimed FREE slots are charged as reserved capacity until claim release.

Stage writes are flushed and fsynced before promotion; reclamation is flushed and fsynced before ledger release. Crash between I/O and metadata commit leaves the prior charged state and can be retried. Worker mode journals its receipt before reply, and the authority commits consumption with the manifest and cursor. Cancellation revokes pending grants before claim release; takeover advances durable worker fences before publishing its new epoch. Reclamation cannot be reversed into LIVE. Storage layout is a fixed pool so metadata rollback cannot expose a partially written slot as an authoritative new fragment.

## Scope of fault evidence

Tests can demonstrate process interruption, rollback, restart, stale messages and concurrent local connections. File synchronization depends on OS/filesystem/device behaviour. This implementation does not establish power-loss, device/rack independence, Byzantine safety, 4+2 performance or the patent target.

## Primary invariants

1. Slot-category capacity conservation; only FREE online slots allocate.
2. Every staged/live row has the correct immutable stripe identity and row digest.
3. Required live sources cannot be retired while the safety floor would be broken.
4. Admission and each continued step agree with the authoritative snapshot.
5. Cursor, manifest and allocation-category transition commit together.
6. Physical reclamation precedes allocation-ledger release.
7. Stale fences cannot mutate either metadata or managed bytes.
8. A complete checked continuation reaches its target when resources remain available and execution eventually proceeds.

Known limitations: exact terminal-state conflicts; serialized metadata/source checks and global takeover; local per-domain worker locks; no concurrent mutating plans sharing stripes or slots; complete membership scanning instead of writer-maintained indexes; no externally changing policy or aggregate cross-stripe resource policies; planner is bounded exhaustive search rather than a scalable scheduler. Component reuse and worker I/O separation are implemented mechanisms; their usefulness against a competent conventional controller requires evidence.
