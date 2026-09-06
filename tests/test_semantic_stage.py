"""Evaluator-owned semantic grading must enforce qualification at run time."""

from dataclasses import replace
from datetime import datetime, timezone
import unittest

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.runner import evaluate_agent, run_paired_experiment, DEFAULT_MEASUREMENT_PROFILE
from tests.test_evidence_spine import make_manifest


NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)
CONFIG = canonical_hash({'model': 'test-only-judge', 'rubric': 'truth-v1', 'parser': 'v1'})


class FreeFormReference(ReferenceSupportAgent):
    def run(self, request, tools):
        output = super().run(request, tools)
        return replace(output, message='The payment instruction is recorded; arrival is not verified.',
                       message_template_id=None)


class FixtureJudge:
    evaluator_version = 'fixture-judge-v1'
    configuration_hash = CONFIG

    def __init__(self, verdict='pass', error=None):
        self.verdict, self.error = verdict, error
        self.requests = []

    def evaluate(self, request):
        from cx_eval_lab.semantic import SemanticJudgment
        self.requests.append(request)
        if self.error:
            raise self.error
        return SemanticJudgment(self.verdict, 'Synthetic control response, not a semantic validity study.')


def setup_stage(judge=None, **changes):
    from cx_eval_lab.semantic import CalibrationRecord, CalibrationRegistry, SemanticStage
    record = CalibrationRecord(
        evaluator_version='fixture-judge-v1', configuration_hash=CONFIG,
        criterion_id='refund_customer_message_truth_v1',
        dataset_versions=('refund-v1',), policy_versions=('refund-policy-v1',),
        slice_scopes=(('language:en', 'risk:standard', 'journey:refund'),),
        issued_at='2026-09-01T00:00:00+00:00', expires_at='2026-10-01T00:00:00+00:00',
        evidence_kind='synthetic', label_artifact_hash=canonical_hash('synthetic labels'),
        truthful_examples=100, false_examples=100, false_passes=0, false_blocks=0,
        minimum_per_class=30, max_false_pass_upper=0.05, max_false_block_upper=0.05,
    )
    record = replace(record, **changes)
    registry = CalibrationRegistry((record,))
    return SemanticStage(judge or FixtureJudge(), registry, record.content_hash,
                         clock=lambda: NOW, allow_synthetic=True)


class SemanticStageTests(unittest.TestCase):
    def setUp(self):
        self.case = load_refund_cases('evals/cx-support/datasets/regression/refund_v1.json')[0]

    def test_runner_owns_receipt_and_judge_does_not_see_expected_label(self):
        judge = FixtureJudge()
        result = evaluate_agent(FreeFormReference(), (self.case,), semantic_stage=setup_stage(judge))
        self.assertEqual(1, result.task_success_rate)
        receipt = result.case_results[0].semantic_evaluation_receipt
        self.assertIsNotNone(receipt.evidence_context_hash)
        self.assertEqual(1, len(judge.requests))
        self.assertNotIn('expected_outcome', judge.requests[0].evidence_json)
        self.assertNotIn('simulate_timeout_after_commit', judge.requests[0].evidence_json)

    def test_single_run_preserves_semantic_audit_and_usage_separately(self):
        from cx_eval_lab.semantic import SemanticJudgment
        from cx_eval_lab.models import RuntimeEvidence
        class MeteredFixture(FixtureJudge):
            def evaluate(self, request):
                return SemanticJudgment('pass', 'Synthetic fixture.', RuntimeEvidence(
                    'fixture', 'test-model', ('judge-response-1',), 10, 2, 12, 0.001, 'fixture price'))
        judge = MeteredFixture()
        result = evaluate_agent(FreeFormReference(), (self.case,), semantic_stage=setup_stage(judge))
        data = result.case_results[0].to_dict()
        self.assertIn('semantic_stage', data)
        self.assertEqual(0.001, data['semantic_stage']['judgment']['runtime_evidence']['cost_usd'])
        self.assertEqual(0.08, data['cost_usd'])
        self.assertIn('judge_latency_ms', data['semantic_stage'])

    def test_expiry_scope_version_and_small_sample_block_qualification(self):
        changes = (
            {'expires_at': '2026-09-05T00:00:00+00:00'},
            {'configuration_hash': canonical_hash('changed config')},
            {'evaluator_version': 'different-judge'},
            {'slice_scopes': (('language:tr',),)},
            {'dataset_versions': ('different-dataset',)},
            {'policy_versions': ('different-policy',)},
            {'false_examples': 10},
            {'false_passes': 20},
        )
        for change in changes:
            with self.subTest(change=change):
                judge = FixtureJudge()
                result = evaluate_agent(FreeFormReference(), (self.case,),
                                        semantic_stage=setup_stage(judge, **change))
                self.assertEqual(1, result.unqualified_message_count)
                self.assertEqual([], judge.requests)

    def test_abstention_and_timeout_never_pass(self):
        for judge in (FixtureJudge('abstain'), FixtureJudge(error=TimeoutError('private detail'))):
            result = evaluate_agent(FreeFormReference(), (self.case,), semantic_stage=setup_stage(judge))
            self.assertEqual(0, result.task_success_rate)
            self.assertEqual(1, result.semantic_abstention_count)

    def test_qualified_negative_judgment_is_a_false_claim_not_missing_qualification(self):
        result = evaluate_agent(FreeFormReference(), (self.case,),
                                semantic_stage=setup_stage(FixtureJudge('fail')))
        self.assertEqual(0, result.task_success_rate)
        self.assertEqual(0, result.unqualified_message_count)
        self.assertEqual(1, result.false_message_claim_count)

    def test_synthetic_qualification_cannot_enter_measured_run(self):
        result = evaluate_agent(FreeFormReference(), (self.case,), measurement_profile=None,
                                semantic_stage=setup_stage())
        self.assertEqual(1, result.unqualified_message_count)

    def test_paired_artifact_preserves_semantic_stage_and_replays_with_external_trust(self):
        from cx_eval_lab.artifacts import replay_packet
        stage = setup_stage()
        manifest = replace(make_manifest(), population_hash=canonical_hash(
            [[self.case.case_id, self.case.customer_id, list(self.case.slices)]]))
        packet = run_paired_experiment(
            baseline_agent=FreeFormReference(), candidate_agent=FreeFormReference(),
            cases=(self.case,), manifest=manifest, semantic_stage=stage,
            baseline_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
            candidate_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
        ).to_dict()
        audit = packet['trial_artifacts'][0]['payload']['semantic_stage']
        self.assertEqual('synthetic', audit['qualification']['evidence_kind'])
        self.assertEqual('pass', audit['judgment']['verdict'])
        with self.assertRaisesRegex(ValueError, 'independently trusted'):
            replay_packet(packet)
        self.assertTrue(all(result.passed for result in replay_packet(
            packet, trusted_calibration_hashes=frozenset({stage.calibration_hash}))))


if __name__ == '__main__':
    unittest.main()
