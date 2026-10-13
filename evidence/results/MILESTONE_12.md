# Milestone 12 — minimum-work conventional recovery planning

13 October 2026. A real planner limitation was found and corrected: local first-feasible choices can discard staging unnecessarily. The new minimum-work conventional planner reduces committed stage writes by **50% in the 2+1 example and 25% in the 4+2 example**, while preserving exact content and failed-storage charges. **The stronger conventional baseline and selective mode do identical work in all 12 matched sets.** The saving is shared conventional functionality, not an established inventive advantage.

## Implementation and proof scope

`conventional_min_work_plan` uses bounded branch and bound to minimize `(stage_actions, total_actions)` over partial-state assignment with online LIVE rows fixed. A relaxed per-task objective bounds the remaining work; completed search proves the optimum in that assignment problem. Budget exhaustion returns UNKNOWN without an installable witness, including after finding a feasible incumbent. The existing first-feasible method remains available and remains `replan`'s default. `--planner min-work` opts into optimization; all validation modes receive the same planner.

The independent `min_work_oracle` searches model transitions using Dijkstra with cost `(is_stage, 1)`; it imports no assignment costs or pruning. Independent replay validates executable restoration. The [contract](../../spec/minimum_work.md) qualifies fixed LIVE rows, finite grammar, immutable authentic staging and uniform managed extents. This is not minimum total physical I/O, CPU, latency, peak capacity, or arbitrary migration. An external proposal's “optimality” annotation does not authorize a mutation; normal revision admission rechecks the actual state and physical bytes.

The minimal logical counterexample has A eligible for X/Y, B eligible for X/W, B already staged on X, retired Y and free W. First-feasible chooses X for A, discards B's work and writes two rows in eight actions. The minimum planner reclaims Y for A and promotes B:X: one stage, five actions. This choice is feasible under the same resource and source-floor contract.

The new 136-case matrix contains 96 two-stripe 2+1 states plus 40 single-stripe states across both profiles. Feasibility and optimum scores agree with the independent oracle throughout; no UNKNOWN occurs. Two first-feasible choices are suboptimal lexicographically: one needs an extra stage, the other performs extra actions at equal stage count. Input-order permutations, unsafe states and exhausted-incumbent tests supplement the matrix.

For a completed optimization over this enumerated assignment space, another scheduler cannot legitimately claim fewer stage/actions than the proven conventional optimum under the same objective and assumptions. This bound does not exclude faster planning/verification, UNKNOWN-budget cases, different physical costs, migrations or different fault contracts; those would need separate mechanisms and comparators.

## Registered real-store comparison

Source/protocol freeze: `2c98eab7579f28e8f578e4e9cb745cdb0510c099`. The [protocol](../../experiments/minimum_work_protocol.md) precedes collection. [Raw evidence](minimum-work-milestone-12.json) preserves all **12 matched sets / 36 stores**, rotated variant orders, seeds 20261013–20261015, complete witnesses/actions/events, ledgers, readback, independent oracles and source/script/protocol hashes. No failed attempt, UNKNOWN, outlier or variant was discarded.

Every parent reserves its original destinations and stages B:X before A's destination Z fails. A can use retired Y instead of consuming B's staging; B can instead use free W. The 4+2 fixture also has matching A:P and B:Q reservations. Each variant receives identical 1025-byte immutable A/B content, foreground content, 1024-byte extents, coding profile, eligibility, failure, claims, worker barriers and physical checks.

| Profile | Path | Matched sets | Old first-feasible work (stages/actions) | Minimum conventional | Minimum selective | Committed stage extent bytes: old → minimum |
|---|---|---:|---:|---:|---:|---:|
| 2+1 | Local | 3 | 2 / 9 | 1 / 6 | 1 / 6 | 2048 → 1024 |
| 2+1 | Workers | 3 | 2 / 9 | 1 / 6 | 1 / 6 | 2048 → 1024 |
| 4+2 | Local | 3 | 4 / 13 | 3 / 10 | 3 / 10 | 4096 → 3072 |
| 4+2 | Workers | 3 | 4 / 13 | 3 / 10 | 3 / 10 | 4096 → 3072 |

Unlike the minimal logical example, the real example also abandons failed Z, hence one additional action. The independent actual-fixture oracle explores 68 states for 2+1 and 17203 for 4+2, proving the respective 1/6 and 3/10 objectives in its finite nonmigration grammar. Both resolve FOUND; neither is omitted for a search timeout.

All 36 stores restore exact A/B/foreground bytes, reach the whole-store target and leave no active plan. Every failed Z extent remains charged RETIRED at 1024 bytes. Each minimum run preserves B:X without another stage to X and safely reclaims Y. The [4+2 shadow/worker demonstration](minimum-work-demo-milestone-12.json) independently records the same result. Source checks, staged authentication, promotion checks, fences, claims and worker revocation remain enabled.

Committed stage extents are operation counts multiplied by fixed extent size; they do not include all source reads, reclamation writes, duplicate unacknowledged worker writes or total network traffic. No timings are collected. Planning cost may offset copying savings. The existing 20% verification CPU / 10% restoration-or-space / 5% foreground targets are not passed by these percentages.

**Gate decision:** the primary baseline is minimum-work conventional, not the weaker first-feasible control. Its witness, action sequence, stage extent bytes, failed charge and terminal state equal minimum-work selective in every set. This corrects the planner and strengthens B1; it does not establish a component-certificate benefit. A large timing confirmation remains gated out for this hypothesis. The earlier 53/100 assessment and illustrative conditional 73/100 target remain unchanged.

## Verification and publication

Seven new focused test methods passed before source freeze. They cover the 136-case oracle matrix, twelve input-order permutations, optimization exhaustion after an incumbent, unsafe states, sixteen real-byte profile/path/mode cells, corrupt retained staging and explicit CLI UNKNOWN/optimum proposals.

[Full verification](verification-milestone-12.json) passed **150 methods / 388 subtests**, zero failures/errors, including the retained **57 actual process-exit regression cases**. The legacy 10,000-trace campaign retains 2479 initial configurations, 3772 states, 46282 validated actions/cache-reference comparisons and 92564 malformed-generation checks, zero violations. The independent coding campaign checks 65536 field products, 15 generator minors, 180 reconstructions, 720 finite cases, 840 cache/reference comparisons and 840 stale-generation checks, zero disagreement. The 40-case partial matrix and new 136-case minimum-work matrix both pass without UNKNOWN or disagreement. These remain finite/local checks, not all concurrent histories or hardware faults.

All **52 production/test hashes** match frozen comparison, demonstration, final verification and current files. [Source CI](https://github.com/Meet9315/Recovery_Cert/actions/runs/38356322593) passed **Ubuntu and Windows**, with [saved conclusions](ci-milestone-12.json) binding both jobs to the frozen commit. CI runs the entire regression suite, 1000 legacy traces and both coding/planner campaigns; it does not repeat the manual real-store collection.

All production/test source remains frozen during collection. [Focused primary-source screening](MINIMUM_WORK_PRIOR_ART_REVIEW.md) places this ordinary cost-aware repair optimization alongside established graph optimization, matching-based repair and cache-aware reconstruction scheduling; it is not exhaustive claim clearance. The next invention gate remains a precise distinction that survives that stronger comparator, rather than another favorable comparison against first-feasible planning.

## Reproduce

```powershell
python -m prism_c verify --report evidence/results/verification-minimum-new.json --traces 10000 --seed 20261011
python -m prism_c minimum-work-demo --root tmp/minimum-new --report evidence/results/minimum-new.json --profile 4+2 --storage-workers --validation-mode shadow
python -m experiments.audit_minimum_work --report evidence/results/minimum-work-new.json
```

Use fresh output/store names to preserve existing records. No production distributed or hardware-fault claim follows from these local fixtures.
