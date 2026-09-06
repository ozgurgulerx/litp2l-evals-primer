"""Executed paired changes must retain slice, denominator and unknown semantics."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cx_eval_lab.evidence import canonical_hash


def rehash(packet):
    replacements = {}
    for artifact in packet['trial_artifacts']:
        old = artifact['artifact_hash']
        artifact['artifact_hash'] = canonical_hash(artifact['payload'])
        replacements[old] = artifact['artifact_hash']
    for arm in ('baseline', 'candidate'):
        for row in packet[f'{arm}_trials']:
            row['artifact_hash'] = replacements[row['artifact_hash']]


class PairedSliceTests(unittest.TestCase):
    def setUp(self):
        from cx_eval_lab.paired_slices import run_study
        self.study = run_study()

    def derive(self, packet=None, required=('risk:protected',)):
        from cx_eval_lab.paired_slices import derive_slice_report
        return derive_slice_report(self.study['packet'] if packet is None else packet, required)

    def test_executed_improvement_hides_protected_regression(self):
        report = self.derive()
        overall = report['overall']
        self.assertEqual((4, 8, 3), (overall['case_count'], overall['pair_count'], overall['customer_count']))
        self.assertEqual(0.5, overall['trial_weighted_delta'])
        self.assertAlmostEqual(1 / 3, overall['cluster_weighted_delta'])
        self.assertEqual(6, len(overall['changes']['fixed']))
        self.assertEqual(2, len(overall['changes']['regressed']))
        protected = next(row for row in report['slices'] if row['slice'] == 'risk:protected')
        self.assertEqual(-1, protected['trial_weighted_delta'])
        self.assertEqual('required', protected['membership'])
        self.assertEqual('hold', report['status'])
        self.assertFalse(report['deployment_authorized'])
        self.assertIn({'case_id': 'case-3', 'trial_index': 0}, protected['changes']['regressed'])

    def test_missing_required_slice_is_unknown_not_zero(self):
        from cx_eval_lab.paired_slices import run_study
        report = run_study(required_slices=('language:missing',))['report']
        missing = next(row for row in report['slices'] if row['slice'] == 'language:missing')
        self.assertEqual(0, missing['pair_count'])
        self.assertIsNone(missing['baseline_rate'])
        self.assertIsNone(missing['trial_weighted_delta'])
        self.assertEqual('hold', missing['status'])
        self.assertEqual('exploratory', next(row for row in report['slices'] if row['slice'] == 'all')['membership'])

    def test_unknown_prose_is_not_classified_as_a_known_regression(self):
        from cx_eval_lab.paired_slices import run_study
        report = run_study(unqualified_candidate=True)['report']
        self.assertEqual(8, len(report['overall']['changes']['unqualified']))
        self.assertEqual([], report['overall']['changes']['regressed'])
        self.assertIsNone(report['overall']['comparison'])
        self.assertIsNone(report['overall']['trial_weighted_delta'])

    def test_overlapping_slices_are_not_disjoint_totals(self):
        report = self.derive()
        self.assertGreater(sum(row['pair_count'] for row in report['slices']), report['overall']['pair_count'])
        self.assertTrue(report['overlapping_slices_not_additive'])

    def test_replay_rejects_hash_and_coherently_forged_pass_summary(self):
        for coherent in (False, True):
            packet = copy.deepcopy(self.study['packet'])
            artifact = packet['trial_artifacts'][0]
            artifact['payload']['evaluation']['passed'] = not artifact['payload']['evaluation']['passed']
            if coherent:
                rehash(packet)
                packet['baseline_trials'][0]['passed'] = artifact['payload']['evaluation']['passed']
            with self.assertRaises(ValueError):
                self.derive(packet)

    def test_case_metadata_cannot_change_between_arms_or_repetitions(self):
        for key, value in (('slices', ['changed']), ('customer_id', 'other'), ('utterance', 'changed')):
            packet = copy.deepcopy(self.study['packet'])
            packet['trial_artifacts'][1]['payload']['case'][key] = value
            rehash(packet)
            with self.assertRaises(ValueError):
                self.derive(packet)

    def test_incomplete_pair_inventory_and_native_schema_are_rejected(self):
        for action in ('missing', 'duplicate', 'native', 'bool-index'):
            packet = copy.deepcopy(self.study['packet'])
            if action == 'missing':
                packet['candidate_trials'].pop()
            elif action == 'duplicate':
                packet['candidate_trials'].append(copy.deepcopy(packet['candidate_trials'][0]))
            elif action == 'native':
                packet['trial_artifacts'][0]['payload']['schema'] = 'resolution-trial-v2'
            else:
                packet['baseline_trials'][0]['trial_index'] = False
            with self.assertRaises(ValueError):
                self.derive(packet)

    def test_required_slice_contract_and_input_immutability(self):
        original = copy.deepcopy(self.study['packet'])
        self.derive()
        self.assertEqual(original, self.study['packet'])
        for required in ('all', ('all', 'all'), ('',), (True,)):
            with self.assertRaises(ValueError):
                self.derive(required=required)
        with self.assertRaises(ValueError):
            self.derive(required=('changed-policy',))

    def test_cli_retains_packet_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'study.json'
            command = [sys.executable, '-m', 'cx_eval_lab.paired_slices', '--output', str(path)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, first.returncode, first.stderr)
            original = path.read_bytes()
            self.assertEqual('paired-slices-v1', json.loads(original)['report']['schema'])
            self.assertNotEqual(0, subprocess.run(command, capture_output=True).returncode)
            self.assertEqual(original, path.read_bytes())
