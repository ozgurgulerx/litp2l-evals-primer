"""Retained dataset-promotion evidence must reproduce, not just contain a pass flag."""

import json
import unittest
from pathlib import Path


class IncidentArtifactTests(unittest.TestCase):
    def test_retained_incident_study_reproduces_the_promotion_controls(self):
        path = Path(__file__).resolve().parents[1] / 'docs/assets/incident-regression-v1.json'
        report = json.loads(path.read_text())
        from cx_eval_lab.incident_regression import replay_study

        self.assertTrue(replay_study(report))
        self.assertTrue(report['conformance_passed'])
        self.assertIs(report['deployment_authorized'], False)
        self.assertTrue(report['reruns']['reference']['passed'])
        self.assertFalse(report['reruns']['mutant']['passed'])


if __name__ == '__main__':
    unittest.main()
