"""Immutable domain records shared by the CX system and eval harness."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


VALID_OUTCOMES = frozenset({"refunded", "not_refunded"})
VALID_CLAIMED_OUTCOMES = frozenset({"refunded", "not_refunded", "needs_review"})


@dataclass(frozen=True)
class RefundAgentInput:
    """The case fields visible to the system under test."""

    utterance: str


@dataclass(frozen=True)
class RefundWorldSeed:
    """Operational backend state, excluding evaluator labels and slices."""

    customer_id: str
    order_id: str
    amount_cents: int
    eligible: bool
    approval_threshold_cents: int
    simulate_timeout_after_commit: bool


@dataclass(frozen=True)
class RefundCase:
    case_id: str
    customer_id: str
    order_id: str
    utterance: str
    amount_cents: int
    eligible: bool
    approval_threshold_cents: int
    expected_outcome: str
    slices: tuple[str, ...]
    simulate_timeout_after_commit: bool = False
    dataset_version: str = "refund-v0"

    def __post_init__(self) -> None:
        if not isinstance(self.slices, (list, tuple)) or isinstance(self.slices, str):
            raise ValueError("slices must be a list or tuple of labels")
        object.__setattr__(self, "slices", tuple(self.slices))
        required_strings = (
            self.case_id,
            self.customer_id,
            self.order_id,
            self.utterance,
            self.dataset_version,
        )
        if not all(isinstance(value, str) and value for value in required_strings):
            raise ValueError("case, customer, and order identifiers are required")
        if not isinstance(self.eligible, bool):
            raise ValueError("eligible must be a boolean")
        if not isinstance(self.simulate_timeout_after_commit, bool):
            raise ValueError("simulate_timeout_after_commit must be a boolean")
        invalid_amount_type = not isinstance(self.amount_cents, int) or isinstance(
            self.amount_cents, bool
        )
        invalid_threshold_type = not isinstance(
            self.approval_threshold_cents, int
        ) or isinstance(self.approval_threshold_cents, bool)
        if invalid_amount_type or invalid_threshold_type:
            raise ValueError("monetary values must be integers")
        if self.amount_cents < 0 or self.approval_threshold_cents < 0:
            raise ValueError("monetary values cannot be negative")
        if self.expected_outcome not in VALID_OUTCOMES:
            raise ValueError(f"unsupported expected outcome: {self.expected_outcome}")
        if not self.slices or not all(
            isinstance(slice_name, str) and slice_name for slice_name in self.slices
        ):
            raise ValueError("every case must declare valid slice labels")

    @property
    def agent_input(self) -> RefundAgentInput:
        return RefundAgentInput(utterance=self.utterance)

    @property
    def world_seed(self) -> RefundWorldSeed:
        return RefundWorldSeed(
            customer_id=self.customer_id,
            order_id=self.order_id,
            amount_cents=self.amount_cents,
            eligible=self.eligible,
            approval_threshold_cents=self.approval_threshold_cents,
            simulate_timeout_after_commit=self.simulate_timeout_after_commit,
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> RefundCase:
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "slices": list(self.slices)}


@dataclass(frozen=True)
class ToolEvent:
    sequence: int
    tool: str
    status: str
    details: tuple[tuple[str, str | int | bool], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "tool": self.tool,
            "status": self.status,
            "details": dict(self.details),
        }


@dataclass(frozen=True)
class WorldSnapshot:
    identity_verified: bool = False
    policy_consulted: bool = False
    approval_granted: bool = False
    refund_idempotency_keys: tuple[str, ...] = ()
    timeout_delivered: bool = False

    @property
    def refund_transaction_count(self) -> int:
        return len(self.refund_idempotency_keys)


@dataclass(frozen=True)
class ResolutionResponse:
    message: str
    claimed_outcome: str

    def __post_init__(self) -> None:
        if self.claimed_outcome not in VALID_CLAIMED_OUTCOMES:
            raise ValueError(f"unsupported claimed outcome: {self.claimed_outcome}")


@dataclass(frozen=True)
class AgentOutput:
    message: str
    claimed_outcome: str

    def __post_init__(self) -> None:
        if self.claimed_outcome not in VALID_CLAIMED_OUTCOMES:
            raise ValueError(f"unsupported claimed outcome: {self.claimed_outcome}")


@dataclass(frozen=True)
class MeasurementProfile:
    """Harness-owned synthetic operating measurements for deterministic runs."""

    latency_ms: int
    cost_usd_per_case: float

    def __post_init__(self) -> None:
        if (
            not isinstance(self.latency_ms, int)
            or isinstance(self.latency_ms, bool)
            or self.latency_ms < 0
        ):
            raise ValueError("latency_ms must be a non-negative integer")
        if (
            not isinstance(self.cost_usd_per_case, (int, float))
            or isinstance(self.cost_usd_per_case, bool)
            or not math.isfinite(self.cost_usd_per_case)
            or self.cost_usd_per_case < 0
        ):
            raise ValueError("cost_usd_per_case must be finite and non-negative")


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    observed: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str
    slices: tuple[str, ...]
    passed: bool
    unauthorized_action_count: int
    duplicate_refund_count: int
    unsafe_timeout_recovery_count: int
    false_success_claim_count: int
    latency_ms: int
    cost_usd: float | None
    checks: tuple[CheckResult, ...]
    events: tuple[ToolEvent, ...]
    final_message: str
    claimed_outcome: str
    execution_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "slices": list(self.slices),
            "passed": self.passed,
            "unauthorized_action_count": self.unauthorized_action_count,
            "duplicate_refund_count": self.duplicate_refund_count,
            "unsafe_timeout_recovery_count": self.unsafe_timeout_recovery_count,
            "false_success_claim_count": self.false_success_claim_count,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "checks": [check.to_dict() for check in self.checks],
            "events": [event.to_dict() for event in self.events],
            "final_message": self.final_message,
            "claimed_outcome": self.claimed_outcome,
            "execution_error": self.execution_error,
        }


@dataclass(frozen=True)
class EvaluationReport:
    dataset_version: str
    agent_name: str
    case_results: tuple[CaseEvaluation, ...]
    task_success_rate: float
    slice_success_rates: tuple[tuple[str, float], ...]
    unauthorized_action_count: int
    duplicate_refund_count: int
    unsafe_timeout_recovery_count: int
    false_success_claim_count: int
    p95_latency_ms: int
    cost_per_success_usd: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "agent_name": self.agent_name,
            "case_count": len(self.case_results),
            "task_success_rate": self.task_success_rate,
            "slice_success_rates": dict(self.slice_success_rates),
            "unauthorized_action_count": self.unauthorized_action_count,
            "duplicate_refund_count": self.duplicate_refund_count,
            "unsafe_timeout_recovery_count": self.unsafe_timeout_recovery_count,
            "false_success_claim_count": self.false_success_claim_count,
            "p95_latency_ms": self.p95_latency_ms,
            "cost_per_success_usd": self.cost_per_success_usd,
            "case_results": [result.to_dict() for result in self.case_results],
        }
