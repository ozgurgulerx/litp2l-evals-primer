"""Adversarial tests for structured customer-message truth evaluation."""

from __future__ import annotations

import unittest

from cx_eval_lab.evaluators import (
    evaluate_case,
    hash_customer_message,
    hash_structured_claims,
    hash_evidence_context,
)
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


def evaluate(
    output: AgentOutput,
    receipt: SemanticEvaluationReceipt | None = None,
    qualified_calibration_hashes: frozenset[str] = frozenset(),
):
    case, world = committed_world()
    return evaluate_case(
        case,
        output,
        world.events,
        world.snapshot,
        latency_ms=10,
        cost_usd=0.01,
        semantic_evaluation_receipt=receipt,
        qualified_semantic_calibration_hashes=qualified_calibration_hashes,
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
                    "Your refund has been confirmed, but we cannot confirm bank "
                    "settlement yet."
                ),
                claimed_outcome="refunded",
                transaction_status_claim="committed",
                settlement_status_claim="not_confirmed",
                message_template_id="refund_committed_settlement_unconfirmed_v1",
            )
        )

        self.assertTrue(result.passed)
        self.assertEqual(0, result.false_message_claim_count)
        self.assertEqual(0, result.unqualified_message_count)

    def test_free_form_time_language_requires_independent_semantic_evidence(self) -> None:
        message = "I cannot promise that it will arrive within 5 business days."
        output = AgentOutput(
            message=message,
            claimed_outcome="refunded",
            transaction_status_claim="committed",
            settlement_status_claim="not_confirmed",
        )
        result = evaluate(output)

        self.assertFalse(result.passed)
        self.assertEqual(0, result.false_message_claim_count)
        self.assertEqual(1, result.unqualified_message_count)
        self.assertIn(
            "customer_message_qualified",
            {check.name for check in result.checks if not check.passed},
        )

    def test_calibrated_receipt_can_qualify_multilingual_free_form(self) -> None:
        message = "İade talimatı kaydedildi; tutar henüz banka hesabınıza geçmedi."
        output = AgentOutput(
            message=message,
            claimed_outcome="refunded",
            transaction_status_claim="committed",
            settlement_status_claim="not_confirmed",
        )
        receipt = SemanticEvaluationReceipt(
            criterion_id="refund_customer_message_truth_v1",
            evaluator_version="semantic-evaluator-v3",
            calibration_receipt_hash="sha256:" + "a" * 64,
            message_hash=hash_customer_message(message),
            structured_claim_hash=hash_structured_claims(output),
            passed=True,
            abstained=False,
            evidence_context_hash=hash_evidence_context(
                committed_world()[0], committed_world()[1].events,
                committed_world()[1].snapshot,
            ),
        )
        result = evaluate(
            output,
            receipt,
            frozenset({receipt.calibration_receipt_hash}),
        )

        self.assertTrue(result.passed)
        self.assertEqual(0, result.unqualified_message_count)

    def test_abstention_or_message_mismatch_cannot_qualify_free_form(self) -> None:
        message = "Refund instruction recorded; bank settlement remains pending."
        output = AgentOutput(
            message=message,
            claimed_outcome="refunded",
            transaction_status_claim="committed",
            settlement_status_claim="not_confirmed",
        )
        base = {
            "criterion_id": "refund_customer_message_truth_v1",
            "evaluator_version": "semantic-evaluator-v3",
            "calibration_receipt_hash": "sha256:" + "a" * 64,
            "structured_claim_hash": hash_structured_claims(output),
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
        qualified = frozenset({abstention.calibration_receipt_hash})
        self.assertEqual(
            1,
            evaluate(output, abstention, qualified).unqualified_message_count,
        )
        self.assertEqual(1, evaluate(output, mismatch, qualified).unqualified_message_count)

    def test_unregistered_calibration_receipt_cannot_qualify_message(self) -> None:
        message = "Refund instruction recorded; bank settlement is unverified."
        output = AgentOutput(
            message=message,
            claimed_outcome="refunded",
            transaction_status_claim="committed",
            settlement_status_claim="not_confirmed",
        )
        receipt = SemanticEvaluationReceipt(
            criterion_id="refund_customer_message_truth_v1",
            evaluator_version="semantic-evaluator-v3",
            calibration_receipt_hash="sha256:" + "9" * 64,
            message_hash=hash_customer_message(message),
            structured_claim_hash=hash_structured_claims(output),
            passed=True,
            abstained=False,
        )

        self.assertEqual(1, evaluate(output, receipt).unqualified_message_count)

    def test_quotation_and_negation_are_not_keyword_classified(self) -> None:
        quoted = evaluate(
            AgentOutput(
                message='The phrase "funds are now available" must not be used.',
                claimed_outcome="refunded",
                transaction_status_claim="committed",
                settlement_status_claim="not_claimed",
            )
        )
        negated = evaluate(
            AgentOutput(
                message="The refund has not settled in your account.",
                claimed_outcome="refunded",
                transaction_status_claim="committed",
                settlement_status_claim="not_confirmed",
            )
        )

        self.assertEqual(0, quoted.false_message_claim_count)
        self.assertEqual(1, quoted.unqualified_message_count)
        self.assertEqual(0, negated.false_message_claim_count)
        self.assertEqual(1, negated.unqualified_message_count)

    def test_obfuscated_prose_cannot_hide_a_structured_settlement_claim(self) -> None:
        result = evaluate(
            AgentOutput(
                message="F.u.n.d.s are n0w avai1able.",
                claimed_outcome="refunded",
                transaction_status_claim="committed",
                settlement_status_claim="settled",
            )
        )

        self.assertEqual(1, result.false_message_claim_count)


if __name__ == "__main__":
    unittest.main()
