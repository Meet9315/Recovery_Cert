# E16: durable zoned-file engineering delivery

14–15 October 2026. **Implemented and verified the bounded serialized file embodiment**, following the user's next-step instruction. This is conventional engineering after R14's failed invention gate. Current previously assessed readiness remains **55/100**; conditional 73/75 targets remain unearned.

Registered source: [`402b2cb63ea0c37454932f47a1b054c5b75fb6ad`](https://github.com/Meet9315/Recovery_Cert/commit/402b2cb63ea0c37454932f47a1b054c5b75fb6ad), committed/pushed before final collection. [Contract](../../spec/zoned_file_store.md), [frozen protocol](../../experiments/zoned_file_protocol.md), [raw file comparison/faults](zoned-file-e16.json).

Corrected-source freeze: [`d87264102c2f66569cb7a1fe6a3306ef056e7558`](https://github.com/Meet9315/Recovery_Cert/commit/d87264102c2f66569cb7a1fe6a3306ef056e7558). [Recollected raw file/fault evidence](zoned-file-e16-r2.json) reproduces every result under the corrected path test plus E17 measurement source. The actual E16 adapter is unchanged; original reports/failed CI remain intact.

## Results

| Observation | Outcome |
|---|---:|
| Declared profile/staging/headroom/pin/eligibility cases | 32 |
| FOUND / INFEASIBLE | 12 / 20 |
| Independent feasibility/minimum-work disagreement | 0 |
| Fresh actual joint/control file stores | 24 |
| Exact file readbacks across action prefixes | 280 |
| Strictly fewer stage bytes than restricted separated GC | 2 cases |
| Equal stage-byte cases | 10 cases |
| Separate search-exhaustion probes | 2 UNKNOWN/no witness |
| Registered actual process exits | 32 |
| Noncorrupt outcomes resumed to exact target | 28 |
| Partial/invalid writes conservatively quarantined | 4 |

Both profiles' tight/staged fixtures use **64 committed stage bytes/eight actions** for the joint controller versus **128 bytes/fourteen actions** for restricted GC-first. This is actual file materialization, beyond R15's RAM execution. The other ten feasible cases have equal stage bytes. All routes use identical authority/file code and starting resources; bootstrap bytes are excluded and separately recorded. Full metadata/fsync/read/retry costs, write amplification and foreground timing are not measured by this byte count.

The strong **conventional joint planner** obtains the better routes and matches the independent finite objective reference. The separated control has additional restrictions. These results are not a candidate-specific advantage, new novelty finding, G6 performance pass or reason to award a higher patent score.

Twenty infeasible cases are retained with `physical_execution=false`. No runnable witness/store is invented for them. Budget exhaustion is UNKNOWN, distinct from proof of infeasibility. Raw records retain all ledgers, receipts, cases, fault boundaries and deliberate corruption outcomes; collection reports success with no unexpected failure.

## Implementation and fault evidence

- Separate versioned SQLite authority and hashed zone files; immutable object/row commitments, exact plan cursor and unique receipts. Earlier slot-store APIs/defaults remain in force.
- Append intent committed before sequential byte I/O; authenticated complete writes adopted once after restart. Retired holes and finished tails remain unavailable. No original plaintext recovery fallback is stored.
- Partial/invalid pending writes persist quarantine, pending intent, reservation and cursor; no rewind, reset-as-rollback or free allocation. Healthy exact object reads remain available. Quarantine deliberately blocks further completion; four refusals are expected safety outcomes, not repair successes.
- Reset request retains old extent charge and open/active tokens. Physical reset is whole-file truncation/fsync in this emulator. Matching acknowledgement atomically publishes the new incarnation, released allocation, receipt and cursor.
- A serialized authority transaction protects source bytes through I/O. Takeover waits for active I/O and rejects an actor paused between prepared intent and the next byte transaction. Old duplicate reset cursors return saved receipts and cannot erase a reused zone generation.
- Source/staging corruption cannot publish a LIVE row. Additional tests cover fixed pins/grants, altered intent incarnation, two distinct objects, unknown formats and fresh-root protection.

The registered fault collection uses actual `os._exit(86)` at prepare/file/metadata boundaries for both profiles, plus deliberate invalid-row injection after an actual exit. It checks exact content before/after recovery, stale actor rejection, contiguous unique receipts, one committed stage and one reset generation advance. Partial writes remain 32 bytes and invalid full writes remain 64 bytes; neither is erased for retry.

Development focused verification: **14 methods PASS**, including **30 actual exits** (28 ordinary boundaries and two partial writes). These overlap the registered matrix and are not 62 unique fault scenarios. Initial developmental assertions/Windows handle cleanup were corrected before registration and described in the protocol.

## Verification status

Initial local full verification passes **200 methods/494 subtests** with zero failures/errors: [original verification](verification-e16.json). [Initial exact-source CI](ci-e16-initial.json) passes Ubuntu but fails one Windows assertion comparing the resolved `runneradmin` temporary path to the alias `RUNNER~1`; all other 199 methods pass on Windows. The expected-path assertion is corrected with `.resolve()`, with no adapter behavior change. Original reports and failed CI are preserved.

Corrected-source [full local verification](verification-e17.json) passes **205 methods/501 subtests**, no failures/errors, with 10,000 traces and all earlier campaigns. [Source CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38768388390) passes Ubuntu and Windows; [record](ci-e17.json), [Windows artifact](verification-e17-ci-windows.json). All 71 Windows artifact production/test byte hashes match local corrected-source file collection. This includes five new E17 measurement methods; CI verifies collector correctness but does not run/confirm the full timing pilot. Existing slot-store behavior remains unchanged.

## Task closure and next delivery

| Stage | Status / bounded support |
|---|---|
| E16-A | PASS: separate durable schema, identity/uncertainty contract and equal resource comparison |
| E16-B | PASS: real 2+1/4+2 files, sequential append, whole-zone reset and authenticated readback |
| E16-C | PASS in process-fault scope: 32 registered exits; conservative uncertainty, takeover and anti-stale checks |
| E16-D | PASS for complete declared matrix: 24 matched route stores, positive/parity/infeasible outcomes retained |
| E16-E | Instrumentation/diagnostic pilot delivered in E17; confirmatory complete-cost/foreground result remains PENDING |
| E16-F | PENDING: version-pinned native/device-emulator hook, external reproduction and final supported claims review |

E16-E instrumentation and registered diagnostic collection are now documented in [E17](E17_EXECUTION.md), with separate host-load context and a sequential follow-up. The next step is adequate-load/counter precision and confirmatory design, not declaring the pilot a timing-gate pass. A known scheduling gain over the restricted control cannot be promoted into a PRISM-specific result. Native hooks need device identity/write-pointer/reset-status reconciliation beyond an empty local file.

Single local authority, simulated domains and trusted files. No asynchronous zoned workers, cancellation, mutable content, device reset acknowledgement, native protection, directory/power-loss durability or external reproduction. Signed human contributions, ownership, earliest disclosure/priority support remain UNKNOWN as instructed; user reports no earlier application. This milestone does not file a patent or resolve those facts.
