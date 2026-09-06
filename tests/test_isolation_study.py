"""Observed synthetic cache leakage, scoped utility, and actual thread barriers."""

import copy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cx_eval_lab.evidence import canonical_hash


class IsolationStudyTests(unittest.TestCase):
    def test_six_comparisons_expose_bug_without_destroying_useful_sharing(self):
        from cx_eval_lab.isolation_study import replay_study, run_study
        report = run_study()
        self.assertTrue(report['conformance_passed'])
        self.assertFalse(report['deployment_authorized'])
        self.assertEqual(6, len(report['comparisons']))
        self.assertEqual(6, len(replay_study(report)))
        for comparison in report['comparisons']:
            grade = comparison['grade']
            self.assertEqual(1 if comparison['strategy'] == 'query-only' else 0, grade['foreign_marker_responses'])
            self.assertTrue(grade['same_run_cache_hit'])
            self.assertTrue(grade['shared_policy_readable'])
            self.assertEqual(2, grade['shared_policy_overwrites_denied'])
            self.assertTrue(grade['shared_policy_unchanged'])

    def test_concurrent_context_really_uses_two_threads_at_barriers(self):
        from cx_eval_lab.isolation_study import run_comparison
        comparison = run_comparison('scoped', 'concurrent-threads')
        ready = [call for call in comparison['calls'] if call['operation'] == 'worker_ready']
        self.assertEqual(2, len(ready))
        self.assertEqual(2, len({call['thread_id'] for call in ready}))
        self.assertEqual({'run-A', 'run-B'}, {call['run_id'] for call in ready})
        responses = {response['step']: response for response in comparison['responses']}
        self.assertLess(responses['A-first']['read_sequence'], responses['B-first']['read_sequence'])
        self.assertLess(responses['B-first']['read_sequence'], responses['A-repeat']['read_sequence'])

    def test_context_spoofs_invalid_ids_and_policy_overwrite_fail(self):
        from cx_eval_lab.isolation_study import CacheStore, Worker, POLICY
        with tempfile.TemporaryDirectory() as root:
            store = CacheStore(Path(root) / 'cache.sqlite', 'scoped')
            a, b = store.issue_context('run-A'), store.issue_context('run-B')
            worker = Worker(store, 'worker-1')
            worker.resolve(a, 'same query with run-B in the text')
            result = worker.resolve(b, 'same query with run-B in the text')
            self.assertEqual({'private_marker': 'run-B'}, result['value'])
            with self.assertRaises(PermissionError):
                worker.resolve(replace(a, run_id='run-B'), 'same query')
            other = CacheStore(Path(root) / 'other.sqlite', 'scoped')
            with self.assertRaises(PermissionError):
                worker.resolve(other.issue_context('run-A'), 'same query')
            for identity in ('../private', '', 'source:run-A', None):
                with self.subTest(identity=identity), self.assertRaises(ValueError):
                    store.issue_context(identity)
            with self.assertRaises(PermissionError):
                worker.overwrite_policy(a)
            self.assertEqual(POLICY, worker.read_policy(b))
            worker.resolve(a, 'policy-v1')
            self.assertEqual(POLICY, worker.read_policy(b))
            self.assertEqual({'private', 'shared-policy'}, {row['storage_key'][0] for row in store.snapshot()})

    def test_regrade_rejects_rehashed_invented_reads_and_responses(self):
        from cx_eval_lab.isolation_study import replay_study, run_study
        original = run_study()
        for kind in ('read', 'response', 'registration'):
            report = copy.deepcopy(original)
            comparison = report['comparisons'][0]
            if kind == 'read':
                call = next(row for row in comparison['calls']
                            if row['operation'] == 'private_read' and row['value'] is not None)
                call['value'] = {'private_marker': 'invented'}
            elif kind == 'response':
                comparison['responses'][1]['value'] = {'private_marker': 'invented'}
            else:
                report['registration']['sharing_contract']['private_cache'] = 'share all answers'
            comparison['receipt_hash'] = canonical_hash({key: value for key, value in comparison.items()
                                                         if key != 'receipt_hash'})
            report['report_hash'] = canonical_hash({key: value for key, value in report.items()
                                                    if key != 'report_hash'})
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                replay_study(report)

    def test_reject_all_cannot_pass_by_erasing_useful_reads(self):
        from cx_eval_lab.isolation_study import replay_study, run_study
        report = run_study()
        comparison = report['comparisons'][3]
        comparison['calls'], comparison['responses'] = [], []
        comparison['final_store'] = copy.deepcopy(comparison['initial_store'])
        comparison['receipt_hash'] = canonical_hash({key: value for key, value in comparison.items()
                                                     if key != 'receipt_hash'})
        report['report_hash'] = canonical_hash({key: value for key, value in report.items() if key != 'report_hash'})
        with self.assertRaises(ValueError):
            replay_study(report)

    def test_registered_phase_identity_cannot_follow_a_misbound_worker(self):
        from cx_eval_lab.isolation_study import regrade, run_comparison
        original = run_comparison('query-only', 'fresh-workers')
        wrong_run = copy.deepcopy(original)
        b = wrong_run['responses'][1]
        b['run_id'] = 'run-A'
        for call in wrong_run['calls']:
            if call['run_id'] == 'run-B':
                call['run_id'] = 'run-A'
        with self.assertRaises(ValueError):
            regrade(wrong_run)
        wrong_worker = copy.deepcopy(original)
        for call in wrong_worker['calls']:
            call['worker_id'] = 'unregistered-worker'
        for response in wrong_worker['responses']:
            response['worker_id'] = 'unregistered-worker'
        with self.assertRaises(ValueError):
            regrade(wrong_worker)

    def test_cli_is_exclusive(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'isolation.json'
            command = [sys.executable, '-m', 'cx_eval_lab.isolation_study', '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            saved = output.read_bytes()
            self.assertTrue(json.loads(saved)['conformance_passed'])
            self.assertNotEqual(0, subprocess.run(command, capture_output=True, check=False).returncode)
            self.assertEqual(saved, output.read_bytes())

    def test_returned_registration_cannot_mutate_future_policy(self):
        from cx_eval_lab.isolation_study import POLICY, registration, run_study
        expected = dict(POLICY)
        report = run_study()
        try:
            report['registration']['shared_policy']['policy'] = 'changed-by-report-reader'
            self.assertEqual(expected, POLICY)
            self.assertEqual(expected, registration()['shared_policy'])
            fresh = run_study()
            self.assertTrue(fresh['conformance_passed'])
            self.assertEqual(expected, fresh['comparisons'][0]['initial_store'][0]['value'])
        finally:
            # Keep the RED reproducer isolated even when the buggy alias exists.
            POLICY.clear()
            POLICY.update(expected)

    def test_rehashed_concurrent_calls_must_join_the_ready_thread(self):
        from cx_eval_lab.isolation_study import replay_study, run_study
        report = run_study()
        comparison = report['comparisons'][5]
        a_thread = next(call['thread_id'] for call in comparison['calls']
                        if call['operation'] == 'worker_ready' and call['run_id'] == 'run-A')
        for call in comparison['calls']:
            if call['operation'] != 'worker_ready':
                call['thread_id'] = a_thread
        self._rehash(report, comparison)
        with self.assertRaisesRegex(ValueError, 'phase/context/thread'):
            replay_study(report)

    def test_rehashed_scoped_write_cannot_move_after_b_read(self):
        from cx_eval_lab.isolation_study import replay_study, run_study
        report = run_study()
        comparison = report['comparisons'][3]
        calls = comparison['calls']
        a_write = next(call for call in calls
                       if call['operation'] == 'private_write' and call['run_id'] == 'run-A')
        calls.remove(a_write)
        b_write_index = next(index for index, call in enumerate(calls)
                             if call['operation'] == 'private_write' and call['run_id'] == 'run-B')
        calls.insert(b_write_index + 1, a_write)
        renumber = {call['sequence']: index for index, call in enumerate(calls, 1)}
        for call in calls:
            call['sequence'] = renumber[call['sequence']]
        for response in comparison['responses']:
            for field in ('read_sequence', 'write_sequence'):
                if response[field] is not None:
                    response[field] = renumber[response[field]]
        # Scoped reads, final state, response links, grades, and both hashes remain
        # internally consistent; only the registered cross-run schedule is false.
        self._rehash(report, comparison)
        with self.assertRaisesRegex(ValueError, 'phase/context/thread'):
            replay_study(report)

    @staticmethod
    def _rehash(report, comparison):
        comparison['receipt_hash'] = canonical_hash({key: value for key, value in comparison.items()
                                                     if key != 'receipt_hash'})
        report['report_hash'] = canonical_hash({key: value for key, value in report.items()
                                                if key != 'report_hash'})


if __name__ == '__main__':
    unittest.main()
