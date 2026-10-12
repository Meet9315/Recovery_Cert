# Checked successors for interrupted recovery

The local immutable-content authority now supports retaining acknowledged staging and useful reservations while replacing a scoped recovery plan. This is a shared conventional capability. It does not establish a selective-validation performance advantage or novelty.

## Planner and checker

`conventional_partial_plan(state, max_states=20000)` assigns missing online rows to distinct eligible online domains and slots. It prefers matching STAGED, then matching RESERVED, then FREE destinations. Backtracking can discard previously completed staging when retaining it blocks another stripe's only feasible placement. First feasible matching is not a minimum-byte or minimum-time optimizer. Exhausted budgets return UNKNOWN. Exhausted assignment search returns INFEASIBLE only for the supported nonmigration assignment problem with existing online LIVE rows fixed. Unsafe input below the reconstruction floor rejects.

`partial_oracle` independently explores a finite action grammar by BFS. It can discard initial partial allocations or offline LIVE rows, reclaim, acquire each slot at most once beyond its initial incarnation, stage and promote. It does not migrate newly promoted LIVE rows. State/depth limits return UNKNOWN. Independent checker replay validates every resulting witness; model transition is a separate implementation. A 40-case single-stripe matrix covers both profiles and FREE/RETIRED/RESERVED/STAGED/LIVE destination states, offline status, and fallback eligibility. A separate blocking two-stripe example requires discarding staged work.

The new `abandon` action changes an exact RESERVED/STAGED allocation, or an offline LIVE row, to RETIRED without touching physical bytes. Online LIVE rows cannot be abandoned. Failed extents stay charged until a later successful physical reclaim; marking storage offline does not manufacture free capacity. Ordinary witness initial/terminal commitments remain exact.

## Admission and identity

`revision_snapshot(parent, destinations, fence)` projects the parent's complete stripe membership and the union of its old claimed slots and proposed destinations. Existing slots cannot be silently removed. Other active owners reject; legacy unscoped plans are not revised by this API.

Plan outside the writer lock, then call `revise(parent, witness, destinations, fence, request_id, expected_digest)`. In a writer transaction the authority checks the current fence, active parent, parent witness identity, complete claims, exact new snapshot and terminal, live physical source rows and any retained STAGED row's immutable digest and canonical padding. The new terminal cannot contain unowned RESERVED/STAGED allocations. Corrupt retained staging rejects; staging deliberately abandoned by the witness need not be adopted.

Before transferring resources, revoke all PREPARED parent worker grants and wait for their per-domain execution locks. A healthy in-flight write completes before revocation; its delayed receipt cannot advance the successor. RESERVED bytes written but not acknowledged are not treated as authenticated STAGED work and may need to be reconstructed again.

Commit a fresh successor identity, parent SUPERSEDED status, incremented lineage, complete scope, new cache and transferred claims/holds/source pins in one authority transaction. There is no visible unclaimed interval. All old plan commands and receipts fail to mutate the successor; old metadata step replay is rejected even at earlier cursors. Each successor still binds a complete exact witness; no terminal predicate is weakened. Source and promotion checks remain enabled in every cache mode.

Request identities are globally unique bounded strings. An exact duplicate returns its committed successor under the current fence; a changed payload rejects. Keep the saved proposal and request identity when retrying. Lineage is persisted in an additive table, leaving older plans and witnesses readable. Canceled, completed and superseded parent plans cannot create a fresh revision.

## Fault behavior

Actual process-exit regression coverage spans after validation, after worker revocation, before authority commit and after commit, for both profiles and local/worker paths: 16 cases. A precommit exit retains the parent's authority claims and status. A postcommit exit leaves exactly one successor; the same request recovers it.

Worker revocation commits in its own database before the authority transaction. An exit between those commits can therefore leave an ACTIVE parent with externally revoked grants. This is deliberately fail-closed. Retry the exact saved revision proposal; alternatively use takeover and replan under the new fence. Simply replaying the old revoked token is not a recovery procedure. No cross-database atomic commit, host-power-loss guarantee, remote worker protocol or independent-device failure claim is made.

## CLI

`revision-demo` creates a fresh interrupted store, fails X, preserves one staged row, substitutes Z, executes the successor and checks exact original bytes. It supports `--profile 2+1|4+2`, `--storage-workers` and all validation modes.

For an existing interrupted scoped plan:

```powershell
python -m prism_c replan --root <store> --plan <parent> --takeover --destinations Z:0 --report <proposal.json>
python -m prism_c revise --root <store> --plan <parent> --fence <current-fence> --proposal <proposal.json> --request-id <stable-request>
python -m prism_c resume --root <store> --plan <returned-successor> --fence <current-fence>
```

`replan` does not install the proposal; non-FOUND outcomes return exit status 2. The proposal includes the parent's witness digest, destinations and complete new witness. `revise` never replans implicitly, making exact proposal retries possible after the old parent becomes SUPERSEDED. The operator reads the current fence from `status` or uses the authority API takeover return value.
