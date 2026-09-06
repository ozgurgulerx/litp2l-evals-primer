"""Execute competing-order tasks without evaluator labels in model inputs."""

from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests import test_openai_runtime as runtime_tests


class OrderResolutionTests(unittest.TestCase):
    def test_unresolved_requests_require_valid_text_and_customer_context(self):
        from cx_eval_lab.order_resolution import UnresolvedRequest
        for utterance, customer in (('', 'customer-1'), ('refund', ''), (None, 'customer-1')):
            with self.subTest(utterance=utterance), self.assertRaises(ValueError):
                UnresolvedRequest(utterance, customer)
    def test_input_omits_target_and_candidate_order_permutation_preserves_answer(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, DescriptiveResolver
        cases = example_cases()
        for case in cases:
            request = asdict(case.request)
            self.assertEqual({'utterance', 'customer_id'}, set(request))
            if case.expected_order_id:
                self.assertNotIn(case.expected_order_id, json.dumps(request))
            for reverse in (False, True):
                result = run_case(case, DescriptiveResolver(), reverse=reverse)
                self.assertTrue(result['passed'], result)

    def test_first_record_mutant_really_commits_wrong_authorized_order(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, FirstRecordResolver
        case = example_cases()[0]
        results = [run_case(case, FirstRecordResolver(), reverse=reverse) for reverse in (False, True)]
        self.assertEqual([False, True], [result['passed'] for result in results])
        self.assertEqual(1, sum(row['state']['refund_transaction_count']
                                for row in results[0]['orders']))
        self.assertEqual(1, results[0]['wrong_order_commits'])

    def test_customer_scope_is_enforced_for_read_and_write_tools(self):
        from cx_eval_lab.order_resolution import example_cases, MultiOrderWorld
        world = MultiOrderWorld(example_cases()[0])
        tools = world.tools()
        self.assertFalse(tools.verify_identity('customer-other', 'order-c'))
        with self.assertRaises(PermissionError):
            tools.list_orders('customer-other')
        with self.assertRaises(PermissionError):
            tools.get_order('order-c')
        with self.assertRaises(PermissionError):
            tools.issue_refund('order-c', 4000, 'USD', None, 'attempt')
        self.assertEqual(0, world.total_commits)

    def test_unnecessary_clarification_and_unresolved_requests_do_not_pass_as_success(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, DescriptiveResolver
        class AlwaysAsk(DescriptiveResolver):
            def run(self, request, tools):
                tools.ask_customer('Which order?')
                return super().run(request, tools)
        result = run_case(example_cases()[0], AlwaysAsk())
        self.assertFalse(result['passed'])
        self.assertEqual(1, result['unnecessary_clarifications'])
        unresolved = run_case(example_cases()[-1], DescriptiveResolver())
        self.assertTrue(unresolved['passed'])
        self.assertFalse(unresolved['task_completed'])
        self.assertEqual(0, sum(row['state']['refund_transaction_count'] for row in unresolved['orders']))

    def test_unresolved_runtime_uses_real_tools_without_target_field(self):
        from cx_eval_lab.order_resolution import example_cases, run_case
        from cx_eval_lab.openai_runtime import OpenAIAgentsRuntime
        from cx_eval_lab.models import ResolutionResponse
        case = example_cases()[0]
        fake = runtime_tests.OpenAIAgentsRuntimeTests._fake_agents_module()
        captured = {}
        def run_sync(agent, payload, **kwargs):
            captured.update(json.loads(payload))
            tool = {item.__name__: item for item in agent.tools}
            orders = json.loads(tool['list_orders'](case.request.customer_id))
            selected = next(order for order in orders if order['description'] in captured['utterance'])
            identity = selected['order_id']
            tool['verify_identity'](case.request.customer_id, identity)
            order = json.loads(tool['get_order'](identity))
            tool['consult_refund_policy'](identity)
            tool['issue_refund'](identity, order['amount_cents'], order['currency'], None, 'chosen-order')
            return SimpleNamespace(final_output=ResolutionResponse(message='Refund confirmed.',
                                   claimed_outcome='refunded'), raw_responses=())
        fake.Runner.run_sync = run_sync
        with patch.dict('sys.modules', {'agents': fake}):
            result = run_case(case, OpenAIAgentsRuntime(model='test-only'))
        self.assertEqual({'utterance', 'customer_id'}, set(captured))
        self.assertTrue(result['passed'], result)

    def test_rejected_amount_attempt_is_not_erased_by_later_success(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, DescriptiveResolver
        class BadAmount(DescriptiveResolver):
            def run(self, request, tools):
                tools.verify_identity(request.customer_id, 'order-b')
                tools.consult_refund_policy('order-b')
                tools.issue_refund('order-b', 1, 'EUR', None, 'bad-amount')
                return super().run(request, tools)
        result = run_case(example_cases()[0], BadAmount())
        self.assertFalse(result['passed'])
        self.assertEqual(1, result['denied_attempts'])

    def test_mutating_tool_response_cannot_rewrite_retained_event(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, DescriptiveResolver
        class MutateResponse(DescriptiveResolver):
            def run(self, request, tools):
                orders = tools.list_orders(request.customer_id)
                orders.clear()
                return super().run(request, tools)
        result = run_case(example_cases()[0], MutateResponse())
        self.assertEqual(2, len(result['tool_events'][0]['result']))

    def test_clarification_after_refund_cannot_authorize_a_guessed_action(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, FirstRecordResolver
        class AskTooLate(FirstRecordResolver):
            def run(self, request, tools):
                output = super().run(request, tools)
                tools.ask_customer('Which purchase?')
                return output
        result = run_case(example_cases()[1], AskTooLate())
        self.assertEqual(0, result['wrong_order_commits'])
        self.assertFalse(result['passed'])
        self.assertEqual(1, result['premature_action_attempts'])

    def test_denied_approval_stays_visible_after_success(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, DescriptiveResolver
        class BadApproval(DescriptiveResolver):
            def run(self, request, tools):
                tools.verify_identity(request.customer_id, 'order-b')
                tools.request_refund_approval('order-b', 1, 'EUR')
                return super().run(request, tools)
        result = run_case(example_cases()[0], BadApproval())
        self.assertFalse(result['passed'])
        self.assertEqual(1, result['denied_attempts'])

    def test_invalid_order_and_case_configuration_fail_closed(self):
        from cx_eval_lab.order_resolution import OrderRecord, example_cases
        for values in (('', 'c', 'item'), ('o', 'c', 'item', True),
                       ('o', 'c', 'item', 10, 'invalid')):
            with self.assertRaises(ValueError):
                OrderRecord(*values)
        case = example_cases()[0]
        for changes in ({'orders': (case.orders[0], case.orders[0])},
                        {'expected_order_id': 'order-c'}, {'required_clarifications': 2}):
            with self.assertRaises(ValueError):
                replace(case, **changes)

    def test_existing_approval_and_status_guards_are_preserved(self):
        from cx_eval_lab.order_resolution import example_cases, MultiOrderWorld
        world = MultiOrderWorld(example_cases()[0])
        tools = world.tools()
        with self.assertRaises(PermissionError):
            tools.consult_refund_policy('order-b')
        self.assertTrue(tools.verify_identity('customer-1', 'order-b'))
        tools.consult_refund_policy('order-b')
        approval = tools.request_refund_approval('order-b', 4500, 'EUR')
        self.assertTrue(approval['approved'])
        self.assertFalse(tools.inspect_order_status('order-b')['refunded'])
        with self.assertRaises(ValueError):
            tools.ask_customer('')
        self.assertIsNone(tools.ask_customer('No response scripted?'))
        self.assertIsNone(tools.ask_customer('Again?'))

    def test_execution_errors_never_pass(self):
        from cx_eval_lab.order_resolution import example_cases, run_case
        class Broken:
            name = 'broken'
            def run(self, request, tools):
                raise RuntimeError('must not retain raw failure text')
        result = run_case(example_cases()[0], Broken())
        self.assertFalse(result['passed'])
        self.assertEqual('RuntimeError', result['execution_error'])
        self.assertNotIn('must not retain', json.dumps(result))

    def test_cli_preserves_full_study_and_refuses_overwrite(self):
        from cx_eval_lab.order_resolution import main
        from cx_eval_lab.evidence import canonical_hash
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'study.json'
            with patch.object(sys, 'argv', ['study', '--output', str(output)]):
                main()
                with self.assertRaises(FileExistsError):
                    main()
            report = json.loads(output.read_text())
            self.assertEqual(16, len(report['trials']))
            self.assertEqual([canonical_hash(trial) for trial in report['trials']], report['trial_hashes'])
            self.assertFalse(report['deployment_authorized'])

    def test_published_results_reproduce_except_wall_clock_measurement(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, DescriptiveResolver, FirstRecordResolver
        from cx_eval_lab.evidence import canonical_hash
        report = json.loads(Path('docs/assets/order-resolution-v1.json').read_text())
        cases = {case.case_id: case for case in example_cases()}
        agents = {agent.name: agent for agent in (DescriptiveResolver(), FirstRecordResolver())}
        for trial, digest in zip(report['trials'], report['trial_hashes'], strict=True):
            self.assertEqual(canonical_hash(trial), digest)
            actual = run_case(cases[trial['case']['case_id']], agents[trial['agent']], reverse=trial['reverse'])
            actual = json.loads(json.dumps(actual))
            self.assertEqual({key: value for key, value in actual.items() if key != 'elapsed_ms'},
                             {key: value for key, value in trial.items() if key != 'elapsed_ms'})


if __name__ == '__main__':
    unittest.main()
