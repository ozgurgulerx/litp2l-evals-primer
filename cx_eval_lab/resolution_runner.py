"""Registered paired runs for native unresolved-order tasks."""

from dataclasses import asdict
from pathlib import Path

from cx_eval_lab.artifacts import TrialArtifact
from cx_eval_lab.evidence import ExperimentManifest, PairedExperiment, canonical_hash
from cx_eval_lab.order_resolution import run_case
from cx_eval_lab.resolution_evidence import (
    DATASET, ESTIMAND, EVALUATOR, SCHEMA, case_from_dict, design, evaluate_execution,
    population_entry, validate_registration,
)
from cx_eval_lab.runner import DEFAULT_MEASUREMENT_PROFILE
from cx_eval_lab.source_provenance import capture_source_inputs
from cx_eval_lab.statistics import PairedTrial


def make_manifest(cases, baseline_agent_id, candidate_agent_id, *, repetitions=2, semantic_stage=None):
    """A synthetic teaching registration, constructed before any agent runs."""
    from cx_eval_lab import resolution_semantic as ns
    semantic = None if semantic_stage is None else semantic_stage.registration
    registration = design(baseline_agent_id, candidate_agent_id, semantic)
    return ExperimentManifest(
        experiment_id='paired-order-resolution-v1', created_at='2026-09-06T00:00:00Z',
        valid_until='2026-10-01T00:00:00Z', code_revision='working-tree-unpinned',
        model_id='deterministic-controls-no-model', prompt_version='description-matching-control-v1',
        tool_version='multi-order-mock-v1', dataset_version=DATASET,
        evaluator_version=EVALUATOR if semantic is None else ns.EVALUATOR,
        policy_version='resolution-contract-gate-v1', environment_version='python-3.12',
        population_hash=canonical_hash([population_entry(c) for c in cases]), repetitions=repetitions,
        measurement_kind='synthetic', estimand=ESTIMAND if semantic is None else ns.ESTIMAND,
        statistical_method='clustered_normal_interval',
        non_inferiority_margin=0.03, confidence_level=0.95, minimum_independent_clusters=30,
        sequential_policy='fixed_sample_no_interim_looks',
        input_hashes=(*capture_source_inputs(Path(__file__).resolve().parents[1]),
                      ('resolution-cases', canonical_hash([asdict(c) for c in cases])),
                      ('resolution-design', canonical_hash(registration)),
                      *((('native-semantic-registration', canonical_hash(semantic)),) if semantic else ())),
        invalidation_rules=('case_or_design_change', 'source_change', 'semantic_scope_not_qualified'))


def run_paired_resolution(*, cases, baseline_agent, candidate_agent, manifest,
                          measurement_profile=DEFAULT_MEASUREMENT_PROFILE, semantic_stage=None):
    cases = tuple(case_from_dict(asdict(c)) for c in cases)
    registration = design(baseline_agent.name, candidate_agent.name,
                          None if semantic_stage is None else semantic_stage.registration)
    validate_registration(manifest, cases, registration)
    kind = 'measured' if measurement_profile is None else measurement_profile.evidence_kind
    if measurement_profile is not None and kind != 'synthetic':
        raise ValueError('measured resolution runs require wall-clock and runtime evidence')
    if kind != manifest.measurement_kind:
        raise ValueError('resolution measurement profile and manifest disagree')
    trials, artifacts = {'baseline': [], 'candidate': []}, []
    agents = {'baseline': baseline_agent, 'candidate': candidate_agent}
    for index in range(manifest.repetitions):
        for case_index, case in enumerate(cases):
            # Matched permutations; counterbalanced arm execution to expose order effects.
            arms = ('candidate', 'baseline') if (case_index + index) % 2 else ('baseline', 'candidate')
            for arm in arms:
                execution = run_case(case, agents[arm], reverse=bool(index % 2))
                runtime = execution['output']['runtime_evidence']
                payload = {**execution, 'schema': SCHEMA, 'dataset_version': DATASET,
                    'design': registration, 'identity': {'case_id': case.case_id, 'trial_index': index,
                        'arm': arm, 'manifest_hash': manifest.content_hash},
                    'latency_ms': round(execution['elapsed_ms']) if measurement_profile is None
                                  else measurement_profile.latency_ms,
                    'cost_usd': (None if runtime is None else runtime['cost_usd'])
                                if measurement_profile is None else measurement_profile.cost_usd_per_case,
                    'measurement': {'evidence_kind': 'measured', 'source': 'runner wall-clock; runtime usage'}
                                   if measurement_profile is None else asdict(measurement_profile),
                    'semantic_evaluation_receipt': None, 'qualified_semantic_calibration_hashes': [],
                    'semantic_stage': None}
                result = evaluate_execution(payload)
                if semantic_stage is not None:
                    payload, result = _semantic_result(payload, result, semantic_stage, kind)
                artifact = TrialArtifact.capture({**payload, 'evaluation': result.to_dict()})
                artifacts.append(artifact)
                trials[arm].append(PairedTrial(case.case_id, index, case.request.customer_id, arm,
                    result.passed, result.latency_ms, result.cost_usd, manifest.content_hash,
                    tuple(c.name for c in result.checks if not c.passed), artifact.content_hash))
    return PairedExperiment(manifest, tuple(trials['baseline']), tuple(trials['candidate']), tuple(artifacts))


def _semantic_result(payload, structural, stage, kind):
    from cx_eval_lab.resolution_semantic import SCHEMA as NATIVE_SCHEMA
    from cx_eval_lab.resolution_semantic_replay import JointResolutionEvaluation, verify_semantics
    identity = payload['identity']
    invocation = canonical_hash([identity['manifest_hash'], identity['case_id'],
                                  identity['trial_index'], identity['arm']])
    receipt, trust, audit = stage.grade(payload, measurement_kind=kind, invocation_id=invocation)
    updated = {k: v for k, v in payload.items() if k != 'passed'}
    updated = {**updated, 'schema': NATIVE_SCHEMA, 'structural_contract_passed': structural.passed,
               'semantic_evaluation_receipt': None if receipt is None else receipt.to_dict(),
               'qualified_semantic_calibration_hashes': sorted(trust), 'semantic_stage': audit}
    result = JointResolutionEvaluation(structural, verify_semantics(updated, trust))
    return {**updated, 'semantic_message_qualified': result.to_dict()['semantic_message_qualified']}, result
