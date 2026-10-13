"""Regression checks for the isolated R14-A executable mechanism screen."""

from dataclasses import replace
import unittest

from analysis.zoned_frontier_gate import (
    ConventionalIndex, Extent, FrontierIndex, ResetTicket, Snapshot,
    StaleEvidence, begin_reset, finish_reset, full_reset_allowed, retirement_safe,
)


class ZonedFrontierGateTests(unittest.TestCase):
    def test_retired_bytes_are_not_appendable_headroom(self):
        snapshot = Snapshot((Extent("live", "LIVE"), Extent("dead")), capacity=2, written=2)
        self.assertEqual(snapshot.appendable(), 0)
        self.assertFalse(full_reset_allowed(snapshot))

    def test_each_blocker_is_independently_required(self):
        for extent in (Extent("e", "LIVE"), Extent("e", "STAGED"), Extent("e", pins=1), Extent("e", grants=1)):
            with self.subTest(extent=extent):
                snapshot = Snapshot((extent,), written=1)
                self.assertFalse(full_reset_allowed(snapshot))
                self.assertFalse(ConventionalIndex(snapshot).allowed(snapshot))
                self.assertFalse(FrontierIndex(snapshot).allowed(snapshot))

    def test_inserted_member_and_unconsumed_hold_invalidate_old_evidence(self):
        original = Snapshot(holds=1)
        after, old = original.replace_extent(Extent("new", "LIVE"))
        self.assertEqual(after.holds, 1)
        for klass in (ConventionalIndex, FrontierIndex):
            with self.subTest(index=klass.__name__):
                index = klass(original)
                with self.assertRaises(StaleEvidence):
                    index.allowed(after)
                index.advance(original, after, old, after.extents[0])
                self.assertFalse(index.allowed(after))

    def test_pin_transfer_and_worker_drain_are_needed_before_reset(self):
        current = Snapshot((Extent("e", "RETIRED", 1, 1),), written=1)
        indexes = (ConventionalIndex(current), FrontierIndex(current))
        for pins, grants, allowed in ((0, 1, False), (0, 0, True)):
            with self.subTest(pins=pins, grants=grants):
                new = Extent("e", "RETIRED", pins, grants)
                after, old = current.replace_extent(new)
                for index in indexes:
                    index.advance(current, after, old, new)
                    self.assertEqual(index.allowed(after), allowed)
                self.assertEqual(full_reset_allowed(after), allowed)
                current = after

    def test_namespace_incarnation_fence_and_missing_event_fail_closed(self):
        initial = Snapshot()
        variants = (initial.change(namespace=2), initial.change(incarnation=2),
                    initial.change(fence=2), initial.change().change())
        for after in variants:
            for klass in (ConventionalIndex, FrontierIndex):
                with self.subTest(state=after, index=klass.__name__):
                    index = klass(initial)
                    with self.assertRaises(StaleEvidence):
                        index.allowed(after)
                    if after.revision == 2:
                        with self.assertRaises(StaleEvidence):
                            index.advance(initial, after)
                    else:
                        index.advance(initial, after)
                        self.assertTrue(index.allowed(after))

    def test_outage_holds_and_pending_reset_block_admission(self):
        for snapshot in (Snapshot(online=False), Snapshot(holds=1),
                         Snapshot(pending=ResetTicket("A", 1, 1, "r"))):
            with self.subTest(snapshot=snapshot):
                for klass in (ConventionalIndex, FrontierIndex):
                    self.assertFalse(klass(snapshot).allowed(snapshot))
                with self.assertRaises(ValueError):
                    begin_reset(snapshot, "new")

    def test_uncertain_reset_never_credits_capacity(self):
        before = Snapshot((Extent("e"),), capacity=1, written=1)
        pending, ticket = begin_reset(before, "r")
        uncertain = finish_reset(pending, ticket, False)
        self.assertEqual(uncertain, pending)
        self.assertEqual(uncertain.appendable(), 0)
        after = finish_reset(uncertain, ticket, True)
        self.assertEqual(after.appendable(), 1)
        self.assertEqual(after.incarnation, 2)
        with self.assertRaises(StaleEvidence):
            finish_reset(after, ticket, True)

    def test_stale_reset_identity_and_takeover_cannot_credit_capacity(self):
        pending, ticket = begin_reset(Snapshot(written=4), "r")
        for bad in (replace(ticket, operation="other"), replace(ticket, incarnation=2),
                    replace(ticket, zone="B"), replace(ticket, fence=2)):
            with self.subTest(ticket=bad), self.assertRaises(StaleEvidence):
                finish_reset(pending, bad, True)
        with self.assertRaises(StaleEvidence):
            finish_reset(pending.change(fence=2), ticket, True)

    def test_changed_dependency_after_reset_intent_cannot_be_erased(self):
        pending, ticket = begin_reset(Snapshot((Extent("e"),), written=1), "r")
        changed, _ = pending.replace_extent(Extent("e", pins=1))
        with self.assertRaises(StaleEvidence):
            finish_reset(changed, ticket, True)

    def test_coding_safety_is_checked_at_retirement_not_reset(self):
        copies = (("s", 0, "A"), ("b", 1, "B"), ("duplicate", 1, "D"))
        self.assertFalse(retirement_safe(copies, "s", 2))
        replacement = copies[:2] + (("replacement", 0, "D"),)
        self.assertTrue(retirement_safe(replacement, "s", 2))
        self.assertFalse(retirement_safe(replacement, "s", 2, ("D",)))
        self.assertFalse(full_reset_allowed(Snapshot((Extent("s", "LIVE"),), written=1)))

    def test_invalid_geometry_and_extent_cannot_create_headroom(self):
        for factory in (lambda: Extent("x", pins=-1), lambda: Snapshot(written=5),
                        lambda: Snapshot((Extent("x"), Extent("x")), written=2),
                        lambda: Snapshot(written=4, holds=1), lambda: Snapshot(written=1.0),
                        lambda: Snapshot(online="false")):
            with self.subTest(factory=factory), self.assertRaises(ValueError):
                factory()
        pending, ticket = begin_reset(Snapshot(written=4), "r")
        with self.assertRaises(ValueError):
            finish_reset(pending, ticket, "false")

    def test_retirement_contract_rejects_missing_and_invalid_rows(self):
        for copies, remove in (((("s", 9, "A"),), "s"), ((("s", 0, "A"),), "absent"),
                               ((("s", 0, "A"), ("s", 1, "B")), "s")):
            with self.subTest(copies=copies), self.assertRaises(ValueError):
                retirement_safe(copies, remove, 2)
