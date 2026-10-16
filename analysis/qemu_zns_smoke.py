"""Actual QEMU NVMe ZNS command test through qtest on a new disposable image.

No existing image/device path is accepted. No guest OS or KVM is required. This
tests emulated commands, not a persistent authority or physical power loss.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import uuid


class QemuZns:
    BAR = 0x10000000
    DATA = 0x200000

    def __init__(self, root, zone_capacities=None):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=False)
        self.binary = shutil.which("qemu-system-x86_64")
        if not self.binary:
            raise RuntimeError("QEMU unavailable")
        self.serial = "RCSD" + uuid.uuid4().hex[:16]
        self.namespaces = {}
        namespace_args = []
        capacities = zone_capacities or {"smoke": 192}
        for nsid, (name, units) in enumerate(capacities.items(), 1):
            image = self.root / f"owned-ns-{nsid}.raw"
            with image.open("xb") as handle:
                handle.truncate(64 * 1024 * 1024 if zone_capacities is None else 1024 * 1024)
            self.namespaces[name] = {"nsid": nsid, "capacity_units": units, "image": str(image)}
            namespace_args += ["-drive", f"file={image},format=raw,if=none,id=znsdrive{nsid}",
                "-device", f"nvme-ns,drive=znsdrive{nsid},bus=nvme0,nsid={nsid},zoned=on,zoned.zone_size=1M,zoned.zone_capacity={units*4096},zoned.max_open=1,zoned.max_active=1"]
        # Distribution QEMU lacks the qtest accelerator/clock_step command.
        # A tiny CLI/HLT loop leaves PCI configuration entirely to this driver
        # while TCG's virtual timers run normally. It boots no OS/user image.
        firmware = bytearray([255]) * 65536
        firmware[-16:-12] = b"\xfa\xf4\xeb\xfd"
        bios = self.root / "owned-halt-bios.bin"
        bios.write_bytes(firmware)
        self.temp = tempfile.TemporaryDirectory(prefix="rcsd-qtest-")
        self.socket_path = Path(self.temp.name) / "control.sock"
        self.error_log = (self.root / "qemu-stderr.log").open("wb")
        self.command = [self.binary, "-machine", "q35,accel=tcg", "-bios", str(bios), "-m", "64",
            "-display", "none", "-nodefaults", "-monitor", "none",
            "-qtest", f"unix:{self.socket_path},server=on,wait=off", "-qtest-log", str(self.root/"qtest.log"),
            "-device", f"nvme,id=nvme0,serial={self.serial},addr=04.0"] + namespace_args
        self.process = subprocess.Popen(self.command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=self.error_log)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        for _ in range(100):
            if self.process.poll() is not None:
                raise RuntimeError((self.root/"qemu-stderr.log").read_text())
            try:
                self.sock.connect(str(self.socket_path))
                break
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(.02)
        else:
            raise TimeoutError("QEMU qtest socket unavailable")
        self.stream = self.sock.makefile("rwb", buffering=0)
        self.trace = []
        self.queues = {0: {"sq": 0x100000, "cq": 0x101000, "tail": 0, "head": 0, "phase": 1},
                       1: {"sq": 0x102000, "cq": 0x103000, "tail": 0, "head": 0, "phase": 1}}
        self.cid = 0
        self.pci_write(0x10, self.BAR)
        self.pci_write(0x14, 0)
        self.pci_write(4, 6)
        self.stride = 4 << ((self.read_register(0, 64) >> 32) & 15)
        self.write_register(0x24, 63 | (63 << 16))
        self.write_register(0x28, self.queues[0]["sq"], 64)
        self.write_register(0x30, self.queues[0]["cq"], 64)
        self.write_register(0x14, 1 | (6 << 4) | (6 << 16) | (4 << 20))
        for _ in range(100):
            if self.read_register(0x1c) & 1:
                break
            time.sleep(.01)
        else:
            raise TimeoutError("NVMe controller not ready")
        self.submit(5, words={10: 1 | (63 << 16), 11: 1}, prp=self.queues[1]["cq"])
        self.submit(1, words={10: 1 | (63 << 16), 11: 1 | (1 << 16)}, prp=self.queues[1]["sq"])

    def call(self, command):
        self.stream.write((command + "\n").encode())
        while True:
            response = self.stream.readline().decode().strip()
            if response.startswith("IRQ"):
                continue
            if not response.startswith("OK"):
                raise RuntimeError(f"qtest {command.split()[0]}: {response}")
            return response[2:].strip()

    def pci_write(self, offset, value):
        self.call(f"outl 0xcf8 {0x80000000 | (4 << 11) | offset:#x}")
        self.call(f"outl 0xcfc {value:#x}")

    def read_register(self, offset, width=32):
        return int(self.call(f"{'readq' if width == 64 else 'readl'} {self.BAR+offset:#x}"), 0)

    def write_register(self, offset, value, width=32):
        self.call(f"{'writeq' if width == 64 else 'writel'} {self.BAR+offset:#x} {value:#x}")

    def memory_write(self, address, data):
        self.call(f"write {address:#x} {len(data):#x} 0x{data.hex()}")

    def memory_read(self, address, size):
        return bytes.fromhex(self.call(f"read {address:#x} {size:#x}").removeprefix("0x"))

    def submit(self, opcode, *, queue=0, nsid=0, words=None, prp=DATA):
        self.cid = (self.cid + 1) % 65536
        command = bytearray(64)
        struct.pack_into("<BBHI", command, 0, opcode, 0, self.cid, nsid)
        struct.pack_into("<Q", command, 24, prp)
        for word, value in (words or {}).items():
            struct.pack_into("<I", command, word * 4, value)
        q = self.queues[queue]
        self.memory_write(q["sq"] + q["tail"] * 64, command)
        q["tail"] = (q["tail"] + 1) % 64
        self.write_register(0x1000 + 2 * queue * self.stride, q["tail"])
        if getattr(self, "after_submit", None):
            self.after_submit(queue, opcode, self.cid)
        for _ in range(1000):
            completion = self.memory_read(q["cq"] + q["head"] * 16, 16)
            value, _, _, sqid, cid, status = struct.unpack("<IIHHHH", completion)
            if status & 1 == q["phase"]:
                if cid != self.cid or sqid != queue:
                    raise RuntimeError("Wrong NVMe command/queue completion")
                self.trace.append({"queue": queue, "opcode": opcode, "cid": cid, "status": status >> 1, "result": value})
                q["head"] = (q["head"] + 1) % 64
                if q["head"] == 0:
                    q["phase"] ^= 1
                self.write_register(0x1000 + (2 * queue + 1) * self.stride, q["head"])
                if status >> 1:
                    raise RuntimeError(f"NVMe command error {status >> 1:#x}")
                return value
            # TCG's virtual clock runs with our isolated halt-only firmware.
            time.sleep(.001)
        raise TimeoutError("NVMe command completion missing")

    def identify_serial(self):
        self.submit(6, words={10: 1})
        return self.memory_read(self.DATA, 4096)[4:24].decode().strip()

    def report(self, slba=0, *, nsid=1):
        self.submit(0x7a, queue=1, nsid=nsid, words={10: slba, 12: 1023, 13: 0})
        raw = self.memory_read(self.DATA, 4096)
        count = struct.unpack_from("<Q", raw)[0]
        if not count:
            raise RuntimeError("Empty zone report")
        capacity, start, wp = struct.unpack_from("<QQQ", raw, 72)
        return {"reported_zones": count, "type": raw[64] & 15, "condition": raw[65] >> 4,
                "capacity_lba": capacity, "start_lba": start, "wp_lba": wp}

    def manage(self, action, slba=0, *, nsid=1):
        self.submit(0x79, queue=1, nsid=nsid, words={10: slba, 13: action})

    def write(self, payload, slba=0, *, nsid=1):
        if not 0 < len(payload) <= 4096 or len(payload) % 512:
            raise ValueError("Native writes need aligned bytes within one PRP page")
        self.memory_write(self.DATA, payload)
        self.submit(1, queue=1, nsid=nsid, words={10: slba, 12: len(payload)//512-1})

    def read(self, slba=0, *, nsid=1, length=4096):
        if not 0 < length <= 4096 or length % 512:
            raise ValueError("Native reads need aligned bytes within one PRP page")
        self.memory_write(self.DATA, bytes(length))
        self.submit(2, queue=1, nsid=nsid, words={10: slba, 12: length//512-1})
        return self.memory_read(self.DATA, length)

    def close(self):
        if hasattr(self, "stream"):
            self.stream.close()
        if hasattr(self, "sock"):
            self.sock.close()
        if hasattr(self, "process") and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)
        if hasattr(self, "error_log"):
            self.error_log.close()
        if hasattr(self, "temp"):
            self.temp.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    output = Path(args.report)
    if output.exists() or Path(args.root).exists():
        raise ValueError("Fresh root/report required")
    result = {"platform": platform.platform(), "success": False, "observations": [],
              "existing_image_or_device_used": False, "persistent_authority_integration": False,
              "power_loss_tested": False, "nvme_zone_append_tested": False,
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    device = QemuZns.__new__(QemuZns)
    try:
        device.__init__(args.root)
        result.update(qemu_version=subprocess.check_output([device.binary, "--version"], text=True).splitlines()[0],
                      qemu_binary_sha256=hashlib.sha256(Path(device.binary).read_bytes()).hexdigest(),
                      command=device.command, assigned_serial=device.serial)
        if device.identify_serial() != device.serial:
            raise RuntimeError("Namespace/controller serial binding mismatch")
        initial = device.report()
        result["observations"].append({"phase": "initial", **initial})
        if initial["type"] != 2 or initial["condition"] != 1 or initial["wp_lba"] != 0 or initial["capacity_lba"] != 1536:
            raise RuntimeError("Initial ZNS geometry/state mismatch")
        payload = bytes((17*i+31) % 251 for i in range(4096))
        device.write(payload)
        after = device.report()
        result["observations"].append({"phase": "written", **after})
        if after["wp_lba"] != 8 or device.read() != payload:
            raise RuntimeError("Actual write-pointer/readback mismatch")
        for name, action, condition in (("closed", 1, 4), ("finished", 2, 14), ("reset", 4, 1)):
            device.manage(action)
            observed = device.report()
            result["observations"].append({"phase": name, **observed})
            if observed["condition"] != condition or name == "reset" and observed["wp_lba"] != 0:
                raise RuntimeError(f"{name} status/position mismatch")
        replacement = bytes([93])*4096
        device.write(replacement)
        if device.read() != replacement:
            raise RuntimeError("Reset reuse readback mismatch")
        result["success"] = True
    except Exception as error:
        result["error"] = repr(error)
    finally:
        result["command_completions"] = getattr(device, "trace", [])
        result["command"] = getattr(device, "command", None)
        device.close()
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as handle:
            json.dump(result, handle, sort_keys=True, indent=2)
            handle.write("\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
