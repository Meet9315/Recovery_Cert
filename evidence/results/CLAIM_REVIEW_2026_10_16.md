# Claim review and filing-review packet — 16 October 2026

Status: technical drafting and refreshed source screen; **not a filing-ready specification, novelty clearance or professional legal opinion**. No earlier application is reported by the user. Human contribution, ownership and earliest disclosure/claim-priority facts remain UNKNOWN under the user's instruction. No application is submitted by this work.

## Supported embodiment

The implemented system is a Python/SQLite single-authority recovery prototype for immutable erasure-coded objects, with trusted local processes, simulated failure domains and opt-in zoned-file emulation. The [persistent contract](../../spec/zoned_file_store.md) defines prepared append/reset intents, authenticated codeword/manifest identities, durable cursor/receipts, takeover fencing and conservative handling of uncertain physical outcomes. [E16](E16_EXECUTION.md) supplies byte/readback and process-exit evidence. The [nominal model](../../spec/zoned_joint_model.md) and independent oracle specify joint repair/reclamation under explicit capacity/open/active budgets. Process termination is not a power-loss experiment; files are not a native zoned namespace.

E18's added measurement tooling and any subsequent codec optimization must be distinguished from the inventive subject matter. Conventional joint/repeat arms are identical software. A shared codec improvement is ordinary implementation engineering, available to the strongest comparator.

## Narrow illustrative method and support chart

The following is a **claim skeleton for review**, not a representation that its combination is new. It intentionally describes only supported local behavior. An independent claim would need an established distinguishing interaction before filing. Claim language and statutory eligibility require professional review.

In a storage controller maintaining immutable erasure-coded objects and a persistent zone allocation ledger:

1. Store an object identity, coding profile, epoch, content digest and per-code-row digests; maintain zone incarnation, physical capacity and a persistent plan cursor.
2. Admit a finite repair/reclamation sequence only after checking protection and capacity/token constraints for its supported transitions.
3. Before a physical append, persist an operation identity binding the authority/store, cursor, pre-state, action, source epoch and target row digest to the target zone position/incarnation.
4. Materialize the code row, synchronize its file representation and authenticate the observed bytes before atomically recording the receipt, allocation transition and cursor advance.
5. After authority takeover, reconcile a prepared operation against its identity and physical representation. Adopt an exact authenticated completion; quarantine a partial, inconsistent or unexplained result while retaining its capacity charge.
6. Release a zone's capacity only after the supported reference/protection closure and an identity-matching whole-zone reset outcome have been reconciled; reject stale actor/incarnation operations.

| Limitation | Implementation/support | Evidence and scope | Novelty concern |
|---|---|---|---|
| Immutable coding/row authenticity | `prism_c/coding.py`; `ZonedFileStore.create`, `_read` and `_fragment` | Both coding profiles; retained corruption checks | Coding and digest validation are established components. |
| Joint capacity/rank-aware admission | `zoned_baseline.py`, `zoned_oracle.py`, `zoned_model.py` | R15 32-case bounded model; E16 real files | The conventional planner itself obtains the tested benefit. |
| Prepared identity-bound append/reset | `ZonedFileStore.advance`, `_apply_prepared` | E16 process-fault boundaries | Journalling, write-before-commit and guarded replay are known techniques; exact combination is not cleared. |
| Authenticated adoption/quarantine | `_geometry`, `_apply_prepared`, `_commit_action` | 28 resumed and four expected quarantined E16 outcomes | Conservative uncertain-write accounting is technically useful but no non-obvious distinction is established. |
| Reset closure/incarnation guards | Zoned model transitions; persistent intents/takeover | Serialized trusted authority only | Ordinary guarded counters matched the proposed frontier in R14. |
| Native reset/write-pointer reconciliation | Not established by file length/truncation | Native device/power-loss gate pending | Must not broaden the implemented claim to device evidence that does not exist. |

## Refreshed primary-source screen

Search/retrieval date: 16 October 2026. Queries cover zoned erasure repair/reclamation, uncertain writes, reset ordering, recovery and incarnation/reservation terminology. Earlier [source chart](ZONED_FRONTIER_SOURCE_CHART.md), [reassessment](PATENT_REASSESSMENT_2026_10_13.md) and claim reviews remain incorporated. This search is bounded and does not establish absence of other or unpublished art.

| Source | Material checked and public date | Relationship to the skeleton |
|---|---|---|
| [US20170123928A1, Storage space reclamation for zoned storage](https://patents.google.com/patent/US20170123928A1/en) | Published 4 May 2017; claims 1–4, 6–9 and reclamation description around Fig. 10–11. | Copies valid fragments/index changes before reclaim; dependent claim 4 resets write pointers. Description preserves source data on interrupted copying. Directly relevant to migration/reset/recovery, though the complete present intent-binding combination is not established in one claim. An abandoned application can still disclose relevant technical material; legal status is not an anticipation analysis. |
| [RAIZN, ASPLOS 2023](https://www.pdl.cmu.edu/PDL-FTP/Storage/RAIZN-kim.pdf), [author publication record](https://www.pdl.cmu.edu/PDL-FTP/Storage/RAIZN-kim_abs.shtml) | Publication record gives 25–29 March 2023. Paper section 4, page 6 orders zone resets after writes using a recorded reset pointer; section 5 describes parity persistence/crash-consistency challenges. | Reset ordering with in-flight writes and redundant zoned storage already has a concrete published construction. It does not by itself establish identical reservation/certificate semantics. |
| [US20220357859A1 / US11614870B2, Zoned memory device recovery after a key-value store failure](https://patents.google.com/patent/US11614870B2/en) | A1 publication 10 November 2022; B2 claim 1, dependent claims 3–7, method claims 8–14 and Fig. 5 description checked. | Uses device zone status to identify/recover non-filled zones containing uncommitted key-value data; resetting is a dependent limitation. Scope differs from erasure-coded immutable-row adoption; general status-based recovery is not a new distinction. |
| [RetainZ](https://arxiv.org/abs/2610.05554) | Existing chart examines v1, submitted 4 October 2026; primary abstract/submission record reopened in the refreshed search. | Retention/reclaim-aware placement and common admission are close context. This is not a newly discovered technical contribution of this project. |
| [Eliminating the Hidden Cost of Zone Management in ZNS SSDs](https://arxiv.org/abs/2511.04687) | Abstract/submission history; v1 24 October 2025, v2 18 April 2026. Detailed algorithms are not newly charted here. | Device-side zone-management costs are an additional comparison lead; abstract inspection is insufficient for a claim-level anticipation finding. |

The strongest engineering objection remains constructive: combine conventional protection-aware repair planning, durable operation journals, generation guards, reference closure and acknowledged reclamation. R14 tests an explicit ordinary-counter implementation and finds decision parity. R15/E16 give conventional scheduling the same scope and resources. Neither the new search nor more benchmark samples supplies a missing operational distinction. No exact single-reference anticipation of the entire skeleton is asserted; a non-obvious combination is also **not established**.

## India review boundary and evidence handoff

[Section 3(k)](https://ipindia.gov.in/acts/patent-act-1970/section-3) excludes programs per se/algorithms. The official [guidelines index](https://ipindia.gov.in/resource/patents-resources-guidelines) currently lists CRI 2025; upload dates are not guideline-version dates. The technical storage problem, physical byte actions and measured effects are the relevant factual disclosure; replacing software labels with hardware nouns does not establish eligibility or inventive step. [Section 10](https://ipindia.gov.in/acts/patent-act-1970/section-10) requires adequate description and supported, clear claims. This packet does not certify statutory compliance.

Review handoff consists of this skeleton/chart, current source, [progress](../../PROGRESS.md), all positive/negative raw experiments, source-bound verification/CI and [human contribution](../records/contributions.md), [disclosure](../records/disclosures.md) and [priority](../records/priority_support.md) records. Ask the reviewing professional to check exact distinguishing limitations, closest single reference and combinations, Indian/international families and non-English claims, sufficiency/best-method support, entitlement and public-sharing chronology. No instruction to send this packet to anyone is implied.

Current subjective readiness remains **55/100**, using the same rubric: novelty 11/25, inventive step 5/25, technical character 17/20, substantiation 13/15, applicability 5/5, claim support 3/5, priority evidence 1/5. Total 55. The new claim skeleton organizes existing support; no points are awarded for formatting or conventional optimization. This is not grant probability. Unknown human/publication facts can materially change a later assessment. A score above 70 requires new evidence resolving the actual distinction and associated support, not completion of every software task.
