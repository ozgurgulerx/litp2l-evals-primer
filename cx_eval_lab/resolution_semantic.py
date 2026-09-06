"""Evaluator-owned multi-order truth stage; synthetic permission is diagnostic only."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import math
import re
import time
from typing import Callable

from cx_eval_lab.evaluators import hash_customer_message, hash_structured_claims
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import AgentOutput, RuntimeEvidence, SemanticEvaluationReceipt
from cx_eval_lab.resolution_evidence import DATASET, SLICES
from cx_eval_lab.semantic import CalibrationRegistry, SemanticJudgment, SemanticRequest

CRITERION = 'multi_order_customer_message_truth_v1'
POLICY = 'multi-order-refund-policy-v1'
SCHEMA = 'resolution-trial-v2'
EVALUATOR = 'resolution-joint-v1'
ESTIMAND = 'candidate_minus_baseline_resolution_and_qualified_truth'


@dataclass(frozen=True)
class NativeScope:
    dataset_version: str = DATASET
    slices: tuple[str, ...] = SLICES


def require(condition, message):
    if not condition:
        raise ValueError(message)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, 'aware semantic time required')
    return parsed


def validate_registration(value):
    require(isinstance(value, dict) and set(value) == {'criterion', 'policy_version', 'evaluator_version',
            'configuration_hash', 'calibration_hash', 'allow_synthetic'}, 'invalid native semantic registration')
    require(value['criterion'] == CRITERION and value['policy_version'] == POLICY,
            'unsupported native semantic criterion or policy')
    require(type(value['allow_synthetic']) is bool and isinstance(value['evaluator_version'], str)
            and bool(value['evaluator_version']), 'invalid native evaluator identity or permission')
    for key in ('configuration_hash', 'calibration_hash'):
        require(isinstance(value[key], str) and re.fullmatch(r'sha256:[0-9a-f]{64}', value[key]),
                'native registration requires SHA-256 identities')


def judge_request(execution):
    # Reference labels, future scripted replies, arm, repetition and scores are deliberately absent.
    return json.loads(json.dumps({'customer_request': execution['agent_input'],
        'output': {k: v for k, v in execution['output'].items() if k != 'runtime_evidence'},
        'tool_events': execution['tool_events'], 'orders': execution['orders'],
        'execution_error': execution['execution_error'], 'policy_version': POLICY}, allow_nan=False))


def context_hash(execution):
    return canonical_hash({'schema': 'native-resolution-context-v1', 'policy_version': POLICY,
        **{key: execution[key] for key in ('case', 'agent_input', 'tool_events', 'orders', 'execution_error')}})


def receipt_for(execution, record, verdict):
    output = AgentOutput(**{k: v for k, v in execution['output'].items() if k != 'runtime_evidence'})
    return SemanticEvaluationReceipt(CRITERION, record.evaluator_version, record.content_hash,
        hash_customer_message(output.message), hash_structured_claims(output),
        verdict == 'pass', verdict == 'abstain', context_hash(execution))


def validated_judgment(data):
    require(isinstance(data, dict) and set(data) == {'verdict', 'explanation', 'runtime_evidence',
            'provider_audit_json', 'campaign_audit_json'}, 'invalid native judgment shape')
    require(isinstance(data['explanation'], str) and 1 <= len(data['explanation'].strip()) <= 4096,
            'invalid native judgment explanation')
    runtime = data['runtime_evidence']
    if runtime is not None:
        require(isinstance(runtime, dict), 'invalid native judge runtime')
        runtime = RuntimeEvidence(**runtime)
        tokens = (runtime.input_tokens, runtime.output_tokens, runtime.total_tokens)
        require(all(n is None for n in tokens) or all(type(n) is int and 0 <= n <= 10**9 for n in tokens)
                and tokens[0] + tokens[1] == tokens[2], 'invalid native judge token usage')
        require(runtime.cost_usd is None or type(runtime.cost_usd) in (int, float)
                and math.isfinite(runtime.cost_usd) and 0 <= runtime.cost_usd <= 10**6,
                'invalid native judge cost')
        require(all(isinstance(s, str) and s for s in (runtime.provider, runtime.model_id, runtime.cost_source))
                and isinstance(runtime.response_ids, (list, tuple))
                and all(isinstance(s, str) and s for s in runtime.response_ids), 'invalid native runtime identity')
    for key in ('provider_audit_json', 'campaign_audit_json'):
        require(data[key] is None or isinstance(data[key], str), 'invalid native audit encoding')
        if data[key] is not None:
            require(isinstance(json.loads(data[key]), dict), 'native provider audit must be an object')
    json.dumps(data, allow_nan=False)
    return SemanticJudgment(**{**data, 'runtime_evidence': runtime})


def rejection(record, judge, now, *, measurement_kind, allow_synthetic):
    return record.rejection(judge, NativeScope(), POLICY, now,
        allow_synthetic and measurement_kind == 'synthetic', criterion_id=CRITERION)


@dataclass(frozen=True)
class ResolutionSemanticStage:
    judge: object
    registry: CalibrationRegistry
    calibration_hash: str
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    allow_synthetic: bool = False

    def __post_init__(self):
        require(isinstance(self.registry, CalibrationRegistry), 'operator-owned calibration registry required')
        validate_registration(self.registration)

    @property
    def registration(self):
        return {'criterion': CRITERION, 'policy_version': POLICY,
                'evaluator_version': self.judge.evaluator_version,
                'configuration_hash': self.judge.configuration_hash,
                'calibration_hash': self.calibration_hash, 'allow_synthetic': self.allow_synthetic}

    def grade(self, execution, *, measurement_kind, invocation_id):
        require(measurement_kind in {'synthetic', 'measured'}, 'explicit semantic measurement kind required')
        require(isinstance(invocation_id, str) and invocation_id, 'native invocation identity required')
        # Own the evidence snapshot before handing any data to an external evaluator.
        execution = json.loads(json.dumps(execution, allow_nan=False))
        started = timestamp(self.clock().isoformat())
        record = self.registry.lookup(self.calibration_hash)
        reason = 'qualification_missing_or_revoked' if record is None else rejection(
            record, self.judge, started, measurement_kind=measurement_kind, allow_synthetic=self.allow_synthetic)
        audit = {'status': 'unqualified', 'reason': reason, 'registration': self.registration,
                 'invocation_id': invocation_id, 'started_at': started.isoformat()}
        if reason:
            return None, frozenset(), audit
        request = SemanticRequest(json.dumps(judge_request(execution), sort_keys=True, allow_nan=False),
                                  CRITERION, invocation_id)
        began = time.perf_counter()
        try:
            judgment = self.judge.evaluate(request)
            require(isinstance(judgment, SemanticJudgment), 'invalid native judgment')
            judgment = validated_judgment(asdict(judgment))
        except Exception as error:
            judgment = SemanticJudgment('abstain', f'judge_error:{type(error).__name__}')
        completed = timestamp(self.clock().isoformat())
        reason = 'semantic_clock_regression' if completed < started else rejection(
            record, self.judge, completed, measurement_kind=measurement_kind, allow_synthetic=self.allow_synthetic)
        audit = {**audit, 'status': 'unqualified' if reason else 'graded', 'reason': reason,
                 'completed_at': completed.isoformat(), 'qualification': asdict(record),
                 'request': json.loads(request.evidence_json), 'request_hash': canonical_hash(judge_request(execution)),
                 'judgment': asdict(judgment), 'judge_latency_ms': round((time.perf_counter() - began) * 1000),
                 'error_bounds': record.error_bounds, 'authority': 'lab_only'}
        if reason:
            return None, frozenset(), audit
        return receipt_for(execution, record, judgment.verdict), frozenset({record.content_hash}), audit
