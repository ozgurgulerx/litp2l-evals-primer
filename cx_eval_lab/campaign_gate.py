"""Pinned, dedicated-packet campaign checks; not latest-state or billing proof.

External anchors and operator policy are required. This validates retained
records, not historical admission ordering, execution provenance, or invoices.
"""

import json
import re
from dataclasses import asdict, dataclass, field

from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.campaign_budget import CampaignPolicy, MAX_MONEY, usd_to_micro
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import RefundCase
from cx_eval_lab.semantic import CRITERION


@dataclass(frozen=True)
class CampaignAssessment:
    packet_hash: str
    snapshot_hash: str
    policy_hash: str
    status: str
    issues: tuple[str, ...]
    matched_invocations: int = 0
    known_estimate_micro_usd: int | None = None
    held_reservations_micro_usd: int | None = None
    deployment_authorized: bool = field(default=False, init=False)

    @property
    def content_hash(self):
        return canonical_hash(asdict(self))


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _int(value, maximum=MAX_MONEY):
    _require(type(value) is int and 0 <= value <= maximum, 'invalid_campaign_integer')
    return value


def _digest(value):
    _require(isinstance(value, str) and re.fullmatch(r'sha256:[0-9a-f]{64}', value),
             'invalid_campaign_digest')


def _unique(pairs):
    _require(len(pairs) == len({key for key, _ in pairs}), 'duplicate_campaign_json_keys')
    return dict(pairs)


def _object(encoded):
    _require(isinstance(encoded, str) and len(encoded.encode('utf-8')) <= 2_000_000,
             'invalid_campaign_json')
    result = json.loads(encoded, object_pairs_hook=_unique)
    _require(isinstance(result, dict), 'campaign_json_object_required')
    json.dumps(result, allow_nan=False)
    return result


def _row(row, policy, issues):
    _require(isinstance(row['id'], str) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,256}', row['id']),
             'invalid_invocation_id')
    _digest(row['request_hash'])
    _digest(row['configuration_hash'])
    _require(_int(row['reserved_micro']) == policy.reservation_micro_usd, 'reservation_policy_mismatch')
    admitted = _int(row['admitted_ms'], 2**53)
    if admitted >= policy.deadline_unix_ms:
        issues.add('deadline_violation')
    _require(row['state'] in {'reserved', 'known', 'unknown'}, 'invalid_invocation_state')
    if row['state'] == 'reserved':
        _require(all(row[key] is None for key in ('estimate_micro', 'judgment_json', 'receipt_json')),
                 'pending_invocation_has_final_evidence')
        return
    if row['state'] == 'known':
        _int(row['estimate_micro'])
    else:
        _require(row['estimate_micro'] is None, 'unknown_cost_has_estimate')
    judgment, receipt = _object(row['judgment_json']), _object(row['receipt_json'])
    runtime = judgment.get('runtime_evidence') or {}
    _require(usd_to_micro(runtime.get('cost_usd')) == row['estimate_micro'], 'judgment_cost_mismatch')
    completed = _int(receipt['completed_unix_ms'], 2**53)
    _require(completed >= admitted, 'completion_precedes_admission')
    overrun = row['estimate_micro'] is not None and row['estimate_micro'] > row['reserved_micro']
    expected = {'schema': 'judge-campaign-receipt-v1', 'invocation_id': row['id'],
        'campaign_policy_hash': policy.content_hash, 'request_hash': row['request_hash'],
        'configuration_hash': row['configuration_hash'], 'reserved_micro_usd': row['reserved_micro'],
        'estimate_micro_usd': row['estimate_micro'], 'state': row['state'],
        'judgment_hash': canonical_hash(judgment), 'completed_unix_ms': completed,
        'reservation_overrun': overrun, 'completed_after_deadline': completed >= policy.deadline_unix_ms}
    _require(canonical_hash(receipt) == canonical_hash(expected), 'campaign_receipt_mismatch')
    if overrun:
        issues.add('reservation_overrun')
    if completed >= policy.deadline_unix_ms:
        issues.add('deadline_violation')


def _snapshot(snapshot, policy, issues):
    _require(snapshot['schema'] == 'judge-campaign-snapshot-v1', 'unsupported_campaign_snapshot')
    _require(snapshot['deployment_authorized'] is False, 'campaign_authority_escalation')
    _require(CampaignPolicy(**snapshot['policy']) == policy and snapshot['policy_hash'] == policy.content_hash,
             'campaign_policy_mismatch')
    rows = snapshot['invocations']
    _require(isinstance(rows, list) and len(rows) <= 1_000_000, 'invalid_campaign_inventory')
    for row in rows:
        _row(row, policy, issues)
    _require(len({row['id'] for row in rows}) == len(rows), 'duplicate_campaign_invocation')
    known = sum(row['estimate_micro'] for row in rows if row['state'] == 'known')
    held = sum(row['reserved_micro'] for row in rows if row['state'] != 'known')
    unknown = sum(row['state'] != 'known' for row in rows)
    expected = {'admissions': len(rows), 'known_estimate_micro_usd': known,
                'held_reservations_micro_usd': held, 'committed_micro_usd': known + held,
                'unknown_or_pending_invocations': unknown}
    for key, value in expected.items():
        _require(_int(snapshot[key], MAX_MONEY * 1_000_000) == value, 'campaign_summary_mismatch')
    total = snapshot['complete_estimate_micro_usd']
    _require(total is None if unknown else type(total) is int and total == known,
             'campaign_total_mismatch')
    halt = snapshot['halt_reason']
    _require(halt in {None, 'reservation_overrun', 'deadline_reached', 'clock_regression'},
             'unknown_campaign_halt')
    if halt:
        issues.add(halt)
    if unknown:
        issues.add('unknown_or_pending_cost')
    if len(rows) > policy.max_admissions:
        issues.add('admission_limit_exceeded')
    if known + held > policy.max_estimated_micro_usd:
        issues.add('estimated_budget_exceeded')
    return {row['id']: row for row in rows}, known, held


def _execution_request(payload):
    case = RefundCase.from_dict(payload['case'])
    return {'customer_request': asdict(case.agent_input),
            'output': {key: value for key, value in payload['output'].items() if key != 'runtime_evidence'},
            'events': payload['events'], 'final_state': payload['final_state'],
            'policy_version': payload['policy_version'], 'execution_error': payload['execution_error'],
            'authoritative_order': {'amount_cents': case.amount_cents, 'currency': case.currency,
                'eligible': case.eligible, 'approval_threshold_cents': case.approval_threshold_cents}}


def _join(payload, row, identifier, policy, issues, trusted_calibration_hashes, registered_configuration):
    stage = payload.get('semantic_stage') or {}
    if not stage.get('judgment') or not stage['judgment'].get('campaign_audit_json'):
        issues.add('campaign_judgment_missing')
        return
    _require(stage['invocation_id'] == identifier, 'packet_invocation_mismatch')
    expected_request = canonical_hash(_execution_request(payload))
    _require(canonical_hash(stage['request']) == expected_request and stage['request_hash'] == expected_request,
             'judge_request_differs_from_execution')
    qualification_hash = canonical_hash(stage['qualification'])
    _require(qualification_hash in trusted_calibration_hashes, 'campaign_qualification_not_trusted')
    receipt = payload['semantic_evaluation_receipt']
    verdict = stage['judgment']['verdict']
    _require(verdict in {'pass', 'fail', 'abstain'}, 'invalid_campaign_judge_verdict')
    if receipt is not None:
        _require(stage['status'] == 'graded' and stage['reason'] is None
                 and receipt['passed'] is (verdict == 'pass')
                 and receipt['abstained'] is (verdict == 'abstain'), 'campaign_judgment_receipt_mismatch')
        _require(qualification_hash == receipt['calibration_receipt_hash']
                 and receipt['evaluator_version'] == stage['qualification']['evaluator_version']
                 and receipt['criterion_id'] == stage['qualification']['criterion_id'] == CRITERION,
                 'campaign_qualification_receipt_mismatch')
    else:
        _require(stage['status'] == 'unqualified' and stage['reason'], 'missing_semantic_receipt')
        issues.add('semantic_qualification_missing')
    request_hash = canonical_hash({'criterion': CRITERION, 'evidence': stage['request']})
    configuration = stage['qualification']['configuration_hash']
    _require(registered_configuration is None or configuration == registered_configuration,
             'registered_judge_configuration_mismatch')
    if row is not None:
        _require(row['request_hash'] == request_hash and row['configuration_hash'] == configuration,
                 'packet_campaign_evidence_mismatch')
    audit = _object(stage['judgment']['campaign_audit_json'])
    admission = audit.get('admission')
    if admission:
        _require(admission['invocation_id'] == identifier
                 and admission['campaign_policy_hash'] == policy.content_hash
                 and type(admission['admitted']) is bool, 'campaign_admission_mismatch')
    if audit['status'] == 'recorded':
        _require(row is not None and row['state'] != 'reserved' and admission['admitted'] is True,
                 'recorded_judgment_without_finalized_reservation')
        _require(admission['reason'] == 'reserved', 'recorded_admission_reason_mismatch')
        _require(canonical_hash(audit['receipt']) == canonical_hash(_object(row['receipt_json'])),
                 'packet_campaign_receipt_mismatch')
        inner = {**stage['judgment'], 'campaign_audit_json': None}
        _require(canonical_hash(inner) == canonical_hash(_object(row['judgment_json'])),
                 'packet_campaign_judgment_mismatch')
    elif audit['status'] == 'abstained':
        _require(audit['campaign_policy_hash'] == policy.content_hash, 'campaign_policy_mismatch')
        reason = audit['reason']
        if reason == 'campaign_finalization_error':
            _require(row is not None and admission['admitted'] is True, 'finalization_without_reservation')
            issues.add('campaign_finalization_unconfirmed')
        else:
            _require(reason == 'campaign_admission_error' or admission['admitted'] is False,
                     'invalid_admission_denial')
            issues.add('judge_admission_denied')
    else:
        raise ValueError('unknown_campaign_audit_status')


def assess_campaign(packet, snapshot, *, expected_policy, trusted_packet_hash,
                    trusted_snapshot_hash, trusted_calibration_hashes=frozenset()):
    """Check a dedicated campaign snapshot against one fully retained packet.

    A changed/contradictory record blocks. Unknown/pending/denied work holds.
    Clear means accounting consistency only, not current calibration or release.
    """
    _require(isinstance(expected_policy, CampaignPolicy), 'operator_campaign_policy_required')
    packet_hash, snapshot_hash = '', ''
    try:
        json.dumps([packet, snapshot], allow_nan=False)
        packet_hash, snapshot_hash = canonical_hash(packet), canonical_hash(snapshot)
        _digest(trusted_packet_hash)
        _digest(trusted_snapshot_hash)
        _require(packet_hash == trusted_packet_hash, 'campaign_packet_anchor_mismatch')
        _require(snapshot_hash == trusted_snapshot_hash, 'campaign_snapshot_anchor_mismatch')
        replay_packet(packet, trusted_calibration_hashes=trusted_calibration_hashes)
        _require(dict(packet['manifest']['input_hashes']).get('campaign-policy') == expected_policy.content_hash,
                 'campaign_policy_not_registered')
        issues = set()
        rows, known, held = _snapshot(snapshot, expected_policy, issues)
        expected = {}
        for artifact in packet['trial_artifacts']:
            payload = artifact['payload']
            identity = payload['identity']
            identifier = canonical_hash([identity['manifest_hash'], identity['case_id'],
                                         identity['trial_index'], identity['arm']])
            expected[identifier] = payload
            _join(payload, rows.get(identifier), identifier, expected_policy, issues, trusted_calibration_hashes,
                  dict(packet['manifest']['input_hashes']).get('judge-config'))
        _require(set(rows).issubset(expected), 'foreign_campaign_invocations')
        hard = {'reservation_overrun', 'deadline_reached', 'deadline_violation', 'clock_regression',
                'admission_limit_exceeded', 'estimated_budget_exceeded'}
        status = 'block' if issues & hard else 'hold' if issues else 'clear'
        return CampaignAssessment(packet_hash, snapshot_hash, expected_policy.content_hash, status,
                                  tuple(sorted(issues)), len(rows), known, held)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        reason = str(error) if isinstance(error, ValueError) else 'malformed_campaign_evidence'
        return CampaignAssessment(packet_hash, snapshot_hash, expected_policy.content_hash,
                                  'block', (reason,))
