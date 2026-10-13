# Milestone 12: minimum-work baseline and mechanism gate

Registered 13 October 2026, before real-store comparison collection. This is an untimed work-count study. No CPU, foreground-latency, restoration-time or patent-score confirmation is registered.

Question: does first-feasible partial-state planning unnecessarily discard authentic staging, and does any saving survive a conventional cost-aware replanner?

Implement conventional bounded branch-and-bound assignment minimizing committed stage count, then action count. Independently search finite model transitions by Dijkstra with per-action costs. Compare all 136 specified finite matrix cases, retaining INFEASIBLE and UNKNOWN. An exploration limit must never turn a feasible incumbent into a claimed optimum. Add real-byte, corruption, input-order and CLI regressions.

Freeze production/tests, this protocol and the collection script in Git. Record commit, source hashes and script/protocol hashes. Real-store collection uses two coding profiles × local/worker I/O × seeds 20261013–20261015, three variants each: first-feasible conventional cached (diagnostic control), minimum-work conventional cached (primary baseline), and minimum-work selective. That is 12 matched sets, 36 stores. Rotate variant order deterministically per seed. All variants get identical immutable 1025-byte A/B objects, foreground object, 1024-byte slots, sources, interrupted parent, failure Z, eligible alternatives, source checks, claims, revocation and physical byte enforcement.

The parent reserves every original destination and stages B:X. Z then goes offline. A can use X or retired Y; B can use X or free W. In 4+2, A:P and B:Q are matching reservations. Record complete witnesses, committed action sequences, stage counts/extent bytes, all ledger snapshots, failed charges and exact A/B/foreground readback. Every store must end fully restored without active plans. This fixture represents simulated local domain failure, not loss of a physical device.

Run the independent graph oracle on one actual snapshot per profile with a 100000-state budget; preserve UNKNOWN as unresolved, never omit it. This supplements the matrix and qualifies minimum-work claims to the stated finite grammar. Work counts exclude duplicate unacknowledged writes and do not measure total I/O. Do not claim a wall-time benefit from fewer stage actions; planning cost and real resource contention may offset it.

If minimum-work conventional and selective have identical witnesses and work, the planner saving is a shared conventional improvement. It supplies no selective-validation advantage. Preserve first-feasible savings but do not promote the weaker control to the primary comparator. A large timing confirmation remains gated until an attributable mechanism difference survives the strengthened baseline. Existing 20% verification CPU / 10% secondary / 5% foreground requirements and historical failed measurements remain unchanged.
