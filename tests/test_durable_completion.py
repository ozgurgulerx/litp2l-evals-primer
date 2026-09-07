"""Completion caching never invents recovery of an interrupted agent."""

import hashlib
import json
import multiprocessing
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

from cx_eval_lab.durable_completion import CompletionJournal
from cx_eval_lab.durable_world import DurableCampaign
from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases

POLICY = {'campaign_id': 'completion', 'max_actions': 2, 'currency_caps': {'USD': 8000, 'EUR': 9000}}
MANIFEST = 'a' * 64


def killed_execution(campaign_path, journal_path, committed, release):
    class BlockingAgent(DescriptiveResolver):
        def run(self, request, tools):
            output = super().run(request, tools)
            committed.set()
            release.wait(30)
            return output
    campaign = DurableCampaign.open(campaign_path, **POLICY)
    CompletionJournal.open(journal_path, campaign).execute(
        example_cases()[0], BlockingAgent(), namespace='request', manifest_digest=MANIFEST)


def competing_execution(campaign_path, journal_path, barrier, queue):
    campaign = DurableCampaign.open(campaign_path, **POLICY)
    journal = CompletionJournal.open(journal_path, campaign)
    barrier.wait(10)
    try:
        result = journal.execute(example_cases()[0], DescriptiveResolver(),
                                 namespace='request', manifest_digest=MANIFEST)
        queue.put(('completed', result))
    except ValueError:
        queue.put(('rejected', None))


class CompletionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'campaign.sqlite'
        self.campaign = DurableCampaign.initialize(self.path, **POLICY)
        self.journal_path = Path(directory.name) / 'completion.sqlite'
        self.journal = CompletionJournal.initialize(self.journal_path, self.campaign)
        self.case = example_cases()[0]

    def execute(self, **kwargs):
        return self.journal.execute(self.case, DescriptiveResolver(), namespace='request',
                                    manifest_digest=MANIFEST, **kwargs)

    def test_completed_reopens_identically_without_execution_and_returns_independent_copy(self):
        original = self.execute()
        reopened = CompletionJournal.open(self.journal_path, self.campaign)
        with patch('cx_eval_lab.durable_completion.run_case', side_effect=AssertionError('rerun')):
            cached = reopened.execute(self.case, DescriptiveResolver(), namespace='request', manifest_digest=MANIFEST)
        self.assertEqual(original, cached)
        cached['output']['message'] = 'mutated'
        self.assertEqual(self.execute(), original)
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)
        self.assertEqual(reopened.inspect('request')['status'], 'completed')

    def test_operational_grading_manifest_and_order_changes_refuse_reuse(self):
        self.execute()
        for case, digest, reverse in ((replace(self.case, required_clarifications=1), MANIFEST, False),
                                      (self.case, 'b' * 64, False), (self.case, MANIFEST, True)):
            with self.subTest(case=case, digest=digest, reverse=reverse), self.assertRaises(ValueError):
                self.journal.execute(case, DescriptiveResolver(), namespace='request',
                                     manifest_digest=digest, reverse=reverse)

    def test_kill_after_real_effect_retains_missing_completion_and_refuses_rerun(self):
        ctx = multiprocessing.get_context('spawn')
        committed, release = ctx.Event(), ctx.Event()
        process = ctx.Process(target=killed_execution, args=(self.path, self.journal_path, committed, release))
        process.start()
        try:
            self.assertTrue(committed.wait(15))
            self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)
            process.kill()
            process.join(10)
            self.assertFalse(process.is_alive())
        finally:
            if process.is_alive():
                process.kill()
                process.join(10)
        observation = self.journal.inspect('request')
        self.assertEqual(observation['status'], 'started')
        self.assertFalse(observation['response_present'])
        self.assertEqual(observation['worker_liveness'], 'unknown')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.execute()
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)

    def test_concurrent_calls_charge_once_and_completed_returns_identical(self):
        ctx = multiprocessing.get_context('spawn')
        barrier, queue = ctx.Barrier(2), ctx.Queue()
        processes = [ctx.Process(target=competing_execution,
                     args=(self.path, self.journal_path, barrier, queue)) for _ in range(2)]
        for process in processes:
            process.start()
        try:
            results = [queue.get(timeout=20) for _ in processes]
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode, 0)
            completed = [result for status, result in results if status == 'completed']
            self.assertGreaterEqual(len(completed), 1)
            self.assertTrue(all(result == completed[0] for result in completed))
            self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)
        finally:
            for process in processes:
                if process.is_alive():
                    process.kill()
                    process.join(10)

    def test_corruption_and_missing_storage_fail_closed(self):
        self.execute()
        with sqlite3.connect(self.journal_path) as db:
            db.execute("UPDATE requests SET artifact='{}' WHERE namespace='request'")
        with self.assertRaisesRegex(ValueError, 'hash'):
            self.execute()
        with self.assertRaises(ValueError):
            CompletionJournal.open(self.journal_path.with_name('missing'), self.campaign)
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)

    def test_validation_and_existing_file_refusal(self):
        with self.assertRaises(ValueError):
            CompletionJournal.initialize(self.journal_path, self.campaign)
        invalid: list[Any] = [('', MANIFEST, False), ('request', 'name-only', False),
                              ('request', MANIFEST, 1)]
        for namespace, digest, reverse in invalid:
            with self.subTest(namespace=namespace, digest=digest), self.assertRaises(ValueError):
                self.journal.execute(self.case, DescriptiveResolver(), namespace=namespace,
                                     manifest_digest=digest, reverse=reverse)
        self.assertEqual(self.journal.inspect('missing')['status'], 'not_registered')
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 0)

    def test_nonfinite_artifact_does_not_publish_completion(self):
        with (patch('cx_eval_lab.durable_completion.run_case', return_value={'elapsed_ms': float('nan')}),
              self.assertRaises(ValueError)):
            self.execute()
        self.assertEqual(self.journal.inspect('request')['status'], 'started')

    def test_failed_agent_is_completed_evidence_not_success(self):
        class FailedAgent(DescriptiveResolver):
            def run(self, request, tools):
                raise RuntimeError('unavailable')
        agent = FailedAgent()
        result = self.journal.execute(self.case, agent, namespace='request', manifest_digest=MANIFEST)
        self.assertFalse(result['task_completed'])
        self.assertIsNotNone(result['execution_error'])
        self.assertEqual(self.journal.inspect('request')['status'], 'completed')
        with patch('cx_eval_lab.durable_completion.run_case', side_effect=AssertionError('rerun')):
            self.assertEqual(result, self.journal.execute(self.case, agent, namespace='request',
                                                         manifest_digest=MANIFEST))

    def test_campaign_replacement_schema_and_foreign_journal_are_rejected(self):
        other = DurableCampaign.initialize(self.path.with_name('other.sqlite'), **POLICY)
        with self.assertRaisesRegex(ValueError, 'binding'):
            CompletionJournal.open(self.journal_path, other)
        self.path.rename(self.path.with_name('old.sqlite'))
        replacement = DurableCampaign.initialize(self.path, **POLICY)
        with self.assertRaisesRegex(ValueError, 'binding'):
            CompletionJournal.open(self.journal_path, replacement)
        with self.assertRaisesRegex(ValueError, 'binding'):
            self.execute()

    def test_unavailable_journal_never_calls_runner(self):
        self.journal_path.rename(self.journal_path.with_name('saved.sqlite'))
        with (patch('cx_eval_lab.durable_completion.run_case', side_effect=AssertionError('fallback')),
              self.assertRaises(ValueError)):
            self.execute()
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 0)

    def test_completion_write_failure_leaves_effect_and_incomplete(self):
        with sqlite3.connect(self.journal_path) as db:
            db.execute("CREATE TRIGGER fail_completion BEFORE UPDATE ON requests BEGIN "
                       "SELECT RAISE(ABORT, 'injected disk failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.execute()
        self.assertEqual(self.campaign.snapshot()['charged_actions'], 1)
        self.assertEqual(self.journal.inspect('request')['status'], 'started')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.execute()

    def test_invalid_journal_schema_is_not_migrated(self):
        with sqlite3.connect(self.journal_path) as db:
            db.execute('PRAGMA user_version=2')
        with self.assertRaisesRegex(ValueError, 'schema'):
            CompletionJournal.open(self.journal_path, self.campaign)

    def test_rehashed_artifact_cannot_claim_another_request(self):
        result = self.execute()
        result['agent'] = 'other-agent'
        serialized = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False)
        with sqlite3.connect(self.journal_path) as db:
            db.execute('UPDATE requests SET artifact=?, artifact_hash=?',
                       (serialized, hashlib.sha256(serialized.encode()).hexdigest()))
        with self.assertRaisesRegex(ValueError, 'binding'):
            self.execute()

    def test_cached_identity_preserves_json_types(self):
        result = self.execute()
        result['reverse'] = 0
        serialized = json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False)
        with sqlite3.connect(self.journal_path) as db:
            db.execute('UPDATE requests SET artifact=?, artifact_hash=?',
                       (serialized, hashlib.sha256(serialized.encode()).hexdigest()))
        with self.assertRaisesRegex(ValueError, 'binding'):
            self.execute()

    def test_invalid_initial_result_is_not_published(self):
        with (patch('cx_eval_lab.durable_completion.run_case', return_value={}),
              self.assertRaisesRegex(ValueError, 'binding')):
            self.execute()
        self.assertEqual(self.journal.inspect('request')['status'], 'started')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            self.execute()
