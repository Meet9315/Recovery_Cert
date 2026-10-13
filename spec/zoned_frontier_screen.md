# R14-A: bounded reset-frontier mechanism screen

13 October 2026. This is the first gate of the [redesign plan](../RCSD_PRISM_C_Redesign_Plan.md). The executable [diagnostic](../analysis/zoned_frontier_gate.py) is an in-memory abstraction, not R14-E's durable zoned adapter. No source in the existing `prism_c` runtime is changed.

## Precise algorithm

An extent has immutable identity, one of LIVE/STAGED/RETIRED, a nonnegative pin count and a nonnegative grant count. Extents occupy unit written positions inside a zone. A zone tracks capacity, monotone write pointer, held append units, online status, namespace incarnation, zone incarnation, monotone revision, owner fence and an optional pending reset identity.

The authority derives complete membership and delivers one committed mutation at a time. An inserted extent consumes new append position; retiring an extent never reduces written positions. Every relevant mutation advances the revision. Namespace rebuilding, incarnation replacement and ownership changes have separate guards. These are trusted authority assumptions, not properties proved about the existing SQLite store by this diagnostic. There is no user-supplied dependency list, serialized certificate or concurrent mutator API here.

Proposed frontier: store the set of `(extent identity, reason)` for retained LIVE/STAGED status, nonzero pins and nonzero grants. Build from all authoritative extents; on a committed single-extent change, remove the old reasons and add the new ones. Bind to the full zone/namespace/revision/fence token. An unchanged token permits a constant-size header check and emptiness query. A stale token fails closed until an authoritative update or full rebuild.

Ordinary comparator: retain three counters, for retained extents, total pins and total grants. Build by summing authoritative extents. Subtract the old contribution and add the new contribution on each identical committed event. Use the same generation guard and zone headers. This comparator is implemented separately from the frontier; it does not call frontier construction or predicates.

Independent reference: inspect the current authoritative extents directly without counters/frontier calls. Reset eligibility requires online status, no pending reset, no held append units, and every extent RETIRED with zero pins and grants. The tests and campaign compare both implementations against this recomputation.

## Soundness, completeness and cost for this contract

Let `L(e)` mean extent `e` is LIVE/STAGED, `P(e)` mean its pins are positive and `G(e)` mean its grants are positive. The frontier is empty exactly when every `L(e), P(e), G(e)` is false. Because all counters are nonnegative, the ordinary retained/pin/grant totals are all zero exactly under the same condition. The header conditions are identical. Therefore both decisions equal the full reference for every state in this contract, not just the enumerated matrix.

The invariant holds after full initialization. Replacing one extent removes its old contribution and adds its new contribution in both representations. Inserting one extent contributes its new reasons/counts and advances authority membership. Header changes update guard/header state. Induction establishes the invariant for any finite correctly delivered sequence of these events. Missing/skipped events cannot be reused through a matching authority revision; cache loss uses full rebuild. Counter ABA across authority/index rebuilds must change namespace incarnation; this requirement is explicit and tested with token changes.

Both builds examine E extents. Both single-extent updates examine at most three reason classes. Both warm/reset queries use constant-size metadata. Counter state is constant-size per zone, while the frontier additionally stores blocker identities; the conventional authority still stores the actual extents. Hash-table operations are expected/amortized operations, not a strict worst-case bound or measured CPU saving. Neither path replays a repair suffix during an unchanged reset check.

Coding safety belongs at an earlier transition: before a LIVE extent becomes RETIRED, verify authenticated valid replacement/staging, manifest adoption, retention transfer and the declared decoding/placement obligations; retain outstanding grants/pins as blockers until drained. Removing a retained fragment merely because an unadopted replacement exists is forbidden. Once every reset extent is already retired and unreferenced, resetting that zone does not remove a LIVE coding row. A new data fault can still reduce protection separately; the reset predicate alone does not promise eventual repair completion.

The diagnostic includes a separate MDS retirement predicate for k=2/n=3 and k=4/n=6, counting distinct rows after individually declared domain-failure scenarios. Duplicate rows do not substitute for distinct rows. It is a metadata illustration, not authenticity verification, an arbitrary-matrix rank oracle, placement-target planner, actual repair or new coding result.

## Identity-bound outcome example

An admitted reset creates a ticket bound to zone, incarnation, owner fence and operation identity. Its pending state makes appendable capacity zero. An unconfirmed outcome retains the same write pointer/charge. A matching confirmed result may clear retired extents, set the pointer to zero and advance incarnation. Stale/duplicate receipts, changed dependencies and takeover fail closed. Reconciliation after takeover is outside this screen; a blocked old receipt is not evidence of implemented liveness/recovery.

This is metadata-only arithmetic. Neither a device command nor a subprocess/storage crash is executed by these receipt examples. Real bytes, journalling, fsync, delayed worker I/O, open/active-zone tokens, physical recovery and foreground latency remain outside scope.

## Research consequence

Under the stated frontier algorithm, ordinary indexed reference tracking supplies the same decisions and operation bounds. This constructive comparison rejects the proposed representation as the missing distinguishing contribution for R14-A. It does not prove legal anticipation by a single source, obviousness of every possible exact claim, or absence of an alternative algorithm. A physically different contract alone cannot supply invention evidence.
