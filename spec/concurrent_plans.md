# Compatible concurrent continuations: local embodiment

Version 1 — 12 October 2026. Logical concurrency is supported through interleaved operations on multiple active plans; individual SQLite transactions and byte I/O remain serialized. There is no claim of parallel physical I/O or a throughput gain.

Milestone 4 extension: the preceding I/O statement describes default local mode and the milestone-3 evidence. Opt-in [storage workers](storage_workers.md) now separate stage/reclaim from the authority transaction. Scope compatibility and claims are unchanged; per-domain worker fences/revocations add the required ownership barriers. No measured throughput advantage is established.

## Plan scope

A scoped plan selects a nonempty set of whole immutable stripes and explicit destination/retired slot identities. The authority derives a projection containing every slot currently assigned to those stripes plus those explicit slots. The caller cannot omit a current source, reservation or staged row by supplying an incomplete snapshot.

The checked witness's initial and terminal fingerprints apply to this projection. The terminal condition restores every scoped stripe. Unrelated stripes can remain degraded and independently progress; complete-store restoration is an aggregate outcome, not a precondition for each individual plan.

All scoped stripe metadata and every projected slot are exclusively claimed in the admission transaction. Slots intended for future use remain claimed even after their destination hold is materialized, preventing another plan from reclaiming or reallocating them. Claimed FREE slots are reported as reserved capacity until those claims are released. Complete same-stripe membership is rechecked on every step. Using a slot still assigned to an unscoped stripe is rejected. The finite planner remains repair-only; a general migration scheduler is outside this milestone.

## Compatibility

Two plans are compatible only when their stripe sets and fixed slot-claim sets are disjoint. They may share a physical domain label when they use different preallocated slots. The current failure policy has independent per-stripe constraints and unit slot accounting; aggregate bandwidth, domain repair budgets and cross-stripe policies are not supported. This disjointness rule is deliberately conservative.

Concurrent reads of pinned immutable sources are allowed through the authority. Two mutating plans on the same stripe or source slot are rejected. Shared-source repair plans are not claimed as supported. A full-store legacy plan remains exclusive with every other plan.

## Authority and failure handling

Admission checks the current scoped snapshot, full witness, source bytes and all conflicting claims before creating any holds/pins. Rejection rolls back the entire claim bundle. No partial acquisition or wall-clock expiry is used.

Each step checks its plan fence, stripe claims, slot claims and exact scope membership. Source validation and current-step checking apply to the projected state. Changes outside the scope do not invalidate its terminal fingerprint or cache. Failure of a shared source domain affects every plan that actually uses that domain; an unrelated destination failure does not block another scope.

Takeover is still a global authority-epoch change, fencing all older controllers and transferring every active plan to the new epoch. Independent per-plan controller leases are outside this embodiment.

Completion releases only that plan's claims/pins/holds. Cancellation retires only that plan's reserved/staged slots and keeps their capacity charged until physical acknowledgement. Cleanup may occur beside another scoped plan only when the exact retired slot has no live claim/pin. Full-store active plans block external cleanup.

## Validation required

Check disjoint simultaneous admission, shared-slot and shared-stripe rejection, all 20 action-order interleavings of two 3-step repair plans, duplicate-step races, completion/cancellation isolation, global takeover, shared-domain failure, independent-destination failure and process exit while another plan remains active. Test both conventional cached and selective/shadow validation. Conventional scoped reservations provide the competent baseline; the mechanism is not asserted novel by this implementation.
