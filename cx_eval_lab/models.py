"""Immutable domain records shared by the CX system and eval harness."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


VALID_OUTCOMES = frozenset({"refunded", "not_refunded"})
VALID_CLAIMED_OUTCOMES = frozenset({"refunded", "not_refunded", "needs_review"})
VALID_TRANSACTION_STATUS_CLAIMS = frozenset(
    {"committed", "not_committed", "unknown"}
)
VALID_SETTLEMENT_STATUS_CLAIMS = frozenset(
    {"settled", "not_confirmed", "not_claimed", "unknown"}
)


@dataclass(frozen=True)
class TrustedMessageTemplate:
    template_id: str
    message: str
    transaction_status_claim: str
    settlement_status_claim: str


TRUSTED_MESSAGE_TEMPLATES = (
    TrustedMessageTemplate(
        "refund_committed_v1",
        "Your refund has been confirmed.",
        "committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "refund_committed_short_v1",
        "Refund confirmed.",
        "committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "refund_committed_settlement_unconfirmed_v1",
        "Your refund has been confirmed, but we cannot confirm bank settlement yet.",
        "committed",
        "not_confirmed",
    ),
    TrustedMessageTemplate(
        "not_eligible_v1",
        "This order is not eligible for an automatic refund. I can escalate it.",
        "not_committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "not_eligible_plain_v1",
        "This order is not eligible for a refund.",
        "not_committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "not_eligible_short_v1",
        "The order is not eligible.",
        "not_committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "human_approval_v1",
        "The refund needs human approval.",
        "not_committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "identity_unverified_v1",
        "I could not verify the account.",
        "not_committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "refund_unconfirmed_v1",
        "I could not confirm the refund.",
        "not_committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "review_v1",
        "This needs human review.",
        "not_committed",
        "not_claimed",
    ),
    TrustedMessageTemplate(
        "execution_failed_v1",
        "The agent did not complete this case.",
        "not_committed",
        "not_claimed",
    ),
)


def trusted_message_template_by_id(
    template_id: str,
) -> TrustedMessageTemplate | None:
    return next(
        (
            template
            for template in TRUSTED_MESSAGE_TEMPLATES
            if template.template_id == template_id
        ),
        None,
    )


def trusted_message_template_by_message(
    message: str,
) -> TrustedMessageTemplate | None:
    return next(
        (template for template in TRUSTED_MESSAGE_TEMPLATES if template.message == message),
        None,
    )


@dataclass(frozen=True)
class RefundAgentInput:
    """The case fields visible to the system under test."""

    utterance: str
    customer_id: str
    order_id: str
    candidate_order_ids: tuple[str, ...]


@dataclass(frozen=True)
class RefundWorldSeed:
    """Operational backend state, excluding evaluator labels and slices."""

    customer_id: str
    order_id: str
    amount_cents: int
    currency: str
    eligible: bool
    approval_threshold_cents: int
    simulate_timeout_after_commit: bool
    competing_order_ids: tuple[str, ...] = ()


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
    currency: str = "USD"
    competing_order_ids: tuple[str, ...] = ()
    simulate_timeout_after_commit: bool = False
    dataset_version: str = "refund-v1"

    def __post_init__(self) -> None:
        if not isinstance(self.slices, (list, tuple)) or isinstance(self.slices, str):
            raise ValueError("slices must be a list or tuple of labels")
        object.__setattr__(self, "slices", tuple(self.slices))
        if not isinstance(self.competing_order_ids, (list, tuple)) or isinstance(
            self.competing_order_ids, str
        ):
            raise ValueError("competing_order_ids must be a list or tuple")
        object.__setattr__(self, "competing_order_ids", tuple(self.competing_order_ids))
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
        if not isinstance(self.currency, str) or len(self.currency) != 3:
            raise ValueError("currency must be a three-letter code")
        object.__setattr__(self, "currency", self.currency.upper())
        if self.order_id in self.competing_order_ids:
            raise ValueError("competing orders cannot repeat the target order")
        if len(self.competing_order_ids) != len(set(self.competing_order_ids)):
            raise ValueError("competing order identifiers must be unique")
        if self.expected_outcome not in VALID_OUTCOMES:
            raise ValueError(f"unsupported expected outcome: {self.expected_outcome}")
        if not self.slices or not all(
            isinstance(slice_name, str) and slice_name for slice_name in self.slices
        ):
            raise ValueError("every case must declare valid slice labels")

    @property
    def agent_input(self) -> RefundAgentInput:
        return RefundAgentInput(
            utterance=self.utterance,
            customer_id=self.customer_id,
            order_id=self.order_id,
            candidate_order_ids=(self.order_id, *self.competing_order_ids),
        )

    @property
    def world_seed(self) -> RefundWorldSeed:
        return RefundWorldSeed(
            customer_id=self.customer_id,
            order_id=self.order_id,
            amount_cents=self.amount_cents,
            currency=self.currency,
            eligible=self.eligible,
            approval_threshold_cents=self.approval_threshold_cents,
            simulate_timeout_after_commit=self.simulate_timeout_after_commit,
            competing_order_ids=self.competing_order_ids,
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
    verified_customer_id: str | None = None
    verified_order_id: str | None = None
    policy_consulted: bool = False
    policy_order_id: str | None = None
    approval_granted: bool = False
    approval_id: str | None = None
    approval_order_id: str | None = None
    approved_amount_cents: int | None = None
    approved_currency: str | None = None
    refund_idempotency_keys: tuple[str, ...] = ()
    timeout_delivered: bool = False

    @property
    def refund_transaction_count(self) -> int:
        return len(self.refund_idempotency_keys)


@dataclass(frozen=True)
class ResolutionResponse:
    message: str
    claimed_outcome: str
    transaction_status_claim: str = "unknown"
    settlement_status_claim: str = "not_claimed"
    arrival_commitment_days: int | None = None
    message_template_id: str | None = None
    escalation_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_resolution_claims(self)


@dataclass(frozen=True)
class RuntimeEvidence:
    provider: str
    model_id: str
    response_ids: tuple[str, ...]
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None
    cost_source: str

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "response_ids": list(self.response_ids)}


@dataclass(frozen=True)
class AgentOutput:
    message: str
    claimed_outcome: str
    runtime_evidence: RuntimeEvidence | None = None
    transaction_status_claim: str = "unknown"
    settlement_status_claim: str = "not_claimed"
    arrival_commitment_days: int | None = None
    message_template_id: str | None = None
    escalation_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_resolution_claims(self)


@dataclass(frozen=True)
class SemanticEvaluationReceipt:
    """Evaluator-owned qualification evidence for one free-form message."""

    criterion_id: str
    evaluator_version: str
    calibration_receipt_hash: str
    message_hash: str
    structured_claim_hash: str
    passed: bool
    abstained: bool

    def __post_init__(self) -> None:
        import re

        sha256_pattern = re.compile(r"^sha256:[0-9a-f]{64}$")
        if not self.criterion_id or not self.evaluator_version:
            raise ValueError("semantic criterion and evaluator version are required")
        hashes = (
            self.calibration_receipt_hash,
            self.message_hash,
            self.structured_claim_hash,
        )
        if not all(sha256_pattern.fullmatch(value) for value in hashes):
            raise ValueError("semantic receipt hashes must be sha256: digests")
        if not isinstance(self.passed, bool) or not isinstance(self.abstained, bool):
            raise ValueError("semantic receipt decisions must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_resolution_claims(value: ResolutionResponse | AgentOutput) -> None:
    if not isinstance(value.message, str) or not value.message:
        raise ValueError("customer message is required")
    if value.claimed_outcome not in VALID_CLAIMED_OUTCOMES:
        raise ValueError(f"unsupported claimed outcome: {value.claimed_outcome}")
    if value.transaction_status_claim not in VALID_TRANSACTION_STATUS_CLAIMS:
        raise ValueError("unsupported transaction status claim")
    if value.settlement_status_claim not in VALID_SETTLEMENT_STATUS_CLAIMS:
        raise ValueError("unsupported settlement status claim")
    days = value.arrival_commitment_days
    if days is not None and (
        not isinstance(days, int) or isinstance(days, bool) or days < 0
    ):
        raise ValueError("arrival commitment days must be a non-negative integer")
    if value.message_template_id is not None and (
        not isinstance(value.message_template_id, str) or not value.message_template_id
    ):
        raise ValueError("message_template_id must be a non-empty string")
    if value.escalation_reason is not None and (
        not isinstance(value.escalation_reason, str) or not value.escalation_reason
    ):
        raise ValueError("escalation_reason must be a non-empty string")


@dataclass(frozen=True)
class MeasurementProfile:
    """Harness-owned synthetic operating measurements for deterministic runs."""

    latency_ms: int
    cost_usd_per_case: float
    evidence_kind: str = "synthetic"
    source: str = "harness-owned teaching profile"

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
        if self.evidence_kind not in {"synthetic", "measured"}:
            raise ValueError("evidence_kind must be synthetic or measured")
        if not self.source:
            raise ValueError("measurement source is required")


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
    false_message_claim_count: int = 0
    unqualified_message_count: int = 0
    semantic_abstention_count: int = 0
    unjustified_escalation_count: int = 0
    human_intervention_count: int = 0
    unresolved_work_count: int = 0
    resolution_status: str = "resolved"
    runtime_evidence: RuntimeEvidence | None = None
    semantic_evaluation_receipt: SemanticEvaluationReceipt | None = None

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
            "false_message_claim_count": self.false_message_claim_count,
            "unqualified_message_count": self.unqualified_message_count,
            "semantic_abstention_count": self.semantic_abstention_count,
            "unjustified_escalation_count": self.unjustified_escalation_count,
            "human_intervention_count": self.human_intervention_count,
            "unresolved_work_count": self.unresolved_work_count,
            "resolution_status": self.resolution_status,
            "runtime_evidence": (
                None
                if self.runtime_evidence is None
                else self.runtime_evidence.to_dict()
            ),
            "semantic_evaluation_receipt": (
                None
                if self.semantic_evaluation_receipt is None
                else self.semantic_evaluation_receipt.to_dict()
            ),
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
    measurement_kind: str = "synthetic"
    measurement_source: str = "harness-owned teaching profile"
    false_message_claim_count: int = 0
    unqualified_message_count: int = 0
    semantic_abstention_count: int = 0
    unjustified_escalation_count: int = 0
    human_intervention_count: int = 0
    unresolved_work_count: int = 0

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
            "measurement_kind": self.measurement_kind,
            "measurement_source": self.measurement_source,
            "false_message_claim_count": self.false_message_claim_count,
            "unqualified_message_count": self.unqualified_message_count,
            "semantic_abstention_count": self.semantic_abstention_count,
            "unjustified_escalation_count": self.unjustified_escalation_count,
            "human_intervention_count": self.human_intervention_count,
            "unresolved_work_count": self.unresolved_work_count,
            "case_results": [result.to_dict() for result in self.case_results],
        }
