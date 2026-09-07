"""Existing multi-order/exposure paths retain durable served-candidate effects."""

import multiprocessing
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

from cx_eval_lab.action_budget import ActionBudget
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.exposure_control import ExposureState, transition
from cx_eval_lab.exposure_study import FaultInjectedCandidate, execute_window
from cx_eval_lab.order_resolution import (
    DescriptiveResolver,
    FirstRecordResolver,
    MultiOrderWorld,
    example_cases,
    run_case,
)

POLICY = {'campaign_id': 'exposure', 'max_actions': 2, 'currency_caps': {'USD': 8000, 'EUR': 9000}}


def compete_for_admission(path, barrier, queue):
    campaign = DurableCampaign.open(path, **POLICY)
    barrier.wait(timeout=10)
    try:
        run_case(example_cases()[0], FaultInjectedCandidate('unavailable'), durable_campaign=campaign,
                 execution_namespace='same-request')
        result = 'executed'
    except ValueError:
        result = 'rejected'
    queue.put(result)


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

    def test_same_window_cannot_fabricate_complete_grade_from_prior_effects(self):
        state = ExposureState('cx-simulation-v1', 'baseline-v1', stage='canary', percent=5)
        execute_window(state, 2, 'healthy', durable_campaign=self.campaign, execution_namespace='fixed')
        with self.assertRaisesRegex(ValueError, 'prior execution evidence'):
            execute_window(state, 2, 'healthy', durable_campaign=DurableCampaign.open(self.path, **POLICY),
                           execution_namespace='fixed')
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 2)

    def test_reused_case_evidence_is_rejected_before_agent(self):
        self.run_case('used')
        with patch.object(DescriptiveResolver, 'run') as run, self.assertRaisesRegex(ValueError, 'prior execution evidence'):
            self.run_case('used')
        run.assert_not_called()
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)

    def test_zero_tool_and_clarification_only_attempts_cannot_be_reexecuted(self):
        for namespace, agent, case in [('unavailable', FaultInjectedCandidate('unavailable'), self.case),
                                        ('clarification', DescriptiveResolver(), example_cases()[-1])]:
            first = self.run_case(namespace, agent, case)
            self.assertEqual(sum(order['state']['refund_transaction_count'] for order in first['orders']), 0)
            with self.subTest(namespace=namespace), patch.object(type(agent), 'run', wraps=agent.run) as execute:
                with self.assertRaisesRegex(ValueError, 'prior execution evidence'):
                    self.run_case(namespace, agent, case)
                execute.assert_not_called()

    def test_two_processes_cannot_admit_the_same_zero_tool_request(self):
        context = multiprocessing.get_context('spawn')
        barrier, queue = context.Barrier(3), context.Queue()
        children = [context.Process(target=compete_for_admission, args=(str(self.path), barrier, queue)) for _ in range(2)]
        try:
            for child in children:
                child.start()
            barrier.wait(timeout=10)
            results = [queue.get(timeout=10) for _ in children]
            for child in children:
                child.join(timeout=10)
                self.assertEqual(child.exitcode, 0)
            self.assertCountEqual(results, ['executed', 'rejected'])
            self.assertEqual(self.campaign.snapshot()['charged_actions'], 0)
        finally:
            for child in children:
                if child.is_alive():
                    child.kill()
                child.join(timeout=5)
            queue.close()
            queue.join_thread()

    def test_invalid_backend_combinations_stop_before_baseline_or_agent(self):
        variants: tuple[dict[str, Any], ...] = ({'durable_campaign': self.campaign},
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

    def test_operational_input_change_conflicts_with_zero_tool_admission(self):
        self.run_case('identity', FaultInjectedCandidate('unavailable'))
        changed = replace(self.case, request=replace(self.case.request, utterance='A changed request'))
        with patch.object(DescriptiveResolver, 'run') as execute, self.assertRaisesRegex(ValueError, 'operational input'):
            self.run_case('identity', case=changed)
        execute.assert_not_called()

    def test_previous_lowlevel_evidence_cannot_be_admitted_as_fresh_case(self):
        world = MultiOrderWorld(self.case, durable_campaign=self.campaign, execution_namespace='prior')
        world.tools().verify_identity('customer-1', 'order-a')
        with patch.object(DescriptiveResolver, 'run') as execute, self.assertRaisesRegex(ValueError, 'prior execution evidence'):
            self.run_case('prior')
        execute.assert_not_called()

    def test_schema_one_is_rejected_without_implicit_migration(self):
        with sqlite3.connect(self.path) as db:
            db.execute('PRAGMA user_version=1')
        with self.assertRaisesRegex(ValueError, 'schema mismatch'):
            DurableCampaign.open(self.path, **POLICY)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)

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
