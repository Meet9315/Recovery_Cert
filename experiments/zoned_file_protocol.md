# E16 registered zoned-file correctness/work protocol

14 October 2026. Register source, tests and this protocol in Git before final collection. R15's planner outcomes and work scores are already known, and pre-registration implementation checks are developmental tests, not an unseen hypothesis confirmation. Their first run exposed an overrestrictive reservation assertion and an unclosed test SQLite handle on Windows; both were corrected before registration. No registered failure may be discarded or favorable subset reported.

## Comparison

Use `python -m prism_c.zoned_file_campaign --root <fresh-root> --report <fresh-report>`. No overwrite of root/report. Save environment/source hashes, registered Git HEAD, protocol digest and all case/fault records. Preserve partial records and error if any collection fails. Runtime stores remain under ignored `tmp/`; final JSON evidence is tracked.

All **32 R15 combinations**: profile 2+1/4+2, staging present/absent, extra headroom present/absent, victim pinned/unpinned, target eligibility allowed/excluded. Independently implemented oracle and conventional joint planner must agree on feasibility and optimal `(stage units, actions)`; budget probes 0 and 1 must return UNKNOWN/no runnable witness. Preserve all infeasible cases with physical execution false; no store run is invented for a missing witness.

Every feasible case executes joint and restricted separated-GC witnesses in **two fresh file stores with identical bootstrap bytes, geometry, references and limits**. Check each witness with the independent model interpreter. Reopen and read exact content after every action; 4+2 also uses an independent coding reconstruction on actual LIVE file rows. Audit allocation/cursor consistency and compare the terminal state to nominal replay. Save all per-prefix ledgers and durable receipts.

Primary correctness pass: no oracle disagreement, byte mismatch, unsafe capacity release, unexpected receipt or invalid target. Work metric is actual committed stage bytes including relocation/repair; exclude bootstrap and record it separately. The two known tight/staged cases may save one unit versus restricted GC-first; other equal or failing cases remain in the report. This restricted control is not the strongest conventional comparator: the joint conventional controller itself obtains the improved schedule. No PRISM-specific advantage, statistics, latency or full write-amplification claim.

## Real process exits and uncertainty

For each profile use a fresh staged/tight fixture for every boundary:

- `stage` and `reset_ack`: before_prepare, after_prepare, before_io, after_io, before_commit, after_commit (12 cases/profile).
- `reset_request`: before_commit and after_commit (2/profile).
- `stage/half_io`: partial materialization (1/profile).
- `stage/after_io`: actual exit followed by deliberately injected invalid full row (1/profile).

Total **32 actual exits**, expected `os._exit(86)`. The 28 noncorrupt outcomes must recover under a new owner fence to the same exact target: one committed 64-byte stage, one reset generation increment, no duplicate physical append, unique contiguous receipts, exact contents. All stale actors must be rejected after takeover. Four uncertain outcomes must persist quarantine, retain intent/cursor/charge, preserve the file length, suppress all free allocation and retain healthy object readability; they are expected refusals, not repaired successes.

Separate focused tests cover source/staging corruption, takeover between journal and I/O, serialization during I/O/read, stale duplicate reset after zone reuse, altered intent incarnation, fixed pins/grants, finished tails/retired holes, fresh-root/format rejection, hashed paths and two objects with different contents. Focused tests independently include **30 actual exits** (28 recoverable + 2 partial); these overlap boundary definitions and are not added to the campaign as 62 unique scenarios.

## Verification and stop rules

Run full existing `python -m prism_c verify` after source freeze, with 10,000 traces and seed 20261011, preserving all old campaigns and process regressions. Source CI on Ubuntu/Windows uses existing 1,000-trace workflow; record its exact source SHA and jobs. Check protocol and every source/test hash against both evidence reports and current checkout. Do not alter old reports. Actual process exits are not power-loss tests.

Any registered disagreement or unintended publication/release blocks a pass conclusion; fix in a new source revision and preserve failed collection. Expected quarantine deliberately sacrifices liveness. E16-A through D pass only this bounded file scope. E16-E timing/full costs and E16-F native/emulator/external review remain pending. Patent score stays 55/100 absent a separate substantiated invention reassessment.
