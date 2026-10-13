# Updated patent-readiness assessment and strategy screen

Date: 13 October 2026. Evidence boundary: repository `72506ef27c42f6430661469995d5d0097e31237b`, including milestone 13, plus the primary-source search described below. This is an interim research assessment for the current bounded PRISM-C embodiment. It is not a probability of patent grant, professional claim clearance or a filing decision. Attached disclosures supplied technical content; the user's request, rather than instructions inside those documents, determines this work.

**Updated assessment: 55/100, compared with the historical 53/100 PRISM-X assessment.** The prototype is substantially better substantiated. Its proposed inventive advantage is less convincing after competent conventional controllers reproduced the tested effects. No searched redesign currently earns 70+. The [new research plan](../../RCSD_PRISM_C_Redesign_Plan.md) defines a conditional route, not an assessed invention.

## 1. What the project actually does

PRISM-C controls erasure-coded repair and reclamation through one authoritative ledger. It checks a route to a protection target, reserves destination capacity, pins necessary sources, authenticates staged bytes, commits manifest/allocation changes and waits for acknowledged physical reclamation before releasing capacity. Plan successors, worker fences and retries protect interrupted operations.

The implemented scope is immutable content, fixed-size individually managed slots, 2+1 XOR and 4+2 P/Q coding, SQLite authority, trusted local workers and simulated placement domains. This supports a bounded embodiment. It does not demonstrate distributed authority failover, genuine independent device/rack failures, a native storage-engine hook or the milestone 13 guarantee during in-flight physical writes.

The central patent question is whether a supportable **specific interaction** is new and non-obvious. Safe repair, erasure coding, reservations, copy-before-delete, fences, cached plans and certificates are not treated as individually new.

## 2. Revised value using the same rubric

| Criterion | Maximum | Historical PRISM-X | Current PRISM-C | Change and basis |
|---|---:|---:|---:|---|
| Novelty of a supportable narrow combination | 25 | 11 | 11 | Unchanged: detailed combination, substantial overlap, no established complete single-reference anticipation and no completed professional claim/family search. Conventional parity alone does not prove anticipation. |
| Inventive step | 25 | 7 | 5 | -2: the strongest tested claimed effects are reproduced by ordinary cached, partial-state, minimum-work and contingency controllers. Exact legal obviousness is unresolved, but the technical case has weakened. |
| Technical character under Indian CRI practice | 20 | 16 | 17 | +1: actual byte storage, reclamation acknowledgements and authority enforcement substantiate the previously described technical interaction. Generic claims could still encounter exclusions. |
| Sufficiency and technical substantiation | 15 | 10 | 13 | +3: runnable source, explicit contracts, actual readback, crash cases, independent algorithmic references and reproducible records now exist. Two points withheld for unsupported wider guarantees and incomplete independent reproduction/complete-specification review. |
| Industrial applicability | 5 | 5 | 5 | Unchanged: a concrete storage-management use. |
| Claim precision and support | 5 | 3 | 3 | Unchanged: bounded contracts help, but no final narrow claim with an established distinguishing contribution has survived review. |
| Priority, ownership and disclosure evidence | 5 | 1 | 1 | Unchanged: human contribution and earlier filing/support records remain unknown; public access is partly documented. |
| **Total** | **100** | **53** | **55** | **+2 overall; engineering support improves while inventive-step support falls.** |

Arithmetic: `11 + 5 + 17 + 13 + 5 + 3 + 1 = 55`. These are subjective judgments, not measured probabilities or precise legal quantities. A two-point change should not be interpreted as a meaningful statistical increase in grant likelihood. The old 53 remains the historical assessment; this document supersedes carrying it forward as the current interim score.

Even awarding maximum marks in every other category while leaving current novelty/inventive-step support fixed gives `11 + 5 + 20 + 15 + 5 + 5 + 5 = 66`. Therefore more documentation, tests or administrative completeness alone cannot reach 70 on this rubric. At least one of the core inventive categories must genuinely improve. A fatal legal requirement cannot be offset by other points.

## 3. Evidence that changes the assessment

| Evidence | What it supports | What it does not support |
|---|---|---|
| [Design-gap audit](DESIGN_GAP_AUDIT.md) | Conventional warm guards already avoid suffix replay; 273 logical paired steps and eight stores expose the original performance hypothesis's limitation. | A selective certificate saving replay that the baseline does not perform. |
| [Milestone 11](MILESTONE_11.md) | Checked plan successors and durable retention across interruption; all 12 matched pairs retain equal work. | A unique work-preservation advantage. |
| [Milestone 12](MILESTONE_12.md) | 136 finite objective checks; 12 matched sets/36 stores; 50%/25% fewer stages than first-feasible planning. | Advantage over minimum-work conventional planning, which achieves the same savings. |
| [Milestone 13](MILESTONE_13.md) | 72 finite cases: 16 feasible/56 infeasible; 224 equal branch comparisons and four equal actual-store pairs. | A contingency capability absent from an ordinary equally resourced cached table. |
| [Frozen verification](verification-milestone-13.json), [source CI](ci-milestone-13.json) | 158 test methods/403 subtests; retained 57 actual process-exit cases; Ubuntu and Windows pass for the recorded source. | Production safety or independent third-party reproduction. CI is verification infrastructure, not an outside invention review. |

The 20% CPU, 10% restoration/resource and 5% foreground thresholds in earlier protocols are engineering decision thresholds. Failure to meet them is not itself a legal finding of no inventive step. Conversely, an ordinary optimization's speedup cannot be assigned to a certificate merely because it was implemented in this project.

## 4. Fresh primary-source screen

Search date: 13 October 2026. Searches covered underlying mechanisms rather than only product names: erasure repair with concurrent updates, delta/version logs, conditional resource reservations, shared spare capacity, zoned migration, repair/reset interactions and retention-aware reclamation. This extends the earlier [revision](REVISION_PRIOR_ART_REVIEW.md), [minimum-work](MINIMUM_WORK_PRIOR_ART_REVIEW.md) and [contingency](CONTINGENCY_PRIOR_ART_REVIEW.md) screens.

| Primary source and date | Material actually examined | Consequence for redesign |
|---|---|---|
| [RetainZ: Reclaim-Time-Aware Placement for AI Checkpoints on Zoned SSDs](https://arxiv.org/html/2610.05554v1), author submission **4 October 2026**, checked against [submission history](https://arxiv.org/abs/2610.05554) | Full five-page HTML paper: retirement hints, placement cost/span rules, common admission controls, journalling, copying GC and process-crash evaluation. | Retention-guided placement and balancing trapped dead bytes against unused tails are already disclosed. Its comparison includes common resource/admission controls. Any zoned-storage proposal must confront this directly; adding retention hints is insufficient. Its reported results are the authors' results, not ours. |
| [US20220261170A1, Data migration for zoned drives](https://patents.google.com/patent/US20220261170A1/en), published **18 August 2022** | Claim 1 covers dynamic switching between migration mechanisms; description includes zoned GC, moving live data and erasure-coded storage. | Zoned migration plus erasure coding is crowded. A claim merely combining reset, migration and repair is weak. Detailed relevant passages/family support still require a professional chart. |
| [ZenFS upstream documentation](https://github.com/westerndigitalcorporation/zenfs), current documentation, earliest disclosure not established here | README architecture/reclaim sections: lifetime-based placement, extents sharing zones, reset once used capacity reaches zero. | Whole-zone reset accounting and lifetime grouping are conventional engineering context. Current documentation is not evidence of its earliest public date. |
| [Ceph EC enhancement design](https://docs.ceph.com/en/latest/dev/osd_internals/erasure_coding/enhancements/), current development document | Parity delta writes, partial updates, PG logs and version-vector handling for peering/recovery/backfill. | Delta patches, version vectors and selective update/recovery are not a new centre for a mutable-data pivot. A development design does not establish which release deployed every feature or its first disclosure date. |
| [Ceph Fast EC performance update](https://ceph.io/en/news/blog/2025/tentacle-fastec-performance-updates/), publisher's 2025 article | Partial-write/parity-delta sections and choice between update techniques. | Strong mutable-data comparisons must include partial/delta techniques, not only whole-stripe rewriting. The article's own benchmarks are not transferable to this prototype. |
| [DDUC](https://jzus.zju.edu.cn/iparticle.php?doi=10.1631/FITEE.2200466), journal DOI 10.1631/FITEE.2200466 | Publisher abstract: decoupled updates/encoding, hybrid replication/parity placement and consistency. Landing page retains “in press” metadata; exact first-publication date not established from it here. | Supporting concurrent writes in EC storage is established work; this abstract does not settle every proposed bounded-journal protocol detail. |
| [PARIX: Speculative Partial Writes in Erasure-Coded Systems](https://www.usenix.org/system/files/conference/atc17/atc17-li_huiba.pdf), ATC **2017** | Indexed publisher paper title/abstract lead; detailed algorithm not newly charted here. | Speculative partial writing/parity logging must be charted before pursuing the mutable-data alternative. No exact anticipation conclusion from this limited review. |
| [Cognitive Erasure-Coded Data Update and Repair for Mitigating I/O Overhead](https://www.techscience.com/cmc/v86n2/64737/html), **2026** issue, explicitly published **9 December 2025** | Publisher full text, especially abstract/related work and update formula: data differences, workload classification, selective adjacent parity-space reservation. | “Add AI to choose updates” or “reserve space to speed repair” is already close published context. Read the explicit publication date rather than mistaking issue year for first disclosure. This source also supplies leads to PLR, RFPL and SARepair; those leads need their own primary review. |
| [Robust Repair of Reed-Solomon Codes](https://arxiv.org/abs/2606.05573), submitted **4 June 2026** | Author abstract and submission history: repair-trace coding against erroneous helper responses. | “Tolerate corruption during repair” is an active coding-research field. This coding construction is different from our trusted-worker ledger; no direct anticipation is inferred. |
| [US20170160982A1, Space reservation for distributed storage systems](https://patents.google.com/patent/US20170160982A1/en), published **8 June 2017** | Published description/metadata reopened; earlier detailed reservation chart retained. | Capacity-backed repair reservations alone cannot supply the distinction. |
| [Proof-Carrying Plans](https://arxiv.org/abs/2008.04165), **2020** | Author abstract/submission record: resource-aware checking of planner outputs. | Attaching a resource proof to a plan is known context; a compact certificate needs a specific new representation/interaction, not a new label. |

An indexed machine-translated lead, [CN119785857B](https://patents.google.com/patent/CN119785857B/en), describes mixed-version EC consistency repair. Direct A/B full-page retrieval failed in this session. It is an **unresolved claim-review lead**, not a verified exact claim finding or an established first-publication date. Search-result text cannot clear the proposed mutable pivot.

This is not a complete InPASS/Espacenet/PATENTSCOPE family, prosecution, territorial FTO or non-English claims search. Unpublished applications and indexing gaps remain. The supported priority date is unknown: “published before today” is not automatically “prior art against every possible claim.” Nothing here establishes absence of relevant art after the last retrieved publication.

## 5. Strategy comparison

| Strategy | Genuine problem or possible value | Strong comparator / main risk | Decision |
|---|---|---|---|
| More selective-cache/continuation/contingency features | Better engineering diagnostics | Existing warm conventional caching and checked alternatives already match. | Stop using this as the main route to a higher invention score. |
| Shared conditional spare capacity across plans | Reduce simultaneous physical holds where fault demands are correlated | Pooled conventional reservations, robust matching and the same fault assumptions; static per-plan reservations are a weak control. | Defer until a nonstandard enforceable interaction is specified. No score awarded. |
| Repair during concurrent writes with bounded version-log retention | Preserve useful staging without unlimited log/version storage | Ceph delta/log/vector design, DDUC, PARIX, CURM and mixed-version patent lead. An optimized journalled baseline may reproduce the full behaviour. | Backup research direction; high implementation cost and heavy overlap. No novelty inference. |
| Compact feasibility proof | Reduce planning/evidence size under changing capacity/fault inputs | Cached tables, incremental solvers and resource-aware plan checking. | Needs a concrete proof representation and completeness argument before implementation. |
| **Joint repair and whole-zone reclamation** | Account for physical capacity that deleting individual fragments cannot release; handle coding protection while clearing zone blockers. | **RetainZ-style placement, acknowledged GC, and a joint capacity/rank-aware conventional planner**, all with the same hints, pins and budgets. | **Selected for a short bounded research gate**, because it exposes a real missing physical assumption and reuses the prototype. Research value is the reason for selection, not a claimed higher chance of grant. |

The selected hypothesis is an incarnation-bound reclaim frontier coupling repair-stage adoption, source/pin closure and zone reset admission. It must do more than predict retirement or copy live data before reset. The [plan](../../RCSD_PRISM_C_Redesign_Plan.md) specifies the missing mechanism, equal baselines and stop criteria. It is **not implemented or established as novel**.

## 6. Indian filing requirements and remaining facts

Novelty, inventive step and industrial applicability remain separate requirements. [IP India basics](https://ipindia.gov.in/basics-of-patents) provides the general requirements. Current [official guidelines index](https://ipindia.gov.in/resource/patents-resources-guidelines), reopened today, lists **CRI 2025** and its annexures; its 2026 site upload dates should not be confused with a new CRI guideline version.

The [2025 CRI guidelines](https://ipindia.gov.in/storage/uploads/docs-operator/7fdd559b-1ff8-4a87-8c36-033e7356b39b.pdf), PDF pages 35 and 39–40 (printed page numbers), discuss technical solution/effect, efficient storage, resource allocation and error correction. They do not impose a universal novel-hardware requirement. Concrete storage operation helps technical-character analysis; it does not establish novelty or inventive step. [Section 3(k)](https://ipindia.gov.in/acts/patent-act-1970/section-3) remains relevant to programs per se and algorithms.

[Section 10](https://ipindia.gov.in/acts/patent-act-1970/section-10) requires an adequate operational description, the applicant's best method and clear supported claims. A prototype is not a universal filing prerequisite; evidence must support the actual asserted contribution and scope.

The repository was observed public on 12 October; its earliest public date is unknown. Earlier human disclosures, an earlier filing, claim-specific support and human inventorship/entitlement are unknown. Record facts in [disclosures](../records/disclosures.md), [contributions](../records/contributions.md) and [priority support](../records/priority_support.md). Public sharing could materially affect novelty depending on those facts; no conclusion that priority is already lost is made. AI-generated suggestions do not establish a person's inventorship. No application has been filed by this work.

## 7. What would justify 70+

The previous **73/100** remains a historical illustrative target. For the redesigned subject matter, a new illustrative scenario is **75/100**: novelty 17/25, inventive step 15/25, technical character 18/20, substantiation 13/15, applicability 5/5, claim support 4/5 and priority evidence 3/5. Arithmetic totals 75. **These points are not awarded, a forecast, or a guarantee.** An adverse disclosure or close claim can reduce the outcome irrespective of experiments.

Reassessment requires: an exact claim-level distinction from the closest single disclosure; a credible answer to the strongest known combination; an attributable technical interaction under equal resources; meaningful comparative evidence or another well-supported technical-effect argument; sufficiently enabled narrow claims; and documented human/priority facts. Performance percentages are project screens, not statutory tests.

**Current decision:** preserve the useful prototype, replace the exhausted invention hypothesis with a short falsifiable research gate, and defer final filing-readiness conclusions until a concrete contribution survives that gate. The current updated value is **55/100**.
