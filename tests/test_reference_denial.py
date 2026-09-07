"""A returned tool denial must not become a customer-facing success claim."""

import unittest

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.models import RefundAgentInput, RefundWorldSeed
from cx_eval_lab.world import RefundTools, RefundWorld


class StatusTools(RefundTools):
    def __init__(self, world, status):
        super().__init__(world)
        self.status = status

    def issue_refund(self, *args, **kwargs):
        return {} if self.status is None else {"status": self.status}


class CommittedUnknownTools(RefundTools):
    def issue_refund(self, *args, **kwargs):
        super().issue_refund(*args, **kwargs)
        return {"status": "unknown"}


class ReferenceDenialTests(unittest.TestCase):
    def test_unknown_return_after_effect_is_reconciled_before_claiming_state(self):
        seed = RefundWorldSeed("customer", "order", 4000, "USD", True, 10000, False)
        world = RefundWorld(seed)
        request = RefundAgentInput("Refund this order", "customer", "order", ("order",))
        result = ReferenceSupportAgent().run(request, CommittedUnknownTools(world))
        self.assertEqual("refunded", result.claimed_outcome)
        self.assertEqual(1, world.snapshot.refund_transaction_count)
        self.assertTrue(any(event.tool == "inspect_order_status" for event in world.events))

    def test_denied_unknown_or_missing_status_does_not_claim_refunded(self):
        seed = RefundWorldSeed("customer", "order", 4000, "USD", True, 10000, False)
        request = RefundAgentInput("Refund this order", "customer", "order", ("order",))
        for status in ("blocked", "unknown", None):
            with self.subTest(status=status):
                world = RefundWorld(seed)
                result = ReferenceSupportAgent().run(request, StatusTools(world, status))
                self.assertEqual("needs_review", result.claimed_outcome)
                self.assertEqual("I could not confirm the refund.", result.message)
                self.assertEqual(0, world.snapshot.refund_transaction_count)

    def test_real_commit_and_replay_still_report_the_committed_effect(self):
        seed = RefundWorldSeed("customer", "order", 4000, "USD", True, 10000, False)
        world = RefundWorld(seed)
        request = RefundAgentInput("Refund this order", "customer", "order", ("order",))
        for _ in range(2):
            self.assertEqual("refunded", ReferenceSupportAgent().run(request, RefundTools(world)).claimed_outcome)
        self.assertEqual(1, world.snapshot.refund_transaction_count)


if __name__ == "__main__":
    unittest.main()
