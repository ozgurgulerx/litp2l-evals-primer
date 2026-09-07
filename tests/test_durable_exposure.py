"""Existing multi-order/exposure paths retain durable served-candidate effects."""

import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab.action_budget import ActionBudget
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.exposure_control import ExposureState, transition
from cx_eval_lab.exposure_study import execute_window
from cx_eval_lab.order_resolution import DescriptiveResolver, FirstRecordResolver, MultiOrderWorld, example_cases, run_case


POLICY = {'campaign_id': 'exposure', 'max_actions': 2, 'currency_caps': {'USD': 8000, 'EUR': 9000}}


class DurableExposureTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'campaign.sqlite'
        self.campaign = DurableCampaign.initialize(self.path, **POLICY)
        self.case = example_cases()[0]

    def run_case(self, namespace, agent=None, case=None):
        return run_case(self.case if case is None else case, DescriptiveResolver() if agent is None else agent,
                        durable_campaign=self.campaign, execution_namespace=namespace)

    def test_healthy_wrong_order_and_denial_use_actual_ledger(self):
        healthy = self.run_case('healthy')
        wrong = self.run_case('wrong', FirstRecordResolver())
        denied = self.run_case('denied')
        self.assertTrue(healthy['task_completed'])
        self.assertEqual(wrong['wrong_order_commits'], 1)
        self.assertFalse(wrong['passed'])
        self.assertFalse(denied['task_completed'])
        self.assertEqual(denied['denied_attempts'], 1)
        self.assertEqual(denied['output']['claimed_outcome'], 'needs_review')
        self.assertEqual(healthy['durable_campaign']['before']['charged_actions'], 0)
        self.assertEqual(denied['durable_campaign']['after']['charged_actions'], 2)
        self.assertEqual(healthy['durable_campaign']['campaign_id'], 'exposure')
        self.assertTrue(all('execution_namespace' in order for order in healthy['orders']))
        self.assertNotIn('action_budget', healthy)

    def test_reopened_campaign_across_three_windows_preserves_scope_and_caps(self):
        state = ExposureState('cx-simulation-v1', 'baseline-v1')
        charges, completed, counts = [], [], []
        for number in (1, 2, 3):
            campaign = DurableCampaign.open(self.path, **POLICY)
            window, rows, count = execute_window(state, number, 'healthy', durable_campaign=campaign,
                                                  execution_namespace='fixed-campaign')
            charges.append(campaign.snapshot()['charged_actions'])
            counts.append(count)
            candidates = [row['candidate'] for row in rows if row['candidate'] is not None]
            completed.append(sum(row['task_completed'] for row in candidates))
            self.assertTrue(all(row['baseline']['passed'] for row in rows))
            self.assertTrue(all('durable_campaign' not in row['baseline'] for row in rows))
            for row in rows:
                expected_scope = ('served_candidate_durable_campaign' if row['served'] == 'candidate'
                                  else 'isolated_shadow' if row['candidate'] is not None else 'not_executed')
                self.assertEqual(row['effect_scopes']['candidate'], expected_scope)
                if number == 1:
                    self.assertNotIn('durable_campaign', row['candidate'])
            state = transition(state, window, now=window.end).state
        self.assertEqual(charges, [0, 2, 2])
        self.assertEqual(completed, [40, 2, 0])
        self.assertEqual(counts, [0, 4, 4])
        self.assertEqual(state.stage, 'restricted')

    def test_same_window_reexecution_replays_effects_without_controller_claim(self):
        state = ExposureState('cx-simulation-v1', 'baseline-v1', stage='canary', percent=5)
        first = execute_window(state, 2, 'healthy', durable_campaign=self.campaign, execution_namespace='fixed')[1]
        second = execute_window(state, 2, 'healthy', durable_campaign=DurableCampaign.open(self.path, **POLICY),
                                execution_namespace='fixed')[1]
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 2)
        for left, right in zip(first, second, strict=True):
            if left['served'] == 'candidate':
                self.assertEqual([row['execution_namespace'] for row in left['candidate']['orders']],
                                 [row['execution_namespace'] for row in right['candidate']['orders']])
        replays = [event for row in second if row['served'] == 'candidate' for order in row['candidate']['orders']
                   for event in order['events'] if event['status'] == 'idempotent_replay']
        self.assertEqual(len(replays), 2)

    def test_invalid_backend_combinations_stop_before_baseline_or_agent(self):
        variants = ({'durable_campaign': self.campaign},
                    {'durable_campaign': self.campaign, 'execution_namespace': ' '},
                    {'durable_campaign': self.campaign, 'execution_namespace': 'fixed',
                     'action_budget': ActionBudget(1, {'EUR': 4500})})
        for options in variants:
            with self.subTest(options=tuple(options)), patch('cx_eval_lab.exposure_study.run_case') as run:
                with self.assertRaises(ValueError):
                    execute_window(ExposureState('c', 'b'), 1, 'healthy', **options)
                run.assert_not_called()
            with patch.object(DescriptiveResolver, 'run') as run:
                with self.assertRaises(ValueError):
                    run_case(self.case, DescriptiveResolver(), **options)
                run.assert_not_called()
            with self.assertRaises(ValueError):
                MultiOrderWorld(self.case, **options)

    def test_missing_storage_fails_before_baseline_even_in_shadow(self):
        with patch.object(DurableCampaign, 'snapshot', side_effect=sqlite3.OperationalError('missing DB')):
            with patch('cx_eval_lab.exposure_study.run_case') as run, self.assertRaises(sqlite3.Error):
                execute_window(ExposureState('c', 'b'), 1, 'healthy', durable_campaign=self.campaign,
                               execution_namespace='fixed')
            run.assert_not_called()

    def test_storage_failure_during_action_never_falls_back_to_memory(self):
        with patch.object(DurableCampaign, '_save', side_effect=sqlite3.OperationalError('storage failure')):
            result = self.run_case('failed')
        self.assertFalse(result['task_completed'])
        self.assertEqual(result['execution_error'], 'OperationalError')
        self.assertEqual(sum(order['state']['refund_transaction_count'] for order in result['orders']), 0)
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 0)

    def test_namespace_seed_conflict_is_rejected_before_agent(self):
        self.run_case('same')
        changed = replace(self.case, orders=(replace(self.case.orders[0], amount_cents=1), *self.case.orders[1:]))
        with patch.object(DescriptiveResolver, 'run') as run, self.assertRaises(ValueError):
            self.run_case('same', case=changed)
        run.assert_not_called()

    def test_legacy_shapes_and_in_memory_budget_are_preserved(self):
        legacy = run_case(self.case, DescriptiveResolver())
        memory = run_case(self.case, DescriptiveResolver(), action_budget=ActionBudget(1, {'EUR': 4500}))
        self.assertTrue(legacy['passed'])
        self.assertTrue(memory['passed'])
        self.assertNotIn('durable_campaign', legacy)
        self.assertNotIn('durable_campaign', memory)
        self.assertTrue(all('execution_namespace' not in row for row in legacy['orders']))
        self.assertIn('action_budget', memory)

    def test_all_order_artifacts_share_one_read_snapshot_despite_interleaved_writer(self):
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA journal_mode=WAL')
        world = MultiOrderWorld(self.case, durable_campaign=self.campaign, execution_namespace='interleaved')
        first = world._worlds['order-a']
        second = world._worlds['order-b']
        second.verify_identity('customer-1', 'order-b')
        second.consult_refund_policy('order-b')
        original = DurableCampaign._load
        inserted = False
        def interleave(campaign, db, namespace, seed):
            nonlocal inserted
            result = original(campaign, db, namespace, seed)
            if namespace == first.execution_namespace and not inserted:
                inserted = True
                second.issue_refund('order-b', 4500, 'EUR', None, 'concurrent')
            return result
        with patch.object(DurableCampaign, '_load', interleave):
            artifacts = world.artifacts()
        self.assertTrue(inserted)
        self.assertEqual(sum(row['state']['refund_transaction_count'] for row in artifacts), 0)
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)
