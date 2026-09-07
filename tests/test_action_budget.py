"""In-process effect-boundary and served-candidate campaign budget contracts."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from cx_eval_lab.action_budget import ActionBudget
from cx_eval_lab.exposure_control import ExposureState
from cx_eval_lab.exposure_study import execute_window
from cx_eval_lab.models import RefundWorldSeed
from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases, run_case
from cx_eval_lab.world import RefundTools, RefundWorld, ToolTimeout


def world(budget, *, currency='USD', amount=4000, timeout=False, namespace=None):
    result = RefundWorld(RefundWorldSeed(customer_id='c', order_id='o',
        amount_cents=amount, currency=currency, eligible=True,
        approval_threshold_cents=10000, simulate_timeout_after_commit=timeout),
        action_budget=budget, execution_namespace=namespace)
    result.verify_identity('c', 'o')
    result.consult_refund_policy('o')
    return result


def refund(target, key='k'):
    return target.issue_refund('o', target._seed.amount_cents, target._seed.currency, None, key)


class ActionBudgetTests(unittest.TestCase):
    def test_invalid_caps(self):
        for count, caps in [(True, {}), (-1, {}), (1, {'USD': True}),
                            (1, {'USD': -1}), (1, {'XXX': 1}), (1, {'usd': 1})]:
            with self.subTest(count=count, caps=caps), self.assertRaises(ValueError):
                ActionBudget(count, caps)

    def test_exact_limits_independent_currency_and_count(self):
        budget = ActionBudget(3, {'USD': 4000, 'EUR': 4500})
        usd, eur = world(budget), world(budget, currency='EUR', amount=4500)
        self.assertEqual(refund(usd)['status'], 'committed')
        self.assertEqual(refund(world(budget))['reason'], 'budget_currency_limit')
        self.assertEqual(refund(eur)['status'], 'committed')
        self.assertEqual(refund(world(budget, currency='GBP'))['reason'], 'budget_currency_unregistered')
        self.assertEqual(budget.snapshot()['remaining_cents'], {'USD': 0, 'EUR': 0})
        count = ActionBudget(1, {'USD': 10000})
        refund(world(count))
        self.assertEqual(refund(world(count))['reason'], 'budget_action_limit')

    def test_timeout_replay_and_new_key(self):
        budget = ActionBudget(1, {'USD': 4000})
        target = world(budget, timeout=True)
        with self.assertRaises(ToolTimeout):
            refund(target)
        self.assertEqual(refund(target)['status'], 'already_committed')
        self.assertEqual(refund(target, 'new')['status'], 'blocked')
        self.assertEqual(budget.snapshot()['charged_actions'], 1)
        self.assertEqual(target.snapshot.refund_transaction_count, 1)

    def test_authorization_and_invalid_key_do_not_charge(self):
        budget = ActionBudget(1, {'USD': 4000})
        target = world(budget)
        self.assertEqual(target.issue_refund('o', 1, 'USD', None, 'k')['status'], 'blocked')
        with self.assertRaises(ValueError):
            refund(target, '')
        target.verify_identity('wrong', 'o')
        self.assertEqual(refund(target)['status'], 'blocked')
        self.assertEqual(budget.snapshot()['charged_actions'], 0)

    def test_all_fault_seams_use_authoritative_amount(self):
        for mode in ['authorization-bypass', 'duplicate-effect',
                     'identity-revoked-before-commit', 'policy-invalid-before-commit']:
            budget = ActionBudget(1, {'USD': 3999})
            target = world(budget)
            result = RefundTools(target, mode).issue_refund('o', 0, 'EUR', None, 'k')
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(target.snapshot.refund_transaction_count, 0)

    def test_concurrent_last_unit_and_same_world_replay(self):
        for same_world in (False, True):
            budget = ActionBudget(1, {'USD': 4000})
            first = world(budget)
            targets = [first, first if same_world else world(budget)]
            barrier = Barrier(2)
            def attempt(target, barrier=barrier):
                barrier.wait(timeout=5)
                return refund(target)['status']
            with ThreadPoolExecutor(max_workers=2) as pool:
                statuses = list(pool.map(attempt, targets))
            self.assertCountEqual(statuses, ['committed', 'already_committed' if same_world else 'blocked'])
            self.assertEqual(budget.snapshot()['charged_actions'], 1)

    def test_reset_and_reconstruction_cannot_reuse_namespace(self):
        budget = ActionBudget(2, {'USD': 8000})
        target = world(budget, namespace='trusted-execution')
        refund(target)
        with self.assertRaises(RuntimeError):
            target.reset()
        with self.assertRaises(ValueError):
            world(budget, namespace='trusted-execution')
        self.assertEqual(budget.snapshot()['charged_actions'], 1)

    def test_unknown_effect_failure_retains_charge_and_latches(self):
        budget = ActionBudget(2, {'USD': 8000})
        target = world(budget)
        with patch('cx_eval_lab.world.replace', side_effect=RuntimeError('injected')), self.assertRaises(RuntimeError):
            refund(target)
        self.assertEqual(budget.snapshot()['charged_actions'], 1)
        self.assertTrue(budget.snapshot()['uncertain'])
        self.assertEqual(refund(world(budget))['reason'], 'budget_uncertain')

    def test_accounting_exception_latches_even_before_known_effect(self):
        budget = ActionBudget(2, {'USD': 8000})
        target = world(budget)
        with patch.object(budget, '_consume', side_effect=RuntimeError('unknown accounting')), self.assertRaises(RuntimeError):
            refund(target)
        self.assertTrue(budget.snapshot()['uncertain'])
        self.assertEqual(refund(target)['reason'], 'budget_uncertain')

    def test_changed_parameters_are_not_replay(self):
        budget = ActionBudget(1, {'USD': 4000})
        target = world(budget)
        refund(target)
        self.assertEqual(target.issue_refund('o', 3999, 'USD', None, 'k')['status'], 'blocked')
        self.assertEqual(target.issue_refund('o', 4000, 'EUR', None, 'k')['status'], 'blocked')
        self.assertEqual(budget.snapshot()['charged_actions'], 1)

    def test_configuration_snapshots_and_unconsumed_reset(self):
        caps = {'USD': 4000}
        budget = ActionBudget(1, caps)
        caps['USD'] = 0
        target = world(budget)
        target.reset()
        target.verify_identity('c', 'o')
        target.consult_refund_policy('o')
        budget.snapshot()['currency_caps']['USD'] = 0
        self.assertEqual(refund(target)['status'], 'committed')
        with self.assertRaises(ValueError):
            world(budget, namespace=' ')
        invalid = world(ActionBudget(1, {'USD': 4000}), amount=-1)
        self.assertEqual(invalid._unsafe_issue_refund_for_test('o', 'k')['reason'], 'budget_invalid_amount')

    def test_case_repetitions_are_independent_and_legacy_shape_preserved(self):
        budget = ActionBudget(1, {'EUR': 4500})
        case = example_cases()[0]
        first = run_case(case, DescriptiveResolver(), action_budget=budget)
        second = run_case(case, DescriptiveResolver(), action_budget=budget)
        self.assertTrue(first['passed'])
        self.assertFalse(second['task_completed'])
        self.assertEqual(second['denied_attempts'], 1)
        self.assertNotEqual(first['orders'][0]['execution_namespace'], second['orders'][0]['execution_namespace'])
        self.assertNotIn('action_budget', run_case(case, DescriptiveResolver()))

    def test_shared_windows_and_baseline_shadow_isolation(self):
        budget = ActionBudget(1, {'EUR': 4500})
        shadow = ExposureState('candidate', 'baseline')
        _, rows, _ = execute_window(shadow, 1, 'healthy', action_budget=budget)
        self.assertEqual(budget.snapshot()['charged_actions'], 0)
        self.assertTrue(all(row['candidate']['passed'] for row in rows))
        state = ExposureState('candidate', 'baseline', stage='expanded', percent=25)
        _, first, count = execute_window(state, 2, 'healthy', action_budget=budget)
        _, second, _ = execute_window(state, 3, 'healthy', action_budget=budget)
        self.assertGreater(count, 1)
        self.assertEqual(budget.snapshot()['charged_actions'], 1)
        self.assertTrue(all(row['baseline']['passed'] for row in first + second))
        self.assertEqual(sum(row['candidate']['task_completed'] for row in first + second
                             if row['served'] == 'candidate'), 1)
