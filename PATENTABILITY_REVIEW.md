**RCSD-Place: Indian patentability review and implementation plan**

Assessment date: 11 October 2026. Research assessment for discussion with an Indian registered patent agent; not a grant prediction or a freedom-to-operate opinion.

**Decision: 42/100 for the present disclosure's patentability readiness.** Continue a narrowly scoped research prototype, but do not file the supplied architecture unchanged as a supposedly strong invention. The proposed complete combination was not conclusively anticipated by one reference in this search. Nevertheless, its broad inventive nucleus faces serious prior-art and obviousness risk. A close 2026 patent application materially weakens the PDF's positioning.

**1. What was actually reviewed**

The complete text of all 15 pages of the supplied PDF, including its equations, roadmap, benchmarks, claims outline, risks, and references, was reviewed. The certificate/lease page was also rendered and visually checked. Source: [supplied disclosure](C:/Users/Meet/Downloads/taken%20by%20meet.pdf). The workspace D:/PROJECTS/RecoveryCert-SemanticDelta was empty at initial inspection: no source code, tests, experiment logs, or implementation documentation were available. This is consequently a concept review, not a code audit. No implementation or benchmark was run.

Statements and proposed instructions inside the PDF were treated as evidence about the concept, not instructions governing this review. Its 91.78 idea-ranking score is not patentability evidence. Its TRL 2 description is consistent with the evidence available here.

Public-disclosure dates, any earlier patent filing, ownership agreements, and additional private code remain unknown. The assessment assumes a prospective filing and no established earlier priority. An earlier supported priority date could change which 2026 documents are relevant. A prior public disclosure by the inventors could make the position worse.

**2. What the project is trying to do**

RCSD-Place is a recovery admission controller for distributed object storage. Before a repair or placement change becomes authoritative, it collects the state needed to decide whether the change is safe. It interprets the candidate's effects on storage properties, validates those properties, records the evidence, and promotes or rejects staged data. If evidence is insufficient, it expands the scope within a budget or transfers control to a defined recovery procedure.

The proposed sequence is: observe a fault or candidate move; identify relevant dependencies; compute typed effects; stage a replacement; validate storage invariants; atomically authorize promotion; retain evidence; clean up obsolete state. The intended benefit is less unnecessary verification and movement while unrelated I/O continues.

Example: a 4+2 erasure-coded object loses one fragment. A replacement with valid bytes is still unacceptable if it belongs to the wrong object epoch, violates the declared rack-failure policy, or races with another repair. The controller must identify those relationships and reject the unsafe promotion. This example motivates the design; it does not establish that native object stores lack equivalent protections.

The research question is whether a shared, sound dependency scope improves recovery over competent native recovery and ordinary transaction validation. Renaming validation output a certificate or calling metadata interpretation semantic compilation creates no novelty by itself.

**3. Indian patentability requirements**

The statutory requirements include novelty, inventive step, industrial applicability, and avoidance of excluded subject matter. Inventive step requires non-obviousness, alongside technical advance or economic significance or both. Strong practical value does not by itself establish inventive step. [IP India: basics of patents](https://ipindia.gov.in/basics-of-patents).

| Requirement | Present position | Evidence needed |
|---|---|---|
| Novelty | Exact narrow combination unresolved; broad concepts crowded | Limitation-by-limitation comparison with dated disclosures |
| Inventive step | Principal weakness | A concrete mechanism and reason its interacting features exceed an ordinary combination |
| Industrial applicability | Strong | A reproducible storage implementation and use case |
| Section 3(k) | Plausible technical route, not automatic eligibility | Concrete effects on storage operations, I/O, recovery and concurrency |
| Section 3(f) | Possible aggregation objection | Functional interdependence of components rather than independent modules |
| Sufficiency and best method | Important details missing | Implementable closure rules, commit protocol, failure handling and worked embodiments |
| Clear supported claims and unity | Present outline is too functional | One technical inventive concept with supported limitations and fallback claims |
| Entitlement and priority | Unknown | Inventor contributions, assignments, disclosure chronology and filing records |

Section 3(k) excludes mathematical/business methods, computer programs per se and algorithms; section 3(f) addresses independent arrangements of known devices. Merely placing an algorithm in a storage-system claim does not resolve these issues. [Patents Act, section 3](https://www.ipindia.gov.in/acts/patent-act-1970/section-3).

The official 2025 CRI guidelines are available and were checked, rather than relying on a draft. They recognize technical improvements to storage, resource use and error correction, and do not impose a novel-hardware requirement. That supports this subject area, but does not establish novelty or inventive step for RCSD-Place. [Final CRI Guidelines 2025, especially pp. 35 and 39-40](https://ipindia.gov.in/storage/uploads/docs-operator/7fdd559b-1ff8-4a87-8c36-033e7356b39b.pdf). The government announced release on 29 July 2025; the resource index's later upload date should not be mistaken for the release date. [Official release](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2149719&lang=2&reg=48).

A complete specification must explain the invention and how to perform it, disclose the best method known to the applicant, and support clear claims. A production deployment or working prototype is not a universal prerequisite to filing. Here, experiments and a detailed protocol would strengthen technical credibility and disclosure; they cannot turn an obvious mechanism into a non-obvious one. [Patents Act, section 10](https://ipindia.gov.in/acts/patent-act-1970/section-10).

**4. Closest patent references found**

These are technical prior-art comparisons, not infringement determinations. Foreign publications may matter to Indian novelty even without an enforceable Indian counterpart. An expired or abandoned patent can still contain relevant public disclosure. Priority dates are distinguished from publication dates below; the earliest public disclosure of every family was not exhaustively established.

| Reference and date | Relevant disclosure and assessment |
|---|---|
| [CN121486381A](https://patents.google.com/patent/CN121486381A/en), priority 8 Jan 2026; published 6 Feb 2026 | **Highest-priority new comparison.** Claim 1 links event causality, a recovery cut, boundary recovery proofs, verification of outside state, rollback/replay and progressive synchronization. Claim 3 adds bounded traversal. Description S4 supplies versioned hash evidence. RCSD's typed EC/placement effects and atomic staged promotion were not established as disclosed together. Broad cut-plus-certificate language is at substantial risk. English text is machine-translated; obtain the original and a reliable translation before a legal conclusion. |
| [US10204126B2, Transaction repair](https://patents.google.com/patent/US10204126B2/en), priority 20 Mar 2014; associated A1 published 24 Sep 2015; grant 12 Feb 2019 | Claims 1 and 8 combine transaction deltas, dependency sensitivities, conflict filtering and incremental correction before committed deltas update a database. Strong challenge to generic semantic-delta and dependency-local repair claims. Storage-specific invariant evidence and staged EC recovery need separate comparison. |
| [US9589153B2, Securing integrity and consistency of a cloud storage service](https://patents.google.com/patent/US9589153B2/en), priority 15 Aug 2014; A1 published 18 Feb 2016; grant 7 Mar 2017 | Claims 8-9 join pending-operation conflict/commutativity tests, proofs, authentication and signed commit messages. Strong challenge to verification-plus-queue-check-plus-commit framing. Does not establish the complete proposed EC recovery mechanism. |
| [US20140143367A1, Robustness in a scalable block storage system](https://patents.google.com/patent/US20140143367A1/en), published 22 May 2014 | Description accompanying Fig. 7 uses PUT-log certificates, prepared storage writes and commit/abort; recovery checks certified logs. Claim 1 requires validation before updates. A signed recovery admission record is therefore a weak standalone differentiator. |
| [US8607011B2](https://patents.google.com/patent/US8607011B2/en), priority 4 Apr 2008; cited grant published 10 Dec 2013 | The PDF correctly cites coordinated consistent snapshots. Group-specific I/O blocking and prepare/commit are already present. A claim of avoiding a whole-cluster pause is not a sufficient distinction from all existing snapshot or recovery designs. |
| [US12204413B2](https://patents.google.com/patent/US12204413B2/en), priority 7 Jun 2017; cited grant published in 2025 | Claim 1 records snapshot intent, switches identifiers and waits for completion responses before commitment. Relevant to staging and commitment, but snapshot coordination is less directly aligned than the first three references. A recent grant number does not mean the underlying invention first appeared in 2025. |

No conclusion of exact anticipation is made. Novelty normally needs the claimed combination disclosed in a single qualifying reference; inventive-step analysis may consider combinations with a reason a skilled person would make them. My concern is an examiner combining local causal recovery with known delta/sensitivity processing and existing storage validation. That is an analysis of risk, not an established rejection.

**5. Research literature and native systems**

| Source | What it means for this project |
|---|---|
| [Ceph CRUSH documentation](https://docs.ceph.com/en/latest/rados/operations/crush-map/) | Failure-domain-aware placement is existing functionality. It should be baseline machinery, not the claimed invention. |
| [Ceph peering documentation](https://docs.ceph.com/en/latest/dev/peering/) | Native recovery already reasons about authoritative histories, epochs, past acting sets, missing updates and when writes may resume. This is a much stronger comparison than treating Ceph as placement plus byte repair. Historical release evidence should be pinned for filing. |
| [MinIO/AIStor healing](https://docs.min.io/aistor/operations/core-concepts/healing/) | Object and shard healing are established. Benchmark against actual supported healing behavior. This documentation does not establish an external S3 hook that can veto internal fragment promotion. |
| [NC-Audit: Auditing for Distributed Storage Systems](https://arxiv.org/abs/1203.1730), first posted 2012 | Integrity auditing compatible with coded-storage repair is known. Its cryptographic assurance is different from a trusted controller signing its own invariant results. |
| [Cooperative Local Repair](https://arxiv.org/abs/1409.3900), 2014 preprint | Repair locality has a long research history; the PDF's reference is real. Its code constructions address a different mechanism from recovery admission. |
| [Enabling Node Repair in Any Erasure Code](https://www.cs.cmu.edu/~nihars/publications/repairAnyStorageCode_ISIT2011.pdf), ISIT 2011 | Reducing repair downloads and disk access is established. Avoid claiming those goals without a distinct method. |
| [Coordination Avoidance in Database Systems](https://www.vldb.org/pvldb/vol8/p185-bailis.pdf), PVLDB 2014/2015 | Invariant-based selective coordination is prior art. Continuing unrelated work while maintaining invariants needs a specific technical distinction. |
| [Repairing Conflicts among MVCC Transactions](https://arxiv.org/abs/1603.00542), 2016 | Dependency representations support fine-grained repair of invalidated computations. This is a relevant adjacent field missing from the PDF. |
| [Inductive Proof Slicing](https://arxiv.org/abs/2404.18048), 2024 | Compositional dependency-based verification is established research. It is an analogy for verification scope, not evidence of a runtime object-repair controller. |

**Recent publications checked, through this search on 11 October 2026:**

| Publication | Relevance |
|---|---|
| [Revisiting Network Coding for Warm Blob Storage / NCBlob, FAST 2025](https://www.usenix.org/conference/fast25/presentation/gan) | Improves repair I/O for small blobs through a coding/storage design. Shows that ordinary repair-time gains alone will not distinguish RCSD. |
| [LESS is More for I/O-Efficient Repairs, FAST 2026](https://www.usenix.org/conference/fast26/presentation/cheng) | Reduces accessed data and seeks during repair. Control-plane gains must be isolated from code-level gains. |
| [GroupRS, ICPADS 2025, added to IEEE Xplore 14 Jan 2026](https://ieeexplore.ieee.org/document/11323221/) | Studies placement, repair parallelism and rack-failure reliability. These objectives are active prior-art territory. Abstract-level review here. |
| [Making Wide Stripes Practical, Dec 2025 preprint](https://arxiv.org/abs/2512.10425) | Cascaded parity local-repair codes are another current repair-efficiency approach; not an identified anticipation of the admission controller. |
| [Proof-Gated Publication, 2026 preprint](https://arxiv.org/abs/2608.14643) and [full text](https://arxiv.org/html/2608.14643v1) | Closely adjacent verify-before-publication design for lakehouses, with staged data, signed evidence and commit-path checks. Different application, but generic proof-gated promotion is not a safe novelty claim. This is a preprint; reported results were not reproduced. The returned page dates and identifier should be reconciled against the archived original before relying on its exact public-disclosure date. |

The PDF's coding, audit and snapshot references are directionally useful. Its major omission is comparison with transaction repair, native recovery consistency, and the closer causal-boundary patent. Its benchmark and TRL references guide development but provide no independent evidence of novelty. This was a substantive targeted search, not an exhaustive review of every 2026 publication.

**6. What may still be worth claiming**

The strongest direction is a concrete storage repair mechanism where typed changes determine exactly which storage proof obligations and dependency versions must be validated, and the same evidence controls an atomic fragment/placement promotion. It needs a technical distinction beyond generic locality, hashing and checking before commit.

For evaluation, decompose the proposed combination:

| Proposed limitation | Current assessment |
|---|---|
| Versioned graph of storage entities | Useful representation; novelty weak in isolation |
| Bounded dependency region and outside-state evidence | High overlap risk; cannot be the whole claim |
| Typed storage-effect vector | Specific schema may remain distinguishable; a vector alone is ordinary engineering |
| Effect-selected invariant obligations | Promising research focus only if selection is sound and changes actual work |
| Certificate bound to scope, candidate and generations | Useful implementation detail; signed proof/commit fields are crowded |
| Reversible staging and promotion | Known transaction pattern; must specify storage-specific behavior |
| Atomic validation including boundary membership changes | Essential for correctness; novelty itself still unestablished |
| Incremental expansion with reusable valid evidence | Potential optimization; compare with incremental verification and transaction repair |

A candidate research formulation is: for a declared class of erasure-fragment replacement, derive proof obligations from typed storage effects; obtain versioned evidence for their dependency boundary; stage a candidate bound to that evidence; permit authoritative promotion only when an atomic validation confirms both entity versions and dependency-membership versions; selectively invalidate affected evidence when those versions change.

This formulation contains proposed engineering additions beyond the supplied disclosure. It is not a filing-ready claim, a finding of novelty, or evidence that the inventors already conceived every detail. Document actual inventor contributions and rerun the prior-art comparison before using it.

**7. Technical gaps to close before claiming safety**

1. **Closure versus budget.** A traversal stopped by a budget is not necessarily dependency-closed. Return COMPLETE, INCOMPLETE or CONTRADICTORY. Only COMPLETE with sufficient evidence can qualify for certification. Remove the unsupported word 'minimal'; a fixed-point closure need not be a globally smallest sufficient set.

2. **Boundary completeness and phantom dependencies.** Checking versions of nodes already read will miss a new repair-queue entry or newly created dependency. Version the relevant adjacency sets, queue partitions or predicates, and validate them too. Otherwise a certificate can be internally consistent yet incomplete.

3. **Atomicity.** A final version reread followed by a separate commit leaves a race. Validation and authorization must share a linearization point, using an actual transactional metadata authority or an equivalent proven protocol. A simulator that serializes everything cannot demonstrate distributed safety.

4. **Fencing.** Lease expiry alone does not stop an old controller from writing after failover. Storage-side promotion must reject stale fencing tokens. Define which authority allocates tokens and how crashes affect ownership.

5. **Staging semantics.** Stage data durably but keep it non-authoritative. 'Not durable before commit' is ambiguous: durability of staged bytes and visibility of the authoritative mapping are different events. Preserve existing valid shards until the commit and retention conditions are satisfied. Abort must never erase an acknowledged newer write.

6. **Durability versus decodability.** Having k valid independent shards now proves neither configured redundancy nor survival of the next permitted failure. Count distinct fragment identities and verify rank for the selected code. For declared failure sets F, require enough independent valid fragments after removing F, or explicitly label an allowed degraded state. Do not equate the number of racks with a complete reliability guarantee.

7. **Pre-existing damage.** Recovery starts from a state that may already violate a desired redundancy policy. Define staged progress and the final restoration target; otherwise an all-invariants gate can prohibit every useful intermediate repair.

8. **Certificate meaning.** A digest authenticates the evidence selected; it does not prove nothing was omitted. A signature attributes a statement; it does not prove the controller is correct. Specify trusted metadata authority, checksum authenticity, fault model, checker/policy version, evidence retention and independent replay.

9. **Budget meaning.** Separate bounded graph work, bounded staging I/O and end-to-end recovery work. Native fallback may exceed the cut budget. Charge rejected/retried attempts and staging work; otherwise advertised overhead bounds are misleading.

10. **Integration authority.** An observer built on S3 notifications can evaluate decisions but has not demonstrated that it prevents internal healing commits. Either own the relevant fragment/manifest path or implement a version-pinned engine hook. Name the exact interception point before promising a live healing gate.

11. **Fallback ownership.** Fence or abort the staged action before native recovery takes ownership. Native recovery may preserve its own invariants without enforcing new provenance policies. Mark those additional guarantees unavailable, or quarantine the action, rather than silently treating fallback as fully certified.

12. **Liveness and comparison.** Bound retries and prevent starvation during topology churn. Unrelated objects can share I/O devices or policy counters, so outside-cut activity is not necessarily unaffected. Report both safety and interference.

**8. Implementation plan with decision gates**

Planning estimate: 12-16 focused weeks for an experienced developer, with additional time likely for a native Ceph hook. This is an estimate, not an assertion that the current repository has any implementation. Use a Linux VM or equivalent reproducible Linux environment for real storage tests; retain portable simulator tests on Windows.

| Phase | Work and deliverables | Exit gate |
|---|---|---|
| Week 1: define scope and filing facts | Disclosure chronology; inventor/owner records; comparison of closest patent limitations; one operation: replace an EC fragment; crash/omission/corruption model with trusted metadata authority | A specific distinguishable hypothesis, or stop/reframe before expensive integration |
| Weeks 2-3: formal model and simulator | Deterministic event log; object epochs, shard identities, maps, placement policies and queue generations; independent full-state oracle; small-state protocol model | Explicit safety, degraded-mode and liveness specifications; counterexample traces reproducible |
| Weeks 4-5: closure and effects | Rule-driven fixed-point closure; membership versions; PASS/FAIL/UNKNOWN checks; typed effects selecting obligations; explainable expansion trace | Cut results agree with the independent oracle on generated cases; no incomplete cut accepted |
| Weeks 6-7: certificate and durable gate | Canonical evidence format; checker version; staged manifest; atomic validation/promotion; fencing; idempotent restart; separate garbage collection | No stale-token promotion, phantom dependency escape or double ownership in tested/modelled interleavings |
| Weeks 8-10: live data-path prototype | Actual bytes and EC shards; controller-owned fragment manifests over lab storage endpoints; real promotion enforcement; fault injection | A physical shard loss is repaired through the gate, while a deliberately stale repair is blocked |
| Weeks 11-12: comparative experiments | Native and ordinary-validation baselines; ablations; workload/fault matrix; raw traces; scripts and environment manifests | Demonstrated incremental benefit at equivalent declared safety; report adverse and no-benefit cases |
| Weeks 13-16: optional native adapter and patent packet | Version-pinned native recovery hook; full disclosure with state machine, worked examples and evidence; agent claim review | Native recovery claim only if actual internal promotion is controlled; otherwise limit claims to the implemented architecture |

Use Python for a deterministic simulator and initial controller, a transactional metadata store for the lab prototype, and standard erasure coding rather than a new code. A single-process transaction store can establish a limited proof of concept but not distributed high availability. Add a distributed authority only when its semantics are specified and tested. Choose languages and dependencies for reproducibility; none contributes patentability merely by being selected.

Suggested modules: model, event_log, graph, closure_rules, effect_compiler, invariant_oracle, certificate, lease_store, promotion_gate, adapters, fault_runner and benchmarks. The oracle must compute full-state truth independently of cut-selection code to avoid validating the same bug twice.

**Protocol sketch for the prototype**

```
receive candidate with immutable operation ID
obtain authoritative snapshot and ownership fence
build dependency closure and boundary membership evidence
if incomplete: expand within budget or hand off safely
derive typed effects and required invariant checks
stage candidate fragments; persist hashes and durable receipts
evaluate candidate against evidence and declared degraded-state policy
if failed: abort staged action without changing current authority
if unknown: expand/retry within policy, otherwise hand off
produce candidate-bound verification record
atomically validate entity versions, membership versions and fence
and commit manifest transition plus certificate reference
on conflict: invalidate affected evidence and retry within budget
after authoritative commit: reclaim obsolete data only when safe
```

The atomic step is a requirement to implement, not a capability obtained by writing this pseudocode. For a scope crossing multiple metadata partitions, use a proven cross-partition transaction or restrict the MVP to one authority and reject unsupported scopes.

Certificate fields should include operation and cluster IDs; schema/checker/policy versions; pre-state epoch; candidate manifest hash; typed effects and selected obligations; dependency and boundary versions; source fragment identities/epochs/hashes; durable-stage receipts; invariant witnesses; fence; budget consumption; decision and authentication. Retain the evidence needed to reproduce checks, not only its hash.

**9. Experiments that would actually strengthen the application**

Use native recovery as the primary practical comparator, not an artificial whole-cluster rebuild. Add an ordinary optimistic-concurrency implementation with the same invariants and no exported certificate. Also compare global checking, fixed-radius checking, cut-only checking, and the full typed-effect design. A certificate-only baseline must still be reasonably optimized; deliberately inefficient baselines prove little.

Essential faults: drive loss; rack loss; corrupt shard; duplicate shard identity; valid checksum with wrong epoch; map change during verification; queue insertion after closure; concurrent writer; overlapping repairs; controller crash at each persistence boundary; delayed old-controller promotion; timeout; partition; certificate replay; partial staging; budget exhaustion; and native fallback racing with RCSD.

Start with 10,000 randomized traces and exhaustive small-state interleavings where practical. Zero observed unsafe commits is an empirical result, not a proof of universal safety. Preserve failing seeds and state histories. Formally state the modeled assumptions and limitations.

Sweep 4 KiB to 1 GiB objects in practical subsets, 4+2 then larger EC profiles, 1/4/16/64 concurrent repairs, rack/zone layouts, read/write mixes and foreground load. Avoid an infeasible full Cartesian product; begin with a documented representative matrix, then stress the identified bottlenecks.

Measure bytes read/written/moved, graph-maintenance CPU and memory, stage storage, certificate/evidence sizes, verification count, invalidations, retries, rollback and recovery time, fallback rate, unavailable-object time, GET/PUT p95/p99 and goodput. Keep verification work separate from data repair work and charge startup/background graph maintenance.

Correct the PDF's metrics: define the affected protection domain before comparing blast ratios; use exact-oracle minimum bytes only where computable and otherwise label the denominator as a lower bound or baseline; report metadata-only cases separately when an oracle-byte denominator is zero. Distinguish state inspected from state mutated. Small cuts with frequent fallback are not automatically a win.

Illustrative engineering targets to agree before experiments: at least 20% lower verification CPU or inspected state against equivalent ordinary validation; at most 5% no-fault throughput regression; no more than 10% adverse p99 regression under the selected repair workload; no unsafe commits in the defined campaign. These numbers are proposed decision thresholds, not legal tests or achieved results. Report repeated runs and uncertainty, with resource-matched baselines.

If the full system does not outperform ordinary cut-local validation, the extra certificate and semantic-vector architecture has not earned its claimed performance contribution. If benefits come only from no-op filtering, narrow the invention to the actual mechanism and search that mechanism separately. If the effect-selection logic omits required checks, fix safety before measuring speed.

**10. Score and how to interpret it**

This is a transparent subjective readiness rubric, not a statistically calibrated grant probability. The components are not legal substitutes for one another: failure of a required legal test can defeat a claim regardless of total score.

| Factor | Maximum | Present score | Reason |
|---|---:|---:|---|
| Novelty of a supportable narrow combination | 25 | 9 | No conclusive single-reference anticipation found, but close disclosure exists |
| Inventive step | 25 | 5 | Combination of established mechanisms remains the central risk |
| Technical character under Indian CRI practice | 20 | 14 | Storage-system effects are credible, presently unmeasured |
| Sufficiency and technical substantiation | 15 | 6 | Architecture exists; closure and promotion protocols are underspecified |
| Industrial applicability | 5 | 5 | Clear storage infrastructure use |
| Claim precision and support | 5 | 2 | Current outline uses broad functional outcomes |
| Priority, ownership and disclosure evidence | 5 | 1 | Unverified, not an assumed legal defect |
| **Total** | **100** | **42** | **Worth testing; weak case for filing unchanged** |

The score could improve if a narrow mechanism survives claim charting, is sufficiently disclosed and demonstrates a technical contribution beyond ordinary validation. It could fall sharply if the close references cover the final mechanism or an earlier public disclosure defeats novelty. Finishing the prototype alone does not justify a promised future score.

**11. Filing preparation and timing**

Establish the earliest disclosure date now. Record public repositories, demonstrations, papers, theses, slides, competitions and disclosures without confidentiality. India has specific anticipation exceptions, not a general assumption that every inventor publication receives a grace period. Section 31's exceptions concern particular exhibitions and learned-society disclosures; have an agent assess actual facts. [Section 31](https://www.ipindia.gov.in/acts/patent-act-1970/section-31).

If a public deadline is imminent, discuss an adequately detailed provisional filing promptly rather than waiting for the entire roadmap. A provisional must support the eventual claimed subject matter to secure useful priority; later additions are not automatically backdated. A complete specification normally must follow within 12 months. [Section 9](https://www.ipindia.gov.in/acts/patent-act-1970/section-9), [section 11](https://ipindia.gov.in/acts/patent-act-1970/section-11).

Prepare a filing packet containing: inventors and contributions; applicant and assignments; problem and closest art; the precise mechanism; algorithm/state-machine details; storage topology and data structures; at least one fully worked embodiment; concurrency and crash cases; alternative embodiments; technical effects with accurately labeled evidence; claim-support table; and disclosure chronology. Separate measured results from hypotheses. Do not paste the research roadmap into a specification as if every future feature were already enabled.

For a new Indian application, docket the examination request under the current Rule 24B: generally 31 months from priority or filing, whichever is earlier. Older pre-amendment applications have a transitional provision; do not use an old 48-month checklist for a new filing. [Current Rule 24B](https://ipindia.gov.in/acts/patent-rules-2003/rule-24b).

If an Indian resident intends to file abroad, address section 39 before doing so: foreign-filing permission or the applicable prior Indian filing route and secrecy conditions matter. [Official PCT guidance](https://www.ipindia.gov.in/pages/patents/pct-isa-ipea). Confirm forms, applicant category and deadlines with the filing agent; this review does not submit an application.

**12. Search coverage and remaining limits**

Search covered public web-indexed patent disclosures, selected claims/descriptions on Google Patents, original papers/preprints, publisher and conference pages, official storage documentation, and current IP India legislation/guidelines. Query families included storage repair with dependency graphs/certificates, bounded causal recovery, pre-commit erasure repair, semantic transaction validation, invariant coordination, and 2025-2026 repair publications. Irrelevant keyword matches were excluded.

A follow-on professional search should include InPASS, WIPO PATENTSCOPE and Espacenet; Indian counterparts, families, citations and prosecution histories; non-English originals; and classification searches around G06F11/14, G06F16/23, G06F21/64 and H04L67/1095, refining subclasses to the final claim. These databases were not exhaustively searched here. The CN A1 publication was inspected; a secondary B-version lead was not independently verified and is not relied on for status.

Unpublished applications, indexing gaps and uncertain historical documentation dates remain blind spots. No Indian freedom-to-operate clearance or legal-status verification was performed. Patentability concerns what can be claimed; freedom to operate concerns rights that a deployment may infringe. They require different analyses.

**Recommended next action:** resolve disclosure/priority facts and have the closest references claim-charted before major integration work. In parallel, implement the small deterministic model of complete dependency evidence and atomic promotion. That is the fastest way to learn whether a defensible storage-specific invention remains.
