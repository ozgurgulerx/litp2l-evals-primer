"""Pinned campaign evidence must agree before it can clear its own gate."""

import copy
import json
import unittest

from cx_eval_lab.campaign_budget import CampaignPolicy
from cx_eval_lab.campaign_study import run_study
from cx_eval_lab.evidence import canonical_hash


def rehash_packet(packet):
    replacements = {}
    for artifact in packet['trial_artifacts']:
        payload = artifact['payload']
        payload['evaluation']['semantic_stage'] = copy.deepcopy(payload['semantic_stage'])
        old = artifact['artifact_hash']
        artifact['artifact_hash'] = canonical_hash(payload)
        replacements[old] = artifact['artifact_hash']
    for arm in ('baseline', 'candidate'):
        for row in packet[f'{arm}_trials']:
            row['artifact_hash'] = replacements[row['artifact_hash']]


class CampaignGateTests(unittest.TestCase):
    def setUp(self):
        self.report = run_study(unknown_second=False, budget_micro_usd=2000)
        self.policy = CampaignPolicy(**self.report['ledger']['policy'])

    def assess(self, report=None, **changes):
        from cx_eval_lab.campaign_gate import assess_campaign
        report = report or self.report
        arguments = dict(expected_policy=self.policy,
            trusted_packet_hash=canonical_hash(report['packet']),
            trusted_snapshot_hash=canonical_hash(report['ledger']),
            trusted_calibration_hashes=frozenset({report['synthetic_calibration_hash']}))
        return assess_campaign(report['packet'], report['ledger'], **{**arguments, **changes})

    def test_complete_consistent_campaign_clears_only_its_own_check(self):
        result = self.assess()
        self.assertEqual('clear', result.status)
        self.assertEqual(4, result.matched_invocations)
        self.assertEqual(1440, result.known_estimate_micro_usd)
        self.assertFalse(result.deployment_authorized)
        self.assertEqual((), result.issues)

    def test_unknown_and_denied_judgments_hold(self):
        report = run_study()
        result = self.assess(report, expected_policy=CampaignPolicy(**report['ledger']['policy']))
        self.assertEqual('hold', result.status)
        self.assertIn('unknown_or_pending_cost', result.issues)
        self.assertIn('judge_admission_denied', result.issues)

    def test_external_anchors_are_required_and_not_read_from_the_report(self):
        for changes in ({'trusted_packet_hash': canonical_hash('wrong')},
                        {'trusted_snapshot_hash': canonical_hash('wrong')},
                        {'trusted_snapshot_hash': None}):
            with self.subTest(changes=changes):
                self.assertEqual('block', self.assess(**changes).status)

    def test_recomputed_anchor_cannot_hide_false_summary_or_missing_rows(self):
        for mutate in (lambda ledger: ledger.update(known_estimate_micro_usd=0),
                       lambda ledger: ledger['invocations'].pop(),
                       lambda ledger: ledger['invocations'].append(copy.deepcopy(ledger['invocations'][0])),
                       lambda ledger: ledger.update(admissions=True),
                       lambda ledger: ledger['policy'].update(max_admissions=100)):
            report = copy.deepcopy(self.report)
            mutate(report['ledger'])
            self.assertEqual('block', self.assess(report).status)

    def test_row_receipt_and_inner_judgment_cannot_disagree(self):
        for field, value in (('estimate_micro', 1), ('reserved_micro', 500),
                             ('request_hash', canonical_hash('different evidence')),
                             ('judgment_json', '{"verdict":"fail"}')):
            report = copy.deepcopy(self.report)
            report['ledger']['invocations'][0][field] = value
            self.assertEqual('block', self.assess(report).status)

    def test_packet_to_ledger_join_is_checked_beyond_ordinary_replay(self):
        for field, value in (('invocation_id', 'wrong-id'), ('request', {'different': 'evidence'})):
            report = copy.deepcopy(self.report)
            report['packet']['trial_artifacts'][0]['payload']['semantic_stage'][field] = value
            rehash_packet(report['packet'])
            self.assertEqual('block', self.assess(report).status)

    def test_actual_reservation_overrun_blocks(self):
        report = run_study(reservation_micro_usd=300)
        result = self.assess(report, expected_policy=CampaignPolicy(**report['ledger']['policy']))
        self.assertEqual('block', result.status)
        self.assertIn('reservation_overrun', result.issues)

    def test_audit_qualification_must_match_the_trusted_receipt(self):
        report = copy.deepcopy(self.report)
        report['packet']['trial_artifacts'][0]['payload']['semantic_stage']['qualification']['false_examples'] = 101
        rehash_packet(report['packet'])
        self.assertEqual('block', self.assess(report).status)

    def test_consistently_rewritten_judge_input_must_still_match_the_execution(self):
        from cx_eval_lab.semantic import CRITERION
        report = copy.deepcopy(self.report)
        stage = report['packet']['trial_artifacts'][0]['payload']['semantic_stage']
        stage['request']['authoritative_order']['eligible'] = False
        stage['request_hash'] = canonical_hash(stage['request'])
        row = next(row for row in report['ledger']['invocations'] if row['id'] == stage['invocation_id'])
        row['request_hash'] = canonical_hash({'criterion': CRITERION, 'evidence': stage['request']})
        receipt = json.loads(row['receipt_json'])
        receipt['request_hash'] = row['request_hash']
        row['receipt_json'] = json.dumps(receipt)
        audit = json.loads(stage['judgment']['campaign_audit_json'])
        audit['receipt'] = receipt
        stage['judgment']['campaign_audit_json'] = json.dumps(audit)
        rehash_packet(report['packet'])
        self.assertEqual('block', self.assess(report).status)

    def test_passed_semantic_receipt_cannot_contradict_its_judgment(self):
        report = copy.deepcopy(self.report)
        stage = report['packet']['trial_artifacts'][0]['payload']['semantic_stage']
        stage['judgment']['verdict'] = 'fail'
        row = next(row for row in report['ledger']['invocations'] if row['id'] == stage['invocation_id'])
        inner = {**stage['judgment'], 'campaign_audit_json': None}
        row['judgment_json'] = json.dumps(inner)
        receipt = json.loads(row['receipt_json'])
        receipt['judgment_hash'] = canonical_hash(inner)
        row['receipt_json'] = json.dumps(receipt)
        audit = json.loads(stage['judgment']['campaign_audit_json'])
        audit['receipt'] = receipt
        stage['judgment']['campaign_audit_json'] = json.dumps(audit)
        rehash_packet(report['packet'])
        self.assertEqual('block', self.assess(report).status)

    def test_recorded_admission_must_say_it_reserved_capacity(self):
        report = copy.deepcopy(self.report)
        stage = report['packet']['trial_artifacts'][0]['payload']['semantic_stage']
        audit = json.loads(stage['judgment']['campaign_audit_json'])
        audit['admission']['reason'] = 'estimated_budget_exhausted'
        stage['judgment']['campaign_audit_json'] = json.dumps(audit)
        rehash_packet(report['packet'])
        self.assertEqual('block', self.assess(report).status)

    def test_judge_configuration_must_match_its_registration(self):
        report = copy.deepcopy(self.report)
        packet = report['packet']
        packet['manifest']['input_hashes'] = [
            [key, canonical_hash('different registered judge') if key == 'judge-config' else digest]
            for key, digest in packet['manifest']['input_hashes']]
        packet['manifest_hash'] = canonical_hash(packet['manifest'])
        for artifact in packet['trial_artifacts']:
            payload = artifact['payload']
            identity, stage = payload['identity'], payload['semantic_stage']
            identity['manifest_hash'] = packet['manifest_hash']
            new_id = canonical_hash([identity['manifest_hash'], identity['case_id'],
                                     identity['trial_index'], identity['arm']])
            row = next(row for row in report['ledger']['invocations'] if row['id'] == stage['invocation_id'])
            row['id'] = stage['invocation_id'] = new_id
            receipt = json.loads(row['receipt_json'])
            receipt['invocation_id'] = new_id
            row['receipt_json'] = json.dumps(receipt)
            audit = json.loads(stage['judgment']['campaign_audit_json'])
            audit['receipt'] = receipt
            audit['admission']['invocation_id'] = new_id
            stage['judgment']['campaign_audit_json'] = json.dumps(audit)
        for arm in ('baseline', 'candidate'):
            for row in packet[f'{arm}_trials']:
                row['manifest_hash'] = packet['manifest_hash']
        rehash_packet(packet)
        self.assertEqual('block', self.assess(report).status)


if __name__ == '__main__':
    unittest.main()
