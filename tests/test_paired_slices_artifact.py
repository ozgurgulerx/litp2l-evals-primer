"""The published slice example must match re-execution and independently derived grades."""

import json
import unittest
from pathlib import Path

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.paired_slices import derive_slice_report, run_study

ARTIFACT = Path(__file__).resolve().parents[1] / 'docs/assets/paired-slices-v1.json'


class PairedSlicesArtifactTests(unittest.TestCase):
    def test_retained_study_matches_actual_mock_execution(self):
        retained = json.loads(ARTIFACT.read_text())
        self.assertEqual(retained, run_study())
        self.assertEqual('executed_deterministic_mock', retained['evidence_kind'])
        self.assertFalse(retained['deployment_authorized'])

    def test_replayed_report_preserves_changes_and_independent_denominators(self):
        retained = json.loads(ARTIFACT.read_text())
        self.assertEqual(16, len(replay_packet(retained['packet'])))
        report = derive_slice_report(retained['packet'], tuple(retained['protocol']['required_slices']))
        self.assertEqual(retained['report'], report)
        overall = report['overall']
        self.assertEqual((4, 8, 3), (overall['case_count'], overall['pair_count'], overall['customer_count']))
        self.assertEqual(6, len(overall['changes']['fixed']))
        self.assertEqual(2, len(overall['changes']['regressed']))
        self.assertEqual([], overall['changes']['unqualified'])
        self.assertEqual(0.5, overall['trial_weighted_delta'])
        self.assertAlmostEqual(1 / 3, overall['cluster_weighted_delta'])
        protected = next(row for row in report['slices'] if row['slice'] == 'risk:protected')
        self.assertEqual(1, protected['customer_count'])
        self.assertEqual(-1, protected['trial_weighted_delta'])
        self.assertIsNone(protected['comparison'])
        self.assertEqual('hold', report['status'])
        self.assertFalse(report['deployment_authorized'])
