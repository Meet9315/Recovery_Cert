# R15: conventional joint zoned repair and reclamation

14 October 2026. **Completed the nominal finite engineering model, joint conventional planner, independent reference and RAM byte comparison.** This follows the user's renewed instruction after R14. The earlier frontier gate remains failed; this is not a newly surviving invention.

Freeze: [`4a874b8d282345b81f32885fc03152feeb81be76`](https://github.com/Meet9315/Recovery_Cert/commit/4a874b8d282345b81f32885fc03152feeb81be76), before final collection. [Contract](../../spec/zoned_joint_model.md), [protocol](../../experiments/zoned_joint_protocol.md), [source context](ZONED_JOINT_SOURCE_SCREEN.md), [raw comparison](zoned-joint-r15.json).

## Outcome

| Result | Outcome |
|---|---:|
| Declared profile/staging/headroom/pin/eligibility cases | 32 |
| Feasible / infeasible / UNKNOWN in complete matrix | 12 / 20 / 0 |
| Feasibility/minimum-work disagreements with reference | 0 |
| Cases with fewer stages than restricted separated GC | 2 |
| Feasible cases with equal stage count to control | 10 |
| Exact RAM byte readbacks across joint/control prefixes | 280 |
| Separate zero/one-budget probes | Both solvers UNKNOWN, no witness |
| Full local regression verification | 186 methods / 452 subtests, PASS |

The joint A* solver agrees with the independent uniform-cost oracle on exact `(new stage units, action count)` in every declared case. Both witnesses are replayed through both interpreters. This proves the optimum **within the supported finite grammar**, not general distributed optimization or timing.

Each profile's tight-capacity/staged fixture uses **one stage/eight actions**, versus **two stages/fourteen actions** for the separated row-preserving control. Uniform 64-byte units give **64 versus 128 new bytes written in RAM**: 50% fewer stage bytes in those two fixtures. Other feasible cases do not reduce stage count, including cases with added spare headroom. No universal saving is claimed.

The control has additional GC-first row-preservation/intermediate-state restrictions. The equally capable conventional joint planner already achieves the better route. This gain belongs to **ordinary joint scheduling**; it does not establish a PRISM/certificate advantage, satisfy G6 CPU/restoration/foreground gates or increase readiness above **55/100**.

## Changes

- Append-only allocation, fixed capacity, held tail, managed reservation, open/active limits and finished-tail accounting.
- LIVE/STAGED/RETIRED extents, fixed external pins/grants and immutable coding identity.
- Promotion/retirement and whole-zone reset request/acknowledgement. Pending reset retains physical charge and prior resource tokens until acknowledgement.
- Joint reconstruction/relocation/retirement/reset planning with stage reuse and an admissible write bound.
- Independent transition/safety/target/search and replay without production transition/target/heuristic calls.
- RAM fragments/readback at every prefix, independent 4+2 reconstruction and distinct two-object payloads.
- Sixteen new methods covering the matrix, multi-stripe competition, holds/tokens, protection floors and stale guards.

```powershell
python -m prism_c.zoned_campaign --report evidence/results/zoned-joint-new.json
```

Use a fresh output path. Existing slot-store defaults/APIs are unchanged. These modules operate a model/RAM store, not the durable authority or a native zoned device.

## Verification and limits

[Full local verification](verification-r15.json) passes 186 methods/452 subtests with no failures/errors. Existing real process-exit regressions/finite campaigns remain included. Those physical tests concern the earlier slot store; no new zoned crash/power-loss guarantee follows. [Source CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38551920795) passes Ubuntu and Windows; [record](ci-r15.json).

Collection/verification hash 65 production/test files and preserve the protocol hash. Historical R14 data remains unchanged. Native placement, RetainZ/ZenFS execution, uncertain append/finish recovery, external concurrency, physical device durability and measured CPU/foreground performance remain outside this embodiment.

The previously missing R14-B/C concepts are delivered **in nominal engineering scope**: finite physical grammar, joint conventional baseline and independent oracle. R14's patent-directed stop is not retrospectively changed to PASS. No candidate-specific frontier/novel protocol was added.

The next engineering task is a separately specified durable zoned-file emulator with prepared append/reset intents, conservative uncertain-outcome accounting, actual byte files and process-exit tests: [next tasks](../../RCSD_PRISM_C_Next_Engineering_Tasks.md). Earlier slot-store guarantees do not transfer automatically. Hardware/external reproduction and human/priority facts remain unresolved.
