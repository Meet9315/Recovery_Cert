"""Read-only Linux inventory for a disposable zoned-storage backend; no disk writes."""

import gzip
import json
from pathlib import Path
import platform
import shutil
import subprocess


def main():
    kernel = platform.release()
    report = {"kernel": kernel, "platform": platform.platform(),
              "tools": {name: shutil.which(name) for name in ("python3", "modprobe", "qemu-system-x86_64", "blkzone", "lsblk", "nvme")},
              "kvm_present": Path("/dev/kvm").exists(), "configfs_present": Path("/sys/kernel/config").is_dir(),
              "devices": [], "kernel_config": {}, "read_only_probe": True}
    for path in (Path("/proc/config.gz"), Path(f"/boot/config-{kernel}")):
        if path.is_file():
            text = gzip.decompress(path.read_bytes()).decode() if path.suffix == ".gz" else path.read_text()
            report["kernel_config"] = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in text.splitlines()
                                       if line.startswith(("CONFIG_BLK_DEV_NULL_BLK=", "CONFIG_BLK_DEV_ZONED=", "CONFIG_CONFIGFS_FS="))}
            break
    for path in sorted(Path("/sys/block").glob("*")):
        zoned = path / "queue/zoned"
        report["devices"].append({"name": path.name, "zoned": zoned.read_text().strip() if zoned.exists() else None})
    if report["tools"]["modprobe"]:
        result = subprocess.run(["modprobe", "--show-depends", "null_blk"], capture_output=True, text=True, timeout=15)
        report["null_blk_module_probe"] = {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
