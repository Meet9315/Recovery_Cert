"""Registered bounded engineering comparison; not the R14 patent candidate."""

import argparse
from dataclasses import asdict
from itertools import product
import json
from pathlib import Path
import subprocess

from .coding import digest, encode, recover
from .coding_oracle import oracle_recover
from .model import SearchStatus
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES
from .zoned_baseline import conventional_zoned_plan, separated_gc_plan
from .zoned_model import ZExtent, ZStripe, ZZone, ZonedState, replay, step
from .zoned_oracle import oracle_replay, zoned_oracle


def zoned_fixture(profile=DEFAULT_PROFILE, staged=True, extra=False, locked=False, eligible=True):
    n = PROFILES[profile].total_rows
    zones = [ZZone("A", "A", 2, (ZExtent("LIVE", "object", 0, int(locked)), ZExtent()), "FULL")]
    zones += [ZZone(f"B{i}", f"B{i}", 1, (ZExtent("LIVE", "object", i, pins=1),), "FULL") for i in range(1, n-1)]
    zones.append(ZZone("X", "X", 1, (ZExtent("STAGED", "object", n-1),) if staged else (), "FULL" if staged else "EMPTY"))
    if extra:
        zones.append(ZZone("Y", "Y", 1))
    domains = tuple(z.domain for z in zones if eligible or z.domain != "X")
    spec = ZStripe("object", domains, profile, profile == FOUR_PLUS_TWO)
    return ZonedState((spec,), tuple(zones), (("A", 1),))


def check_memory_bytes(initial, witness):
    """Replay real codeword bytes in RAM; not filesystem/device durability."""
    contents = {p.name: bytes((i + sum(p.name.encode("utf-8"))) % 251
                              for i in range(PROFILES[p.profile].data_rows * 64)) for p in initial.stripes}
    expected = {p.name: encode(contents[p.name], p.profile) for p in initial.stripes}
    physical = {}
    for z in initial.zones:
        for offset, extent in enumerate(z.extents):
            physical[z.name, z.incarnation, offset] = expected[extent.stripe][extent.row] if extent.stripe else bytes([165]) * 64
    def readback(s):
        for p in s.stripes:
            rows = {}
            for z in s.zones:
                if z.domain in s.offline:
                    continue
                for offset, e in enumerate(z.extents):
                    if e.status == "LIVE" and e.stripe == p.name:
                        data = physical[z.name, z.incarnation, offset]
                        if digest(data) != digest(expected[p.name][e.row]):
                            raise AssertionError("Materialized fragment identity mismatch")
                        rows[e.row] = data
            data, regenerated = recover(rows, len(contents[p.name]), p.profile)
            if data != contents[p.name]:
                raise AssertionError("Prefix object readback mismatch")
            if p.profile == FOUR_PLUS_TWO:
                subset = {row: rows[row] for row in sorted(rows)[:4]}
                if oracle_recover(subset, len(data)) != data:
                    raise AssertionError("Independent coding readback mismatch")
        return True
    current = initial
    readback(current)
    prefixes = 1
    for action in witness.actions:
        zone = next(z for z in current.zones if z.name == action.zone)
        if action.kind == "stage":
            p = next(p for p in current.stripes if p.name == action.stripe)
            rows = {e.row: physical[z.name, z.incarnation, offset] for z in current.zones if z.domain not in current.offline
                    for offset, e in enumerate(z.extents) if e.status == "LIVE" and e.stripe == p.name}
            _, regenerated = recover(rows, len(contents[p.name]), p.profile)
            physical[zone.name, zone.incarnation, len(zone.extents)] = regenerated[action.row]
        if action.kind == "promote":
            e = zone.extents[action.offset]
            if physical[zone.name, zone.incarnation, action.offset] != expected[e.stripe][e.row]:
                raise AssertionError("Promotion admitted wrong bytes")
        after = step(current, action)
        if action.kind == "reset_request":
            if sum(key[0] == zone.name and key[1] == zone.incarnation for key in physical) != len(zone.extents):
                raise AssertionError("Reset intent prematurely erased bytes")
        if action.kind == "reset_ack":
            physical = {key: value for key, value in physical.items() if key[:2] != (zone.name, zone.incarnation)}
        current = after
        readback(current)
        prefixes += 1
    if current != replay(initial, witness):
        raise AssertionError("Byte trace/model terminal mismatch")
    return {"prefix_readbacks": prefixes, "exact_contents": True,
            "object_sha256": {name: digest(data) for name, data in contents.items()},
            "stage_host_bytes": 64 * sum(a.kind == "stage" for a in witness.actions),
            "scope": "64-byte aligned units in memory; no disk/fsync/crash proof"}


def run_zoned_campaign(records=None):
    records = [] if records is None else records
    found = infeasible = savings = byte_prefixes = 0
    for profile, staged, extra, locked, eligible in product((DEFAULT_PROFILE, FOUR_PLUS_TWO), (False, True), (False, True), (False, True), (False, True)):
        initial = zoned_fixture(profile, staged, extra, locked, eligible)
        joint = conventional_zoned_plan(initial)
        oracle_status, oracle_witness, oracle_score, oracle_states = zoned_oracle(initial)
        expected_found = not locked and (eligible or extra)
        if (joint.status != oracle_status or joint.status == SearchStatus.UNKNOWN
                or (joint.status == SearchStatus.FOUND) != expected_found or joint.score != oracle_score):
            raise AssertionError(f"Independent feasibility/work mismatch: {profile,staged,extra,locked,eligible}")
        record = {"profile": profile, "staged": staged, "extra": extra, "locked": locked, "eligible": eligible,
                  "initial": asdict(initial), "status": joint.status.value, "score": joint.score,
                  "planner_states": joint.explored, "oracle_states": oracle_states}
        if joint.status == SearchStatus.FOUND:
            found += 1
            final = replay(initial, joint.witness)
            if oracle_replay(initial, joint.witness) != final or replay(initial, oracle_witness) != oracle_replay(initial, oracle_witness):
                raise AssertionError("Independent witness replay mismatch")
            control = separated_gc_plan(initial)
            if control.status != SearchStatus.FOUND:
                raise AssertionError("Separated control unexpectedly failed this declared fixture")
            oracle_replay(initial, control.witness)
            joint_bytes = check_memory_bytes(initial, joint.witness)
            control_bytes = check_memory_bytes(initial, control.witness)
            byte_prefixes += joint_bytes["prefix_readbacks"] + control_bytes["prefix_readbacks"]
            saves = joint.score[0] < control.score[0]
            savings += saves
            record.update({"witness": joint.witness.to_dict(), "oracle_witness": oracle_witness.to_dict(),
                           "control_score": control.score, "control_witness": control.witness.to_dict(),
                           "joint_bytes": joint_bytes, "control_bytes": control_bytes,
                           "stage_saving_against_restricted_control": saves, "terminal": asdict(final)})
        else:
            infeasible += 1
        records.append(record)
    probes = []
    for budget in (0, 1):
        initial = zoned_fixture()
        candidate = conventional_zoned_plan(initial, budget)
        reference = zoned_oracle(initial, budget)
        if candidate.status != reference[0] or candidate.status != SearchStatus.UNKNOWN or candidate.witness is not None or reference[1] is not None:
            raise AssertionError("Exhausted budget supplied an installable witness")
        probes.append({"budget": budget, "status": "UNKNOWN", "witness": None})
    return {"cases": len(records), "found": found, "infeasible": infeasible, "unknown": 0,
            "disagreements": 0, "strict_stage_savings_vs_restricted_control": savings,
            "byte_prefix_readbacks": byte_prefixes, "budget_probes": probes, "records": records,
            "scope": "Finite conventional joint model/planner and RAM byte replay; no durable zoned adapter",
            "patent_advantage_claimed": False, "rating_changed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    path = Path(args.report)
    if path.exists():
        raise ValueError("Use a fresh report path")
    from .__main__ import environment
    metadata = environment()
    root = Path(__file__).resolve().parent.parent
    metadata["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=root).strip()
    import hashlib
    metadata["protocol_sha256"] = hashlib.sha256((root / "experiments/zoned_joint_protocol.md").read_bytes()).hexdigest()
    records = []
    try:
        result = {"environment": metadata, "success": True, **run_zoned_campaign(records)}
    except Exception as error:
        result = {"environment": metadata, "success": False, "error": repr(error), "partial_records": records}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("environment", "records", "partial_records")}, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
