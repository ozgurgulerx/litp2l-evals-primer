"""End-to-end synthetic campaign evidence and selected-cost accounting."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CampaignStudyTests(unittest.TestCase):
    def test_executed_study_preserves_unknowns_and_independently_replays(self):
        from cx_eval_lab.campaign_study import run_study
        from cx_eval_lab.artifacts import replay_packet
        from cx_eval_lab.cost_accounting import summarize_packet_costs
        report = run_study()
        trust = frozenset({report['synthetic_calibration_hash']})
        self.assertEqual(4, len(replay_packet(report['packet'], trusted_calibration_hashes=trust)))
        costs = summarize_packet_costs(report['packet'], trusted_calibration_hashes=trust)
        self.assertEqual(report['costs'], costs)
        self.assertEqual(320000, costs['agent_known_micro_usd'])
        self.assertEqual(360, costs['judge_known_micro_usd'])
        self.assertEqual(320360, costs['known_subtotal_micro_usd'])
        self.assertEqual(1, costs['unknown_component_count'])
        self.assertEqual(2, costs['judge_not_dispatched_trials'])
        self.assertIsNone(costs['complete_selected_estimate_micro_usd'])
        self.assertEqual(2, report['ledger']['admissions'])
        self.assertEqual(960, report['ledger']['committed_micro_usd'])
        self.assertFalse(report['deployment_authorized'])

    def test_all_known_costs_and_invalid_artifacts(self):
        from cx_eval_lab.campaign_study import run_study
        from cx_eval_lab.cost_accounting import summarize_packet_costs
        report = run_study(unknown_second=False, budget_micro_usd=2000)
        self.assertEqual(321440, report['costs']['complete_selected_estimate_micro_usd'])
        self.assertEqual(0, report['costs']['unknown_component_count'])
        report['packet']['trial_artifacts'][0]['payload']['cost_usd'] = 999
        with self.assertRaises(ValueError):
            summarize_packet_costs(report['packet'], trusted_calibration_hashes=frozenset(
                {report['synthetic_calibration_hash']}))

    def test_cli_preserves_existing_output_and_emits_regradable_packet(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'study.json'
            command = [sys.executable, '-m', 'cx_eval_lab.campaign_study', '--output', str(path)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, first.returncode, first.stderr)
            original = path.read_bytes()
            self.assertEqual(2, json.loads(original)['ledger']['admissions'])
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, second.returncode)
            self.assertEqual(original, path.read_bytes())

    def test_retained_study_costs_recompute_without_a_provider(self):
        from cx_eval_lab.cost_accounting import summarize_packet_costs
        report = json.loads(Path('docs/assets/judge-campaign-study-v1.json').read_text())
        self.assertEqual(report['costs'], summarize_packet_costs(report['packet'],
            trusted_calibration_hashes=frozenset({report['synthetic_calibration_hash']})))


if __name__ == '__main__':
    unittest.main()
