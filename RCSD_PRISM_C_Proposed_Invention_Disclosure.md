# RCSD-PRISM-C
## Reservation-Backed Continuation Witnesses for Capacity-Constrained Repair and Reclamation in Erasure-Coded Storage

**Document type:** Proposed invention disclosure, drafting source, research specification and implementation plan\
**Version:** 0.1 — 11 October 2026\
**Status:** PROPOSED DESIGN; not an implemented system, established novelty finding, filed patent or grant prediction\
**Intended filing context:** India; jurisdiction-specific review required\
**Inventors, applicant, ownership, priority and public disclosures:** TO BE CONFIRMED from actual contributions and records\
**Engineering name:** RCSD-PRISM-C; “C” denotes continuation. Naming does not establish novelty.\
**Basis:** RCSD-Place PDF, RCSD-PRISM-X enhanced disclosure, the accompanying patentability reviews, and the proposed capacity-constrained continuation pivot.

**Implementation amendment — 12 October 2026:** The original proposal below is retained as a dated research specification. A bounded local implementation now exists, including checked successor plans for interrupted recovery and a conventional partial-state replanner. The [implemented contract](spec/plan_revision.md), [milestone 11 evidence](evidence/results/MILESTONE_11.md) and [refreshed mechanism chart](evidence/results/REVISION_PRIOR_ART_REVIEW.md) define the narrower supported embodiment. Domains are simulated labels; workers are trusted local processes. All twelve matched work-retention pairs show conventional parity, so this amendment establishes neither a novel distinction nor the conditional 73/100 target.

**Planner extension — 13 October 2026:** [Minimum-work planning](spec/minimum_work.md) optimizes committed stage count, then action count, within the fixed-LIVE partial assignment problem. An independent graph oracle and 136-case matrix check its bounded objective. The [milestone 12 collection](evidence/results/MILESTONE_12.md) records fewer writes than first-feasible choices but identical work between minimum-work conventional and selective modes. This is a shared conventional improvement; it establishes no new inventive distinction or score increase.

**Contingency gate — 13 October 2026:** The [one-additional-failure finite model](spec/contingency_policy.md) checks every declared failure at every precompletion boundary, with independent coverage replay and feasibility reference. [Milestone 13](evidence/results/MILESTONE_13.md) records 16 feasible/56 infeasible configurations, 224 equal conventional alternatives and four equal existing-API byte/claim smoke pairs. A new authority-owned durable policy guarantee is not implemented; this gate finds no distinguishing effect and does not justify further durable integration or a score increase.

> **Executive decision:** Investigate a narrower technical mechanism that couples an executable repair continuation with enforceable capacity reservations, retained source fragments, manifest transitions and deletion authority. The candidate contribution is the specific interaction and its implementation, not safe scheduling, reservations, erasure coding or certificates individually. The earlier **53/100 subjective readiness assessment remains the assessed position**. **73/100 is only an illustrative evidence target**, not the rating of this proposal.

**Reassessment amendment — 13 October 2026:** The quoted executive decision and section 14 score table preserve the original proposal's historical assessment. The [current interim reassessment](evidence/results/PATENT_REASSESSMENT_2026_10_13.md) is now **55/100**: implementation/technical support rises, inventive-step support falls after the equal-baseline findings. No 70+ score is earned. The [next research plan](RCSD_PRISM_C_Redesign_Plan.md) investigates an incarnation-bound frontier for joint repair and whole-zone reset. It is a proposed physical-contract change requiring an exact mechanism/claim screen and equal conventional comparator; no zoned implementation or novel contribution is asserted by this amendment.

---

# 1. The invention in 60 seconds

A repair can be individually safe and still consume the only suitable capacity required to finish another repair. This matters when storage is nearly full, placement rules restrict destination choices, and repairs compete with migration and garbage collection. Checking the current fragment set alone does not establish that the remaining recovery work can complete.

RCSD-PRISM-C proposes a storage controller that constructs a bounded, executable **continuation witness**: a sequence of fragment staging, promotion and reclamation operations leading to a defined restoration target. Before admitting the sequence, the system backs its capacity assumptions with enforceable reservations and its source assumptions with retention pins. Each authoritative transition validates the relevant evidence and atomically advances both storage metadata and the continuation state.

The controller does not count logically deleted bytes as free physical space. Reusable capacity becomes available only after a generation-bound physical deletion acknowledgement. Competing operations cannot reuse reserved capacity or delete pinned fragments through another API.

The proposed result is a storage system that can make repair progress under constrained capacity while retaining a validated completion route under explicitly stated assumptions. Whether this is a non-obvious advance over existing resource-safety scheduling and transactional storage remains unproven.

**Technical problem:** How can concurrent erasure-coded repair and reclamation preserve an executable route to a specified protection target without overcommitting scarce destination capacity or reclaiming required source data?

**Intended technical effect:** Reduce repair stalls or temporary storage requirements relative to equally safe baseline controllers, while preserving declared recoverability and crash-consistency invariants.

# 2. Relationship to PRISM-X

| PRISM-X component | Role in this proposal |
|---|---|
| Positive and negative predicate witnesses | Validate competing reservations, source availability and relevant membership changes |
| Fragment stage receipt | Establish immutable staged identity and durability under the declared storage model |
| Ownership fence | Reject stale controller promotion and deletion requests |
| Manifest/debt transaction | Extended to consume reservations and advance the continuation cursor |
| Degraded-state progress checks | Retained as immediate safety checks; supplemented by completion feasibility |
| Selective invalidation | Applied to the remaining continuation and its resource dependencies |
| Bounded graph discovery | Optional planning accelerator; cannot turn incomplete evidence into permission |

This proposal adds removals, capacity dependencies and continuation obligations. It does not claim that merely adding valid coded fragments creates a novel survivability test: for fixed code and failure assumptions, adding valid independent information cannot reduce decoding rank.

# 3. Scope and assumptions

## 3.1 Minimum supported embodiment

- Immutable object-content versions using a fixed Reed–Solomon profile initially.
- A small protection group containing multiple stripes and their shared capacity accounts.
- One linearizable metadata transaction domain covering all admission-critical records of that group.
- Trusted storage agents that enforce reservations, retention pins, immutable identities and fences.
- Bounded planning horizon and an explicitly enumerated placement/failure policy.
- Crash/restart, duplicate delivery, stale controllers and message reordering.

Capacity shared with other groups must first be assigned to the group through an authoritative allocator. Local counters cannot reserve globally shared bytes independently. Cross-partition atomicity is outside the first embodiment.

## 3.2 Limits of the guarantee

The initial witness guarantees a feasible continuation for the validated state, assuming reserved resources remain available, protected inputs remain intact, storage agents obey the protocol and operations eventually receive service. It does not guarantee completion after arbitrary new failures or permanent network partitions.

A new failure invalidates affected evidence and triggers replanning. Immediate safety must still meet the separately stated fault model. A stronger claim of continued completion after any selected additional failure requires a contingency policy or branching witness, with resource feasibility verified for every supported branch; this is a separate research extension.

Byzantine storage, arbitrary hidden writes, compromised administrators and unbounded policy changes are excluded from the initial design.

# 4. Definitions and state

| Symbol/record | Meaning |
|---|---|
| `S` | Authoritative logical state plus acknowledged physical allocation state |
| `M` | Fragment manifests, indexed by immutable content version and stripe |
| `Q` | Per-domain physical capacity ledger |
| `R` | Durable capacity reservations and their ownership |
| `P` | Retention pins on exact fragment incarnations |
| `D` | Outstanding restoration obligations |
| `W` | Continuation witness and dependency coverage |
| `f` | Monotonically advancing controller fence |
| `content_version` | Identity of encoded object contents; separate from manifest revision |
| `manifest_revision` | Revision of placement/authority metadata |
| `storage_incarnation` | Identity preventing reuse of an old receipt after replacement or restart |
| `Target(S)` | Explicit terminal protection and placement conditions |

For each capacity domain, account separately for live bytes, staged bytes, retired-but-not-erased bytes, unmaterialized reserved bytes, and available bytes. These categories must not overlap. When a reservation is materialized as staged bytes, its accounting category changes without creating new free capacity.

A witness includes:

```text
plan_id, plan_revision, protection_group_id
owner_fence, content_versions, manifest_revisions
code_generation, policy_generation, checker_version
steps[], current_step, dependency_coverage
reservation_ids[], source_pin_ids[]
expected_capacity_revisions, predicate_index_incarnations
terminal_target, assumed_fault_model, witness_digest
```

Each step identifies its operation, exact inputs/outputs, capacity changes, source pins, preconditions, postconditions and successor dependencies. A digest binds the record; it does not prove correctness.

# 5. Formal admission conditions

Let a continuation be `pi = (a1, ..., at)` with checked states `S0, ..., St`.

Admission requires:

1. `S0` matches the authoritative snapshot and all dependency revisions.
2. Every action's preconditions hold in its preceding simulated state.
3. Every intermediate state satisfies the defined immediate safety predicate `Safe(Si)`.
4. Every intermediate state obeys physical capacity accounting, including staging and unacknowledged reclamation.
5. All external capacity assumptions are backed by reservations; required source identities are pinned.
6. The final state satisfies `Target(St)`.
7. The runtime can enforce every assumption used by the checker.

`Safe` and `Target` are different predicates. A degraded initial state may not meet the final protection target, while still satisfying minimum decoding, content integrity and permitted exposure requirements. The specification must say which temporary exposures are admissible.

For a fixed failure family `Fpolicy`, decoding can be checked using `rank(G(surviving fragments)) >= k` for the required scenarios. Rank checking itself is known. A non-regression condition may be imposed for allowed degraded transitions, but cannot silently require full terminal protection at every step.

Finding a feasible path is sufficient; finding an optimal path is not required. Search exhaustion means **UNKNOWN**, not impossible and not safe. A bounded exhaustive checker can validate a supplied plan independently of its planner.

# 6. Worked scheduling example

Consider two degraded stripes, A and B. Each needs one additional fragment to meet its terminal target. Each fragment occupies one unit. Suitable free capacity consists of:

| Destination domain | Free capacity | A eligible? | B eligible? |
|---|---:|---|---|
| X | 1 unit | Yes | Yes |
| Y | 1 unit | Yes | No |

Both stripes have sufficient valid sources to construct the missing fragment. Eligibility follows a fixed placement policy and current domain membership.

A greedy controller can put A's fragment in X. That repair improves A and is individually safe, but B cannot finish using the remaining eligible capacity. Finishing may require undoing or relocating A's work, or obtaining additional capacity.

A continuation-aware controller reserves Y for A and X for B, then performs both repairs. This illustrates why current-state safety differs from completion feasibility.

**This example is not evidence of novelty.** Matching, constraint scheduling and resource reservations can solve it. It is a minimum functional test. The research must demonstrate an additional benefit from the protocol's interaction with reclamation, crashes and concurrent storage mutations over a baseline that already makes this correct assignment.

A reclamation extension should include a retired fragment occupying a required destination. Its bytes must remain unavailable until deletion is acknowledged. Constructing and checking that full example is an implementation deliverable; no numerical result is claimed here.

# 7. Proposed protocol

## 7.1 Discover and plan

1. Read a consistent protection-group snapshot, including actual allocation categories.
2. Identify required terminal obligations and permitted intermediate states.
3. Generate a finite continuation using constraint search, scheduling or another replaceable planner.
4. Independently check each transition and the terminal state.
5. Collect complete dependency coverage, including negative predicates for competing reservations and deletion requests.

## 7.2 Acquire backing

Acquire group-owned capacity reservations and fragment retention pins through conditional authoritative updates. Revalidate after acquisition; the original planning snapshot may have become stale.

Reservations must constrain every participating allocator and storage writer. A metadata record ignored by direct writes provides no capacity guarantee. Initial implementation should acquire required external capacity as a bundle within the metadata domain, avoiding hold-and-wait cycles across independent plans.

Future capacity released by the plan is a dependency, not currently available space. Its allocation is enabled only after the predecessor reclamation acknowledgement.

## 7.3 Stage and verify

The agent consumes a matching reservation to write immutable bytes and issues a durable receipt bound to plan, fragment, content version, storage incarnation and allocation identity. Retention protects staged data until adoption or fenced cancellation.

## 7.4 Advance authority

```text
advance(plan_id, step_id, evidence):
    begin linearizable metadata transaction
    require active plan, expected revision and current owner fence
    require expected content, code and policy generations
    require complete and current dependency coverage
    require reservations, source pins and receipts match this step
    require independently checked transition and continuation validity
    require step has not already been applied
    apply manifest and restoration-obligation changes
    transfer capacity accounting without double counting
    advance continuation cursor and retention dependencies
    record operation result and any reclamation intent
    commit
```

The checker may reuse a previously validated suffix only if all inputs relevant to that suffix remain valid. Trusting a controller-supplied Boolean is not an independent check.

## 7.5 Reclaim physical space

Physical deletion is asynchronous and cannot be made atomic merely by putting an intent in a metadata transaction.

1. The transaction retires the exact fragment from authority and creates a generation-bound deletion intent after checking pins and continuation safety.
2. The storage agent checks the intent and enforced fence, deletes that exact incarnation, and durably acknowledges completion.
3. A metadata update records the acknowledgement and releases its occupied capacity.
4. Only then may a dependent allocation spend those bytes.

An authorized deletion must not race with repinning or reintroducing the same incarnation. Once retirement authorizes irreversible deletion, adoption requires a new identity and verified physical presence. Duplicate deletion messages are idempotent.

# 8. Concurrency, invalidation and recovery

| Event | Required response |
|---|---|
| Unrelated metadata update | Preserve evidence only when coverage establishes independence |
| Reserved destination fails | Invalidate affected continuation; stop dependent destructive steps and replan |
| Source fragment fails | Revalidate decoding and all steps using that source |
| Controller crashes | Retain durable plan, pins, reservations and operation results; fenced successor resumes |
| Staging completes after cancellation | Reject promotion; reconcile orphan bytes before freeing their accounting |
| Delete acknowledgement is lost | Retry/reconcile; do not assume capacity is free |
| Policy or code generation changes | Revalidate affected obligations; do not reinterpret old witness silently |
| Index rebuild or counter reset | Change incarnation; reject old coverage witnesses |
| Reservation cancellation/expiry | Invalidate dependencies before capacity reassignment; never rely on wall-clock expiry alone |
| Planning budget exhausted | Return UNKNOWN; retain safe state or use an equally safe fallback |

Fallback must acquire the same authoritative ownership and honour outstanding pins, reservations and deletion intents. A native controller that bypasses these records breaks the guarantee.

Liveness additionally requires fair scheduling, eventual communication and an attainable target. Capacity safety does not itself prevent starvation. Admission should cap plan size and reservation duration using fenced cancellation and reconciliation rather than unsafe lease expiry.

# 9. Candidate inventive interaction

The proposed investigation centres on all of the following acting together:

1. A storage-specific continuation whose intermediate states include actual staging and reclamation accounting.
2. Enforceable reservations and source pins backing the continuation's assumptions.
3. Manifest promotion or retirement coupled atomically to continuation advancement and resource ownership changes.
4. Physical reclamation acknowledgements controlling when future capacity becomes spendable.
5. Dependency-specific invalidation of the remaining witness under concurrent changes.

These are **candidate claim features**, not a finding that their combination is new or inventive. If an ordinary resource-safety planner with transactional reservations achieves the same behaviour and cost, the proposal may be an obvious implementation rather than a patentable advance.

# 10. Prior-art comparison and search agenda

| Source | Relevant known subject matter | Required distinction to investigate |
|---|---|---|
| [US20170160982A1](https://patents.google.com/patent/US20170160982A1/en), published 8 June 2017 | Space reservation for distributed storage transfers, including erasure-coded repair and competing transfers | A reservation alone cannot be the inventive centre |
| [ARES, 2018](https://arxiv.org/abs/1805.03727) | Reconfigurable erasure-coded atomic storage | Identify what the continuation/reclamation interaction adds beyond safe reconfiguration |
| [FastPR, 2022](https://ieeexplore.ieee.org/document/9721141/) | Coupled migration/reconstruction scheduling for proactive repair | Compare against capable repair scheduling, not naive orderings |
| [US20180121286A1](https://patents.google.com/patent/US20180121286A1) | Coding-matrix decomposition, repair feasibility and reused calculations | Do not claim rank or memoization as new |
| [US7979771B2](https://patents.google.com/patent/US7979771B2/en) | Erasure-coded storage migration and delayed old-copy removal during authority transfer | Copy-before-delete or authority transfer alone is insufficient |
| [FoundationDB, SIGMOD 2021](https://www.foundationdb.org/files/fdb-paper.pdf) | Serializable transactional metadata and conflict checking | Explain why ordinary transactions do not already supply the asserted advance |

The comparison is preliminary, not an exhaustive claim chart or family/status search. Publication dates must be compared against the actual supported priority date, which is unknown.

Further search must cover Banker's algorithm and resource-safe scheduling; deadlock-free storage migration; garbage-collection barriers; reference counting and retention pins; proof-carrying storage operations; crash-consistent reclamation; capacity-constrained reconfiguration; and all relevant patent families. Search combinations and claim language, not only the proposed product name.

# 11. Illustrative claim directions

**Not filing-ready claims.** Scope must follow the implemented mechanism, actual inventor contributions, prior-art search and professional drafting.

## 11.1 Method claim skeleton

A method of controlling erasure-coded storage comprising: obtaining authoritative fragment and physical-allocation state; validating a continuation of storage transitions to a specified protection target; backing identified resource and source dependencies with enforced reservations and retention records; conditionally committing a manifest transition together with advancement of the continuation and corresponding resource records; issuing an identity-bound physical reclamation intent when permitted by the validated continuation; and making reclaimed capacity allocatable only following acknowledgement of physical reclamation.

## 11.2 Possible dependent limitations

- Accounting for retired-but-not-erased fragments separately from available capacity.
- Binding receipts and deletion intents to immutable content and storage incarnations.
- Preventing competing continuations from consuming identical capacity allocations.
- Invalidating only suffix obligations covered by a changed dependency.
- Recovering the cursor, resource ownership and deletion state after fenced controller takeover.
- Rejecting admission when dependency coverage is incomplete.

System claims should preserve the actual distinguishing interaction rather than omit it and become generic processor/storage claims. No broad monopoly over recovery certificates, safe repairs or erasure coding is proposed.

# 12. Implementation plan and decision gates

| Phase | Indicative effort | Deliverable and gate |
|---|---|---|
| 1. Formal specification | 1–2 weeks | State machine, immediate/terminal safety predicates, allocation equations, explicit fault assumptions |
| 2. Strong baseline and examples | 2 weeks | Transactional reservations plus competent resource-safety scheduler; reproduce constrained-capacity traces |
| 3. Planner and independent checker | 2–3 weeks | Finite witness format, exhaustive small-state oracle, rejection of malformed witnesses |
| 4. Storage enforcement | 3–4 weeks | Real stage/promote/retire/delete interfaces, immutable identities, pins, durable receipts and acknowledgement ledger |
| 5. Recovery and concurrency | 2–3 weeks | Crash injection, duplicate messages, takeover, cancellation and reconciliation |
| 6. Comparative evaluation | 2 weeks | Reproducible traces and equally safe baseline comparisons |
| 7. Patent drafting decision | After evidence | Claim chart, inventorship/priority records and professionally reviewed disclosure |

Estimates assume access to a modifiable storage implementation and are planning assumptions, not delivery commitments. A simulator alone cannot demonstrate actual storage enforcement.

# 13. Validation requirements

## 13.1 Correctness

- Check all reachable states of a deliberately small model, reporting its exact bounds.
- Assert no overcommitment, double allocation, deletion of pinned data or stale-owner authority.
- Distinguish logical retirement from completed physical deletion in every crash window.
- Check that every admitted witness reaches its target in the model when its assumptions remain satisfied and execution is fair.
- Inject destination loss, source loss and policy changes; verify invalidation precedes dependent destructive operations.
- Validate negative-predicate coverage under concurrent reservation creation and index rebuild.

Passing finite tests is evidence, not an unbounded proof. Any formal proof must state its model assumptions and relationship to implementation.

## 13.2 Baselines

1. Conservative serial repair with safe staging and reclamation.
2. Transactional reservations with a competent capacity-aware scheduler.
3. The same continuation planner with full revalidation instead of selective reuse.
4. A small-state optimal/exhaustive scheduler for measuring planner quality.

All baselines use the same protection policy, resource budget and authoritative interfaces. Disabling safety in a baseline is not an acceptable performance comparison.

## 13.3 Measurements

Measure time to restoration, repair completion rate, peak temporary bytes, unusable reserved capacity, bytes recopied after replanning, verification CPU, metadata conflicts, p95/p99 foreground latency and reconciliation time after crash. Sweep capacity pressure, destination eligibility overlap, concurrent plan count and failure rates.

No performance gains are claimed. Set acceptance thresholds before evaluation and publish negative results. A benefit that vanishes against the competent baseline does not support the proposed inventive interaction.

# 14. Indian patentability and illustrative score

India requires novelty, inventive step and industrial applicability; computer-related subject matter also requires consideration of statutory exclusions. Physical storage interaction should be explained through concrete technical operation and effects, not merely by adding hardware nouns. See the [Indian Patent Office basics](https://ipindia.gov.in/basics-of-patents) and [official guidelines index](https://ipindia.gov.in/resource/patents-resources-guidelines).

The following is a subjective research/readiness rubric, **not a legal test or probability of grant**:

| Criterion | Earlier PRISM-X assessment | Illustrative evidence target |
|---|---:|---:|
| Novelty | 11/25 | 17/25 |
| Inventive step | 7/25 | 15/25 |
| Technical character | 16/20 | 17/20 |
| Disclosure sufficiency | 10/15 | 12/15 |
| Industrial applicability | 5/5 | 5/5 |
| Claim quality | 3/5 | 4/5 |
| Priority/disclosure position | 1/5 | 3/5 |
| **Total** | **53/100** | **73/100, conditional only** |

The target requires a defensible claim distinction, a credible non-obvious technical interaction, enabled implementation details, meaningful comparative evidence and resolved priority/disclosure records. This document by itself satisfies none of the empirical gates and does not raise the assessed score to 73.

Novelty and inventive step cannot be compensated for simply by accumulating points in other rows. Experimental success also cannot restore novelty lost through earlier disclosure.

# 15. Inventorship, records and open questions

Record actual human contributions to the eventual claimed subject matter and obtain professional advice on inventorship and entitlement. Do not infer inventorship from document authorship, project membership or an AI-generated suggestion.

Before filing, resolve:

1. Has any version been published, demonstrated publicly, placed on GitHub, submitted to a journal or shared without confidentiality? Record exact dates and contents.
2. Does an earlier application exist, and does it actually support this new subject matter?
3. Which storage platform supplies enforceable allocation, pinning and deletion hooks?
4. What exact capacity domain fits within one authoritative transaction boundary?
5. What is the supported failure family, and when is replanning permitted?
6. What technical advantage survives comparison with a resource-safety scheduler and transactional reservations?
7. Which mechanism is genuinely contributed by the human inventors and supported in sufficient detail?

# 16. Decision criteria

**Proceed** if a concrete implementation reveals a defensible protocol distinction, demonstrates its technical effect and survives a broader prior-art analysis.

**Narrow** if the evidence supports only a specific reclamation-accounting or witness-invalidation mechanism.

**Stop or pivot** if the design is adequately explained by standard scheduling, reservations and transactions, or if its claimed advantages depend on an unsafe baseline.

**Present conclusion:** This is a proposed research direction with a conditional path toward stronger filing readiness. It is not a validated 70-plus patent candidate.
