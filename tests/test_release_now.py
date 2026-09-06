"""New decisions must recompute current checks, not accept historical passes."""

import copy
from dataclasses import asdict, replace
from datetime import timedelta
import unittest

from cx_eval_lab.evidence import DeterministicTestReceipt, PrerequisiteReceipt, canonical_hash
from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases
from cx_eval_lab.resolution_evidence import design
from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
from cx_eval_lab.semantic import CalibrationRegistry
from cx_eval_lab.source_provenance import capture_source_inputs
from tests.test_resolution_semantic import setup_stage, NOW
from tests import test_source_provenance as source_fixtures


class ReleaseNowTests(unittest.TestCase):
    def setUp(self):
        self.source = source_fixtures.SourceProvenanceTests()
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.stage = setup_stage()
        cases, agent = example_cases(), DescriptiveResolver()
        self.values = {'resolution-cases': [asdict(case) for case in cases],
            'resolution-design': design(agent.name, agent.name, self.stage.registration),
            'native-semantic-registration': self.stage.registration}
        manifest = replace(make_manifest(cases, agent.name, agent.name, semantic_stage=self.stage),
            code_revision=self.source.revision, input_hashes=(*capture_source_inputs(self.source.root),
                *((name, canonical_hash(value)) for name, value in self.values.items())))
        self.packet = run_paired_resolution(cases=cases, baseline_agent=agent, candidate_agent=agent,
                                           manifest=manifest, semantic_stage=self.stage).to_dict()
        self.arguments = dict(trusted_packet_hash=canonical_hash(self.packet),
            historical_calibration_hashes={self.stage.calibration_hash}, registry=self.stage.registry,
            now=NOW, root=self.source.root, input_files={}, input_values=self.values,
            expected_revision=self.source.revision, expected_evaluator_version=manifest.evaluator_version,
            deterministic_test_receipt=DeterministicTestReceipt('synthetic-test-control',
                manifest.code_revision, (('synthetic_control', True),), canonical_hash('fixture tests')),
            prerequisite_receipts=tuple(PrerequisiteReceipt(key, (('synthetic_control', True),),
                canonical_hash(key)) for key in ('typed_tool_boundary', 'semantic_state_grading')),
            allow_synthetic=True)

    def assess(self, **changes):
        from cx_eval_lab.release_now import assess_release_now
        return assess_release_now(self.packet, **{**self.arguments, **changes}).to_dict()

    def test_verified_current_controls_still_hold_for_insufficient_samples(self):
        result = self.assess()
        self.assertEqual('hold', result['action'])
        self.assertEqual('current', result['checks']['replay']['calibration_status'])
        self.assertEqual(16, result['checks']['replay']['replayed_trials'])
        self.assertEqual(self.source.revision, result['checks']['source']['code_revision'])
        self.assertEqual('inconclusive', result['checks']['base_receipt']['comparison']['status'])
        self.assertFalse(result['deployment_authorized'])
        self.assertEqual('none', result['authority_ceiling'])

    def test_revocation_preserves_history_but_blocks_new_decision(self):
        original = copy.deepcopy(self.packet)
        result = self.assess(registry=CalibrationRegistry(self.stage.registry.records,
                                                         frozenset({self.stage.calibration_hash})))
        self.assertEqual('block', result['action'])
        self.assertIn('current_calibration_not_current', result['issues'])
        self.assertEqual(0, result['checks']['replay']['failed_trials'])
        self.assertEqual(original, self.packet)

    def test_synthetic_default_and_missing_registry_cannot_pass_current_check(self):
        for changes in ({'allow_synthetic': False}, {'registry': CalibrationRegistry(())}):
            with self.subTest(changes=changes):
                result = self.assess(**changes)
                self.assertEqual('block', result['action'])
                self.assertEqual('not_current', result['checks']['replay']['calibration_status'])

    def test_changed_source_inputs_or_expected_identity_block(self):
        for changes in ({'input_values': {**self.values, 'resolution-cases': []}},
                        {'expected_revision': '0' * 40}, {'expected_evaluator_version': 'unknown'}):
            with self.subTest(changes=changes):
                self.assertIn('source_verification_failed', self.assess(**changes)['issues'])
        path = self.source.root / 'cx_eval_lab/evaluators.py'
        path.write_text('VERSION = 999\n')
        self.assertEqual('block', self.assess()['action'])

    def test_wrong_anchor_and_missing_historical_trust_fail_closed(self):
        self.assertIn('packet_anchor_mismatch', self.assess(trusted_packet_hash=canonical_hash('other'))['issues'])
        result = self.assess(historical_calibration_hashes=set())
        self.assertEqual('block', result['action'])
        self.assertIn('historical_replay_failed', result['issues'])

    def test_expired_manifest_cannot_issue_new_receipt_and_naive_clock_rejected(self):
        result = self.assess(now=NOW + timedelta(days=40))
        self.assertIn('manifest_not_current', result['issues'])
        self.assertEqual('block', result['action'])
        self.assertIsNone(result['checks']['base_receipt'])
        with self.assertRaises(ValueError):
            self.assess(now=NOW.replace(tzinfo=None))

    def test_future_execution_cannot_support_an_earlier_decision(self):
        from tests.test_resolution_evidence import rehash
        changed = copy.deepcopy(self.packet)
        for artifact in changed['trial_artifacts']:
            audit = artifact['payload']['semantic_stage']
            audit['started_at'] = (NOW + timedelta(hours=2)).isoformat()
            audit['completed_at'] = (NOW + timedelta(hours=2)).isoformat()
        rehash(changed)
        self.packet = changed
        result = self.assess(trusted_packet_hash=canonical_hash(changed))
        self.assertEqual('block', result['action'])
        self.assertIn('evidence_after_decision_time', result['issues'])

    def test_future_campaign_event_and_missing_policy_inputs_both_block(self):
        milliseconds = int(NOW.timestamp() * 1000)
        for field in ('admission', 'completion'):
            snapshot = {'invocations': [{'admitted_ms': milliseconds + (field == 'admission'),
                'receipt_json': '{"completed_unix_ms":%d}' % (milliseconds + (field == 'completion'))}]}
            result = self.assess(campaign_snapshot=snapshot)
            self.assertEqual('block', result['action'])
            self.assertIn('evidence_after_decision_time', result['issues'])
            self.assertIn('campaign_inputs_missing', result['issues'])
        result = self.assess(campaign_snapshot={'invocations': [{'admitted_ms': -1, 'receipt_json': None}]})
        self.assertIn('invalid_evidence_chronology', result['issues'])

    def test_bad_packet_or_base_receipts_do_not_produce_a_new_pass(self):
        from cx_eval_lab.release_now import assess_release_now
        for packet in ({}, {'bad': float('nan')}, {'manifest': None}):
            result = assess_release_now(packet, **self.arguments).to_dict()
            self.assertEqual('block', result['action'])
            self.assertIn('malformed_packet', result['issues'])
        result = self.assess(prerequisite_receipts=())
        self.assertIn('base_receipt_failed', result['issues'])
        self.assertEqual('block', self.assess(now=NOW - timedelta(days=1))['action'])
        with self.assertRaises(ValueError):
            self.assess(allow_synthetic='true')


if __name__ == '__main__':
    unittest.main()
