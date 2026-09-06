"""Semantic evidence must be bound to the situation and all output claims."""

import unittest
from dataclasses import replace

from cx_eval_lab.evaluators import (
    evaluate_case, hash_customer_message, hash_structured_claims,
)
from cx_eval_lab.models import AgentOutput, SemanticEvaluationReceipt
from tests.test_semantic_claim_integrity import committed_world


class SemanticContextTests(unittest.TestCase):
    def test_legacy_receipt_without_context_is_not_qualified(self):
        case, world = committed_world()
        output = AgentOutput('Instruction recorded; settlement is unverified.', 'refunded',
                             transaction_status_claim='committed')
        receipt = SemanticEvaluationReceipt(
            'refund_customer_message_truth_v1', 'judge-v1', 'sha256:' + 'a' * 64,
            hash_customer_message(output.message), hash_structured_claims(output),
            True, False,
        )
        result = evaluate_case(case, output, world.events, world.snapshot, 1, 0,
                               semantic_evaluation_receipt=receipt,
                               qualified_semantic_calibration_hashes=frozenset({receipt.calibration_receipt_hash}))
        self.assertEqual(1, result.unqualified_message_count)

    def test_changed_outcome_or_escalation_changes_claim_hash(self):
        output = AgentOutput('Please wait.', 'refunded')
        for changed in (replace(output, claimed_outcome='needs_review'),
                        replace(output, escalation_reason='identity_failed')):
            self.assertNotEqual(hash_structured_claims(output), hash_structured_claims(changed))


if __name__ == '__main__':
    unittest.main()
