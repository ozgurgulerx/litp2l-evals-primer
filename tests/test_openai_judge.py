"""Provider contract tests; no network or paid model evaluation."""

import copy
import json
import unittest
from dataclasses import replace
from types import SimpleNamespace

from cx_eval_lab.semantic import SemanticRequest


def response(**changes):
    return {**{
        'id': 'resp_fixture', 'model': 'pinned-fixture-model', 'status': 'completed',
        'error': None, 'incomplete_details': None,
        'usage': {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120},
        'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                    'content': [{'type': 'output_text', 'text': json.dumps({
                        'verdict': 'pass', 'explanation': 'Fixture judgment, not measured truth.'})}]}],
    }, **changes}


class FakeClient:
    base_url = 'https://api.openai.com/v1/'

    def __init__(self, payload=None, error=None):
        self.payload, self.error = payload or response(), error
        self.options, self.calls = [], []
        self.responses = SimpleNamespace(create=self.create)

    def with_options(self, **options):
        self.options.append(options)
        return self

    def create(self, **request):
        self.calls.append(request)
        if self.error:
            raise self.error
        return SimpleNamespace(model_dump=lambda **kwargs: copy.deepcopy(self.payload))


class OpenAIJudgeTests(unittest.TestCase):
    def judge(self, client=None, **changes):
        from cx_eval_lab.openai_judge import JudgeConfig, OpenAIResponsesJudge
        config = JudgeConfig(model='pinned-fixture-model', input_usd_per_million=2,
                             output_usd_per_million=8, price_version='fixture-not-a-market-price')
        return OpenAIResponsesJudge(replace(config, **changes), client or FakeClient())

    def test_request_is_bounded_stateless_and_structured(self):
        client = FakeClient()
        judge = self.judge(client)
        result = judge.evaluate(SemanticRequest('{"output":{"message":"hello"}}'))
        self.assertEqual('pass', result.verdict)
        self.assertEqual({'timeout': 30.0, 'max_retries': 0}, client.options[0])
        request = client.calls[0]
        self.assertFalse(request['store'])
        self.assertFalse(request['stream'])
        self.assertEqual([], request['tools'])
        self.assertEqual('disabled', request['truncation'])
        self.assertTrue(request['text']['format']['strict'])
        self.assertEqual(512, request['max_output_tokens'])
        self.assertEqual(120, result.runtime_evidence.total_tokens)
        self.assertAlmostEqual(0.00036, result.runtime_evidence.cost_usd)
        self.assertIn('undiscounted', result.runtime_evidence.cost_source)
        audit = json.loads(result.provider_audit_json)
        self.assertEqual('resp_fixture', audit['response']['id'])
        self.assertEqual(judge.configuration_hash, audit['configuration_hash'])

    def test_incomplete_refused_malformed_and_model_drift_abstain_with_usage(self):
        bad_text = ('{"verdict":"pass","explanation":"x","extra":true}',
                    '{"verdict":"fail","verdict":"pass","explanation":"x"}',
                    'not json', '{"verdict":true,"explanation":"x"}')
        payloads = [response(status='incomplete'), response(model='unregistered-model')]
        refusal = response()
        refusal['output'][0]['content'].append({'type': 'refusal', 'refusal': 'fixture refusal'})
        payloads.append(refusal)
        for text in bad_text:
            payload = response()
            payload['output'][0]['content'][0]['text'] = text
            payloads.append(payload)
        for payload in payloads:
            with self.subTest(payload=payload):
                result = self.judge(FakeClient(payload)).evaluate(SemanticRequest('{}'))
                self.assertEqual('abstain', result.verdict)
                self.assertEqual(120, result.runtime_evidence.total_tokens)
                self.assertIsNotNone(result.provider_audit_json)

    def test_timeout_has_unknown_cost_and_no_retry_or_private_error_text(self):
        client = FakeClient(error=TimeoutError('sensitive provider error'))
        result = self.judge(client).evaluate(SemanticRequest('{}'))
        self.assertEqual('abstain', result.verdict)
        self.assertIsNone(result.runtime_evidence)
        self.assertEqual(1, len(client.calls))
        self.assertNotIn('sensitive', result.provider_audit_json)
        self.assertTrue(json.loads(result.provider_audit_json)['cost_unknown'])

    def test_missing_or_invalid_usage_does_not_become_zero_cost(self):
        for usage in (None, {'input_tokens': True, 'output_tokens': 20, 'total_tokens': 21},
                      {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 999}):
            result = self.judge(FakeClient(response(usage=usage))).evaluate(SemanticRequest('{}'))
            self.assertEqual('abstain', result.verdict)
            self.assertIsNone(result.runtime_evidence.cost_usd)

    def test_config_change_invalidates_calibration_identity(self):
        judge = self.judge()
        for change in ({'model': 'other'}, {'timeout_seconds': 20}, {'max_output_tokens': 128},
                       {'price_version': 'different'}, {'rubric': 'A different reviewed rubric.'}):
            self.assertNotEqual(judge.configuration_hash, self.judge(**change).configuration_hash)

    def test_invalid_configuration_and_oversized_input_do_not_call_provider(self):
        for change in ({'timeout_seconds': float('nan')}, {'input_usd_per_million': -1},
                       {'max_output_tokens': True}, {'model': ''}, {'output_usd_per_million': None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.judge(**change)
        client = FakeClient()
        result = self.judge(client, max_input_bytes=10).evaluate(SemanticRequest('{"long":"input"}'))
        self.assertEqual('abstain', result.verdict)
        self.assertEqual([], client.calls)


if __name__ == '__main__':
    unittest.main()
