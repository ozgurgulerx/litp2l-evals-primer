"""Provider contract tests; no network or paid model evaluation."""

import copy
import json
import os
import unittest
from unittest.mock import patch
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
        self.assertEqual({'timeout': 30.0, 'max_retries': 0,
                          'base_url': 'https://api.openai.com/v1'}, client.options[0])
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

    def test_effective_client_endpoint_drift_blocks_before_sending(self):
        client = FakeClient()
        judge = self.judge(client)
        client.base_url = 'https://example.invalid/v1'
        result = judge.evaluate(SemanticRequest('{}'))
        self.assertEqual('abstain', result.verdict)
        self.assertEqual([], client.calls)

    def test_extreme_usage_abstains_and_preserves_raw_evidence(self):
        usage = {'input_tokens': 10**400, 'output_tokens': 20, 'total_tokens': 10**400 + 20}
        result = self.judge(FakeClient(response(usage=usage)), input_usd_per_million=2.0,
                            output_usd_per_million=8.0).evaluate(SemanticRequest('{}'))
        self.assertEqual('abstain', result.verdict)
        self.assertIsNone(result.runtime_evidence.cost_usd)
        self.assertEqual(usage, json.loads(result.provider_audit_json)['response']['usage'])

    def test_invalid_configuration_and_oversized_input_do_not_call_provider(self):
        for change in ({'timeout_seconds': float('nan')}, {'timeout_seconds': 10**400},
                       {'input_usd_per_million': 10**400}, {'input_usd_per_million': -1},
                       {'max_output_tokens': True}, {'model': ''}, {'output_usd_per_million': None}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.judge(**change)
        client = FakeClient()
        result = self.judge(client, max_input_bytes=10).evaluate(SemanticRequest('{"long":"input"}'))
        self.assertEqual('abstain', result.verdict)
        self.assertEqual([], client.calls)

    def test_paired_runner_preserves_provider_evidence_and_replays(self):
        from cx_eval_lab.dataset import load_refund_cases
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.runner import run_paired_experiment, DEFAULT_MEASUREMENT_PROFILE
        from cx_eval_lab.artifacts import replay_packet
        from tests.test_semantic_stage import FreeFormReference, setup_stage
        from tests.test_evidence_spine import make_manifest
        client = FakeClient()
        judge = self.judge(client)
        stage = setup_stage(judge, evaluator_version=judge.evaluator_version,
                            configuration_hash=judge.configuration_hash)
        cases = load_refund_cases('evals/cx-support/datasets/regression/refund_v1.json')[:1]
        manifest = replace(make_manifest(), population_hash=canonical_hash(
            [[c.case_id, c.customer_id, list(c.slices)] for c in cases]))
        packet = run_paired_experiment(
            baseline_agent=FreeFormReference(), candidate_agent=FreeFormReference(),
            cases=cases, manifest=manifest, semantic_stage=stage,
            baseline_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
            candidate_measurement_profile=DEFAULT_MEASUREMENT_PROFILE).to_dict()
        self.assertEqual(4, len(client.calls))
        for artifact in packet['trial_artifacts']:
            judgment = artifact['payload']['semantic_stage']['judgment']
            self.assertEqual('resp_fixture', json.loads(judgment['provider_audit_json'])['response']['id'])
        self.assertEqual(4, len(replay_packet(packet,
                         trusted_calibration_hashes=frozenset({stage.calibration_hash}))))

    def test_installed_sdk_with_in_memory_http_transport_never_uses_network(self):
        import httpx2
        from openai import OpenAI
        from cx_eval_lab.openai_judge import OpenAIResponsesJudge
        for status in (200, 429):
            calls = []
            def handler(request):
                calls.append(request)
                body = response() if status == 200 else {'error': {'message': 'fixture rate limit'}}
                return httpx2.Response(status, json=body)
            with patch.dict(os.environ, {'OPENAI_API_KEY': 'fixture-not-a-real-key'}), OpenAI(
                        api_key=os.environ['OPENAI_API_KEY'], base_url='https://api.openai.com/v1',
                        http_client=httpx2.Client(transport=httpx2.MockTransport(handler))) as client:
                judge = OpenAIResponsesJudge(self.judge().config, client)
                result = judge.evaluate(SemanticRequest('{}'))
            self.assertEqual(1, len(calls))
            self.assertEqual('/v1/responses', calls[0].url.path)
            body = json.loads(calls[0].content)
            self.assertEqual(512, body['max_output_tokens'])
            self.assertFalse(body['store'])
            self.assertEqual('pass' if status == 200 else 'abstain', result.verdict)


if __name__ == '__main__':
    unittest.main()
