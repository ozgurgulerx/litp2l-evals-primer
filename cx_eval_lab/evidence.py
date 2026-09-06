"""Immutable manifests and evidence-authority receipts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from cx_eval_lab.statistics import PairedComparison, PairedTrial


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    created_at: str
    code_revision: str
    model_id: str
    prompt_version: str
    tool_version: str
    dataset_version: str
    evaluator_version: str
    policy_version: str
    repetitions: int
    measurement_kind: str
    input_hashes: tuple[tuple[str, str], ...]
    invalidation_rules: tuple[str, ...]

    def __post_init__(self) -> None:
        required = (
            self.experiment_id,
            self.created_at,
            self.code_revision,
            self.model_id,
            self.prompt_version,
            self.tool_version,
            self.dataset_version,
            self.evaluator_version,
            self.policy_version,
        )
        if not all(isinstance(value, str) and value for value in required):
            raise ValueError("all manifest identifiers and versions are required")
        if not isinstance(self.repetitions, int) or self.repetitions < 1:
            raise ValueError("repetitions must be a positive integer")
        if self.measurement_kind not in {"synthetic", "measured"}:
            raise ValueError("measurement_kind must be synthetic or measured")
        hashes = tuple(sorted(tuple(item) for item in self.input_hashes))
        if not hashes or any(len(item) != 2 or not all(item) for item in hashes):
            raise ValueError("input_hashes must contain named non-empty hashes")
        if len(hashes) != len({name for name, _ in hashes}):
            raise ValueError("input hash names must be unique")
        rules = tuple(self.invalidation_rules)
        if not rules or not all(isinstance(rule, str) and rule for rule in rules):
            raise ValueError("at least one invalidation rule is required")
        object.__setattr__(self, "input_hashes", hashes)
        object.__setattr__(self, "invalidation_rules", rules)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        return {
            **value,
            "input_hashes": [list(item) for item in self.input_hashes],
            "invalidation_rules": list(self.invalidation_rules),
        }

    @property
    def content_hash(self) -> str:
        payload = json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(payload).hexdigest()}"


@dataclass(frozen=True)
class PairedExperiment:
    manifest: ExperimentManifest
    baseline_trials: tuple[PairedTrial, ...]
    candidate_trials: tuple[PairedTrial, ...]

    @property
    def all_trials(self) -> tuple[PairedTrial, ...]:
        return (*self.baseline_trials, *self.candidate_trials)

    @property
    def recomputed_trial_count(self) -> int:
        return len(self.all_trials)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "manifest_hash": self.manifest.content_hash,
            "baseline_trials": [trial.to_dict() for trial in self.baseline_trials],
            "candidate_trials": [trial.to_dict() for trial in self.candidate_trials],
        }


@dataclass(frozen=True)
class EvidenceReceipt:
    experiment_id: str
    manifest_hash: str
    state: str
    action: str
    authority_ceiling: str
    raw_artifact_hash: str
    deterministic_tests_passed: bool
    hard_failure_count: int
    comparison: PairedComparison
    prerequisite_ids: tuple[str, ...]
    invalidation_rules: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "comparison": self.comparison.to_dict(),
            "prerequisite_ids": list(self.prerequisite_ids),
            "invalidation_rules": list(self.invalidation_rules),
        }


def build_evidence_receipt(
    *,
    manifest: ExperimentManifest,
    comparison: PairedComparison,
    hard_failure_count: int,
    raw_artifact_hash: str,
    deterministic_tests_passed: bool,
) -> EvidenceReceipt:
    if hard_failure_count < 0:
        raise ValueError("hard_failure_count cannot be negative")
    prerequisites = (
        "typed_tool_boundary",
        "semantic_state_grading",
        "repeated_paired_trials",
        "minimum_evidence",
    )
    complete = bool(raw_artifact_hash) and deterministic_tests_passed
    if not complete:
        state, action, authority = "buildable", "block", "none"
    elif hard_failure_count:
        state, action, authority = "evidence_ready", "block", "none"
    elif comparison.status == "inconclusive":
        state, action, authority = "evidence_ready", "hold", "none"
    elif comparison.status != "pass":
        state, action, authority = "evidence_ready", "block", "none"
    elif manifest.measurement_kind == "synthetic":
        state, action, authority = "evidence_ready", "lab_pass", "lab_only"
    else:
        state, action, authority = "qualified", "canary_eligible", "bounded_canary"
    return EvidenceReceipt(
        experiment_id=manifest.experiment_id,
        manifest_hash=manifest.content_hash,
        state=state,
        action=action,
        authority_ceiling=authority,
        raw_artifact_hash=raw_artifact_hash,
        deterministic_tests_passed=deterministic_tests_passed,
        hard_failure_count=hard_failure_count,
        comparison=comparison,
        prerequisite_ids=prerequisites,
        invalidation_rules=manifest.invalidation_rules,
    )
