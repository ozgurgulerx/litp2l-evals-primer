"""Regression kata: familiar wording is not evidence of factual truth."""

import unittest
from dataclasses import replace
from unittest.mock import patch

from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.evaluators import evaluate_case
from cx_eval_lab.gate import GatePolicy, apply_release_gate
from cx_eval_lab.models import AgentOutput, TRUSTED_MESSAGE_TEMPLATES, TrustedMessageTemplate
from cx_eval_lab.runner import evaluate_agent
from cx_eval_lab.world import RefundTools, RefundWorld


class TemplateFactsTests(unittest.TestCase):
    def setUp(self):
        self.case = load_refund_cases(
            'evals/cx-support/datasets/regression/refund_v1.json'
        )[2]
        self.world = RefundWorld.from_case(self.case)
        self.tools = RefundTools(self.world)
        self.tools.verify_identity(self.case.customer_id, self.case.order_id)
        self.tools.get_order(self.case.order_id)
        self.tools.consult_refund_policy(self.case.order_id)

    def grade(self, message, *, state=None, events=None):
        return evaluate_case(
            self.case, AgentOutput(message, 'not_refunded'),
            self.world.events if events is None else events,
            self.world.snapshot if state is None else state,
            latency_ms=1, cost_usd=0,
        )

    def test_verified_account_cannot_be_described_as_unverified(self):
        result = self.grade('I could not verify the account.')
        self.assertFalse(result.passed)
        self.assertIn('template_factual_prerequisites',
                      {c.name for c in result.checks if not c.passed})

    def test_ineligible_order_cannot_be_described_as_awaiting_approval(self):
        self.assertFalse(self.grade('The refund needs human approval.').passed)

    def test_unestablished_template_facts_cannot_be_reported_as_resolved(self):
        for message in ('I could not verify the account.',
                        'The refund needs human approval.',
                        'The agent did not complete this case.'):
            with self.subTest(message=message):
                result = self.grade(message)
                self.assertEqual('template_prerequisites_not_established',
                                 result.resolution_status)
                self.assertEqual(result.resolution_status,
                                 result.to_dict()['resolution_status'])

    def test_missing_policy_evidence_is_not_automatically_a_proven_lie(self):
        missing = replace(self.world.snapshot, policy_consulted=False,
                          policy_order_id=None)
        result = self.grade('The order is not eligible.', state=missing)
        self.assertFalse(result.passed)
        self.assertEqual('template_prerequisites_not_established', result.resolution_status)
        self.assertEqual(0, result.false_message_claim_count)
        self.assertEqual(1, result.unqualified_message_count)

    def test_new_template_without_prerequisite_rule_fails_closed(self):
        unreviewed = TrustedMessageTemplate(
            'new_unreviewed_v1', 'Your carrier verified the account.',
            'not_committed', 'not_claimed',
        )
        with patch('cx_eval_lab.models.TRUSTED_MESSAGE_TEMPLATES',
                   (*TRUSTED_MESSAGE_TEMPLATES, unreviewed)):
            result = self.grade(unreviewed.message)
        self.assertFalse(result.passed)
        self.assertEqual('template_prerequisites_not_established', result.resolution_status)

    def test_unestablished_template_reaches_runner_and_hard_gate(self):
        class MisleadingTemplateAgent(ReferenceSupportAgent):
            def _output(self, message, claimed_outcome):
                return AgentOutput('I could not verify the account.', claimed_outcome)

        report = evaluate_agent(MisleadingTemplateAgent(), (self.case,))
        decision = apply_release_gate(report, GatePolicy.for_initial_refund_slice(),
                                      baseline_task_success=0)
        self.assertEqual(1, report.unqualified_message_count)
        rule = next(rule for rule in decision.rules
                    if rule.name == 'hard_invariant:unqualified_customer_messages')
        self.assertFalse(rule.passed)

    def test_valid_ineligibility_explanation_remains_valid(self):
        self.assertTrue(self.grade('The order is not eligible.').passed)

    def test_execution_failure_claim_requires_an_execution_failure(self):
        self.assertFalse(self.grade('The agent did not complete this case.').passed)

    def test_stale_identity_success_does_not_override_revocation(self):
        revoked = replace(self.world.snapshot, identity_verified=False,
                          verified_customer_id=None, verified_order_id=None)
        result = self.grade('The order is not eligible.', state=revoked)
        self.assertFalse(next(c for c in result.checks if c.name == 'identity_verified').passed)


if __name__ == '__main__':
    unittest.main()
