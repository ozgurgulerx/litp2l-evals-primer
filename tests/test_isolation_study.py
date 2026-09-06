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
            for identity in ('../private', '', 'source:run-A', None):
                with self.subTest(identity=identity), self.assertRaises(ValueError):
                    store.issue_context(identity)
            with self.assertRaises(PermissionError):
                worker.overwrite_policy(a)
            self.assertEqual(POLICY, worker.read_policy(b))

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


if __name__ == '__main__':
    unittest.main()
