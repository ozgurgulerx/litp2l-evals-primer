"""Native semantic receipt verification, separate from judge execution."""

from dataclasses import asdict, dataclass
from types import SimpleNamespace

from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import CheckResult
from cx_eval_lab.resolution_semantic import (
    EVALUATOR, judge_request, receipt_for, rejection, require, timestamp, validate_registration,
    validated_judgment,
)
from cx_eval_lab.semantic import CalibrationRecord


@dataclass(frozen=True)
class SemanticStatus:
    qualified: bool
    passed: bool
    abstained: bool
    reason: str | None


def _audit(payload, registration):
    audit = payload['semantic_stage']
    require(isinstance(audit, dict) and audit.get('registration') == registration,
            'native semantic audit registration mismatch')
    base = {'status', 'reason', 'registration', 'invocation_id', 'started_at'}
    full = base | {'completed_at', 'qualification', 'request', 'request_hash', 'judgment',
                   'judge_latency_ms', 'error_bounds', 'authority'}
    require(set(audit) in (base, full), 'native audit must distinguish predispatch from completed call')
    started = timestamp(audit['started_at'])
    if set(audit) == base:
        require(audit['status'] == 'unqualified' and isinstance(audit['reason'], str) and audit['reason'],
                'predispatch rejection requires an explanation')
        return None, None, audit['reason']
    require(type(audit['judge_latency_ms']) is int and audit['judge_latency_ms'] >= 0
            and audit['authority'] == 'lab_only', 'invalid native audit latency or authority')
    record = CalibrationRecord(**audit['qualification'])
    require(record.content_hash == registration['calibration_hash'], 'native qualification hash mismatch')
    request = judge_request(payload)
    require(canonical_hash(audit['request']) == canonical_hash(request)
            and audit['request_hash'] == canonical_hash(request), 'native semantic request differs from execution')
    judgment = validated_judgment(audit['judgment'])
    require(canonical_hash(audit['error_bounds']) == canonical_hash(record.error_bounds),
            'native calibration bounds mismatch')
    judge = SimpleNamespace(evaluator_version=registration['evaluator_version'],
                            configuration_hash=registration['configuration_hash'])
    args = dict(measurement_kind=payload['measurement']['evidence_kind'],
                allow_synthetic=registration['allow_synthetic'])
    require(rejection(record, judge, started, **args) is None, 'native dispatch began outside qualified scope')
    completed = timestamp(audit['completed_at'])
    reason = 'semantic_clock_regression' if completed < started else rejection(record, judge, completed, **args)
    require(audit['reason'] == reason and audit['status'] == ('unqualified' if reason else 'graded'),
            'native postdispatch qualification status mismatch')
    return record, judgment, reason


def verify_semantics(payload, trusted_calibration_hashes):
    registration = payload['design']['semantic_qualification']
    validate_registration(registration)
    record, judgment, reason = _audit(payload, registration)
    audit = payload['semantic_stage']
    identity = payload['identity']
    expected_id = canonical_hash([identity['manifest_hash'], identity['case_id'],
                                  identity['trial_index'], identity['arm']])
    require(audit.get('invocation_id') == expected_id, 'native semantic invocation mismatch')
    receipt = payload['semantic_evaluation_receipt']
    accepted = payload['qualified_semantic_calibration_hashes']
    if receipt is None:
        require(accepted == [] and reason is not None, 'missing native qualification reason')
        return SemanticStatus(False, False, False, reason)
    require(accepted == [registration['calibration_hash']]
            and registration['calibration_hash'] in trusted_calibration_hashes,
            'native replay requires independently trusted calibration')
    require(reason is None and record is not None and judgment is not None, 'native graded status mismatch')
    require(canonical_hash(receipt) == canonical_hash(receipt_for(payload, record, judgment.verdict).to_dict()),
            'native semantic receipt or verdict mismatch')
    return SemanticStatus(True, judgment.verdict == 'pass', judgment.verdict == 'abstain', None)


@dataclass(frozen=True)
class JointResolutionEvaluation:
    structural: object
    semantic: SemanticStatus

    @property
    def case_id(self):
        return self.structural.case_id

    @property
    def task_completed(self):
        return self.structural.task_completed

    @property
    def latency_ms(self):
        return self.structural.latency_ms

    @property
    def cost_usd(self):
        return self.structural.cost_usd

    @property
    def unqualified_message_count(self):
        return int(not self.semantic.qualified)

    @property
    def passed(self):
        return self.structural.passed and self.semantic.qualified and self.semantic.passed

    @property
    def checks(self):
        return (*self.structural.checks, CheckResult('qualified_multi_order_message',
            self.semantic.qualified and self.semantic.passed,
            self.semantic.reason or ('abstain' if self.semantic.abstained else
                                     'pass' if self.semantic.passed else 'fail')))

    def to_dict(self):
        return {**self.structural.to_dict(), 'criterion': EVALUATOR,
                'structural_contract_passed': self.structural.passed,
                'checks': [c.to_dict() for c in self.checks], 'passed': self.passed,
                'semantic_status': asdict(self.semantic),
                'semantic_message_qualified': self.semantic.qualified and not self.semantic.abstained,
                'unqualified_message_count': self.unqualified_message_count,
                'semantic_abstention_count': int(self.semantic.abstained)}


def current_rejection(payload, registry, now, allow_synthetic):
    receipt, audit = payload['semantic_evaluation_receipt'], payload['semantic_stage']
    record = registry.lookup(receipt['calibration_receipt_hash'])
    if record is None:
        return 'qualification_missing_or_revoked'
    if canonical_hash(audit['qualification']) != record.content_hash:
        return 'qualification_audit_mismatch'
    registration = payload['design']['semantic_qualification']
    judge = SimpleNamespace(evaluator_version=registration['evaluator_version'],
                            configuration_hash=registration['configuration_hash'])
    return rejection(record, judge, now, measurement_kind=payload['measurement']['evidence_kind'],
                     allow_synthetic=allow_synthetic)
