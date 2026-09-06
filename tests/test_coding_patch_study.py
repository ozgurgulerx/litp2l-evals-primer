"""Actual fixed-source patch execution; never a model capability benchmark."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab import coding_patch_study as study


class CodingPatchStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = study.run_study()

    def test_controls_execute_separate_visible_and_acceptance_suites(self):
        self.assertTrue(self.report['conformance_passed'])
        self.assertFalse(self.report['deployment_authorized'])
        controls = {row['name']: row for row in self.report['controls']}
        self.assertEqual('accepted', controls['correct']['status'])
        self.assertEqual('integrity_blocked', controls['protected-test-edit']['status'])
        self.assertEqual([], controls['protected-test-edit']['suites'])
        for name in ('original-denominator', 'visible-overfit'):
            self.assertEqual('rejected', controls[name]['status'])
            self.assertEqual(2, controls[name]['suites'][0]['passed'])
            self.assertLess(controls[name]['suites'][1]['passed'], 8)
        for suite in controls['correct']['suites']:
            self.assertEqual(suite['registered'], suite['passed'])
            self.assertEqual(0, suite['returncode'])
            self.assertGreaterEqual(suite['duration_seconds'], 0)
        self.assertTrue(any(row['input_unchanged'] is False
                            for suite in controls['input-mutating']['suites'] for row in suite['results']))
        for row in self.report['controls']:
            self.assertIn('candidate.py', row['files'])
            self.assertIn('diff', row)
            if row['name'] != 'protected-test-edit':
                self.assertEqual(row['protected_before'], row['protected_after'])

    def test_replay_rejects_tampering_before_any_execution(self):
        self.assertTrue(study.verify_study(self.report))
        for field in ('source_inventory', 'controls'):
            altered = copy.deepcopy(self.report)
            altered[field] = {} if field == 'source_inventory' else []
            with self.subTest(field=field), patch.object(study.subprocess, 'run') as runner:
                with self.assertRaises(ValueError):
                    study.verify_study(altered)
                runner.assert_not_called()

    def test_rehashed_invented_results_still_fail_replay(self):
        altered = copy.deepcopy(self.report)
        altered['controls'][0]['status'] = 'accepted'
        altered['report_hash'] = study.digest({k: v for k, v in altered.items() if k != 'report_hash'})
        with self.assertRaisesRegex(ValueError, 'replay'):
            study.verify_study(altered)

    def test_rehashed_case_coverage_and_result_fabrications_fail_replay(self):
        for defect in ('missing-case', 'invented-pass', 'integer-boolean', 'extra-field'):
            altered = copy.deepcopy(self.report)
            suite = altered['controls'][0]['suites'][1]
            if defect == 'missing-case':
                suite['results'].pop()
                suite['registered'] -= 1
            elif defect == 'invented-pass':
                suite['results'][1] = {**suite['results'][1], 'output_passed': True, 'passed': True}
                suite['passed'] += 1
            elif defect == 'integer-boolean':
                suite['results'][0]['input_unchanged'] = 1
            else:
                altered['controls'][0]['duration_seconds'] = 0
            suite['stdout'] = json.dumps(suite['results'], sort_keys=True) + '\n'
            altered['report_hash'] = study.digest({k: v for k, v in altered.items() if k != 'report_hash'})
            with self.subTest(defect=defect), self.assertRaisesRegex(ValueError, 'replay'):
                study.verify_study(altered)

    def test_child_test_deletion_and_extra_files_block_after_execution(self):
        real_run = subprocess.run

        def poison(command, **kwargs):
            result = real_run(command, **kwargs)
            (Path(kwargs['cwd']) / 'acceptance.json').unlink()
            (Path(kwargs['cwd']) / 'unexpected.txt').write_text('unexpected')
            return result

        with patch.object(study.subprocess, 'run', side_effect=poison):
            report = study.run_study()
        self.assertFalse(report['conformance_passed'])
        self.assertEqual('integrity_blocked', report['controls'][2]['status'])
        self.assertIn('unexpected.txt', report['controls'][2]['suites'][0]['files_after'])
        self.assertEqual(1, len(report['controls'][2]['suites']))

    def test_rehashed_invalid_duration_rejected_without_execution(self):
        for value in (-1, 'fast', True):
            altered = copy.deepcopy(self.report)
            altered['controls'][0]['suites'][0]['duration_seconds'] = value
            altered['report_hash'] = study.digest({k: v for k, v in altered.items() if k != 'report_hash'})
            with self.subTest(value=value), patch.object(study.subprocess, 'run') as runner:
                with self.assertRaisesRegex(ValueError, 'duration'):
                    study.verify_study(altered)
                runner.assert_not_called()

    def test_numeric_rates_accept_integer_values_but_reject_booleans(self):
        expected = study.VISIBLE[1]['expected']
        self.assertTrue(study.output_matches({**expected, 'completion': 1, 'known_pass_rate': 1}, expected))
        for field in ('registered', 'known_pass_rate', 'completion'):
            self.assertFalse(study.output_matches({**expected, field: True}, expected))
        self.assertFalse(study.output_matches({**expected, 'completion': float('inf')}, expected))

    def test_timeout_and_missing_results_cannot_pass(self):
        for effect in (subprocess.TimeoutExpired('fixed child', 5, output=b'partial\xff'),
                       subprocess.CompletedProcess([], 0, '{}', '')):
            with self.subTest(effect=type(effect).__name__), \
                    patch.object(study.subprocess, 'run', side_effect=effect if isinstance(effect, Exception) else None,
                                 return_value=effect):
                report = study.run_study()
            self.assertFalse(report['conformance_passed'])
            self.assertTrue(all(row['status'] != 'accepted' for row in report['controls']))
            first = report['controls'][0]['suites'][0]
            if isinstance(effect, subprocess.TimeoutExpired):
                self.assertEqual('timeout', first['status'])
                self.assertIsNone(first['returncode'])
                self.assertEqual('partial\ufffd', first['stdout'])
            else:
                self.assertEqual('invalid_results', first['status'])

    def test_negative_control_transport_failure_is_not_expected_rejection(self):
        real_run = subprocess.run
        for defect in ('timeout', 'missing-test'):
            def fail_original(command, defect=defect, **kwargs):
                source = (Path(kwargs['cwd']) / 'candidate.py').read_text()
                if source == study.BUILTINS['original-denominator']:
                    if defect == 'timeout':
                        raise subprocess.TimeoutExpired(command, 2)
                    return subprocess.CompletedProcess(command, 0, '[]', '')
                return real_run(command, **kwargs)

            with self.subTest(defect=defect), patch.object(study.subprocess, 'run', side_effect=fail_original):
                report = study.run_study()
            self.assertEqual('accepted', report['controls'][2]['status'])
            self.assertFalse(report['conformance_passed'])

    def test_missing_protected_test_blocks_before_candidate_execution(self):
        original = study._prepare

        def remove_test(root, name):
            original(root, name)
            (root / 'acceptance.json').unlink()

        with patch.object(study, '_prepare', side_effect=remove_test), \
                patch.object(study.subprocess, 'run') as runner:
            report = study.run_study()
        runner.assert_not_called()
        self.assertFalse(report['conformance_passed'])

    def test_child_uses_isolated_interpreter_and_no_inherited_credentials(self):
        real_run = subprocess.run

        def inspect(command, **kwargs):
            self.assertEqual(['-I', '-S'], command[1:3])
            self.assertEqual({}, kwargs['env'])
            self.assertTrue(Path(kwargs['cwd'], 'harness.py').is_file())
            return real_run(command, **kwargs)

        with patch.object(study.subprocess, 'run', side_effect=inspect) as runner:
            self.assertTrue(study.run_study()['conformance_passed'])
        self.assertEqual(8, runner.call_count)

    def test_fresh_cli_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'nested' / 'study.json'
            command = [sys.executable, '-m', 'cx_eval_lab.coding_patch_study', '--output', str(target)]
            first = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
            self.assertEqual(0, first.returncode, first.stderr)
            report = json.loads(target.read_text())
            self.assertTrue(study.verify_study(report))
            before = target.read_bytes()
            second = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
            self.assertNotEqual(0, second.returncode)
            self.assertEqual(before, target.read_bytes())


if __name__ == '__main__':
    unittest.main()
