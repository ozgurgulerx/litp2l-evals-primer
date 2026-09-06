"""Repeated-look decisions must account for paths, not sum marginal errors."""

import itertools
import math
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


class SequentialStudyTests(unittest.TestCase):
    def test_log_evidence_handles_extreme_probabilities_and_avoids_reciprocal_overflow(self):
        from cx_eval_lab.sequential_study import log_evidence, should_stop
        self.assertTrue(math.isfinite(log_evidence(1, 1, margin=0.9, alternative=5e-324)))
        self.assertTrue(should_stop('likelihood_ratio', 0, 500, looks=(500,),
                                   margin=0.9, alternative=0.01, alpha=5e-324))
    def test_log_likelihood_ratio_and_null_expectation(self):
        from cx_eval_lab.sequential_study import log_evidence
        p0, p1, n = 0.3, 0.1, 5
        expected = sum(math.comb(n, k) * p0**k * (1-p0)**(n-k)
                       * math.exp(log_evidence(k, n, margin=p0, alternative=p1))
                       for k in range(n+1))
        self.assertAlmostEqual(1.0, expected)
        expectation_above_boundary = sum(math.comb(n, k) * 0.4**k * 0.6**(n-k)
            * math.exp(log_evidence(k, n, margin=p0, alternative=p1)) for k in range(n+1))
        self.assertLess(expectation_above_boundary, 1.0)
        self.assertAlmostEqual(3 * math.log(0.1/0.3) + 7 * math.log(0.9/0.7),
                               log_evidence(3, 10, margin=p0, alternative=p1))

    def test_dynamic_enumeration_matches_all_binary_paths(self):
        from cx_eval_lab.sequential_study import enumerate_stopping, should_stop
        for method in ('fixed_final', 'repeated_fixed', 'bonferroni', 'likelihood_ratio'):
            looks = (2, 4, 6)
            report = enumerate_stopping(method=method, looks=looks, true_loss=0.4,
                                        margin=0.6, alternative=0.2, alpha=0.2)
            total = 0.0
            first = {n: 0.0 for n in looks}
            for path in itertools.product((0, 1), repeat=6):
                stopping = next((n for n in looks if should_stop(method, sum(path[:n]), n,
                                looks=looks, margin=0.6, alternative=0.2, alpha=0.2)), None)
                if stopping is not None:
                    k = sum(path)
                    mass = 0.4**k * 0.6**(6-k)
                    total += mass
                    first[stopping] += mass
            self.assertAlmostEqual(total, report['promotion_probability'])
            self.assertAlmostEqual(1.0, report['promotion_probability'] + report['no_promotion_probability'])
            for row in report['first_crossings']:
                self.assertAlmostEqual(first[row['n']], row['first_promotion_probability'])
            self.assertAlmostEqual(sum(n * mass for n, mass in first.items()) + 6 * (1-total),
                                   report['expected_observations_until_stop_or_horizon'])

    def test_repeated_fixed_tests_inflate_error_but_registered_rules_control_it(self):
        from cx_eval_lab.sequential_study import enumerate_stopping
        results = {method: enumerate_stopping(method=method) for method in
                   ('fixed_final', 'repeated_fixed', 'bonferroni', 'likelihood_ratio')}
        self.assertGreater(results['repeated_fixed']['promotion_probability'], 0.05)
        for method in ('fixed_final', 'bonferroni', 'likelihood_ratio'):
            self.assertLessEqual(results[method]['promotion_probability'], 0.05 + 1e-12)
            self.assertTrue(results[method]['null_true'])
            self.assertEqual(results[method]['promotion_probability'], results[method]['false_promotion_probability'])

    def test_label_bias_and_perfect_dependence_break_truth_claims(self):
        from cx_eval_lab.sequential_study import enumerate_stopping, dependent_counterexample
        biased = enumerate_stopping(method='likelihood_ratio', true_loss=0.1,
                                     hidden_loss_probability=1.0)
        self.assertAlmostEqual(1.0, biased['false_promotion_probability'])
        dependent = dependent_counterexample()
        self.assertGreater(dependent['false_promotion_probability'], 0.9)

    def test_reject_invalid_design_instead_of_silently_sorting_looks(self):
        from cx_eval_lab.sequential_study import enumerate_stopping
        for kwargs in ({'looks': (20, 10)}, {'looks': (10, 10)}, {'looks': ()},
                       {'looks': (True,)}, {'looks': (501,)}, {'alternative': 0.04},
                       {'alpha': float('nan')}, {'margin': 0}, {'method': 'unregistered'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                enumerate_stopping(**kwargs)

    def test_published_results_reproduce_with_float_tolerance(self):
        from cx_eval_lab.sequential_study import enumerate_stopping
        report = json.loads(Path('docs/assets/sequential-study-v1.json').read_text())
        for recorded in (*report['studies'], report['biased_labels']):
            actual = enumerate_stopping(**{key: recorded[key] for key in ('method', 'looks',
                'true_loss', 'margin', 'alternative', 'alpha', 'hidden_loss_probability')})
            for key in ('promotion_probability', 'no_promotion_probability',
                        'false_promotion_probability', 'expected_observations_until_stop_or_horizon'):
                self.assertAlmostEqual(recorded[key], actual[key], places=12)
            self.assertEqual([row['largest_promoting_loss_count'] for row in recorded['first_crossings']],
                             [row['largest_promoting_loss_count'] for row in actual['first_crossings']])

    def test_cli_retains_report_and_rejects_overwrite(self):
        from cx_eval_lab.sequential_study import main
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            with patch.object(sys, 'argv', ['study', '--output', str(path)]):
                main()
                self.assertEqual(12, len(json.loads(path.read_text())['studies']))
                with patch('sys.stderr'), self.assertRaises(SystemExit) as raised:
                    main()
                self.assertEqual(2, raised.exception.code)


if __name__ == '__main__':
    unittest.main()
