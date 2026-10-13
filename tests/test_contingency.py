from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from prism_c.checker import replay
from prism_c.contingency import (ContingencyPolicy, conventional_cached_branches, plan_contingency,
                                select_branch, select_cached_branch)
from prism_c.contingency_campaign import contingency_state, run_contingency_campaign
from prism_c.contingency_check import check_policy
from prism_c.contingency_demo import contingency_demo
from prism_c.contingency_reference import contingency_oracle
from prism_c.min_work import conventional_min_work_plan
from prism_c.model import Rejected, SearchStatus


class ContingencyTests(unittest.TestCase):
    def fixture(self):
        state = contingency_state()
        domains = tuple(sorted({s.domain for s in state.slots}))
        result = plan_contingency(state, domains)
        self.assertEqual(result.status, SearchStatus.FOUND)
        return state, result.policy

    def test_complete_precompletion_coverage_and_serialization(self):
        state, policy = self.fixture()
        encoded = json.loads(json.dumps(policy.to_dict()))
        restored = ContingencyPolicy.from_dict(encoded)
        self.assertEqual(restored, policy)
        result = check_policy(state, restored)
        self.assertEqual(result["branch_count"], 21)
        self.assertEqual(len(policy.nominal.actions), 3)
        self.assertTrue(all(b.cursor < 3 for b in policy.branches))
        with patch("prism_c.contingency.conventional_min_work_plan", side_effect=AssertionError("checker invoked planner")):
            self.assertEqual(check_policy(state, policy)["branch_count"], 21)

    def test_forged_coverage_snapshot_routes_and_identity_reject(self):
        state, policy = self.fixture()
        first, other = policy.branches[0], policy.branches[-1]
        broken = (replace(policy, branches=policy.branches[:-1]),
                  replace(policy, branches=policy.branches + (first,)),
                  replace(policy, branches=(replace(first, witness=other.witness),) + policy.branches[1:]),
                  replace(policy, branches=(replace(first, cursor=True),) + policy.branches[1:]),
                  replace(policy, version=True),
                  replace(policy, fault_domains=policy.fault_domains[:-1]),
                  replace(policy, initial="wrong"))
        for index, malformed in enumerate(broken):
            with self.subTest(tamper=index), self.assertRaises(Rejected):
                check_policy(state, malformed)
        wire = policy.to_dict()
        wire["digest"] = "wrong"
        with self.assertRaises(Rejected):
            ContingencyPolicy.from_dict(wire)

    def test_unsafe_margin_and_colocated_spares_cannot_earn_guarantee(self):
        for state in (contingency_state(live=4), contingency_state(x_slots=2, y_slots=0)):
            ordinary = conventional_min_work_plan(state)
            self.assertEqual(ordinary.status, SearchStatus.FOUND)
            self.assertEqual(plan_contingency(state, ("D0",)).status, SearchStatus.INFEASIBLE)
            self.assertEqual(contingency_oracle(state, ("D0",)).status, SearchStatus.INFEASIBLE)
            status, table = conventional_cached_branches(state, ordinary.witness, ("D0",))
            self.assertEqual(status, SearchStatus.INFEASIBLE)
            self.assertIsNone(table)

    def test_all_budget_limits_preserve_unknown_without_a_policy(self):
        state, policy = self.fixture()
        for options in ({"max_states": 0}, {"max_states": 1}, {"branch_budget": 1}, {"max_branch_checks": 1}):
            result = plan_contingency(state, policy.fault_domains, **options)
            self.assertEqual(result.status, SearchStatus.UNKNOWN)
            self.assertIsNone(result.policy)
        self.assertEqual(contingency_oracle(state, policy.fault_domains, max_states=1).status, SearchStatus.UNKNOWN)
        self.assertEqual(contingency_oracle(state, policy.fault_domains, assignment_budget=0).status, SearchStatus.UNKNOWN)

    def test_cached_selectors_match_without_online_replanning_and_reject_second_fault(self):
        state, policy = self.fixture()
        status, table = conventional_cached_branches(state, policy.nominal, policy.fault_domains)
        self.assertEqual(status, SearchStatus.FOUND)
        current = state
        with patch("prism_c.contingency.conventional_min_work_plan", side_effect=AssertionError("online replanning")):
            for cursor, action in enumerate(policy.nominal.actions):
                for domain in policy.fault_domains:
                    failed = replace(current, offline=(domain,))
                    self.assertEqual(select_branch(policy, cursor, domain, failed),
                                     select_cached_branch(table, cursor, domain, failed))
                current = replay(current, (action,), False)
        for selector in (lambda s, c, d: select_branch(policy, c, d, s),
                         lambda s, c, d: select_cached_branch(table, c, d, s)):
            with self.assertRaises(Rejected):
                selector(replace(state, offline=("D0", "D1")), 0, "D0")
            with self.assertRaises(Rejected):
                selector(replace(state, offline=("D0",)), 3, "D0")
            with self.assertRaises(Rejected):
                selector(replace(state, offline=("D0",)), 0, "unknown")
            changed = replace(state, slots=tuple(replace(s, incarnation=s.incarnation + 1)
                              if s.key == "Y:0" else s for s in state.slots), offline=("D0",))
            with self.assertRaises(Rejected):
                selector(changed, 0, "D0")

    def test_contract_cannot_be_empty_unknown_offline_or_vacuously_completed(self):
        state, policy = self.fixture()
        for planner in (plan_contingency, contingency_oracle):
            for domains in ((), ("unknown",), ("D0", "D0")):
                with self.assertRaises(Rejected):
                    planner(state, domains)
            complete = replay(state, policy.nominal.actions)
            with self.assertRaises(Rejected):
                planner(complete, policy.fault_domains)
            with self.assertRaises(Rejected):
                planner(replace(state, offline=("D0",)), ("D0",))

    def test_registered_finite_matrix_matches_independent_game(self):
        report = run_contingency_campaign()
        self.assertEqual(report["configurations"], 72)
        self.assertEqual((report["found"], report["infeasible"]), (16, 56))
        self.assertEqual(report["branch_comparisons"], 224)
        self.assertEqual(report["disagreements"], 0)
        self.assertFalse(report["selective_advantage_found"])

    def test_real_existing_authority_enforces_spare_and_checked_fallback(self):
        for workers in (False, True):
            for domain in ("D0", "X"):
                for selector in ("policy", "conventional"):
                    with self.subTest(workers=workers, domain=domain, selector=selector), tempfile.TemporaryDirectory() as tmp:
                        mode = "selective" if selector == "policy" else "conventional_cached"
                        result = contingency_demo(Path(tmp) / "store", workers, mode, domain, 2, selector)
                        self.assertTrue(all(result["readback_matches"].values()))
                        self.assertEqual(result["branch_coverage"], 21)
                        self.assertEqual(result["ledger_final"][domain]["bytes"]["RETIRED"], 1024)
                        self.assertTrue(result["spare_stealing_rejected"])
                        self.assertEqual(result["online_replanning_calls"], 0)
                        self.assertFalse(result["durable_policy_admission_implemented"])
