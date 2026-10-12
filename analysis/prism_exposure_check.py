"""Small mathematical check of PRISM-X section 8, not a storage prototype.

Assume an MDS (4,6) code with authenticated distinct valid fragment rows.
Fixed physical failure universe: loss of rack R1..R6 and device D0..D5.
Losses are unions, so selecting a device in the failed rack adds no loss.
Before repair D5 has no valid fragment. A candidate adds its fragment on
R1 or R6. No existing valid fragment is removed and policy is unchanged.
"""

import itertools
import json


def exposed(layout, scenarios):
    return {
        (rack, device)
        for rack, device in scenarios
        if sum(r != rack and d != device for d, r in layout.items()) < 4
    }


def main():
    scenarios = list(itertools.product(range(6), range(6)))
    before = {device: device for device in range(5)}
    on_r1 = {**before, 5: 0}
    on_r6 = {**before, 5: 5}
    initial, colocated, separate = [
        exposed(layout, scenarios) for layout in (before, on_r1, on_r6)
    ]
    result = {
        "scenario_labels": len(scenarios),
        "initial_unprotected": len(initial),
        "r1_candidate_unprotected": len(colocated),
        "r6_candidate_unprotected": len(separate),
        "r1_strictly_reduces_exposure": colocated < initial,
        "r1_meets_final_target": not colocated,
        "r6_meets_final_target": not separate,
        "r1_remaining_scenarios": [
            {"rack": f"R{r + 1}", "device": f"D{d}"}
            for r, d in sorted(colocated)
        ],
    }
    assert (len(initial), len(colocated), len(separate)) == (20, 4, 0)
    assert colocated < initial and separate < initial
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
