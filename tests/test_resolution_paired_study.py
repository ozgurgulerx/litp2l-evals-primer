"""A structural score must not become complete application qualification."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


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
        # Three right-order endpoints for the mutant, but one acted before clarification.
        self.assertEqual([3, 6], [r['candidate_completed_tasks'] for r in report['comparisons']])

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

    def test_retained_comparisons_replay_with_documented_outcomes(self):
        from cx_eval_lab.artifacts import replay_packet
        report = json.loads(Path('docs/assets/paired-order-resolution-v1.json').read_text())
        for row in report['comparisons']:
            results = replay_packet(row['packet'])
            self.assertEqual(16, len(results))
            self.assertEqual(row['candidate_contract_passes'], sum(r.passed for r in results[8:]))
            self.assertEqual(row['candidate_completed_tasks'], sum(r.task_completed for r in results[8:]))

    def test_cli_checks_output_before_execution_and_rejects_unsafe_authority(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from types import SimpleNamespace
        from cx_eval_lab.resolution_paired_study import main, run_study
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'study.json'
            with patch.object(sys, 'argv', ['study', '--output', str(output)]):
                main()
                original = output.read_bytes()
                with patch('cx_eval_lab.resolution_paired_study.run_study') as execute:
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as failure:
                        main()
                    self.assertEqual(2, failure.exception.code)
                    execute.assert_not_called()
                self.assertEqual(original, output.read_bytes())
        with patch('cx_eval_lab.resolution_paired_study.build_evidence_receipt',
                   return_value=SimpleNamespace(action='lab_pass', authority_ceiling='canary_eligible')):
            with self.assertRaisesRegex(ValueError, 'cannot authorize release'):
                run_study()


if __name__ == '__main__':
    unittest.main()
