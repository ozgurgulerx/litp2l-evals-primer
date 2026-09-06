"""Immutable manifests and fail-closed evidence-authority receipts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Any

from cx_eval_lab.statistics import (
    PairedComparison,
    PairedTrial,
    paired_non_inferiority,
)


_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_METHOD_AUTHORITY_CEILINGS = {
    # This small-sample teaching implementation is not a production release test.
    "clustered_normal_interval": "lab_only",
}
_REQUIRED_PREREQUISITES = frozenset(
    {"typed_tool_boundary", "semantic_state_grading"}
)


def canonical_hash(value: Any) -> str:
    """Return a deterministic SHA-256 identifier for a JSON-compatible value."""

    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    created_at: str
    valid_until: str
    code_revision: str
    model_id: str
    prompt_version: str
    tool_version: str
    dataset_version: str
    evaluator_version: str
    policy_version: str
    environment_version: str
    population_hash: str
    repetitions: int
    measurement_kind: str
    estimand: str
    statistical_method: str
    non_inferiority_margin: float
    confidence_level: float
    minimum_independent_clusters: int
    sequential_policy: str
    input_hashes: tuple[tuple[str, str], ...]
    invalidation_rules: tuple[str, ...]

    def __post_init__(self) -> None:
        required = (
            self.experiment_id,
            self.created_at,
            self.valid_until,
            self.code_revision,
            self.model_id,
            self.prompt_version,
            self.tool_version,
            self.dataset_version,
            self.evaluator_version,
            self.policy_version,
            self.environment_version,
            self.estimand,
            self.statistical_method,
            self.sequential_policy,
        )
        if not all(isinstance(value, str) and value for value in required):
            raise ValueError("all manifest identifiers, versions, and plans are required")
        created_at = _parse_timestamp(self.created_at, "created_at")
        valid_until = _parse_timestamp(self.valid_until, "valid_until")
        if valid_until <= created_at:
            raise ValueError("valid_until must be later than created_at")
        if not isinstance(self.repetitions, int) or self.repetitions < 1:
            raise ValueError("repetitions must be a positive integer")
        if self.measurement_kind not in {"synthetic", "measured"}:
            raise ValueError("measurement_kind must be synthetic or measured")
        if (
            self.measurement_kind == "measured"
            and self.code_revision == "working-tree-unpinned"
        ):
            raise ValueError("measured evidence requires a pinned code revision")
        if self.statistical_method not in _METHOD_AUTHORITY_CEILINGS:
            raise ValueError("statistical_method is not registered")
        _validate_sha256(self.population_hash, "population_hash")
        if not 0 <= self.non_inferiority_margin <= 1:
            raise ValueError("non_inferiority_margin must be in [0, 1]")
        if not 0 < self.confidence_level < 1:
            raise ValueError("confidence_level must be between 0 and 1")
        if self.minimum_independent_clusters < 1:
            raise ValueError("minimum_independent_clusters must be positive")
        hashes = tuple(sorted(tuple(item) for item in self.input_hashes))
        if not hashes or any(len(item) != 2 or not all(item) for item in hashes):
            raise ValueError("input_hashes must contain named non-empty hashes")
        if len(hashes) != len({name for name, _ in hashes}):
            raise ValueError("input hash names must be unique")
        for name, value in hashes:
            _validate_sha256(value, f"input hash {name}")
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
        return canonical_hash(self.to_dict())


@dataclass(frozen=True)
class PairedExperiment:
    manifest: ExperimentManifest
    baseline_trials: tuple[PairedTrial, ...]
    candidate_trials: tuple[PairedTrial, ...]
    trial_artifacts: tuple = ()

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
            "trial_artifacts": [artifact.to_dict() for artifact in self.trial_artifacts],
        }


@dataclass(frozen=True)
class DeterministicTestReceipt:
    """Content-addressed reference to a test result produced outside the gate."""

    suite_id: str
    code_revision: str
    checks: tuple[tuple[str, bool], ...]
    artifact_hash: str

    def __post_init__(self) -> None:
        if not self.suite_id or not self.code_revision:
            raise ValueError("test suite and code revision are required")
        checks = tuple(sorted(tuple(item) for item in self.checks))
        if not checks or any(
            len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            or not isinstance(item[1], bool)
            for item in checks
        ):
            raise ValueError("test receipt requires named boolean checks")
        if len(checks) != len({name for name, _ in checks}):
            raise ValueError("test check names must be unique")
        _validate_sha256(self.artifact_hash, "test artifact hash")
        object.__setattr__(self, "checks", checks)

    @property
    def passed(self) -> bool:
        return all(result for _, result in self.checks)

    @property
    def receipt_hash(self) -> str:
        return canonical_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "code_revision": self.code_revision,
            "checks": [list(item) for item in self.checks],
            "artifact_hash": self.artifact_hash,
            "passed": self.passed,
        }


@dataclass(frozen=True)
class PrerequisiteReceipt:
    """Content-addressed qualification state for one required capability."""

    prerequisite_id: str
    checks: tuple[tuple[str, bool], ...]
    evidence_hash: str

    def __post_init__(self) -> None:
        if not self.prerequisite_id:
            raise ValueError("prerequisite_id is required")
        checks = tuple(sorted(tuple(item) for item in self.checks))
        if not checks or any(
            len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            or not isinstance(item[1], bool)
            for item in checks
        ):
            raise ValueError("prerequisite receipt requires named boolean checks")
        if len(checks) != len({name for name, _ in checks}):
            raise ValueError("prerequisite check names must be unique")
        _validate_sha256(self.evidence_hash, "prerequisite evidence hash")
        object.__setattr__(self, "checks", checks)

    @property
    def state(self) -> str:
        return "qualified" if all(result for _, result in self.checks) else "buildable"

    @property
    def content_hash(self) -> str:
        return canonical_hash(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "prerequisite_id": self.prerequisite_id,
            "checks": [list(item) for item in self.checks],
            "evidence_hash": self.evidence_hash,
            "state": self.state,
        }


@dataclass(frozen=True)
class EvidenceReceipt:
    experiment_id: str
    manifest_hash: str
    state: str
    action: str
    authority_ceiling: str
    raw_artifact_hash: str
    deterministic_test_receipt: DeterministicTestReceipt
    hard_failure_count: int
    comparison: PairedComparison
    prerequisite_receipts: tuple[PrerequisiteReceipt, ...]
    component_hashes: tuple[tuple[str, str], ...]
    issued_at: str
    valid_until: str
    invalidation_rules: tuple[str, ...]

    @property
    def deterministic_tests_passed(self) -> bool:
        return self.deterministic_test_receipt.passed

    @property
    def prerequisite_ids(self) -> tuple[str, ...]:
        return tuple(item.prerequisite_id for item in self.prerequisite_receipts)

    def _payload_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "manifest_hash": self.manifest_hash,
            "state": self.state,
            "action": self.action,
            "authority_ceiling": self.authority_ceiling,
            "raw_artifact_hash": self.raw_artifact_hash,
            "deterministic_test_receipt": self.deterministic_test_receipt.to_dict(),
            "deterministic_tests_passed": self.deterministic_tests_passed,
            "hard_failure_count": self.hard_failure_count,
            "comparison": self.comparison.to_dict(),
            "prerequisite_receipts": [
                item.to_dict() for item in self.prerequisite_receipts
            ],
            "prerequisite_ids": list(self.prerequisite_ids),
            "component_hashes": [list(item) for item in self.component_hashes],
            "issued_at": self.issued_at,
            "valid_until": self.valid_until,
            "invalidation_rules": list(self.invalidation_rules),
        }

    @property
    def content_hash(self) -> str:
        return canonical_hash(self._payload_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload_dict(), "receipt_hash": self.content_hash}


def build_evidence_receipt(
    *,
    experiment: PairedExperiment,
    deterministic_test_receipt: DeterministicTestReceipt,
    prerequisite_receipts: tuple[PrerequisiteReceipt, ...],
    issued_at: str,
) -> EvidenceReceipt:
    """Recompute every decision-bearing value from pinned experiment artifacts."""

    manifest = experiment.manifest
    issued = _parse_timestamp(issued_at, "issued_at")
    created = _parse_timestamp(manifest.created_at, "created_at")
    expires = _parse_timestamp(manifest.valid_until, "valid_until")
    if issued < created:
        raise ValueError("issued_at cannot be earlier than created_at")
    if issued > expires:
        raise ValueError("issued_at cannot be later than valid_until")
    if deterministic_test_receipt.code_revision != manifest.code_revision:
        raise ValueError("test receipt code revision does not match manifest")
    if not prerequisite_receipts:
        raise ValueError("at least one prerequisite receipt is required")
    if len({item.prerequisite_id for item in prerequisite_receipts}) != len(
        prerequisite_receipts
    ):
        raise ValueError("prerequisite receipt identifiers must be unique")
    if not experiment.all_trials:
        raise ValueError("an evidence receipt requires raw paired trials")
    if any(trial.manifest_hash != manifest.content_hash for trial in experiment.all_trials):
        raise ValueError("trial manifest hash does not match the experiment manifest")

    comparison = paired_non_inferiority(
        experiment.baseline_trials,
        experiment.candidate_trials,
        margin=manifest.non_inferiority_margin,
        confidence_level=manifest.confidence_level,
        minimum_independent_clusters=manifest.minimum_independent_clusters,
    )
    if comparison.method != manifest.statistical_method:
        raise ValueError("statistical implementation does not match the registered method")
    hard_failure_count = sum(
        bool(trial.failed_checks) for trial in experiment.candidate_trials
    )
    prerequisite_ids = {item.prerequisite_id for item in prerequisite_receipts}
    prerequisites_qualified = _REQUIRED_PREREQUISITES.issubset(
        prerequisite_ids
    ) and all(
        item.state == "qualified"
        for item in prerequisite_receipts
        if item.prerequisite_id in _REQUIRED_PREREQUISITES
    )
    authority = _METHOD_AUTHORITY_CEILINGS[manifest.statistical_method]

    if not prerequisites_qualified:
        state, action, authority = "locked", "block", "none"
    elif not deterministic_test_receipt.passed:
        state, action, authority = "buildable", "block", "none"
    elif hard_failure_count or comparison.status == "fail":
        state, action, authority = "evidence_ready", "block", "none"
    elif comparison.status == "inconclusive":
        state, action, authority = "evidence_ready", "hold", "none"
    else:
        # No method currently registered by this lab may grant deployment authority.
        state, action = "evidence_ready", "lab_pass"

    component_hashes = tuple(
        sorted(
            (
                *manifest.input_hashes,
                ("manifest", manifest.content_hash),
                ("population", manifest.population_hash),
                ("test_receipt", deterministic_test_receipt.receipt_hash),
                *(
                    (f"prerequisite:{item.prerequisite_id}", item.content_hash)
                    for item in prerequisite_receipts
                ),
            )
        )
    )
    return EvidenceReceipt(
        experiment_id=manifest.experiment_id,
        manifest_hash=manifest.content_hash,
        state=state,
        action=action,
        authority_ceiling=authority,
        raw_artifact_hash=canonical_hash(experiment.to_dict()),
        deterministic_test_receipt=deterministic_test_receipt,
        hard_failure_count=hard_failure_count,
        comparison=comparison,
        prerequisite_receipts=tuple(prerequisite_receipts),
        component_hashes=component_hashes,
        issued_at=issued_at,
        valid_until=manifest.valid_until,
        invalidation_rules=manifest.invalidation_rules,
    )


def resolve_evidence_authority(
    receipt: EvidenceReceipt,
    *,
    current_component_hashes: tuple[tuple[str, str], ...],
    as_of: str,
) -> EvidenceReceipt:
    """Resolve expiry against time and exact current component identities."""

    observed_at = _parse_timestamp(as_of, "as_of")
    issued_at = _parse_timestamp(receipt.issued_at, "issued_at")
    valid_until = _parse_timestamp(receipt.valid_until, "valid_until")
    normalized_hashes = tuple(sorted(tuple(item) for item in current_component_hashes))
    if observed_at < issued_at:
        return replace(receipt, state="locked", action="block", authority_ceiling="none")
    expired = observed_at > valid_until or normalized_hashes != receipt.component_hashes
    if not expired:
        return receipt
    return replace(receipt, state="expired", action="block", authority_ceiling="none")


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be a sha256: digest")


def _parse_timestamp(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed
