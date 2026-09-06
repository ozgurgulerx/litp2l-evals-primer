"""A mocked SDK campaign is an integration experiment, not a live model study."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class NativeProviderStudyTests(unittest.TestCase):
    def test_controls_derive_campaign_states_and_keep_release_blocked(self):
        from cx_eval_lab.native_provider_study import run_study
        from cx_eval_lab.artifacts import replay_packet
        study = run_study()
        self.assertFalse(study['deployment_authorized'])
        self.assertEqual(4, len(study['calibration_transport']))
        controls = study['controls']
        self.assertEqual(['clear', 'hold', 'hold', 'block'],
                         [c['assessment']['status'] for c in controls])
        self.assertEqual([16, 16, 2, 1], [len(c['transport']) for c in controls])
        trust = {study['calibration']['record_hash']}
        for control in controls:
            self.assertEqual(16, len(replay_packet(control['packet'], trusted_calibration_hashes=trust)))
            self.assertEqual('block', control['release_receipt']['action'])
            self.assertEqual('none', control['release_receipt']['authority_ceiling'])
            for call in control['transport']:
                self.assertEqual('/v1/responses', call['path'])
                self.assertFalse(call['request']['store'])
                self.assertEqual('multi_order_truth_verdict', call['request']['text']['format']['name'])
                self.assertNotIn('expected_order_id', call['request']['input'][0]['content'])
        self.assertEqual(5760, controls[0]['assessment']['known_estimate_micro_usd'])
        self.assertIsNone(controls[1]['costs']['complete_selected_estimate_micro_usd'])

    def test_cli_retains_evidence_without_overwriting(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'transport.json'
            command = [sys.executable, '-m', 'cx_eval_lab.native_provider_study', '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            saved = output.read_bytes()
            self.assertFalse(json.loads(saved)['deployment_authorized'])
            self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(saved, output.read_bytes())


if __name__ == '__main__':
    unittest.main()
