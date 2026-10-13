"""Independent finite shortest-action oracle for the actual retained-work examples."""

import hashlib
from pathlib import Path
import subprocess

from prism_c.__main__ import environment, write_report
from prism_c.checker import check
from prism_c.model import State, Slot, Stripe, Witness, SearchStatus
from prism_c.partial_recovery import partial_oracle
import json


def main():
    root = Path(__file__).resolve().parent.parent
    source = root / "evidence/results/revision-advantage-milestone-11.json"
    paired = json.loads(source.read_text(encoding="utf-8"))
    cases = []
    for profile in ("2+1", "4+2"):
        raw = next(p["runs"]["conventional_cached"]["raw"] for p in paired["pairs"]
                   if p["profile"] == profile and not p["workers"])
        value = raw["initial"]
        state = State(tuple(Stripe(s["name"], tuple(s["eligible"]), s["profile"]) for s in value["stripes"]),
                      tuple(Slot(**s) for s in value["slots"]), tuple(value["offline"]))
        matched = Witness.from_dict(raw["witness"])
        result = partial_oracle(state, max_states=100000, max_steps=16)
        if result.status != SearchStatus.FOUND:
            raise AssertionError(f"Finite oracle did not settle {profile}: {result.reason}")
        check(state, result.witness)
        if len(matched.actions) != len(result.witness.actions):
            raise AssertionError("Matching example is not shortest in the finite grammar")
        live_missing = sum(spec.code.total_rows - len({s.row for s in state.slots
                           if s.stripe == spec.name and s.status == "LIVE" and s.domain not in state.offline})
                           for spec in state.stripes)
        acknowledged = sum(s.status == "STAGED" and s.domain not in state.offline for s in state.slots)
        lower_bound = live_missing - acknowledged
        actual_stages = sum(a.kind == "stage" for a in matched.actions)
        if actual_stages != lower_bound:
            raise AssertionError("Fixture does not attain fixed-live-row staging lower bound")
        cases.append({"profile": profile, "state": value, "matching_witness": matched.to_dict(),
                      "oracle_witness": result.witness.to_dict(), "oracle_states": result.explored,
                      "shortest_actions": len(result.witness.actions), "matching_stages": actual_stages,
                      "fixed_live_row_staging_lower_bound": lower_bound,
                      "scope": "Supported finite nonmigration grammar; fixed slots and online LIVE rows",
                      "global_minimum_io_claimed": False})
    report = {"environment": environment(), "cases": cases, "status": "completed",
              "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
              "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write_report(root / "evidence/results/revision-oracle-milestone-11.json", report)
    print(json.dumps([{k: c[k] for k in ("profile", "oracle_states", "shortest_actions", "matching_stages")}
                      for c in cases], indent=2))


if __name__ == "__main__":
    main()
