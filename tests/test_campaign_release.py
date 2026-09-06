"""Campaign consistency is independent of statistical release evidence."""

import unittest
from dataclasses import replace

from cx_eval_lab.artifacts import TrialArtifact
from cx_eval_lab.campaign_budget import CampaignPolicy
from cx_eval_lab.campaign_gate import assess_campaign
from cx_eval_lab.campaign_study import run_study
from cx_eval_lab.evidence import (DeterministicTestReceipt, ExperimentManifest, PairedExperiment,
                                  PrerequisiteReceipt, build_evidence_receipt, canonical_hash)
from cx_eval_lab.statistics import PairedTrial


def experiment_from_packet(packet):
    return PairedExperiment(ExperimentManifest(**packet['manifest']),
        tuple(PairedTrial(**row) for row in packet['baseline_trials']),
        tuple(PairedTrial(**row) for row in packet['candidate_trials']),
        tuple(TrialArtifact.capture(row['payload']) for row in packet['trial_artifacts']))


def campaign_assessment(report):
    return assess_campaign(report['packet'], report['ledger'],
        expected_policy=CampaignPolicy(**report['ledger']['policy']),
        trusted_packet_hash=canonical_hash(report['packet']),
        trusted_snapshot_hash=canonical_hash(report['ledger']),
        trusted_calibration_hashes=frozenset({report['synthetic_calibration_hash']}))


def release_receipt(report, assessment):
    experiment = experiment_from_packet(report['packet'])
    return build_evidence_receipt(experiment=experiment,
        deterministic_test_receipt=DeterministicTestReceipt('synthetic-join-control',
            experiment.manifest.code_revision, (('fixture_test', True),), canonical_hash('synthetic test receipt')),
        prerequisite_receipts=tuple(PrerequisiteReceipt(name, (('fixture_contract', True),), canonical_hash(name))
            for name in ('typed_tool_boundary', 'semantic_state_grading')),
        issued_at='2026-09-06T12:00:00Z', campaign_assessment=assessment)


class CampaignReleaseTests(unittest.TestCase):
    def setUp(self):
        self.report = run_study(unknown_second=False, budget_micro_usd=2000)

    def test_clear_campaign_cannot_override_statistical_inconclusiveness(self):
        receipt = release_receipt(self.report, campaign_assessment(self.report))
        self.assertEqual('clear', receipt.to_dict()['campaign_check']['status'])
        self.assertEqual('inconclusive', receipt.comparison.status)
        self.assertEqual('hold', receipt.action)
        self.assertEqual('none', receipt.authority_ceiling)

    def test_declared_campaign_without_assessment_is_held_not_unchecked(self):
        receipt = release_receipt(self.report, None)
        self.assertEqual('hold', receipt.action)
        self.assertEqual(['campaign_assessment_missing'], receipt.to_dict()['campaign_check']['issues'])

    def test_campaign_block_overrides_otherwise_inconclusive_quality(self):
        self.report['ledger']['known_estimate_micro_usd'] = 0
        assessment = campaign_assessment(self.report)
        receipt = release_receipt(self.report, assessment)
        self.assertEqual('block', receipt.action)
        self.assertEqual('none', receipt.authority_ceiling)
        self.assertIn(('campaign_check', canonical_hash(receipt.to_dict()['campaign_check'])), receipt.component_hashes)

    def test_assessment_for_other_packet_or_policy_cannot_be_reused(self):
        assessment = campaign_assessment(self.report)
        for changes in ({'packet_hash': canonical_hash('other')}, {'policy_hash': canonical_hash('other')}):
            with self.assertRaises(ValueError):
                release_receipt(self.report, replace(assessment, **changes))

    def test_legacy_receipt_explicitly_says_campaign_not_checked(self):
        from tests.test_evidence_spine import make_receipt
        receipt = make_receipt()
        self.assertEqual('not_checked', receipt.to_dict()['campaign_check']['status'])
        self.assertEqual('lab_pass', receipt.action)


if __name__ == '__main__':
    unittest.main()
