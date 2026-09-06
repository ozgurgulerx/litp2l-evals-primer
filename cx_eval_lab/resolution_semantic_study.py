"""Row-derived synthetic native semantic controls; never empirical qualification."""

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
from pathlib import Path

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.calibration_data import compile_calibration
from cx_eval_lab.cost_accounting import summarize_packet_costs
from cx_eval_lab.evidence import (
    DeterministicTestReceipt, PrerequisiteReceipt, build_evidence_receipt, canonical_hash,
)
from cx_eval_lab.order_resolution import (
    DescriptiveResolver, FirstRecordResolver, example_cases, run_case,
)
from cx_eval_lab.replay_authority import assess_replay
from cx_eval_lab.resolution_evidence import DATASET, SLICES
from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
from cx_eval_lab.resolution_semantic import (
    CRITERION, POLICY, NativeScope, ResolutionSemanticStage, judge_request,
)
from cx_eval_lab.semantic import CalibrationRegistry, SemanticJudgment, SemanticRequest

NOW = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)


class FalseSettlementResolver(DescriptiveResolver):
    name = 'false-settlement-mutant'

    def run(self, request, tools):
        output = super().run(request, tools)
        return replace(output, message='Your money has arrived.')


class LiteralFixtureJudge:
    """Three exact sentences only; deliberately not a general semantic evaluator."""

    evaluator_version = 'native-literal-fixture-v1'
    configuration_hash = canonical_hash({
        'rubric': 'literal-confirmed-with-commit; clarification-with-no-commit; arrived-false',
        'criterion': CRITERION, 'version': 1,
    })

    def evaluate(self, request):
        evidence = json.loads(request.evidence_json)
        count = sum(row['state']['refund_transaction_count'] for row in evidence['orders'])
        message = evidence['output']['message']
        if message == 'Your money has arrived.':
            verdict = 'fail'  # The mock exposes no authoritative settlement confirmation.
        elif message == 'Your refund has been confirmed.':
            verdict = 'pass' if count == 1 else 'fail'
        elif message == 'Please clarify which purchase you mean.':
            unanswered = any(event['tool'] == 'ask_customer' and event.get('result') is None
                             and 'error' not in event for event in evidence['tool_events'])
            verdict = 'pass' if count == 0 and unanswered else 'fail'
        else:
            verdict = 'abstain'
        return SemanticJudgment(verdict, 'Synthetic literal rule, not general semantic validity; '
                                'object intent is graded separately by the structural contract.')


def _calibration(judge):
    scope = {'dataset_version': DATASET, 'policy_version': POLICY, 'slices': list(SLICES)}
    reviewers = ['synthetic-reviewer-a', 'synthetic-reviewer-b']
    executions, rows = [], []
    cases = example_cases()
    for case in (cases[0], cases[3]):
        for agent, label in ((DescriptiveResolver(), 'truthful'), (FalseSettlementResolver(), 'false')):
            execution = run_case(case, agent)
            evidence = judge_request(execution)
            identity = f'{case.case_id}:{agent.name}'
            judgment = judge.evaluate(SemanticRequest(json.dumps(evidence), CRITERION, identity))
            executions.append({'row_id': identity, 'execution': execution,
                               'execution_hash': canonical_hash(execution)})
            rows.append({'id': identity, 'group_id': f'synthetic-fixture:{identity}',
                'split': 'calibration', 'scope': scope, 'evidence': evidence,
                'reviews': [{'reviewer_id': reviewer, 'label': label} for reviewer in reviewers],
                'adjudication': None, 'judgment': {'verdict': judgment.verdict,
                    'evaluator_version': judge.evaluator_version,
                    'configuration_hash': judge.configuration_hash, 'criterion_id': CRITERION,
                    'evidence_hash': canonical_hash(evidence)}})
    annotations = {'schema_version': 'calibration-annotations-v1', 'evidence_kind': 'synthetic',
                   'scope': scope, 'rows': rows}
    policy = {'issued_at': '2026-09-01T00:00:00Z', 'expires_at': '2026-10-01T00:00:00Z',
              'minimum_per_class': 2, 'max_false_pass_upper': 0.80,
              'max_false_block_upper': 0.80, 'max_abstention_rate': 0.0}
    config = {'policy': policy, 'trusted_reviewers': reviewers,
              'excluded_group_ids': [], 'excluded_evidence_hashes': []}
    record = compile_calibration(annotations, **config)
    return record, {'annotations': annotations, 'operator_config': config,
                    'executions': executions, 'record': asdict(record),
                    'record_hash': record.content_hash, 'error_bounds': record.error_bounds,
                    'deployment_authorized': False}


def _comparison(candidate, stage):
    cases, baseline = example_cases(), DescriptiveResolver()
    manifest = replace(make_manifest(cases, baseline.name, candidate.name, semantic_stage=stage),
                       experiment_id='native-semantic-' + candidate.name)
    experiment = run_paired_resolution(cases=cases, baseline_agent=baseline,
        candidate_agent=candidate, manifest=manifest, semantic_stage=stage)
    packet = experiment.to_dict()
    trust = {stage.calibration_hash}
    results = replay_packet(packet, trusted_calibration_hashes=trust)
    candidate_results = results[len(experiment.baseline_trials):]
    checks = (('all_registered_trials_replayed', len(results) == 16),)
    evidence = {'checks': checks, 'packet_hash': canonical_hash(packet)}
    prerequisites = tuple(PrerequisiteReceipt(name, ((check, False),), canonical_hash({'missing': check}))
        for name, check in (('typed_tool_boundary', 'full_boundary_qualification_available'),
                            ('semantic_state_grading', 'independent_human_native_qualification_available')))
    receipt = build_evidence_receipt(experiment=experiment,
        deterministic_test_receipt=DeterministicTestReceipt('native-semantic-replay',
            manifest.code_revision, checks, canonical_hash(evidence)),
        prerequisite_receipts=prerequisites, issued_at=NOW.isoformat())
    if receipt.action != 'block' or receipt.authority_ceiling != 'none':
        raise ValueError('synthetic native evidence cannot authorize release')
    return {'candidate': candidate.name, 'packet': packet, 'test_evidence': evidence,
            'release_receipt': receipt.to_dict(),
            'costs': summarize_packet_costs(packet, trusted_calibration_hashes=trust),
            'candidate_joint_passes': sum(result.passed for result in candidate_results),
            'candidate_structural_passes': sum(result.structural.passed for result in candidate_results),
            'candidate_completed_tasks': sum(result.task_completed for result in candidate_results)}


def run_study():
    judge = LiteralFixtureJudge()
    record, calibration = _calibration(judge)
    strict = replace(record, minimum_per_class=30)
    reason = strict.rejection(judge, NativeScope(), POLICY, NOW, True, criterion_id=CRITERION)
    stage = ResolutionSemanticStage(judge, CalibrationRegistry((record,)), record.content_hash,
                                    clock=lambda: NOW, allow_synthetic=True)
    comparisons = [_comparison(agent, stage) for agent in
                  (FalseSettlementResolver(), FirstRecordResolver(), DescriptiveResolver())]
    packet = comparisons[-1]['packet']
    revoked = assess_replay(packet, trusted_packet_hash=canonical_hash(packet),
        historical_calibration_hashes={record.content_hash},
        registry=CalibrationRegistry((record,), frozenset({record.content_hash})),
        now=NOW, allow_synthetic=True)
    return {'study': 'native-resolution-semantic-study-v1',
            'evidence_kind': 'executed_deterministic_mock', 'deployment_authorized': False,
            'calibration': calibration, 'strict_policy': asdict(strict),
            'strict_policy_rejection': reason, 'comparisons': comparisons,
            'revoked_assessment': asdict(revoked),
            'limitations': 'Four synthetic rows and synthetic reviewers, not independent human labels. '
                'Fixture group IDs identify executions, not independent customers: all cases share one '
                'customer. Calibration overlaps comparison controls; no held-out evaluation exists. '
                'The permissive n=2 and 0.80 upper-bound policy exercises wiring only. The literal '
                'judge recognizes three sentences and does not infer arbitrary customer intent. '
                'Two permutations are not independent samples. Agent cost/latency profiles are '
                'synthetic; mock wall times are retained separately. No live models, authenticated '
                'review, general semantic validity, or deployment qualification.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, 'Choose a new native semantic artifact path.\n')
    report = run_study()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
