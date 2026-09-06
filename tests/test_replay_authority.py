"""Historical reproduction is distinct from present calibration eligibility."""

import copy
import unittest
from dataclasses import replace
from datetime import datetime

from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.runner import run_paired_experiment, DEFAULT_MEASUREMENT_PROFILE
from cx_eval_lab.semantic import CalibrationRegistry
from tests.test_evidence_spine import make_manifest
from tests.test_semantic_stage import FreeFormReference, setup_stage, NOW


class ReplayAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.stage = setup_stage()
        cases = load_refund_cases('evals/cx-support/datasets/regression/refund_v1.json')[:1]
        self.packet = run_paired_experiment(
            baseline_agent=FreeFormReference(), candidate_agent=FreeFormReference(),
            cases=cases, manifest=replace(make_manifest(), population_hash=canonical_hash(
                [[c.case_id, c.customer_id, list(c.slices)] for c in cases])),
            baseline_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
            candidate_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
            semantic_stage=self.stage,
        ).to_dict()
        self.anchor = canonical_hash(self.packet)

    def assess(self, **kwargs):
        from cx_eval_lab.replay_authority import assess_replay
        return assess_replay(
            kwargs.pop('packet', self.packet), trusted_packet_hash=self.anchor,
            historical_calibration_hashes=frozenset({self.stage.calibration_hash}),
            registry=kwargs.pop('registry', self.stage.registry), now=kwargs.pop('now', NOW),
            **kwargs,
        )

    def test_current_synthetic_check_is_explicitly_lab_only(self):
        result = self.assess(allow_synthetic=True)
        self.assertEqual('current', result.calibration_status)
        self.assertEqual(4, result.replayed_trials)
        self.assertEqual(4, result.semantic_trials)
        self.assertFalse(result.deployment_authorized)
        self.assertEqual(self.anchor, result.packet_hash)
        self.assertTrue(result.synthetic_diagnostic)
        self.assertEqual(canonical_hash([self.stage.calibration_hash]), result.historical_trust_hash)
        self.assertEqual([], list(result.issues))

    def test_revocation_does_not_rewrite_historical_grade(self):
        original = copy.deepcopy(self.packet)
        result = self.assess(registry=CalibrationRegistry(
            self.stage.registry.records, frozenset({self.stage.calibration_hash})))
        self.assertEqual('not_current', result.calibration_status)
        self.assertEqual(4, result.replayed_trials)
        self.assertTrue(all('missing_or_revoked' in issue for issue in result.issues))
        self.assertEqual(original, self.packet)

    def test_expiry_and_synthetic_default_cannot_be_current(self):
        synthetic = self.assess()
        self.assertTrue(all('synthetic_qualification_not_permitted' in i for i in synthetic.issues))
        expired = self.assess(now=NOW.replace(month=10), allow_synthetic=True)
        self.assertTrue(all('qualification_not_current' in i for i in expired.issues))

    def test_unknown_registry_and_missing_historical_trust_fail_separately(self):
        result = self.assess(registry=CalibrationRegistry(()))
        self.assertEqual('not_current', result.calibration_status)
        from cx_eval_lab.replay_authority import assess_replay
        with self.assertRaisesRegex(ValueError, 'independently trusted'):
            assess_replay(self.packet, trusted_packet_hash=self.anchor,
                          historical_calibration_hashes=frozenset(),
                          registry=self.stage.registry, now=NOW)

    def test_external_anchor_rejects_even_self_consistent_rewrites(self):
        changed = {**self.packet, 'operator_note': 'A coherently altered packet'}
        with self.assertRaisesRegex(ValueError, 'trusted packet'):
            self.assess(packet=changed)

    def test_invalid_operator_clock_and_synthetic_flag_are_rejected(self):
        for kwargs in ({'now': datetime(2026, 9, 6)}, {'now': 'yesterday'},
                       {'allow_synthetic': 'yes'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.assess(**kwargs)

    def test_replayable_audit_mismatch_is_not_current_authority(self):
        from cx_eval_lab.artifacts import _regrade
        for change, expected in (
            (lambda p: p.update(semantic_stage=None), 'qualification_audit_missing'),
            (lambda p: p['semantic_stage']['qualification'].update(
                configuration_hash=canonical_hash('changed')), 'qualification_audit_mismatch'),
            (lambda p: p['semantic_evaluation_receipt'].update(
                evaluator_version='unregistered'), 'evaluator_configuration_mismatch'),
        ):
            with self.subTest(expected=expected):
                packet = copy.deepcopy(self.packet)
                for artifact in packet['trial_artifacts']:
                    old = artifact['artifact_hash']
                    payload = artifact['payload']
                    change(payload)
                    # Construct a historically self-consistent fixture, then anchor it.
                    payload['evaluation'] = _regrade(
                        payload, frozenset({self.stage.calibration_hash})).to_dict()
                    artifact['artifact_hash'] = canonical_hash(payload)
                    for row in packet['baseline_trials'] + packet['candidate_trials']:
                        if row['artifact_hash'] == old:
                            row['artifact_hash'] = artifact['artifact_hash']
                from cx_eval_lab.replay_authority import assess_replay
                result = assess_replay(
                    packet, trusted_packet_hash=canonical_hash(packet),
                    historical_calibration_hashes=frozenset({self.stage.calibration_hash}),
                    registry=self.stage.registry, now=NOW, allow_synthetic=True)
                self.assertEqual('not_current', result.calibration_status)
                self.assertTrue(all(expected in issue for issue in result.issues))

    def test_no_semantic_receipts_is_not_a_calibration_pass(self):
        from tests.test_trial_replay import TrialReplayTests
        from cx_eval_lab.replay_authority import assess_replay
        packet = TrialReplayTests().packet()
        result = assess_replay(
            packet, trusted_packet_hash=canonical_hash(packet),
            historical_calibration_hashes=frozenset(), registry=CalibrationRegistry(()), now=NOW)
        self.assertEqual('not_applicable', result.calibration_status)
        self.assertEqual(0, result.semantic_trials)
        self.assertFalse(result.deployment_authorized)

    def test_current_calibration_does_not_hide_invalid_receipts_or_failed_grades(self):
        from cx_eval_lab.artifacts import _regrade
        from cx_eval_lab.replay_authority import assess_replay
        packet = copy.deepcopy(self.packet)
        for artifact in packet['trial_artifacts']:
            old = artifact['artifact_hash']
            payload = artifact['payload']
            payload['semantic_evaluation_receipt']['evidence_context_hash'] = canonical_hash('wrong')
            result = _regrade(payload, frozenset({self.stage.calibration_hash}))
            payload['evaluation'] = result.to_dict()
            artifact['artifact_hash'] = canonical_hash(payload)
            for row in packet['baseline_trials'] + packet['candidate_trials']:
                if row['artifact_hash'] == old:
                    row.update(artifact_hash=artifact['artifact_hash'], passed=result.passed,
                               failed_checks=[c.name for c in result.checks if not c.passed])
        assessment = assess_replay(
            packet, trusted_packet_hash=canonical_hash(packet),
            historical_calibration_hashes=frozenset({self.stage.calibration_hash}),
            registry=self.stage.registry, now=NOW, allow_synthetic=True)
        self.assertEqual('current', assessment.calibration_status)
        self.assertEqual(4, assessment.failed_trials)
        self.assertEqual(4, assessment.unqualified_message_trials)
        self.assertFalse(assessment.deployment_authorized)


if __name__ == '__main__':
    unittest.main()
