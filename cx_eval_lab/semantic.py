"""Evaluator-owned semantic stage and scoped calibration registry.

Registry entries are trusted operator inputs, not self-attestations by an agent
or judge. Synthetic entries exercise plumbing; they never qualify measured runs.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable, Protocol

from cx_eval_lab.evaluators import hash_customer_message, hash_evidence_context, hash_structured_claims
from cx_eval_lab.evidence import canonical_hash
from cx_eval_lab.models import RuntimeEvidence, SemanticEvaluationReceipt
from cx_eval_lab.statistical_study import exact_loss_interval


CRITERION = "refund_customer_message_truth_v1"


def _timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("qualification timestamps must include a timezone")
    return parsed


@dataclass(frozen=True)
class CalibrationRecord:
    evaluator_version: str
    configuration_hash: str
    criterion_id: str
    dataset_versions: tuple[str, ...]
    policy_versions: tuple[str, ...]
    slice_scopes: tuple[tuple[str, ...], ...]
    issued_at: str
    expires_at: str
    evidence_kind: str
    label_artifact_hash: str
    truthful_examples: int
    false_examples: int
    false_passes: int
    false_blocks: int
    minimum_per_class: int
    max_false_pass_upper: float
    max_false_block_upper: float
    abstentions: int = 0
    max_abstention_rate: float = 0.20

    def __post_init__(self):
        for digest in (self.configuration_hash, self.label_artifact_hash):
            if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
                raise ValueError("qualification hashes must be SHA-256 digests")
        if not self.evaluator_version or not self.criterion_id:
            raise ValueError("criterion and evaluator version are required")
        if self.evidence_kind not in {"synthetic", "human_reviewed"}:
            raise ValueError("qualification evidence kind must be explicit")
        if _timestamp(self.expires_at) <= _timestamp(self.issued_at):
            raise ValueError("qualification expiry must follow issue time")
        for name in ("dataset_versions", "policy_versions"):
            values = tuple(getattr(self, name))
            if not values or any(not isinstance(v, str) or not v for v in values):
                raise ValueError("nonempty qualification scopes are required")
            object.__setattr__(self, name, values)
        scopes = tuple(sorted(tuple(sorted(scope)) for scope in self.slice_scopes))
        if len(scopes) != 1:
            raise ValueError("each calibration record must cover one joint slice scope")
        if not scopes or any(not scope or any(not isinstance(v, str) or not v for v in scope)
                             for scope in scopes):
            raise ValueError("explicit joint slice scopes are required")
        object.__setattr__(self, "slice_scopes", scopes)
        for errors, count in ((self.false_passes, self.false_examples),
                              (self.false_blocks, self.truthful_examples)):
            if type(errors) is not int or type(count) is not int or not 0 <= errors <= count <= 500 or count < 1:
                raise ValueError("calibration counts require 0 <= errors <= examples <= 500")
        if type(self.minimum_per_class) is not int or self.minimum_per_class < 1:
            raise ValueError("minimum calibration count must be positive")
        if (type(self.abstentions) is not int or not 0 <= self.abstentions
                <= self.false_blocks + self.false_examples - self.false_passes):
            raise ValueError("abstention count conflicts with class-conditional outcomes")
        for limit in (self.max_false_pass_upper, self.max_false_block_upper, self.max_abstention_rate):
            if isinstance(limit, bool) or not isinstance(limit, (float, int)) or not 0 <= limit <= 1:
                raise ValueError("error-rate limits must be probabilities")

    @property
    def content_hash(self):
        return canonical_hash(asdict(self))

    @property
    def error_bounds(self):
        # Upper endpoint of a 90% equal-tailed interval is a one-sided 95% bound.
        return {
            "false_pass_upper_95": exact_loss_interval(self.false_passes, self.false_examples, 0.90)[1],
            "false_block_upper_95": exact_loss_interval(self.false_blocks, self.truthful_examples, 0.90)[1],
        }

    def rejection(self, judge, case, policy_version, now, allow_synthetic):
        if self.evidence_kind == "synthetic" and not allow_synthetic:
            return "synthetic_qualification_not_permitted"
        if not _timestamp(self.issued_at) <= now < _timestamp(self.expires_at):
            return "qualification_not_current"
        if (self.criterion_id != CRITERION or self.evaluator_version != judge.evaluator_version
                or self.configuration_hash != judge.configuration_hash):
            return "evaluator_configuration_mismatch"
        if (case.dataset_version not in self.dataset_versions or policy_version not in self.policy_versions
                or tuple(sorted(case.slices)) not in self.slice_scopes):
            return "outside_qualified_scope"
        if min(self.truthful_examples, self.false_examples) < self.minimum_per_class:
            return "insufficient_calibration_examples"
        if self.abstentions / (self.truthful_examples + self.false_examples) > self.max_abstention_rate:
            return "calibration_abstention_limit_exceeded"
        bounds = self.error_bounds
        if (bounds["false_pass_upper_95"] > self.max_false_pass_upper
                or bounds["false_block_upper_95"] > self.max_false_block_upper):
            return "calibration_error_bound_exceeded"
        return None


@dataclass(frozen=True)
class CalibrationRegistry:
    records: tuple[CalibrationRecord, ...]
    revoked_hashes: frozenset[str] = frozenset()

    def __post_init__(self):
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "revoked_hashes", frozenset(self.revoked_hashes))
        if len({record.content_hash for record in self.records}) != len(self.records):
            raise ValueError("duplicate calibration registration")

    def lookup(self, digest):
        if digest in self.revoked_hashes:
            return None
        return next((record for record in self.records if record.content_hash == digest), None)


@dataclass(frozen=True)
class SemanticRequest:
    evidence_json: str
    criterion_id: str = CRITERION


@dataclass(frozen=True)
class SemanticJudgment:
    verdict: str
    explanation: str
    runtime_evidence: RuntimeEvidence | None = None

    def __post_init__(self):
        if self.verdict not in {"pass", "fail", "abstain"} or not self.explanation:
            raise ValueError("judge requires pass/fail/abstain and an explanation")


class SemanticJudge(Protocol):
    evaluator_version: str
    configuration_hash: str

    def evaluate(self, request: SemanticRequest) -> SemanticJudgment: ...


@dataclass(frozen=True)
class SemanticStage:
    judge: SemanticJudge
    registry: CalibrationRegistry
    calibration_hash: str
    clock: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    allow_synthetic: bool = False

    def grade(self, case, output, events, state, *, execution_error=None,
              policy_version="refund-policy-v1", measurement_kind="measured"):
        started = time.perf_counter()
        record = self.registry.lookup(self.calibration_hash)
        synthetic_allowed = self.allow_synthetic and measurement_kind == "synthetic"
        reason = "qualification_missing_or_revoked" if record is None else record.rejection(
            self.judge, case, policy_version, self.clock(), synthetic_allowed)
        if reason:
            return None, frozenset(), {"status": "unqualified", "reason": reason}
        # Omit expected outcome, experiment arm, evaluator slices, and injected faults.
        request = SemanticRequest(json.dumps({
            "customer_request": asdict(case.agent_input), "output": {
                key: value for key, value in asdict(output).items() if key != "runtime_evidence"
            },
            "events": [event.to_dict() for event in events], "final_state": asdict(state),
            "policy_version": policy_version, "execution_error": execution_error,
            "authoritative_order": {"amount_cents": case.amount_cents, "currency": case.currency,
                "eligible": case.eligible, "approval_threshold_cents": case.approval_threshold_cents},
        }, sort_keys=True, ensure_ascii=False))
        try:
            judgment = self.judge.evaluate(request)
            if not isinstance(judgment, SemanticJudgment):
                raise TypeError("judge returned an invalid contract")
        except Exception as error:
            judgment = SemanticJudgment("abstain", f"judge_error:{type(error).__name__}")
        # A slow call must not carry qualification beyond expiry.
        reason = record.rejection(self.judge, case, policy_version, self.clock(), synthetic_allowed)
        audit = {"status": "unqualified" if reason else "graded", "reason": reason,
                 "qualification": asdict(record), "error_bounds": record.error_bounds,
                 "request": json.loads(request.evidence_json),
                 "request_hash": canonical_hash(json.loads(request.evidence_json)),
                 "judgment": asdict(judgment),
                 "judge_latency_ms": round((time.perf_counter() - started) * 1000),
                 "authority": "lab_only"}
        if reason:
            return None, frozenset(), audit
        receipt = SemanticEvaluationReceipt(
            CRITERION, self.judge.evaluator_version, record.content_hash,
            hash_customer_message(output.message), hash_structured_claims(output),
            judgment.verdict == "pass", judgment.verdict == "abstain",
            hash_evidence_context(case, events, state, execution_error=execution_error,
                                  policy_version=policy_version),
        )
        return receipt, frozenset({record.content_hash}), audit
