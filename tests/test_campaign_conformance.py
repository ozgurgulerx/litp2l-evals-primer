"""Executed offline controls connect campaign checks to bounded release receipts."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CampaignConformanceTests(unittest.TestCase):
    def test_controls_recompute_campaign_and_combined_actions(self):
        from cx_eval_lab.campaign_conformance import run_controls
        report = run_controls()
        observed = {row['name']: (row['assessment']['status'], row['release_receipt']['action'])
                    for row in report['controls']}
        self.assertEqual({'all-known': ('clear', 'hold'), 'unknown-cost': ('hold', 'block'),
                          'reservation-overrun': ('block', 'block'),
                          'changed-snapshot': ('block', 'block')}, observed)
        self.assertFalse(report['deployment_authorized'])
        self.assertTrue(all(row['release_receipt']['authority_ceiling'] == 'none'
                            for row in report['controls']))

    def test_cli_output_is_immutable_and_workflow_runs_controls(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'controls.json'
            command = [sys.executable, '-m', 'cx_eval_lab.campaign_conformance', '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, first.returncode, first.stderr)
            original = output.read_bytes()
            self.assertEqual(4, len(json.loads(original)['controls']))
            self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(original, output.read_bytes())
        workflow = Path('.github/workflows/eval-conformance.yml').read_text()
        self.assertIn('cx_eval_lab.campaign_conformance', workflow)

    def test_retained_controls_reassess_against_their_explicit_fixture_anchors(self):
        from dataclasses import asdict
        from cx_eval_lab.campaign_budget import CampaignPolicy
        from cx_eval_lab.campaign_gate import assess_campaign
        report = json.loads(Path('docs/assets/campaign-release-conformance-v1.json').read_text())
        for control in report['controls']:
            anchors = control['simulated_operator_anchors']
            assessment = assess_campaign(control['packet'], control['snapshot'],
                expected_policy=CampaignPolicy(**control['operator_policy']),
                trusted_packet_hash=anchors['packet'], trusted_snapshot_hash=anchors['snapshot'],
                trusted_calibration_hashes=frozenset(control['synthetic_calibration_hashes']))
            self.assertEqual(control['assessment'], json.loads(json.dumps(asdict(assessment))))

    def test_control_runner_rejects_wrong_expected_results_and_authority(self):
        from types import SimpleNamespace
        from cx_eval_lab.campaign_conformance import _control
        from cx_eval_lab.campaign_study import run_study
        study = run_study(unknown_second=False, budget_micro_usd=2000)
        original = json.dumps(study, sort_keys=True)
        with self.assertRaisesRegex(ValueError, 'campaign control failed'):
            _control('wrong-expectation', study, 'block', 'hold')
        with self.assertRaisesRegex(ValueError, 'combined release control failed'):
            _control('wrong-release', study, 'clear', 'lab_pass')
        with patch('cx_eval_lab.campaign_conformance.build_evidence_receipt',
                   return_value=SimpleNamespace(action='hold', authority_ceiling='canary_eligible')):
            with self.assertRaisesRegex(ValueError, 'combined release control failed'):
                _control('unsafe-authority', study, 'clear', 'hold')
        _control('mutated-copy', study, 'block', 'block', tamper=True)
        self.assertEqual(original, json.dumps(study, sort_keys=True))

    def test_cli_refuses_existing_output_before_running_controls(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from cx_eval_lab.campaign_conformance import main
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'controls.json'
            with patch.object(sys, 'argv', ['campaign_conformance', '--output', str(output)]):
                main()
                original = output.read_bytes()
                self.assertEqual(4, len(json.loads(original)['controls']))
                with patch('cx_eval_lab.campaign_conformance.run_controls') as rerun:
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as failure:
                        main()
                    self.assertEqual(2, failure.exception.code)
                    rerun.assert_not_called()
                self.assertEqual(original, output.read_bytes())


if __name__ == '__main__':
    unittest.main()
