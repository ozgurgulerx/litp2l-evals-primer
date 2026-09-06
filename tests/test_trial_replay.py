"""Complete paired evidence must allow re-grading without rerunning agents."""

import copy
import unittest

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.runner import run_paired_experiment, DEFAULT_MEASUREMENT_PROFILE
from tests.test_evidence_spine import make_manifest


class TrialReplayTests(unittest.TestCase):
    def packet(self):
        return run_paired_experiment(
            baseline_agent=ReferenceSupportAgent(), candidate_agent=ReferenceSupportAgent(),
            cases=load_refund_cases('evals/cx-support/datasets/regression/refund_v1.json'),
            manifest=make_manifest(),
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


if __name__ == '__main__':
    unittest.main()
