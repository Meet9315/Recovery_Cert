import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

from prism_c.checker import check
from prism_c.min_work import conventional_min_work_plan, min_work_oracle, work_score
from prism_c.min_work_campaign import run_min_work_campaign
from prism_c.min_work_demo import min_work_demo, min_work_fixture
from prism_c.model import Rejected, SearchStatus, Slot, State, Stripe
from prism_c.partial_recovery import conventional_partial_plan
from prism_c.profiles import DEFAULT_PROFILE, FOUR_PLUS_TWO


class MinimumWorkTests(unittest.TestCase):
    def counterexample(self):
        return State((Stripe("A", ("S", "T", "X", "Y")), Stripe("B", ("S", "T", "X", "W"))),
                     tuple(Slot(f"{n}{r}", d, "LIVE", n, r, 1) for n in ("A", "B")
                           for r, d in enumerate(("S", "T"))) +
                     (Slot("X", "X", "STAGED", "B", 2, 1),
                      Slot("Y", "Y", "RETIRED", incarnation=1), Slot("W", "W")))

    def test_global_retention_and_input_order_agree_with_graph_oracle(self):
        state = self.counterexample()
        self.assertEqual(work_score(conventional_partial_plan(state).witness), (2, 8))
        reference = min_work_oracle(state)
        self.assertEqual(reference.status, SearchStatus.FOUND)
        self.assertEqual(work_score(reference.witness), (1, 5))
        rng = random.Random(20261013)
        for index in range(12):
            slots, specs = list(state.slots), list(state.stripes)
            rng.shuffle(slots)
            rng.shuffle(specs)
            with self.subTest(order=index):
                varied = replace(state, slots=tuple(slots), stripes=tuple(specs))
                result = conventional_min_work_plan(varied)
                self.assertEqual(result.status, SearchStatus.FOUND)
                self.assertEqual(work_score(result.witness), (1, 5))
                self.assertTrue(check(varied, result.witness).target())

    def test_incumbent_is_not_misreported_as_optimal_on_budget_exhaustion(self):
        for budget in (0, 1, 3, 5):
            result = conventional_min_work_plan(self.counterexample(), budget)
            self.assertEqual(result.status, SearchStatus.UNKNOWN)
            self.assertIsNone(result.witness)
        self.assertEqual(min_work_oracle(self.counterexample(), 0).status, SearchStatus.UNKNOWN)
        impossible = replace(self.counterexample(), offline=("X", "Y"))
        for planner in (conventional_min_work_plan, min_work_oracle):
            self.assertEqual(planner(impossible).status, SearchStatus.INFEASIBLE)

    def test_finite_campaign_objective_matches_independent_oracle(self):
        report = run_min_work_campaign()
        self.assertEqual(report["configurations"], 136)
        self.assertEqual(report["disagreements"], 0)
        self.assertEqual(report["unknown"], 0)
        self.assertEqual(report["first_feasible_suboptimal_cases"], 2)

    def test_real_byte_revision_both_profiles_paths_and_validation_modes(self):
        for profile in (DEFAULT_PROFILE, FOUR_PLUS_TWO):
            for workers in (False, True):
                for mode in ("conventional_cached", "selective", "full", "shadow"):
                    with self.subTest(profile=profile, workers=workers, mode=mode), tempfile.TemporaryDirectory() as tmp:
                        result = min_work_demo(Path(tmp) / "store", profile, workers, mode)
                        expected = (1, 6) if profile == DEFAULT_PROFILE else (3, 10)
                        self.assertEqual(result["executed_score"], expected)
                        self.assertTrue(all(result["readback_matches"].values()))
                        self.assertNotIn("X:0", [a["slot"] for a in result["executed_actions"] if a["kind"] == "stage"])
                        self.assertEqual(result["ledger_final"]["Z"]["bytes"]["RETIRED"], 1024)
                        self.assertTrue(result["audit"]["target"])

    def test_retention_optimization_does_not_adopt_corrupt_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, fence, _, parent, targets = min_work_fixture(Path(tmp) / "store")
            result = conventional_min_work_plan(store.revision_snapshot("initial", targets, fence))
            with store._transaction() as db:
                row = db.execute("SELECT * FROM slots WHERE key='X:0'").fetchone()
                store._io(db, row, b"corrupted retained staging")
            with self.assertRaises(Rejected):
                store.revise("initial", result.witness, targets, fence, "corrupt", parent.digest())
            self.assertEqual(store.plan_info("initial")["status"], "ACTIVE")

    def test_cli_minimum_work_proposal_and_unknown_are_explicit(self):
        from prism_c.__main__ import main
        with tempfile.TemporaryDirectory() as tmp:
            store, fence, _, _, targets = min_work_fixture(Path(tmp) / "store")
            output = Path(tmp) / "proposal.json"
            base = ["prism_c", "replan", "--root", str(store.root), "--plan", "initial", "--fence", str(fence),
                    "--planner", "min-work", "--report", str(output), "--destinations", *targets]
            for budget, expected in ((1, 2), (20000, 0)):
                with patch.object(sys, "argv", [*base, "--max-states", str(budget)]), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(), expected)
                proposal = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(proposal["optimality_proven"], expected == 0)
                if expected:
                    self.assertIsNone(proposal["witness"])
                else:
                    self.assertEqual(proposal["objective"], [1, 6])

    def test_invalid_state_cannot_be_optimized(self):
        unsafe = replace(self.counterexample(), slots=self.counterexample().slots[1:])
        for planner in (conventional_min_work_plan, min_work_oracle):
            with self.assertRaises(Rejected):
                planner(unsafe)
