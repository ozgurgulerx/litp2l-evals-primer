"""CI must exercise passing, held and blocked evidence without deploying AI."""

import copy
import errno
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]


class CIConformanceTests(unittest.TestCase):
    def test_cli_retains_three_actions_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'ci-evidence'
            command = [sys.executable, '-m', 'cx_eval_lab.ci_conformance',
                       '--output-dir', str(output), '--code-revision', 'test-revision']
            result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads((output / 'conformance.json').read_text())
            self.assertEqual(['lab_pass', 'hold', 'block'], [r['action'] for r in report['checks']])
            self.assertFalse(report['deployment_authorized'])
            self.assertEqual('test-revision', report['code_revision'])
            self.assertFalse((output / 'conformance-failure.json').exists())
            for row in report['checks']:
                self.assertTrue((output / row['artifact']).is_file())
                self.assertEqual(20, row['replayed_trials'])
            second = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
            self.assertNotEqual(0, second.returncode)
            self.assertEqual(report, json.loads((output / 'conformance.json').read_text()))
            self.assertFalse((output / 'conformance-failure.json').exists())

    def test_failed_controls_retain_diagnostics_without_later_execution(self):
        from cx_eval_lab.ci_conformance import run_conformance
        real_run = subprocess.run
        cases = (
            ('timeout', 'command', subprocess.TimeoutExpired, None),
            ('launch_error', 'command', OSError, None),
            ('unexpected_exit', 'exit', ValueError, None),
            ('invalid_packet', 'packet', FileNotFoundError, 'missing'),
            ('invalid_packet', 'packet', json.JSONDecodeError, 'malformed'),
            ('invalid_evidence', 'verification', KeyError, 'structure'),
            ('invalid_evidence', 'verification', TypeError, 'list'),
            ('invalid_evidence', 'verification', ValueError, 'receipt'),
            ('invalid_evidence', 'verification', ValueError, 'replay'),
        )
        for status, phase, exception, defect in cases:
            with self.subTest(status=status, defect=defect), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'evidence'

                def invoke(command, status=status, defect=defect, **kwargs):
                    target = Path(command[-1])
                    if target.name != 'policy-bypass.json':
                        return real_run(command, **kwargs)
                    if status == 'timeout':
                        raise subprocess.TimeoutExpired(command, 30, output=b'partial\xff', stderr=b'error\xfe')
                    if status == 'launch_error':
                        raise OSError(errno.ENOENT, 'launch unavailable', command[0])
                    if status == 'unexpected_exit':
                        return subprocess.CompletedProcess(command, 7, 'failed', 'error')
                    if defect == 'missing':
                        return subprocess.CompletedProcess(command, 2, '', '')
                    if defect in {'malformed', 'structure', 'list'}:
                        target.write_text({'malformed': '{', 'structure': '{}', 'list': '[]'}[defect])
                        return subprocess.CompletedProcess(command, 2, '', '')
                    result = real_run(command, **kwargs)
                    packet = json.loads(target.read_text())
                    if defect == 'receipt':
                        packet['receipt']['receipt_hash'] = 'invalid'
                    else:
                        packet['experiment']['trial_artifacts'].pop()
                    target.write_text(json.dumps(packet))
                    return result

                with patch('cx_eval_lab.ci_conformance.subprocess.run', side_effect=invoke) as runner, \
                        self.assertRaises(exception):
                    run_conformance(output, 'test-revision')
                self.assertEqual(3, runner.call_count)
                self.assertFalse((output / 'conformance.json').exists())
                failure_path = output / 'conformance-failure.json'
                report = json.loads(failure_path.read_text())
                self.assertEqual('ci-conformance-failure-v1', report['schema'])
                self.assertEqual('test-revision', report['code_revision'])
                self.assertFalse(report['deployment_authorized'])
                self.assertEqual('policy-bypass', report['failed_control'])
                self.assertEqual(phase, report['phase'])
                self.assertEqual(status, report['status'])
                self.assertEqual('FileNotFoundError' if status == 'launch_error' else exception.__name__,
                                 report['error_type'])
                self.assertNotIn('action', report)
                self.assertNotIn('candidate_action', report)
                from cx_eval_lab.evidence import canonical_hash
                self.assertEqual([
                    {'name': name, 'artifact': f'{name}.json', 'action': action,
                     'replayed_trials': 20,
                     'artifact_hash': canonical_hash(json.loads((output / f'{name}.json').read_text()))}
                    for name, action in [('reference', 'lab_pass'), ('insufficient-evidence', 'hold')]
                ], report['checks'])
                record = json.loads((output / 'policy-bypass-command.json').read_text())
                self.assertEqual(2, record['expected_returncode'])
                if phase == 'command':
                    self.assertIsNone(record['returncode'])
                    self.assertEqual(status, record['status'])
                if status == 'timeout':
                    self.assertEqual('partial\ufffd', record['stdout'])
                    self.assertEqual('error\ufffd', record['stderr'])
                before = failure_path.read_bytes()
                with patch('cx_eval_lab.ci_conformance.subprocess.run') as runner:
                    with self.assertRaises(FileExistsError):
                        run_conformance(output, 'test-revision')
                    runner.assert_not_called()
                self.assertEqual(before, failure_path.read_bytes())

    def test_first_timeout_does_not_run_later_controls(self):
        from cx_eval_lab.ci_conformance import run_conformance
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'
            error = subprocess.TimeoutExpired('experiment', 30, output='text partial')
            with patch('cx_eval_lab.ci_conformance.subprocess.run', side_effect=error) as runner, \
                    self.assertRaises(subprocess.TimeoutExpired) as raised:
                run_conformance(output, 'test-revision')
            self.assertIs(error, raised.exception)
            runner.assert_called_once()
            report = json.loads((output / 'conformance-failure.json').read_text())
            self.assertEqual([], report['checks'])
            self.assertEqual('reference', report['failed_control'])
            record = json.loads((output / 'reference-command.json').read_text())
            self.assertEqual('text partial', record['stdout'])
            self.assertEqual('', record['stderr'])

    def test_real_subprocess_timeout_retains_partial_streams(self):
        from cx_eval_lab.ci_conformance import run_conformance
        real_run = subprocess.run

        def slow_child(command, **kwargs):
            return real_run([sys.executable, '-c',
                             ('import os,time; os.write(1,b"started\\xff"); '
                              'os.write(2,b"waiting\\xfe"); time.sleep(10)')],
                            **{**kwargs, 'timeout': 0.5})

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'
            with patch('cx_eval_lab.ci_conformance.subprocess.run', side_effect=slow_child) as runner, \
                    self.assertRaises(subprocess.TimeoutExpired):
                run_conformance(output, 'test-revision')
            runner.assert_called_once()
            record = json.loads((output / 'reference-command.json').read_text())
            self.assertIsNone(record['returncode'])
            self.assertEqual('started\ufffd', record['stdout'])
            self.assertEqual('waiting\ufffd', record['stderr'])
            self.assertFalse((output / 'conformance.json').exists())

    def test_cli_reports_malformed_shape_as_controlled_failure(self):
        from cx_eval_lab.ci_conformance import main
        with patch.object(sys, 'argv', ['ci_conformance', '--output-dir', 'unused',
                                       '--code-revision', 'test-revision']), \
                patch('cx_eval_lab.ci_conformance.run_conformance', side_effect=TypeError('bad shape')), \
                patch('sys.stderr', new_callable=io.StringIO) as stderr:
            with self.assertRaises(SystemExit) as raised:
                main()
            self.assertEqual(2, raised.exception.code)
            self.assertIn('conformance failed', stderr.getvalue())

    def test_diagnostic_write_failure_preserves_original_timeout(self):
        from cx_eval_lab.ci_conformance import run_conformance
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'
            error = subprocess.TimeoutExpired('experiment', 30)
            with patch('cx_eval_lab.ci_conformance.subprocess.run', side_effect=error), \
                    patch('cx_eval_lab.ci_conformance._write', side_effect=PermissionError('unwritable')), \
                    self.assertRaises(subprocess.TimeoutExpired) as raised:
                run_conformance(output, 'test-revision')
            self.assertIs(error, raised.exception)
            self.assertEqual(2, len(error.__notes__))
            self.assertFalse((output / 'conformance.json').exists())

    def test_pages_requires_read_only_conformance_job(self):
        workflow = ROOT / '.github/workflows/eval-conformance.yml'
        self.assertTrue(workflow.is_file(), 'reusable conformance workflow is missing')
        document = yaml.load(workflow.read_text(), Loader=yaml.BaseLoader)
        self.assertIn('pull_request', document['on'])
        self.assertIn('workflow_call', document['on'])
        self.assertNotIn('pull_request_target', document['on'])
        self.assertEqual({'contents': 'read'}, document['permissions'])
        steps = document['jobs']['conformance']['steps']
        self.assertTrue(any('ci_conformance' in step.get('run', '') for step in steps))
        self.assertTrue(any('coverage report --fail-under=80' in step.get('run', '') for step in steps))
        uploads = [step for step in steps if 'upload-artifact@' in step.get('uses', '')]
        self.assertEqual('always()', uploads[0]['if'])
        self.assertFalse(any(step.get('continue-on-error') == 'true' for step in steps))
        pages = yaml.load((ROOT / '.github/workflows/pages.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual('eval-conformance', pages['jobs']['build-and-deploy']['needs'])

    def test_packet_verification_rejects_missing_evidence_and_authority_escalation(self):
        from cx_eval_lab.ci_conformance import run_conformance, verify_packet
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'evidence'
            run_conformance(output, 'test-revision')
            original = json.loads((output / 'reference.json').read_text())
            for mutate, expected in (
                (lambda p: p['experiment']['trial_artifacts'].pop(), 'artifact'),
                (lambda p: p['receipt'].update(action='canary'), 'action'),
                (lambda p: p['receipt'].update(authority_ceiling='production'), 'authority'),
                (lambda p: p['receipt'].update(receipt_hash='wrong'), 'receipt hash'),
            ):
                with self.subTest(expected=expected):
                    changed = copy.deepcopy(original)
                    mutate(changed)
                    with self.assertRaisesRegex(ValueError, expected):
                        verify_packet(changed, action='lab_pass', revision='test-revision')
            with self.assertRaisesRegex(ValueError, 'revision'):
                verify_packet(original, action='lab_pass', revision='another-revision')


if __name__ == '__main__':
    unittest.main()
