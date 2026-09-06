"""Qualify the measuring method against a known finite population model."""

import unittest
import math
import json
import subprocess
import sys
import tempfile
from pathlib import Path


class StatisticalStudyTests(unittest.TestCase):
    def test_zero_losses_do_not_prove_zero_population_risk(self):
        from cx_eval_lab.statistical_study import exact_loss_interval
        lower, upper = exact_loss_interval(0, 30, confidence=0.95)
        self.assertEqual(0, lower)
        self.assertAlmostEqual(1 - 0.025 ** (1 / 30), upper)
        self.assertGreater(upper, 0.03)

    def test_known_sparse_population_exposes_false_promotions(self):
        from cx_eval_lab.statistical_study import sparse_population_study
        study = sparse_population_study(n=30, loss_probability=0.04)
        self.assertAlmostEqual(1, study['enumerated_probability_mass'])
        normal = study['methods']['clustered_normal_interval']
        self.assertAlmostEqual(0.96 ** 30, normal['false_promotion_probability'])
        self.assertLess(normal['coverage_probability'], 0.90)
        exact = study['methods']['exact_binomial_special_case']
        self.assertGreaterEqual(exact['coverage_probability'], 0.95)
        self.assertLessEqual(exact['false_promotion_probability'], 0.025)

    def test_label_error_is_not_repaired_by_an_exact_interval(self):
        from cx_eval_lab.statistical_study import sparse_population_study
        study = sparse_population_study(n=200, loss_probability=0.10,
                                        hidden_loss_probability=1.0)
        self.assertEqual(-0.10, study['true_difference'])
        self.assertEqual(0, study['observed_difference'])
        self.assertEqual(0, study['methods']['exact_binomial_special_case']['coverage_probability'])
        self.assertEqual(1, study['methods']['exact_binomial_special_case']['false_promotion_probability'])

    def test_exact_interval_endpoints_symmetry_and_invalid_inputs(self):
        from cx_eval_lab.statistical_study import exact_loss_interval
        a, b = exact_loss_interval(3, 10)
        c, d = exact_loss_interval(7, 10)
        self.assertAlmostEqual(a, 1 - d)
        self.assertAlmostEqual(b, 1 - c)
        self.assertEqual(1, exact_loss_interval(10, 10)[1])
        for k, n in ((-1, 30), (31, 30), (0, 0), (True, 30), (0, 3.5)):
            with self.subTest(k=k, n=n), self.assertRaises(ValueError):
                exact_loss_interval(k, n)

    def test_unequal_clusters_change_the_estimand(self):
        from cx_eval_lab.statistical_study import unequal_cluster_example
        result = unequal_cluster_example()
        self.assertAlmostEqual(0, result['equal_customer_difference'])
        self.assertAlmostEqual(-0.8, result['pooled_task_difference'])
        self.assertEqual(30, result['independent_clusters'])

    def test_cli_persists_full_inspectable_study_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'study.json'
            command = [sys.executable, '-m', 'cx_eval_lab.statistical_study',
                       '--output', str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(path.exists(), 'the study CLI must preserve its evidence')
            report = json.loads(path.read_text())
            self.assertEqual('lab_only', report['authority'])
            self.assertTrue(any(s['n'] == 200 and s['loss_probability'] == 0.01
                                for s in report['studies']))
            self.assertTrue(all('count_outcomes' in s for s in report['studies']))
            repeat = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, repeat.returncode)

    def test_cached_counts_still_reject_boolean_inputs(self):
        from cx_eval_lab.statistical_study import exact_loss_interval
        exact_loss_interval(1, 30)
        with self.assertRaises(ValueError):
            exact_loss_interval(True, 30)

    def test_binomial_endpoints_solve_registered_tail_equations(self):
        from cx_eval_lab.statistical_study import exact_loss_interval
        lower, upper = exact_loss_interval(3, 10)
        upper_tail = sum(math.comb(10, j) * upper ** j * (1 - upper) ** (10 - j)
                         for j in range(4))
        lower_tail = sum(math.comb(10, j) * lower ** j * (1 - lower) ** (10 - j)
                         for j in range(3))
        self.assertAlmostEqual(0.025, upper_tail)
        self.assertAlmostEqual(0.975, lower_tail)

    def test_invalid_probability_or_confidence_is_rejected(self):
        from cx_eval_lab.statistical_study import exact_loss_interval, sparse_population_study
        for probability in (-0.1, 1.1, float('nan'), True):
            with self.subTest(probability=probability), self.assertRaises(ValueError):
                sparse_population_study(loss_probability=probability)
        for confidence in (0, 1, float('nan')):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                exact_loss_interval(3, 30, confidence)

    def test_published_artifact_matches_executed_generator(self):
        from cx_eval_lab.statistical_study import study_report
        path = Path(__file__).resolve().parents[1] / 'docs/assets/statistical-method-study-v1.json'
        expected = json.loads(path.read_text())
        actual = json.loads(json.dumps(study_report()))
        def compare(left, right):
            if isinstance(left, dict):
                self.assertEqual(left.keys(), right.keys())
                for key in left:
                    compare(left[key], right[key])
            elif isinstance(left, list):
                self.assertEqual(len(left), len(right))
                for a, b in zip(left, right):
                    compare(a, b)
            elif isinstance(left, float):
                # libm rounding can differ between macOS and Linux CI.
                self.assertAlmostEqual(left, right, places=12)
            else:
                self.assertEqual(left, right)
        compare(expected, actual)


if __name__ == '__main__':
    unittest.main()
