import hashlib
import json
import multiprocessing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab.durable_completion import CompletionJournal
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.exposure_control import ExposureState
from cx_eval_lab.exposure_study import (
    FaultInjectedCandidate,
    build_window_plan,
    case_from_plan,
    execute_window,
)
from cx_eval_lab.order_resolution import run_case
from cx_eval_lab.window_registration import WindowRegistry


def killed_after_wrong_effect(campaign_path, journal_path, case, namespace, ready, release):
    campaign = DurableCampaign.open(campaign_path, campaign_id='test', max_actions=10,
                                   currency_caps={'EUR': 90000, 'USD': 90000})
    journal = CompletionJournal.open(journal_path, campaign)
    from cx_eval_lab.order_resolution import run_case
    def execute_then_wait(*args, **kwargs):
        run_case(*args, **kwargs)
        ready.set()
        release.wait(30)
        raise RuntimeError('must be killed')
    with patch('cx_eval_lab.durable_completion.run_case', side_effect=execute_then_wait):
        journal.execute(case, FaultInjectedCandidate('wrong_order'), namespace=namespace,
                        manifest_digest='a' * 64)


class WindowCompletionTests(unittest.TestCase):
    def test_batch_does_not_mix_completion_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = DurableCampaign.initialize(Path(directory) / 'effects', campaign_id='test',
                max_actions=2, currency_caps={'EUR': 9000})
            journal = CompletionJournal.initialize(Path(directory) / 'journal', campaign)
            with sqlite3.connect(journal.path) as db:
                db.execute('PRAGMA journal_mode=WAL')
            plan = build_window_plan(ExposureState('candidate', 'baseline'), 1, 'healthy')
            case = case_from_plan(plan['members'][0]['case'])
            agent = FaultInjectedCandidate('healthy')
            bindings = [{'namespace': name, 'case': case, 'agent': agent.name,
                         'reverse': False, 'manifest_digest': 'a' * 64} for name in ('one', 'two')]
            journal.execute(case, agent, namespace='one', manifest_digest='a' * 64)
            original = CompletionJournal._artifact
            written = []
            def interleaved(instance, row):
                result = original(instance, row)
                if not written:
                    written.append(True)
                    journal.execute(case, agent, namespace='two', manifest_digest='a' * 64)
                return result
            with patch.object(CompletionJournal, '_artifact', interleaved):
                self.assertEqual([row['status'] for row in journal.inspect_many(bindings)],
                                 ['completed', 'missing'])
            self.assertEqual([row['status'] for row in journal.inspect_many(bindings)],
                             ['completed', 'completed'])

    def test_killed_effect_missing_completion_and_never_recorded_remain_selected(self):
        from cx_eval_lab.window_completion import inspect_window
        with tempfile.TemporaryDirectory() as directory:
            campaign = DurableCampaign.initialize(Path(directory) / 'effects', campaign_id='test',
                max_actions=10, currency_caps={'EUR': 90000, 'USD': 90000})
            journal = CompletionJournal.initialize(Path(directory) / 'journal', campaign)
            registry = WindowRegistry.initialize(Path(directory) / 'windows', campaign)
            plan = registry.register(build_window_plan(
                ExposureState('candidate', 'baseline', stage='expanded', percent=25), 1, 'wrong_order',
                execution_namespace='study', manifest_digest='a' * 64, effect_backend='durable'))
            selected = [row for row in plan['members'] if row['served'] == 'candidate']
            journal.execute(case_from_plan(selected[0]['case']), FaultInjectedCandidate('wrong_order'),
                namespace=selected[0]['candidate_namespace'], manifest_digest='a' * 64)
            context = multiprocessing.get_context('spawn')
            ready, release = context.Event(), context.Event()
            child = context.Process(target=killed_after_wrong_effect, args=(campaign.path, journal.path,
                case_from_plan(selected[1]['case']), selected[1]['candidate_namespace'], ready, release))
            child.start()
            try:
                self.assertTrue(ready.wait(10))
                child.kill()
                child.join(10)
                self.assertFalse(child.is_alive())
            finally:
                if child.is_alive():
                    child.kill()
                    child.join(10)
            with patch('cx_eval_lab.durable_completion.run_case', side_effect=AssertionError('read only')):
                report = inspect_window(registry, journal, 'study', 1, manifest_digest='a' * 64)
            rows = [row for row in report['members'] if row['served'] == 'candidate']
            self.assertEqual(report['planned_served'], len(selected))
            self.assertEqual(rows[0]['status'], 'completed')
            self.assertEqual(rows[1]['status'], 'no_completion')
            self.assertIsNone(rows[1]['candidate_pass'])
            self.assertIs(rows[1]['observed_wrong_order_violation'], True)
            self.assertEqual(rows[2]['status'], 'no_completion_record')
            self.assertIsNone(rows[2]['observed_wrong_order_violation'])
            self.assertIsNone(rows[2]['candidate_pass'])
            self.assertEqual(campaign.snapshot()['charged_actions'], 2)
            with self.assertRaises(ValueError):
                inspect_window(registry, journal, 'study', 1, manifest_digest='b' * 64)
            with self.assertRaises(ValueError):
                journal.inspect_many([{'namespace': selected[1]['candidate_namespace'],
                    'case': case_from_plan(selected[1]['case']), 'agent': FaultInjectedCandidate.name,
                    'reverse': False, 'manifest_digest': 'b' * 64}])

    def test_bogus_completed_pass_refused(self):
        from cx_eval_lab.window_completion import inspect_window
        with tempfile.TemporaryDirectory() as directory:
            campaign = DurableCampaign.initialize(Path(directory) / 'effects', campaign_id='test',
                max_actions=2, currency_caps={'EUR': 9000})
            journal = CompletionJournal.initialize(Path(directory) / 'journal', campaign)
            registry = WindowRegistry.initialize(Path(directory) / 'windows', campaign)
            execute_window(ExposureState('candidate', 'baseline', stage='canary', percent=5), 1, 'healthy',
                durable_campaign=campaign, window_registry=registry, completion_journal=journal,
                manifest_digest='a' * 64, execution_namespace='study')
            with sqlite3.connect(journal.path) as db:
                namespace, value = db.execute('SELECT namespace, artifact FROM requests LIMIT 1').fetchone()
                artifact = {**json.loads(value), 'passed': 1}
                serialized = json.dumps(artifact, sort_keys=True, separators=(',', ':'))
                db.execute('UPDATE requests SET artifact=?, artifact_hash=? WHERE namespace=?',
                    (serialized, hashlib.sha256(serialized.encode()).hexdigest(), namespace))
            with self.assertRaisesRegex(ValueError, 'boolean'):
                inspect_window(registry, journal, 'study', 1, manifest_digest='a' * 64)

    def test_execution_and_read_only_join_preserve_planned_denominator(self):
        from cx_eval_lab.window_completion import inspect_window
        with tempfile.TemporaryDirectory() as directory:
            campaign = DurableCampaign.initialize(Path(directory) / 'effects', campaign_id='test',
                max_actions=2, currency_caps={'EUR': 9000})
            journal = CompletionJournal.initialize(Path(directory) / 'journal', campaign)
            registry = WindowRegistry.initialize(Path(directory) / 'windows', campaign)
            state = ExposureState('candidate', 'baseline', stage='canary', percent=5)
            execute_window(state, 1, 'healthy', durable_campaign=campaign, window_registry=registry,
                completion_journal=journal, manifest_digest='a' * 64, execution_namespace='study')
            with patch('cx_eval_lab.durable_completion.run_case', side_effect=AssertionError('read only')):
                report = inspect_window(registry, journal, 'study', 1, manifest_digest='a' * 64)
            selected = [row for row in report['members'] if row['served'] == 'candidate']
            self.assertEqual(len(report['members']), 40)
            self.assertEqual(report['planned_served'], len(selected))
            self.assertTrue(all(row['status'] == 'completed' for row in selected))
            self.assertTrue(all(row['status'] == 'out_of_scope' for row in report['members']
                                if row['served'] != 'candidate'))
            self.assertFalse(report['deployment_authorized'])
            with (patch('cx_eval_lab.durable_completion.run_case', side_effect=AssertionError('no repeat candidate')),
                  patch('cx_eval_lab.exposure_study.run_case', wraps=run_case) as baseline):
                execute_window(state, 1, 'healthy', durable_campaign=campaign, window_registry=registry,
                    completion_journal=journal, manifest_digest='a' * 64, execution_namespace='study')
                self.assertEqual(baseline.call_count, 40)

    def test_invalid_journal_stops_shadow_before_agent(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = DurableCampaign.initialize(Path(directory) / 'effects', campaign_id='test',
                max_actions=2, currency_caps={'EUR': 9000})
            journal = CompletionJournal.initialize(Path(directory) / 'journal', campaign)
            registry = WindowRegistry.initialize(Path(directory) / 'windows', campaign)
            with sqlite3.connect(journal.path) as db:
                db.execute('PRAGMA user_version=99')
            with patch('cx_eval_lab.exposure_study.run_case') as run:
                with self.assertRaisesRegex(ValueError, 'schema'):
                    execute_window(ExposureState('candidate', 'baseline'), 1, 'healthy',
                        durable_campaign=campaign, window_registry=registry, completion_journal=journal,
                        manifest_digest='a' * 64, execution_namespace='study')
                run.assert_not_called()

    def test_bound_batch_missing_completed_and_identity_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            campaign = DurableCampaign.initialize(Path(directory) / 'effects', campaign_id='test',
                max_actions=2, currency_caps={'EUR': 9000})
            journal = CompletionJournal.initialize(Path(directory) / 'journal', campaign)
            plan = build_window_plan(ExposureState('candidate', 'baseline'), 1, 'healthy')
            case = case_from_plan(plan['members'][0]['case'])
            agent = FaultInjectedCandidate('healthy')
            binding = {'namespace': 'one', 'case': case, 'agent': agent.name,
                       'reverse': False, 'manifest_digest': 'a' * 64}
            self.assertEqual(journal.inspect_many([binding])[0]['status'], 'missing')
            journal.execute(case, agent, namespace='one', manifest_digest='a' * 64)
            rows = journal.inspect_many([binding])
            self.assertEqual(rows[0]['status'], 'completed')
            rows[0]['artifact']['orders'].clear()
            self.assertTrue(journal.inspect_many([binding])[0]['artifact']['orders'])
            with self.assertRaises(ValueError):
                journal.inspect_many([{**binding, 'manifest_digest': 'b' * 64}])
