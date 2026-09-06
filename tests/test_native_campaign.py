"""Native campaign admission must join its own criterion and execution evidence."""

import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cx_eval_lab.budgeted_judge import BudgetedSemanticJudge
from cx_eval_lab.campaign_budget import CampaignLedger, CampaignPolicy
from cx_eval_lab.campaign_gate import assess_campaign
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import RuntimeEvidence
from cx_eval_lab.order_resolution import DescriptiveResolver, example_cases
from cx_eval_lab.resolution_runner import make_manifest, run_paired_resolution
from cx_eval_lab.resolution_semantic import CRITERION
from cx_eval_lab.semantic import SemanticJudgment
from tests.test_resolution_semantic import NativeFixtureJudge, setup_stage


class MeteredNativeFixture(NativeFixtureJudge):
    def __init__(self, unknown=False):
        super().__init__()
        self.unknown = unknown

    def evaluate(self, request):
        self.requests.append(request)
        return SemanticJudgment('pass', 'Synthetic metering control, not semantic accuracy.',
            RuntimeEvidence('fixture', 'fixture-model', ('fixture-response',), 100, 20, 120,
                            None if self.unknown else 0.00036, 'invented fixture price'))


def execute_native_campaign(root, *, unknown=False, admissions=20):
    inner = MeteredNativeFixture(unknown)
    policy = CampaignPolicy('native-fixture', 20_000, admissions, 2000, 500)
    ledger = CampaignLedger.create(Path(root) / 'campaign.sqlite', policy, clock_ms=lambda: 1000)
    stage = setup_stage(BudgetedSemanticJudge(inner, ledger))
    cases, agent = example_cases(), DescriptiveResolver()
    manifest = make_manifest(cases, agent.name, agent.name, semantic_stage=stage)
    packet = run_paired_resolution(cases=cases, baseline_agent=agent, candidate_agent=agent,
                                  manifest=manifest, semantic_stage=stage).to_dict()
    return packet, ledger.snapshot(), stage, inner


class NativeCampaignTests(unittest.TestCase):
    def assess(self, packet, snapshot, stage):
        return assess_campaign(packet, snapshot, expected_policy=stage.judge.ledger.policy,
            trusted_packet_hash=canonical_hash(packet), trusted_snapshot_hash=canonical_hash(snapshot),
            trusted_calibration_hashes={stage.calibration_hash})

    def test_native_campaign_registers_then_clears_accounting_only(self):
        with tempfile.TemporaryDirectory() as root:
            packet, snapshot, stage, inner = execute_native_campaign(root)
        inputs = dict(packet['manifest']['input_hashes'])
        self.assertEqual(stage.judge.ledger.policy.content_hash, inputs.get('campaign-policy'))
        self.assertEqual(stage.judge.configuration_hash, inputs.get('judge-config'))
        result = self.assess(packet, snapshot, stage)
        self.assertEqual(('clear', 16, 5760),
                         (result.status, result.matched_invocations, result.known_estimate_micro_usd))
        self.assertFalse(result.deployment_authorized)
        self.assertTrue(all(r.criterion_id == CRITERION and r.invocation_id is None for r in inner.requests))

    def test_unknown_cost_or_admission_denial_holds_without_extra_dispatch(self):
        for unknown, admissions, calls in ((True, 20, 16), (False, 2, 2)):
            with self.subTest(unknown=unknown), tempfile.TemporaryDirectory() as root:
                packet, snapshot, stage, inner = execute_native_campaign(root, unknown=unknown,
                                                                         admissions=admissions)
            result = self.assess(packet, snapshot, stage)
            self.assertEqual('hold', result.status, result.issues)
            self.assertIn('unknown_or_pending_cost' if unknown else 'judge_admission_denied', result.issues)
            self.assertEqual(calls, len(inner.requests))

    def test_missing_or_changed_budget_registration_rejects_before_agent_execution(self):
        with tempfile.TemporaryDirectory() as root:
            _, _, stage, _ = execute_native_campaign(root)
            cases, agent = example_cases(), DescriptiveResolver()
            manifest = make_manifest(cases, agent.name, agent.name, semantic_stage=stage)
            for key in ('campaign-policy', 'judge-config'):
                invalid = replace(manifest, input_hashes=tuple((k, v) for k, v in manifest.input_hashes
                                                              if k != key))
                with self.subTest(key=key), patch('cx_eval_lab.resolution_runner.run_case') as run:
                    with self.assertRaisesRegex(ValueError, 'campaign'):
                        run_paired_resolution(cases=cases, baseline_agent=agent, candidate_agent=agent,
                                              manifest=invalid, semantic_stage=stage)
                    run.assert_not_called()

    def test_legacy_criterion_hash_cannot_substitute_for_native_request(self):
        from cx_eval_lab.semantic import CRITERION as LEGACY
        with tempfile.TemporaryDirectory() as root:
            packet, snapshot, stage, _ = execute_native_campaign(root)
        # Even recomputed outer anchors do not repair an inconsistent inner join.
        altered = copy.deepcopy(snapshot)
        row = altered['invocations'][0]
        payload = next(a['payload'] for a in packet['trial_artifacts']
                       if a['payload']['semantic_stage']['invocation_id'] == row['id'])
        row['request_hash'] = canonical_hash({'criterion': LEGACY,
                                              'evidence': payload['semantic_stage']['request']})
        receipt = json.loads(row['receipt_json'])
        row['receipt_json'] = json.dumps({**receipt, 'request_hash': row['request_hash']})
        result = self.assess(packet, altered, stage)
        self.assertEqual('block', result.status)
        self.assertIn('packet_campaign_evidence_mismatch', result.issues)


if __name__ == '__main__':
    unittest.main()
