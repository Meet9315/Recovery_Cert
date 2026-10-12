# Milestone 1: Local continuation and reclamation prototype

Date: 11 October 2026. The authoritative machine-readable outputs are [verification.json](verification.json) and [demo.json](demo.json), which include runtime versions and source hashes.

## Results

| Check | Observed result |
|---|---|
| Test methods | 30 passed |
| Independent small eligibility comparison | All 49 pairs agreed with the finite assignment oracle |
| Actual subprocess interruption cases | 15 passed, with restart and fenced continuation |
| Seeded model traces | 10,000 |
| Distinct initial configurations | 2,479 |
| Distinct visited states | 3,772 |
| Validated model actions | 46,282 |
| Malformed-generation validator checks | 92,564 |
| Observed invariant violations | 0 |
| Durable demo | Seven committed steps; both original contents recovered exactly |

## Demonstration

Initially each stripe has two rows on domains S and T. B's only eligible missing-row destination is X; A may use X or Y. X is initially occupied by retired bytes. The witness reclaims X, repairs B there, and repairs A on Y. Future X capacity remains charged before reclaim acknowledgement, and becomes held rather than generally available after acknowledgement.

All six managed slots are LIVE at completion. The persisted cursor is seven and the plan is DONE. Source bytes and newly reconstructed rows are checked against immutable digests; content readback after authority reopening matches the originals.

The conventional capacity-aware baseline also produces a valid solution. The BFS planner and baseline may choose different safe action orders. No superiority over that baseline is inferred from their correctness.

## Interpretation

This establishes an executable reduced embodiment and reproducible finite/process-fault evidence. It does not establish selective reuse, scalable concurrent planning, independent failure-domain protection, power-loss behaviour, performance thresholds or patent novelty. The conditional 73/100 target remains unearned.
