"""Paired statistical decisions for binary evaluation outcomes."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from statistics import NormalDist
from typing import Any


@dataclass(frozen=True)
class PairedTrial:
    """One arm of a registered case/trial pair."""

    case_id: str
    trial_index: int
    cluster_id: str
    arm: str
    passed: bool
    latency_ms: int = 0
    cost_usd: float | None = None
    manifest_hash: str = ""
    failed_checks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.arm not in {"baseline", "candidate"}:
            raise ValueError("arm must be baseline or candidate")
        if not self.case_id or not self.cluster_id:
            raise ValueError("case_id and cluster_id are required")
        if not isinstance(self.trial_index, int) or self.trial_index < 0:
            raise ValueError("trial_index must be a non-negative integer")
        object.__setattr__(self, "failed_checks", tuple(self.failed_checks))

    @property
    def pair_key(self) -> tuple[str, int]:
        return self.case_id, self.trial_index

    @property
    def trial_id(self) -> str:
        return f"{self.arm}:{self.case_id}:{self.trial_index:04d}"

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "failed_checks": list(self.failed_checks)}


@dataclass(frozen=True)
class PairedComparison:
    """Cluster-aware normal interval over paired binary differences."""

    method: str
    confidence_level: float
    margin: float
    pair_count: int
    independent_cluster_count: int
    minimum_independent_clusters: int
    baseline_rate: float
    candidate_rate: float
    point_difference: float
    lower_bound: float | None
    upper_bound: float | None
    non_inferior: bool
    superior: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def paired_non_inferiority(
    baseline_trials: tuple[PairedTrial, ...],
    candidate_trials: tuple[PairedTrial, ...],
    *,
    margin: float,
    confidence_level: float = 0.95,
    minimum_independent_clusters: int = 30,
) -> PairedComparison:
    """Compare paired outcomes while treating customer/session clusters as units.

    This teaching implementation uses a normal interval over cluster-level mean
    paired differences. Production work should pre-register a method appropriate
    to its sample, estimand, rarity, and stopping rule.
    """

    _validate_configuration(margin, confidence_level, minimum_independent_clusters)
    baseline = _index_trials(baseline_trials, "baseline")
    candidate = _index_trials(candidate_trials, "candidate")
    if baseline.keys() != candidate.keys():
        raise ValueError("baseline and candidate paired trial keys must match exactly")
    if not baseline:
        raise ValueError("at least one paired trial is required")

    pair_differences: list[float] = []
    cluster_differences: dict[str, tuple[float, ...]] = {}
    for key in sorted(baseline):
        baseline_trial = baseline[key]
        candidate_trial = candidate[key]
        if baseline_trial.cluster_id != candidate_trial.cluster_id:
            raise ValueError(f"cluster mismatch for paired trial key {key}")
        difference = float(candidate_trial.passed) - float(baseline_trial.passed)
        pair_differences.append(difference)
        cluster_id = baseline_trial.cluster_id
        cluster_differences = {
            **cluster_differences,
            cluster_id: (*cluster_differences.get(cluster_id, ()), difference),
        }

    cluster_means = tuple(
        sum(values) / len(values) for values in cluster_differences.values()
    )
    point_difference = sum(cluster_means) / len(cluster_means)
    baseline_rate = sum(float(item.passed) for item in baseline.values()) / len(baseline)
    candidate_rate = sum(float(item.passed) for item in candidate.values()) / len(candidate)
    cluster_count = len(cluster_means)

    if cluster_count < minimum_independent_clusters:
        return PairedComparison(
            method="clustered_normal_interval",
            confidence_level=confidence_level,
            margin=margin,
            pair_count=len(pair_differences),
            independent_cluster_count=cluster_count,
            minimum_independent_clusters=minimum_independent_clusters,
            baseline_rate=baseline_rate,
            candidate_rate=candidate_rate,
            point_difference=point_difference,
            lower_bound=None,
            upper_bound=None,
            non_inferior=False,
            superior=False,
            status="inconclusive",
        )

    standard_error = _standard_error(cluster_means)
    critical_value = NormalDist().inv_cdf(0.5 + confidence_level / 2)
    lower_bound = point_difference - critical_value * standard_error
    upper_bound = point_difference + critical_value * standard_error
    non_inferior = lower_bound >= -margin
    return PairedComparison(
        method="clustered_normal_interval",
        confidence_level=confidence_level,
        margin=margin,
        pair_count=len(pair_differences),
        independent_cluster_count=cluster_count,
        minimum_independent_clusters=minimum_independent_clusters,
        baseline_rate=baseline_rate,
        candidate_rate=candidate_rate,
        point_difference=point_difference,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        non_inferior=non_inferior,
        superior=lower_bound > 0,
        status="pass" if non_inferior else "fail",
    )


def _index_trials(
    trials: tuple[PairedTrial, ...],
    expected_arm: str,
) -> dict[tuple[str, int], PairedTrial]:
    indexed: dict[tuple[str, int], PairedTrial] = {}
    for trial in trials:
        if trial.arm != expected_arm:
            raise ValueError(f"expected {expected_arm} trial, received {trial.arm}")
        if trial.pair_key in indexed:
            raise ValueError(f"duplicate paired trial key: {trial.pair_key}")
        indexed = {**indexed, trial.pair_key: trial}
    return indexed


def _standard_error(values: tuple[float, ...]) -> float:
    if len(values) == 1:
        return 0.0
    mean = sum(values) / len(values)
    sample_variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(sample_variance / len(values))


def _validate_configuration(
    margin: float,
    confidence_level: float,
    minimum_independent_clusters: int,
) -> None:
    if (
        not isinstance(margin, (int, float))
        or isinstance(margin, bool)
        or not math.isfinite(margin)
        or not 0 <= margin <= 1
    ):
        raise ValueError("margin must be a finite number in [0, 1]")
    if (
        not isinstance(confidence_level, (int, float))
        or isinstance(confidence_level, bool)
        or not 0 < confidence_level < 1
    ):
        raise ValueError("confidence_level must be between 0 and 1")
    if (
        not isinstance(minimum_independent_clusters, int)
        or isinstance(minimum_independent_clusters, bool)
        or minimum_independent_clusters < 1
    ):
        raise ValueError("minimum_independent_clusters must be positive")
