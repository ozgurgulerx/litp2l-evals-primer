"""Synthetic incident promotion uses executed failures and bound review."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cx_eval_lab.incident_regression import (
    Inventory, RegressionRelease, Review, capture_incident, promote,
    propose_regression, replay_study, run_study,
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
                    replace(self.review, proposer_hash='0' * 64),
                    replace(self.review, incident_hash='0' * 64),
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
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            saved = output.read_bytes()
            self.assertNotEqual(0, subprocess.run(args, capture_output=True, timeout=30).returncode)
            self.assertEqual(saved, output.read_bytes())
