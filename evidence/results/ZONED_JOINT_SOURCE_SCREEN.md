# R15 joint conventional model: focused source context

14 October 2026. This is engineering context, not a new novelty/family/FTO opinion. Earlier exact [R14 chart](ZONED_FRONTIER_SOURCE_CHART.md) and failure remain preserved.

| Primary source examined | Relationship |
|---|---|
| [Zoned Storage device overview](https://zonedstorage.io/docs/introduction/zoned-storage) and [NVM Express ZNS index](https://nvmexpress.org/specification/nvme-zoned-namespaces-zns-command-set-specification/) | Append-only zones, reset/finish and open/active constraints inform the model. Official index currently lists ZNS 1.5 (31 July 2026). No native compatibility/device test is claimed. |
| [WO2019231646A1, Garbage collection implementing erasure coding](https://patents.google.com/patent/WO2019231646A1/en), published 5 December 2019 | Abstract/claim 1 and description [0012] directly combine GC with producing erasure-coded fragments rather than an intermediate replicated extent. Different embodiment from the joint row-exchange model; nevertheless the broad GC+EC coupling is established published context. No complete family/prosecution review performed. |
| [FastPR](https://ieeexplore.ieee.org/document/9721141/), DOI 10.1109/TPDS.2022.3152817 | Earlier primary abstract review: coupled migration/reconstruction with matching. Supports conventional optimization context; not an exact anticipation of this finite grammar. |
| [ZapRAID](https://arxiv.org/abs/2402.17963), 2024 | Search surfaced the author abstract on log-structured RAID for ZNS and group-based layouts. Detailed GC algorithm not examined in this execution; retain as a further source lead, not a resolved claim chart. |
| [RetainZ v1](https://arxiv.org/html/2610.05554v1), 4 October 2026 | Prior pinned paper/source review remains applicable to retention-aware zoned placement. No RetainZ/native placement implementation is benchmarked here. |

Another reconstruction+GC lead, US20240152426A1, appeared in indexed publication text, but direct Google Patents retrieval failed. It remains unverified full-text material and supplies no exact claim finding.

The implemented A* objective search, uniform-cost oracle, preservation of known staging and safe retirement/reset ordering are described as **conventional engineering**. The separate GC-first control is deliberately more restrictive. A better result against that control does not defeat the equally capable joint baseline, create a new certificate advantage or change the assessment to 70+. Stronger technical novelty would need a concrete additional mechanism and an exact comparison.
