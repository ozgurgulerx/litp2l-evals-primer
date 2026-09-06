"""Anchored historical replay plus a separate current-calibration assessment.

The caller owns the packet anchor, historical trust and current registry. This
module authenticates none of them and never authorizes application deployment.
It uses the installed grader; source/version attestation is a separate boundary.
"""

from dataclasses import dataclass, field
from datetime import datetime
from types import SimpleNamespace

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import RefundCase
from cx_eval_lab.semantic import CalibrationRegistry


@dataclass(frozen=True)
class ReplayAssessment:
    packet_hash: str
    registry_hash: str
    historical_trust_hash: str
    synthetic_diagnostic: bool
    checked_at: str
    replayed_trials: int
    failed_trials: int
    unqualified_message_trials: int
    semantic_trials: int
    calibration_status: str
    issues: tuple[str, ...]
    deployment_authorized: bool = field(default=False, init=False)


def _current_rejection(payload, registry, now, allow_synthetic):
    receipt = payload['semantic_evaluation_receipt']
    record = registry.lookup(receipt['calibration_receipt_hash'])
    if record is None:
        return 'qualification_missing_or_revoked'
    audit = payload.get('semantic_stage')
    if not isinstance(audit, dict) or not isinstance(audit.get('qualification'), dict):
        return 'qualification_audit_missing'
    if canonical_hash(audit['qualification']) != record.content_hash:
        return 'qualification_audit_mismatch'
    if (receipt['evaluator_version'] != record.evaluator_version
            or receipt['criterion_id'] != record.criterion_id):
        return 'evaluator_configuration_mismatch'
    judge = SimpleNamespace(evaluator_version=receipt['evaluator_version'],
                            configuration_hash=audit['qualification'].get('configuration_hash'))
    return record.rejection(judge, RefundCase.from_dict(payload['case']),
                            payload['policy_version'], now, allow_synthetic)


def assess_replay(packet, *, trusted_packet_hash, historical_calibration_hashes,
                  registry, now, allow_synthetic=False):
    """Reproduce historical grades, then check present calibration eligibility.

    Invalid reproduction raises ValueError. Revocation/expiry instead produces
    a separate not_current result, preserving the original packet and grades.
    allow_synthetic is a diagnostic override, never deployment authority.
    """
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('current assessment requires an aware operator clock')
    if type(allow_synthetic) is not bool or not isinstance(registry, CalibrationRegistry):
        raise ValueError('invalid current registry or synthetic permission')
    digest = canonical_hash(packet)
    if digest != trusted_packet_hash:
        raise ValueError('packet differs from independently trusted packet hash')
    results = replay_packet(packet, trusted_calibration_hashes=historical_calibration_hashes)
    issues, semantic_trials = [], 0
    for artifact in packet['trial_artifacts']:
        payload = artifact['payload']
        if payload['semantic_evaluation_receipt'] is None:
            continue
        semantic_trials += 1
        reason = _current_rejection(payload, registry, now, allow_synthetic)
        if reason:
            issues.append(f"{artifact['artifact_hash']}:{reason}")
    registry_hash = canonical_hash({
        'records': sorted(record.content_hash for record in registry.records),
        'revoked_hashes': sorted(registry.revoked_hashes),
    })
    status = 'not_applicable' if not semantic_trials else 'not_current' if issues else 'current'
    return ReplayAssessment(
        packet_hash=digest, registry_hash=registry_hash,
        historical_trust_hash=canonical_hash(sorted(historical_calibration_hashes)),
        synthetic_diagnostic=allow_synthetic, checked_at=now.isoformat(),
        replayed_trials=len(results), semantic_trials=semantic_trials,
        failed_trials=sum(not result.passed for result in results),
        unqualified_message_trials=sum(result.unqualified_message_count > 0 for result in results),
        calibration_status=status, issues=tuple(issues))
