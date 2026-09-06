"""Executed offline controls connect campaign checks to bounded release receipts."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == '__main__':
    unittest.main()
