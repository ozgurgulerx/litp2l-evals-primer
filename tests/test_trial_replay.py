"""Complete paired evidence must allow re-grading without rerunning agents."""

import copy
import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from dataclasses import replace

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.runner import run_paired_experiment, DEFAULT_MEASUREMENT_PROFILE
from tests.test_evidence_spine import make_manifest
from cx_eval_lab.evidence import canonical_hash


class TrialReplayTests(unittest.TestCase):
    def packet(self):
        cases = load_refund_cases('evals/cx-support/datasets/regression/refund_v1.json')
        return run_paired_experiment(
            baseline_agent=ReferenceSupportAgent(), candidate_agent=ReferenceSupportAgent(),
            cases=cases,
            manifest=replace(make_manifest(), population_hash=canonical_hash(
                [[case.case_id, case.customer_id, list(case.slices)] for case in cases])),
            baseline_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
            candidate_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
        ).to_dict()

    def test_paired_packet_preserves_complete_regradable_artifacts(self):
        packet = self.packet()
        self.assertIn('trial_artifacts', packet)
        self.assertEqual(20, len(packet['trial_artifacts']))
        for row in packet['baseline_trials'] + packet['candidate_trials']:
            self.assertIn('artifact_hash', row)

    def test_replay_reconstructs_grades_and_rejects_tampered_or_missing_evidence(self):
        from cx_eval_lab.artifacts import replay_packet
        packet = self.packet()
        results = replay_packet(packet)
        self.assertEqual(20, len(results))
        self.assertTrue(all(result.passed for result in results))
        changed = copy.deepcopy(packet)
        changed['trial_artifacts'][0]['payload']['output']['message'] = 'False message'
        with self.assertRaisesRegex(ValueError, 'artifact hash'):
            replay_packet(changed)
        missing = copy.deepcopy(packet)
        missing['trial_artifacts'].pop()
        with self.assertRaisesRegex(ValueError, 'artifact'):
            replay_packet(missing)

    def test_replay_rejects_omitted_entire_case(self):
        from cx_eval_lab.artifacts import replay_packet
        packet = self.packet()
        omitted = packet['baseline_trials'][0]['case_id']
        for arm in ('baseline', 'candidate'):
            packet[f'{arm}_trials'] = [row for row in packet[f'{arm}_trials']
                                     if row['case_id'] != omitted]
        packet['trial_artifacts'] = [item for item in packet['trial_artifacts']
                                    if item['payload']['identity']['case_id'] != omitted]
        with self.assertRaisesRegex(ValueError, 'population'):
            replay_packet(packet)

    def test_fresh_process_cli_replays_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'packet.json'
            path.write_text(json.dumps({'experiment': self.packet()}))
            command = [sys.executable, '-m', 'cx_eval_lab', 'replay', '--input', str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('20 trials', result.stdout)
            self.assertIn('lab_only', result.stdout)


if __name__ == '__main__':
    unittest.main()
