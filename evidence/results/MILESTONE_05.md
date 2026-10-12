# Milestone 5: versioned 4+2 coding and reconstruction

Verified locally on 12 October 2026, Python 3.11.4 / SQLite 3.42.0 / Windows. This is prototype correctness evidence, not a performance or patentability result.

## Implemented behaviour

The fixed `pq-4+2-gf256-v1` profile stores four data rows and two P/Q parity rows. Any four authentic rows reconstruct the immutable object; repair preserves a four-row safety floor and finishes at six distinct online domains. The original `xor-2+1-v1` profile remains the default. Planner, independent checker, conventional scheduler, both cache classes, durable storage and storage-worker preparation now use each stripe's immutable profile.

Profiles are covered by witness/cache/worker state commitments. Default-profile fingerprints preserve historical commitments. An additive SQLite migration and snapshot decoding support old stores; a test resumes a pending historical 2+1 worker grant after migration without rebuilding its valid cache. Profile downgrade, invalid row numbers, inconsistent extra rows, nonzero padding and corrupt sources reject. See the [coding contract](../../spec/coding_profiles.md).

## Verification evidence

The [full report](verification-milestone-05.json) records **96 passing test methods**, **288 subtests**, no failures or errors, and 147.26 seconds total. Source SHA-256 values cover all 24 package/test files and match the verified checkout. Eleven new test methods cover codec, storage, policy, workers, upgrades and failure recovery. Historical milestone reports are retained.

| Check | Observed result | Scope |
|---|---|---|
| Field multiplication | 65,536 products match independent polynomial arithmetic | Every GF(256) byte pair |
| Generator determinants | All 15 four-row minors nonzero | Fixed 6-by-4 P/Q matrix |
| Reconstruction campaign | 180 reconstructions match independent encode/recover oracle | All 15 subsets across 12 seeded lengths |
| Finite repair campaign | 720 cases: 60 feasible, 660 infeasible; zero disagreement | Two destinations with eligibility, offline and retired flags |
| Transition/cache checks | 420 actions, 840 cached/full suffix comparisons, 840 stale-incarnation rejections | Feasible finite repair cases; 810 distinct visited states |
| Durable reconstruction | Original content restored from all 15 initial four-row subsets | Real local preallocated byte pools |
| Domain erasures | Every two-domain failure combination recovers; third failure rejects | Simulated labels, six-row initial stripe |
| Local/worker validation | Restoration succeeds in full, conventional cached, selective and shadow modes | Both execution paths |
| Actual process exits | Four new 4+2 cases, 37 total across the regression suite | Worker fsync/journal and controller receipt/commit boundaries |
| Legacy model campaign | 10,000 traces, 2,479 distinct initial configurations, 3,772 distinct states, 46,282 actions/comparisons; zero invariant violations | Previously registered sequential 2+1 model; repetitions counted |

The independent coding oracle uses a separately written literal generator, polynomial multiplication and cofactor inversion; it imports no production coding/profile helpers. The finite repair capacity oracle uses the need for two distinct online eligible destinations. Production BFS and conventional matching both agree with it; no UNKNOWN result was relabelled as infeasible. These finite checks are not an unbounded proof or enumeration of arbitrary concurrency.

## Persistent demonstration

The [mixed-profile worker demonstration](four-plus-two-demo-milestone-05.json) starts A with 4+2 rows 0, 2, 4 and 5, then restores missing **data rows 1 and 3**. B concurrently restores its default 2+1 stripe using a disjoint scope. A retired destination is reclaimed before reuse. Ten interleaved actions produce four durable worker receipts (one reclaim and three stages). Shadow validation checks full-reference agreement; both original objects match after reopening, all claims are released and both stripes reach their targets.

The preserved local store is `tmp/four-plus-two-demo-milestone-05`, excluded from version control. Reproduce using a new root:

```powershell
python -m prism_c verify --report evidence/results/verification-milestone-05-new.json --traces 10000 --seed 20261011
python -m prism_c four-plus-two-demo --root tmp/four-plus-two-demo-new --report evidence/results/four-plus-two-demo-new.json --validation-mode shadow
```

## Interpretation and next work

The larger coding-profile correctness portion of E02 is now supported within this local embodiment. Its comparative-performance portion remains unmet: no controller-level CPU, foreground p99, repair-throughput or competent-baseline improvement was measured. Conventional caching remains the runtime default. P/Q erasure coding is an established technique; adding it earns no novelty points. The earlier 53/100 assessment and conditional 73/100 target remain unchanged.

Next engineering task: register and implement the controller-level comparison runner for both profiles, accounting for persistence, physical source/payload checks, worker preparation and receipt reconciliation against the same capable conventional cached baseline. Network authentication, independent devices and power-loss experiments remain separate outstanding work.
