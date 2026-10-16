"""Native-emulator bytes on the existing conventional model's complete routes."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import platform
import subprocess

from analysis.qemu_zns_smoke import QemuZns
from prism_c.coding import digest, encode, recover
from prism_c.model import SearchStatus
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO, PROFILES
from prism_c.zoned_baseline import conventional_zoned_plan, separated_gc_plan
from prism_c.zoned_campaign import zoned_fixture
from prism_c.zoned_model import goal, replay, step


UNIT = 4096


def run_case(root, profile, extra, arm):
    initial = zoned_fixture(profile, extra=extra)
    planned = separated_gc_plan(initial) if arm == "separated" else conventional_zoned_plan(initial)
    if planned.status != SearchStatus.FOUND:
        raise RuntimeError("Declared native route is not feasible")
    contents = {s.name: bytes((i + 37) % 251 for i in range(PROFILES[s.profile].data_rows * UNIT)) for s in initial.stripes}
    encoded = {s.name: encode(contents[s.name], s.profile) for s in initial.stripes}
    manifests = {s.name: {"length": len(contents[s.name]), "profile": s.profile,
                         "sha256": digest(contents[s.name]), "rows": [digest(row) for row in encoded[s.name]]} for s in initial.stripes}
    result = {"profile": profile, "extra": extra, "arm": arm, "success": False,
              "initial": asdict(initial), "witness": planned.witness.to_dict(), "manifests": manifests,
              "prefixes": [], "native_stage_bytes": 0}
    device = QemuZns.__new__(QemuZns)
    try:
        device.__init__(root, {z.name: z.capacity for z in initial.zones})
        if device.identify_serial() != device.serial:
            raise RuntimeError("Controller identity mismatch")
        result.update(assigned_serial=device.serial, namespaces=device.namespaces, command=device.command,
                      qemu_version=subprocess.check_output([device.binary, "--version"], text=True).splitlines()[0],
                      qemu_binary_sha256=digest(Path(device.binary).read_bytes()))
        def namespace(zone):
            return device.namespaces[zone.name]["nsid"]
        for zone in initial.zones:
            for offset, extent in enumerate(zone.extents):
                payload = encoded[extent.stripe][extent.row] if extent.stripe else bytes([165])*UNIT
                device.write(payload, offset*8, nsid=namespace(zone))
        # Do not use expected codeword payloads to materialize any later stage.
        del encoded

        def decoded(state):
            result = {}
            for spec in state.stripes:
                manifest = manifests[spec.name]
                rows = {}
                for zone in state.zones:
                    if zone.domain in state.offline:
                        continue
                    for offset, extent in enumerate(zone.extents):
                        if extent.status == "LIVE" and extent.stripe == spec.name:
                            payload = device.read(offset*8, nsid=namespace(zone))
                            if digest(payload) != manifest["rows"][extent.row]:
                                raise RuntimeError("Native source row authentication failure")
                            rows[extent.row] = payload
                data, regenerated = recover(rows, manifest["length"], spec.profile)
                if digest(data) != manifest["sha256"] or [digest(row) for row in regenerated] != manifest["rows"]:
                    raise RuntimeError("Native reconstructed identity mismatch")
                result[spec.name] = data, regenerated
            return result

        def check(state, cursor):
            reports = {}
            for zone in state.zones:
                observed = device.report(nsid=namespace(zone))
                phase = zone.reset_prior if zone.phase == "RESETTING" else zone.phase
                expected_conditions = {"EMPTY": (1,), "OPEN": (2, 3), "CLOSED": (4,), "FULL": (14,), "FINISHED": (14,)}
                if observed["capacity_lba"] != zone.capacity*8 or observed["condition"] not in expected_conditions[phase]:
                    raise RuntimeError("Native geometry/state differs from model")
                if phase not in ("FULL", "FINISHED") and observed["wp_lba"] != len(zone.extents)*8:
                    raise RuntimeError("Native write pointer differs from model")
                reports[zone.name] = observed
            recovered = decoded(state)
            if any(recovered[name][0] != data for name, data in contents.items()):
                raise RuntimeError("Prefix content mismatch")
            result["prefixes"].append({"cursor": cursor, "state_sha256": state.fingerprint(), "reports": reports, "exact_readback": True})

        current = initial
        check(current, 0)
        for cursor, action in enumerate(planned.witness.actions, 1):
            zone = next(z for z in current.zones if z.name == action.zone)
            following = step(current, action)
            if action.kind == "stage":
                payload = decoded(current)[action.stripe][1][action.row]
                device.write(payload, len(zone.extents)*8, nsid=namespace(zone))
                result["native_stage_bytes"] += len(payload)
            elif action.kind == "promote":
                payload = device.read(action.offset*8, nsid=namespace(zone))
                extent = zone.extents[action.offset]
                if digest(payload) != manifests[extent.stripe]["rows"][extent.row]:
                    raise RuntimeError("Native staged row authentication failure")
            elif action.kind in ("open", "close", "finish", "reset_ack"):
                device.manage({"open": 3, "close": 1, "finish": 2, "reset_ack": 4}[action.kind], nsid=namespace(zone))
            current = following
            check(current, cursor)
        if current != replay(initial, planned.witness) or not goal(current):
            raise RuntimeError("Native route does not reach replayed target")
        if result["native_stage_bytes"] != UNIT*sum(a.kind == "stage" for a in planned.witness.actions):
            raise RuntimeError("Stage byte receipt mismatch")
        result["success"] = True
    except Exception as error:
        result["error"] = repr(error)
    finally:
        result["command_completions"] = getattr(device, "trace", [])
        device.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    root, output = Path(args.root), Path(args.report)
    if root.exists() or output.exists():
        raise ValueError("Fresh runtime/report required")
    root.mkdir(parents=True)
    report = {"platform": platform.platform(), "success": False, "cases": [],
              "native_command_byte_routes": True, "persistent_authority_integration": False,
              "power_loss_tested": False, "external_reproduction": False, "patent_rating_changed": False,
              "harness_sha256": digest(Path(__file__).read_bytes()), "qtest_driver_sha256": digest(Path(__file__).with_name("qemu_zns_smoke.py").read_bytes())}
    for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
        for extra in (False, True):
            for arm in ("joint", "separated"):
                case = run_case(root/f"case-{len(report['cases'])}", profile, extra, arm)
                report["cases"].append(case)
                print(profile, extra, arm, case["success"], case.get("error"), flush=True)
                if not case["success"]:
                    break
            else:
                continue
            break
        else:
            continue
        break
    report["success"] = len(report["cases"]) == 8 and all(c["success"] for c in report["cases"])
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
