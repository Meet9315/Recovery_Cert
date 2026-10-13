# Milestone 11 — checked recovery revisions with a capable conventional baseline

The interrupted-recovery redesign is implemented within the trusted local prototype. It preserves acknowledged healthy staging, redirects failed-destination work, revokes old worker grants, transfers resource ownership atomically and rejects obsolete commands/receipts. **All 12 matched pairs show the same retained work and repair operations in conventional cached and selective modes. This hypothesis does not supply the missing comparative advantage in these fixtures.** No rating increase or performance target is earned.

## Implemented scope

- Conventional partial-state assignment with backtracking, safe abandonment of blocking allocations and explicit UNKNOWN on exhausted budgets.
- Independent finite BFS oracle and independent action replay; no global byte/time-optimal scheduler claim.
- Checked successor admission with immutable new witness, fresh plan identity, persistent lineage, exact request retries and additive database migration.
- Complete scope/claim transfer, authenticated retained STAGED bytes and padding, live source checks and old-intent drain/revocation before commit.
- `replan`, `revise` and `revision-demo` CLI commands. Saved proposals support exact retries after the parent becomes SUPERSEDED.
- Both coding profiles, local and separate-process worker paths, and all four validation modes. Defaults remain conventional cached and serialized reads.

The [contract](../../spec/plan_revision.md) explains fixed online LIVE rows, finite search grammar, failed capacity charges and cross-database fault behavior. Offline failure is a domain label in a local store; it does not simulate a physically inaccessible separate device. A PREPARED write without an authority acknowledgement is still RESERVED and is not adopted as authenticated staging. A precommit crash can leave externally revoked worker grants while the parent remains ACTIVE; retry the exact revision or take over and replan. No unbounded liveness, remote consensus or power-loss guarantee is asserted.

## Registered comparison and result

Implementation/protocol freeze: `cd46eb3caa64cf7a7fa80e5056c7f148e4d0a299`. The [protocol](../../experiments/revision_protocol.md) precedes collection. The [raw report](revision-advantage-milestone-11.json) saves all 24 stores, 12 pair orders, seeds 20261012–20261014, witnesses, events, ledgers, rejections, readback, script/protocol hashes and all 48 production/test hashes. This is an **untimed mechanism gate**, not a ten-pair CPU/latency confirmation.

Both controllers use the same conventional partial replanner and revision/resource/worker APIs. Every fixture interrupts two immutable 1025-byte repair objects after all reservations and the first healthy stage; X fails, Z is available, and one authenticated staged row survives. Every pair has identical witness digest, committed successor actions, retained staging, stage-byte counts, terminal fingerprint and offline charges.

| Profile | Path | Pairs | Retained STAGED rows per store | Successor actions | Committed stage extent/row bytes | Failed X remains charged |
|---|---|---:|---:|---:|---:|---:|
| 2+1 | Local | 3 | 1 | 5 | 1024 / 513 | 1024 bytes |
| 2+1 | Workers | 3 | 1 | 5 | 1024 / 513 | 1024 bytes |
| 4+2 | Local | 3 | 1 | 9 | 3072 / 771 | 1024 bytes |
| 4+2 | Workers | 3 | 1 | 9 | 3072 / 771 | 1024 bytes |

The 2+1 continuation abandons failed X, promotes retained Y, and reserves/stages/promotes Z. The 4+2 continuation additionally stages/promotes two surviving reservations, while retaining the earlier P stage. All three original objects, including foreground content, match exactly in every store. All stores reach the whole-store target with no active plans. Extent/row counts are not total physical I/O measurements and omit repeated unacknowledged writes. Fault/race regressions cover those cases separately.

The independent [actual-fixture oracle](revision-oracle-milestone-11.json), using [this script](../../experiments/check_revision_oracle.py), finds shortest continuations of 5 and 9 actions after 20 and 1732 explored states. For these fixed-LIVE-row fixtures, the minimum number of stage actions is one and three: respectively two/four missing online rows minus one already authenticated staged row. Both conventional continuations attain those bounds. This is not a general minimum-I/O theorem or arbitrary migration result. The script records its own/input hashes and commit identity; it supplements rather than changes the registered paired collection.

**Gate decision:** reject retained-work revision as a selective-mode differentiator for these fixtures. A competent conventional journalled controller has the same capability. A larger timing confirmation is gated out; equality in work counts does not prove equality in CPU or rule out a different future mechanism. The earlier 20% isolated-verification CPU, 10% restoration/space and 5% foreground criteria remain unpassed. Physical revision enforcement was implemented as useful shared functionality under the user's request, not presented as a successful mechanism-difference result.

## Correctness, provenance and CI

The initial [full verification](verification-milestone-11.json) passed **143 methods and 360 subtests**, zero failures/errors, including **57 actual process-exit regression cases**: 41 retained and 16 new revision-boundary exits. The new exits cover both profiles × local/workers × after validation / after revocation / before commit / after commit. Tests also cover a live worker blocked at I/O, delayed receipts, corrupt staging, stale snapshots/fences, competing claims, concurrent duplicate revisions, repeated lineage and CLI proposal retries/migration.

The initial 10,000-trace campaign retains 2479 initial configurations, 3772 states, 46282 transitions/cache-reference comparisons and 92564 malformed-generation checks, zero violations. The independent 4+2 campaign retains 65536 field products, 15 generator minors, 180 reconstructions, 720 finite cases, 840 cache/reference and 840 stale-generation checks, zero disagreement. The new 40-case partial-state matrix finds zero UNKNOWN or feasibility/checker disagreements. These bounded checks are not all concurrent histories or hardware faults.

The [initial source CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38290394279) passed on Ubuntu and Windows. A preceding historical [Windows run](https://github.com/Meet9315/Recovery_Cert/actions/runs/38287271570) failed one CPU-attribution test because a short process-CPU interval measured zero. The test incorrectly required a positive duration. Commit `4c33efe13c2ed7d0ece795a995060658ab97ae5f` changes only that test: it now injects a zero clock, verifies actual outer call counts, exact zero duration, non-overlapping categories and controller bounds. No production timing, acceptance threshold, measurement or collected pair changes.

The [final verification after that correction](verification-milestone-11-final.json) passed **143 methods / 360 subtests**, zero failures/errors, all 57 process-exit cases, 1000 legacy traces, the full independent coding campaign and the 40-case partial matrix. All **48 source/test hashes** match current files and the final demonstration. The earlier 10,000-trace report is preserved; this reduced repeat checks the corrected test and whole suite without discarding the larger campaign. [Final source CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38291360181) also passed **Ubuntu and Windows**; [saved conclusions](ci-milestone-11.json) bind those jobs to `4c33efe13c2ed7d0ece795a995060658ab97ae5f`.

Production hashes remain identical across frozen collection and final source; only `tests/test_measurement_diagnostics.py` differs. The [final 4+2 shadow/worker demonstration](revision-demo-milestone-11-final.json) records current hashes and exact readback. The earlier [2+1 shadow demonstration](revision-demo-milestone-11.json) is retained as pre-freeze smoke evidence; its CLI source hash predates the final proposal-output update, so it is not described as matching final verification.

## Patent/research interpretation

The [refreshed primary-source chart](REVISION_PRIOR_ART_REVIEW.md) records related reservations, atomic reconfiguration, recovery journals, idempotent backfill, partial reconstruction and current 2026 repair-efficiency work. It does not establish anticipation of every exact element or exhaustive novelty clearance. Proposal and execution-plan amendments point to the implemented scope and negative mechanism gate. Human inventorship, disclosure history, priority, legal eligibility and final claim review remain UNKNOWN.

The earlier **53/100 assessment is unchanged**; **73/100 remains an illustrative conditional target**. The next research requirement is a specific technical distinction with an explained advantage that survives a competent baseline and primary prior-art comparison. More implementations of shared conventional capabilities do not satisfy that requirement.

## Reproduce

Use fresh stores/report names to preserve these records:

```powershell
python -m prism_c verify --report evidence/results/verification-revision-new.json --traces 10000 --seed 20261011
python -m prism_c revision-demo --root tmp/revision-new --report evidence/results/revision-demo-new.json --profile 4+2 --storage-workers --validation-mode shadow
python -m experiments.audit_revision_advantage --report evidence/results/revision-advantage-new.json
```

The oracle script consumes the frozen milestone 11 paired report and saves its dedicated oracle report; preserve/rename that oracle report before rerunning. There is no novel-effect confirmation campaign to reproduce for this rejected work-retention hypothesis.
