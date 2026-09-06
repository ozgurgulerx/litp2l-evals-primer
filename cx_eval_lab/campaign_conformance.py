"""Offline campaign/release composition controls, not deployment qualification."""

import argparse
import copy
import json
from dataclasses import asdict
from pathlib import Path

from cx_eval_lab.artifacts import TrialArtifact, replay_packet
from cx_eval_lab.campaign_budget import CampaignPolicy
from cx_eval_lab.campaign_gate import assess_campaign
from cx_eval_lab.campaign_study import run_study
from cx_eval_lab.evidence import (DeterministicTestReceipt, ExperimentManifest, PairedExperiment,
                                  PrerequisiteReceipt, build_evidence_receipt, canonical_hash)
from cx_eval_lab.statistics import PairedTrial


def _control(name, study, expected_campaign, expected_release, *, tamper=False):
    packet, original = study['packet'], study['ledger']
    # Simulated operator anchors captured before the fault injection.
    policy = CampaignPolicy(**original['policy'])
    anchors = {'packet': canonical_hash(packet), 'snapshot': canonical_hash(original)}
    snapshot = {**copy.deepcopy(original), 'known_estimate_micro_usd': 0} if tamper else original
    trust = frozenset({study['synthetic_calibration_hash']})
    results = replay_packet(packet, trusted_calibration_hashes=trust)
    assessment = assess_campaign(packet, snapshot, expected_policy=policy,
        trusted_packet_hash=anchors['packet'], trusted_snapshot_hash=anchors['snapshot'],
        trusted_calibration_hashes=trust)
    if assessment.status != expected_campaign:
        raise ValueError(f'{name}: campaign control failed')
    experiment = PairedExperiment(ExperimentManifest(**packet['manifest']),
        tuple(PairedTrial(**row) for row in packet['baseline_trials']),
        tuple(PairedTrial(**row) for row in packet['candidate_trials']),
        tuple(TrialArtifact.capture(row['payload']) for row in packet['trial_artifacts']))
    test_evidence = {'campaign_expected': expected_campaign, 'campaign_observed': assessment.status,
                     'replayed_trials': len(results)}
    receipt = build_evidence_receipt(experiment=experiment,
        deterministic_test_receipt=DeterministicTestReceipt('offline-campaign-protocol-control',
            experiment.manifest.code_revision, (('campaign_control_passed', True),
            ('four_trials_replayed', len(results) == 4)), canonical_hash(test_evidence)),
        # These fixture prerequisites isolate composition; they do not qualify a real service.
        prerequisite_receipts=tuple(PrerequisiteReceipt(key, (('synthetic_control_only', True),),
            canonical_hash({'synthetic_prerequisite': key}))
            for key in ('typed_tool_boundary', 'semantic_state_grading')),
        issued_at='2026-09-06T12:00:00Z', campaign_assessment=assessment)
    if receipt.action != expected_release or receipt.authority_ceiling != 'none':
        raise ValueError(f'{name}: combined release control failed')
    return {'name': name, 'packet': packet, 'snapshot': snapshot, 'operator_policy': asdict(policy),
            'simulated_operator_anchors': anchors, 'synthetic_calibration_hashes': sorted(trust),
            'fault_injection': 'changed snapshot after anchoring' if tamper else None,
            'assessment': asdict(assessment), 'test_evidence': test_evidence,
            'release_receipt': receipt.to_dict()}


def run_controls():
    known = run_study(unknown_second=False, budget_micro_usd=2000)
    controls = (
        _control('all-known', known, 'clear', 'hold'),
        _control('unknown-cost', run_study(), 'hold', 'block'),
        _control('reservation-overrun', run_study(reservation_micro_usd=300), 'block', 'block'),
        _control('changed-snapshot', known, 'block', 'block', tamper=True),
    )
    return {'schema': 'campaign-release-conformance-v1', 'evidence_kind': 'executed_synthetic_controls',
            'deployment_authorized': False, 'controls': list(controls),
            'limitations': 'synthetic judges/prices/calibration/prerequisites; pinned snapshot consistency '
                           'only; not current registry qualification, invoice or execution attestation'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.exit(2, 'Choose a new conformance artifact path.\n')
    report = run_controls()
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False) + '\n')


if __name__ == '__main__':
    main()
