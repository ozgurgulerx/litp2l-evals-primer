"""Installed SDK plus in-memory HTTP and local campaign controls; no live calls."""

import argparse
from dataclasses import asdict, replace
from importlib.metadata import version
import json
from pathlib import Path
import platform
import tempfile
import uuid

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.budgeted_judge import BudgetedSemanticJudge
from cx_eval_lab.campaign_budget import CampaignLedger, CampaignPolicy
from cx_eval_lab.campaign_gate import assess_campaign
from cx_eval_lab.cost_accounting import summarize_packet_costs
from cx_eval_lab.evidence import (
    DeterministicTestReceipt, PrerequisiteReceipt, build_evidence_receipt, canonical_hash,
)
from cx_eval_lab.openai_judge import JudgeConfig, OpenAIResponsesJudge, NATIVE_CRITERION
from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases
from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
from cx_eval_lab.resolution_semantic import ResolutionSemanticStage
from cx_eval_lab.resolution_semantic_study import LiteralFixtureJudge, NOW, _calibration
from cx_eval_lab.semantic import CalibrationRegistry, SemanticRequest


class MockTransportLog:
    """Logs only synthetic bodies; never credentials, headers or network traffic."""

    def __init__(self, config, *, rate_limited=False):
        self.config, self.rate_limited = config, rate_limited
        self.calls = []

    def handle(self, request):
        import httpx2
        body = json.loads(request.content)
        if request.url.path != '/v1/responses':
            raise ValueError('unexpected mock SDK endpoint')
        status = 429 if self.rate_limited else 200
        if self.rate_limited:
            response = {'error': {'message': 'Synthetic rate limit; no network call.'}}
        else:
            verdict = LiteralFixtureJudge().evaluate(SemanticRequest(
                body['input'][0]['content'], NATIVE_CRITERION))
            response = {'id': f'resp_native_fixture_{len(self.calls)}',
                'model': self.config.model, 'status': 'completed', 'error': None,
                'incomplete_details': None,
                'usage': {'input_tokens': 100, 'output_tokens': 20, 'total_tokens': 120},
                'output': [{'type': 'message', 'role': 'assistant', 'status': 'completed',
                    'content': [{'type': 'output_text', 'text': json.dumps({
                        'verdict': verdict.verdict, 'explanation': verdict.explanation})}]}]}
        self.calls.append({'path': request.url.path, 'request': body,
                           'status_code': status, 'response': response})
        return httpx2.Response(status, json=response)


def _client(transport):
    import httpx2
    from openai import OpenAI
    # An ephemeral non-credential satisfies SDK construction. MockTransport handles
    # every request in-process; no environment key or real provider is consulted.
    return OpenAI(api_key=uuid.uuid4().hex, base_url='https://api.openai.com/v1', max_retries=0,
                  http_client=httpx2.Client(transport=httpx2.MockTransport(transport.handle)))


def _control(name, config, record, *, rate_limited=False, max_admissions=20, reservation=500):
    transport = MockTransportLog(config, rate_limited=rate_limited)
    clock_ms = int(NOW.timestamp() * 1000)
    policy = CampaignPolicy('native-' + name, 20_000, max_admissions, clock_ms + 60_000, reservation)
    with tempfile.TemporaryDirectory() as root, _client(transport) as client:
        ledger = CampaignLedger.create(Path(root) / 'campaign.sqlite', policy, clock_ms=lambda: clock_ms)
        judge = BudgetedSemanticJudge(OpenAIResponsesJudge(config, client), ledger)
        stage = ResolutionSemanticStage(judge, CalibrationRegistry((record,)), record.content_hash,
                                        clock=lambda: NOW, allow_synthetic=True)
        cases, agent = example_cases(), DescriptiveResolver()
        manifest = replace(make_manifest(cases, agent.name, agent.name, semantic_stage=stage),
                           experiment_id='native-provider-' + name)
        experiment = run_paired_resolution(cases=cases, baseline_agent=agent, candidate_agent=agent,
                                           manifest=manifest, semantic_stage=stage)
        packet, snapshot = experiment.to_dict(), ledger.snapshot()
    trust = {record.content_hash}
    anchors = {'packet': canonical_hash(packet), 'snapshot': canonical_hash(snapshot)}
    assessment = assess_campaign(packet, snapshot, expected_policy=policy,
        trusted_packet_hash=anchors['packet'], trusted_snapshot_hash=anchors['snapshot'],
        trusted_calibration_hashes=trust)
    results = replay_packet(packet, trusted_calibration_hashes=trust)
    checks = (('sixteen_trials_replayed', len(results) == 16),)
    proof = {'checks': checks, 'packet_hash': anchors['packet'], 'campaign_status': assessment.status}
    receipt = build_evidence_receipt(experiment=experiment,
        deterministic_test_receipt=DeterministicTestReceipt('native-mock-provider-replay',
            manifest.code_revision, checks, canonical_hash(proof)),
        prerequisite_receipts=tuple(PrerequisiteReceipt(key, (('independent_qualification', False),),
            canonical_hash({'unqualified': key})) for key in ('typed_tool_boundary', 'semantic_state_grading')),
        issued_at=NOW.isoformat(), campaign_assessment=assessment)
    if receipt.action != 'block' or receipt.authority_ceiling != 'none':
        raise ValueError('mock provider evidence cannot authorize deployment')
    return {'name': name, 'packet': packet, 'snapshot': snapshot, 'transport': transport.calls,
            'simulated_operator_anchors': anchors, 'operator_policy': asdict(policy),
            'assessment': asdict(assessment), 'test_evidence': proof,
            'release_receipt': receipt.to_dict(),
            'costs': summarize_packet_costs(packet, trusted_calibration_hashes=trust)}


def run_study():
    config = JudgeConfig(model='pinned-fixture-model', criterion_id=NATIVE_CRITERION,
        input_usd_per_million=2, output_usd_per_million=8, price_version='invented-fixture-price')
    transport = MockTransportLog(config)
    with _client(transport) as client:
        record, calibration = _calibration(OpenAIResponsesJudge(config, client))
    controls = [_control('known', config, record),
                _control('rate-limited', config, record, rate_limited=True),
                _control('admission-limited', config, record, max_admissions=2),
                _control('reservation-overrun', config, record, reservation=300)]
    if [c['assessment']['status'] for c in controls] != ['clear', 'hold', 'hold', 'block']:
        raise ValueError('native provider campaign controls did not reproduce')
    return {'schema': 'native-provider-study-v1', 'evidence_kind': 'executed_sdk_mock_transport',
            'deployment_authorized': False, 'judge_config': asdict(config),
            'runtime_versions': {'python': platform.python_version(), 'openai': version('openai'),
                                 'httpx2': version('httpx2')},
            'calibration': calibration, 'calibration_transport': transport.calls, 'controls': controls,
            'limitations': 'No network/provider calls, real credentials or money; HTTP envelopes, '
                'usage, prices, clock, reviewers and qualification policy are synthetic. Calibration '
                'and comparison scenarios overlap; all cases share one customer. The installed SDK '
                'executes requests against an in-memory handler, not a model. Four calibration '
                'requests are outside the paired campaign ledgers and retained separately. Campaign '
                'clear means pinned consistency, not invoice accuracy, snapshot freshness, semantic '
                'validity, execution attestation, current qualification or deployment authority. '
                'Admission budgets judges only, not agents, and does not cancel in-flight work.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, 'Choose a new native provider artifact path.\n')
    report = run_study()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
