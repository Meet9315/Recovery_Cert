"""Independent bounded planning, physical-ledger and RAM coding regressions."""

from dataclasses import replace
import unittest
from unittest.mock import patch

from prism_c.model import Rejected, SearchStatus
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO
from prism_c.zoned_baseline import conventional_zoned_plan, lower_bound, separated_gc_plan
from prism_c.zoned_campaign import check_memory_bytes, run_zoned_campaign, zoned_fixture
from prism_c.zoned_model import ZAction, ZExtent, ZStripe, ZZone, ZWitness, ZonedState, goal, replay, step, validate
from prism_c.zoned_oracle import oracle_replay, reference_successors, zoned_oracle


class ZonedJointTests(unittest.TestCase):
    def test_joint_route_reuses_staging_and_matches_independent_optimum(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            with self.subTest(profile=profile):
                s = zoned_fixture(profile)
                joint, control = conventional_zoned_plan(s), separated_gc_plan(s)
                oracle = zoned_oracle(s)
                self.assertEqual(joint.status, SearchStatus.FOUND)
                self.assertEqual(joint.score, (1, 8))
                self.assertEqual(control.score[0], 2)
                self.assertEqual(joint.score, oracle[2])
                self.assertEqual(replay(s, joint.witness), oracle_replay(s, joint.witness))
                self.assertEqual(replay(s, oracle[1]), oracle_replay(s, oracle[1]))
                self.assertTrue(check_memory_bytes(s, joint.witness)["exact_contents"])

    def test_declared_matrix_has_no_feasibility_or_objective_disagreements(self):
        result = run_zoned_campaign()
        self.assertEqual((result["cases"], result["found"], result["infeasible"], result["unknown"]), (32, 12, 20, 0))
        self.assertEqual(result["strict_stage_savings_vs_restricted_control"], 2)
        self.assertFalse(result["patent_advantage_claimed"])

    def test_no_gain_is_inferred_when_control_has_extra_headroom(self):
        s = zoned_fixture(extra=True)
        joint, control = conventional_zoned_plan(s), separated_gc_plan(s)
        self.assertEqual(joint.score[0], control.score[0])

    def test_initial_staging_removes_a_mandatory_write_from_lower_bound(self):
        self.assertEqual(lower_bound(zoned_fixture()), 0)
        self.assertEqual(lower_bound(zoned_fixture(staged=False)), 1)
        s = zoned_fixture()
        result = conventional_zoned_plan(s, use_bound=False)
        self.assertEqual(result.score, conventional_zoned_plan(s).score)

    def test_retirement_is_logical_and_reset_ack_releases_physical_headroom(self):
        s = zoned_fixture()
        s = step(s, ZAction("promote", "X", 1, 0))
        s = step(s, ZAction("retire", "A", 1, 0))
        self.assertEqual(s.zones[0].appendable(), 0)
        pending = step(s, ZAction("reset_request", "A", 1))
        self.assertEqual(pending.zones[0].appendable(), 0)
        self.assertEqual(len(pending.zones[0].extents), 2)
        after = step(pending, ZAction("reset_ack", "A", 1))
        self.assertEqual(after.zones[0].appendable(), 2)
        self.assertEqual(after.zones[0].incarnation, 2)
        with self.assertRaises(Rejected):
            step(after, ZAction("reset_ack", "A", 1))

    def test_reset_does_not_erase_live_staged_pinned_or_granted_extents(self):
        s = zoned_fixture()
        for zone in (s.zones[0], s.zones[-1]):
            with self.subTest(zone=zone.name), self.assertRaises(Rejected):
                step(s, ZAction("reset_request", zone.name, 1))
        for e in (ZExtent(pins=1), ZExtent(grants=1)):
            zones = s.zones + (ZZone("D", "D", 1, (e,), "FULL"),)
            with self.subTest(extent=e), self.assertRaises(Rejected):
                step(replace(s, zones=zones), ZAction("reset_request", "D", 1))

    def test_pinned_blocker_is_not_automatically_unpinned(self):
        s = zoned_fixture(locked=True)
        self.assertEqual(conventional_zoned_plan(s).status, SearchStatus.INFEASIBLE)
        self.assertEqual(zoned_oracle(s)[0], SearchStatus.INFEASIBLE)
        with self.assertRaises(Rejected):
            step(s, ZAction("retire", "A", 1, 0))

    def test_pending_reset_keeps_open_and_active_tokens_until_ack(self):
        s = zoned_fixture(staged=False)
        zones = (ZZone("A", "A", 2, (ZExtent(),), "OPEN"),) + s.zones[1:]
        # Put row zero on an additional full source while A is all-dead.
        zones += (ZZone("S", "S", 1, (ZExtent("LIVE", "object", 0, pins=1),), "FULL"),)
        s = replace(s, zones=zones, reclaim=(), stripes=(replace(s.stripes[0], eligible=s.stripes[0].eligible+("S",)),))
        pending = step(s, ZAction("reset_request", "A", 1))
        self.assertTrue(pending.zones[0].uses_open())
        self.assertTrue(pending.zones[0].uses_active())
        with self.assertRaises(Rejected):
            step(pending, ZAction("open", "X", 1))
        self.assertFalse(any(a.kind == "open" and a.zone == "X" for a, _ in reference_successors(pending)))
        after = step(pending, ZAction("reset_ack", "A", 1))
        self.assertEqual(step(after, ZAction("open", "X", 1)).zones[-2].phase, "OPEN")

    def test_active_token_requires_finish_and_finish_strands_tail(self):
        s = zoned_fixture(staged=False)
        zone = replace(s.zones[0], extents=s.zones[0].extents[:1], phase="CLOSED")
        s = replace(s, zones=(zone,)+s.zones[1:], reclaim=())
        with self.assertRaises(Rejected):
            step(s, ZAction("open", "X", 1))
        after = step(s, ZAction("finish", "A", 1))
        self.assertEqual(after.zones[0].appendable(), 0)
        self.assertEqual(step(after, ZAction("open", "X", 1)).zones[-1].phase, "OPEN")

    def test_external_append_holds_are_not_reusable_or_finishable(self):
        s = zoned_fixture(staged=False)
        zones = s.zones + (ZZone("H", "H", 2, (ZExtent(),), "CLOSED", external_hold=1),)
        s = replace(s, zones=zones, reclaim=(("H", 1),))
        self.assertEqual(conventional_zoned_plan(s).status, SearchStatus.INFEASIBLE)
        self.assertEqual(zoned_oracle(s)[0], SearchStatus.INFEASIBLE)
        for kind in ("finish", "reset_request"):
            with self.subTest(kind=kind), self.assertRaises(Rejected):
                step(s, ZAction(kind, "H", 1))

    def test_duplicate_rows_and_colocated_domains_do_not_replace_fault_protection(self):
        s = zoned_fixture(FOUR_PLUS_TWO)
        zones = list(s.zones)
        zones[1] = replace(zones[1], domain="A")
        spec = replace(s.stripes[0], eligible=tuple(dict.fromkeys(z.domain for z in zones)))
        unsafe = replace(s, zones=tuple(zones), stripes=(spec,))
        self.assertEqual(conventional_zoned_plan(unsafe).status, SearchStatus.INFEASIBLE)
        self.assertEqual(zoned_oracle(unsafe)[0], SearchStatus.INFEASIBLE)
        duplicate = replace(s.zones[-1], extents=(ZExtent("STAGED", "object", 1),))
        s = replace(s, zones=s.zones[:-1]+(duplicate,))
        promoted = step(s, ZAction("promote", "X", 1, 0))
        with self.assertRaises(Rejected):
            step(promoted, ZAction("retire", "A", 1, 0))

    def test_exhausted_search_never_returns_an_installable_witness(self):
        for budget in (0, 1):
            with self.subTest(budget=budget):
                joint = conventional_zoned_plan(zoned_fixture(), budget)
                reference = zoned_oracle(zoned_fixture(), budget)
                self.assertEqual(joint.status, SearchStatus.UNKNOWN)
                self.assertEqual(reference[0], SearchStatus.UNKNOWN)
                self.assertIsNone(joint.witness)
                self.assertIsNone(reference[1])

    def test_stale_scope_and_incarnation_witnesses_reject(self):
        s = zoned_fixture()
        w = conventional_zoned_plan(s).witness
        for checker in (replay, oracle_replay):
            with self.subTest(checker=checker.__name__):
                with self.assertRaises(Rejected):
                    checker(replace(s, max_open=2), w)
                bad = replace(w.actions[-1], incarnation=1)
                with self.assertRaises(Rejected):
                    checker(s, ZWitness(w.initial, w.actions[:-1]+(bad,)))

    def test_reference_does_not_call_production_transition_or_goal(self):
        s = zoned_fixture()
        with patch("prism_c.zoned_model.step", side_effect=AssertionError("shared transition")), patch("prism_c.zoned_model.goal", side_effect=AssertionError("shared goal")):
            status, witness, score, _ = zoned_oracle(s)
            self.assertEqual(status, SearchStatus.FOUND)
            self.assertEqual(score, (1, 8))
            self.assertIsNotNone(oracle_replay(s, witness))

    def test_invalid_geometry_and_working_copy_budget_reject(self):
        s = zoned_fixture()
        cases = (replace(s, max_open=-1), replace(s, zones=s.zones[:1]+(s.zones[0],)),
                 replace(s, zones=(replace(s.zones[0], external_hold=1),)+s.zones[1:]),
                 replace(s, zones=(replace(s.zones[0], extents=list(s.zones[0].extents)),)+s.zones[1:]),
                 replace(s, zones=s.zones+(ZZone("Q", "Q", 1, (ZExtent("LIVE", "object", 0),), "FULL"),
                                         ZZone("R", "R", 1, (ZExtent("LIVE", "object", 1),), "FULL"))))
        for invalid in cases:
            with self.subTest(state=invalid), self.assertRaises(Rejected):
                validate(invalid)

    def test_two_stripes_share_zone_budgets_and_restore_both(self):
        zones = tuple(ZZone(name, name, 1, (ZExtent("LIVE", stripe, row, pins=1),), "FULL")
                      for name, stripe, row in (("S", "a", 0), ("T", "a", 1), ("U", "b", 0), ("V", "b", 1)))
        zones += (ZZone("X", "X", 1), ZZone("Y", "Y", 1))
        domains = tuple(z.domain for z in zones)
        s = ZonedState((ZStripe("a", domains), ZStripe("b", domains)), zones)
        result = conventional_zoned_plan(s)
        reference = zoned_oracle(s)
        self.assertEqual(result.status, SearchStatus.FOUND)
        self.assertEqual(result.score, reference[2])
        self.assertEqual(result.score[0], 2)
        self.assertTrue(goal(replay(s, result.witness)))
        byte_report = check_memory_bytes(s, result.witness)
        self.assertTrue(byte_report["exact_contents"])
        self.assertEqual(len(set(byte_report["object_sha256"].values())), 2)
