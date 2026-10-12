# Milestone 3: Compatible concurrent scoped continuations

Date: 12 October 2026.

## Outcome

Multiple disjoint whole-stripe plans can remain active and progress independently through the local durable authority. Conflicting stripe/slot claims reject atomically. Completion, cancellation and cleanup preserve other plans' allocations and checked continuations. The implementation passes the stated correctness checks. Individual SQLite transactions and physical I/O remain serialized; independent storage agents and parallel physical throughput are not implemented.

This completes the scoped-plan portion of I03. I03 remains PARTIAL because its separate storage-worker portion is pending. No performance advantage, novel mechanism or new patentability rating is established.

## Implementation

- Derive complete membership from the authoritative state with explicit destination identities; callers cannot omit current sources or partial allocations.
- Acquire exclusive stripe and slot claim bundles with admission, source-byte checks and witness validation in one transaction.
- Apply full, conventional cached, selective and shadow validation to the same complete scoped projection.
- Preserve destination claims after reservation or reclamation, and report claimed FREE capacity as reserved until release.
- Recheck every claim and complete stripe membership before continued I/O.
- Release only the completing/canceled plan's claims, holds and pins; retire only its partial allocations.
- Allow exact-incarnation cleanup of unclaimed retired slots while other scoped plans remain active.
- Keep legacy full-store plans exclusive and support additive migration of existing active plans.
- Retain the global takeover fence, physical source checks, idempotent cursors and fsync boundaries.
- Add `concurrent-demo`, active-plan status and scope details to the CLI.

See the [scope specification](../../spec/concurrent_plans.md), [scope derivation](../../prism_c/scope.py), [authority](../../prism_c/storage.py) and [concurrency tests](../../tests/test_concurrent.py).

## Correctness evidence

The [verification report](verification-milestone-03.json) contains per-test outcomes, runtime information and source hashes. The [persistent shadow demonstration](concurrent-demo-milestone-03.json) contains witnesses, rejection reasons, ledger/state traces, acknowledgements and validation events.

| Check | Result |
|---|---|
| Full test suite | 70 methods passed; 139 reported subtests |
| New concurrency tests | 18 methods passed |
| Two 3-step plans | All 20 order-preserving schedules passed in durable stores |
| Runtime validation modes | Full, conventional cached, selective and shadow restored the same bytes |
| Simultaneous admission | Disjoint plans admitted; a shared destination produced one winner |
| Duplicate-step race | One application plus one idempotent acknowledgement |
| Independent controller processes | Both completed against the same local authority |
| Additional actual process-exit cases | 8 cases with another active plan; recovery completed both |
| Total process-exit cases across suite | 26, including the prior 18 cases |
| Seeded sequential model traces | 10,000; 2,479 distinct initial configurations; 3,772 visited states |
| Selective/full suffix comparisons in campaign | 46,282; no disagreement |
| Malformed-generation checks in campaign | 92,564 |
| Observed campaign invariant violations | 0 |
| Persistent concurrent demonstration | Seven interleaved steps, both objects recovered, two conflicts rejected |
| Demonstration cache reuse | No cache rebuilds or changed-component suffix replay; shadow still performed full reference replay |

The eight new interruption cases cover staging after fsync, before commit and after commit in conventional/shadow modes, plus reclaim after fsync in both modes. The other plan's durable cursor/state/claims survive. A separate test runs two controller processes; those controllers call the same serialized authority and are not independent storage daemons.

The 20 schedules are exhaustive only for that fixture's two fixed 3-action sequences. The seeded campaign is unchanged and sequential, not an exhaustive concurrency proof. Process exits do not establish power-loss durability, device failure independence or Byzantine safety. No new CPU, latency or throughput measurements were made.

## Reproduce

From the project root, with Python 3.11 or later:

```powershell
python -m unittest tests.test_concurrent -v
python -m prism_c verify --report evidence/results/verification-milestone-03-new.json --traces 10000 --seed 20261011
python -m prism_c concurrent-demo --root tmp/concurrent-demo-new --report evidence/results/concurrent-demo-new.json --validation-mode shadow
python -m prism_c status --root tmp/concurrent-demo-milestone-03 --plan A
```

Use a new or empty root for a new demonstration. The verified persistent store is `tmp/concurrent-demo-milestone-03`; no existing store is reset.

## Next engineering task

Specify and implement independent storage-worker commands and receipts, with durable fencing at the worker boundary, exact slot-incarnation identity, retry reconciliation and delayed/stale acknowledgement rejection. Moving physical I/O outside the authority transaction requires a new safety argument and fault tests. Merely launching more controller processes does not fulfill that requirement. Larger coding profiles, controller-level comparison and the claim/priority review remain pending. The earlier 53/100 assessment and conditional 73/100 research target are unchanged.
