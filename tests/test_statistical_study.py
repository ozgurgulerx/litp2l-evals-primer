"""Qualify the measuring method against a known finite population model."""

import math
import unittest


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
        study = sparse_population_study(n=100, loss_probability=0.10,
                                        hidden_loss_probability=1.0)
        self.assertEqual(-0.10, study['true_difference'])
        self.assertEqual(0, study['observed_difference'])
        self.assertEqual(0, study['methods']['exact_binomial_special_case']['coverage_probability'])

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


if __name__ == '__main__':
    unittest.main()
