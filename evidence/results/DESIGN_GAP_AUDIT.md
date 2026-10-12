# The unfinished advantage: mechanism audit and the next redesign hypothesis

12 October 2026. The screenshot identifies the central unresolved question: what useful capability does this design provide beyond a competent conventional recovery controller?

**Finding:** the current successful execution paths do not expose an advantage from selective suffix replay. Conventional guarded caching already avoids that replay, and conventional scoping already isolates unrelated work. This is a structural limitation of the tested embodiment, beyond sample size or noisy clocks. It does not establish that every possible future embodiment must fail, or settle novelty. The 53/100 assessment and conditional 73/100 target remain unchanged.

## What was checked

The reproducible [untimed audit](../../experiments/audit_conventional_advantage.py) uses the independent replay checker, deployed caches and real authority/storage-worker APIs. [Raw evidence](conventional-advantage-audit.json) records the production Git revision, all 41 production/test hashes, the audit script hash and individual observations. Production and test source are unchanged from the milestone 10 revision verified by 132 methods/326 subtests and Ubuntu/Windows CI. This audit introduces no new performance estimate, fault-process count or regression-suite count.

| Probe | Observed outcome |
|---|---|
| Both profiles, 2/8/16 stripes; 273 paired logical steps | Conventional guard hit on all 273 steps; both cache modes replayed zero suffix actions during warm validation; independent full replay agreed |
| Eight real stores: both profiles × local/worker execution × both modes | 84 repair steps completed; all 42 conventional steps reused the guard; all 84 completion validations replayed zero suffix actions |
| Interleaved disjoint plans, annotations, an outside-scope outage, takeover and reopening | Both modes restored the selected scopes and exact original bytes; these events supplied no additional suffix-replay saving for selective mode |
| Four in-scope destination outages: both profiles × both modes | Both modes rejected continuation with unchanged cursor while original content remained decodable |
| Expanded eligibility, tested in the logical model | Independent replay still reached a safe target, but both modes rejected the old exact terminal commitment |
| Worker preparation in the real worker cells | 18 full remaining-suffix checks remained, nine per mode |

The outside-scope outage deliberately disables `F0` belonging to an unrelated foreground stripe. That stripe stays decodable but degraded, so the whole-store target is false. The two selected repair scopes meet their targets. This is an isolation probe, not complete-store restoration. The eligibility expansion is a model-only mutation: production currently has no policy-update API.

## Why the existing comparisons do not expose the proposed advantage

1. **A checked next step advances the conventional guard.** [WholeSuffixCache](../../prism_c/selective.py) compares the complete scoped state with its predicted state and updates that prediction after the independently checked transition. On that normal path it already replays zero suffix actions. Selective partitioning and merging cannot remove replay that is absent.
2. **Scope isolation is available to both modes.** [PlanScope](../../prism_c/scope.py) excludes unrelated stripes/slots and filters domain health to scoped membership. Another disjoint plan, an irrelevant annotation or an outside-scope outage leaves both controllers' relevant snapshot unchanged. Comparing selective scoping to an artificially global conventional lock would weaken the baseline.
3. **Changed components can still invalidate the whole committed witness.** A witness commits to an exact terminal fingerprint, including policy and health state. The policy probe shows that selective validation can replay less before rejecting, yet it does not authorize continued repair. Faster rejection could be useful in a separate workload; it has not been measured, and a conventional controller must also receive reasonable early rejection/dependency checks.
4. **Worker preparation still fully rechecks the suffix.** [prepare_worker_step](../../prism_c/worker_authority.py) does this before writing an intent, regardless of cache mode. Safely reusing already checked evidence there could improve ordinary controller efficiency in both modes; it would not by itself distinguish the invention.
5. **Planning/resource guarantees are shared.** The [conventional scheduler](../../prism_c/baseline.py) makes a capacity-aware assignment, while both variants use the same holds, pins, byte checks, durable intents and receipts. The easy greedy-placement and deletion-accounting examples therefore demonstrate functionality, rather than a comparative advantage.

For a successful next action following the admitted witness, the conventional cache's predicted state equals the actual scoped state after the previous checked action. Its guard consequently reuses the terminal result. Repeatedly scaling the same successful trace does not create a new replay-saving opportunity. Missing/malformed caches, changed policies, invalid states and new APIs are outside that simple argument; the audit does not claim a universal impossibility theorem or a proof about runtime complexity.

The current worker path also has ordinary repeated physical reconstruction/checking. Those checks remain required. Any safe optimization must be supplied equally to the strongest conventional comparator. A larger benchmark or another coding profile alone does not resolve G2.

## Chosen next hypothesis: revise recovery without throwing away valid work

**Hypothesis to investigate, not an established improvement:** after a destination failure or relevant resource change interrupts an admitted repair, a checked in-place plan revision can preserve already authenticated staging and unaffected reservations while replacing only the affected continuation. Its intended effect is less re-copied data and faster restoration under the same capacity/fault contract.

This addresses a capability missing from the current prototype. Today, the witness is fixed; relevant failure stops it, and cancellation retires its reserved/staged allocations. The conventional matching helper also rejects a nonquiescent initial snapshot. That helper limitation must be removed in the baseline before making any comparative claim. A conventional journalled replanner may obtain the same benefit. This audit does not assert that in-place revision, selective revalidation or preserving staged work is novel.

The revised witness should retain an exact commitment for its new revision. Do not simply ignore changed fields or accept a weaker old certificate. Independently check the new continuation from the authoritative current state, with the new destinations, current fault state, source identities and physical charges.

## Ordered work and decision points

| Step | Concrete deliverable | Required result before proceeding |
|---|---|---|
| 1. Freeze the interrupted-state contract | Specify retained LIVE/STAGED/RESERVED/RETIRED bytes, offline pools, source floor, target, plan revision, claims and worker revocation barrier | No free capacity before physical acknowledgement; no old command/receipt can gain authority after revision |
| 2. Strengthen B1 first | Conventional partial-state replanner with the same action vocabulary, staged-byte adoption, durable journal, reservations, source protection, scope/dependency tracking and read optimizations | Its capability matches the proposed controller; it is not forced to cancel/copy work unnecessarily |
| 3. Construct a decisive finite example | A feasible interrupted repair after one destination fails, with authenticated staging on a surviving destination, an eligible alternate slot and correctly charged failed/orphaned bytes | Independent oracle establishes feasibility and minimum required work/capacity; both variants obey the same failure and placement policy |
| 4. Check the proposed difference | Model a versioned revision that revokes/drains affected in-flight intents, retains justified staging/claims and atomically replaces checked continuation authority | An explained operation/cost difference survives the strengthened B1 and does not merely exploit its missing feature |
| 5. Implement real byte enforcement | Add the selected revision mechanism only if step 4 supports it; test old receipts, late writes, crash boundaries, failed physical pools and duplicate revision requests | No stale adoption, release of charged bytes or weakening of source/content validation |
| 6. Refresh comparison and claim hypothesis | Map the final mechanism to primary prior art; register matched workload, CPU attribution, restoration metric, foreground arrival load, seeds and ablations | A testable mechanism-specific effect remains; novelty is assessed separately from performance |
| 7. Confirm the effect | At least ten independent pairs per frozen cell, all failures/UNKNOWN cases retained, conventional and reuse-disabled controls | Meet the predeclared engineering criteria against the strongest B1; do not change the primary metric after results |

The existing plan proposes 20% verification-CPU improvement, a preselected 10% restoration/temporary-allocation improvement and at most 5% foreground p99 degradation. Broad process CPU is not interchangeable with isolated verification CPU. For this hypothesis, restoration time is the proposed secondary metric; record re-copied bytes and charged-space peaks for attribution. If a different primary effect is justified, revise the research protocol transparently before collecting measurements, without erasing earlier failed targets or awarding a rating increase automatically.

**Decision rule:** if the strengthened conventional replanner achieves the same retained-work behavior and there is no attributable useful difference, reject this hypothesis and revise the idea. Do not repeatedly run the same experiment, handicap the baseline or call routine optimization the missing inventive contribution. No winning redesign has been established by this audit.

## Reproduce

Use a new report path to preserve this evidence:

```powershell
python -m experiments.audit_conventional_advantage --seed 20261012 --report evidence/results/conventional-advantage-audit-new.json
```

The script measures mechanism counts and correctness outcomes, not speed. It runs temporary local stores and removes them after collecting evidence; raw pool data and worker secrets are untracked. New-revision feasibility, implementation, performance and prior-art support remain outstanding work.
