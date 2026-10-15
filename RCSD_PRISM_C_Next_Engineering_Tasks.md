# Next engineering delivery after R15

14 October 2026. R15's nominal model, joint conventional planner/reference and RAM execution are complete: [results](evidence/results/R15_EXECUTION.md). R14's frontier distinction remains failed. This is an **engineering** continuation, not approval of a patent candidate or new score.

**E16 implementation amendment — 14 October 2026:** The original next-delivery list below is retained. [E16 file results](evidence/results/E16_EXECUTION.md) now implement E16-A through D in the [bounded serialized contract](spec/zoned_file_store.md): 24 fresh joint/control stores, 280 exact file prefix readbacks, 28 recovered process-exit outcomes and four conservatively quarantined outcomes. Full regression/source CI collection is pending at this drafting stage. E16-E/F remain pending; no native/power-loss/performance/patent-score result is inferred.

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
