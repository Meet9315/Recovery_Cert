"""R14-A executable mechanism screen, not a zoned storage controller.

Compare a blocker-set frontier, ordinary indexed counters and independent
full-state recomputation. All states and receipts are metadata in memory.
No physical writes, durable authority, native integration or timings.
"""

import argparse
from dataclasses import asdict, dataclass, replace
import hashlib
import itertools
import json
from pathlib import Path
import subprocess


class StaleEvidence(ValueError):
    pass


@dataclass(frozen=True)
class Extent:
    identity: str
    state: str = "RETIRED"
    pins: int = 0
    grants: int = 0

    def __post_init__(self):
        if (not self.identity or self.state not in ("LIVE", "STAGED", "RETIRED")
                or type(self.pins) is not int or self.pins < 0
                or type(self.grants) is not int or self.grants < 0):
            raise ValueError("Invalid extent")


@dataclass(frozen=True)
class ResetTicket:
    zone: str
    incarnation: int
    fence: int
    operation: str


@dataclass(frozen=True)
class Snapshot:
    extents: tuple[Extent, ...] = ()
    zone: str = "A"
    capacity: int = 4
    written: int = 0
    holds: int = 0
    online: bool = True
    incarnation: int = 1
    revision: int = 0
    namespace: int = 1
    fence: int = 1
    pending: ResetTicket | None = None

    def __post_init__(self):
        if (any(type(value) is not int for value in
                (self.capacity, self.written, self.holds, self.incarnation,
                 self.revision, self.namespace, self.fence))
                or type(self.online) is not bool or not self.zone
                or not 0 <= self.written <= self.capacity
                or len(self.extents) > self.written or self.holds < 0
                or self.holds > self.capacity - self.written
                or min(self.incarnation, self.namespace, self.fence) < 1
                or self.revision < 0
                or len({e.identity for e in self.extents}) != len(self.extents)):
            raise ValueError("Invalid bounded geometry/identity")

    def token(self):
        # These counters are authority-owned, not supplied by a proof producer.
        return (self.zone, self.namespace, self.incarnation, self.revision,
                self.fence, self.capacity, self.written, self.holds,
                self.online, self.pending)

    def change(self, **changes):
        if "revision" in changes:
            raise ValueError("Revision is derived by authority mutation")
        return replace(self, revision=self.revision + 1, **changes)

    def replace_extent(self, extent):
        items = {e.identity: e for e in self.extents}
        old = items.get(extent.identity)
        items[extent.identity] = extent
        ordered = tuple(items[k] for k in sorted(items))
        # Insertion is an append of a unit extent, not logical slot reuse.
        written = self.written + (old is None)
        return self.change(extents=ordered, written=written), old

    def appendable(self):
        if not self.online or self.pending is not None:
            return 0
        return self.capacity - self.written - self.holds


def full_reset_allowed(snapshot):
    """Independent reference: no aggregate/set/checker calls."""
    if not snapshot.online or snapshot.pending is not None or snapshot.holds:
        return False
    for extent in snapshot.extents:
        if extent.state != "RETIRED" or extent.pins != 0 or extent.grants != 0:
            return False
    return True


class ConventionalIndex:
    """Ordinary retained-object, pin and grant counters with a generation guard."""

    def __init__(self, snapshot):
        self.retained = sum(e.state != "RETIRED" for e in snapshot.extents)
        self.pins = sum(e.pins for e in snapshot.extents)
        self.grants = sum(e.grants for e in snapshot.extents)
        self.bound = snapshot.token()

    def allowed(self, snapshot):
        if self.bound != snapshot.token():
            raise StaleEvidence("Conventional index requires update/rebuild")
        return (snapshot.online and snapshot.pending is None and snapshot.holds == 0
                and self.retained == self.pins == self.grants == 0)

    def advance(self, before, after, old=None, new=None):
        if self.bound != before.token() or after.revision != before.revision + 1:
            raise StaleEvidence("Noncontiguous authoritative event")
        if old is not None:
            self.retained -= old.state != "RETIRED"
            self.pins -= old.pins
            self.grants -= old.grants
        if new is not None:
            self.retained += new.state != "RETIRED"
            self.pins += new.pins
            self.grants += new.grants
        self.bound = after.token()


class FrontierIndex:
    """Proposed explicit per-extent blocker set, with the same authority guard."""

    @staticmethod
    def reasons(extent):
        reasons = set()
        if extent.state in ("LIVE", "STAGED"):
            reasons.add((extent.identity, "retained"))
        if extent.pins:
            reasons.add((extent.identity, "pin"))
        if extent.grants:
            reasons.add((extent.identity, "grant"))
        return reasons

    def __init__(self, snapshot):
        self.blockers = set()
        for extent in snapshot.extents:
            self.blockers.update(self.reasons(extent))
        self.bound = snapshot.token()

    def allowed(self, snapshot):
        if self.bound != snapshot.token():
            raise StaleEvidence("Frontier requires update/rebuild")
        return (snapshot.online and snapshot.pending is None and snapshot.holds == 0
                and not self.blockers)

    def advance(self, before, after, old=None, new=None):
        if self.bound != before.token() or after.revision != before.revision + 1:
            raise StaleEvidence("Noncontiguous authoritative event")
        if old is not None:
            self.blockers.difference_update(self.reasons(old))
        if new is not None:
            self.blockers.update(self.reasons(new))
        self.bound = after.token()


def begin_reset(snapshot, operation):
    if not operation or not full_reset_allowed(snapshot):
        raise ValueError("Reset is not admitted")
    ticket = ResetTicket(snapshot.zone, snapshot.incarnation, snapshot.fence, operation)
    return snapshot.change(pending=ticket), ticket


def finish_reset(snapshot, ticket, confirmed):
    """In-memory accounting example; no device reset or durability is asserted."""
    if type(confirmed) is not bool:
        raise ValueError("A boolean confirmed device outcome is required")
    if (ticket != snapshot.pending or ticket.zone != snapshot.zone
            or ticket.incarnation != snapshot.incarnation or ticket.fence != snapshot.fence):
        raise StaleEvidence("Receipt is not bound to current reset")
    # Unexpected membership changes still cannot authorize deletion of live data.
    if not full_reset_allowed(replace(snapshot, pending=None)):
        raise StaleEvidence("Reset dependencies changed")
    if not confirmed:
        return snapshot
    return snapshot.change(extents=(), written=0, pending=None,
                           incarnation=snapshot.incarnation + 1)


def retirement_safe(copies, remove, k, failures=()):
    """Separate finite MDS retirement rule; copies=(identity,row,domain).

    This is not the reset checker, optimizer, a byte-authentication proof or a
    new coding construction. Domain failure scenarios are checked one at a time.
    """
    if (k not in (2, 4) or len({c[0] for c in copies}) != len(copies)
            or remove not in {c[0] for c in copies}
            or any(type(c[1]) is not int or c[1] not in range(k + (1 if k == 2 else 2))
                   for c in copies)):
        raise ValueError("Invalid finite coding contract")
    remaining = [c for c in copies if c[0] != remove]
    return all(len({row for _, row, domain in remaining if domain != fault}) >= k
               for fault in (None,) + tuple(failures))


def matrix():
    options = tuple(itertools.product(("RETIRED", "LIVE", "STAGED"), (0, 1), (0, 1)))
    for size in (0, 1, 2):
        for attributes in itertools.product(options, repeat=size):
            extents = tuple(Extent(f"e{i}", *values) for i, values in enumerate(attributes))
            for online, holds, pending in itertools.product((False, True), (0, 1), (False, True)):
                ticket = ResetTicket("A", 1, 1, "seed-reset") if pending else None
                yield Snapshot(extents, written=size, online=online, holds=holds, pending=ticket)


def collect():
    records = []
    comparisons = mutations = stale_rejections = 0
    for number, initial in enumerate(matrix()):
        baseline, frontier = ConventionalIndex(initial), FrontierIndex(initial)
        expected = full_reset_allowed(initial)
        assert baseline.allowed(initial) == frontier.allowed(initial) == expected
        assert baseline.allowed(initial) == frontier.allowed(initial) == expected  # warm guard
        comparisons += 2
        variants = [(initial.change(online=not initial.online), None, None, "domain")]
        variants += [(initial.change(holds=1-initial.holds), None, None, "hold"),
                     (initial.change(fence=2), None, None, "takeover"),
                     (initial.change(namespace=2), None, None, "namespace"),
                     (initial.change(incarnation=2), None, None, "incarnation")]
        inserted = Extent("inserted", "LIVE")
        after, old = initial.replace_extent(inserted)
        # A held unit may not be silently consumed by an unrelated append.
        variants.append((after, old, inserted, "inserted-membership"))
        for existing in initial.extents:
            for state, pins, grants in itertools.product(("RETIRED", "LIVE", "STAGED"), (0, 1), (0, 1)):
                new = Extent(existing.identity, state, pins, grants)
                after, old = initial.replace_extent(new)
                variants.append((after, old, new, "extent-update"))
        for after, old, new, event in variants:
            ordinary, proposed = ConventionalIndex(initial), FrontierIndex(initial)
            for index in (ordinary, proposed):
                try:
                    index.allowed(after)
                except StaleEvidence:
                    stale_rejections += 1
                else:
                    raise AssertionError("Changed membership/state accepted by stale evidence")
                index.advance(initial, after, old, new)
            result = full_reset_allowed(after)
            assert ordinary.allowed(after) == proposed.allowed(after) == result
            comparisons += 1
            mutations += 1
        records.append({"case": number, "initial": asdict(initial), "reset_allowed": expected,
                        "mutation_checks": len(variants), "disagreements": 0})
    full = Snapshot((Extent("source", "LIVE", 1), Extent("d0"), Extent("d1"), Extent("d2")), written=4)
    all_dead = full.change(extents=tuple(replace(e, state="RETIRED", pins=0) for e in full.extents))
    pending, ticket = begin_reset(all_dead, "reclaim-A")
    uncertain = finish_reset(pending, ticket, False)
    confirmed = finish_reset(pending, ticket, True)
    assert full.appendable() == uncertain.appendable() == 0 and confirmed.appendable() == 4
    coding = {"critical_row_rejected": not retirement_safe((("s", 0, "A"), ("b", 1, "B")), "s", 2),
              "duplicate_row_rejected": not retirement_safe((("s", 0, "A"), ("b", 1, "B"), ("dup", 1, "D")), "s", 2),
              "replacement_admitted": retirement_safe((("s", 0, "A"), ("b", 1, "B"), ("copy", 0, "D")), "s", 2),
              "fault_floor_rejected": not retirement_safe((("s", 0, "A"), ("b", 1, "B"), ("copy", 0, "D")), "s", 2, ("D",)),
              "four_plus_two_critical_rejected": not retirement_safe(tuple((str(i), i, str(i)) for i in range(4)), "0", 4),
              "four_plus_two_redundancy_admitted": retirement_safe(tuple((str(i), i, str(i)) for i in range(6)), "0", 4, ("1",))}
    assert all(coding.values())
    return {"cases": len(records), "decision_comparisons": comparisons,
            "authoritative_mutations": mutations, "stale_guard_rejections": stale_rejections,
            "disagreements": 0, "case_records": records, "coding_retirement_checks": coding,
            "capacity_example": {"logical_retired_units": 3, "initial_appendable_units": full.appendable(),
                                 "uncertain_reset_appendable_units": uncertain.appendable(),
                                 "confirmed_reset_appendable_units": confirmed.appendable()},
            "mechanism_gate": "NO_DISTINCTION_FOR_SPECIFIED_FRONTIER",
            "physical_controller_implemented": False, "timing_campaign_performed": False,
            "scope": "Finite reset-index equivalence and in-memory receipt accounting, not repair planning/native I/O",
            "complexity": {"both_build": "O(E)", "both_single_extent_update": "O(1) fixed reason classes",
                           "both_guard_query": "O(1)", "reference_scan": "O(E)",
                           "notes": "Abstract operation bounds, not measured CPU performance or worst-case hash-table bounds"}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    path = Path(args.report)
    if path.exists():
        raise ValueError("Use a fresh report path; old evidence is not overwritten")
    root = Path(__file__).resolve().parent.parent
    source_names = ("analysis/zoned_frontier_gate.py", "tests/test_zoned_frontier_gate.py",
                    "spec/zoned_frontier_screen.md", "experiments/zoned_frontier_protocol.md")
    metadata = {"git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
                "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                  for name in source_names}}
    try:
        report = {"environment": metadata, "success": True, **collect()}
    except Exception as error:
        report = {"environment": metadata, "success": False, "error": repr(error)}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("case_records", "environment")}, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
