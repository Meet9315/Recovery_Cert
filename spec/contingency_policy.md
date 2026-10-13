# One-additional-failure continuation gate

13 October 2026. Finite research model and guarded existing-API demonstrations. This is not a new durable storage-authority admission guarantee or an established inventive distinction.

## Guarantee and assumptions

Begin with a degraded, well-formed immutable stripe group above its reconstruction floor. Before accepting a nonempty nominal repair route, demonstrate restoration for **one** failure from an explicitly enumerated set of currently online scoped domains, at **every committed action boundary before nominal completion**, including boundary zero. No failure is permitted after that one event for this contract. With no event, the nominal route completes normally. The completion target is all rows online plus no RESERVED/STAGED leftovers.

All slots in the complete modeled scope must remain exclusively owned, including unused spares; live sources must remain pinned. Other writers, corruption beyond the declared domain failure, changing placement policy/membership, further faults, indefinite unavailability of healthy storage and unfair scheduling are excluded. Actions are atomic in this model. In-flight worker operations, host/device failures, network partitions and power loss are outside this new guarantee. A declared failed extent is unavailable and stays charged until physical reclamation; no failure adds free capacity.

For the registered 4+2 example, five authenticated rows permit losing one source while retaining four decodable rows. Two distinct healthy spare domains are needed to restore all six rows when a source fails before the first action. Two slots in the same spare domain are insufficient. Four live rows cannot tolerate a declared source failure at boundary zero; initial safe recoverability and this stronger completion guarantee are separate requirements.

## Planner and artifact

`plan_contingency` explores a finite nominal action graph. A nominal state can progress only when every supported fault there has a checked fallback. After the single fault, the existing conventional minimum-work planner produces a complete exact-snapshot witness; no second contingency is promised. Search returns FOUND for a checked feasible root, not a globally minimum robust plan. Exhausted nominal, branch or coverage budgets return UNKNOWN without a policy. Known infeasibility applies only to the finite nonmigration grammar and explicit fault set; unresolved branch search cannot prove infeasibility.

The grammar retains initial online LIVE rows; allows reserve/stage/promote/reclaim, abandonment of initial pending allocations or offline LIVE rows, and at most one acquisition per slot beyond its initial incarnation. A branch starts its own finite grammar from the actual failed prefix. A branch can therefore replace a nominal allocation whose extent became offline, while a fresh branch allocation cannot be repeatedly abandoned and reacquired.

`ContingencyPolicy` binds the initial fingerprint, canonical failure set, nominal witness, version and `(cursor, failed_domain)` fallback witnesses in a digest. A serialized digest detects changes, but is not an authority signature or proof of genuine physical bytes. Independent checking remains necessary.

## Independent checks and reference

`check_policy` uses independent witness replay, not planner transitions or optimizer calls. It derives the required branch-key set from every precompletion boundary crossed with every declared domain. Missing, duplicate, extra or malformed branch keys reject. It checks immediate post-fault decoding safety, exact initial/terminal bindings, the finite action grammar, complete restoration and absence of leftover partial allocations for every route. A root that continues after completion is rejected. Root-terminal faults are outside the covered window, because resource claims would have been released.

`contingency_oracle` independently explores nominal actions through checker replay and uses exhaustive permutations of missing-row/slot assignments for post-fault feasibility. Its assignment oracle imports neither the minimum-work objective nor its branch-and-bound pruning. Fixed online LIVE rows stay put; partial rows may be safely abandoned and re-created, so this feasibility oracle need not preserve their work. Separate graph/assignment budgets return UNKNOWN. The registered matrix contains 72 states; it is not an unbounded proof for arbitrary groups.

## Strong conventional comparison

The conventional comparator gets the identical nominal schedule, complete scope ownership, failure set and minimum-work fallback planner. It prechecks and caches **every** alternative in a normal lookup table, with the same full failed-snapshot guard. It is not forced to wait for a fault and replan. The candidate selects from a checked policy bundle. Both can select a fallback with zero new planning calls; authority revision still independently rechecks installation and physical bytes. Equal capability/work provides no component-certificate advantage.

## Existing authority smoke test

The demonstration validates the client-held policy, then uses existing `admit_scoped` to own both spare slots and all source membership. An unrelated foreground admission cannot steal unused Y. At a covered boundary, it marks a domain offline, checks the complete failed snapshot, chooses the cached witness, and calls the existing `revise`/`execute` path. Old worker grants, receipts, source checks, claims, fences and physical authentication retain their existing semantics. The example checks original A/foreground bytes and charged failed extents.

The policy bundle is not journalled or enforced as a new authority-owned admission record. Restart recovery of that bundle and failures during physical I/O are not implemented by this gate. Existing process-fault regressions remain relevant to `revise`, but do not extend this policy's modeled failure window. New durable integration and a large confirmation campaign remain gated on a useful distinction against the equally capable conventional comparator.

```powershell
python -m prism_c contingency-gate --report evidence/results/contingency-gate-new.json
python -m prism_c contingency-demo --root tmp/contingency-new --report evidence/results/contingency-demo-new.json --storage-workers --validation-mode shadow --fault-domain D0 --cursor 2
```

Use fresh names. The demo's default scope is one 4+2 repair stripe plus unrelated foreground content; failure domains D0–D4/X/Y refer to simulated labels in one local store.
