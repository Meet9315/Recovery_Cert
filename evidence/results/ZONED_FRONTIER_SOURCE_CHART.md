# R14-A: exact mechanism/source comparison

13 October 2026. Primary paper/publication text was reopened; source files were retrieved through GitHub's API at immutable revisions and inspected locally. This is a technical element chart/combination objection, not an exhaustive legal claim, family, FTO or priority opinion. Exact gate contract: [reset frontier screen](../../spec/zoned_frontier_screen.md).

## Versions and material examined

| Source | Pinned material | Relevant evidence and limits |
|---|---|---|
| [RetainZ v1](https://arxiv.org/html/2610.05554v1), submitted 4 October 2026 | Full paper sections II–IV. [Source](https://github.com/DonaldLucy/RetainZ/tree/20195ab77a28e1fc3e0d0555cd6265a0b064148a), commit timestamp 4 October 2026; `src/retainz.cpp`, `src/summary_accounting.cpp`, `src/metadata.cpp` examined. | Placement uses retirement hints. `reset_zone` rejects live extents; `reset_zero` derives live usage. The aggregate variant caches written-extent summaries and rebuilds affected zones. Pin/grant/EC semantics of our diagnostic are not claimed to be in RetainZ. We inspect source, not reproduce its device evaluation. |
| [ZenFS](https://github.com/westerndigitalcorporation/zenfs/blob/919c2ebbcdc170525a9abffb8b61a3795b1e6ae5/fs/zbd_zenfs.cc), pinned HEAD retrieved today | `fs/zbd_zenfs.cc`, commit timestamp 3 February 2025. `Zone::IsUsed`, `Zone::Reset`, `ResetUnusedIOZones`. | Used-capacity tracking gates reset; reusable capacity is updated following backend success. A source revision timestamp is not a complete first-publication proof. This is not a full implementation/prosecution review and does not imply native execution of our protocol. |
| [US20220261170A1](https://patents.google.com/patent/US20220261170A1/en), published 18 August 2022 | Claim 1; FIGS. 10–11 description, including live-only migration, RAID rebuild/protection, reclamation and space-monitoring choices. | Zoned migration/rebuild/GC and protecting data across moves have direct disclosed context. Claim 1's dynamic switching is narrower/different from our index. Do not equate description overlap with complete claim anticipation. |
| [US20170160982A1](https://patents.google.com/patent/US20170160982A1/en), published 8 June 2017 | Distributed-transfer reservation description reopened; previous [revision source chart](REVISION_PRIOR_ART_REVIEW.md) retained. | Destination space reservation/failed-transfer handling supplies known resource-control context. No new detailed claim-family mapping beyond the relevant mechanism is asserted here. |
| Existing prototype | [Plan revision](../../spec/plan_revision.md), scoped worker ownership, [minimum-work contract](../../spec/minimum_work.md) and source at `7d66bcb166bf4df27bd03f257d2c40c17d1d5b98`. | Already implements guarded claims, pins, identity-bound acknowledgements and predecessor grant revocation for individually managed slots. It is our engineering comparator, not presumed independent prior art of an earlier supported filing. |

No third-party source is copied into tracked project code. Retrieved originals remain in the ignored research cache. The diagnostic is independently written Python; no ZenFS/RetainZ dependency or installation is added.

## Candidate element chart

| Proposed element | Closest inspected material / conventional construction | Surviving question |
|---|---|---|
| Derive reset blockers from retained extents | RetainZ live-extent check; ZenFS used-capacity condition. | Blocker membership completeness is necessary engineering, not yet a new mechanism. |
| Include pins and outstanding worker grants | Existing local controller's retention and revocation; ordinary per-extent reference/grant counts. | Sources above are not claimed to disclose all these exact fields, but adding already enforced references to the reset guard has a direct conventional construction. |
| Bind evidence to namespace/zone incarnation, revision and owner fence | Existing authority guards/fences; conventional generation-guarded index. | No specified distinct guard/representation algorithm. |
| Repair/adopt replacement before retiring source | Zoned migration/rebuild/protection description and existing checked successors. | A specific new coding/substitution protocol would need its own disclosure. The proposed frontier does not supply one. |
| Incremental updates rather than full blocker rescans | RetainZ aggregate variant's cached summaries; independently constructed ordinary counter updates. | Proposed frontier and counters both build in O(E), update a fixed number of classes and query with a constant-size guard. No reduced work established. |
| Wait for matching confirmed reset before crediting capacity | ZenFS backend outcome handling; existing acknowledged-reclamation contract generalized to a zone identity. | Durable uncertain-outcome recovery is not implemented by the in-memory screen. A certificate label alone does not add it. |
| Retention-guided placement or common reserve | RetainZ placement/common-admission controls and known transfer reservations. | Cannot be presented as the new contribution or withheld from the baseline. |

## Strongest combination objection and constructive response

Start from conventional zone usage tracking and safe migration/reset. Count retained extents and every enforced reference/grant, guard the index by authority generations, check coding/manifest protection at retirement, and retain physical charges until confirmed reset. This produces the same described reset frontier operationally without a specialized certificate. A zone need not rescan coding dependencies after an earlier safe retirement has removed them from the LIVE manifest; a failure or new reference invalidates/adapts the authoritative state independently.

The [specified algorithm and induction argument](../../spec/zoned_frontier_screen.md) make this objection concrete, and the [registered comparison](../../experiments/zoned_frontier_protocol.md) tests the index variants against full recomputation. We do not infer that every possible alternative is obvious, that one patent anticipates the whole protocol, or that RetainZ's checkpoint scope is identical to erasure-coded repair. **The current proposal does not articulate an operational distinction that defeats this construction.**

Consequently the paper mechanism gate calls for stopping this particular patent-directed build if the executable check agrees. A different original algorithm/protocol could reopen the gate, but none is supplied by renaming the same dependency index. Missing inventorship/priority facts cannot be resolved by this source chart.
