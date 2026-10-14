# R15 registered conventional joint-planning campaign

14 October 2026. Register source/protocol before final collection. Exploratory focused tests and the motivating fixture were run while developing the model; the expected effects are therefore informed by those pilots, not a blind preregistration. Preserve that distinction.

Purpose: complete the nominal engineering model/solver/reference after the failed frontier screen. [Contract](../spec/zoned_joint_model.md). No claim-specific candidate or native/durable adapter is being evaluated. Primary comparison is exact feasibility and lexicographic work optimum against independently implemented uniform-cost search/replay. A restricted GC-first control diagnoses the value of joint scheduling.

## Declared matrix

Profiles 2+1 and 4+2 × existing final-row staging yes/no × extra empty spare yes/no × victim source externally pinned yes/no × X eligible yes/no = **32** fixed cases. A has capacity two and is full with row 0/retired filler. Other source rows occupy full one-unit zones and are externally pinned. X has capacity one and is staged/full or empty. Optional Y is empty/capacity one. Require all rows restored with distinct eligible domains, and one appendable unit in A. Scope max-open/max-active is one each.

Expected finite feasibility: `not pinned and (X eligible or extra Y)`; 12 FOUND and 20 INFEASIBLE. Both solvers must settle all cases within 20,000 expansions or report actual UNKNOWN instead of calling the case proven. Expected strict stage-saving cases versus the restricted separated control: existing staging, no extra spare, eligible X and unpinned A, once per profile. The stronger conventional joint solver already gets this effect; it is not invention evidence.

For every FOUND case: compare exact optimum `(stage units, actions)` with the oracle, replay both witnesses through both interpreters, execute joint/control bytes in RAM, preserve both routes and all prefix readback counts/hashes. Record identical starting capacity/fault/placement budgets and the control's extra restrictions. Preserve failures and partial records; do not remove unfavourable cases. No timing/noise/CI percentile claim is made.

Deliberately run budgets zero and one on an unlocked feasible case; require UNKNOWN without an installable witness from both solvers. Meaningful regression tests additionally cover two-stripe competition, held tails, finish/active constraints, pending-reset token retention, pins/grants, row/domain faults, stale incarnations/scope and invalid geometry. These tests do not exhaust every configuration of the general finite grammar.

Final collection and full verification:

```powershell
python -m prism_c.zoned_campaign --report evidence/results/zoned-joint-r15.json
python -m prism_c verify --report evidence/results/verification-r15.json --traces 10000 --seed 20261011
```

Use fresh report paths. The runner records the source commit, production/test SHA-256 map and protocol hash. The full suite discovers the new matrix regression; CI covers it along with existing correctness/process regressions. Full-source CI is tracked separately. Leave historical reports and failed invention gates unchanged.

## Interpretation and next gate

A settled exact objective and RAM readback establish only the bounded engineering contract. A 50% stage reduction in two tiny model cases is not measured restoration/CPU/foreground performance or a 20% patent-contribution result. Current 55/100 remains unchanged absent a new whole-invention reassessment with a surviving distinction.

If this passes, the next engineering deliverable is a separately designed durable zoned-file emulator with a versioned on-disk schema, acknowledged append/reset outcomes and actual process-exit tests. It must not inherit the earlier slot adapter's durability guarantee automatically. Native device/external reproduction and a novel protocol remain unresolved.
