import itertools
import unittest
from dataclasses import replace

from prism_c.baseline import conventional_plan
from prism_c.checker import check, replay
from prism_c.coding import encode, recover
from prism_c.model import Action, Rejected, SearchStatus, Slot, State, Stripe, Witness, fixture, plan


class ModelTests(unittest.TestCase):
    def test_matching_baseline_avoids_greedy_dead_end(self):
        initial = fixture()
        witness = conventional_plan(initial)
        self.assertIsNotNone(witness)
        self.assertTrue(check(initial, witness).target())
        placements = {a.stripe: a.slot for a in witness.actions if a.kind == "reserve"}
        self.assertEqual(placements, {"A": "Y0", "B": "X0"})

    def test_reclamation_is_an_explicit_predecessor(self):
        initial = fixture(reclamation=True)
        result = plan(initial)
        self.assertEqual(result.status, SearchStatus.FOUND)
        self.assertTrue(check(initial, result.witness).target())
        x_actions = [a.kind for a in result.witness.actions if a.slot == "X0"]
        self.assertEqual(x_actions, ["reclaim", "reserve", "stage", "promote"])

    def test_budgets_never_claim_infeasibility(self):
        self.assertEqual(plan(fixture(), max_states=1).status, SearchStatus.UNKNOWN)
        self.assertEqual(plan(fixture(), max_steps=1).status, SearchStatus.UNKNOWN)
        self.assertEqual(plan(fixture(), max_states=0).status, SearchStatus.UNKNOWN)

    def test_infeasible_is_relative_to_complete_grammar(self):
        self.assertEqual(plan(fixture(infeasible=True)).status, SearchStatus.INFEASIBLE)
        self.assertIsNone(conventional_plan(fixture(infeasible=True)))

    def test_incomplete_terminal_rejected(self):
        witness = conventional_plan(fixture())
        with self.assertRaises(Rejected):
            check(fixture(), replace(witness, actions=witness.actions[:-1]))

    def test_snapshot_and_version_conflict(self):
        witness = conventional_plan(fixture())
        for bad in (replace(witness, initial="bad"), replace(witness, version=2),
                    replace(witness, terminal="bad")):
            with self.assertRaises(Rejected):
                check(fixture(), bad)

    def test_tampered_serialized_digest(self):
        value = conventional_plan(fixture()).to_dict()
        value["terminal"] = "forged"
        with self.assertRaises(Rejected):
            Witness.from_dict(value)

    def test_double_spending_and_future_free_space(self):
        initial = fixture(reclamation=True)
        with self.assertRaises(Rejected):
            replay(initial, (Action("reserve", "X0", "B", 2, 1),), False)
        actions = (Action("reserve", "Y0", "A", 2, 0), Action("reserve", "Y0", "B", 2, 1))
        with self.assertRaises(Rejected):
            replay(initial, actions, False)

    def test_live_retirement_below_floor_is_rejected(self):
        with self.assertRaises(Rejected):
            replay(fixture(), (Action("retire", "A0", "A", 0, 1),), False)

    def test_generation_and_row_identity_checked(self):
        with self.assertRaises(Rejected):
            replay(fixture(), (Action("stage", "A0", "A", 1, 1),), False)
        with self.assertRaises(Rejected):
            replay(fixture(), (Action("reserve", "Y0", "A", 2, 99),), False)

    def test_independent_matching_oracle_all_small_eligibility_pairs(self):
        domains = ("X", "Y", "Z")
        subsets = [combo for n in range(1, 4) for combo in itertools.combinations(domains, n)]
        for left, right in itertools.product(subsets, repeat=2):
            with self.subTest(left=left, right=right):
                initial = State((Stripe("A", ("S", "T") + left), Stripe("B", ("S", "T") + right)),
                    tuple(Slot(f"{name}{row}", domain, "LIVE", name, row, 1)
                          for name in ("A", "B") for row, domain in enumerate(("S", "T")))
                    + tuple(Slot(domain, domain) for domain in domains))
                # Independent finite feasibility oracle: enumerate assignments,
                # no transition function or continuation checker used here.
                feasible = any(a != b for a in left for b in right)
                result = plan(initial)
                self.assertNotEqual(result.status, SearchStatus.UNKNOWN)
                self.assertEqual(result.status == SearchStatus.FOUND, feasible)
                baseline = conventional_plan(initial)
                self.assertEqual(baseline is not None, feasible)
                if feasible:
                    check(initial, result.witness)
                    check(initial, baseline)

    def test_codec_all_two_row_combinations_and_odd_lengths(self):
        for data in (b"", b"x", b"hello world", bytes(range(255))):
            encoded = encode(data)
            for chosen in itertools.combinations(range(3), 2):
                content, fragments = recover({r: encoded[r] for r in chosen}, len(data))
                self.assertEqual(content, data)
                self.assertEqual(fragments, encoded)


if __name__ == "__main__":
    unittest.main()
