"""Unit tests for the resettable CX refund world."""

from __future__ import annotations

import unittest

from cx_eval_lab.models import RefundCase
from cx_eval_lab.world import RefundWorld, ToolTimeout


class RefundWorldTests(unittest.TestCase):
    def setUp(self) -> None:
        self.case = RefundCase(
            case_id="refund-unit-001",
            customer_id="customer-001",
            order_id="order-001",
            utterance="Please refund my order.",
            amount_cents=4_000,
            eligible=True,
            approval_threshold_cents=10_000,
            expected_outcome="refunded",
            slices=("language:en", "risk:standard"),
        )
        self.world = RefundWorld.from_case(self.case)

    def test_world_transitions_return_new_snapshots(self) -> None:
        before = self.world.snapshot

        self.world.verify_identity(self.case.customer_id, self.case.order_id)

        self.assertIsNot(before, self.world.snapshot)
        self.assertFalse(before.identity_verified)
        self.assertTrue(self.world.snapshot.identity_verified)

    def test_reset_restores_the_initial_state_and_clears_trace(self) -> None:
        self.world.verify_identity(self.case.customer_id, self.case.order_id)
        self.world.consult_refund_policy(self.case.order_id)
        self.world.issue_refund(self.case.order_id)

        self.world.reset()

        self.assertEqual(0, self.world.snapshot.refund_transaction_count)
        self.assertFalse(self.world.snapshot.identity_verified)
        self.assertEqual((), self.world.events)

    def test_timeout_after_commit_keeps_authoritative_refund_state(self) -> None:
        timeout_case = RefundCase(
            **{
                **self.case.to_dict(),
                "case_id": "refund-unit-timeout",
                "simulate_timeout_after_commit": True,
            }
        )
        world = RefundWorld.from_case(timeout_case)
        world.verify_identity(timeout_case.customer_id, timeout_case.order_id)
        world.consult_refund_policy(timeout_case.order_id)

        with self.assertRaises(ToolTimeout):
            world.issue_refund(timeout_case.order_id)

        self.assertEqual(1, world.snapshot.refund_transaction_count)
        self.assertEqual("timed_out_after_commit", world.events[-1].status)

    def test_guarded_refund_enforces_exactly_once_at_the_effect_boundary(self) -> None:
        self.world.verify_identity(self.case.customer_id, self.case.order_id)
        self.world.consult_refund_policy(self.case.order_id)

        self.world.issue_refund(self.case.order_id)
        self.world.issue_refund(self.case.order_id)

        self.assertEqual(1, self.world.snapshot.refund_transaction_count)

    def test_fault_injected_ledger_can_expose_a_duplicate_to_the_grader(self) -> None:
        self.world.verify_identity(self.case.customer_id, self.case.order_id)
        self.world.consult_refund_policy(self.case.order_id)

        self.world._unsafe_issue_refund_for_test(self.case.order_id, "attempt-1")
        self.world._unsafe_issue_refund_for_test(self.case.order_id, "attempt-2")

        self.assertEqual(2, self.world.snapshot.refund_transaction_count)


if __name__ == "__main__":
    unittest.main()
