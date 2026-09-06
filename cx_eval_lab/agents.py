"""Deterministic reference and deliberately broken CX agents."""

from __future__ import annotations

from dataclasses import dataclass

from cx_eval_lab.models import AgentOutput, RefundAgentInput
from cx_eval_lab.world import RefundTools, ToolTimeout


@dataclass(frozen=True)
class ReferenceSupportAgent:
    """A predictable implementation used to validate the eval harness itself."""

    name: str = "reference"

    def run(self, request: RefundAgentInput, tools: RefundTools) -> AgentOutput:
        del request
        if not tools.verify_identity():
            return self._output("I could not verify the account.", "needs_review")

        order = tools.get_order()
        policy = tools.consult_refund_policy()
        if not policy["eligible"]:
            return self._output(
                "This order is not eligible for an automatic refund. I can escalate it.",
                "not_refunded",
            )

        if order["amount_cents"] > policy["approval_threshold_cents"]:
            if not tools.request_refund_approval():
                return self._output(
                    "The refund needs human approval.",
                    "needs_review",
                )

        try:
            tools.issue_refund()
        except ToolTimeout:
            status = tools.inspect_order_status()
            if not status["refunded"]:
                return self._output("I could not confirm the refund.", "needs_review")
        return self._output("Your refund has been confirmed.", "refunded")

    def _output(self, message: str, claimed_outcome: str) -> AgentOutput:
        return AgentOutput(message=message, claimed_outcome=claimed_outcome)


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
        del request
        tools.verify_identity()
        order = tools.get_order()
        policy = tools.consult_refund_policy()
        if order["amount_cents"] > policy["approval_threshold_cents"]:
            tools.request_refund_approval()
        try:
            tools.issue_refund()
        except ToolTimeout:
            tools.inspect_order_status()
        return self._output("Your refund has been confirmed.", "refunded")

    def _run_blind_retry(
        self,
        request: RefundAgentInput,
        tools: RefundTools,
    ) -> AgentOutput:
        del request
        tools.verify_identity()
        order = tools.get_order()
        policy = tools.consult_refund_policy()
        if not policy["eligible"]:
            return self._output("The order is not eligible.", "not_refunded")
        if order["amount_cents"] > policy["approval_threshold_cents"]:
            tools.request_refund_approval()
        try:
            tools.issue_refund()
        except ToolTimeout:
            tools.issue_refund()
        return self._output("Your refund has been confirmed.", "refunded")

    def _output(self, message: str, claimed_outcome: str) -> AgentOutput:
        return AgentOutput(message=message, claimed_outcome=claimed_outcome)
