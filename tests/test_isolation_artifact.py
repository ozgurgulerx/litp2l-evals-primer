"""Reconstruct book results from retained operations, not stored pass flags."""

import json
from pathlib import Path
import unittest

from cx_eval_lab.isolation_study import replay_study


class IsolationArtifactTests(unittest.TestCase):
    def test_retained_packet_supports_private_and_permitted_sharing_results(self):
        path = Path(__file__).resolve().parents[1] / 'docs/assets/isolation-study-v1.json'
        report = json.loads(path.read_text())
        grades = replay_study(report)
        self.assertEqual([1, 1, 1, 0, 0, 0],
                         [grade['foreign_marker_responses'] for grade in grades])
        self.assertEqual([False, False, False, True, True, True],
                         [grade['contract_passed'] for grade in grades])
        self.assertEqual([1, 1, 1, 2, 2, 2], [grade['private_writes'] for grade in grades])
        for grade in grades:
            self.assertTrue(grade['same_run_cache_hit'])
            self.assertTrue(grade['shared_policy_readable'])
            self.assertTrue(grade['shared_policy_unchanged'])
            self.assertEqual(2, grade['shared_policy_overwrites_denied'])
        self.assertEqual(18, sum(len(row['responses']) for row in report['comparisons']))
        self.assertIs(report['deployment_authorized'], False)


if __name__ == '__main__':
    unittest.main()
