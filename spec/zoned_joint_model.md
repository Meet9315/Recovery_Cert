# R15: conventional joint zoned repair and reclamation

14 October 2026. Engineering continuation authorized by the user's instruction to complete the next steps after the R14 stop. This builds the previously missing **nominal finite model, joint conventional planner and independent reference**. It does not reopen the failed frontier invention, implement a durable device adapter or earn a patent score increase.

## Supported physical abstraction

Immutable objects, known 2+1 XOR / 4+2 P/Q profiles, aligned unit extents, one simulated authority and fixed simulated failure domains. At most n+1 working LIVE/STAGED/reserved copies per stripe. Each zone has a fixed capacity, append order, incarnation, external held tail units, one managed reservation, and phase EMPTY/OPEN/CLOSED/FULL/FINISHED/RESETTING. No individual allocated extent can be reused by retiring it.

Written extent count remains charged through retirement/discard. OPEN/CLOSED tails are appendable after subtracting held/reserved units. FINISHED strands its unwritten tail; the append pointer is effectively at the end, although the model retains the number of materialized extents separately. FULL and FINISHED consume no open/active tokens. OPEN consumes both; CLOSED consumes an active token. **RESETTING retains its prior open/active tokens until matching acknowledgement.** These are configured aggregate scope budgets, not a device capability query or per-device native compliance claim.

The [Zoned Storage overview](https://zonedstorage.io/docs/introduction/zoned-storage) documents append-only operations, reset, close/finish and resource limits. The [official NVM Express index](https://nvmexpress.org/specification/nvme-zoned-namespaces-zns-command-set-specification/) currently lists ZNS 1.5, ratified 31 July 2026. Our FINISHED/RESETTING labels record model provenance/pending accounting; they are not a literal native device-state enumeration or tested implementation of that specification.

All initial extent bytes are assumed authentic and of the declared immutable epoch. Metadata transitions model successful committed actions. No I/O failure during an action, uncertain append/finish, late worker execution, competing writers, controller takeover, HMAC receipts, fsync/power loss or distributed consensus is modeled. Pins, grants and external holds belong to other actors and remain fixed; the planner cannot silently clear them. A different fault/ownership contract requires another model.

## Actions

| Action | Effect and required guard |
|---|---|
| open | Acquire configured open/active tokens; require online EMPTY/CLOSED zone with usable tail. |
| close | Release open token; keep active token for nonempty zone. No managed reservation may be outstanding. |
| finish | Strand tail and release active token following modeled successful completion; forbidden with held/reserved tail. |
| reserve | Hold one actual tail unit for an eligible stripe/row; no duplicate working row in that zone; enforce copy/resource limits. |
| stage | Consume matching reservation and append authenticated row from a current LIVE decoding basis; no logical hole reuse. |
| promote | Adopt valid eligible staging as LIVE. |
| retire / discard | Mark LIVE / unadopted STAGED extent RETIRED only without pins/grants; all coding/fault floors still hold. Capacity remains written. |
| reset_request | Only all-retired/unreferenced/unheld zone; mark RESETTING without crediting tail or tokens. |
| reset_ack | Confirm the one pending reset for the current incarnation; clear allocated extents and advance incarnation. No duplicate/stale acknowledgement. |

Every prefix must have k distinct online LIVE rows per stripe. For `single_fault=True`, it must have k distinct rows after independently losing **each one online domain** as well. This checks a static protection floor, not eventual repair completion after a new failure during execution. 4+2 fixtures use that stronger floor; 2+1 fixtures begin with two LIVE rows and use only the no-additional-fault floor.

Terminal state requires all n distinct rows in n distinct eligible online domains, no extra LIVE copies, no unadopted staging/managed reservation/pending reset, and the requested appendable headroom in each named reclamation zone. Retired written extents may remain charged elsewhere.

## Conventional solver and exact objective

`conventional_zoned_plan` searches all supported joint transitions with A*. It minimizes **new stage units, then all action count**. With uniform 64-byte aligned rows in the campaign, one stage unit corresponds to 64 bytes written to the RAM byte store. Reads, coding CPU, journals, network, media erasures, alignment amplification and device costs are outside this objective. This is not the G6 performance metric.

The admissible lower bound counts rows absent from both online LIVE and STAGED extents. Already written staging does not require a new stage merely to be promoted. Any absent row requires at least one stage; migration/reset may add work, so ignoring that work is optimistic. Standard best-cost reopening handles graph states. Exhaustion returns UNKNOWN with no witness. FOUND occurs only when a goal is removed at its proven minimum lexicographic cost; complete frontier exhaustion yields INFEASIBLE only for this finite grammar.

State keys omit monotonically increasing incarnations to bound reset cycles. Incarnation renaming does not change legal future costs/eligibility; a more costly cycle cannot improve an optimum. Exact witness actions retain the actual incarnations and the complete initial fingerprint, and replay checks them. Reclamation goals concern appendable units rather than a particular generation number, so this quotient does not erase a goal-relevant fact. This does not apply to external opaque generation-sensitive actors; they are outside the contract.

The independent `zoned_oracle` uses uniform-cost search with separate transition, safety, terminal and state-key implementations. It imports shared immutable record types/code definitions, but calls no production transition, target or heuristic. `oracle_replay` derives allowable actions independently. This is independent algorithmic checking by this project, not independent external reproduction.

## Restricted separated control

The diagnostic control first performs GC while retaining every initially LIVE coding row, then repairs. It may promote/discard staging, reconstruct copies and reset whole zones, with the same physical budgets and coding floors. Its additional row-preservation/intermediate-goal restrictions can force extra writes; therefore it is **weaker than the primary joint conventional solver**. Savings against it are attributed to ordinary joint scheduling, not PRISM or a novel certificate. Retention-aware placement/native RetainZ are not executed here.

## Actual byte scope

The campaign replays distinct object payloads and real 64-byte codeword fragments in RAM. New staging reconstructs from current LIVE bytes; promotion checks the expected row; every action prefix returns exact original contents. 4+2 prefix recovery is also compared with the separate polynomial/cofactor coding oracle. Retired bytes persist in RAM until reset acknowledgement. These checks do not write a device/file or prove durability.

## Example

Victim A has LIVE row 0 plus a retired unit, and is full. Other source zones hold the remaining n−2 LIVE rows, pinned by external actors. X is full with an existing staged final row. No tail exists. Promote X, retire A's row 0 while keeping the declared floor, reset A with acknowledgement, then regenerate row 0 in one tail unit of A. All rows and one appendable unit are restored.

The separated row-preserving control instead needs room for a copy of old row 0. It can discard/reset X, write that copy, reclaim A and reconstruct the final row into A. That costs two new stages instead of one in this fixture. Added spare headroom can remove the difference. The joint conventional solver is the actual implementation of the better route; no claim of beating an equally capable joint baseline is made.
