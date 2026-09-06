"""Row-derived synthetic qualification exercises wiring, not empirical validity."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class NativeSemanticStudyTests(unittest.TestCase):
    def test_row_compilation_joint_controls_and_current_revocation_are_retained(self):
        from cx_eval_lab.resolution_semantic_study import run_study
        from cx_eval_lab.artifacts import replay_packet
        report = run_study()
        self.assertEqual(4, len(report['calibration']['annotations']['rows']))
        self.assertEqual(2, report['calibration']['record']['truthful_examples'])
        self.assertEqual(2, report['calibration']['record']['false_examples'])
        self.assertEqual('synthetic', report['calibration']['record']['evidence_kind'])
        self.assertEqual('insufficient_calibration_examples', report['strict_policy_rejection'])
        self.assertEqual([0, 2, 8], [c['candidate_joint_passes'] for c in report['comparisons']])
        trust = {report['calibration']['record_hash']}
        for control in report['comparisons']:
            self.assertEqual(16, len(replay_packet(control['packet'], trusted_calibration_hashes=trust)))
            self.assertEqual('block', control['release_receipt']['action'])
            self.assertEqual('none', control['release_receipt']['authority_ceiling'])
        self.assertEqual('not_current', report['revoked_assessment']['calibration_status'])
        self.assertFalse(report['deployment_authorized'])

    def test_cli_refuses_to_overwrite_its_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'native.json'
            command = [sys.executable, '-m', 'cx_eval_lab.resolution_semantic_study', '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, first.returncode, first.stderr)
            original = output.read_bytes()
            self.assertFalse(json.loads(original)['deployment_authorized'])
            self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(original, output.read_bytes())
        self.assertIn('cx_eval_lab.resolution_semantic_study',
                      Path('.github/workflows/eval-conformance.yml').read_text())


if __name__ == '__main__':
    unittest.main()
