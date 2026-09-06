"""A structural score must not become complete application qualification."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ResolutionPairedStudyTests(unittest.TestCase):
    def test_study_retains_two_replayable_comparisons_without_release_authority(self):
        from cx_eval_lab.resolution_paired_study import run_study
        from cx_eval_lab.artifacts import replay_packet
        report = run_study()
        self.assertFalse(report['deployment_authorized'])
        self.assertEqual(2, len(report['comparisons']))
        for row in report['comparisons']:
            self.assertEqual(16, len(replay_packet(row['packet'])))
            self.assertEqual('block', row['release_receipt']['action'])
            self.assertEqual('none', row['release_receipt']['authority_ceiling'])
            self.assertEqual(1, row['release_receipt']['comparison']['independent_cluster_count'])
            self.assertEqual(16, row['unqualified_message_trials'])
        self.assertEqual([2, 8], [r['candidate_contract_passes'] for r in report['comparisons']])
        self.assertEqual([4, 6], [r['candidate_completed_tasks'] for r in report['comparisons']])

    def test_cli_rejects_overwrite_and_ci_retains_its_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'resolution.json'
            command = [sys.executable, '-m', 'cx_eval_lab.resolution_paired_study', '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, first.returncode, first.stderr)
            original = output.read_bytes()
            self.assertEqual('paired-order-resolution-study-v1', json.loads(original)['study'])
            self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(original, output.read_bytes())
        self.assertIn('cx_eval_lab.resolution_paired_study',
                      Path('.github/workflows/eval-conformance.yml').read_text())


if __name__ == '__main__':
    unittest.main()
