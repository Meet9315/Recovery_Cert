# Next engineering delivery after R15

14 October 2026. R15's nominal model, joint conventional planner/reference and RAM execution are complete: [results](evidence/results/R15_EXECUTION.md). R14's frontier distinction remains failed. This is an **engineering** continuation, not approval of a patent candidate or new score.

**E16 implementation amendment — 14–15 October 2026:** The original next-delivery list below is retained. [E16 file results](evidence/results/E16_EXECUTION.md) now implement E16-A through D in the [bounded serialized contract](spec/zoned_file_store.md): 24 fresh joint/control stores, 280 exact file prefix readbacks, 28 recovered process-exit outcomes and four conservatively quarantined outcomes. Corrected-source full verification passes 205 methods/501 subtests and CI passes Ubuntu/Windows; the original path-only CI failure is retained. E16-E instrumentation is delivered in E17, but its confirmatory result and E16-F remain pending; no native/power-loss/patent-score result is inferred.

## Durable zoned-file emulator to implement next

1. Specify a versioned persistent zone/object/plan schema and exclusive single-authority scope. Keep it opt-in; never silently reinterpret old slot databases.
2. Persist immutable epochs/row digests, capacity/materialized positions, finished tails, holds/reservations, incarnations and plan cursor. Use controlled filenames, not arbitrary zone names as paths.
3. Journal identity-bound append intent before materialization. Retain capacity after uncertain completion. Recovery must inspect actual append position/authenticated bytes; partial/invalid appends consume retired capacity or quarantine the zone, rather than rewind it as if the write never happened.
4. Enforce source retention/grants through I/O. Start serialized under one authority; asynchronous workers require a separately specified fence/grant protocol.
5. Journal reset intent only after complete closure. Keep capacity/tokens charged until the matching incarnation/operation outcome is reconciled. No stale completion may affect a reused zone.
6. Atomically publish manifest, allocation/receipt result and cursor after required synchronization. Distinguish intent from physical acknowledgement. Power-loss/device/directory durability needs platform-specific evidence beyond process exits.
7. Resume by durable operation identity without duplicate appends/reset against a new incarnation. Specify cancellation/takeover/grant drain before exposing them.

## Verification order

| Stage | Required deliverable |
|---|---|
| E16-A | Durable states/schema, identity/uncertainty contract and equal conventional comparison. |
| E16-B | Actual 2+1/4+2 byte files; sequential append/whole-zone reset; no retired-hole reuse. |
| E16-C | Real exits around append/reset acknowledgements and metadata commits; exact readback, no overcredit/stale effects. |
| E16-D | Matched joint/control routes in fresh stores; actual repair/GC write bytes; positive/parity/failed cases preserved. |
| E16-E | Registered complete costs/foreground workload after correctness; include intent/index/fallback costs and strongest joint baseline. |
| E16-F | Version-pinned device emulator/native hook, external reproduction and final supported claim review. |

E16 was **not implemented/tested by R15**. Its later delivery is recorded in the amendment above. Uncertain-outcome handling is materially more than adding writes to a model. Existing storage defaults remain in force; the new file adapter is opt-in.

Readiness remains **55/100**. Patent-directed work still needs a specific mechanism beyond the joint conventional planner, fresh claim/source comparison, supported effects and human/priority facts. Unknown facts remain unknown; no filing/inventorship is inferred.

## Measurement work after E17 instrumentation

**E18 registration — 15 October 2026:** [New protocol](experiments/zoned_measurement_protocol.md) implements the next measurement steps below: scoped planning/admission/action profiles, a predeclared 4/6/8-group calibration ladder, actual-enqueue/CPU floors and ten matched three-arm sets per four configurations. Eight focused methods pass. Full-source verification and collection remain pending at this registration point. No E17 result is deleted or converted into confirmation; any future adequate conventional characterization is not a new candidate advantage.

The [registered cost pilot](experiments/zoned_cost_protocol.md) now implements the instrumentation portion of E16-E. [E17 results](evidence/results/E17_EXECUTION.md) and [collection context](evidence/results/E17_COLLECTION_CONTEXT.md) distinguish the initial shared-host-load pilot from the separate sequential follow-up. Both are descriptive, below confirmation sample floors.

1. Inspect all eight strata and identical-joint repeats before proposing a speed claim. Distinguish controller-thread CPU from whole-process/foreground CPU, and post-verification/bootstrap from the restoration interval. Attribute action costs with scoped diagnostic spans before naming a decoding, locking or metadata bottleneck.
2. Calibrate CPU batch precision and restoration backlog on disposable calibration stores. Save every attempt, including failed/insufficient ones. A merely nonzero/50-ms counter is not enough for a small relative-effect claim; the new confirmation protocol must set a larger measured CPU floor informed by observed clock increments and repeat variation.
3. Supply enough actual repair work for at least 1,000 foreground arrivals before restoration in every compared arm, with all completions retained. Increase a realistic fixed workload rather than insert artificial waiting. Freeze workload choices before confirmation; record the active-zone budget needed for retained partial zones.
4. Use at least ten complete matched sets per declared configuration, randomized saved order and the strongest conventional joint baseline. Register confidence/paired-effect analysis, complete controller costs and foreground criteria before outcomes. If no distinct candidate mechanism exists, report baseline characterization rather than invent a candidate advantage.
5. For any proposed scope/caching or read-concurrency optimization, explicitly preserve source/row authenticity, complete affected membership, physical append uncertainty, reset incarnation and takeover rules. Give the conventional controller the same ordinary optimization. Check against full reference validation and actual fault cases before performance collection.
6. Keep E16-F separate: choose and pin an actual device/emulator backend, implement authoritative write-pointer/reset-status/identity reconciliation, and run its supported failure model. Local file fsync/zero length does not establish native reset status or power-loss durability. External reproduction and supported claim review are additional outputs.

This measurement plan does not alter R14's negative invention finding or complete the original conditional filing plan. The remaining inventive contribution and human facts cannot be supplied by collecting more identical-controller timings.

## Profile-guided implementation after E18

**16 October status:** verification/profiles/calibration pass, but characterization is interrupted at 64/120 saved windows. [Execution record](evidence/results/E18_EXECUTION.md) and [checkpoint audit](evidence/results/e18-checkpoint-audit.json) preserve that partial attempt. Finish measurement through an explicitly declared continuation or separately registered fresh campaign before claiming a full E18 result. The codec work below is planned, not implemented; it must use a new source-bound calibration and cannot silently reuse the interrupted campaign.

E18's eight instrumented stores identify coding as the largest recorded action-phase elapsed category and model validation as the largest planning category. These are elapsed profiles with overhead, not isolated production CPU shares. Keep the ten-set conventional characterization separate from any implementation change.

The next concrete performance implementation should first strengthen the **shared conventional codec**:

1. Preserve the current 2+1/4+2 generator matrices, GF polynomial, row ordering, byte lengths and zero padding. Keep an independent bytewise/field-arithmetic reference and all existing object/row authenticity checks.
2. Investigate identity-row copies, precomputed per-coefficient byte translation and whole-buffer XOR to remove Python calls per byte in `coding.combine`. Python documents [256-byte translation tables](https://docs.python.org/3.11/library/stdtypes.html#bytes.translate) and [integer/byte conversion](https://docs.python.org/3.11/library/stdtypes.html#int.from_bytes); these support a standard-library implementation hypothesis, not a measured saving yet.
3. Check every field coefficient/value pair, all supported decoding bases, odd/zero-length/padded content, original/extra-row corruption and source/staged checks before performance collection. Preserve byte-for-byte old-store and historical witness compatibility. Do not remove decode consistency, regenerated-row digests or content checks for speed.
4. Give the faster codec to **all** conventional arms. Measure table creation/cold initialization separately, then complete controller and foreground costs under a new source-bound calibration. E18's selection cannot be reused across changed source. A codec speedup is shared engineering, not an inventive distinction.
5. Only after attributing the new costs, consider planner/model-validation optimization or transaction-local reuse. Specify full affected membership, source retention and authentication before adding a cache; compare with complete reference validation and fault tests. Separate read concurrency requires its own retention/fallback contract.

Conventional context: Intel's [ISA-L erasure-code header](https://github.com/intel/isa-l/blob/master/include/erasure_code.h) already exposes coefficient-table preparation and vector encode/decode operations. This is a current API context check, not a dated patent-anticipation assessment or a claim that the proposed Python implementation is novel. No ISA-L dependency/native binding is added by E18. A useful absolute improvement still needs comparison with the equally capable optimized baseline, and cannot by itself raise the assessed score above 70.

Native device/emulator execution, independent reproduction and supported final claim review remain separate requirements. Improving this prototype's codec will not supply unknown inventor/ownership/priority facts.
