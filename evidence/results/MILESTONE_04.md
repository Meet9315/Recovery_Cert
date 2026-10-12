# Milestone 4: Durable local storage-worker boundary

Date: 12 October 2026.

## Outcome

The opt-in runtime now executes plan staging and reclamation in separate local storage processes, outside the authority writer transaction. Committed command intents authorize exact extents and incarnations; durable worker fences and revocation barriers prevent old commands from writing after takeover or claim release. The authority checks durable receipts, physical bytes and the current continuation before committing its allocation transition. All declared local correctness checks pass.

This completes I03 for the tested local process/worker scope. Domain labels and files remain on the same host. It does not establish independent hardware fault guarantees, a network deployment, useful performance advantage or a new patentability score. Default local mode remains available.

## Implementation and evidence

See the [worker protocol](../../spec/storage_workers.md), [worker process](../../prism_c/worker.py), [authority integration](../../prism_c/worker_authority.py) and [tests](../../tests/test_workers.py). The [verification report](verification-milestone-04.json) includes exact source hashes, per-test outcomes, runtime versions and the seeded campaign. The [worker demonstration](worker-demo-milestone-04.json) preserves state/ledger traces, commands' witness identities, rejection reasons, worker acknowledgements and original content readbacks.

| Check | Result |
|---|---|
| Full test suite | 85 methods passed; 155 reported subtests |
| New worker tests | 15 methods passed |
| Prior concurrency checks | Retained all 20 schedules of the two 3-step fixture |
| Validation modes with workers | Full, conventional cached, selective and shadow restored the same objects |
| Physical I/O separation | Another scoped plan completed while a domain worker held its I/O lock |
| Cancel/takeover barriers | Waited for in-flight I/O; revoked/fenced delayed commands before ownership release |
| Stale/altered receipts | Rejected without cursor advancement |
| Slot reuse | Canceled grant could not overwrite the reallocated extent |
| Duplicate stage controllers | One commit and one idempotent acknowledgement |
| Additional physical worker exits | 3: before I/O, after fsync, after worker journal commit |
| Additional controller exits | 4: after prepare, after receipt, before commit, after commit |
| Total process-exit cases across suite | 33, including the prior 26 cases |
| Sequential seeded campaign | 10,000 traces; 2,479 distinct initial configurations; 3,772 visited states |
| Selective/full suffix comparisons | 46,282; no disagreement |
| Observed campaign invariant violations | 0 |
| Persistent worker demonstration | Seven interleaved steps; three durable receipts from separate worker processes |
| Demonstration readback | Both original objects match; complete target reached; two conflicts rejected |

The three receipts represent one retired-destination reclamation and two fragment stage writes. The worker PIDs differ from the controller's PID. Receipt consumption remains atomic with cursor, cache and manifest state. Physical completion alone leaves the original RESERVED/RETIRED capacity charged until authority acknowledgement.

Cancellation and takeover races were exercised with a paused worker holding its domain lock. No timeout releases its claims. Worker receipt corruption and altered signatures are rejected by comparison with the trusted durable journal; corrupted acknowledged bytes reject rather than being silently rewritten. The local worker-control channel and databases remain trusted. There is no remote adversarial authorization claim.

The 10,000 model traces remain sequential and have their prior finite scope; they are not 10,000 worker fault scenarios. Preparation deliberately performs complete suffix replay, and completion repeats source/receipt checks. No new CPU, latency, foreground-impact or throughput measurements were made. Historical milestone reports are retained as evidence of their original scope and source version.

## Reproduce

```powershell
python -m unittest tests.test_workers -v
python -m prism_c verify --report evidence/results/verification-milestone-04-new.json --traces 10000 --seed 20261011
python -m prism_c concurrent-demo --root tmp/worker-demo-new --report evidence/results/worker-demo-new.json --validation-mode shadow --storage-workers
python -m prism_c status --root tmp/worker-demo-milestone-04 --plan A
```

Use a new/empty demo root. The preserved verified store is `tmp/worker-demo-milestone-04`; its runtime databases/secrets and pools are intentionally outside version control. Source and saved evidence reports are version controlled. GitHub Actions is configured for Python 3.11 on Ubuntu and Windows with a 1,000-trace CI campaign; remote CI status is separate from these completed local results.

## Remaining work

The next implementation task is a larger coding profile, beginning with a specified 4+2 code and independent reconstruction oracle before changing the fixed row predicates. Then perform controller-level comparisons that charge preparation, process launch, persistence, barriers, source checks and reconciliation. Worker loss during a partial multi-worker barrier fails closed and may reduce availability; network daemons, independent physical devices and power-loss evidence remain pending. The earlier 53/100 assessment and conditional 73/100 research target remain unchanged.
