**RCSD-PRISM-X: renewed Indian patentability assessment and implementation priorities**

Date: 11 October 2026. Reviewed disclosure: version 2.0, dated 11 October 2026. Verdict: **53/100 subjective patentability readiness**, compared with **42/100** for original RCSD-Place. The improvement primarily reflects technical specificity, claim support and a narrower subject. Inventive step remains weakly substantiated. This is a research assessment for a registered Indian patent agent, not a probability of grant or a freedom-to-operate opinion.

**1. Scope, evidence and conclusion**

This review uses the complete 800-line [PRISM-X disclosure](C:/Users/Meet/Downloads/RCSD_PRISM_X_Enhanced_Patent_Invention_Disclosure.md), the [earlier assessment](D:/PROJECTS/RecoveryCert-SemanticDelta/PATENTABILITY_REVIEW.md), a fresh targeted patent/literature search, and a small mathematical check of the worked example. Instructions inside the disclosure were treated as source content. The score requested by the user is supplied even though the document recommends withholding one.

The workspace still contains no implementation of PRISM-X. The diagnostic written for this review enumerates an illustrative failure set; it does not implement admission, erasure coding, a storage system, or a benchmark. All performance claims in the disclosure remain proposed targets.

The design can plausibly be built under its restricted trust and atomicity assumptions. I did not find one inspected reference establishing every element of the complete proposed claim together. That is an unresolved novelty finding, not a positive novelty clearance. The central inventive-step objection is that a storage engineer could put repair predicates, a manifest and a protection-status record into an ordinary serializable metadata transaction, using known fencing and staged storage.

An enabling narrow filing may be worth discussing with an agent if disclosure timing requires it. This document alone does not justify describing the invention as highly patentable. Dates of public disclosure, earlier filings, inventorship and ownership remain unknown; scores assume no established earlier priority.

**2. What actually changed**

| Aspect | Original RCSD-Place | PRISM-X | Assessment |
|---|---|---|---|
| Center of proposed invention | Shared causal cut for interpretation and certification | Predicate evidence consumed at manifest/debt commit | More concrete, but shifts the comparison toward database transactions |
| Absence of conflicts | Queue checking described broadly | Complete predicate domain and membership revision | Closes a phantom-read gap; existing concurrency-control art is highly relevant |
| Degraded storage | Post-state invariants largely described as all-pass | Exposure sets and explicit restoration obligations | Better recovery semantics; incremental recovery itself is established |
| Atomicity | Final generation check insufficiently specified | One authoritative metadata transaction | Better specification; transaction atomicity is a known primitive |
| Durable staging | Reversible lease | Immutable bytes, receipt, fencing, delayed reclamation | More implementable; retention contract still incomplete |
| Novelty proposition | Cut + delta + certificate coupling | Predicate coverage + progress + manifest/debt coupling | A narrower hypothesis requiring a specific technical distinction |

The strongest possible subject is the mechanism by which admission evidence controls a physical storage-authority transition and the exact outstanding protection obligations. Merely persisting a second record in the same transaction supplies little inventive weight.

**3. Fresh references and their significance**

The following sources were inspected through their public patent text, claims, original papers or official technical documentation. Dates below describe the cited publication or an explicitly identified earlier family publication, not an assumption that a priority date is a public-disclosure date. Territorial status and infringement were not verified.

| Source | Verified relevant teaching | Consequence for PRISM-X |
|---|---|---|
| [US8396831B2, Optimistic serializable snapshot isolation](https://patents.google.com/patent/US8396831B2/en); A1 publication 23 June 2011, grant 12 March 2013 | Read-set validation and phantom checking; claim 16 records scan information and checks equivalent results at transaction end | Negative witnesses cannot be presented as the invention of detecting an absent record becoming present. This reference uses scan validation, not necessarily PRISM's exact domain counter. |
| [FoundationDB: A Distributed Unbundled Transactional Key Value Store, SIGMOD 2021](https://www.foundationdb.org/files/fdb-paper.pdf), algorithm 1 | Commit conflict detection uses read/write key ranges; range conflicts prevent phantoms | A strong technical baseline for atomic absence checking and multiple metadata updates. It does not itself disclose PRISM's complete EC/debt protocol. |
| [US20180121286A1, Efficient repair of erasure coded data based on coefficient matrix decomposition](https://patents.google.com/patent/US20180121286A1), 3 May 2018; priority listed 1 November 2016 | Claim 1 specifies matrix decomposition for efficient rank evaluation; description discusses future-failure repair feasibility and reusable computation | The disclosure's warning is substantiated. Full rank calculation or cached survivability checks cannot independently carry the novelty argument. |
| [US20160196295A1, Rendezvous-based optimistic concurrency control](https://patents.google.com/patent/US20160196295A1/en), 2016 | Validation subscribes to changes in read sets, including predicate/range requests, and operates alongside transaction work | Changed-dependency detection is established; its exact mechanism differs from a revision-indexed admission witness. |
| [US9075773B1, Prioritized repair of data storage failures](https://patents.google.com/patent/US9075773B1/en), 2015 | Repair tasks, protection levels and resource budgets drive recovery scheduling | Tracking outstanding repairs and reduced protection is known. This is not an identified disclosure of atomic scenario-set debt discharge. |
| [US12235730B1, Prioritizing important files while restoring protection](https://patents.google.com/patent/US12235730B1/en), 25 February 2025 | Claim 1 maintains file protection levels and restores degraded protection using priority/non-priority tables | A recent example of protection-state tracking. Relevant background, less direct than phantom-validation art. |
| [Bringing Order to Practical Validation of Database Isolation Levels, TOCS 2026](https://www.doc.ic.ac.uk/~afd/papers/2026/TOCS.pdf) | Version-certificate and ordering-based checking handles predicate operations; extends EuroSys 2024 work | Useful for validation design. It checks execution histories; it is not a runtime fragment-admission protocol. Similar vocabulary does not establish anticipation. |

The earlier [causal recovery patent CN121486381A](https://patents.google.com/patent/CN121486381A/en) was also reopened. Moving graph cuts out of the independent claim reduces that particular overlap. Its existence still prevents treating a general recovery-boundary certificate as new. A reliable original-language claim review remains necessary.

The earlier transaction-repair, authenticated-commit and prepared-storage references remain relevant: [US10204126B2](https://patents.google.com/patent/US10204126B2/en), [US9589153B2](https://patents.google.com/patent/US9589153B2/en), and [US20140143367A1](https://patents.google.com/patent/US20140143367A1/en). Those comparisons are documented in the earlier report; the current search concentrated on the added limitations.

Recent coding work such as [LESS, FAST 2026](https://www.usenix.org/conference/fast26/presentation/cheng) concerns repair I/O and code constructions. It is relevant to benchmark interpretation, but less close to PRISM's core than older concurrency-control work. Recency alone does not determine prior-art relevance. The earlier proof-gated-publication preprint has unresolved exact-date metadata and is not decisive for this score.

**4. Preliminary limitation chart for proposed Claim 1**

This is a technical comparison, not a completed legal claim chart. 'Unresolved' means the exact interaction has not been established either as new or as anticipated.

| Claim limitation | Closest inspected threat | Residual distinction or missing proof |
|---|---|---|
| Replacement of an EC fragment with epoch/profile/policy | Established storage recovery and rank-feasibility art | An operation context, with little inventive weight alone |
| Positive and complete negative witnesses | US8396831B2 and FoundationDB range validation | Exact coverage-index construction and writer obligations need comparison |
| Survivability and degraded-progress obligations | US20180121286A1 plus protection-tracking references | Scenario-set progress tied to admission remains unresolved |
| Evidence binding identities, revisions and results | Earlier storage authentication and transaction-validation art | A data package alone may be routine serialization |
| Non-authoritative durable stage and receipt | Earlier prepared-storage and commit designs | Receipt retention and endpoint enforcement must be specified |
| Validate versions, receipt and fence at linearization | Standard conditional transactions plus ownership fencing | Correct implementation is necessary; novelty not established |
| Atomic manifest and obligation update | Ordinary multi-record transactions | Needs more than atomically updating associated bookkeeping |
| Re-evaluate affected checks | Transaction repair and dependency-aware validation | Exact safe reuse algorithm and measurable advantage are missing |

Proposed system Claim 2 is particularly broad: it omits much of the detailed exposure/progress relation that supposedly distinguishes the design. It risks claiming ordinary conditional metadata updates with an additional obligation record. Claim 1 is a stronger research starting point, but complete writer coverage is still partly a promised property rather than a fully disclosed construction.

The narrowest proposed fallback retains complete reservation coverage and a joint manifest/debt transaction. Narrowing can improve clarity and enablement, but a narrower obvious claim remains obvious. Method, system and storage-medium wording cannot compensate for a missing technical contribution.

**5. The strongest inventive-step challenge**

A plausible examiner reasoning chain is: an engineer wants concurrent repairs to avoid stale state; uses serializable validation to prevent phantoms; evaluates known erasure/placement conditions; stores the new manifest and the corresponding remaining-repair record together to prevent inconsistency; applies a fence to reject old owners. These features solve their usual problems in their usual ways.

This is my risk analysis, not a legal finding that a particular combination defeats the claims. A professional analysis must establish relevant dates, the skilled person's knowledge, claim construction and a reason to combine, avoiding hindsight.

To answer it, PRISM must identify exactly what the proposed mechanism achieves that an equivalently safe ordinary implementation does not achieve, and why that result follows from a specific interaction. A faster implementation may support a technical-effect argument, but ordinary optimization does not automatically supply inventive step. Preventing a phantom that standard serializable validation also prevents is not evidence of an additional correctness capability.

**6. Technical findings from this review**

**A. The progress condition is automatic for a useful but simple subset of repairs.** If policy, identities and code remain fixed, and a repair only adds a valid coding row without removing any surviving row, matrix rank after any fixed physical failure can only stay equal or increase. Consequently the exposure set cannot grow. Under those assumptions, the non-regression test expresses a mathematical property already implied by additive repair. It has more substantive work to do for transitions that remove, relocate or replace still-valid fragments, change code, or interact with reclamation.

This observation does not prove the complete protocol obvious. It means an additive-only demonstration is a weak basis for attributing special inventive value to exposure non-regression.

**B. Section 8's rejection example conflicts with the permissive progress rule.** I executed a small enumeration with an MDS 4-of-6 stripe, five surviving fragments on R1-R5, and a fixed 36-label family of rack-plus-device loss scenarios. Failures are unions, so a device in the lost rack adds no extra loss. Results:

| Layout | Unprotected scenario labels | Strict progress from initial state? | Meets complete target? |
|---|---:|---|---|
| Five surviving fragments | 20 | Starting state | No |
| Add replacement on R1 | 4 | Yes | No |
| Add replacement on R6 | 0 | Yes | Yes |

Thus R1 can satisfy strict exposure reduction while failing the final target. The disclosure can reject it by declaring a separate hard anti-colocation policy or a full-restoration-only operation mode, but the rejection does not follow from the general exposure-progress rule alone. The counts are properties of this illustrative fixed scenario family, not production reliability probabilities or benchmark results. Reproducer: [analysis/prism_exposure_check.py](D:/PROJECTS/RecoveryCert-SemanticDelta/analysis/prism_exposure_check.py).

**C. Manifest epoch and content epoch need different semantics.** The document places source epochs in fragment identity and increments manifest state during repair. Clarify whether a repair changes content generation. Surviving fragments must not become inadmissible merely because metadata membership advanced. Specify object-content epoch, manifest revision and fragment incarnation independently.

**D. Index coverage must survive index replacement.** Admission pseudocode compares predicate revisions, but needs an explicit match for index namespace/incarnation, coverage schema, writer-interception version and policy/checker versions. Rebuilding an index with the same numerical revision must not validate old evidence. Prevent revision wraparound/reset reuse, or scope counters to unique generations.

**E. Stage receipts need a retention protocol.** A receipt can establish an earlier durable write while garbage collection later removes the staged bytes. Bind a stage pin/retention state into admission and prevent cleanup until a terminal decision. State assumptions for endpoint failures between stage and promotion; metadata linearizability does not atomically freeze physical disks or detect every new failure.

**F. The admissibility checker must own debt correctness.** The authority must validate, recompute or trust an explicitly identified verified controller for proposed_debt_delta. Checking a client-supplied PASS or coverage_complete flag is not independent verification. Require persisted debt to correspond to the exact committed manifest and policy; specify debt invalidation/recomputation on unrelated failures and topology changes too.

**G. Own reservations require a defined rule.** 'No overlapping repair' must exclude an operation's own authorized reservation while still rejecting rivals. Otherwise reserving the stripe can invalidate the operation's own witness. Specify acquisition, predicate evaluation, promotion and release ordering.

**H. Fairness and progress are not implied by safety.** Continual conflicting reservations can starve a repair. A globally changed policy or stripe-level debt revision can invalidate most checks and remove expected reuse. Define bounded retries, owner arbitration, handoff success and liveness assumptions.

**I. Physical staging and admission can be separated safely only with enforced authority.** Every native healing path and privileged mutation must obey the gate. An S3 observer does not establish this property. Document exactly how the manifest controls read/reconstruction eligibility and how endpoints enforce deletion fences.

**J. Compact exposure representation needs an honest bound.** Enumerating every tolerated combination can grow combinatorially. Define a finite supported failure family for the MVP, measure cost, and specify the soundness of any later compression. Do not infer economical operation from a small 4+2 example.

**7. Indian requirements and score**

India requires novelty, inventive step, industrial applicability and compliance with exclusions. A useful technical system may still fail inventive step. [IP India overview](https://ipindia.gov.in/basics-of-patents).

The current official [2025 CRI guidelines](https://ipindia.gov.in/storage/uploads/docs-operator/7fdd559b-1ff8-4a87-8c36-033e7356b39b.pdf) were reopened. A concrete improvement to storage operations has a plausible technical-character argument. New hardware is not universally required. The application should explain actual admission enforcement, durability behavior and resource effects; abstract obligation evaluation or generic computer wording is weaker.

[Section 3(k)](https://www.ipindia.gov.in/acts/patent-act-1970/section-3) remains relevant to algorithms/programs per se; section 3(f) may matter if the claimed arrangement amounts to independent known components. The stated joint transaction supplies functional interaction, but does not automatically establish inventiveness. [Section 10](https://ipindia.gov.in/acts/patent-act-1970/section-10) requires adequate description, best method and supported clear claims. More detailed pseudocode helps; undefined coverage and receipt guarantees still matter.

| Same rubric as earlier review | Maximum | Original | PRISM-X | Reason for revised assessment |
|---|---:|---:|---:|---|
| Novelty of a supportable narrow combination | 25 | 9 | 11 | Better-defined combination; no complete single-reference anticipation established, but significant overlap |
| Inventive step | 25 | 5 | 7 | More specific coupling; standard transaction combination remains a strong challenge |
| Technical character under Indian CRI practice | 20 | 14 | 16 | Concrete storage-authority boundary and transition semantics |
| Sufficiency and technical substantiation | 15 | 6 | 10 | Data model, protocol, fault assumptions and examples; no working implementation and gaps remain |
| Industrial applicability | 5 | 5 | 5 | Clear distributed-storage application |
| Claim precision and support | 5 | 2 | 3 | Draft claims exist; broad system claim and ambiguous example limit support |
| Priority, ownership and disclosure evidence | 5 | 1 | 1 | Still unknown; this is incomplete evidence, not an assumed legal defect |
| **Total** | **100** | **42** | **53** | **Improved research/disclosure readiness; not a strong established patent case** |

This is a subjective rubric, not a calibrated likelihood. Points do not offset a failed legal requirement. The increase of 11 points chiefly rewards a clearer and more enabled proposal. It does not mean the search has proved a valuable monopoly or that implementation will inevitably raise the score. No future score is promised.

A prototype is not a universal filing prerequisite. The need here is an adequately disclosed contribution; experiments can substantiate asserted effects and expose gaps. Additional prose or features alone should not increase the novelty/inventive-step scores.

**8. Revised implementation plan**

The order should put the strongest ordinary baseline early. Waiting until late integration to discover that a standard transaction delivers the same result wastes effort. Planning estimate: 10-14 focused developer weeks to an evaluated narrow prototype, with native-engine integration potentially adding 2-4 or more weeks. Estimates depend on storage and concurrency experience.

| Phase | Deliverable | Acceptance decision |
|---|---|---|
| Week 1 | Resolve policy modes, content/manifest epochs, receipt retention, coverage incarnations and reservation lifecycle; prepare claim chart | Every hard condition and every permissible intermediate transition is explicit |
| Weeks 2-3 | Independent full-state oracle, deterministic events, small-state concurrency model, and ordinary serializable/OCC baseline | Baseline prevents phantoms, stale owners and debt/manifest mismatch with equivalent invariants |
| Weeks 4-5 | PRISM coverage/witness data and selective revalidation over the same authority and storage path | Results agree with oracle; cached outcomes have complete dependency sets |
| Weeks 6-7 | Real staged bytes and EC fragments, retention pins, durable receipts, atomic admission, idempotent replay, safe deletion | Stage-loss/cleanup race and uncertain-commit cases do not produce unsupported authoritative state |
| Weeks 8-9 | Concurrent repair, policy/index rebuild, partition, controller-crash and fenced-handoff campaigns | No unsafe commit in the stated modeled/tested space; failed traces preserved |
| Weeks 10-12 | Resource-matched performance and ablation campaign | Quantified benefit, if any, beyond the ordinary safe implementation |
| Weeks 13-14 | Reproducibility packet, claim support and professional reassessment | Continue filing work only around surviving technical distinctions |
| Optional extension | Version-pinned Ceph or other engine promotion hook | Demonstrate actual internal admission control before claiming native integration |

Use an established transactional metadata implementation for baseline and PRISM alike. Start with a single logical transaction domain. A local authority is acceptable for a restricted demonstration but is not evidence of distributed failover correctness. Keep slow fragment copying outside the commit transaction; validate retained evidence in a short authoritative transaction.

Required metadata records: manifest revision and content epoch; code and placement-policy generation; predicate namespace/incarnation/revision; checker and coverage version; owner fence; stage pin and receipt; recovery debt with matching manifest/policy provenance; consumed operation ID and decision digest. Ordinary and PRISM paths must check the same facts.

**Test additions beyond the supplied matrix:** rebuild an index while restoring its counter to an old value; change a checker version during reuse; delete a stage after issuing a receipt; insert the current operation's own reservation; repair while a content write changes epoch; increase protection debt through a concurrent detected failure; run two individually safe candidates whose combined effect is unsafe; attempt stale cleanup after successful promotion; exhaust the verification budget during an uncertain commit.

The corrected R1 example should pass as intermediate progress when the policy allows it and fail when a separately stated hard rule prohibits it. These two modes must have distinct expected outcomes; one test cannot establish both.

**9. Evidence needed to earn a stronger assessment**

Compare: ordinary serializable/predicate-OCC admission; the same baseline with incremental caching; PRISM; PRISM with witness reuse disabled; and appropriate native recovery. Unsafe entity-only validation is useful to expose races but is not the main performance comparator. If native recovery lacks added provenance obligations, label the semantic difference rather than treating raw timings as equivalent safety.

Measure all predicate-index writes, contention/aborts, proof selection and computation, retained evidence size, stage overhead, failed attempts and fallback work. Report total recovery time and protection-exposure duration as well as CPU and I/O. A small verification saving accompanied by prolonged degraded exposure is not an unqualified improvement.

The disclosure's 20% verification saving and 5% no-fault overhead figures are proposed engineering thresholds, not patent law or existing results. Run repeated workloads, publish confidence intervals and negative cases, and preserve independent oracle traces. Ten thousand randomized histories can detect defects; they cannot prove universal correctness.

Most persuasive remaining research questions:

- Can exact dependency evidence safely avoid expensive rechecking where competent cached serializable validation cannot do so as efficiently?
- Does a particular combined replacement/reclamation transition need a new representation or protocol to preserve scenario protection under concurrency?
- Can the coverage index achieve a provable completeness guarantee with materially less contention than a standard range/predicate design?

These are directions to investigate, not newly verified inventions. Search any resulting concrete mechanism before attributing patent value to it.

If ordinary safe transactions reproduce the same behavior and performance, simplify the system and reconsider patent expenditure. If a real distinct mechanism emerges, describe the causal link between its operations and measured technical effect, with claim limitations supported by the original filing content.

**10. Filing and search limitations**

Resolve disclosure dates and inventorship now. A name on an AI-assisted document is not evidence of legal inventorship or ownership. Do not assume the new version inherits any earlier priority automatically; support for each claimed addition matters. An Indian provisional ordinarily requires a complete specification within 12 months. [Section 9](https://www.ipindia.gov.in/acts/patent-act-1970/section-9). Prior public disclosure requires fact-specific advice; India's exceptions are limited. [Section 31](https://www.ipindia.gov.in/acts/patent-act-1970/section-31).

This search focused on Google Patents text, original papers, official documentation and Indian guidance, using both disclosure terms and underlying mechanisms: phantom detection, predicate/range validation, repair feasibility, protection restoration, atomic storage metadata and manifest updates. Exact-word searches for recovery debt do not establish absence of substantively similar work under other names.

The strongest newly verified challenges are older concurrency-control art and the cited rank-feasibility patent. Recent protection-restoration and predicate-validation publications update the landscape without proving complete anticipation. One attempted erasure-write patent page was inaccessible and was not treated as verified evidence. No complete InPASS/Espacenet/PATENTSCOPE family search, non-English claim translation, prosecution review or territorial FTO analysis was performed. Unpublished applications and indexing gaps remain.

**Recommendation:** research go, filing decision conditional. PRISM-X is substantially easier to specify and test than the original, but the next valuable step is a precise comparison against an ordinary safe transaction implementation and a professional claim chart. The current evidence supports **53/100 readiness**, not an 80-90/100 patentability claim.
