# Milestone 10 — actual lost-receipt retry and scoped contention

The registered campaign completed all **40 paired runs / 80 measured repair groups**, plus eight retained warmups, without failed attempts. Both coding profiles recovered exact original bytes after an actual worker exit or during independent scoped-controller contention. **No configuration establishes either the 20% broad-CPU or 10% restoration proxy target versus conventional caching.** The foreground latency gate was not evaluated. The earlier **53/100 assessment and conditional 73/100 target remain unchanged**.

## Registration and implementation

The [protocol](../../experiments/fault_contention_protocol.md), CLI, benchmark-only instrumentation and tests were committed as `f3cacf3` before this campaign. The [raw report](fault-contention-milestone-10.json) records protocol SHA-256, environment and **41 source/test hashes**, all matching the frozen code and current files. No source/test changes were made after measurement began. Seed 20261012; ten measured pairs per configuration; randomized mode order; matched seeds, conventional repair witnesses, immutable bytes, 1024-byte slots and whole-stripe/disjoint-slot claims. One warmup per mode/configuration is retained and excluded from effect estimates. There was no outlier removal or replacement.

Both modes use production authenticated read-result reuse and the same opt-in snapshot content probes. Runtime authority, worker receipt format, physical authentication, fences, claims and defaults are unchanged. The new helpers instrument normal worker `handle` and authority APIs; telemetry remains separate from receipt authority.

Each store has two 1025-byte repair objects plus a fully protected foreground object. Stripe 0's repair destinations begin retired and require reclamation; stripe 1's destinations begin free. Source/destination domains are shared labels with disjoint scope slots, rather than independent hardware.

Lost-receipt retry uses one controller for both scopes. At its first stage, an actual worker calls `os._exit(77)` after committing its durable receipt and before returning it. The authority cursor and ledger stay unchanged; retry reuses the same prepared token, retrieves the committed receipt and completes through normal checked authority validation. This represents a lost worker acknowledgement and same-epoch retry, without controller restart or takeover.

Contention uses two separate controller processes released from a common barrier, one for each scope. **All 40 measured contention attempts have overlapping actual repair-step intervals**, retained with distinct process IDs. Both scopes reach their protection target and leave no active plans.

## Paired effects

Positive percentages indicate lower selective cost relative to conventional caching. Values are the mean paired percentage reduction and seeded bootstrap 95% interval, using all ten pairs in each cell.

| Profile | Scenario | Broad CPU reduction | Restoration wall-time reduction |
|---|---|---:|---:|
| 2+1 | Lost-receipt retry | −1.23% [−5.73, 2.71] | −2.03% [−3.59, −0.54] |
| 2+1 | Scoped contention | −0.68% [−8.37, 6.01] | 1.26% [−5.88, 6.92] |
| 4+2 | Lost-receipt retry | −11.41% [−33.92, 4.05] | −10.92% [−35.08, 4.96] |
| 4+2 | Scoped contention | 3.98% [−3.35, 12.65] | 1.43% [−9.46, 14.02] |

No point estimate meets the respective 20%/10% threshold, and no lower confidence bound meets it. The 2+1 retry restoration interval indicates a small slowdown in this sample; the other intervals include zero. The largest 4+2 retry observation, pair index 6, has 94.97% greater selective CPU and 101.95% greater selective restoration time. It remains included; its cause is unidentified. Bootstrap intervals from ten pairs are descriptive local evidence, without multiple-comparison adjustment or deployment extrapolation.

Wall time covers barrier release through collection of every controller result, including retry, snapshot content probes and result serialization. Broad CPU includes the timed parent, controllers after receiving the barrier, and every worker from process startup/imports through its operation. Worker diagnostic-file writing/teardown and controller result serialization CPU are excluded; their wall time is included. Fixture creation, worker initialization, planning/admission, controller startup/readiness and terminal audit are outside the timed restoration interval. Instrumentation and Windows CPU-clock quantization limit small-effect interpretation. This is not isolated verification CPU or the complete G6 metric.

## Fault, content and liveness evidence

The measured groups contain **40 actual worker exits**; retained warmups contain four more. Every exit has CPU telemetry and observed exit status 77. Every retry preserves the ledger/cursor and returns the exact durable receipt for its original token. All 80 reopened stores meet the coding target, have no active plans, conserve managed slot capacity and return exact original bytes for all three objects. **840 authenticated foreground probes** following repair actions pass. These sparse probes are correctness checks and cannot establish the 5% foreground latency gate.

Parent and controller 50 ms pulse threads retain monotonic, wall and process-CPU observations. No observed gap reaches 500 ms in any measured attempt or warmup. This bounds the recorded observation delays; it does not explain timing variation or prove continuous worker/device liveness.

## Verification and remaining work

The [full local verification](verification-milestone-10.json) passed **132 methods and 326 subtests**, with zero failures/errors and **41 actual process-exit regression cases** (37 retained plus four new receipt-commit exits). Its 41 source/test hashes match both current files and the timing report. Three new test methods exercise both modes/profiles, receipt-commit process exits, cursor/charge preservation, independent-controller restoration and retained failed registration outcomes. Existing physical-byte, stale-fence, corruption, coding-oracle and process-interruption regressions passed.

The 10,000-trace legacy campaign covered 2,479 initial configurations, 3,772 states, 46,282 validated actions/cache-reference comparisons and 92,564 malformed-generation checks, with zero violations. The independent 4+2 oracle checked 65,536 field products, 15 nonzero generator minors, 180 reconstructions and 720 finite repair cases, including 840 cached/full comparisons and 840 stale-incarnation checks, with zero disagreement. These are finite/local checks rather than unbounded or hardware-fault proofs.

The frozen source/protocol commit `f3cacf3e90e30d6dc57db9a7498a9ff48d884499` has been pushed to the authorized repository, and its [CI verification](https://github.com/Meet9315/Recovery_Cert/actions/runs/38276513209) passed on both Ubuntu and Windows. Each CI job runs the process-fault/integrity suite, 1,000 legacy traces and the independent coding campaign. CI does not repeat the manual performance experiment. Production/benchmark/test source is unchanged from that passing commit.

This adds bounded recovery/contention evidence without establishing a selective advantage, inventive interaction, independent-device durability or production readiness. G2 and complete G6 remain unresolved. Next, audit the strongest conventional baseline and worker-preparation/source-check costs, register a larger workload only where a specific useful advantage is testable, and collect fresh paired foreground confirmation with the same read improvements in both modes. Remote workers, actual host/device/power-loss evidence and the patent prior-art/claim assessment remain separate requirements.

Run fresh evidence into new paths:

```powershell
python -m prism_c fault-contention-benchmark --runs 10 --seed 20261012 --report evidence/results/fault-contention-new.json
python -m prism_c verify --traces 10000 --seed 20261011 --report evidence/results/verification-milestone-10-new.json
```
