"""A real-byte interrupted-plan demonstration shared with the parity audit."""

from dataclasses import asdict

from .model import Rejected, SearchStatus
from .partial_recovery import conventional_partial_plan
from .profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from .revision_fixture import revision_fixture


def revision_demo(root, profile="2+1", workers=False, mode="conventional_cached", seed=20261012):
    profile_id = DEFAULT_PROFILE if profile == "2+1" else FOUR_PLUS_TWO
    store, fence, contents, parent, retained, targets = revision_fixture(root, profile_id, workers, mode, seed)
    store.set_offline("X", fence)
    initial = store.revision_snapshot("initial", targets, fence)
    result = conventional_partial_plan(initial)
    if result.status != SearchStatus.FOUND:
        raise AssertionError(result.reason)
    before = store.ledger()
    identifier = store.revise("initial", result.witness, targets, fence, "revision-demo", parent.digest())
    rejected = []
    for label, operation in (("old controller", lambda: store.step("initial", fence)),
                             ("old destination cleanup", lambda: store.cleanup("X:0", 1, fence))):
        try:
            operation()
        except Rejected as error:
            rejected.append({"operation": label, "reason": str(error)})
        else:
            raise AssertionError("Obsolete or claimed operation accepted")
    trace = []
    while store.plan_info(identifier)["status"] == "ACTIVE":
        step = store.step(identifier, fence)
        trace.append({"step": step, "ledger": store.ledger()})
    matches = {name: store.read_snapshot(name) == data for name, data in contents.items()}
    if not all(matches.values()) or not store.audit()["target"] or store.active_plans():
        raise AssertionError("Revision failed exact restoration")
    if any(a.kind == "stage" and a.slot == retained for a in result.witness.actions):
        raise AssertionError("Authenticated staging was needlessly rewritten")
    return {"scope": "Trusted local single-authority simulated domains; destination X offline",
            "profile": profile_id, "workers": workers, "validation_mode": mode,
            "initial": asdict(initial), "parent_witness": parent.to_dict(),
            "witness": result.witness.to_dict(), "retained_staged_slot": retained,
            "assignment_states": result.explored, "parent": store.plan_info("initial"),
            "successor": store.plan_info(identifier), "ledger_before_revision": before,
            "trace": trace, "audit": store.audit(), "ledger_final": store.ledger(),
            "readback_matches": matches, "rejections": rejected, "events": store.events(),
            "patent_rating_changed": False, "performance_advantage_claimed": False}
