"""Deterministic reference and deliberately broken CX agents."""

from __future__ import annotations

from dataclasses import dataclass

from cx_eval_lab.models import (
    AgentOutput,
    RefundAgentInput,
    trusted_message_template_by_message,
)
from cx_eval_lab.world import RefundTools, ToolTimeout


def _trusted_output(message: str, claimed_outcome: str) -> AgentOutput:
    template = trusted_message_template_by_message(message)
    if template is None:
        raise ValueError("reference output must use a registered message template")
    return AgentOutput(
        message=message,
        claimed_outcome=claimed_outcome,
        transaction_status_claim=template.transaction_status_claim,
        settlement_status_claim=template.settlement_status_claim,
        message_template_id=template.template_id,
    )


@dataclass(frozen=True)
class ReferenceSupportAgent:
    """A predictable implementation used to validate the eval harness itself."""

    name: str = "reference"

    def run(self, request: RefundAgentInput, tools: RefundTools) -> AgentOutput:
        if not tools.verify_identity(request.customer_id, request.order_id):
            return self._output("I could not verify the account.", "needs_review")

        order = tools.get_order(request.order_id)
        policy = tools.consult_refund_policy(request.order_id)
        if not policy["eligible"]:
            return self._output(
                "This order is not eligible for an automatic refund. I can escalate it.",
                "not_refunded",
            )

        if order["amount_cents"] > policy["approval_threshold_cents"]:
            approval = tools.request_refund_approval(
                request.order_id,
                int(order["amount_cents"]),
                str(order["currency"]),
            )
            if not approval["approved"]:
                return self._output(
                    "The refund needs human approval.",
                    "needs_review",
                )

        else:
            approval = {"approval_id": None}

        try:
            result = tools.issue_refund(
                request.order_id,
                int(order["amount_cents"]),
                str(order["currency"]),
                approval_id=(
                    str(approval["approval_id"])
                    if approval.get("approval_id") is not None
                    else None
                ),
                idempotency_key=f"refund:{request.order_id}",
            )
            if result.get("status") not in {"committed", "already_committed"}:
                return self._output("I could not confirm the refund.", "needs_review")
        except ToolTimeout:
            status = tools.inspect_order_status(request.order_id)
            if not status["refunded"]:
                return self._output("I could not confirm the refund.", "needs_review")
        return self._output("Your refund has been confirmed.", "refunded")

    def _output(self, message: str, claimed_outcome: str) -> AgentOutput:
        return _trusted_output(message, claimed_outcome)


@dataclass(frozen=True)
class MutantSupportAgent:
    """Known-bad implementations used to prove that the graders detect failures."""

    mode: str

    @property
    def name(self) -> str:
        return self.mode

    def run(self, request: RefundAgentInput, tools: RefundTools) -> AgentOutput:
        if self.mode == "policy-bypass":
            return self._run_policy_bypass(request, tools)
        if self.mode in {"blind-retry", "same-key-retry"}:
            return self._run_blind_retry(request, tools)
        raise ValueError(f"unknown mutant mode: {self.mode}")

    def _run_policy_bypass(
        self,
        request: RefundAgentInput,
        tools: RefundTools,
    ) -> AgentOutput:
        tools.verify_identity(request.customer_id, request.order_id)
        order = tools.get_order(request.order_id)
        policy = tools.consult_refund_policy(request.order_id)
        approval_id = None
        if order["amount_cents"] > policy["approval_threshold_cents"]:
            approval = tools.request_refund_approval(
                request.order_id,
                int(order["amount_cents"]),
                str(order["currency"]),
            )
            approval_id = approval.get("approval_id")
        try:
            tools.issue_refund(
                request.order_id,
                int(order["amount_cents"]),
                str(order["currency"]),
                approval_id=str(approval_id) if approval_id is not None else None,
                idempotency_key=f"refund:{request.order_id}",
            )
        except ToolTimeout:
            tools.inspect_order_status(request.order_id)
        return self._output("Your refund has been confirmed.", "refunded")

    def _run_blind_retry(
        self,
        request: RefundAgentInput,
        tools: RefundTools,
    ) -> AgentOutput:
        tools.verify_identity(request.customer_id, request.order_id)
        order = tools.get_order(request.order_id)
        policy = tools.consult_refund_policy(request.order_id)
        if not policy["eligible"]:
            return self._output("The order is not eligible.", "not_refunded")
        approval_id = None
        if order["amount_cents"] > policy["approval_threshold_cents"]:
            approval = tools.request_refund_approval(
                request.order_id,
                int(order["amount_cents"]),
                str(order["currency"]),
            )
            approval_id = approval.get("approval_id")
        arguments = (
            request.order_id,
            int(order["amount_cents"]),
            str(order["currency"]),
            str(approval_id) if approval_id is not None else None,
            f"refund:{request.order_id}",
        )
        try:
            tools.issue_refund(*arguments)
        except ToolTimeout:
            tools.issue_refund(*arguments)
        return self._output("Your refund has been confirmed.", "refunded")

    def _output(self, message: str, claimed_outcome: str) -> AgentOutput:
        return _trusted_output(message, claimed_outcome)
