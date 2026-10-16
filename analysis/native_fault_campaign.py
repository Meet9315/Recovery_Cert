"""E21 real native-emulator authority routes, actor exits and drain boundaries."""

import argparse
from contextlib import contextmanager
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from prism_c.__main__ import environment
from prism_c.coding import digest
from prism_c.model import Rejected
from prism_c.native_authority import NativeAuthority, NativeClient, Uncertain
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES
from prism_c.zoned_baseline import conventional_zoned_plan, separated_gc_plan
from prism_c.zoned_campaign import zoned_fixture
from prism_c.zoned_model import ZAction, replay


ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def launch(root, initial):
    root.mkdir(parents=True, exist_ok=False)
    geometry = root/"geometry.json"
    geometry.write_text(json.dumps({z.name: z.capacity for z in initial.zones}))
    stderr = (root/"supervisor-stderr.log").open("wb")
    process = subprocess.Popen([sys.executable, "-m", "analysis.native_session_server", "--root", str(root/"device"), "--geometry", str(geometry)],
                               cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stderr, stderr=stderr)
    descriptor = root/"device/session.json"
    try:
        for _ in range(300):
            if process.poll() is not None:
                raise RuntimeError((root/"supervisor-stderr.log").read_text())
            try:
                json.loads(descriptor.read_bytes())
                break
            except (OSError, ValueError):
                time.sleep(.05)
        else:
            raise TimeoutError("Native supervisor did not start")
        yield descriptor, process
    finally:
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=15)
        stderr.close()


def actor(root, fence, kind, boundary):
    authority = NativeAuthority(root)
    def exit_at(actual_kind, actual_boundary):
        if (actual_kind, actual_boundary) == (kind, boundary):
            os._exit(86)
    while authority.advance(fence, hook=exit_at)["status"] != "DONE":
        authority.read("object")


def run_case(root, profile, *, extra=False, arm="joint", fault=None, delayed=None, edge=None):
    initial = zoned_fixture(profile, extra=extra)
    contents = {s.name: bytes((i+19) % 251 for i in range(PROFILES[s.profile].data_rows*4096)) for s in initial.stripes}
    planned = separated_gc_plan(initial) if arm == "separated" else conventional_zoned_plan(initial)
    witness = planned.witness
    if fault or delayed or edge:
        # Finishing A intentionally strands its newly reclaimed tail. Keep the
        # original reclaim route as a prefix, but require repair-only at the
        # final diagnostic close/finish boundary; do not claim final reclaim.
        initial = replace(initial, reclaim=())
        witness = replace(witness, initial=initial.fingerprint())
        terminal = replay(initial, witness)
        zone = next(z for z in terminal.zones if z.name == "A")
        witness = replace(witness, actions=witness.actions+(ZAction("close", zone.name, zone.incarnation), ZAction("finish", zone.name, zone.incarnation)))
        replay(initial, witness)
    result = {"profile": profile, "extra": extra, "arm": arm, "fault": fault, "delayed": delayed, "edge": edge,
              "success": False, "witness": witness.to_dict(), "initial": asdict(initial), "exact_prefixes": 0,
              "diagnostic_final_goal_relaxed_to_repair_only": bool(fault or delayed or edge)}
    try:
        with launch(root, initial) as (descriptor, supervisor):
            authority = NativeAuthority.create(root/"authority", initial, contents, descriptor)
            fence = authority.takeover()
            authority.admit(witness, fence)
            result["binding"] = authority.info()["binding"]
            assert authority.read("object") == contents["object"]
            result["exact_prefixes"] += 1
            partial_expected = fault == ("stage", "half_io") or delayed == "stage"
            if fault or delayed or edge in ("altered_intent", "session_loss"):
                selected = fault or (("stage", "after_prepare") if edge else ("never", "never"))
                if delayed:
                    desired = "stage" if delayed == "stage" else "reset_ack"
                    while witness.actions[authority.info()["cursor"]].kind != desired:
                        authority.advance(fence)
                    authority.client.call("delay_next", fence, kind="write" if delayed == "stage" else "manage", milliseconds=1000)
                child = subprocess.Popen([sys.executable, "-m", "analysis.native_fault_campaign", "actor", "--root", str(authority.root),
                                          "--fence", str(fence), "--kind", selected[0], "--boundary", selected[1]], cwd=ROOT,
                                         stdout=subprocess.DEVNULL, stderr=(root/"actor-stderr.log").open("wb"))
                if delayed:
                    for _ in range(1000):
                        log = root/"device/operations.jsonl"
                        events = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
                        if any(e["event"] == "submitted_unacknowledged" for e in events):
                            child.kill()
                            break
                        if child.poll() is not None:
                            raise RuntimeError("Actor ended before submitted/unacknowledged boundary")
                        time.sleep(.005)
                    else:
                        child.kill()
                        raise TimeoutError("Native submission marker not reached")
                code = child.wait(timeout=60)
                result["actor_exit_code"] = code
                assert code == (-9 if delayed else 86), (code, (root/"actor-stderr.log").read_text())
                authority = NativeAuthority(authority.root)
                result["after_exit"] = {k: authority.info()[k] for k in ("cursor", "pending", "fence")}
                if edge == "session_loss":
                    supervisor.terminate()
                    supervisor.wait(timeout=15)
                    before = authority.info()["fence"]
                    try:
                        authority.takeover()
                    except Uncertain:
                        pass
                    else:
                        raise AssertionError("Lost native session was adopted")
                    assert authority.info()["fence"] == before
                    assert all(row["appendable_units"] == 0 for row in authority.ledger().values())
                    result.update(success=True, outcome="SESSION_LOSS_FAILS_CLOSED; NOT POWER_LOSS_RECOVERY")
                else:
                    new_fence = authority.takeover()
                    before_stats = authority.client.call("stats", new_fence)
                    try:
                        authority.advance(fence)
                    except Rejected:
                        pass
                    else:
                        raise AssertionError("Old authority was accepted")
                    try:
                        authority.client.call("report", fence, zone="A")
                    except Uncertain:
                        pass
                    else:
                        raise AssertionError("Old native request was submitted")
                    assert authority.client.call("stats", new_fence)["commands"] == before_stats["commands"]
                    result["stale_actor_and_native_request_rejected_without_submission"] = True
                    if edge == "altered_intent":
                        with authority.transaction() as db:
                            document = authority.load(db)
                            document["pending"]["id"] = "altered"
                            authority.save(db, document)
                    try:
                        authority.execute(new_fence)
                    except Rejected:
                        assert partial_expected or edge == "altered_intent"
                        if edge == "altered_intent":
                            assert authority.client.call("stats", new_fence)["commands"] == before_stats["commands"]
                        assert all(row["appendable_units"] == 0 for row in authority.ledger().values())
                        if partial_expected:
                            assert authority.info()["quarantine"]
                            doc = authority.info()
                            assert authority.decoded(doc, authority.snapshot())["object"][0] == contents["object"]
                            result["outcome"] = "PARTIAL_APPEND_QUARANTINED; SOURCES_RETAINED"
                        else:
                            result["outcome"] = "ALTERED_INTENT_REJECTED; NO_FREE_CREDIT"
                    else:
                        assert not partial_expected and edge != "altered_intent"
                        assert authority.audit()["target"] and authority.read("object") == contents["object"]
                        assert len(authority.receipts()) == len(witness.actions)
                        result["outcome"] = "RESUMED_EXACT_TARGET"
                    result["success"] = True
            elif edge == "identity":
                original = descriptor.read_bytes()
                changed = json.loads(original)
                changed["serial"] = "RECREATED-DEVICE"
                descriptor.write_text(json.dumps(changed))
                before = authority.client.call("stats", fence)["commands"]
                try:
                    NativeAuthority(authority.root)
                except Rejected:
                    pass
                else:
                    raise AssertionError("Changed descriptor was accepted")
                assert authority.client.call("stats", fence)["commands"] == before
                descriptor.write_bytes(original)
                result.update(success=True, outcome="CHANGED_SESSION_IDENTITY_REJECTED_BEFORE_IO")
            else:
                for cursor in range(len(witness.actions)):
                    authority.advance(fence, cursor)
                    assert authority.read("object") == contents["object"]
                    result["exact_prefixes"] += 1
                assert authority.audit()["target"]
                assert len(authority.receipts()) == len(witness.actions)
                result.update(success=True, outcome="NOMINAL_EXACT_TARGET")
            result["receipts"] = authority.receipts()
            result["final_ledger"] = authority.ledger()
            result["final_info"] = {k: authority.info()[k] for k in ("cursor", "fence", "pending", "quarantine")}
        result["supervisor_report"] = json.loads((root/"device/supervisor-report.json").read_text())
        operations = [json.loads(line) for line in (root/"device/operations.jsonl").read_text().splitlines()]
        result["native_writes_excluding_bootstrap"] = sum(e["event"] == "started" and e["op"] == "write" and e["operation"] != "bootstrap" for e in operations)
        result["native_resets"] = sum(e["event"] == "started" and e["op"] == "manage" and e["action"] == 4 for e in operations)
        if result.get("outcome") in ("RESUMED_EXACT_TARGET", "NOMINAL_EXACT_TARGET"):
            assert result["native_writes_excluding_bootstrap"] == 2*sum(a.kind == "stage" for a in witness.actions)
            assert result["native_resets"] == sum(a.kind == "reset_ack" for a in witness.actions)
    except Exception as error:
        result.update(success=False, error=repr(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("actor", "collect"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--report")
    parser.add_argument("--fence", type=int)
    parser.add_argument("--kind")
    parser.add_argument("--boundary")
    args = parser.parse_args()
    if args.phase == "actor":
        actor(args.root, args.fence, args.kind, args.boundary)
        return 0
    root, output = Path(args.root), Path(args.report)
    if root.exists() or output.exists():
        raise ValueError("Fresh native campaign root/report required")
    root.mkdir(parents=True)
    configurations = [(p, {"extra": extra, "arm": arm}) for p in (DEFAULT_PROFILE, FOUR_PLUS_TWO) for extra in (False, True) for arm in ("joint", "separated")]
    configurations += [(p, {"fault": (kind, boundary)}) for p in (DEFAULT_PROFILE, FOUR_PLUS_TWO)
                       for kind in ("open", "close", "finish", "stage", "reset_ack")
                       for boundary in ("before_prepare", "after_prepare", "before_io", "after_io", "before_commit", "after_commit")]
    configurations += [(p, {"fault": ("stage", "half_io")}) for p in (DEFAULT_PROFILE, FOUR_PLUS_TWO)]
    configurations += [(p, {"fault": ("reset_request", boundary)}) for p in (DEFAULT_PROFILE, FOUR_PLUS_TWO) for boundary in ("before_commit", "after_commit")]
    configurations += [(p, {"delayed": kind}) for p in (DEFAULT_PROFILE, FOUR_PLUS_TWO) for kind in ("stage", "reset_ack")]
    configurations += [(p, {"edge": kind}) for p in (DEFAULT_PROFILE, FOUR_PLUS_TWO) for kind in ("identity", "altered_intent", "session_loss")]
    report = {"environment": environment(), "success": False, "cases": [], "registered_cases": len(configurations),
              "physical_power_loss_tested": False, "external_reproduction": False, "patent_rating_changed": False,
              "harness_sha256": digest(Path(__file__).read_bytes()),
              "supervisor_sha256": digest(Path(__file__).with_name("native_session_server.py").read_bytes()),
              "qemu_driver_sha256": digest(Path(__file__).with_name("qemu_zns_smoke.py").read_bytes()),
              "protocol_sha256": digest((ROOT/"experiments/native_authority_protocol.md").read_bytes())}
    try:
        report["git_head_at_start"] = subprocess.check_output(["git", "-c", f"safe.directory={ROOT}", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        report["git_head_at_start"] = None
    for profile, config in configurations:
        case = run_case(root/f"case-{len(report['cases']):03d}", profile, **config)
        report["cases"].append(case)
        print(len(report["cases"]), profile, config, case["success"], case.get("error"), flush=True)
        if not case["success"]:
            break
    report["success"] = len(report["cases"]) == len(configurations) and all(c["success"] for c in report["cases"])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
