"""Integrated killed execution -> observed effect -> durable rollback receipt."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cx_eval_lab import recovery_decision_study as study
from cx_eval_lab.recovery_decision_study import run_study


class RecoveryDecisionStudyTests(unittest.TestCase):
    def test_real_kill_retains_missing_response_and_rolls_back_once(self):
        report = run_study()
        self.assertTrue(report['conformance_passed'])
        self.assertFalse(report['deployment_authorized'])
        self.assertEqual(len(report['joined']['members']), 40)
        selected = [r for r in report['joined']['members'] if r['served'] == 'candidate']
        self.assertEqual(len(selected), report['joined']['planned_served'])
        self.assertEqual(selected[0]['status'], 'no_completion')
        self.assertIsNone(selected[0]['candidate_pass'])
        self.assertIs(selected[0]['observed_wrong_order_violation'], True)
        self.assertEqual(report['budget']['charged_actions'], 1)
        self.assertEqual(report['receipt']['decision']['reason'], 'hard_violation')
        self.assertEqual(report['receipt'], report['reopened_receipt'])
        self.assertEqual(report['controller_state']['revision'], 1)
        self.assertEqual(report['process']['exitcode'], -9)

    def test_cli_writes_new_packet_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            command = [sys.executable, '-m', 'cx_eval_lab.recovery_decision_study', '--output', str(path)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(path.read_text())['conformance_passed'])
            original = path.read_bytes()
            result = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_bytes(), original)

    def test_ci_generates_packet_before_always_upload(self):
        workflow = Path('.github/workflows/eval-conformance.yml').read_text()
        command = 'uv run python -m cx_eval_lab.recovery_decision_study --output ci-evidence/recovery-decision.json'
        self.assertIn(command, workflow)
        self.assertLess(workflow.index(command), workflow.index('Retain available evidence even on failure'))

    def test_cli_entrypoint_and_early_overwrite_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.json'
            with patch.object(sys, 'argv', ['study', '--output', str(path)]):
                study.main()
                with patch.object(study, 'run_study') as execute, self.assertRaises(SystemExit):
                    study.main()
                execute.assert_not_called()
            self.assertTrue(json.loads(path.read_text())['conformance_passed'])

    def test_worker_can_finish_if_supervisor_does_not_interrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            campaign = study.DurableCampaign.initialize(root / 'effects', **study.POLICY)
            journal = study.CompletionJournal.initialize(root / 'journal', campaign)
            plan = study.build_window_plan(study.ExposureState('candidate', 'baseline'), 1,
                'wrong_order', execution_namespace='study', manifest_digest='a' * 64,
                effect_backend='durable')
            ready, release = Mock(), Mock()
            member = plan['members'][0]
            study._worker(campaign.path, journal.path, member, 'a' * 64, ready, release)
            ready.set.assert_called_once()
            release.wait.assert_called_once_with(30)
            self.assertEqual(journal.inspect(member['candidate_namespace'])['status'], 'completed')
            self.assertEqual(campaign.snapshot()['charged_actions'], 1)
