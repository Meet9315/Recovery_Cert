"""Copy closed E21 operation logs into immutable per-case JSON evidence shards."""

import argparse
import json
from pathlib import Path

from prism_c.coding import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-in-campaign-only", action="store_true",
                        help="CI artifact contains closed summary in campaign JSON, not a duplicate per-case file")
    args = parser.parse_args()
    root, report_path, output = Path(args.root), Path(args.report), Path(args.output)
    report = json.loads(report_path.read_bytes())
    if not report["success"] or len(report["cases"]) != 84:
        raise ValueError("Archive only a complete successful campaign; retain failed raw data separately")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"campaign_sha256": digest(report_path.read_bytes()), "cases": [],
                "supervisor_summary_source": "campaign report only" if args.summary_in_campaign_only else "per-case file and campaign report"}
    for index, case in enumerate(report["cases"]):
        raw = (root/f"case-{index:03d}/device/operations.jsonl").read_bytes()
        events = [json.loads(line) for line in raw.splitlines()]
        if not args.summary_in_campaign_only:
            closed = json.loads((root/f"case-{index:03d}/device/supervisor-report.json").read_bytes())
            if closed != case["supervisor_report"]:
                raise ValueError("Supervisor report changed")
        saved = (json.dumps(events, sort_keys=True, indent=2)+"\n").encode()
        name = f"case-{index:03d}.json"
        with (output/name).open("xb") as handle:
            handle.write(saved)
        manifest["cases"].append({"case": index, "file": name, "sha256": digest(saved),
                                  "events": len(events), "original_jsonl_sha256": digest(raw)})
    with (output/"manifest.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("Archived", len(manifest["cases"]), "closed native operation logs")


if __name__ == "__main__":
    main()
