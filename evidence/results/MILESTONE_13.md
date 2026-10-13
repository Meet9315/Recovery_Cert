# Milestone 13 — one-additional-failure feasibility gate

13 October 2026. The requested finite gate is implemented and its collection is complete. **Sixteen of 72 configurations support the declared additional-failure guarantee; 56 reject.** The independent feasibility game agrees. **All 224 cached alternatives and all four real-store pairs show conventional parity.** No distinguishing advantage or new rating is established, so a new durable policy-admission layer and a large timing campaign are gated out.

## Supported guarantee

Before admitting a degraded repair, check restoration after one failure from a declared set of online scoped domains at every committed action boundary before nominal completion, including boundary zero. There is at most one such event. All modeled resources remain owned, sources remain authenticated/pinned, policy and membership remain fixed and healthy storage eventually serves operations. With no failure, the nominal route restores the target. Root-terminal failures, a second fault, in-flight physical I/O failures, hidden corruption, remote/device failures and power loss are outside this gate.

The registered model is a 4+2 stripe with four or five initially LIVE rows and 0/1/2 spare slots in each of X/Y, independently, initially FREE or RETIRED. Failure scope is either D0 alone or every online scoped domain. Five live rows preserve four after losing one source. Two distinct spare domains then allow restoring all six rows. Four initial rows fail the source-fault guarantee at boundary zero; two spare slots co-located in X do not substitute for two distinct eligible domains. This is a stronger admission condition than ordinary current-state repair feasibility.

## Implementation and independent reference

- Finite nominal search permits progress only from states whose every declared failure has a checked exact fallback. A result is a feasible robust route, not a global minimum robust allocation/work optimum.
- `ContingencyPolicy` serializes the initial fingerprint, failure set, nominal witness, every cursor/domain branch and a digest. The digest is not an authority signature or physical-byte proof.
- Independent `check_policy` imports neither optimizer calls nor planner transitions. It derives complete coverage and checks immediate post-fault decoding safety, exact witness bindings, the finite nonmigration grammar, full targets and no unowned partial leftovers.
- Independent `contingency_oracle` uses checker replay for nominal exploration and exhaustive assignment permutations for fault completion feasibility. It shares no objective increments or optimizer pruning.
- Separate nominal, branch and coverage budgets fail closed. Three deliberately exhausted probes return UNKNOWN with no policy; they are retained separately from the complete matrix.
- Conventional cached alternatives receive the same nominal schedule, scope, failures, minimum-work planner and full snapshot guard. Both representations perform zero planning calls during branch selection.

See the [full contract](../../spec/contingency_policy.md) for grammar and the distinction between client-held proof assumptions and a new authority-owned durable admission guarantee.

## Registered evidence

Implementation/protocol freeze: `f42f1d62e0c78eae05ed1de7656b1f519febf766`. The [protocol](../../experiments/contingency_protocol.md) precedes collection. [Raw gate evidence](contingency-gate-milestone-13.json) preserves all 72 cases, positive policies/witnesses, negative cases, independent statuses, all 224 branch comparisons, budget probes, eight smoke-store events/ledgers, source hashes and protocol/runner hashes.

| Matrix outcome | Count | Interpretation |
|---|---:|---|
| Feasible | 16 | Five LIVE rows and at least one slot in each distinct spare domain X/Y; both failure scopes and both spare statuses |
| Infeasible | 56 | Includes insufficient immediate redundancy, capacity and distinct-domain placement |
| UNKNOWN in the registered matrix | 0 | All registered finite cases settled within budgets |
| Deliberate UNKNOWN budget probes | 3 | Nominal exploration, branch optimization and coverage budgets; no policy admitted |
| Cached branch comparisons | 224 | Exact witness/terminal/work equality with the conventional table |

The ordinary FREE-spare example repairs one missing row in three nominal actions: reserve X, stage X, promote X. It checks seven fault domains at cursors 0/1/2, yielding **21 branches**. RETIRED-spare roots require reclamation and have four nominal boundaries; larger slot counts supply more capacity but do not remove the distinct-domain requirement. No postcompletion event is counted as covered after claims release.

## Actual-byte and ownership smoke evidence

Four matched pairs cover local/workers × source D0/staged destination X, each event at cursor 2 after acknowledged staging and before promotion. Conventional cached selects an ordinary precomputed alternative; selective selects the checked policy branch. Both use existing `admit_scoped`, `revise` and `execute`; no new storage mutation or receipt authority is introduced.

All eight stores reject an unrelated foreground plan that tries to claim the held unused Y spare, restore exact A/foreground bytes, reach the whole-store target and leave no active plans. Every tested failed allocated extent remains **1024 bytes RETIRED**. Source D0 failure leaves four authentic LIVE rows immediately; its branch retains staged X and repairs the lost row on Y. X failure abandons its failed staged allocation and repairs the missing row on Y. Both selector representations use zero online replanning and produce identical witnesses, work, failed snapshots and final ledgers.

The [separate shadow/worker demonstration](contingency-demo-milestone-13.json) independently records source D0 failure, 21 covered branches, exact bytes, held-spare rejection and successful restoration. These are guarded existing-API smoke cases, not fault-at-every-boundary physical device or process-exit tests. Policy bundles are not persistently admitted/enforced by the authority; no restart/in-flight guarantee is asserted for them.

## Verification and decision

Eight new focused test methods passed before freeze. Tests cover policy serialization, independently derived coverage, seven tamper cases, immediate-rank/co-location rejection, budget UNKNOWN, no replanning during selection, stale/second/late/unknown fault rejection, the full matrix and eight actual-byte/controller/path cells.

[Full verification](verification-milestone-13.json) passed **158 methods / 403 subtests**, zero failures/errors, including the retained **57 actual process-exit regression cases**. This gate introduces no new process-exit fault claim. The legacy 10,000-trace campaign retains 2479 initial configurations, 3772 states, 46282 transitions/cache-reference comparisons and 92564 malformed-generation checks, zero violations. The independent coding campaign checks 65536 field products, 15 generator minors, 180 reconstructions, 720 finite cases, 840 cache/reference and 840 stale-generation checks, zero disagreement. The 40-case partial and 136-case minimum-work matrices pass; the new 72-case contingency campaign repeats the 16/56 outcome and 224 equal alternatives, with separate UNKNOWN budget probes retained.

All **59 production/test hashes** match frozen collection, demonstration, verification and current files. [Source CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38419584731) passed **Ubuntu and Windows**, with [saved conclusions](ci-milestone-13.json) binding both jobs to `f42f1d62e0c78eae05ed1de7656b1f519febf766`. CI runs correctness/process regressions, 1000 legacy traces and the coding/planner/contingency campaigns; it does not repeat the manual gate's eight-store collection. These finite/local results are not all concurrent histories or hardware-fault proofs.

The [primary-source screen](CONTINGENCY_PRIOR_ART_REVIEW.md) documents related verifiable resource plans, fault-tolerant reconfiguration and recovery reservations, with abstract/full-text limitations kept explicit. It does not settle every exact claim's novelty or inventive step.

**Gate decision:** the bounded recovery property is feasible under the stated assumptions, but ordinary cached alternatives provide the same capability. Reject this representation as the missing comparative contribution for these cases. The 20% verification-CPU, 10% restoration/space and 5% foreground targets remain unpassed; no timings were collected. **53/100 is unchanged, and 73/100 remains conditional.** The requested finite feasibility/comparison deliverable is complete; further durable integration is gated out by the negative distinguishing-effect result.

## Reproduce

```powershell
python -m prism_c verify --report evidence/results/verification-contingency-new.json --traces 10000 --seed 20261011
python -m prism_c contingency-gate --report evidence/results/contingency-gate-new.json
python -m prism_c contingency-demo --root tmp/contingency-new --report evidence/results/contingency-demo-new.json --storage-workers --validation-mode shadow --fault-domain D0 --cursor 2
```

Use fresh store/report names to preserve all existing evidence.
