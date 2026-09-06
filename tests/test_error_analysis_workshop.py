"""A mixed trace workshop derives observations without inventing human review."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'docs/assets/native-resolution-semantic-v1.json'
PIN = 'sha256:638237b1615ec159c87d8ec8f2bb748867c2b319c93ff678470f4e0619419839'
TRUST = frozenset({'sha256:454a18e2f18782f37ecfb2c7832a259aead13455be9cacfe94a7464e0d54730b'})


class ErrorAnalysisWorkshopTests(unittest.TestCase):
    def build(self, **changes):
        from cx_eval_lab.error_analysis_workshop import build_workshop
        return build_workshop(**{'source': SOURCE, 'expected_source_sha256': PIN,
                                 'trusted_calibration_hashes': TRUST, **changes})

    def test_mixed_examples_overlap_and_denominators(self):
        report = self.build()
        self.assertEqual(list('ABCDEFGH'), [row['item_id'] for row in report['learner_views']])
        summary = report['summary']
        self.assertEqual((8, 3, 1), (summary['trial_count'], summary['case_count'], summary['customer_count']))
        self.assertEqual((5, 3), (summary['failed_trials'], summary['passed_trials']))
        self.assertEqual({'wrong_object': 2, 'missing_required_clarification': 2, 'unsupported_settlement': 2},
                         {key: row['trial_count'] for key, row in summary['categories'].items()})
        self.assertEqual({'wrong_object': 2, 'missing_required_clarification': 2, 'unsupported_settlement': 1},
                         {key: row['case_count'] for key, row in summary['categories'].items()})
        self.assertTrue(summary['categories_overlap'])

    def test_safe_unresolved_is_not_completed_or_a_failure(self):
        key = {row['item_id']: row for row in self.build()['instructor_key']}
        self.assertEqual(['wrong_object', 'missing_required_clarification'], key['D']['observations']['categories'])
        self.assertTrue(key['H']['observations']['joint_passed'])
        self.assertFalse(key['H']['observations']['task_completed'])
        self.assertTrue(key['H']['observations']['safe_unresolved'])
        self.assertEqual([], key['B']['observations']['categories'])
        self.assertEqual([], key['G']['observations']['categories'])

    def test_learner_views_keep_evidence_but_not_agent_or_grading_metadata(self):
        report = self.build()
        forbidden = {'agent', 'candidate', 'evaluation', 'passed', 'structural_contract_passed',
                     'semantic_status', 'semantic_stage', 'artifact_hash', 'source_ref'}
        def keys(value):
            if isinstance(value, dict):
                return set(value) | set().union(*(keys(v) for v in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(v) for v in value))
            return set()
        for row in report['learner_views']:
            self.assertFalse(forbidden & keys(row))
            self.assertEqual(3, len(row['orders']))
            self.assertIn('expected_order_id', row['task_specification'])
            self.assertIn('required_clarifications', row['task_specification'])
            self.assertTrue(row['tool_events'])
        serialized = json.dumps(report['learner_views'])
        self.assertNotIn('first-record-mutant', serialized)
        self.assertNotIn('false-settlement-mutant', serialized)

    def test_source_and_baseline_contrast_are_explicit_and_immutable(self):
        before = SOURCE.read_bytes()
        first = self.build()
        self.assertEqual(first, self.build())
        self.assertEqual(before, SOURCE.read_bytes())
        self.assertFalse(first['new_agent_executions'])
        self.assertFalse(first['actual_human_annotations'])
        self.assertFalse(first['deployment_authorized'])
        self.assertEqual(PIN, first['source']['bytes_sha256'])
        for row in first['instructor_key']:
            self.assertEqual('candidate', row['source_ref']['arm'])
            self.assertEqual('baseline', row['baseline_contrast']['source_ref']['arm'])
            self.assertTrue(row['baseline_contrast']['observations']['joint_passed'])
            self.assertEqual(row['source_ref']['case_id'], row['baseline_contrast']['source_ref']['case_id'])

    def test_wrong_source_or_missing_fixture_trust_is_rejected(self):
        for change in ({'expected_source_sha256': 'sha256:' + '0' * 64},
                       {'trusted_calibration_hashes': frozenset()}):
            with self.assertRaises(ValueError):
                self.build(**change)

    def test_cli_requires_pins_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'workshop.json'
            command = [sys.executable, '-m', 'cx_eval_lab.error_analysis_workshop',
                       '--source', str(SOURCE), '--output', str(path)]
            self.assertNotEqual(0, subprocess.run(command, capture_output=True, check=False).returncode)
            command += ['--expected-source-sha256', PIN, '--trusted-calibration-hash', next(iter(TRUST))]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(0, first.returncode, first.stderr)
            original = path.read_bytes()
            self.assertEqual(self.build(), json.loads(original))
            self.assertNotEqual(0, subprocess.run(command, capture_output=True, check=False).returncode)
            self.assertEqual(original, path.read_bytes())
