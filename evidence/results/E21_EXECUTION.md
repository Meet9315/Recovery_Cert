# E21 native-session authority and actual process-fault delivery

16 October 2026. **PASS within the declared continuous-session contract:** local and remote native campaigns, full local regression and all three source-CI jobs. [Registered 84-case protocol](../../experiments/native_authority_protocol.md), [contract](../../spec/native_session_authority.md), [final evidence audit](e21-evidence-check.json). This extends E20's actual NVMe codeword routes with a distinct opt-in journaled authority while preserving historical file-store behavior and all earlier evidence.

Implementation source [`49db8a156b1f62bb8399cdf1f5a979e19d5f2b09`](https://github.com/Meet9315/Recovery_Cert/commit/49db8a156b1f62bb8399cdf1f5a979e19d5f2b09). Prepared drafts were registered before activation. E19's source-bound timing campaign/audit finished before native runtime/test activation; no new native tests contaminate those measurements.

## Implemented behavior

`prism_c/native_authority.py` uses a new `prism-native-session-v1` SQLite WAL/FULL format, immutable code-row/content identities, one finite admitted plan, unique receipts and prepared native open/close/finish/stage/reset operations. Native bootstrap binds a fresh authority UUID to one continuous private supervisor session, controller serial, namespace/capacity map and boot ID; an incomplete bootstrap cannot reopen. Both 2+1/4+2 use 4096-byte code rows. Existing file-store APIs/formats are unchanged.

The serial supervisor owns the actual QEMU controller and survives authority actor exits. Requests carry store/session/token/fence identity. Takeover waits for the supervisor's prior-command completion barrier, then publishes the new database fence. Late old-fence RPCs are rejected before native submission. A SQLite lock alone is not assumed to drain a command already submitted by a dead actor.

Native reconciliation accepts only the prepared old/intended condition and position. Completed appends are authenticated against reconstruction from retained native LIVE sources, not plaintext fallback. Partial/unexplained writes quarantine and retain capacity; pending or unavailable outcomes expose zero appendable credit. Two aligned 2048-byte writes expose a real half-row fault boundary. Open/active tokens remain conservatively charged through uncertain outcomes. FULL/FINISHED pointer sentinels are handled as charged capacity. Repeated old cursors return receipts without reissuing I/O.

The initial six-method focused run reported two Windows cleanup errors: bootstrap SQLite context managers committed but did not close their handles. Explicit `closing(...)` fixes both paths. The corrected focused run passes all six methods. This was a resource-lifetime fix; failures are recorded here rather than represented as a clean first run.

## Completed native verification

Eight nominal routes keep their original repair/reclaim objectives. Diagnostic close/finish fault fixtures preserve the original tight route as a prefix but relax the final objective to repair-only because finish deliberately strands the reclaimed tail. They must not be presented as still satisfying the original reclaimed appendable-space goal.

The boundary matrix contains 66 actual process exits; four additional actors are killed after an explicit NVMe-submitted/unacknowledged marker, and four setup exits prepare altered-intent/session-loss cases. Total: **74 actual actor terminations in each 84-case campaign**. Delay is after a real submission doorbell and before observing completion; the emulator may internally complete during the delay. This tests an owner's unobserved completion, not a claim that the physical device remains busy for a specified duration.

Both the [local raw campaign](native-authority-e21.json) and [remote native CI campaign](native-authority-e21-ci.json) pass all 84 registered cases, with the following outcomes **per campaign**:

| Outcome | Cases |
|---|---:|
| Nominal original repair/reclaim target | 8 |
| Resumed to declared diagnostic target | 66 |
| Partial append quarantined with sources retained | 4 |
| Changed session identity rejected before I/O | 2 |
| Altered intent rejected without free credit | 2 |
| Lost session failed closed | 2 |

Each campaign contains **84 fresh sessions, 784 independently replayed committed receipts and 41488 successful NVMe completions**. The audit checks the complete 66-boundary matrix, both profiles/headroom/comparator routes, unique receipt identities, production/reference prefix agreement, no duplicate native append/reset, stale actor/raw-request rejection and conservative ledgers. It verifies all **84 archived operation shards** and all **four submitted-command completion/drain orderings** in each campaign: [local manifest](native-e21-operations/manifest.json), [CI manifest](native-e21-ci-operations/manifest.json). The local original `native-authority-e21-r1.json` is retained byte-for-byte alongside its canonical copy; there was no failed registered native collection.

[Full local regression](verification-e21.json) passes **224 methods/691 subtests**, 10000 model traces and all earlier finite/process campaigns, zero failures/errors. All **76 source/test hashes** match local native collection, remote native collection and both correctness artifacts: [Ubuntu](verification-e21-ci-ubuntu.json), [Windows](verification-e21-ci-windows.json). All 74 E19 runtime/test files remain unchanged. [All three source-CI jobs pass](ci-e21.json), including native ZNS. The [source workflow](https://github.com/Meet9315/Recovery_Cert/actions/runs/38866744648) uses 1000 model traces per correctness platform; it is not reported as 10000. CI is automated platform reproduction, not an outside human review.

Local collection uses WSL2 Linux 6.18.33.1, Python 3.10.12, SQLite 3.37.2 and QEMU 6.2.0; remote native CI uses Linux 6.17.0-1022-azure, Python 3.11.17, SQLite 3.45.1 and QEMU 8.2.2. [Backend build record](native-e21-backend-builds.json) identifies the exact package versions and observed local binary digest. The original E21 harness did not embed QEMU build metadata; local metadata was checked separately during collection, and the remote version is extracted from its completed job log. A remote QEMU binary digest was **not captured**, and no exact remote binary identity is invented.

Local native verification starts after the focused correction and before the implementation commit is created; its raw Git HEAD is therefore `6d4994680cae547465c4d9ddeb4cc6e8a256bcfb`, with the activated source in the working tree. No runtime/test/supervisor/harness edit is made during collection. All 76 byte hashes plus helper/protocol digests match the committed implementation and remote native CI; the earlier Git label is not presented as the implementation revision. This is correctness/fault verification, not a source-first performance campaign. Remote native CI runs from the exact `49db8a1` implementation checkout. [Reproducible audit helper](../../analysis/check_native_delivery.py) recomputes receipts, coverage, command log identities and source bindings rather than accepting the report's success flag alone. Run `python -m analysis.check_native_delivery` from the final evidence checkout. Historical E18/E19 audits bind their original 73/74-file source sets and were completed before E21 activation; do not run those old current-source assertions against this 76-file checkout or rewrite their raw reports.

## Scope that remains outside this contract

Supervisor/session loss fails closed; it does not establish automatic recovery after device recreation, VM loss or a physical power cut. Backing bytes and a reused serial do not certify persistent device write pointers/incarnations. Physical media/controller durability, independent outside reproduction, a distinguishing invention and human entitlement/disclosure facts remain unresolved. No native zone-append, distributed consensus, adversarial access control, mutable objects or dynamic cancellation guarantee is made. Patent-readiness remains **55/100**, not grant probability.
