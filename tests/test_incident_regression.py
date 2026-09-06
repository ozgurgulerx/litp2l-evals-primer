"""Synthetic incident promotion uses executed failures and bound review."""
import json
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from cx_eval_lab.incident_regression import (
    Inventory,
    RegressionRelease,
    Review,
    capture_incident,
    promote,
    propose_regression,
    replay_study,
    run_study,
)


class IncidentRegressionTests(unittest.TestCase):
    def setUp(self):
        self.incident = capture_incident()
        self.proposal = propose_regression(self.incident)
        self.review = Review(self.incident.digest, self.proposal.digest,
                             'synthetic-reviewer', 'refund-policy-v1', 'approved', 'approved')
        self.parent = RegressionRelease('regression-v0')

    def test_execution_minimization_review_and_new_release(self):
        original = self.incident.to_dict()
        self.assertFalse(original['execution']['passed'])
        self.assertGreater(original['execution']['final_state']['refund_transaction_count'], 1)
        self.assertLess(len(self.proposal.case.utterance), len(self.incident.case.utterance))
        self.assertFalse(self.proposal.case.competing_order_ids)
        child = promote(self.parent, self.incident, self.proposal, self.review)
        self.assertEqual(0, len(self.parent.entries))
        self.assertEqual(1, len(child.entries))
        self.assertEqual(self.parent.digest, child.parent_hash)
        self.assertEqual(original, self.incident.to_dict())
        with self.assertRaises(FrozenInstanceError):
            child.version = 'changed'

    def test_review_and_protected_inventory_fail_closed(self):
        variants = [None, replace(self.review, decision='rejected'),
                    replace(self.review, privacy_review='pending'),
                    replace(self.review, proposer_hash='sha256:' + '0' * 64),
                    replace(self.review, incident_hash='sha256:' + '0' * 64),
                    replace(self.review, reviewer_id=self.proposal.proposer_id),
                    replace(self.review, domain_policy='other-policy')]
        for review in variants:
            with self.subTest(review=review), self.assertRaises(ValueError):
                promote(self.parent, self.incident, self.proposal, review)
        for role in ('sealed-acceptance', 'judge-calibration'):
            with self.subTest(role=role), self.assertRaises(ValueError):
                promote(self.parent, self.incident, self.proposal, self.review,
                        (Inventory(role, (self.incident.group_id,)),))

    def test_duplicate_case_and_modified_source_are_rejected(self):
        child = promote(self.parent, self.incident, self.proposal, self.review)
        with self.assertRaises(ValueError):
            promote(child, self.incident, self.proposal, self.review)
        stale = replace(self.proposal, case=replace(self.proposal.case, amount_cents=4321))
        with self.assertRaises(ValueError):
            promote(self.parent, self.incident, stale, self.review)
        execution = json.loads(self.incident.execution_json)
        execution['final_state']['refund_transaction_count'] = 0
        forged = replace(self.incident, execution_json=json.dumps(execution))
        with self.assertRaises(ValueError):
            propose_regression(forged)

    def test_report_reexecutes_and_is_detached(self):
        report = run_study()
        self.assertTrue(report['conformance_passed'])
        self.assertFalse(report['deployment_authorized'])
        self.assertTrue(replay_study(report))
        report['reruns']['mutant']['events'] = []
        from cx_eval_lab.evidence import canonical_hash
        report['report_hash'] = canonical_hash({k: v for k, v in report.items() if k != 'report_hash'})
        with self.assertRaises(ValueError):
            replay_study(report)

    def test_validation_and_exclusive_cli(self):
        for value in ('NaN', '{"x": NaN}', '[]'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                replace(self.incident, execution_json=value)
        with self.assertRaises(ValueError):
            RegressionRelease('bad', role='sealed-acceptance')
        with self.assertRaises(ValueError):
            Inventory('development', ('x',))
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'study.json'
            args = [sys.executable, '-m', 'cx_eval_lab.incident_regression', '--output', str(output)]
            result = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            saved = output.read_bytes()
            self.assertNotEqual(0, subprocess.run(args, capture_output=True, timeout=30, check=False).returncode)
            self.assertEqual(saved, output.read_bytes())

    def test_protected_source_and_candidate_content_cannot_be_renamed_away(self):
        from cx_eval_lab.incident_regression import content_hash
        for role in ('sealed-acceptance', 'judge-calibration'):
            inventories = [Inventory(role, source_hashes=(self.incident.digest,)),
                           Inventory(role, content_hashes=(content_hash(self.incident.case),)),
                           Inventory(role, content_hashes=(content_hash(self.proposal.case),))]
            for inventory in inventories:
                with self.subTest(inventory=inventory), self.assertRaises(ValueError):
                    promote(self.parent, self.incident, self.proposal, self.review, (inventory,))
        renamed = replace(self.proposal.case, case_id='renamed', dataset_version='other')
        self.assertEqual(content_hash(self.proposal.case), content_hash(renamed))

    def test_wrong_causal_precondition_and_target_review_are_rejected(self):
        from cx_eval_lab.incident_regression import execute
        case = replace(self.incident.case, simulate_timeout_after_commit=False)
        incident = replace(self.incident, case=case, execution_json=json.dumps(execute(case)))
        with self.assertRaises(ValueError):
            propose_regression(incident)
        changed_target = propose_regression(self.incident, target_version='regression-v2')
        with self.assertRaises(ValueError):
            promote(self.parent, self.incident, changed_target, self.review)

    def test_populated_parent_is_preserved_and_all_cases_materialize(self):
        from cx_eval_lab.incident_regression import execute
        first = promote(self.parent, self.incident, self.proposal, self.review)
        case = replace(self.incident.case, order_id='synthetic-other-order')
        incident = replace(self.incident, incident_id='synthetic-incident-02', group_id='synthetic-session-02',
                           case=case, execution_json=json.dumps(execute(case)))
        proposal = propose_regression(incident, target_version='regression-v2')
        review = replace(self.review, incident_hash=incident.digest, proposer_hash=proposal.digest)
        second = promote(first, incident, proposal, review)
        self.assertEqual(first.entries, second.entries[:1])
        self.assertEqual(first.digest, second.parent_hash)
        self.assertEqual(2, len(second.materialize()))
        self.assertTrue(all(case.dataset_version == 'regression-v2' for case in second.materialize()))
        duplicate = propose_regression(self.incident, target_version='regression-v3')
        with self.assertRaisesRegex(ValueError, 'duplicate content'):
            promote(second, self.incident, duplicate,
                    replace(self.review, proposer_hash=duplicate.digest))

    def test_parent_entry_hash_forgery_and_malformed_rows_are_rejected(self):
        child = promote(self.parent, self.incident, self.proposal, self.review)
        row = json.loads(child.entries[0])
        row['content_hash'] = 'sha256:' + '0' * 64
        for entries in ((json.dumps(row),), ('{}',), child.entries * 2):
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                RegressionRelease('regression-v2', entries)

    def test_current_protected_inventory_checks_carried_parent_entries(self):
        from cx_eval_lab.incident_regression import content_hash, execute
        parent = promote(self.parent, self.incident, self.proposal, self.review)
        case = replace(self.incident.case, order_id='synthetic-next-order')
        incident = replace(self.incident, incident_id='synthetic-next-incident', group_id='synthetic-next-group',
                           case=case, execution_json=json.dumps(execute(case)))
        proposal = propose_regression(incident, target_version='regression-v2')
        review = replace(self.review, incident_hash=incident.digest, proposer_hash=proposal.digest)
        self.assertEqual(2, len(promote(parent, incident, proposal, review).entries))
        for role in ('sealed-acceptance', 'judge-calibration'):
            inventories = [Inventory(role, groups=(self.incident.group_id,)),
                           Inventory(role, source_hashes=(self.incident.digest,)),
                           Inventory(role, content_hashes=(content_hash(self.proposal.case),))]
            for inventory in inventories:
                with self.subTest(inventory=inventory), self.assertRaises(ValueError):
                    promote(parent, incident, proposal, review, (inventory,))
