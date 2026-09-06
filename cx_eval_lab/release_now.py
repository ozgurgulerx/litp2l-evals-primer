"""Recompute a point-in-time lab release decision from operator-owned inputs.

No cached assessment is accepted. Operator identity, clock, registry freshness,
loaded-code identity and eventual exposure control are not authenticated here.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
import json

from cx_eval_lab.artifacts import TrialArtifact
from cx_eval_lab.campaign_gate import assess_campaign
from cx_eval_lab.evidence import ExperimentManifest, PairedExperiment, build_evidence_receipt, canonical_hash
from cx_eval_lab.replay_authority import assess_replay
from cx_eval_lab.source_provenance import verify_sources
from cx_eval_lab.statistics import PairedTrial


@dataclass(frozen=True)
class CurrentReleaseDecision:
    payload_json: str

    def to_dict(self):
        payload = json.loads(self.payload_json)
        return {**payload, 'receipt_hash': canonical_hash(payload)}


def _decision(packet_hash, now, action, issues, checks):
    return CurrentReleaseDecision(json.dumps({
        'schema': 'current-release-decision-v1', 'packet_hash': packet_hash,
        'checked_at': now.isoformat(), 'action': action, 'issues': sorted(set(issues)),
        'authority_ceiling': 'none', 'deployment_authorized': False,
        'checks': checks, 'component_hashes': {key: canonical_hash(value) for key, value in checks.items()
                                             if value is not None},
        'scope': 'point-in-time local consistency; not a reusable deployment permit',
    }, sort_keys=True, allow_nan=False))


def _experiment(packet):
    return PairedExperiment(ExperimentManifest(**packet['manifest']),
        tuple(PairedTrial(**row) for row in packet['baseline_trials']),
        tuple(PairedTrial(**row) for row in packet['candidate_trials']),
        tuple(TrialArtifact.capture(row['payload']) for row in packet['trial_artifacts']))


def _chronology(packet, snapshot, now):
    observed = []
    for artifact in packet['trial_artifacts']:
        stage = artifact['payload'].get('semantic_stage') or {}
        for key in ('started_at', 'completed_at'):
            if key in stage:
                stamp = datetime.fromisoformat(stage[key].replace('Z', '+00:00'))
                if stamp.tzinfo is None or stamp.utcoffset() is None:
                    raise ValueError('aware evidence timestamp required')
                observed.append(stamp.timestamp() * 1000)
    for row in ([] if snapshot is None else snapshot['invocations']):
        timestamps = [row['admitted_ms']]
        if row['receipt_json'] is not None:
            timestamps.append(json.loads(row['receipt_json'])['completed_unix_ms'])
        if any(type(stamp) is not int or stamp < 0 for stamp in timestamps):  # noqa: E721 -- reject bool and integer subclasses
            raise ValueError('invalid campaign evidence timestamp')
        observed.extend(timestamps)
    return {'known_timestamps_checked': len(observed),
            'evidence_after_decision': any(stamp > now.timestamp() * 1000 for stamp in observed),
            'scope': 'available native semantic and campaign times; not clock authentication'}


def assess_release_now(packet, *, trusted_packet_hash, historical_calibration_hashes,
                       registry, now, root, input_files, input_values,
                       expected_revision, expected_evaluator_version,
                       deterministic_test_receipt, prerequisite_receipts,
                       campaign_policy=None, campaign_snapshot=None, trusted_snapshot_hash=None,
                       allow_synthetic=False):
    """Verify raw evidence and restrict a newly computed base release decision.

    root/input maps, expected identities, historical trust, current registry,
    campaign policy/anchors and software/prerequisite receipts are operator inputs.
    Do not source them from an untrusted uploaded packet. Re-run at use time in a
    controlled checkout; this result cannot prove later state or authorize traffic.
    """
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('release assessment requires an aware operator clock')
    if not isinstance(allow_synthetic, bool):
        raise ValueError('synthetic diagnostic permission must be explicit')
    checks: dict[str, dict | None] = {
        'source': None, 'replay': None, 'chronology': None, 'campaign': None, 'base_receipt': None}
    try:
        owned = json.loads(json.dumps(packet, allow_nan=False))
        packet_hash = canonical_hash(owned)
        experiment = _experiment(owned)
    except (ValueError, TypeError, KeyError, AttributeError):
        return _decision(None, now, 'block', ['malformed_packet'], checks)
    if packet_hash != trusted_packet_hash:
        return _decision(packet_hash, now, 'block', ['packet_anchor_mismatch'], checks)
    try:
        checks['source'] = asdict(verify_sources(experiment.manifest, root=root,
            input_files=input_files, input_values=input_values, expected_revision=expected_revision,
            expected_evaluator_version=expected_evaluator_version))
    except (ValueError, TypeError, OSError):
        return _decision(packet_hash, now, 'block', ['source_verification_failed'], checks)
    try:
        replay = assess_replay(owned, trusted_packet_hash=trusted_packet_hash,
            historical_calibration_hashes=historical_calibration_hashes, registry=registry,
            now=now, allow_synthetic=allow_synthetic)
        checks['replay'] = asdict(replay)
    except (ValueError, TypeError, KeyError, AttributeError):
        return _decision(packet_hash, now, 'block', ['historical_replay_failed'], checks)
    issues = []
    semantic_expected = any(a['payload'].get('semantic_stage') is not None
                            for a in owned['trial_artifacts'])
    if replay.calibration_status == 'not_current' or (
            semantic_expected and replay.calibration_status == 'not_applicable'):
        issues.append('current_calibration_not_current')
    if replay.unqualified_message_trials:
        issues.append('unqualified_message_evidence')
    try:
        checks['chronology'] = _chronology(owned, campaign_snapshot, now)
        if checks['chronology']['evidence_after_decision']:
            issues.append('evidence_after_decision_time')
    except (ValueError, TypeError, KeyError, AttributeError):
        issues.append('invalid_evidence_chronology')
    manifest = experiment.manifest
    created = datetime.fromisoformat(manifest.created_at.replace('Z', '+00:00'))
    expires = datetime.fromisoformat(manifest.valid_until.replace('Z', '+00:00'))
    if not created <= now < expires:
        return _decision(packet_hash, now, 'block', [*issues, 'manifest_not_current'], checks)
    campaign = None
    if 'campaign-policy' in dict(manifest.input_hashes) or campaign_snapshot is not None:
        if campaign_policy is None or campaign_snapshot is None or trusted_snapshot_hash is None:
            issues.append('campaign_inputs_missing')
        else:
            try:
                campaign = assess_campaign(owned, campaign_snapshot, expected_policy=campaign_policy,
                    trusted_packet_hash=trusted_packet_hash, trusted_snapshot_hash=trusted_snapshot_hash,
                    trusted_calibration_hashes=historical_calibration_hashes)
                checks['campaign'] = asdict(campaign)
            except (ValueError, TypeError, KeyError, AttributeError):
                issues.append('campaign_assessment_failed')
    try:
        base = build_evidence_receipt(experiment=experiment,
            deterministic_test_receipt=deterministic_test_receipt,
            prerequisite_receipts=prerequisite_receipts, issued_at=now.isoformat(),
            campaign_assessment=campaign)
        checks['base_receipt'] = base.to_dict()
    except (ValueError, TypeError, KeyError, AttributeError):
        return _decision(packet_hash, now, 'block', [*issues, 'base_receipt_failed'], checks)
    return _decision(packet_hash, now, 'block' if issues else base.action, issues, checks)
