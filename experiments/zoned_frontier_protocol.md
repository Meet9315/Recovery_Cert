# R14-A frontier/counter comparison protocol

Registered before evidence collection, 13 October 2026. See [contract](../spec/zoned_frontier_screen.md), [source mapping](../evidence/results/ZONED_FRONTIER_SOURCE_CHART.md) and [conditional plan](../RCSD_PRISM_C_Redesign_Plan.md).

Purpose: execute the early mechanism gate. This is not the later R14-F performance campaign. The algorithmic question is whether the specified blocker-set frontier supplies an eligibility/validation capability unavailable to ordinary indexed counters with identical guarded authoritative events. Independent full recomputation checks both. No timing metric is selected because the proposed operation bounds are already equivalent; a timed comparison against repeated full scans would handicap the competent comparator.

## Frozen matrix and mutations

One zone of capacity four units; 0, 1 or 2 extents. Each extent independently has state RETIRED/LIVE/STAGED, pins 0/1 and grants 0/1. Enumerate online/offline, held append budget 0/1 and pending reset present/absent. Includes deliberately inconsistent/adversarial admission snapshots, not a claim that every state is reachable from a correct durable authority. Expected initial cases: `(1 + 12 + 144) * 8 = 1256`.

Every case compares cold and warm reset decisions. For every case generate domain change, hold change, takeover, namespace replacement, zone-incarnation replacement and inserted live membership. Also replace every existing extent with every one of its 12 attribute combinations, including no-op logical values whose committed event still advances revision. Before each update both old guards must reject; after applying the same authoritative event both new decisions must equal the independent reference. Preserve all initial case records and counts. These are exhaustive one-event variations; sequential pin/grant drain is covered by separate regression tests. Do not label them exhaustive concurrent histories.

Expected totals are derived from the generator, not results: `8*6 + 96*18 + 1152*30 = 36,336` mutations, 72,672 stale rejections and 38,848 decision comparisons (2,512 cold/warm plus mutations). A disagreement fails the screen's correctness requirement. Zero disagreement verifies equivalence for these cases, not comparative timing or legal novelty.

Separate examples retain the three-logically-dead/zero-appendable-unit trap, zero credited capacity for an uncertain reset, four credited units only for a confirmed reset, and six finite coding-retirement positive/negative checks. Tests cover missing events, stale/duplicate tickets, takeover, late dependency changes, distinct-row rejection and invalid metadata. No physical data readback, real failure injection or solver-budget test is claimed; no repair optimizer is implemented here.

## Decision and exclusions

R14-A **fails the distinguishing-mechanism gate** if the conventional construction duplicates the proposed operation/coverage at the same asymptotic cost. In that case R14-B through R14-G depend on an unmet prerequisite. Mark them explicitly GATED OUT, rather than build a large candidate/durable adapter or represent them as completed. Retain the diagnostic as useful negative evidence. Final filing/ownership review remains unresolved; the technical gate cannot supply missing human facts.

Primary CPU/write/foreground thresholds in the later plan are not evaluated by this screen. No public claim of a 20% saving, hardware behaviour, native RetainZ/ZenFS execution, patent grant or score increase follows from these counts.

Run only after source/protocol registration:

```powershell
python -m analysis.zoned_frontier_gate --report evidence/results/zoned-frontier-gate-r14.json
python -m prism_c verify --report evidence/results/verification-r14.json --traces 10000 --seed 20261011
```

Use a fresh output path for recollection. Preserve the registration commit, source/protocol SHA-256 hashes, raw case records, test outcome and later CI status separately. The gate runner hashes its analysis module, regression file, contract and this protocol; ordinary `verify` hashes the production/test folders, so it does not silently cover the analysis module.
