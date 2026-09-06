"""Execute a synthetic judge-budget campaign and retain complete trial evidence."""

import argparse
import hashlib
import json
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.budgeted_judge import BudgetedSemanticJudge
from cx_eval_lab.campaign_budget import CampaignLedger, CampaignPolicy
from cx_eval_lab.cost_accounting import summarize_packet_costs
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.evidence import ExperimentManifest, canonical_hash
from cx_eval_lab.models import RuntimeEvidence
from cx_eval_lab.runner import DEFAULT_MEASUREMENT_PROFILE, run_paired_experiment
from cx_eval_lab.semantic import CalibrationRecord, CalibrationRegistry, SemanticJudgment, SemanticStage
from cx_eval_lab.source_provenance import capture_source_inputs


ROOT = Path(__file__).resolve().parents[1]


class StudyAgent(ReferenceSupportAgent):
    """Exercise semantic grading after actual deterministic mock-world effects."""

    def run(self, request, tools):
        output = super().run(request, tools)
        return replace(output, message='The instruction is recorded, but arrival is not verified.',
                       message_template_id=None)


class ScriptedJudge:
    evaluator_version = 'campaign-study-fixture-v1'

    def __init__(self, unknown_second):
        self.configuration_hash = canonical_hash({'fixture': self.evaluator_version,
                                                   'unknown_second': unknown_second})
        known = SemanticJudgment('pass', 'Scripted pass; not measured semantic accuracy.',
            RuntimeEvidence('fixture', 'scripted-judge', (), 100, 20, 120, 0.00036,
                            'invented fixture price; not an invoice'), '{"kind":"synthetic"}')
        unknown = SemanticJudgment('abstain', 'Scripted timeout with unknown cost.',
                                    provider_audit_json='{"kind":"synthetic_timeout"}')
        self.responses = iter((known, unknown if unknown_second else known, known, known))

    def evaluate(self, request):
        return next(self.responses)


def _stage(judge):
    record = CalibrationRecord(judge.evaluator_version, judge.configuration_hash,
        'refund_customer_message_truth_v1', ('refund-v1',), ('refund-policy-v1',),
        (('language:en', 'risk:standard', 'journey:refund'),),
        '2026-09-01T00:00:00Z', '2026-10-01T00:00:00Z', 'synthetic',
        canonical_hash('invented calibration counts for plumbing only'),
        100, 100, 0, 0, 30, 0.05, 0.05)
    return SemanticStage(judge, CalibrationRegistry((record,)), record.content_hash,
                         clock=lambda: datetime(2026, 9, 6, tzinfo=timezone.utc), allow_synthetic=True)


def run_study(*, unknown_second=True, budget_micro_usd=1000):
    policy = CampaignPolicy('synthetic-judge-budget-v1', budget_micro_usd, 4, 2000, 600)
    dataset = ROOT / 'evals/cx-support/datasets/regression/refund_v1.json'
    cases = load_refund_cases(dataset)[:1]
    inner = ScriptedJudge(unknown_second)
    inputs = (*capture_source_inputs(ROOT),
              ('dataset', 'sha256:' + hashlib.sha256(dataset.read_bytes()).hexdigest()),
              ('campaign-policy', policy.content_hash), ('judge-config', inner.configuration_hash))
    manifest = ExperimentManifest(
        experiment_id='synthetic-judge-admission-v1', created_at='2026-09-06T00:00:00Z',
        valid_until='2026-10-01T00:00:00Z', code_revision='working-tree-unpinned',
        model_id='deterministic-reference-no-model', prompt_version='scripted-fixture',
        tool_version='typed-refund-tools-v1', dataset_version='refund-v1',
        evaluator_version='refund-evaluators-v1', policy_version='refund-gate-v1',
        environment_version='python-3.12', population_hash=canonical_hash(
            [[c.case_id, c.customer_id, list(c.slices)] for c in cases]),
        repetitions=2, measurement_kind='synthetic',
        estimand='candidate_minus_baseline_verified_success', statistical_method='clustered_normal_interval',
        non_inferiority_margin=0.03, confidence_level=0.95, minimum_independent_clusters=30,
        sequential_policy='fixed_sample_no_interim_looks', input_hashes=inputs,
        invalidation_rules=('source_or_dataset_change', 'campaign_policy_or_judge_change'))
    with tempfile.TemporaryDirectory() as temporary:
        ledger = CampaignLedger.create(Path(temporary) / 'campaign.sqlite', policy, clock_ms=lambda: 1000)
        stage = _stage(BudgetedSemanticJudge(inner, ledger))
        packet = run_paired_experiment(baseline_agent=StudyAgent(), candidate_agent=StudyAgent(),
            cases=cases, manifest=manifest, semantic_stage=stage,
            baseline_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
            candidate_measurement_profile=DEFAULT_MEASUREMENT_PROFILE).to_dict()
        snapshot = ledger.snapshot()
    costs = summarize_packet_costs(packet, trusted_calibration_hashes=frozenset({stage.calibration_hash}))
    return {'study': 'judge-campaign-admission-v1', 'evidence_kind': 'executed_synthetic_protocol',
            'deployment_authorized': False, 'synthetic_calibration_hash': stage.calibration_hash,
            'protocol': {'unknown_second': unknown_second, 'budget_micro_usd': budget_micro_usd,
                         'reservation_micro_usd': 600, 'agent_runs': 4,
                         'admission_order': 'baseline0,candidate0,baseline1,candidate1',
                         'claim': 'cost/admission demonstration, not an agent quality comparison'},
            'packet': packet, 'ledger': snapshot, 'costs': costs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, 'Choose a new artifact path.\n')
    report = run_study()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
