"""Pinned local source and current qualification; all application evidence is synthetic."""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path

from cx_eval_lab.calibration_data import compile_calibration
from cx_eval_lab.campaign_budget import CampaignPolicy
from cx_eval_lab.evidence import DeterministicTestReceipt, PrerequisiteReceipt, canonical_hash
from cx_eval_lab.native_provider_study import MockTransportLog, _client, _control
from cx_eval_lab.openai_judge import JudgeConfig, OpenAIResponsesJudge, NATIVE_CRITERION
from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases
from cx_eval_lab.release_now import assess_release_now
from cx_eval_lab.resolution_evidence import design
from cx_eval_lab.resolution_semantic import EVALUATOR, ResolutionSemanticStage
from cx_eval_lab.resolution_semantic_study import NOW, _calibration
from cx_eval_lab.semantic import CalibrationRegistry
from cx_eval_lab.source_provenance import local_revision


def _prerequisites(passed):
    return tuple(PrerequisiteReceipt(key, (('synthetic_test_control_not_actual_qualification', passed),),
        canonical_hash({'synthetic_control': key, 'passed': passed}))
        for key in ('typed_tool_boundary', 'semantic_state_grading'))


def _setup(config):
    transport = MockTransportLog(config)
    with _client(transport) as client:
        judge = OpenAIResponsesJudge(config, client)
        _, calibration = _calibration(judge)
        operator_config = {**calibration['operator_config'], 'policy': {
            **calibration['operator_config']['policy'], 'expires_at': '2026-09-07T00:00:00Z'}}
        record = compile_calibration(calibration['annotations'], **operator_config)
        calibration = {**calibration, 'operator_config': operator_config, 'record': asdict(record),
                       'record_hash': record.content_hash, 'error_bounds': record.error_bounds}
        stage = ResolutionSemanticStage(judge, CalibrationRegistry((record,)), record.content_hash,
                                        clock=lambda: NOW, allow_synthetic=True)
        policy = CampaignPolicy('native-current-known', 20_000, 20,
                                int(NOW.timestamp() * 1000) + 60_000, 500)
        agent = DescriptiveResolver()
        # Construct these operator expectations before execution, not by trusting
        # the later packet's own claims about its inputs or configuration.
        values = {'resolution-cases': [asdict(case) for case in example_cases()],
                  'resolution-design': design(agent.name, agent.name, stage.registration),
                  'native-semantic-registration': stage.registration,
                  'campaign-policy': {'schema': 'judge-campaign-policy-v1', **asdict(policy)},
                  'judge-config': judge.configuration_identity}
    return record, calibration, transport.calls, policy, values


def _assessments(packet, arguments, record):
    controls = (
        ('current-diagnostic', {}),
        ('revoked', {'registry': CalibrationRegistry((record,), frozenset({record.content_hash}))}),
        ('expired', {'now': datetime(2026, 9, 8, 12, tzinfo=timezone.utc)}),
        ('synthetic-disabled', {'allow_synthetic': False}),
        ('wrong-revision', {'expected_revision': '0' * 40}),
        ('changed-cases', {'input_values': {**arguments['input_values'], 'resolution-cases': []}}),
        ('unqualified-prerequisites', {'prerequisite_receipts': _prerequisites(False)}),
    )
    return [{'name': name, 'assessment': assess_release_now(packet, **{**arguments, **changes}).to_dict()}
            for name, changes in controls]


def _conforms(assessments, revision):
    results = {item['name']: item['assessment'] for item in assessments}
    current = results['current-diagnostic']
    source = current['checks']['source'] or {}
    replay = current['checks']['replay'] or {}
    return (source.get('code_revision') == revision and replay.get('calibration_status') == 'current'
            and replay.get('replayed_trials') == 16 and replay.get('failed_trials') == 0
            and current['action'] == 'hold'
            and all(result['action'] == 'block' for name, result in results.items()
                    if name != 'current-diagnostic')
            and (results['revoked']['checks']['replay'] or {}).get('failed_trials') == 0
            and 'current_calibration_not_current' in results['expired']['issues']
            and 'source_verification_failed' in results['wrong-revision']['issues']
            and 'source_verification_failed' in results['changed-cases']['issues'])


def run_study():
    root = Path(__file__).resolve().parents[1]
    revision = local_revision(root)
    config = JudgeConfig(model='pinned-fixture-model', criterion_id=NATIVE_CRITERION,
        input_usd_per_million=2, output_usd_per_million=8, price_version='invented-fixture-price')
    record, calibration, calibration_calls, policy, values = _setup(config)
    control = _control('current-known', config, record, code_revision=revision)
    packet, snapshot = control['packet'], control['snapshot']
    # These in-process anchors are a synthetic operator trust exercise, not signatures.
    anchors = {'packet': canonical_hash(packet), 'snapshot': canonical_hash(snapshot)}
    test_receipt = DeterministicTestReceipt('synthetic-current-release-test-control', revision,
        (('synthetic_replay_control_not_capability_validation', True),),
        canonical_hash({'synthetic_test_control': True}))
    prerequisites = _prerequisites(True)
    arguments = dict(trusted_packet_hash=anchors['packet'],
        historical_calibration_hashes={record.content_hash}, registry=CalibrationRegistry((record,)),
        now=NOW, root=root, input_files={}, input_values=values, expected_revision=revision,
        expected_evaluator_version=EVALUATOR, deterministic_test_receipt=test_receipt,
        prerequisite_receipts=prerequisites, campaign_policy=policy, campaign_snapshot=snapshot,
        trusted_snapshot_hash=anchors['snapshot'], allow_synthetic=True)
    assessments = _assessments(packet, arguments, record)
    return {'schema': 'current-release-study-v1', 'evidence_kind': 'executed_local_sdk_mock_transport',
        'conformance_passed': _conforms(assessments, revision),
        'deployment_authorized': False, 'source_root': str(root), 'expected_revision': revision,
        'expected_evaluator_version': EVALUATOR, 'judge_config': asdict(config),
        'calibration': calibration, 'calibration_transport': calibration_calls,
        'packet': packet, 'snapshot': snapshot, 'transport': control['transport'],
        'operator_values': values, 'operator_policy': asdict(policy),
        'simulated_operator_anchors': anchors, 'historical_calibration_hashes': [record.content_hash],
        'synthetic_deterministic_receipt': asdict(test_receipt),
        'synthetic_prerequisite_receipts': [asdict(receipt) for receipt in prerequisites],
        'assessments': assessments,
        'limitations': 'Real local source bytes are compared with the current committed revision, '
            'not copied fixture sources. A dirty source checkout yields source_verification_failed; '
            'the report is retained and the CLI exits nonzero if controls fail to reproduce. '
            'All models, reviewers, qualification, prerequisite assertions, clock, prices and HTTP '
            'responses are synthetic; no network or paid calls. Four calibration executions/requests '
            'are separate from sixteen paired agent executions/SDK requests. All cases share one '
            'customer and calibration overlaps controls. The synthetic true prerequisite controls '
            'isolate current-state checks; they are not actual full qualification. The current '
            'diagnostic must still hold for insufficient independent samples. Anchors are supplied '
            'by this local process, not authenticated signatures. Source consistency does not attest '
            'loaded code, dependencies, real execution or future registry freshness. No result '
            'authorizes deployment, and original packet grades are never overwritten.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, 'Choose a new current-release artifact path.\n')
    report = run_study()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')
    if not report['conformance_passed']:
        parser.exit(1, 'Current-release controls did not reproduce; inspect retained checks.\n')


if __name__ == '__main__':
    main()
