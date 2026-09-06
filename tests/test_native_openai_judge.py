"""Native criterion wire conformance with the installed SDK, not live accuracy."""

from dataclasses import FrozenInstanceError, asdict, replace
from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import patch

import httpx2
from openai import OpenAI

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.openai_judge import JudgeConfig, OpenAIResponsesJudge, _schema
from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases
from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
from cx_eval_lab.resolution_semantic import CRITERION as NATIVE_CRITERION, POLICY, ResolutionSemanticStage
from cx_eval_lab.resolution_evidence import DATASET, SLICES
from cx_eval_lab.semantic import CRITERION, CalibrationRecord, CalibrationRegistry, SemanticRequest
from tests.test_openai_judge import response


def config(**changes):
    return JudgeConfig(model='pinned-fixture-model', criterion_id=NATIVE_CRITERION,
                       input_usd_per_million=2, output_usd_per_million=8,
                       price_version='synthetic-price', **changes)


def client_for(handler):
    with patch.dict(os.environ, {'OPENAI_API_KEY': 'fixture-not-a-real-key'}):
        return OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url='https://api.openai.com/v1',
                      http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))


class NativeOpenAIJudgeTests(unittest.TestCase):
    def test_explicit_criterion_is_frozen_and_keeps_legacy_hash_unchanged(self):
        def handler(request):
            self.fail('configuration inspection must not send requests')
        with client_for(handler) as client:
            legacy = OpenAIResponsesJudge(JudgeConfig(model='pinned-fixture-model'), client)
            old_config = {key: value for key, value in asdict(legacy.config).items()
                          if key != 'criterion_id'}
            old_hash = canonical_hash({'config': old_config, 'schema': _schema(),
                'adapter': legacy.evaluator_version, 'endpoint': 'https://api.openai.com/v1', 'max_retries': 0})
            self.assertEqual(old_hash, legacy.configuration_hash)
            native = OpenAIResponsesJudge(config(), client)
            self.assertNotEqual(legacy.configuration_hash, native.configuration_hash)
            self.assertNotEqual(native.configuration_hash,
                                OpenAIResponsesJudge(replace(native.config, rubric='Reviewed custom rubric'),
                                                     client).configuration_hash)
            with self.assertRaises(FrozenInstanceError):
                native.config.criterion_id = CRITERION

    def test_only_supported_criteria_and_no_dispatch_on_request_mismatch(self):
        for bad in ('other', '', None, ['unhashable']):
            with self.subTest(criterion=bad), self.assertRaises(ValueError):
                JudgeConfig(model='pinned-fixture-model', criterion_id=bad)
        calls = []
        def handler(request):
            calls.append(request)
            return httpx2.Response(200, json=response())
        with client_for(handler) as client:
            for settings, criterion in ((config(), CRITERION),
                                        (JudgeConfig(model='pinned-fixture-model'), NATIVE_CRITERION)):
                result = OpenAIResponsesJudge(settings, client).evaluate(SemanticRequest('{}', criterion))
                self.assertEqual('abstain', result.verdict)
                self.assertEqual('not_sent', json.loads(result.provider_audit_json)['status'])
        self.assertEqual([], calls)

    def test_native_sdk_pass_fail_abstain_429_and_invalid_usage(self):
        for verdict, status, bad_usage in (('pass', 200, False), ('fail', 200, False),
                ('abstain', 200, False), ('pass', 429, False), ('pass', 200, True)):
            calls = []
            def handler(request):
                calls.append(request)
                payload = response()
                payload['output'][0]['content'][0]['text'] = json.dumps({
                    'verdict': verdict, 'explanation': 'Mock HTTP result; no accuracy claim.'})
                if bad_usage:
                    payload['usage']['total_tokens'] = 999
                return httpx2.Response(status, json=payload if status == 200 else
                    {'error': {'message': 'fixture rate limit', 'type': 'rate_limit_error'}})
            with self.subTest(verdict=verdict, status=status, invalid_usage=bad_usage), client_for(handler) as client:
                judge = OpenAIResponsesJudge(config(), client)
                result = judge.evaluate(SemanticRequest('{}', NATIVE_CRITERION))
                self.assertEqual(verdict if status == 200 and not bad_usage else 'abstain', result.verdict)
                self.assertEqual(1, len(calls))
                body = json.loads(calls[0].content)
                self.assertEqual('/v1/responses', calls[0].url.path)
                self.assertEqual('multi_order_truth_verdict', body['text']['format']['name'])
                self.assertEqual([], body['tools'])
                self.assertFalse(body['store'])
                self.assertFalse(body['stream'])
                self.assertEqual('disabled', body['truncation'])
                for phrase in ('customer intent', 'all orders', 'observed clarification', 'claims'):
                    self.assertIn(phrase, body['instructions'].lower())
                if status == 200 and not bad_usage:
                    self.assertEqual(120, result.runtime_evidence.total_tokens)
                    self.assertAlmostEqual(0.00036, result.runtime_evidence.cost_usd)
                elif bad_usage:
                    self.assertIsNone(result.runtime_evidence.total_tokens)
                    self.assertIsNone(result.runtime_evidence.cost_usd)
                    self.assertEqual(999, json.loads(result.provider_audit_json)['response']['usage']['total_tokens'])
                else:
                    self.assertIsNone(result.runtime_evidence)

    def test_native_stage_paired_run_retains_actual_sdk_evidence_and_replays(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx2.Response(200, json=response(id=f'resp_native_{len(calls)}'))
        with client_for(handler) as client:
            judge = OpenAIResponsesJudge(config(), client)
            record = CalibrationRecord(judge.evaluator_version, judge.configuration_hash, NATIVE_CRITERION,
                (DATASET,), (POLICY,), (SLICES,), '2026-09-01T00:00:00Z', '2026-10-01T00:00:00Z',
                'synthetic', canonical_hash('invented fixture counts, not reviewed human labels'),
                100, 100, 0, 0, 30, 0.05, 0.05)
            stage = ResolutionSemanticStage(judge, CalibrationRegistry((record,)), record.content_hash,
                clock=lambda: datetime(2026, 9, 6, tzinfo=timezone.utc), allow_synthetic=True)
            cases, baseline, candidate = example_cases(), DescriptiveResolver(), DescriptiveResolver()
            manifest = make_manifest(cases, baseline.name, candidate.name, semantic_stage=stage)
            packet = run_paired_resolution(cases=cases, baseline_agent=baseline, candidate_agent=candidate,
                manifest=manifest, semantic_stage=stage).to_dict()
        self.assertEqual(16, len(calls))
        results = replay_packet(packet, trusted_calibration_hashes={record.content_hash})
        self.assertEqual(16, len(results))
        self.assertTrue(all(result.passed for result in results))
        for call in calls:
            wire = json.loads(call.content)
            evidence_text = wire['input'][0]['content']
            evidence = json.loads(evidence_text)
            self.assertEqual(3, len(evidence['orders']))
            for hidden in ('expected_order_id', 'required_clarifications', 'clarification_reply', 'case_id'):
                self.assertNotIn(hidden, evidence_text)
        for artifact in packet['trial_artifacts']:
            audit = artifact['payload']['semantic_stage']
            self.assertEqual('lab_only', audit['authority'])
            self.assertEqual('synthetic', audit['qualification']['evidence_kind'])
            judgment = audit['judgment']
            self.assertEqual(120, judgment['runtime_evidence']['total_tokens'])
            provider = json.loads(judgment['provider_audit_json'])
            self.assertEqual(judge.configuration_hash, provider['configuration_hash'])
            self.assertTrue(provider['response']['id'].startswith('resp_native_'))


if __name__ == '__main__':
    unittest.main()
