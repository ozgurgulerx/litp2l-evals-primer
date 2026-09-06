"""CI must exercise passing, held and blocked evidence without deploying AI."""

import json
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[1]


class CIConformanceTests(unittest.TestCase):
    def test_cli_retains_three_actions_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'ci-evidence'
            command = [sys.executable, '-m', 'cx_eval_lab.ci_conformance',
                       '--output-dir', str(output), '--code-revision', 'test-revision']
            result = subprocess.run(command, capture_output=True, text=True, timeout=15)
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads((output / 'conformance.json').read_text())
            self.assertEqual(['lab_pass', 'hold', 'block'], [r['action'] for r in report['checks']])
            self.assertFalse(report['deployment_authorized'])
            self.assertEqual('test-revision', report['code_revision'])
            for row in report['checks']:
                self.assertTrue((output / row['artifact']).is_file())
                self.assertEqual(20, row['replayed_trials'])
            second = subprocess.run(command, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(0, second.returncode)

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
