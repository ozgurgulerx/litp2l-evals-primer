"""Execute competing-order tasks without evaluator labels in model inputs."""

from dataclasses import asdict
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_openai_runtime import OpenAIAgentsRuntimeTests


class OrderResolutionTests(unittest.TestCase):
    def test_input_omits_target_and_candidate_order_permutation_preserves_answer(self):
        from cx_eval_lab.order_resolution import example_cases, run_case, DescriptiveResolver
        cases = example_cases()
        for case in cases:
            request = asdict(case.request)
            self.assertEqual({'utterance', 'customer_id'}, set(request))
            self.assertNotIn(case.expected_order_id, json.dumps(request)) if case.expected_order_id else None
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
        from cx_eval_lab.order_resolution import example_cases, MultiOrderWorld
        from cx_eval_lab.openai_runtime import OpenAIAgentsRuntime
        from cx_eval_lab.models import ResolutionResponse
        case = example_cases()[0]
        world = MultiOrderWorld(case)
        fake = OpenAIAgentsRuntimeTests._fake_agents_module()
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
            OpenAIAgentsRuntime(model='test-only').run_unresolved(case.request, world.tools())
        self.assertEqual({'utterance', 'customer_id'}, set(captured))
        self.assertEqual(1, world.total_commits)


if __name__ == '__main__':
    unittest.main()
