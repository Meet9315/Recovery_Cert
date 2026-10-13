# RCSD-PRISM-C: next research plan for joint repair and whole-zone reclamation

Version 0.1 — 13 October 2026. Status: **conditional research design; implementation pending**. Current interim readiness: **55/100**, from the [dated reassessment](evidence/results/PATENT_REASSESSMENT_2026_10_13.md). Historical target: 73/100. Revised illustrative scenario: 75/100 only if new evidence justifies it; neither target is an assessed score.

## 1. Change the technical question

The current store treats slots as individually reclaimable. Investigate storage whose physical reclamation unit contains multiple fragments: a zoned device can require a whole-zone reset before old written space becomes appendable again. The existing slot ledger cannot be presented as a verified implementation of that physical contract.

Research question: **Can a specific representation of the joint repair/reset dependencies safely reduce the cost of selecting and validating a reclamation route, while keeping exact physical headroom and erasure-code protection, compared with an equally capable conventional controller?**

This replaces attempts to obtain fewer stages than the completed minimum-work optimum in the old fixed-LIVE slot grammar. Both controllers receive the new physical grammar. Changing media or obligations alone is not invention evidence.

## 2. Hypothesis and claim boundary

Working term: **generation-bound reclaim frontier**. This is a hypothesis about dependency representation and admission, not a finished algorithm or a new patent name.

For each candidate zone reset, derive a complete set of blockers: live/retained extents, staged receipts, active source pins, outstanding worker grants and coding/placement obligations that removing those extents would affect. Bind this frontier to zone incarnation/write pointer, authoritative extent membership and the relevant plan/coding/policy generations.

A proposed repair-stage adoption may satisfy some blockers by establishing a valid replacement or an allowed coding-row substitution. Advance the frontier and plan in one authoritative commit only after bytes and placement are verified. Issue reset only after every blocker is resolved, all affected grants are revoked/drained, and the stated protection contract holds. Uncertain reset outcomes remain physically charged until an identity-bound acknowledgement or authoritative device reconciliation establishes the outcome.

**Possible technical distinction to investigate:** a sound dependency representation that incrementally certifies joint coding and reset eligibility under blocker changes with less total work than competent conventional incremental tracking. The full operational details, completeness proof, complexity and distinguishing claim language are still missing. These are tasks, not accomplishments.

Pins, membership guards, copy-before-delete, reset generations, ordinary resource reservations and attaching a certificate are known foundations. If the frontier is just the conventional dependency index under a new name, reject the invention hypothesis. If an ordinary optimized controller can use the same representation without a substantive distinction, its benefit cannot be assigned exclusively to PRISM.

## 3. New physical contract

Start with immutable objects and the existing coding profiles. Use one authority, trusted workers and simulated domains for the initial model. Do not add concurrent content writes, distributed authority, Byzantine responses or device power-loss claims to this gate.

| Record | Required meaning |
|---|---|
| Zone | Device/domain identity, incarnation, aligned capacity, committed write pointer, open/active state and reset-intent identity. |
| Extent | Zone, offset, aligned length, immutable fragment identity/content epoch, coding row, state and receipt identity. |
| Membership | Authority-derived complete extent membership; detecting an inserted extent/pin must not depend on a caller-provided incomplete list. |
| Hold | Exact appendable destination budget and any open/active-zone token, attributed to a plan/fence. |
| Retention/grant | All relevant source pins and materialized/pending worker intents, with persistent revocation state. |
| Frontier | Derived dependencies plus version/incarnation guards; reconstructible from authoritative state after a cache loss. |
| Reset receipt | Intent and zone incarnation, resolved physical result and the new append position; stale identity cannot credit capacity. |

`logical retired bytes != immediately appendable bytes`. Logical deletion changes retention; it does not rewind a zone write pointer. Capacity becomes reusable through valid appendable tails or a confirmed reset. Count relocation and staging writes, temporary copies, stranded dead bytes, unused/finished tails, metadata/journal cost and open/active-zone resources for both paths.

No future reset is credited merely because a plan expects it. First acquire actual headroom for any required move. Completion is conditional on healthy storage, fair scheduling and the exact admitted fault model. A new fault invalidates affected evidence and may require replanning; do not inherit milestone 13's guarantee implicitly.

## 4. Worked capacity example and required negative cases

Illustrative geometry: three zones A/B/C, four aligned extent units each, all already written to their ends. A holds three retired extents and one pinned source; B holds four retained extents; C holds four retained extents. There are three logically retired units, **zero appendable units**, and no resettable zone. A two-unit staged repair cannot be admitted on those three “free” units. Moving A's source also needs actual headroom. This example is a specified model case, not a measured prototype result or a candidate advantage.

With a fourth empty four-unit zone D, reserving one unit for a checked replacement may make A resettable after source transfer and grant drain. A's four units become available only after reset acknowledgement. Whether copying that same row or reconstructing another permitted row is better depends on the explicit protection contract and costs. A global conventional planner gets both choices. There is no assumed numerical saving.

Required cases include: all-dead zone; dead extents with one source pin; dead extents with an outstanding worker grant; stale reset receipt; inserted extent after frontier creation; lost append/reset acknowledgement; takeover before reset acknowledgement; insufficient open-zone tokens; domain failure during the plan; a pinned source needed by a different plan; a purported replacement with duplicate coding row or invalid placement; and exhausted search returning UNKNOWN without admission.

Reset must not occur while live bytes are needed for protection or retained-object reads. Every retained object must return exact original bytes after repair/reclamation and recovery.

## 5. Competent comparison, including the recent work

The [RetainZ paper](https://arxiv.org/html/2610.05554v1), submitted 4 October 2026, already uses retirement conditions for zoned placement and compares policies with common admission, journals, copying GC and resource budgets. Reuse those comparison principles; do not claim its results as ours. Its exact deployment scope differs from EC repair, but “retention-aware placement” cannot be our distinction.

[ZenFS](https://github.com/westerndigitalcorporation/zenfs) supplies established lifetime grouping/reset context. [US20220261170A1](https://patents.google.com/patent/US20220261170A1/en) supplies a close zoned migration/EC context. Their mechanisms need explicit claim mapping alongside the earlier repair-reservation art.

| Comparator | Capabilities required |
|---|---|
| B0 — ordinary safe zoned controller | Authenticated relocation/staging, source retention, ordered reset and durable outcome accounting. Diagnostic control; never treat safety defects as advantages. |
| B1 — lifetime/retirement-aware placement | Same hints, geometry, retained objects, GC reserve and admission budget; version-pinned RetainZ/ZenFS-derived design appropriate to the experiment. No claim of having integrated these systems yet. |
| **B2 — joint conventional planner** | Same repair/reconstruction/relocation/reset choices, coding floor, pins, worker revocation, partial work reuse and capacity budget. Add dependency indexes, cached guards and incremental repair/reset updates where useful. Primary mechanistic comparator. |
| O — independent bounded oracle | Exhaustive legal routes over the same finite grammar, exact physical-resource accounting and objective. Check feasibility/work optimum, not an artificially slow timed baseline. |
| Candidate | Same data-plane/physical checks; proposed frontier representation only. Include build, invalidation, rebuild, fallback and extra metadata costs. |

B2 is allowed every known optimization and all equal information. If it matches minimum physical work, narrow any remaining research question to demonstrable computation/metadata cost. Never claim fewer physical operations than an oracle optimum under the same objective. A B0/B1-only improvement is insufficient where B2 cheaply reproduces it.

## 6. Ordered tasks and evidence gates

This is a focused research sprint, not another unconditional production milestone. Estimates are effort ranges, not promised completion dates. Exit early on a decisive negative finding.

| Task | Deliverable | Dependencies | Estimate | Pass/stop decision |
|---|---|---|---|---|
| R14-A: mechanism/source screen | Element-by-element chart of RetainZ, zoned migration patent, reservations and candidate frontier; strongest combination objection; precise update algorithm and completeness argument. | This design | 1–2 focused days | Stop if no operational distinction beyond ordinary pin tracking, epoch guards and cached indexes can be stated. Current broad source screen is complete; this exact chart/proof is pending. |
| R14-B: physical finite contract | Zone/extent grammar, geometry, fault/admission rules, workload generator and frozen protocol; named negative cases. | R14-A survives | 1–2 days | Reject logical-free capacity accounting; unresolved assumptions block performance claims. |
| R14-C: baseline and oracle first | B2 joint planner plus independently implemented reference and smallest motivating example. | R14-B | 2–3 days | Prove the physical problem is real. If B2 cheaply supplies the proposed effect, stop the patent direction or identify a different precise representation before coding the candidate. |
| R14-D: candidate representation | Separate frontier build/update/checker; mutation histories; exact accounting and source hashes. | R14-C distinction remains | 2–4 days | Same feasibility/readback results as oracle, safe UNKNOWN and no hidden physical resources. Distinguishing cost must survive optimized B2. |
| R14-E: bounded durable adapter | Fresh isolated zoned-file emulator; write pointer/reset journal/receipt generation; real bytes; existing authority/worker semantics extended only through a reviewed interface. | R14-D passes | 3–5 days | Crash/receipt/claim tests pass and reset never destroys retained bytes. Emulator evidence is not hardware evidence. |
| R14-F: matched campaign | Registered paired repair+GC workload, foreground offered arrivals, sensitivity/negative cases and raw partial failures. | R14-E | 2–3 days collection/analysis | Test attributable benefit after including all costs. Failure cannot be relabelled success. |
| R14-G: platform and invention review | Version-pinned device emulator/native adapter, external reproduction, final narrow claim chart and human/priority records. | Technical gates survive | Separate estimate after platform choice | Reassess score and filing scope; if distinction vanishes, retain engineering and stop this candidate. |

Initial research requires roughly 4–7 focused days before a candidate build decision. Later stages are conditional. Current completed work is this reassessment, source screen, candidate selection and plan. No zoned controller, frontier proof, new comparison or device evidence has been completed.

Suggested future files, **not existing implementations**: `spec/zoned_repair_reclaim.md`, `experiments/zoned_reclaim_protocol.md`, `prism_c/zoned_model.py`, `prism_c/zoned_baseline.py`, `prism_c/zoned_frontier.py`, `prism_c/zoned_oracle.py`, and focused tests. Keep the new grammar separate until compatibility, authority transactions and physical receipt changes are verified. Preserve all old evidence and defaults.

## 7. Predeclare useful effects and attribution

Choose **one primary effect before collection**, after the bounded mechanism screen identifies it:

1. If the distinction is computational: at least 20% less total controller CPU for joint repair/reclamation than optimized B2, with equal work, integrity and admitted workload; report preprocessing, cache rebuilding and metadata cost.
2. If it changes placement/work selection: at least 20% fewer combined repair/staging/live-GC host-write bytes than the strongest comparable online baseline, at equal starting state, headroom, hints, fault contract and admitted workload. The independent finite optimum constrains this claim; if B2 matches, it is not a unique candidate effect.

Both require no correctness failures, no additional physical reserve that explains the result, no selective workload rejection, and no greater than 5% foreground p99 degradation under matched offered load. Analyze uncertainty with enough matched runs, registered workload strata and retained failures. These numbers are engineering screens, not legal requirements or current results. Do not select whichever primary metric looks best after measurement. Do not aggregate away a failed workload class.

For the finite gate, establish soundness/completeness under the declared grammar and report operation counts/evidence sizes across scaling inputs. Tiny wall-clock differences are not adequate proof of a useful CPU improvement. Include changes that force complete rebuild and cases where the candidate loses.

Ablations must remove frontier reuse while keeping data-plane enforcement, and remove the claimed repair/reset coupling while retaining ordinary reset safety. If a gain persists unchanged, the coupling is not its demonstrated cause. If B2 adopts a conventional optimization that removes the gain, keep the stronger result.

## 8. Alternative and stop conditions

If R14-A/C fails, do not repeat extensive cache benchmarks. The backup question is bounded-journal repair under concurrent writes, but it first needs a detailed primary comparison with Ceph delta/log/version handling, DDUC, PARIX, CURM and the unresolved mixed-version patent lead identified in the [assessment](evidence/results/PATENT_REASSESSMENT_2026_10_13.md). No novelty points are assigned to that backup.

Continue useful engineering if desired, with performance effects attributed accurately. For patent work, stop or seek a different original technical contribution if both hypotheses reduce to known optimized designs. The project can be a useful software/research result without supporting broad patent claims.

## 9. Conditions for a higher updated value

The illustrative **75/100** scenario is `17 + 15 + 18 + 13 + 5 + 4 + 3`; it is not promised. Actual reassessment can remain 55 or fall. Evidence must justify the changes, including a defensible claim distinction and response to the known combination. No preset number compels a reviewer to raise a score.

Record inventor contributions to any surviving mechanism, original conception/support, earlier filing and every public version. The existing public repository and previous user-authorized pushes are documented in [disclosures](evidence/records/disclosures.md). Publishing this plan does not create patent priority. A registered Indian patent agent should assess those facts and final supported claims; this work does not file or guarantee a patent.
