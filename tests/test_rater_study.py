"""Synthetic rater analysis preserves paired items, unknowns and assignment effects."""

import copy
import itertools
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from fractions import Fraction
from pathlib import Path


class RaterStudyTests(unittest.TestCase):
    def test_original_fixture_preserved_and_manual_kappa_matches(self):
        from cx_eval_lab.rater_study import run_study
        report = run_study()
        root = Path(__file__).resolve().parents[1]
        fixture = json.loads((root / 'evals/cx-support/examples/human-annotations-v1.json').read_text())
        self.assertEqual(fixture, report['inputs']['source_fixture'])
        pair = report['pair_metrics']['R1:R2']
        self.assertEqual(8, pair['full']['n'])
        self.assertEqual(.75, pair['full']['observed_agreement'])
        self.assertEqual('23/64', pair['full']['expected_agreement_exact'])
        self.assertEqual('25/41', pair['full']['kappa_exact'])
        self.assertEqual(6, pair['binary_decidable']['n'])
        self.assertEqual(4, len(report['adjudication_records']))
        self.assertEqual(fixture['adjudications'], [r['original'] for r in report['adjudication_records']])
        self.assertFalse(report['deployment_authorized'])

    def test_unknown_category_is_not_missing_or_binary_fail(self):
        from cx_eval_lab.rater_study import pair_metrics
        rows = [{'item_id': 'a', 'left': 'unknown', 'right': 'unknown'},
                {'item_id': 'b', 'left': None, 'right': 'pass'},
                {'item_id': 'c', 'left': 'fail', 'right': 'pass'}]
        result = pair_metrics(rows)
        self.assertEqual(2, result['full']['n'])
        self.assertEqual(.5, result['full']['observed_agreement'])
        self.assertEqual(1, result['full']['confusion']['unknown']['unknown'])
        self.assertEqual(['b'], result['missing_item_ids'])
        self.assertEqual(1, result['binary_decidable']['n'])
        self.assertEqual(1 / 3, result['binary_decidable']['item_coverage'])

    def test_bootstrap_mass_and_undefined_kappa_are_not_silently_dropped(self):
        from cx_eval_lab.rater_study import run_study
        bootstrap = run_study()['registered_pair_bootstrap']
        self.assertEqual(495, bootstrap['count_vector_count'])
        self.assertEqual(8 ** 8, bootstrap['ordered_resample_count'])
        self.assertEqual(8 ** 8, sum(r['multiplicity'] for r in bootstrap['count_vectors']))
        self.assertEqual(Fraction(3 ** 8 + 2 ** 8 + 1, 8 ** 8), Fraction(bootstrap['undefined_probability_exact']))
        self.assertEqual(Fraction(1), sum(Fraction(r['probability_exact']) for r in bootstrap['distribution']))
        self.assertEqual('conditional_on_defined_kappa', bootstrap['percentiles']['conditioning'])
        self.assertFalse(bootstrap['percentiles']['coverage_qualified'])

    def test_small_ordered_resampling_matches_compressed_distribution(self):
        from cx_eval_lab.rater_study import bootstrap_pair
        rows = [{'item_id': 'a', 'left': 'pass', 'right': 'pass'},
                {'item_id': 'b', 'left': 'fail', 'right': 'pass'},
                {'item_id': 'c', 'left': 'fail', 'right': 'fail'}]
        expected = Counter()
        for sample in itertools.product(rows, repeat=3):
            left, right = Counter(r['left'] for r in sample), Counter(r['right'] for r in sample)
            observed = Fraction(sum(r['left'] == r['right'] for r in sample), 3)
            chance = sum((Fraction(left[c] * right[c], 9) for c in ('pass', 'fail', 'unknown')), Fraction())
            kappa = None if chance == 1 else str((observed - chance) / (1 - chance))
            expected[kappa] += 1
        actual = {r['kappa_exact']: r['multiplicity'] for r in bootstrap_pair(rows)['distribution']}
        self.assertEqual(dict(expected), actual)

    def test_no_eligible_pairs_and_single_category_kappa_are_undefined(self):
        from cx_eval_lab.rater_study import bootstrap_pair, pair_metrics
        rows = [{'item_id': 'a', 'left': None, 'right': None}]
        result = pair_metrics(rows)
        self.assertIsNone(result['full']['kappa'])
        self.assertIsNone(result['full']['observed_agreement'])
        self.assertIsNone(bootstrap_pair(rows)['percentiles'])
        rows[0] = {'item_id': 'a', 'left': 'unknown', 'right': 'unknown'}
        result = bootstrap_pair(rows)
        self.assertEqual(1., result['undefined_probability'])
        self.assertIsNone(result['percentiles'])

    def test_assignment_changes_scores_without_changing_outputs(self):
        from cx_eval_lab.rater_study import run_study
        control = run_study()['assignment_control']
        self.assertEqual(.5, control['confounded']['candidate_minus_baseline'])
        self.assertEqual(0., control['crossed']['candidate_minus_baseline'])
        self.assertEqual({'strict': 0., 'lenient': 0.}, control['per_reviewer_paired_gaps'])
        self.assertEqual({'strict': .5, 'lenient': 1.}, control['matched_panel_pass_rates'])
        self.assertEqual(8, len(control['confounded']['observations']))
        self.assertEqual(16, len(control['crossed']['observations']))
        for case in control['potential_ratings']:
            self.assertEqual(case['outputs']['baseline'], case['outputs']['candidate'])

    def test_invalid_labels_ids_evidence_and_original_joins_rejected(self):
        from cx_eval_lab.rater_study import example_inputs, pair_metrics, run_study
        for rows in ([{'item_id': 'x', 'left': True, 'right': 'pass'}],
                     [{'item_id': 'x', 'left': 'PASS', 'right': 'pass'}],
                     [{'item_id': 'x', 'left': 'pass', 'right': 'pass'}] * 2):
            with self.assertRaises(ValueError):
                pair_metrics(rows)
        for mode in ('evidence-hash', 'rubric', 'source-hash', 'assignment-output'):
            inputs = example_inputs()
            if mode == 'evidence-hash':
                inputs['item_evidence'][0]['evidence_hash'] = 'sha256:bad'
            elif mode == 'rubric':
                inputs['item_evidence'][0]['rubric_version'] = 'other'
            elif mode == 'source-hash':
                inputs['source_fixture']['annotations'][0]['label'] = 'fail'
            else:
                inputs['assignment_control'][0]['outputs']['candidate']['message'] = 'different'
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                run_study(inputs)

    def test_replay_rejects_coherent_computed_tampering(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.rater_study import replay_study, run_study
        report = run_study()
        self.assertEqual(report, replay_study(report))
        for field in ('pair_metrics', 'assignment_control', 'adjudication_records'):
            changed = copy.deepcopy(report)
            changed[field] = {}
            changed['report_hash'] = canonical_hash({k: v for k, v in changed.items() if k != 'report_hash'})
            with self.assertRaises(ValueError):
                replay_study(changed)

    def test_cli_output_is_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rater.json'
            cmd = [sys.executable, '-m', 'cx_eval_lab.rater_study', '--output', str(path)]
            first = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(0, first.returncode, first.stderr)
            before = path.read_bytes()
            self.assertNotEqual(0, subprocess.run(cmd, capture_output=True, check=False).returncode)
            self.assertEqual(before, path.read_bytes())

    def test_retained_artifact_exactly_reanalyzes(self):
        from cx_eval_lab.rater_study import replay_study, run_study
        path = Path(__file__).resolve().parents[1] / 'docs/assets/rater-study-v1.json'
        artifact = json.loads(path.read_text())
        self.assertEqual(run_study(), artifact)
        self.assertEqual(artifact, replay_study(artifact))

    def test_missing_rater_only_changes_affected_pairs_and_preserves_originals(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.rater_study import example_inputs, run_study
        inputs = example_inputs()
        for annotation in inputs['source_fixture']['annotations']:
            if annotation['case_id'] == 'H04' and annotation['reviewer'] == 'R1':
                annotation['label'] = None
        inputs['source']['content_hash'] = canonical_hash(inputs['source_fixture'])
        original = copy.deepcopy(inputs)
        report = run_study(inputs)
        self.assertEqual(original, inputs)
        self.assertEqual(original['source_fixture'], report['inputs']['source_fixture'])
        self.assertEqual(7, report['pair_metrics']['R1:R2']['full']['n'])
        self.assertEqual(5 / 7, report['pair_metrics']['R1:R2']['full']['observed_agreement'])
        self.assertEqual(7, report['pair_metrics']['R1:R3']['full']['n'])
        self.assertEqual(8, report['pair_metrics']['R2:R3']['full']['n'])
        self.assertEqual(['H04'], report['registered_pair_bootstrap']['excluded_missing_item_ids'])
        self.assertEqual(7 ** 7, report['registered_pair_bootstrap']['ordered_resample_count'])

    def test_empty_and_single_category_agreement_interval_is_not_kappa_interval(self):
        from cx_eval_lab.rater_study import pair_metrics
        result = pair_metrics([])
        self.assertIsNone(result['agreement_interval_iid_assumption'])
        self.assertIsNone(result['full']['item_coverage'])
        result = pair_metrics([{'item_id': 'one', 'left': 'pass', 'right': 'pass'}])
        self.assertIsNone(result['full']['kappa'])
        interval = result['agreement_interval_iid_assumption']
        self.assertTrue(interval['fixture_does_not_establish_sampling'])
        self.assertFalse(interval['coverage_qualified_for_fixture'])
        self.assertAlmostEqual(.025, interval['lower'])
        self.assertEqual(1., interval['upper'])

    def test_source_annotation_join_and_registered_pair_fail_closed(self):
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.rater_study import example_inputs, run_study
        for mode in ('duplicate-annotation', 'missing-slot', 'unknown-case', 'unknown-reviewer',
                     'unexpected-label', 'duplicate-item', 'duplicate-adjudication', 'missing-evidence',
                     'same-pair', 'unknown-pair', 'nan-input', 'different-potential-rating'):
            inputs = example_inputs()
            source = inputs['source_fixture']
            if mode == 'duplicate-annotation':
                source['annotations'][0] = dict(source['annotations'][1])
            elif mode == 'missing-slot':
                source['annotations'].pop()
            elif mode == 'unknown-case':
                source['annotations'][0]['case_id'] = 'foreign'
            elif mode == 'unknown-reviewer':
                source['annotations'][0]['reviewer'] = 'foreign'
            elif mode == 'unexpected-label':
                source['annotations'][0]['label'] = False
            elif mode == 'duplicate-item':
                source['items'][0] = dict(source['items'][1])
            elif mode == 'duplicate-adjudication':
                source['adjudications'][0] = dict(source['adjudications'][1])
            elif mode == 'missing-evidence':
                inputs['item_evidence'].pop()
            elif mode in ('same-pair', 'unknown-pair'):
                inputs['bootstrap_pair'] = ['R1', 'R1' if mode == 'same-pair' else 'unknown']
            elif mode == 'nan-input':
                source['items'][0]['situation'] = float('nan')
            else:
                inputs['assignment_control'][0]['ratings']['strict']['candidate'] = 'fail'
            if mode != 'nan-input':
                inputs['source']['content_hash'] = canonical_hash(source)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                run_study(inputs)
