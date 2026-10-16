"""Kernel zoned-I/O smoke test on a newly created owned RAM-backed null device.

Never accepts a device path. Does not integrate the persistent storage authority
or claim survival of VM/power loss. Linux and root/configfs capability required.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import struct
import subprocess
import time
import uuid


def zone_report(fd, sector=0):
    import fcntl
    buffer = bytearray(struct.pack("=QII", sector, 1, 0) + bytes(64))
    fcntl.ioctl(fd, 0xC0101282, buffer, True)
    _, count, flags = struct.unpack_from("=QII", buffer)
    if count != 1 or not flags & 1:
        raise RuntimeError("Authoritative capacity report unavailable")
    start, length, wp, kind, condition, _, _, capacity = struct.unpack_from("=QQQBBBB4xQ", buffer, 16)
    return {"start_sectors": start, "length_sectors": length, "wp_sectors": wp,
            "type": kind, "condition": condition, "capacity_sectors": capacity}


def operation(fd, command, zone):
    import fcntl
    fcntl.ioctl(fd, command, struct.pack("=QQ", zone["start_sectors"], zone["length_sectors"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-owned-nullblk", action="store_true", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    destination = Path(args.report)
    if destination.exists():
        raise ValueError("Fresh evidence report required")
    result = {"kernel": platform.release(), "success": False, "observations": [],
              "existing_device_paths_accepted": False, "owned_device_created": False,
              "persistent_authority_integration": False,
              "power_loss_tested": False, "nvme_zone_append_tested": False,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    config_root = Path("/sys/kernel/config/nullb")
    owned, fd = None, None
    try:
        if platform.system() != "Linux" or os.geteuid() != 0:
            raise RuntimeError("Linux root/configfs capability required")
        if not config_root.exists():
            loaded = subprocess.run(["modprobe", "null_blk", "nr_devices=0"], capture_output=True, text=True, timeout=20)
            result["module_load"] = {"exit_code": loaded.returncode, "stderr": loaded.stderr}
            if loaded.returncode or not config_root.exists():
                raise RuntimeError("Running kernel/configfs does not provide null_blk")
        before = {p.name for p in Path("/sys/block").iterdir()}
        owned = config_root / ("rcsd" + uuid.uuid4().hex[:12])
        owned.mkdir(exist_ok=False)
        result["owned_config"] = str(owned)
        settings = {"size": 64, "blocksize": 512, "memory_backed": 1,
                    "zoned": 1, "zone_size": 1, "zone_capacity": 1, "zone_nr_conv": 0}
        for name, value in settings.items():
            (owned / name).write_text(str(value))
        (owned / "power").write_text("1")
        result["owned_device_created"] = True
        module_info = subprocess.run(["modinfo", "null_blk"], capture_output=True, text=True, timeout=15)
        result["module_info"] = {"exit_code": module_info.returncode, "stdout": module_info.stdout, "stderr": module_info.stderr}
        result["settings"] = {name: (owned / name).read_text().strip() for name in settings}
        candidates = []
        for _ in range(40):
            candidates = [p for p in Path("/sys/block").iterdir() if p.name not in before]
            if len(candidates) == 1 and Path("/dev", candidates[0].name).exists():
                break
            time.sleep(.05)
        if len(candidates) != 1:
            raise RuntimeError("Cannot uniquely bind newly created emulator")
        sysfs, device = candidates[0], Path("/dev", candidates[0].name)
        if device.name != owned.name:
            index = (owned / "index").read_text().strip()
            if device.name != "nullb" + index:
                raise RuntimeError("New block device does not match owned configfs index")
        if (sysfs / "queue/zoned").read_text().strip() != "host-managed":
            raise RuntimeError("Owned emulator is not host-managed zoned")
        for line in Path("/proc/self/mountinfo").read_text().splitlines():
            if (sysfs / "dev").read_text().strip() == line.split()[2]:
                raise RuntimeError("Owned emulator unexpectedly mounted")
        fd = os.open(device, os.O_RDWR | os.O_EXCL)
        info = os.fstat(fd)
        if not stat.S_ISBLK(info.st_mode) or f"{os.major(info.st_rdev)}:{os.minor(info.st_rdev)}" != (sysfs / "dev").read_text().strip():
            raise RuntimeError("Block device identity mismatch")
        result["device_binding"] = {"path": str(device), "major": os.major(info.st_rdev), "minor": os.minor(info.st_rdev),
                                    "sysfs": str(sysfs.resolve()), "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip()}
        initial = zone_report(fd)
        result["observations"].append({"phase": "initial", **initial})
        if initial["condition"] != 1 or initial["type"] != 2 or initial["wp_sectors"] != initial["start_sectors"]:
            raise RuntimeError("New sequential zone is not empty")
        if initial["length_sectors"] != 2048 or initial["capacity_sectors"] != 2048:
            raise RuntimeError("Owned emulator geometry differs from creation contract")
        payload = bytes((i * 17 + 31) % 251 for i in range(4096))
        offset = initial["start_sectors"] * 512
        if os.pwrite(fd, payload, offset) != len(payload):
            raise RuntimeError("Short sequential write")
        os.fsync(fd)
        after = zone_report(fd)
        result["observations"].append({"phase": "after_positioned_write", **after})
        if after["wp_sectors"] != initial["wp_sectors"] + 8 or os.pread(fd, len(payload), offset) != payload:
            raise RuntimeError("Write pointer/readback mismatch")
        operation(fd, 0x40101287, initial)  # BLKCLOSEZONE
        closed = zone_report(fd)
        result["observations"].append({"phase": "closed", **closed})
        if closed["condition"] != 4 or closed["wp_sectors"] != after["wp_sectors"]:
            raise RuntimeError("Close changed position or wrong condition")
        operation(fd, 0x40101288, initial)  # BLKFINISHZONE
        finished = zone_report(fd)
        result["observations"].append({"phase": "finished", **finished})
        if finished["condition"] != 14:
            raise RuntimeError("Finish did not produce full condition")
        operation(fd, 0x40101283, initial)  # BLKRESETZONE
        reset = zone_report(fd)
        result["observations"].append({"phase": "reset", **reset})
        if reset["condition"] != 1 or reset["wp_sectors"] != initial["start_sectors"]:
            raise RuntimeError("Reset acknowledgement/position mismatch")
        replacement = bytes([93]) * 4096
        if os.pwrite(fd, replacement, offset) != len(replacement) or os.pread(fd, len(replacement), offset) != replacement:
            raise RuntimeError("Reset reuse readback mismatch")
        result["success"] = True
    except Exception as error:
        result["error"] = repr(error)
    finally:
        if fd is not None:
            os.close(fd)
        if owned is not None and owned.exists():
            try:
                if owned.parent.resolve() != config_root.resolve() or not owned.name.startswith("rcsd"):
                    raise RuntimeError("Unsafe cleanup target")
                if (owned / "power").exists():
                    (owned / "power").write_text("0")
                owned.rmdir()  # Only this invocation's new configfs object; no recursive deletion.
                result["owned_emulator_removed"] = True
            except Exception as error:
                result["cleanup_error"] = repr(error)
                result["success"] = False
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
