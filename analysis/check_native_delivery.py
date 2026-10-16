"""Audit native journal campaign coverage, receipts and independent replay."""

from collections import Counter
import json
from pathlib import Path
import re
from urllib.parse import unquote

from prism_c.coding import digest
from prism_c.zoned_model import ZWitness, goal, replay, step
from prism_c.zoned_oracle import oracle_replay, reference_successors
from prism_c.zoned_store import state_from_dict, witness_from_dict


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT/"evidence/results"


def read(path):
    return json.loads(path.read_bytes())


def audit_campaign(document, *, expected_hashes, current_helpers=True):
    assert document["success"] and document["registered_cases"] == len(document["cases"]) == 84
    assert document["environment"]["source_sha256"] == expected_hashes
    assert not document["physical_power_loss_tested"] and not document["external_reproduction"] and not document["patent_rating_changed"]
    if current_helpers:
        for key, name in (("harness_sha256", "native_fault_campaign.py"), ("supervisor_sha256", "native_session_server.py"), ("qemu_driver_sha256", "qemu_zns_smoke.py")):
            assert document[key] == digest((ROOT/"analysis"/name).read_bytes())
        assert document["protocol_sha256"] == digest((ROOT/"experiments/native_authority_protocol.md").read_bytes())
    counts, profiles, sessions, receipts, completions = Counter(), Counter(), set(), 0, 0
    boundaries, nominal, delayed, edges = set(), set(), set(), set()
    for case in document["cases"]:
        assert case["success"] and "error" not in case
        profiles[case["profile"]] += 1
        counts[case["outcome"]] += 1
        binding = case["binding"]
        assert binding["session"] not in sessions
        sessions.add(binding["session"])
        initial = state_from_dict(case["initial"])
        witness = witness_from_dict(case["witness"])
        terminal = replay(initial, witness)
        assert terminal == oracle_replay(initial, witness) and goal(terminal)
        assert {n: ns["capacity_units"] for n, ns in binding["namespaces"].items()} == {z.name: z.capacity for z in initial.zones}
        rows = case["receipts"]
        assert [r["cursor"] for r in rows] == list(range(case["final_info"]["cursor"]))
        assert [r["action"] for r in rows] == case["witness"]["actions"][:len(rows)]
        assert all(r["stage_bytes"] == (4096 if r["action"]["kind"] == "stage" else 0) for r in rows)
        assert len({r["operation"] for r in rows if r["operation"]}) == sum(bool(r["operation"]) for r in rows)
        receipts += len(rows)
        prefix = ZWitness(initial.fingerprint(), witness.actions[:len(rows)])
        independent = initial
        for action in prefix.actions:
            candidates = [after for allowed, after in reference_successors(independent) if allowed == action]
            assert len(candidates) == 1
            independent = candidates[0]
        production = initial
        for action in prefix.actions:
            production = step(production, action)
        assert production == independent
        native = case["supervisor_report"]
        assert native["session"] == binding["session"] and all(c["status"] == 0 for c in native["command_completions"])
        completions += len(native["command_completions"])
        if case["fault"]:
            boundaries.add((case["profile"], *case["fault"]))
            assert case["actor_exit_code"] == 86
        if case["edge"] in ("altered_intent", "session_loss"):
            assert case["actor_exit_code"] == 86
        if case["delayed"]:
            assert case["actor_exit_code"] == -9
            delayed.add((case["profile"], case["delayed"]))
        if case["edge"]:
            edges.add((case["profile"], case["edge"]))
        if case["fault"] or case["delayed"] or case["edge"] in ("altered_intent", "session_loss"):
            counts["actor_terminations"] += 1
        if case["outcome"] in ("NOMINAL_EXACT_TARGET", "RESUMED_EXACT_TARGET"):
            assert len(rows) == len(witness.actions) and case["final_info"]["pending"] is None and case["final_info"]["quarantine"] is None
            assert case["native_writes_excluding_bootstrap"] == 2*sum(a.kind == "stage" for a in witness.actions)
            assert case["native_resets"] == sum(a.kind == "reset_ack" for a in witness.actions)
        if case["outcome"] == "NOMINAL_EXACT_TARGET":
            nominal.add((case["profile"], case["extra"], case["arm"]))
            assert not case["diagnostic_final_goal_relaxed_to_repair_only"]
            assert case["exact_prefixes"] == len(witness.actions)+1
        elif case["outcome"] != "CHANGED_SESSION_IDENTITY_REJECTED_BEFORE_IO":
            assert case["diagnostic_final_goal_relaxed_to_repair_only"]
        if case["outcome"] in ("PARTIAL_APPEND_QUARANTINED; SOURCES_RETAINED", "ALTERED_INTENT_REJECTED; NO_FREE_CREDIT", "SESSION_LOSS_FAILS_CLOSED; NOT POWER_LOSS_RECOVERY"):
            assert all(row["appendable_units"] == 0 for row in case["final_ledger"].values())
            assert case["final_info"]["pending"] is not None
        if case["outcome"] == "PARTIAL_APPEND_QUARANTINED; SOURCES_RETAINED":
            assert case["final_info"]["quarantine"]
        if case["outcome"] not in ("NOMINAL_EXACT_TARGET", "CHANGED_SESSION_IDENTITY_REJECTED_BEFORE_IO", "SESSION_LOSS_FAILS_CLOSED; NOT POWER_LOSS_RECOVERY"):
            assert case["stale_actor_and_native_request_rejected_without_submission"]
    expected = {(p, kind, boundary) for p in profiles for kind in ("open", "close", "finish", "stage", "reset_ack")
                for boundary in ("before_prepare", "after_prepare", "before_io", "after_io", "before_commit", "after_commit")}
    expected |= {(p, "stage", "half_io") for p in profiles}
    expected |= {(p, "reset_request", b) for p in profiles for b in ("before_commit", "after_commit")}
    assert boundaries == expected and len(boundaries) == 66
    assert profiles == {"xor-2+1-v1": 42, "pq-4+2-gf256-v1": 42}
    assert nominal == {(p, extra, arm) for p in profiles for extra in (False, True) for arm in ("joint", "separated")}
    assert delayed == {(p, kind) for p in profiles for kind in ("stage", "reset_ack")}
    assert edges == {(p, kind) for p in profiles for kind in ("identity", "altered_intent", "session_loss")}
    assert counts == {"actor_terminations": 74, "NOMINAL_EXACT_TARGET": 8, "RESUMED_EXACT_TARGET": 66,
                      "PARTIAL_APPEND_QUARANTINED; SOURCES_RETAINED": 4,
                      "CHANGED_SESSION_IDENTITY_REJECTED_BEFORE_IO": 2,
                      "ALTERED_INTENT_REJECTED; NO_FREE_CREDIT": 2,
                      "SESSION_LOSS_FAILS_CLOSED; NOT POWER_LOSS_RECOVERY": 2}
    return {"cases": 84, "outcomes": dict(counts), "unique_sessions": len(sessions),
            "receipts_independently_replayed": receipts, "successful_nvme_completions": completions,
            "full_source_hashes_match": True, "boundary_coverage": 66}


def audit_operations(campaign_path, operation_manifest):
    campaign = read(campaign_path)
    operations = read(operation_manifest)
    assert operations["campaign_sha256"] == digest(campaign_path.read_bytes())
    assert len(operations["cases"]) == 84
    markers = 0
    for index, (case, ref) in enumerate(zip(campaign["cases"], operations["cases"])):
        path = operation_manifest.parent/ref["file"]
        raw = path.read_bytes()
        assert digest(raw) == ref["sha256"]
        events = json.loads(raw)
        assert ref["case"] == index and len(events) == ref["events"]
        submitted = [i for i, e in enumerate(events) if e["event"] == "submitted_unacknowledged"]
        if case["delayed"]:
            assert len(submitted) == 1
            at = submitted[0]
            original = events[at]
            completion = next(i for i in range(at+1, len(events)) if events[i]["event"] == "completed"
                              and all(events[i].get(k) == original.get(k) for k in ("op", "zone", "fence", "operation", "offset", "action")))
            later_fence = next(i for i in range(at+1, len(events)) if events[i]["event"] == "started" and events[i]["fence"] == 2)
            assert completion < later_fence
            assert original["nvme_opcode"] == (1 if case["delayed"] == "stage" else 0x79)
            markers += 1
        else:
            assert not submitted
        assert case["native_writes_excluding_bootstrap"] == sum(e["event"] == "started" and e["op"] == "write" and e["operation"] != "bootstrap" for e in events)
        assert case["native_resets"] == sum(e["event"] == "started" and e["op"] == "manage" and e["action"] == 4 for e in events)
    assert markers == 4
    return {"operation_shards_verified": 84, "submitted_command_drain_orderings_verified": 4,
            "operation_manifest_sha256": digest(operation_manifest.read_bytes())}


def main():
    verification = read(RESULTS/"verification-e21.json")
    assert verification["success"] and verification["failures"] == verification["errors"] == 0
    hashes = verification["environment"]["source_sha256"]
    assert len(hashes) == 76
    assert all(digest((ROOT/name).read_bytes()) == sha for name, sha in hashes.items())
    local_path = RESULTS/"native-authority-e21.json"
    assert local_path.read_bytes() == (RESULTS/"native-authority-e21-r1.json").read_bytes()
    report = {"date": "2026-10-16", "local": audit_campaign(read(local_path), expected_hashes=hashes),
              "test_methods": verification["test_methods"], "subtests": verification["subtests"],
              "matching_source_test_hashes": len(hashes), "physical_power_loss_tested": False,
              "independent_external_reproduction": False, "patent_readiness": 55,
              "audit_script_sha256": digest(Path(__file__).read_bytes())}
    report["local"].update(audit_operations(local_path, RESULTS/"native-e21-operations/manifest.json"))
    ci_path = RESULTS/"native-authority-e21-ci.json"
    if ci_path.exists():
        report["remote_native_ci"] = audit_campaign(read(ci_path), expected_hashes=hashes)
        report["remote_native_ci"].update(audit_operations(ci_path, RESULTS/"native-e21-ci-operations/manifest.json"))
    ci = read(RESULTS/"ci-e21.json")
    assert ci["conclusion"] == "success" and len(ci["jobs"]) == 3 and all(j["conclusion"] == "success" for j in ci["jobs"])
    assert ci["source_commit"] == read(ci_path)["git_head_at_start"] == "49db8a156b1f62bb8399cdf1f5a979e19d5f2b09"
    assert (ci["test_methods"], ci["subtests"], ci["matching_source_test_hashes"]) == (224, 691, 76)
    prior = read(RESULTS/"verification-e19.json")["environment"]["source_sha256"]
    assert len(prior) == 74 and all(hashes[name] == sha for name, sha in prior.items())
    report["unchanged_e19_source_test_files"] = len(prior)
    for platform in ("ubuntu", "windows"):
        ci_verification = read(RESULTS/f"verification-e21-ci-{platform}.json")
        assert ci_verification["success"] and ci_verification["failures"] == ci_verification["errors"] == 0
        assert ci_verification["environment"]["source_sha256"] == hashes
        assert (ci_verification["test_methods"], ci_verification["subtests"]) == (verification["test_methods"], verification["subtests"])
        assert ci_verification["campaign"]["traces"] == ci["ci_model_traces_per_platform"] == 1000
    assert verification["campaign"]["traces"] == ci["local_model_traces"] == 10000
    report["both_platform_correctness_ci_hashes_match"] = True
    documents = list(ROOT.glob("*.md")) + list((ROOT/"spec").glob("*.md")) + list((ROOT/"experiments").glob("*.md")) + list((ROOT/"evidence").rglob("*.md"))
    links = 0
    for document in documents:
        for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#", "app://", "codex://")):
                continue
            target = unquote(target.split("#")[0])
            if target:
                resolved = (document.parent/target).resolve()
                assert resolved == RESULTS/"e21-evidence-check.json" or resolved.exists(), (document, target)
                links += 1
    report.update(local_document_links_checked=links, broken_local_links=0)
    with (RESULTS/"e21-evidence-check.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
