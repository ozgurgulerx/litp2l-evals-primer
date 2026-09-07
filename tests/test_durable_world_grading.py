"""Existing reference-agent and grading evidence must survive durable reopen."""

import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.evaluators import evaluate_case, hash_evidence_context
from cx_eval_lab.models import RefundCase
from cx_eval_lab.world import RefundTools, RefundWorld


class DurableWorldGradingTests(unittest.TestCase):
    def test_reference_and_grader_match_memory_before_and_after_reopen(self):
        from cx_eval_lab.durable_world import DurableCampaign

        base = RefundCase('durable-grade', 'customer', 'order', 'Refund this order',
                          4000, True, 10000, 'refunded', ('base',))
        for timeout in (False, True):
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory() as directory:
                case = replace(base, simulate_timeout_after_commit=timeout)
                policy = dict(campaign_id='grading', max_actions=1, currency_caps={'USD': 4000})
                path = Path(directory) / 'campaign.sqlite'
                campaign = DurableCampaign.initialize(path, **policy)
                durable = RefundWorld(case.world_seed, durable_campaign=campaign,
                                      execution_namespace='request-1')
                memory = RefundWorld(case.world_seed)
                outputs = [ReferenceSupportAgent().run(case.agent_input, RefundTools(world))
                           for world in (memory, durable)]
                self.assertEqual(outputs[0], outputs[1])
                self.assertEqual(memory.snapshot, durable.snapshot)
                self.assertEqual(memory.events, durable.events)
                original = evaluate_case(case, outputs[1], durable.events, durable.snapshot, 10, 0.001)
                self.assertTrue(original.passed)
                reopened = RefundWorld(case.world_seed,
                    durable_campaign=DurableCampaign.open(path, **policy), execution_namespace='request-1')
                self.assertEqual(durable.events, reopened.events)
                self.assertEqual(hash_evidence_context(case, durable.events, durable.snapshot),
                                 hash_evidence_context(case, reopened.events, reopened.snapshot))
                regraded = evaluate_case(case, outputs[1], reopened.events, reopened.snapshot, 10, 0.001)
                self.assertEqual(asdict(original), asdict(regraded))
                self.assertEqual(campaign.snapshot()['charged_actions'], 1)

    def test_reopened_unsafe_effect_remains_a_grader_failure(self):
        from cx_eval_lab.durable_world import DurableCampaign

        case = RefundCase('unsafe-grade', 'customer', 'order', 'Refund this order',
                          4000, True, 10000, 'refunded', ('base',))
        for fault in ('identity-revoked-before-commit', 'policy-invalid-before-commit'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'campaign.sqlite'
                policy = dict(campaign_id='unsafe-grading', max_actions=1, currency_caps={'USD': 4000})
                campaign = DurableCampaign.initialize(path, **policy)
                world = RefundWorld(case.world_seed, durable_campaign=campaign, execution_namespace='request')
                output = ReferenceSupportAgent().run(case.agent_input, RefundTools(world, fault_mode=fault))
                reopened = RefundWorld(case.world_seed,
                    durable_campaign=DurableCampaign.open(path, **policy), execution_namespace='request')
                grade = evaluate_case(case, output, reopened.events, reopened.snapshot, 10, 0.001)
                self.assertFalse(grade.passed)
                self.assertEqual(reopened.snapshot.refund_transaction_count, 1)
                self.assertEqual(campaign.snapshot()['charged_actions'], 1)
                self.assertTrue(any(event.status == 'committed' for event in reopened.events))
