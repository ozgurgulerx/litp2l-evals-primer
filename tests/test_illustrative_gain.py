"""Point gains must not impersonate statistical superiority."""

import unittest
from dataclasses import replace

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.gate import GatePolicy, apply_release_gate
from cx_eval_lab.runner import evaluate_agent


class IllustrativeGainTests(unittest.TestCase):
    def test_point_gain_rule_is_named_illustrative(self):
        report = evaluate_agent(ReferenceSupportAgent(), load_refund_cases(
            'evals/cx-support/datasets/regression/refund_v1.json'))
        policy = replace(GatePolicy.for_initial_refund_slice(), minimum_task_success_gain=.01)
        decision = apply_release_gate(report, policy, .8)
        self.assertIn('illustrative_point_gain:task_success', {r.name for r in decision.rules})
        self.assertNotIn('superiority:task_success', {r.name for r in decision.rules})


if __name__ == '__main__':
    unittest.main()
