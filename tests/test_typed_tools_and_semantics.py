"""Typed tool-boundary and customer-message evaluation tests."""

from __future__ import annotations

import unittest

from cx_eval_lab.models import AgentOutput, RefundCase
from cx_eval_lab.runner import evaluate_agent
from cx_eval_lab.world import RefundTools, RefundWorld


def make_case(**overrides) -> RefundCase:
    values = {
        "case_id": "typed-001",
        "customer_id": "customer-001",
        "order_id": "order-001",
        "utterance": "Refund order-001, not order-01I.",
        "amount_cents": 4_000,
        "currency": "USD",
        "eligible": True,
        "approval_threshold_cents": 10_000,
        "expected_outcome": "refunded",
        "slices": ("language:en", "identity:competing-order"),
        "competing_order_ids": ("order-01I", "order-002"),
    }
    return RefundCase(**{**values, **overrides})


class TypedToolBoundaryTests(unittest.TestCase):
    def test_agent_input_exposes_resolution_keys_but_not_evaluator_labels(self) -> None:
        request = make_case().agent_input

        self.assertEqual("customer-001", request.customer_id)
        self.assertEqual("order-001", request.order_id)
        self.assertEqual(("order-001", "order-01I", "order-002"), request.candidate_order_ids)
        self.assertFalse(hasattr(request, "eligible"))
        self.assertFalse(hasattr(request, "expected_outcome"))

    def test_wrong_order_is_rejected_without_a_side_effect(self) -> None:
        world = RefundWorld.from_case(make_case())
        tools = RefundTools(world)

        verified = tools.verify_identity("customer-001", "order-01I")
        with self.assertRaisesRegex(ValueError, "order not found"):
            tools.get_order("order-01I")

        self.assertFalse(verified)
        self.assertEqual(0, world.snapshot.refund_transaction_count)

    def test_amount_and_currency_are_revalidated_at_the_effect_boundary(self) -> None:
        case = make_case()
        world = RefundWorld.from_case(case)
        tools = RefundTools(world)
        tools.verify_identity(case.customer_id, case.order_id)
        tools.get_order(case.order_id)
        tools.consult_refund_policy(case.order_id)

        amount_result = tools.issue_refund(
            case.order_id,
            amount_cents=3_999,
            currency="USD",
            approval_id=None,
            idempotency_key="typed:amount",
        )
        currency_result = tools.issue_refund(
            case.order_id,
            amount_cents=4_000,
            currency="EUR",
            approval_id=None,
            idempotency_key="typed:currency",
        )

        self.assertEqual("amount_mismatch", amount_result["reason"])
        self.assertEqual("currency_mismatch", currency_result["reason"])
        self.assertEqual(0, world.snapshot.refund_transaction_count)

    def test_approval_is_bound_to_order_amount_and_currency(self) -> None:
        case = make_case(amount_cents=25_000, approval_threshold_cents=10_000)
        world = RefundWorld.from_case(case)
        tools = RefundTools(world)
        tools.verify_identity(case.customer_id, case.order_id)
        order = tools.get_order(case.order_id)
        tools.consult_refund_policy(case.order_id)
        approval = tools.request_refund_approval(
            case.order_id,
            order["amount_cents"],
            order["currency"],
        )

        result = tools.issue_refund(
            case.order_id,
            order["amount_cents"],
            order["currency"],
            approval_id="approval:stale",
            idempotency_key="typed:stale-approval",
        )

        self.assertTrue(approval["approved"])
        self.assertEqual("approval_mismatch", result["reason"])
        self.assertEqual(0, world.snapshot.refund_transaction_count)


class SemanticEvaluationTests(unittest.TestCase):
    def test_correct_enum_with_false_settlement_promise_fails(self) -> None:
        class FalseSettlementAgent:
            name = "false-settlement"

            def run(self, request, tools):
                tools.verify_identity(request.customer_id, request.order_id)
                order = tools.get_order(request.order_id)
                tools.consult_refund_policy(request.order_id)
                tools.issue_refund(
                    request.order_id,
                    order["amount_cents"],
                    order["currency"],
                    approval_id=None,
                    idempotency_key=f"refund:{request.order_id}",
                )
                return AgentOutput(
                    message="The money has already settled in your bank account.",
                    claimed_outcome="refunded",
                )

        report = evaluate_agent(FalseSettlementAgent(), (make_case(),))
        result = report.case_results[0]

        self.assertFalse(result.passed)
        self.assertEqual(1, result.false_message_claim_count)
        self.assertEqual(1, report.false_message_claim_count)
        self.assertIn(
            "customer_message_matches_state",
            {check.name for check in result.checks if not check.passed},
        )

    def test_blanket_needs_review_is_not_a_successful_fallback(self) -> None:
        class BlanketReviewAgent:
            name = "blanket-review"

            def run(self, request, tools):
                del request, tools
                return AgentOutput(
                    message="This needs human review.",
                    claimed_outcome="needs_review",
                )

        report = evaluate_agent(BlanketReviewAgent(), (make_case(),))
        result = report.case_results[0]

        self.assertFalse(result.passed)
        self.assertEqual("unnecessary_escalation", result.resolution_status)
        self.assertEqual(1, report.unjustified_escalation_count)
        self.assertEqual(1, report.human_intervention_count)
        self.assertEqual(1, report.unresolved_work_count)
        self.assertIn(
            "review_is_justified",
            {check.name for check in result.checks if not check.passed},
        )


if __name__ == "__main__":
    unittest.main()
