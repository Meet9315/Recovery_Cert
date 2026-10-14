"""Registered file-emulator comparison and real process-exit evidence, no timing gate."""

import argparse
from dataclasses import asdict
from itertools import product
import json
from pathlib import Path
import subprocess
import sys

from .coding import digest
from .coding_oracle import oracle_recover
from .model import Rejected, SearchStatus
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES
from .zoned_baseline import conventional_zoned_plan, separated_gc_plan
from .zoned_campaign import zoned_fixture
from .zoned_fault import EXIT_CODE
from .zoned_model import replay
from .zoned_oracle import oracle_replay, zoned_oracle
from .zoned_store import ZonedFileStore


def contents_for(initial):
    return {s.name: bytes((i + sum(s.name.encode("utf-8"))) % 251
                          for i in range(PROFILES[s.profile].data_rows * 64)) for s in initial.stripes}


def assert_bytes(store, contents):
    for name, data in contents.items():
        if store.read(name) != data:
            raise AssertionError("Exact file readback mismatch")
    state = store.snapshot()
    for spec in state.stripes:
        if spec.profile == FOUR_PLUS_TWO:
            rows = {}
            for zone in state.zones:
                if zone.domain in state.offline:
                    continue
                for offset, extent in enumerate(zone.extents):
                    if extent.status == "LIVE" and extent.stripe == spec.name:
                        with store.zone_path(zone.name).open("rb") as handle:
                            handle.seek(offset * 64)
                            rows[extent.row] = handle.read(64)
            if oracle_recover({i: rows[i] for i in sorted(rows)[:4]}, len(contents[spec.name])) != contents[spec.name]:
                raise AssertionError("Independent file coding readback mismatch")


def fresh_store(root, initial, witness):
    contents = contents_for(initial)
    store = ZonedFileStore.create(root, initial, contents)
    fence = store.takeover()
    store.admit(witness, fence)
    return store, fence, contents


def execute_route(root, initial, witness):
    store, fence, contents = fresh_store(root, initial, witness)
    assert_bytes(store, contents)
    prefixes, trace = 1, [{"cursor": 0, "ledger": store.ledger()}]
    for cursor in range(len(witness.actions)):
        store.advance(fence, cursor)
        store = ZonedFileStore(root)
        assert_bytes(store, contents)
        store.audit()
        prefixes += 1
        trace.append({"cursor": cursor + 1, "ledger": store.ledger()})
    if store.snapshot() != replay(initial, witness) or not store.audit()["target"]:
        raise AssertionError("File execution/model target mismatch")
    receipts = store.receipts()
    if len(receipts) != len(witness.actions):
        raise AssertionError("Receipt cardinality mismatch")
    seed_bytes = sum(len(z.extents) * 64 for z in initial.zones)
    return {"root": str(root.resolve()), "prefix_readbacks": prefixes,
            "exact_contents": True, "seed_bytes_excluded": seed_bytes,
            "committed_stage_bytes": sum(r["stage_bytes"] for r in receipts),
            "reset_operations": sum(r["action"]["kind"] == "reset_ack" for r in receipts),
            "object_sha256": {name: digest(data) for name, data in contents.items()},
            "receipts": receipts, "trace": trace, "audit": store.audit()}


def run_comparison(root, records):
    found = infeasible = savings = prefixes = stores = 0
    for index, (profile, staged, extra, locked, eligible) in enumerate(product(
            (DEFAULT_PROFILE, FOUR_PLUS_TWO), (False, True), (False, True), (False, True), (False, True))):
        initial = zoned_fixture(profile, staged, extra, locked, eligible)
        joint = conventional_zoned_plan(initial)
        status, witness, score, _ = zoned_oracle(initial)
        record = {"case": index, "profile": profile, "staged": staged, "extra": extra,
                  "locked": locked, "eligible": eligible, "initial": asdict(initial),
                  "status": joint.status.value, "score": joint.score, "physical_execution": False}
        records.append(record)  # Preserve incomplete/failed cases too.
        if status != joint.status or score != joint.score or status == SearchStatus.UNKNOWN:
            raise AssertionError("Independent file-campaign planner disagreement")
        if status == SearchStatus.FOUND:
            found += 1
            control = separated_gc_plan(initial)
            if control.status != SearchStatus.FOUND:
                raise AssertionError("Restricted comparison failed")
            oracle_replay(initial, joint.witness)
            oracle_replay(initial, control.witness)
            joint_route = execute_route(root / f"case-{index}-joint", initial, joint.witness)
            control_route = execute_route(root / f"case-{index}-control", initial, control.witness)
            if joint_route["committed_stage_bytes"] != 64 * joint.score[0] or control_route["committed_stage_bytes"] != 64 * control.score[0]:
                raise AssertionError("Actual committed work disagrees with declared unit objective")
            saved = joint_route["committed_stage_bytes"] < control_route["committed_stage_bytes"]
            savings += saved
            stores += 2
            prefixes += joint_route["prefix_readbacks"] + control_route["prefix_readbacks"]
            record.update(physical_execution=True, joint=joint_route, control=control_route,
                          joint_witness=joint.witness.to_dict(), control_witness=control.witness.to_dict(),
                          stage_saving_vs_restricted_control=saved)
        else:
            infeasible += 1
    probes = []
    for budget in (0, 1):
        result = conventional_zoned_plan(zoned_fixture(), budget)
        if result.status != SearchStatus.UNKNOWN or result.witness is not None:
            raise AssertionError("Exhaustion returned a runnable plan")
        probes.append({"budget": budget, "status": "UNKNOWN", "physical_execution": False})
    return {"cases": len(records), "found": found, "infeasible": infeasible,
            "disagreements": 0, "fresh_route_stores": stores, "prefix_readbacks": prefixes,
            "strict_savings_vs_restricted_control": savings, "budget_probes": probes}


def run_faults(root, records):
    recovered = quarantined = 0
    boundaries = [(kind, boundary, "recover") for kind in ("stage", "reset_ack") for boundary in
                  ("before_prepare", "after_prepare", "before_io", "after_io", "before_commit", "after_commit")]
    boundaries += [("reset_request", b, "recover") for b in ("before_commit", "after_commit")]
    boundaries += [("stage", "half_io", "partial"), ("stage", "after_io", "invalid")]
    for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
        for kind, boundary, outcome in boundaries:
            path = root / f"fault-{profile}-{kind}-{boundary}-{outcome}"
            initial = zoned_fixture(profile)
            witness = conventional_zoned_plan(initial).witness
            store, fence, contents = fresh_store(path, initial, witness)
            record = {"profile": profile, "kind": kind, "boundary": boundary, "expected": outcome,
                      "root": str(path.resolve()), "success": False}
            records.append(record)
            child = subprocess.run([sys.executable, "-m", "prism_c.zoned_fault", str(path), str(fence),
                                    kind, boundary], capture_output=True, text=True, timeout=45,
                                   cwd=Path(__file__).resolve().parents[1])
            record.update(exit_code=child.returncode, stderr=child.stderr)
            if child.returncode != EXIT_CODE:
                raise AssertionError("Requested actual process exit did not occur")
            store = ZonedFileStore(path)
            assert_bytes(store, contents)
            record.update(before_cursor=store.info()["cursor"], before_ledger=store.ledger(),
                          before_pending=store.info()["pending"])
            newer = store.takeover()
            try:
                store.advance(fence)
            except Rejected:
                record["stale_fence_rejected"] = True
            else:
                raise AssertionError("Old actor survived takeover")
            if outcome == "invalid":
                with store.zone_path("A").open("r+b") as handle:
                    handle.write(b"wrong row")
                    handle.flush()
                    import os
                    os.fsync(handle.fileno())
            if outcome == "recover":
                store.execute(newer)
                assert_bytes(store, contents)
                if not store.audit()["target"] or store.snapshot() != replay(initial, witness):
                    raise AssertionError("Fault reconciliation missed target")
                if sum(r["stage_bytes"] for r in store.receipts()) != 64 or len(store.receipts()) != len(witness.actions):
                    raise AssertionError("Fault caused duplicate committed operation")
                if store.ledger()["A"]["incarnation"] != 2 or store.zone_path("A").stat().st_size != 64:
                    raise AssertionError("Fault miscounted reset generation/write position")
                recovered += 1
            else:
                before_size = store.zone_path("A").stat().st_size
                try:
                    store.advance(newer)
                except Rejected:
                    pass
                else:
                    raise AssertionError("Uncertain invalid write was published")
                document = ZonedFileStore(path).info()
                if (not document["quarantine"] or document["pending"] is None
                        or document["cursor"] != record["before_cursor"]
                        or store.zone_path("A").stat().st_size != before_size
                        or any(z["appendable_units"] for z in store.ledger().values())):
                    raise AssertionError("Uncertainty released capacity or rewound bytes")
                assert_bytes(store, contents)
                record["quarantine_reason"] = document["quarantine"]
                quarantined += 1
            record.update(success=True, final_cursor=store.info()["cursor"], final_ledger=store.ledger(),
                          receipts=store.receipts(), exact_contents=True)
    return {"actual_process_exits": len(records), "recovered_to_target": recovered,
            "conservatively_quarantined": quarantined}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    root, path = Path(args.root).resolve(), Path(args.report).resolve()
    if root.exists() or path.exists():
        raise ValueError("Use fresh store and report paths")
    root.mkdir(parents=True)
    from .__main__ import environment
    metadata = environment()
    project = Path(__file__).resolve().parents[1]
    metadata["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=project).strip()
    metadata["protocol_sha256"] = digest((project / "experiments/zoned_file_protocol.md").read_bytes())
    records, faults = [], []
    result = {"environment": metadata, "success": False, "comparison_records": records, "fault_records": faults,
              "scope": "Serialized 64-byte zoned-file emulation; actual process exits, no power-loss/device or timing claim",
              "patent_advantage_claimed": False, "rating_changed": False}
    try:
        result["comparison"] = run_comparison(root, records)
        result["faults"] = run_faults(root, faults)
        result["success"] = True
    except Exception as error:
        result["error"] = repr(error)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("environment", "comparison_records", "fault_records")}, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
