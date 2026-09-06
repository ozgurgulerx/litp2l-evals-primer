"""Native multi-order truth evidence must not inherit single-order authority."""

import copy
from dataclasses import replace
from datetime import datetime, timezone
import json
import unittest

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.order_resolution import DescriptiveResolver, FirstRecordResolver, example_cases, run_case
from cx_eval_lab.semantic import CalibrationRecord, CalibrationRegistry, SemanticJudgment
from tests.test_resolution_evidence import rehash

NOW = datetime(2026, 9, 6, tzinfo=timezone.utc)


class NativeFixtureJudge:
    evaluator_version = 'native-fixture-judge-v1'
    configuration_hash = canonical_hash('native synthetic rubric control')

    def __init__(self, verdict='pass'):
        self.verdict, self.requests = verdict, []

    def evaluate(self, request):
        self.requests.append(request)
        return SemanticJudgment(self.verdict, 'Synthetic protocol control; not measured judge validity.')


def setup_stage(judge=None, **record_changes):
    from cx_eval_lab.resolution_semantic import CRITERION, POLICY, ResolutionSemanticStage
    from cx_eval_lab.resolution_evidence import DATASET, SLICES
    judge = judge or NativeFixtureJudge()
    record = CalibrationRecord(judge.evaluator_version, judge.configuration_hash, CRITERION,
        (DATASET,), (POLICY,), (SLICES,), '2026-09-01T00:00:00Z', '2026-10-01T00:00:00Z',
        'synthetic', canonical_hash('invented counts for native interface tests'),
        100, 100, 0, 0, 30, 0.05, 0.05)
    record = replace(record, **record_changes)
    return ResolutionSemanticStage(judge, CalibrationRegistry((record,)), record.content_hash,
                                    clock=lambda: NOW, allow_synthetic=True)


def packet_for(stage, candidate=None):
    from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
    cases, baseline = example_cases(), DescriptiveResolver()
    candidate = candidate or DescriptiveResolver()
    manifest = make_manifest(cases, baseline.name, candidate.name, semantic_stage=stage)
    return run_paired_resolution(cases=cases, baseline_agent=baseline, candidate_agent=candidate,
        manifest=manifest, semantic_stage=stage).to_dict()


class ResolutionSemanticTests(unittest.TestCase):
    def test_native_request_omits_reference_labels_but_preserves_observed_clarification(self):
        from cx_eval_lab.resolution_semantic import CRITERION
        stage = setup_stage()
        execution = run_case(example_cases()[1], DescriptiveResolver())
        receipt, trust, audit = stage.grade(execution, measurement_kind='synthetic', invocation_id='trial-1')
        request = stage.judge.requests[0]
        self.assertEqual(CRITERION, request.criterion_id)
        evidence = json.loads(request.evidence_json)
        self.assertEqual(3, len(evidence['orders']))
        self.assertTrue(any(e['tool'] == 'ask_customer' for e in evidence['tool_events']))
        for field in ('expected_order_id', 'required_clarifications', 'clarification_reply', 'case_id'):
            self.assertNotIn(field, request.evidence_json)
        self.assertTrue(receipt.passed)
        self.assertEqual({stage.calibration_hash}, set(trust))
        self.assertEqual('graded', audit['status'])

    def test_native_qualification_requires_native_criterion_scope_and_synthetic_permission(self):
        execution = run_case(example_cases()[0], DescriptiveResolver())
        for change in ({'criterion_id':'refund_customer_message_truth_v1'},
                       {'dataset_versions':('wrong',)}, {'policy_versions':('wrong',)},
                       {'slice_scopes':(('different-slice',),)}, {'false_passes':20},
                       {'expires_at':'2026-09-05T00:00:00Z'}):
            stage = setup_stage(**change)
            receipt, trust, _ = stage.grade(execution, measurement_kind='synthetic', invocation_id='x')
            self.assertIsNone(receipt)
            self.assertFalse(trust)
            self.assertEqual([], stage.judge.requests)
        stage = setup_stage()
        self.assertIsNone(stage.grade(execution, measurement_kind='measured', invocation_id='x')[0])
        self.assertEqual([], stage.judge.requests)

    def test_paired_joint_success_needs_structural_and_semantic_checks(self):
        stage = setup_stage()
        packet = packet_for(stage, FirstRecordResolver())
        results = replay_packet(packet, trusted_calibration_hashes={stage.calibration_hash})
        self.assertEqual(16, len(results))
        self.assertEqual(2, sum(r.passed for r in results[8:]))
        self.assertEqual(0, sum(r.unqualified_message_count for r in results))
        self.assertEqual({'resolution-trial-v2'}, {a['payload']['schema'] for a in packet['trial_artifacts']})
        with self.assertRaises(ValueError):
            replay_packet(packet)

    def test_fail_abstain_and_unqualified_remain_distinct(self):
        for verdict in ('fail', 'abstain'):
            stage = setup_stage(NativeFixtureJudge(verdict))
            packet = packet_for(stage)
            results = replay_packet(packet, trusted_calibration_hashes={stage.calibration_hash})
            self.assertTrue(all(not r.passed and r.unqualified_message_count == 0 for r in results))
            self.assertTrue(all(r.to_dict()['semantic_abstention_count'] == int(verdict == 'abstain')
                                for r in results))
        stage = setup_stage()
        stage = replace(stage, registry=CalibrationRegistry((), frozenset({stage.calibration_hash})))
        results = replay_packet(packet_for(stage))
        self.assertTrue(all(not r.passed and r.unqualified_message_count == 1 for r in results))

    def test_context_receipt_and_verdict_cannot_be_moved_or_rewritten(self):
        stage = setup_stage()
        original = packet_for(stage)
        for mutation in ('receipt', 'request', 'verdict', 'qualification', 'invocation'):
            packet = copy.deepcopy(original)
            p = packet['trial_artifacts'][0]['payload']
            if mutation == 'receipt':
                p['semantic_evaluation_receipt'] = packet['trial_artifacts'][2]['payload']['semantic_evaluation_receipt']
            elif mutation == 'request':
                p['semantic_stage']['request']['customer_request']['utterance'] = 'Changed request'
                p['semantic_stage']['request_hash'] = canonical_hash(p['semantic_stage']['request'])
            elif mutation == 'verdict':
                p['semantic_stage']['judgment']['verdict'] = 'fail'
            elif mutation == 'qualification':
                p['semantic_stage']['qualification']['false_examples'] = 101
            else:
                p['semantic_stage']['invocation_id'] = 'different-trial'
            rehash(packet)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                replay_packet(packet, trusted_calibration_hashes={stage.calibration_hash})

    def test_expiry_during_judgment_and_judge_exception_never_pass(self):
        execution = run_case(example_cases()[0], DescriptiveResolver())
        times = iter((NOW, datetime(2026, 11, 1, tzinfo=timezone.utc)))
        stage = replace(setup_stage(), clock=lambda: next(times))
        receipt, trust, audit = stage.grade(execution, measurement_kind='synthetic', invocation_id='x')
        self.assertIsNone(receipt)
        self.assertEqual('qualification_not_current', audit['reason'])
        class Broken(NativeFixtureJudge):
            def evaluate(self, request):
                raise TimeoutError('private provider details')
        stage = setup_stage(Broken())
        receipt, trust, audit = stage.grade(execution, measurement_kind='synthetic', invocation_id='x')
        self.assertTrue(receipt.abstained)
        self.assertNotIn('private provider details', json.dumps(audit))

    def test_current_registry_revocation_does_not_rewrite_historical_grades(self):
        from cx_eval_lab.replay_authority import assess_replay
        stage = setup_stage()
        packet = packet_for(stage)
        for registry, allow, expected in ((stage.registry, True, 'current'),
                (stage.registry, False, 'not_current'),
                (CalibrationRegistry(stage.registry.records, frozenset({stage.calibration_hash})), True, 'not_current')):
            result = assess_replay(packet, trusted_packet_hash=canonical_hash(packet),
                historical_calibration_hashes={stage.calibration_hash}, registry=registry,
                now=NOW, allow_synthetic=allow)
            self.assertEqual(expected, result.calibration_status)
            self.assertEqual(0, result.failed_trials)
            self.assertFalse(result.deployment_authorized)

    def test_qualified_audit_requires_valid_judgment_metering_and_authority(self):
        stage = setup_stage()
        original = packet_for(stage)
        for change in ('explanation', 'runtime', 'latency', 'authority'):
            packet = copy.deepcopy(original)
            audit = packet['trial_artifacts'][0]['payload']['semantic_stage']
            if change == 'explanation':
                audit['judgment']['explanation'] = ''
            elif change == 'runtime':
                audit['judgment']['runtime_evidence'] = {'cost_usd': -1}
            elif change == 'latency':
                audit['judge_latency_ms'] = -4
            else:
                audit['authority'] = 'deployment_qualified'
            rehash(packet)
            with self.subTest(change=change), self.assertRaises(ValueError):
                replay_packet(packet, trusted_calibration_hashes={stage.calibration_hash})

    def test_predispatch_rejection_cannot_acquire_fabricated_dispatch_costs(self):
        stage = setup_stage()
        stage = replace(stage, registry=CalibrationRegistry(()))
        packet = packet_for(stage)
        audit = packet['trial_artifacts'][0]['payload']['semantic_stage']
        audit.update(judgment={'verdict':'pass', 'runtime_evidence':{'cost_usd':999}},
                     request={'false':'evidence'}, request_hash='not a hash', completed_at='not a date')
        rehash(packet)
        with self.assertRaises(ValueError):
            replay_packet(packet)

    def test_expired_postdispatch_evidence_is_still_joined_to_execution(self):
        from itertools import cycle
        times = cycle((NOW, datetime(2026, 11, 1, tzinfo=timezone.utc)))
        stage = replace(setup_stage(), clock=lambda: next(times))
        packet = packet_for(stage)
        self.assertTrue(all(not r.passed for r in replay_packet(packet)))
        audit = packet['trial_artifacts'][0]['payload']['semantic_stage']
        audit['request']['customer_request']['utterance'] = 'Wrong context'
        audit['request_hash'] = canonical_hash(audit['request'])
        rehash(packet)
        with self.assertRaises(ValueError):
            replay_packet(packet)


if __name__ == '__main__':
    unittest.main()
