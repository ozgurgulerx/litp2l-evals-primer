"""A mocked SDK campaign is an integration experiment, not a live model study."""

import json
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class NativeProviderStudyTests(unittest.TestCase):
    def test_retained_transport_joins_and_redecoded_judgments(self):
        from cx_eval_lab.campaign_budget import CampaignPolicy
        from cx_eval_lab.campaign_gate import assess_campaign
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.openai_judge import JudgeConfig, OpenAIResponsesJudge
        from tests.test_openai_judge import FakeClient
        from types import SimpleNamespace
        study = json.loads(Path('docs/assets/native-provider-campaign-v1.json').read_text())
        judge = OpenAIResponsesJudge(JudgeConfig(**study['judge_config']), FakeClient())
        trust = {study['calibration']['record_hash']}
        for control in study['controls']:
            assessment = assess_campaign(control['packet'], control['snapshot'],
                expected_policy=CampaignPolicy(**control['operator_policy']),
                trusted_packet_hash=control['simulated_operator_anchors']['packet'],
                trusted_snapshot_hash=control['simulated_operator_anchors']['snapshot'],
                trusted_calibration_hashes=trust)
            self.assertEqual(canonical_hash(asdict(assessment)), canonical_hash(control['assessment']))
            stages = [a['payload']['semantic_stage'] for a in control['packet']['trial_artifacts']]
            dispatched = [s for s in stages if json.loads(s['judgment']['campaign_audit_json'])['status']
                          == 'recorded']
            self.assertEqual(len(control['transport']), len(dispatched))
            for call, stage in zip(control['transport'], dispatched):
                self.assertEqual(json.loads(call['request']['input'][0]['content']), stage['request'])
                audit = json.loads(stage['judgment']['provider_audit_json'])
                if call['status_code'] == 429:
                    self.assertEqual('request_failed', audit['status'])
                    self.assertIsNone(stage['judgment']['runtime_evidence'])
                    continue
                raw = audit['response']
                for key in ('id', 'model', 'status'):
                    self.assertEqual(call['response'][key], raw[key])
                for key in ('input_tokens', 'output_tokens', 'total_tokens'):
                    self.assertEqual(call['response']['usage'][key], raw['usage'][key])
                self.assertEqual(call['response']['output'][0]['content'][0]['text'],
                                 raw['output'][0]['content'][0]['text'])
                # Adapter interpretation only, not independent judgment of truth.
                decoded = judge._decode(SimpleNamespace(model_dump=lambda **kwargs: raw))
                self.assertEqual(decoded.verdict, stage['judgment']['verdict'])
                self.assertEqual(decoded.explanation, stage['judgment']['explanation'])
                self.assertEqual(canonical_hash(asdict(decoded.runtime_evidence)),
                                 canonical_hash(stage['judgment']['runtime_evidence']))

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
