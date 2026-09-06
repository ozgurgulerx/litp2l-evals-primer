"""Adversarial tests for structured customer-message truth evaluation."""

from __future__ import annotations

import unittest

from cx_eval_lab.evaluators import evaluate_case, hash_customer_message
from cx_eval_lab.models import AgentOutput, RefundCase, SemanticEvaluationReceipt
from cx_eval_lab.world import RefundTools, RefundWorld


def eligible_case() -> RefundCase:
    return RefundCase(
        case_id="semantic-001",
        customer_id="customer-001",
        order_id="order-001",
        utterance="Please refund the damaged item.",
        amount_cents=4_000,
        currency="USD",
        eligible=True,
        approval_threshold_cents=10_000,
        expected_outcome="refunded",
        slices=("language:en",),
        dataset_version="refund-v1",
    )


def committed_world():
    case = eligible_case()
    world = RefundWorld.from_case(case)
    tools = RefundTools(world)
    tools.verify_identity(case.customer_id, case.order_id)
    order = tools.get_order(case.order_id)
    tools.consult_refund_policy(case.order_id)
    tools.issue_refund(
        case.order_id,
        int(order["amount_cents"]),
        str(order["currency"]),
        approval_id=None,
        idempotency_key=f"refund:{case.order_id}",
    )
    return case, world


def evaluate(output: AgentOutput, receipt: SemanticEvaluationReceipt | None = None):
    case, world = committed_world()
    return evaluate_case(
        case,
        output,
        world.events,
        world.snapshot,
        latency_ms=10,
        cost_usd=0.01,
        semantic_evaluation_receipt=receipt,
    )


class StructuredSemanticClaimTests(unittest.TestCase):
    def test_funds_now_available_is_a_false_settlement_claim(self) -> None:
        result = evaluate(
            AgentOutput(
                message="Your funds are now available.",
                claimed_outcome="refunded",
                transaction_status_claim="committed",
                settlement_status_claim="settled",
            )
        )

        self.assertFalse(result.passed)
        self.assertEqual(1, result.false_message_claim_count)

    def test_negated_settlement_template_does_not_false_positive(self) -> None:
        result = evaluate(
            AgentOutput(
                message=(
                    "Your refund has been confirmed, but it has not settled in "
                    "your bank account yet."
                ),
                claimed_outcome="refunded",
                transaction_status_claim="committed",
                settlement_status_claim="not_settled",
                message_template_id="refund_committed_not_settled_v1",
            )
        )

        self.assertTrue(result.passed)
        self.assertEqual(0, result.false_message_claim_count)
        self.assertEqual(0, result.unqualified_message_count)

    def test_free_form_time_language_requires_independent_semantic_evidence(self) -> None:
        message = "I cannot promise that it will arrive within 5 business days."
        result = evaluate(
            AgentOutput(
                message=message,
                claimed_outcome="refunded",
                transaction_status_claim="committed",
                settlement_status_claim="not_settled",
            )
        )

        self.assertFalse(result.passed)
        self.assertEqual(0, result.false_message_claim_count)
        self.assertEqual(1, result.unqualified_message_count)
        self.assertIn(
            "customer_message_qualified",
            {check.name for check in result.checks if not check.passed},
        )

    def test_calibrated_receipt_can_qualify_multilingual_free_form(self) -> None:
        message = "İade talimatı kaydedildi; tutar henüz banka hesabınıza geçmedi."
        receipt = SemanticEvaluationReceipt(
            criterion_id="refund_customer_message_truth_v1",
            evaluator_version="semantic-evaluator-v3",
            calibration_receipt_hash="sha256:" + "a" * 64,
            message_hash=hash_customer_message(message),
            structured_claim_hash="sha256:" + "b" * 64,
            passed=True,
            abstained=False,
        )
        result = evaluate(
            AgentOutput(
                message=message,
                claimed_outcome="refunded",
                transaction_status_claim="committed",
                settlement_status_claim="not_settled",
            ),
            receipt,
        )

        self.assertTrue(result.passed)
        self.assertEqual(0, result.unqualified_message_count)

    def test_abstention_or_message_mismatch_cannot_qualify_free_form(self) -> None:
        message = "Refund instruction recorded; bank settlement remains pending."
        base = {
            "criterion_id": "refund_customer_message_truth_v1",
            "evaluator_version": "semantic-evaluator-v3",
            "calibration_receipt_hash": "sha256:" + "a" * 64,
            "structured_claim_hash": "sha256:" + "b" * 64,
            "passed": True,
        }
        abstention = SemanticEvaluationReceipt(
            **base,
            message_hash=hash_customer_message(message),
            abstained=True,
        )
        mismatch = SemanticEvaluationReceipt(
            **base,
            message_hash=hash_customer_message("different message"),
            abstained=False,
        )
        output = AgentOutput(
            message=message,
            claimed_outcome="refunded",
            transaction_status_claim="committed",
            settlement_status_claim="not_settled",
        )

        self.assertEqual(1, evaluate(output, abstention).unqualified_message_count)
        self.assertEqual(1, evaluate(output, mismatch).unqualified_message_count)


if __name__ == "__main__":
    unittest.main()
