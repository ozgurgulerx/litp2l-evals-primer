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


if __name__ == '__main__':
    unittest.main()
