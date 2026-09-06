"""Repeated-look decisions must account for paths, not sum marginal errors."""

import itertools
import math
import unittest


class SequentialStudyTests(unittest.TestCase):
    def test_log_evidence_handles_extreme_valid_probabilities_without_ratio_underflow(self):
        from cx_eval_lab.sequential_study import log_evidence
        self.assertTrue(math.isfinite(log_evidence(1, 1, margin=0.9, alternative=5e-324)))
    def test_log_likelihood_ratio_and_null_expectation(self):
        from cx_eval_lab.sequential_study import log_evidence
        p0, p1, n = 0.3, 0.1, 5
        expected = sum(math.comb(n, k) * p0**k * (1-p0)**(n-k)
                       * math.exp(log_evidence(k, n, margin=p0, alternative=p1))
                       for k in range(n+1))
        self.assertAlmostEqual(1.0, expected)
        self.assertAlmostEqual(3 * math.log(0.1/0.3) + 7 * math.log(0.9/0.7),
                               log_evidence(3, 10, margin=p0, alternative=p1))

    def test_dynamic_enumeration_matches_all_binary_paths(self):
        from cx_eval_lab.sequential_study import enumerate_stopping, should_stop
        for method in ('fixed_final', 'repeated_fixed', 'bonferroni', 'likelihood_ratio'):
            looks = (2, 4, 6)
            report = enumerate_stopping(method=method, looks=looks, true_loss=0.4,
                                        margin=0.6, alternative=0.2, alpha=0.2)
            total = 0.0
            for path in itertools.product((0, 1), repeat=6):
                if any(should_stop(method, sum(path[:n]), n, looks=looks,
                                   margin=0.6, alternative=0.2, alpha=0.2) for n in looks):
                    k = sum(path)
                    total += 0.4**k * 0.6**(6-k)
            self.assertAlmostEqual(total, report['promotion_probability'])
            self.assertAlmostEqual(1.0, report['promotion_probability'] + report['no_promotion_probability'])

    def test_repeated_fixed_tests_inflate_error_but_registered_rules_control_it(self):
        from cx_eval_lab.sequential_study import enumerate_stopping
        results = {method: enumerate_stopping(method=method) for method in
                   ('fixed_final', 'repeated_fixed', 'bonferroni', 'likelihood_ratio')}
        self.assertGreater(results['repeated_fixed']['promotion_probability'], 0.05)
        for method in ('fixed_final', 'bonferroni', 'likelihood_ratio'):
            self.assertLessEqual(results[method]['promotion_probability'], 0.05 + 1e-12)

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


if __name__ == '__main__':
    unittest.main()
