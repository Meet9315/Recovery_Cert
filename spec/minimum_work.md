# Minimum-work partial recovery

13 October 2026. A conventional improvement shared by all validation modes; no inventive distinction asserted.

## Problem and objective

Milestone 11's first feasible assignment prefers a stripe's own staged rows locally. That does not maximize useful staging globally. In the minimal example A can use X or Y, B can use X or W, X already stages B's missing row, Y is retired, and W is free. Choosing X for A discards B's staged row and writes two rows. Choosing Y for A retains X for B and writes one row.

`conventional_min_work_plan` minimizes `(number_of_stage_actions, number_of_all_actions)` lexicographically, over the supported partial assignment problem: online LIVE rows fixed, distinct eligible online domains per stripe, one assignment per missing row, shared physical slots used once, pending allocations retained or abandoned and retired slots reclaimed before reuse. Uniform fixed-size runtime extents make committed stage count proportional to stage extent bytes. Fragment lengths and total I/O, CPU, latency, energy, peak charged capacity and deadline costs are **not** this objective. It is not arbitrary migration/reconfiguration or a scalable production scheduling algorithm.

The search is branch and bound with a fixed exploration budget. Independent per-task relaxed costs supply an optimistic bound; they ignore competing destinations and therefore cannot overstate the achievable minimum. Search completion proves the optimum within the stated assignment problem. Exhausting the budget returns UNKNOWN without an installable witness, even when a feasible incumbent exists. No automatic fallback is labelled optimal; operators can explicitly choose first-feasible planning for ordinary feasibility instead.

For accounting, initially pending allocations plus offline LIVE rows contribute one abandonment action each. Retaining a matching STAGED allocation removes its abandonment and adds one promotion, a net zero action increment; matching RESERVED adds one net action. FREE destinations add three actions, and RETIRED or repurposed pending destinations add four beyond already counted abandonment. Each destination requires one stage except matching STAGED work. The final independently replayed witness is checked against the computed score. The checker verifies safe executable restoration; it does not authenticate an externally supplied assertion of global optimality.

## Independent reference and coverage

`min_work_oracle` uses Dijkstra search over model transitions, with edge cost `(is_stage, 1)`. It imports no assignment objective increments or branch bounds. Its finite grammar allows abandoning initial pending work/offline LIVE rows, reclaiming, acquiring a slot once beyond its initial incarnation, staging and promoting. Newly promoted LIVE rows cannot migrate or retire. Its graph budget returns UNKNOWN. Oracle and assignment optimum claims retain their separate grammar qualifications.

The registered finite campaign covers 96 two-stripe 2+1 states varying eligibility, fallback availability, pending status, retired alternatives and failure; plus 40 single-stripe states covering both profiles. Objective and feasibility must agree with the graph oracle, and the minimum planner must not worsen the first-feasible objective. Shuffled input-order, exhausted-incumbent, unsafe-state and real-byte regressions supplement that matrix. Corrupt staging still rejects revision admission. No byte checks, fences, claims or worker barriers are removed.

## Real fixture and CLI

The interrupted fixture stages B on X after all parent reservations, then fails A's destination Z. A may use retired Y instead of consuming B's staged X; B also has free W. The 4+2 fixture includes two other matching reservations. The optimum retains X and reclaims Y, with failed Z still charged. Both profiles support ordinary and worker I/O and all four cache modes.

```powershell
python -m prism_c minimum-work-demo --root tmp/minimum-new --profile 4+2 --storage-workers --validation-mode shadow --report evidence/results/minimum-new.json
python -m prism_c replan --root <store> --plan <parent> --takeover --planner min-work --destinations Y:0 W:0 --report <proposal.json>
```

`replan` keeps its historical first-feasible default. `--planner min-work` is opt-in and emits the objective and solver status; `optimality_proven` is true only for a completed minimum-work search. UNKNOWN produces no witness and exit code 2. Use the existing saved-proposal `revise` and `resume` flow; authority admission rechecks current state and physical authenticity regardless of planning method.

## Fair comparison

The primary comparator is conventional cached **with minimum-work planning**. Selective mode receives identical minimum-work planning. First-feasible execution is a weaker diagnostic control, not the strongest baseline. A decrease relative to first-feasible demonstrates a planner fix, not an effect of component certificates. The [registered mechanism protocol](../experiments/minimum_work_protocol.md) records all variants and gates interpretation before collection.
