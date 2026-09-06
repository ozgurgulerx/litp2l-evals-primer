"""Budget admission integrates with actual runner artifacts using fake providers."""

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from cx_eval_lab.campaign_budget import CampaignLedger, CampaignPolicy
from cx_eval_lab.semantic import SemanticRequest
from tests.test_openai_judge import FakeClient, OpenAIJudgeTests


class BudgetedJudgeTests(unittest.TestCase):
    def setUp(self):
        from cx_eval_lab.budgeted_judge import BudgetedSemanticJudge
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.policy = CampaignPolicy('offline-judge', 1000, 5, 2000, 600)
        self.ledger = CampaignLedger.create(Path(self.temp.name) / 'campaign.sqlite',
                                            self.policy, clock_ms=lambda: 1000)
        self.client = FakeClient()
        self.inner = OpenAIJudgeTests().judge(self.client)
        self.judge = BudgetedSemanticJudge(self.inner, self.ledger)

    def request(self, identifier='one', evidence='{}'):
        return SemanticRequest(evidence, invocation_id=identifier)

    def test_preserves_provider_evidence_and_prevents_duplicate_dispatch(self):
        result = self.judge.evaluate(self.request())
        self.assertEqual('pass', result.verdict)
        self.assertEqual('resp_fixture', json.loads(result.provider_audit_json)['response']['id'])
        self.assertEqual(360, json.loads(result.campaign_audit_json)['receipt']['estimate_micro_usd'])
        self.assertEqual(self.inner.configuration_hash, self.judge.configuration_hash)
        self.assertEqual('abstain', self.judge.evaluate(self.request()).verdict)
        self.assertEqual(1, len(self.client.calls))
        self.assertNotIn('invocation_id', self.client.calls[0]['input'][0]['content'])

    def test_unknown_request_cost_remains_held_and_blocks_next_request(self):
        self.client.error = TimeoutError('private details')
        first = self.judge.evaluate(self.request())
        second = self.judge.evaluate(self.request('two'))
        self.assertEqual('abstain', first.verdict)
        self.assertEqual('abstain', second.verdict)
        self.assertEqual('estimated_budget_exhausted', json.loads(second.campaign_audit_json)['reason'])
        self.assertEqual(1, len(self.client.calls))
        self.assertEqual(600, self.ledger.snapshot()['held_reservations_micro_usd'])
        self.assertNotIn('private details', first.campaign_audit_json)

    def test_persistence_failure_retains_judgment_but_withholds_pass(self):
        with patch.object(CampaignLedger, 'finalize', side_effect=OSError('private path')):
            result = self.judge.evaluate(self.request())
        self.assertEqual('abstain', result.verdict)
        self.assertIsNotNone(result.runtime_evidence)
        audit = json.loads(result.campaign_audit_json)
        self.assertEqual('pass', audit['uncommitted_judgment']['verdict'])
        self.assertNotIn('private path', result.campaign_audit_json)
        self.assertEqual(600, self.ledger.snapshot()['held_reservations_micro_usd'])

    def test_missing_invocation_or_conflict_makes_no_additional_call(self):
        self.assertEqual('abstain', self.judge.evaluate(SemanticRequest('{}')).verdict)
        self.assertEqual([], self.client.calls)
        self.judge.evaluate(self.request())
        self.assertEqual('abstain', self.judge.evaluate(self.request(evidence='{"changed":true}')).verdict)
        self.assertEqual(1, len(self.client.calls))

    def test_paired_invocations_are_distinct_reproducible_and_replayable(self):
        from cx_eval_lab.artifacts import replay_packet
        from cx_eval_lab.dataset import load_refund_cases
        from cx_eval_lab.evidence import canonical_hash
        from cx_eval_lab.runner import DEFAULT_MEASUREMENT_PROFILE, run_paired_experiment
        from tests.test_evidence_spine import make_manifest
        from tests.test_semantic_stage import FreeFormReference, setup_stage
        policy = replace(self.policy, max_estimated_micro_usd=10000)
        ledger = CampaignLedger.create(Path(self.temp.name) / 'paired.sqlite', policy, clock_ms=lambda: 1000)
        judge = replace(self.judge, ledger=ledger)
        stage = setup_stage(judge, evaluator_version=judge.evaluator_version,
                            configuration_hash=judge.configuration_hash)
        cases = load_refund_cases('evals/cx-support/datasets/regression/refund_v1.json')[:1]
        manifest = replace(make_manifest(), population_hash=canonical_hash(
            [[c.case_id, c.customer_id, list(c.slices)] for c in cases]))
        kwargs = dict(baseline_agent=FreeFormReference(), candidate_agent=FreeFormReference(),
                      cases=cases, manifest=manifest, semantic_stage=stage,
                      baseline_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
                      candidate_measurement_profile=DEFAULT_MEASUREMENT_PROFILE)
        packet = run_paired_experiment(**kwargs).to_dict()
        self.assertEqual(4, len(self.client.calls))
        self.assertEqual(4, ledger.snapshot()['admissions'])
        identifiers = {a['payload']['semantic_stage']['invocation_id'] for a in packet['trial_artifacts']}
        self.assertEqual(4, len(identifiers))
        self.assertEqual(4, len(replay_packet(packet,
            trusted_calibration_hashes=frozenset({stage.calibration_hash}))))
        again = run_paired_experiment(**kwargs).to_dict()
        self.assertEqual(4, len(self.client.calls))
        self.assertTrue(all(a['payload']['semantic_stage']['judgment']['verdict'] == 'abstain'
                            for a in again['trial_artifacts']))


if __name__ == '__main__':
    unittest.main()
