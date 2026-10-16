"""Explicit two-session continuation of the preserved 64-window E18 prefix."""

import argparse
import json
from pathlib import Path
import random

from prism_c.coding import digest
from prism_c.zoned_cost import ARMS, cost_window
from prism_c.zoned_measure import Archive, COUNT, MATCHED_SETS, RATE, SEED, UNIT, load_calibration, metadata, quality, summarize


ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "evidence/results/e18-characterization"


def schedule(selections):
    rng = random.Random(SEED + 1)
    result = []
    for selected in selections:
        for pair in range(MATCHED_SETS):
            order = list(ARMS)
            rng.shuffle(order)
            for position, arm in enumerate(order):
                result.append({**selected, "pair": pair, "order": order, "position": position, "arm": arm})
    return result


def validate_prefix(document, entries, folder):
    records = document["records"]
    if len(records) != 64 or (folder / "manifest.json").exists():
        raise ValueError("Expected original interrupted prefix without a final manifest")
    if {r["file"] for r in records} != {p.relative_to(folder).as_posix() for p in (folder / "windows").glob("*.json")}:
        raise ValueError("Unexpected/missing closed shard")
    for index, ref in enumerate(records):
        if ref["file"] != f"windows/window-{index:04d}.json":
            raise ValueError("Shard ordering changed")
        if any(ref[key] != value for key, value in entries[index].items()):
            raise ValueError("Saved prefix differs from registered schedule")
        raw = (folder / ref["file"]).read_bytes()
        if digest(raw) != ref["sha256"] or quality(json.loads(raw)) != ref["quality"]:
            raise ValueError("Saved shard/quality changed")
        if not ref["quality"]["collection_integrity"]:
            raise ValueError("Cannot resume after a collection failure")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    checks = sorted((FOLDER / "checkpoints").glob("checkpoint-*.json"))
    anchor = checks[-1]
    document = json.loads(anchor.read_bytes())
    current = metadata()
    for key in ("source_sha256", "protocol_sha256"):
        if current[key] != document["environment"][key]:
            raise ValueError("Frozen runtime/test/protocol source changed")
    calibration, sha = load_calibration(ROOT / "evidence/results/e18-calibration/manifest.json", document["environment"])
    if sha != document["calibration_sha256"] or calibration["selections"] != document["selections"]:
        raise ValueError("Calibration changed")
    entries = schedule(document["selections"])
    validate_prefix(document, entries, FOLDER)
    for path in checks:
        prefix = json.loads(path.read_bytes())["records"]
        if prefix != document["records"][:len(prefix)]:
            raise ValueError("Checkpoint history changed")
    if args.validate_only:
        print("PASS: 64 immutable windows; exact original schedule and frozen source/calibration")
        return
    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    document["continuation"] = {"environment": current, "start_window": 64,
        "checkpoint": anchor.relative_to(ROOT).as_posix(), "checkpoint_sha256": digest(anchor.read_bytes()),
        "helper_sha256": digest(Path(__file__).read_bytes()),
        "amendment_sha256": digest((ROOT / "experiments/e18_continuation_protocol.md").read_bytes()),
        "two_sessions": True, "original_incomplete_runtime_store_reused": False,
        "session_confounding_removed": False}
    archive = Archive.__new__(Archive)
    archive.root, archive.document, archive.checkpoints = FOLDER, document, len(checks)
    try:
        for index in range(64, len(entries)):
            entry = entries[index]
            record = cost_window(root / f"window-{index}", entry["profile"], UNIT, entry["groups"], entry["extra"], entry["arm"], COUNT, RATE)
            archive.add(record, pair=entry["pair"], order=entry["order"], position=entry["position"])
        document["summary"] = summarize(document["records"], document["selections"])
        document["success"] = document["summary"]["complete"]
    except Exception as error:
        document["error"] = repr(error)
    archive.checkpoint()
    archive.finish()
    print(json.dumps({"success": document["success"], "windows": len(document["records"]), "two_sessions": True}), flush=True)
    if not document["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
