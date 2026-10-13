# RCSD-PRISM-C: Execution Plan for the Conditional 70+ Readiness Target

**Version:** 1.0 — 11 October 2026\
**Basis:** [Proposed invention disclosure](RCSD_PRISM_C_Proposed_Invention_Disclosure.md)\
**Objective:** Produce sufficient technical, prior-art and disclosure evidence to reassess the proposed invention against the illustrative 73/100 readiness target.\
**Current evidence:** Design documents and preliminary research; no integrated PRISM-C implementation or measured results.\
**Score status:** 53/100 is the earlier PRISM-X assessment. PRISM-C has not earned a new assessed score. 73/100 remains a conditional planning target, not a predicted probability of patent grant.

**Execution amendment — 12 October 2026:** This document retains its original planning baseline. Current implementation and completed experiments are tracked in [PROGRESS.md](PROGRESS.md). Interrupted-plan revision, equal conventional partial-state capabilities, real retained-byte enforcement, race/crash checks and an untimed matched comparison are implemented in milestone 11. All twelve pairs have equal retained work, so that hypothesis fails the mechanism-difference gate for these fixtures. Its larger timing confirmation is gated out, rather than counted as complete or successful. The remaining research plan, primary claim distinction, hardware evidence and human contribution/disclosure/priority records remain unresolved.

## 1. What successful execution must establish

The project must answer three questions with reproducible evidence:

1. **What exact mechanism differs from known work?** A specific interaction between continuation validation, capacity ownership, storage reclamation and authoritative updates must survive an adversarial prior-art comparison.
2. **Does that mechanism work?** The implemented storage interfaces must enforce the assumptions used by the checker, including crashes, concurrent plans and delayed physical reclamation.
3. **Why is it technically useful?** A controlled comparison must show an attributable advantage over a competent, equally safe controller using transactional reservations and resource-aware scheduling.

Successful performance alone does not establish novelty or inventive step. An implemented known technique can still fail the patentability gates. Likewise, a score total cannot compensate for a fatal novelty, eligibility, entitlement or disclosure problem.

The research plan is deliberately falsifiable. A legitimate outcome is a narrower invention, a lower reassessment or stopping this patent direction.

## 2. Planning assumptions and roles

**Schedule:** 16 research/development weeks from actual project start, assuming approximately 30–40 focused engineering hours per week, access to a modifiable storage prototype and periodic technical review. Allow a further 2–4 weeks of contingency for failed gates or storage integration. This is an estimate, not a commitment; a part-time project will take longer.

**Roles:** An implementation lead owns the code and traces; a technical reviewer checks invariants, baselines and interpretation; an Indian registered patent agent or appropriately qualified patent professional reviews claims, disclosures, entitlement and filing strategy. One person can perform several engineering roles, but an independent review is valuable for final evidence. No agents have been engaged by this document.

**Resources:** Start the finite model on the existing workstation. Use isolated worker processes and a metadata service for integration. Obtain separate storage failure domains for claims requiring actual host/device fault evidence. A rack label on a single computer is a simulated rack, not physical rack-failure validation. Determine hardware and professional-service costs after the first gate; no cost estimate is invented here.

## 3. Two concurrent tracks

| Period | Technical track | Patent/disclosure track | Decision |
|---|---|---|---|
| Days 1–3 | Freeze problem, assumptions and acceptance criteria | Inventory contributions, disclosures and earlier filings; consult on filing urgency | Can the project proceed with a clear priority/disclosure position? |
| Weeks 1–2 | Specify state machine and construct counterexamples | Claim-element search and combination analysis | **G1:** Is there a plausible specific distinction worth building? |
| Weeks 3–4 | Small-state model and strong baselines | Update claim hypothesis with model findings | **G2:** Does a meaningful technical problem remain against the strong baseline? |
| Weeks 5–6 | Planner, independent checker and dependency coverage | Map proposed claim elements to precise technical definitions | **G3:** Is continuation admission correct within declared model bounds? |
| Weeks 7–9 | Real storage enforcement and durable metadata | Review enablement and supported embodiment scope | **G4:** Do real interfaces enforce every assumption? |
| Weeks 10–11 | Crash recovery, cancellation and concurrency | Check whether recovery details create or narrow the contribution | **G5:** Do recovery and reclamation invariants hold? |
| Weeks 12–13 | Comparative experiments and ablations | Refresh prior-art search using final terminology | **G6:** Is there an attributable benefit against an equally safe baseline? |
| Weeks 14–16 | Reproduction, reviewer audit and evidence freeze | Final claim chart, disclosure update and filing review | **G7:** Reassess readiness from evidence; proceed, narrow or stop |

**Filing timing is independent of this schedule.** Do not treat week 16 as the required filing date. A patent professional should assess timing at project start and again when a sufficiently supported new mechanism emerges. This plan does not impose a working prototype or benchmark result as a universal legal prerequisite to filing. The complete specification must adequately describe the invention and its operation; priority depends on support for the claimed subject matter. See [Section 10](https://ipindia.gov.in/acts/patent-act-1970/section-10) and [Section 11](https://ipindia.gov.in/acts/patent-act-1970/section-11).

## 4. Days 1–3: Establish the evidence baseline

### Tasks

- Save dated copies of the original PDF, PRISM-X disclosure and PRISM-C proposal.
- Create a contribution log: person, date, technical contribution, supporting notebook/code/document and proposed claim relationship.
- Create a disclosure log: public repositories, papers, submissions, demonstrations, presentations and sharing conditions, with exact dates and contents. Mark unknowns as unknown.
- Record any earlier application number, specification and claim support. An earlier project name does not establish priority for new continuation/reclamation subject matter.
- Write a one-page problem statement and freeze the minimum supported fault model.
- Pre-register the experiment questions and acceptance thresholds described below.

### Deliverables

`evidence/records/contributions.md`, `evidence/records/disclosures.md`, `evidence/records/priority_support.md`, `spec/problem_statement.md`, `experiments/protocol.md`.

**Gate G0:** Facts are documented or explicitly unresolved, and the responsible professional has enough information to assess filing urgency. Research on unaffected technical issues may continue while records are resolved. Unresolved facts cannot earn priority/disclosure points.

## 5. Weeks 1–2: Search the claimed interaction before investing heavily

### 5.1 Freeze a claim hypothesis

Use a concrete mechanism rather than the aspiration “preserve a safe route”:

> A checked repair/reclamation continuation is backed by enforceable capacity and source ownership; each authoritative transition advances that continuation with the resource records; future reclaimed capacity becomes allocatable only after an identity-bound storage acknowledgement; changed dependencies determine which remaining evidence must be rechecked.

Prepare a feature table with a definition, enforcement point and intended technical effect for every element. Distinguish ordinary implementation components from the proposed interaction.

### 5.2 Search and chart

Review these starting references in full where relevant; they are leads, not a completed search:

| Starting source | Search/comparison purpose |
|---|---|
| [US20170160982A1](https://patents.google.com/patent/US20170160982A1/en) | Storage reservations for competing transfers and erasure-coded repair |
| [ARES](https://arxiv.org/abs/1805.03727) | Atomic, reconfigurable erasure-coded storage |
| [FastPR](https://ieeexplore.ieee.org/document/9721141/) | Migration and reconstruction scheduling |
| [US20180121286A1](https://patents.google.com/patent/US20180121286A1) | Rank-based repair feasibility and reused computations |
| [US7979771B2](https://patents.google.com/patent/US7979771B2/en) | Fragment migration, authority transfer and retention of old copies |
| [FoundationDB paper](https://www.foundationdb.org/files/fdb-paper.pdf) | Existing transactional metadata capabilities |

Search additional work on Banker's algorithm, resource-safe scheduling, crash-consistent reclamation, garbage-collection barriers, storage admission control, durable allocation, pins and proof-carrying operations. Follow backward/forward citations and patent families; examine relevant Indian counterparts and publication dates. Search claims as well as abstracts. Record query, database, date, document, passages and conclusions.

For novelty, compare the complete proposed claim against each relevant single disclosure. For inventive step, separately assess why a skilled person would combine the known features and whether the interaction yields more than their expected operation. A blank cell in a search chart is an unresolved finding, not proof of novelty. Keep patentability research separate from any freedom-to-operate assessment.

### Deliverables and gate

`evidence/prior_art/search_log.md`, `evidence/prior_art/claim_chart.md`, `evidence/prior_art/combination_analysis.md`, `spec/claim_hypothesis.md`.

**G1 pass:** At least one precisely defined interaction remains plausibly distinguishable after review, with a testable technical effect and an honest account of the strongest obviousness objection.

**G1 fail:** The contribution reduces to reservations, a safe sequence search and routine atomic metadata updates already taught or predictably combined. Narrow to a supported mechanism or stop this patent direction. Do not increase the score because many sources were searched.

## 6. Weeks 1–4: Formal specification and decisive examples

### 6.1 Define the state machine

Specify immutable content identity separately from manifest revision. Define live, staged, retired-but-not-reusable, reserved-but-unmaterialized and available capacity as disjoint categories. Define each action's preconditions, durable writes, linearization point, postconditions and crash recovery.

For an online managed capacity pool:

```text
live + staged + retired_not_reusable + reserved_unmaterialized + available
    = managed_allocatable_capacity
```

System overhead is excluded or separately budgeted. Failed/offline pools have a separate state; do not silently count their space as available. Orphaned allocations remain charged until reconciliation. Materializing a reservation moves bytes between categories instead of double charging them.

Define `Safe(S)` separately from `Target(S)`. The MVP permits a degraded initial state with a specified minimum safety floor and seeks full target restoration. For the successful-continuation statement, assume no new loss of the protected inputs or reserved destinations, eventual communication, fair scheduling and achievable target. Additional faults trigger invalidation and safe replanning; completion after arbitrary additional failures is outside the claim.

**Physical reclamation definition:** A successful filesystem delete or unlink alone may not establish reusable space, for example when open handles or a storage allocator retain the extent. Define the acknowledgement at the allocator that actually grants capacity. Prefer a controlled extent/slot pool for the prototype and bind acknowledgement to a unique allocation generation. Sanitization of old data is a separate issue and is not implied by “reclaimed.”

### 6.2 Model bounds

Begin with an exhaustive model of two stripes, an MDS 2-of-3 code, four simulated placement domains, integer capacity units and two controllers. Expand to three stripes only when state-space measurements support it. Use a separate larger 4+2 workload later. Publish bounds, explored states, transitions, symmetries, cutoffs and any incompleteness.

The model checker and witness checker should not merely call the same planner and trust its result. Use an independent small-state exploration or reference transition implementation to catch shared mistakes.

### 6.3 Required scenarios

| Scenario | Question and evidence |
|---|---|
| A can use X/Y; B can use only X | Baseline sanity: both competent schedulers must choose a feasible assignment |
| Required destination contains retired data | No allocation before acknowledged reclamation; show allocation/deletion trace |
| Two continuations share sources and destinations | Reservations cannot double spend; pins cannot be bypassed |
| Crash after retirement but before acknowledgement | Recovery preserves occupied accounting and prevents premature reuse |
| Late stage/delete message after owner takeover | Exact generation and fence prevent stale mutation |
| Change unrelated to a plan suffix | Selective reuse agrees with complete revalidation |
| New failure invalidates a reserved destination | Destructive dependent steps stop; safety preserved; completion is not promised |
| No feasible route or exhausted search budget | Distinguish proved infeasibility within complete bounds from UNKNOWN |

Produce at least one reclamation/concurrency example beyond the simple X/Y matching case. A well-designed conventional baseline may handle every case safely; the remaining research question is an attributable efficiency or concurrency advantage.

### G2

Deliver `spec/state_machine.md`, `spec/invariants.md`, `model/`, `evidence/model/counterexamples.md` and baseline traces. **Pass** only if a specific unresolved engineering problem or measurable opportunity remains against the strong baseline. If only an intentionally greedy controller fails, the inventive-step evidence is insufficient.

## 7. Weeks 3–6: Baselines, planner and checker

### Baselines to implement first

| Baseline | Required capabilities |
|---|---|
| B0: conservative serial controller | Durable staging, safe deletion, fencing and correct capacity accounting |
| B1: competent conventional controller | Capacity-aware safe sequence planning, transactional reservations, source protection and crash recovery |
| B2: full revalidation variant | Same planner and enforcement as PRISM-C; rechecks the remaining continuation completely |
| O: exhaustive small-state oracle | Finds feasible completions in declared finite bounds; detects missed opportunities |

B1 must include reasonable caching and dependency tracking where conventional implementation permits it. Do not deny it a standard optimization merely to create an advantage. B2 isolates selective validation; beating B2 alone establishes an optimization effect, not a novelty finding.

### Implementation units

- Pure state transitions and failure-policy evaluation.
- Replaceable bounded planner; exact search in small cases, budgeted search for larger ones.
- Witness serializer with versioned fields and canonical identities.
- Independent witness checker for every simulated intermediate state and terminal target.
- Dependency map covering capacity, source identity, policy, code generation, reservations and absence predicates.
- Authoritative revision/index incarnation updates intercepted by every relevant writer.

### G3

Every admitted model continuation obeys invariants and reaches the target when its assumptions remain true and execution is fair, within the explored bounds. Deliberately malformed witnesses must be rejected: omitted dependency, stale revision, double reservation, fictitious reclamation acknowledgement, changed source, false terminal state and duplicate step.

Search budget expiration returns UNKNOWN. State pruning may reduce planning effort only if validated against the oracle or accompanied by a stated soundness argument. Never loosen safety to keep the benchmark fast.

## 8. Weeks 7–9: Build actual storage enforcement

Use real immutable fragment bytes and checksum/content identities, not only simulated metadata. Start with a tested erasure-code implementation, one durable metadata authority and multiple storage-agent processes. Choose the concrete transactional backend after the model is stable and verify its durable conditional-update semantics from official documentation before adoption.

Suggested module boundaries, not existing code:

```text
spec/                    State machine and fault model
model/                   Finite reference model and oracle
src/planner/             Continuation construction
src/checker/             Independent continuation validation
src/metadata/            Authority, revisions, manifests, ownership and ledger
src/storage_agent/       Allocate, stage, retain, retire and reclaim
src/recovery/            Takeover, cancellation and reconciliation
tests/scenarios/         Saved traces and fault campaigns
experiments/             Baselines, workloads and measurement protocol
evidence/                Results, claim support and review records
```

Required agent interfaces: reserve-backed allocation, durable staging receipt, promotion, retention pin, retirement/deletion intent, allocator reclamation acknowledgement and reconciliation. Receipts bind exact fragment/allocation identity, content version and storage incarnation. The metadata authority enforces plan revision and current fence. Storage mutation commands validate the authoritative authorization under a documented race-safe protocol; a stale cached fence is insufficient.

Create one integration test for every possible bypass: direct allocation, native repair, cleanup, garbage collection, cancellation and old-controller RPCs. Either route it through the protocol or make it unavailable in the supported deployment.

**G4 pass:** Real writes and reclamation obey the ledger across process restarts, and unsupported bypass paths are identified. If the prototype is an observer around an existing object API, it cannot support a claim of controlling physical allocation and deletion. A single-host demonstration supports process-crash evidence only; expand deployment before claiming independent device/host failure validation.

## 9. Weeks 10–11: Crash and concurrency campaign

Inject interruption before and after each durable boundary: reservation commit; pin installation; allocation; bytes flush; receipt persistence; promotion transaction; retirement intent; allocator reclamation; acknowledgement persistence; ledger release; and takeover.

Exercise duplicate/reordered messages, lost acknowledgements, simultaneous cancellation and staging, owner restart, source corruption, destination unavailability, predicate phantom insertion and index rebuild.

Cancellation must stop new steps, fence outstanding commands, reconcile materialized bytes and only then release affected resources. A timer expiry alone cannot safely release occupied or still-promotable capacity.

Record a seed, configuration, fault point, complete operation history and invariant-check result for every run. Target at least 10,000 seeded randomized traces plus deterministic traces for every crash boundary; this is a research coverage target, not proof of correctness. Count unique explored cases rather than repeated identical successes.

**G5 pass:** Zero invariant violations in the declared campaigns; bounded-model and integration results agree on corresponding histories; recovery converges under fair, fault-free continuation within a workload-specific bound declared before running. An invariant violation stops performance acceptance until repaired and rechecked.

## 10. Weeks 12–13: Measure attributable technical effects

### Workload design

Start with small, fully explainable fixtures, then scale independently along these axes:

- Managed-pool utilisation: 70%, 85%, 95% and 98%.
- Competing plans: 1, 2, 4 and 8.
- Destination eligibility: disjoint, partly shared and heavily overlapping.
- Reclamation delay: immediate, delayed and lost acknowledgement followed by reconciliation.
- Background mutations: low and high, both related and unrelated to remaining witness dependencies.
- Fault campaign: no faults, process restart and declared source/destination failures.
- Code/workload: model 2-of-3; physical 4+2; multiple fragment sizes and stripe counts recorded explicitly.

Use a staged matrix instead of an unmanageable full Cartesian product. For performance comparisons, use identical replayed events, resource budgets, fault models and termination rules. Measure feasible and infeasible workloads separately. Simulator speed is not storage throughput.

### Proposed acceptance criteria to freeze before results

| Criterion | Proposed project threshold |
|---|---|
| Safety | No observed invariant violation in the declared bounds and campaigns |
| Primary efficiency effect | At least 20% reduction in verification CPU per successfully completed repair versus B1 on a predeclared contention/reclamation suite |
| Practical secondary effect | At least 10% improvement in time to restoration or peak temporary allocation on that suite; select which metric is primary before testing |
| Foreground impact | No more than 5% degradation in p99 foreground latency on a predeclared no-fault control workload |
| Restoration success | No worse completion rate than B1 under the same feasible-workload deadline; report all failures and UNKNOWN outcomes |
| Attribution | Full revalidation and reuse-disabled experiments explain which mechanism produces the gain |

These are proposed engineering success criteria, not patent-law thresholds, promised outcomes or automatically awarded score points. If the mechanism cannot plausibly affect the secondary metric, amend the registered protocol before seeing results and explain why; do not select a favourable metric afterwards.

Count planning, validation, metadata work, invalidation, retries and reconciliation in the total overhead. Report CPU per attempt as well as per completion, wall-clock restoration time, repaired bytes, retained/reserved space and re-copied data. CPU savings that require far more attempts or longer repair time may not be a useful effect.

Use at least ten independently seeded paired runs for each primary configuration, with additional runs if variance makes interpretation uncertain. Report absolute values, effect sizes and 95% confidence intervals. Aggregate at the run level; thousands of operations within one run are not thousands of independent experiments. Include unfavourable workloads and controls.

### Ablations

- Same planner, full suffix revalidation.
- Same storage enforcement, conventional capacity-aware scheduler.
- Same protocol with dependency reuse disabled.
- Same inputs with conservative serial scheduling.

Removing reservations or safe reclamation is permitted only as a negative-control fault experiment, not as an equally safe performance baseline.

**G6 pass:** A reproducible useful effect survives B1, is attributable to the proposed interaction and does not rely on changed protection guarantees. Failure of the 20% target does not legally disprove inventiveness, but it means this project's stated engineering target has not been met and the score must be reassessed accordingly.

## 11. Weeks 14–16: Freeze evidence and reassess

### Reproduction packet

- Exact source revision, build/runtime versions and environment description.
- Witness format, checker version, invariant definitions and model bounds.
- Reproduction instructions, seeds, workload fixtures and raw traces.
- Raw measurements and scripts producing every reported table/plot.
- Crash matrix, detected defects, fixes and remaining limitations.
- Updated prior-art chart mapped to the final mechanism.
- Claim-to-disclosure support table linking each proposed limitation to a specification passage and implementation/test evidence where available.
- Actual inventor contribution and disclosure/priority records.

An independent reviewer reproduces at least one representative success, one crash/reclamation case and the strongest baseline comparison. Ask the reviewer to construct a conventional implementation that defeats the claimed advantage.

### Drafting work

Rewrite the disclosure around the demonstrated mechanism. Include a complete operational example with numerical capacity accounting and a crash/restart sequence. Describe alternative embodiments only when sufficiently enabled. Do not broaden the system claim by dropping the essential interaction. Explain technical effects through actual storage operations.

The Indian Patent Office lists the 2025 CRI guidelines and supporting annexures on its [official guidelines page](https://ipindia.gov.in/resource/patents-resources-guidelines). The professional review should evaluate computer-related exclusions, novelty, inventive step, industrial applicability, clarity and disclosure support for the actual claims. Concrete storage involvement does not automatically resolve all requirements.

### Score reassessment rubric

| Criterion | Earlier assessment | Illustrative target | Evidence required for considering that target |
|---|---:|---:|---|
| Novelty | 11/25 | 17/25 | Final claim chart; precise distinction against closest disclosures; unresolved search limits recorded |
| Inventive step | 7/25 | 15/25 | Strongest combination objection addressed; attributable technical interaction and comparative evidence |
| Technical character | 16/20 | 17/20 | Enforced storage interfaces and concrete effect; Indian CRI review |
| Disclosure sufficiency | 10/15 | 12/15 | Complete state machine, worked embodiment, durable boundaries, recovery and limits |
| Industrial applicability | 5/5 | 5/5 | Reproducible storage use case with a feasible deployment path |
| Claim quality | 3/5 | 4/5 | Clear, supported scope centred on the final mechanism; professional drafting review |
| Priority/disclosure position | 1/5 | 3/5 | Documented facts and claim-specific support; adverse facts remain reflected |
| **Total** | **53/100 for earlier PRISM-X** | **73/100 conditional** | **Fresh holistic assessment; no automatic points for task completion** |

Resolving disclosure records can reveal a worse position. It cannot repair lost novelty merely by documenting it. A search cannot exclude unpublished applications or eliminate every unknown; the final assessment must retain those limitations.

**G7:** Proceed to an evidence-supported filing strategy, narrow the claimed mechanism, continue research on a specific unresolved issue, or stop this patent direction. Preserve actual results whichever decision is made.

## 12. First ten working days

| Day | Work product | Completion condition |
|---|---|---|
| 1 | Evidence/disclosure inventory and project assumptions | All known records captured; unknowns assigned an owner |
| 2 | One-page problem statement and claim hypothesis | Mechanism stated with enforceable inputs/outputs |
| 3 | Capacity ledger and safety/terminal predicates | Logical retirement and reusable capacity distinguished |
| 4 | Closest-source claim chart, first pass | Reservations/reconfiguration/scheduling references compared |
| 5 | Conventional combination analysis | Strongest obviousness explanation written before coding the new mechanism |
| 6 | X/Y baseline fixture and oracle | Competent baseline reaches feasible assignment |
| 7 | Reclamation dependency fixture | Delayed acknowledgement prevents premature capacity reuse |
| 8 | Crash/takeover fixture | Old-generation commands rejected; occupied capacity retained |
| 9 | Candidate mechanism and baseline trace comparison | A precise possible advantage or a clear failure finding is recorded |
| 10 | G1 review and next-stage specification | Proceed, narrow or stop based on evidence |

The first ten days aim to reduce uncertainty, not earn 70 points. Detailed timelines may change after this review.

## 13. Work backlog and evidence tracker

All entries below are pending. Creating this plan does not mark any implementation or legal gate complete.

| ID | Task | Dependency | Priority | Evidence output |
|---|---|---|---|---|
| P01 | Contribution/disclosure/priority inventory | None | Immediate | Signed/dated records and unresolved-items list |
| P02 | Professional timing and entitlement review | P01 | Immediate | Review notes and chosen strategy |
| R01 | Claim hypothesis and closest-art chart | None | Immediate | Search log, chart and combination analysis |
| S01 | State machine, ledger and fault model | None | Immediate | Versioned specification |
| M01 | Model oracle and strong baseline fixtures | S01 | High | Bounded exploration and traces |
| M02 | Reclamation/concurrency/crash examples | M01 | High | Minimal counterexamples and reference results |
| C01 | Planner and independent checker | M02, G1 | High | Checked witness implementation |
| C02 | Complete dependency invalidation | C01 | High | Coverage tests versus full revalidation |
| I01 | Durable authority and storage-agent hooks | C01 | High | Real allocation/promotion/reclamation evidence |
| I02 | Takeover, cancellation and reconciliation | I01 | High | Fault histories and invariant results |
| E01 | Registered comparative experiments | I02 | High | Raw results and attribution analysis |
| E02 | Independent reproduction | E01 | High | Reviewer report |
| P03 | Final claim-support and refreshed search | R01, I01, E01 | High | Supported draft and updated objections |
| A01 | Evidence-based reassessment | E02, P03, P01 | Final | New score with reasons and limitations |

For each task record owner, status, due week, artifact, reviewer and unresolved issue. Use statuses `PENDING`, `IN_PROGRESS`, `PASS`, `FAIL` or `UNKNOWN`. Do not convert UNKNOWN into PASS because a deadline arrived.

## 14. Boundaries that keep the plan achievable

Keep the initial embodiment to a fixed code profile, immutable content, a bounded protection group and a single authoritative metadata domain. Postpone arbitrary code changes, Byzantine verification, global distributed transactions and contingency planning for every future fault until the core evidence is strong.

Do not add AI prediction, blockchain logging or more certificate layers merely to make the disclosure look different. Add a feature only when it solves a documented failure or contributes to the demonstrated technical effect.

The earliest valuable result is a sharply defined mechanism and an honest comparison against a capable conventional controller. The final desired result is a defensible reassessment supported by records, implementation and experiments. Whether that reassessment exceeds 70 remains an outcome to establish.
