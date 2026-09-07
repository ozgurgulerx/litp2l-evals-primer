"""Window membership survives process loss before any agent admission."""

import json
import multiprocessing
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.exposure_control import ExposureState
from cx_eval_lab.exposure_study import build_window_plan, execute_window
from cx_eval_lab.window_registration import WindowRegistry

POLICY = {'campaign_id': 'windows', 'max_actions': 2, 'currency_caps': {'EUR': 9000}}
MANIFEST = 'a' * 64


def killed_window(campaign_path, registry_path, ready, release):
    campaign = DurableCampaign.open(campaign_path, **POLICY)
    registry = WindowRegistry.open(registry_path, campaign)
    def before_agent(*args, **kwargs):
        ready.set()
        release.wait(30)
        raise AssertionError('must be killed')
    with patch('cx_eval_lab.exposure_study.run_case', side_effect=before_agent):
        execute_window(ExposureState('candidate', 'baseline'), 1, 'healthy',
                       durable_campaign=campaign, execution_namespace='study',
                       window_registry=registry, manifest_digest=MANIFEST)


def concurrent_registration(campaign_path, registry_path, manifest, barrier, queue):
    campaign = DurableCampaign.open(campaign_path, **POLICY)
    registry = WindowRegistry.open(registry_path, campaign)
    plan = build_window_plan(ExposureState('candidate', 'baseline'), 1, 'healthy',
                             execution_namespace='study', manifest_digest=manifest,
                             effect_backend='durable')
    barrier.wait(10)
    try:
        queue.put(('saved', registry.register(plan)['manifest_digest']))
    except ValueError:
        queue.put(('conflict', manifest))


class WindowRegistrationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name)
        self.campaign = DurableCampaign.initialize(self.path / 'campaign.sqlite', **POLICY)
        self.registry = WindowRegistry.initialize(self.path / 'windows.sqlite', self.campaign)
        self.state = ExposureState('candidate', 'baseline')

    def plan(self, **kwargs):
        return build_window_plan(self.state, 1, 'healthy', execution_namespace='study',
                                 manifest_digest=MANIFEST, effect_backend='durable', **kwargs)

    def execute(self, **kwargs):
        return execute_window(self.state, 1, 'healthy', durable_campaign=self.campaign,
                              execution_namespace='study', window_registry=self.registry,
                              manifest_digest=MANIFEST, **kwargs)

    def test_reopen_identical_registration_and_independent_inspection(self):
        plan = self.plan()
        self.assertEqual(self.registry.register(plan), plan)
        reopened = WindowRegistry.open(self.registry.path, self.campaign)
        self.assertEqual(reopened.register(plan), plan)
        inspected = reopened.inspect('study', 1)
        self.assertEqual(inspected, plan)
        inspected['members'][0]['case']['request']['utterance'] = 'changed'
        self.assertEqual(reopened.inspect('study', 1), plan)
        self.assertIsNone(reopened.inspect('study', 2))

    def test_changed_registration_is_conflict_before_any_execution(self):
        self.registry.register(self.plan())
        with patch('cx_eval_lab.exposure_study.run_case') as run:
            for state, fault, manifest in ((replace(self.state, revision=1), 'healthy', MANIFEST),
                                            (self.state, 'wrong_order', MANIFEST),
                                            (self.state, 'healthy', 'b' * 64)):
                with self.subTest(state=state, fault=fault), self.assertRaises(ValueError):
                    execute_window(state, 1, fault, durable_campaign=self.campaign,
                                   execution_namespace='study', window_registry=self.registry,
                                   manifest_digest=manifest)
            run.assert_not_called()

    def test_execution_consumes_registered_cases_routes_and_scopes(self):
        self.state = replace(self.state, stage='canary', percent=5)
        plan = self.plan()
        self.registry.register(plan)
        _, rows, count = self.execute()
        self.assertEqual(count, sum(row['served'] == 'candidate' for row in plan['members']))
        for member, row in zip(plan['members'], rows, strict=True):
            self.assertEqual(row['customer_id'], member['customer_id'])
            self.assertEqual(row['served'], member['served'])
            self.assertEqual(row['baseline']['case'], member['case'])
            self.assertEqual(row['candidate'] is not None, member['candidate_execute'])
            self.assertEqual(row['effect_scopes'], member['effect_scopes'])

    def test_kill_after_registration_preserves_all_members_and_zero_effects(self):
        ctx = multiprocessing.get_context('spawn')
        ready, release = ctx.Event(), ctx.Event()
        child = ctx.Process(target=killed_window, args=(self.campaign.path, self.registry.path, ready, release))
        child.start()
        try:
            self.assertTrue(ready.wait(15))
            child.kill()
            child.join(10)
            self.assertFalse(child.is_alive())
        finally:
            if child.is_alive():
                child.kill()
                child.join(10)
        reopened = WindowRegistry.open(self.registry.path, self.campaign)
        self.assertEqual(reopened.inspect('study', 1), self.plan())
        self.assertEqual(len(reopened.inspect('study', 1)['members']), 40)
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 0)

    def test_concurrent_equal_and_conflicting_registration(self):
        for second in (MANIFEST, 'b' * 64):
            with self.subTest(second=second):
                path = self.path / f'{second[0]}.sqlite'
                WindowRegistry.initialize(path, self.campaign)
                ctx = multiprocessing.get_context('spawn')
                barrier, queue = ctx.Barrier(2), ctx.Queue()
                children = [ctx.Process(target=concurrent_registration,
                    args=(self.campaign.path, path, digest, barrier, queue)) for digest in (MANIFEST, second)]
                for child in children:
                    child.start()
                try:
                    outcomes = [queue.get(timeout=20) for _ in children]
                    self.assertEqual(sum(row[0] == 'saved' for row in outcomes), 2 if second == MANIFEST else 1)
                finally:
                    for child in children:
                        child.join(10)
                        if child.is_alive():
                            child.kill()
                            child.join(10)
                self.assertTrue(all(child.exitcode == 0 for child in children))

    def test_missing_invalid_schema_or_changed_binding_blocks_all_work(self):
        with sqlite3.connect(self.registry.path) as db:
            db.execute('PRAGMA user_version=99')
        with patch('cx_eval_lab.exposure_study.run_case') as run, self.assertRaises(ValueError):
            self.execute()
        run.assert_not_called()

    def test_tampered_hash_and_type_changes_are_not_accepted(self):
        self.registry.register(self.plan())
        with sqlite3.connect(self.registry.path) as db:
            db.execute("UPDATE windows SET plan_hash='changed'")
        with self.assertRaises(ValueError):
            self.registry.inspect('study', 1)
        for field, value in (('number', True), ('immature', 0), ('manifest_digest', 'bad')):
            altered = {**self.plan(), field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.registry.register(altered)

    def test_registry_pairing_and_input_validation_precedes_agents(self):
        with patch('cx_eval_lab.exposure_study.run_case') as run:
            for kwargs in ({'window_registry': self.registry}, {'manifest_digest': MANIFEST},
                           {'window_registry': self.registry, 'manifest_digest': MANIFEST}):
                with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                    execute_window(self.state, 1, 'healthy', **kwargs)
            for number in (True, 0, -1, 1.5):
                with self.subTest(number=number), self.assertRaises(ValueError):
                    build_window_plan(self.state, number, 'healthy')
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
