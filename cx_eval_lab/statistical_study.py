"""Exact enumeration of a narrow known-population statistical experiment.

The baseline always passes. Each independent customer has one Bernoulli loss
for the candidate. This is a special paired problem reducible to one binomial
proportion, NOT a general interval for arbitrary paired or clustered outcomes.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache

from cx_eval_lab.statistics import PairedTrial, paired_non_inferiority


def _probability(value, name):
    if (not isinstance(value, (int, float)) or isinstance(value, bool)
            or not math.isfinite(value) or not 0 <= value <= 1):
        raise ValueError(f"{name} must be a finite probability")


def _counts(k, n):
    if (type(n) is not int or not 1 <= n <= 500 or type(k) is not int
            or not 0 <= k <= n):
        raise ValueError("integer counts require 0 <= k <= n and 1 <= n <= 500")


def _mass(k, n, p):
    return math.comb(n, k) * p ** k * (1 - p) ** (n - k)


def _upper_loss_limit(k, n, tail):
    if k == n:
        return 1.0
    low, high = 0.0, 1.0
    for _ in range(60):
        middle = (low + high) / 2
        cdf = math.fsum(_mass(j, n, middle) for j in range(k + 1))
        if cdf > tail:
            low = middle
        else:
            high = middle
    return (low + high) / 2


@lru_cache(maxsize=2048)
def exact_loss_interval(k: int, n: int, confidence: float = 0.95):
    """Equal-tailed Clopper–Pearson bounds by numerical binomial inversion.

Limited to 500 independent Bernoulli observations for this teaching study.
The interval covers the observed-label probability, not unobserved truth when
labels are biased. 'Exact' refers to the binomial model, not float arithmetic.
"""
    _counts(k, n)
    _probability(confidence, "confidence")
    if confidence in (0, 1):
        raise ValueError("confidence must be strictly between zero and one")
    tail = (1 - confidence) / 2
    lower = 0.0 if k == 0 else 1 - _upper_loss_limit(n - k, n, tail)
    return lower, _upper_loss_limit(k, n, tail)


def _paired_losses(k, n):
    baseline = tuple(PairedTrial(str(i), 0, str(i), "baseline", True) for i in range(n))
    candidate = tuple(PairedTrial(str(i), 0, str(i), "candidate", i >= k) for i in range(n))
    return baseline, candidate


def _decisions(k, n, margin, confidence):
    normal = paired_non_inferiority(*_paired_losses(k, n), margin=margin,
                                   confidence_level=confidence)
    loss_lower, loss_upper = exact_loss_interval(k, n, confidence)
    return {
        "clustered_normal_interval": {
            "lower": normal.lower_bound, "upper": normal.upper_bound,
            "promote": normal.non_inferior,
        },
        "exact_binomial_special_case": {
            "lower": -loss_upper, "upper": -loss_lower,
            "promote": -loss_upper >= -margin,
        },
    }


def sparse_population_study(*, n=30, loss_probability=0.04,
                            hidden_loss_probability=0.0, margin=0.03,
                            confidence=0.95):
    """Enumerate every possible observed loss count and its probability.

With probability `hidden_loss_probability`, a true loss is mislabeled as a
success independently. There are no false loss labels. Coverage is evaluated
against TRUE performance; therefore label error can invalidate both methods.
"""
    _counts(0, n)
    for name, value in (("loss_probability", loss_probability),
                        ("hidden_loss_probability", hidden_loss_probability),
                        ("margin", margin)):
        _probability(value, name)
    observed_loss = loss_probability * (1 - hidden_loss_probability)
    truth = -loss_probability
    rows = tuple({"observed_losses": k, "probability": _mass(k, n, observed_loss),
                  "decisions": _decisions(k, n, margin, confidence)} for k in range(n + 1))
    methods = {}
    for name in rows[0]["decisions"]:
        coverage = math.fsum(row["probability"] for row in rows
                            if row["decisions"][name]["lower"] is not None
                            and row["decisions"][name]["lower"] <= truth
                            <= row["decisions"][name]["upper"])
        promotion = math.fsum(row["probability"] for row in rows
                             if row["decisions"][name]["promote"])
        no_interval = math.fsum(row["probability"] for row in rows
                               if row["decisions"][name]["lower"] is None)
        methods[name] = {
            "coverage_probability": coverage if no_interval == 0 else None,
            "promotion_probability": promotion,
            "false_promotion_probability": promotion if truth < -margin else 0.0,
            "no_interval_probability": no_interval,
        }
    return {
        "n": n, "loss_probability": loss_probability,
        "hidden_loss_probability": hidden_loss_probability,
        "true_difference": truth, "observed_difference": -observed_loss,
        "margin": margin, "confidence": confidence,
        "enumerated_probability_mass": math.fsum(row["probability"] for row in rows),
        "methods": methods, "count_outcomes": rows,
    }


def unequal_cluster_example():
    """Fifteen small winning customers and fifteen large losing customers."""
    baseline, candidate = [], []
    for customer in range(30):
        wins = customer < 15
        size = 1 if wins else 9
        for task in range(size):
            case_id = f"{customer}:{task}"
            baseline.append(PairedTrial(case_id, 0, str(customer), "baseline", not wins))
            candidate.append(PairedTrial(case_id, 0, str(customer), "candidate", wins))
    comparison = paired_non_inferiority(tuple(baseline), tuple(candidate), margin=0.03)
    return {"equal_customer_difference": comparison.point_difference,
            "pooled_task_difference": comparison.candidate_rate - comparison.baseline_rate,
            "independent_clusters": comparison.independent_cluster_count,
            "task_pairs": comparison.pair_count,
            "design": "15 customers each gain 1/1; 15 customers each lose 9/9"}


def study_report():
    return {
        "schema": "statistical-method-study-v1",
        "evidence_kind": "exact_enumeration_of_synthetic_population",
        "authority": "lab_only",
        "monte_carlo_error": "none; enumeration with floating-point arithmetic",
        "studies": [
            sparse_population_study(n=30, loss_probability=0),
            sparse_population_study(n=30, loss_probability=0.01),
            sparse_population_study(n=30, loss_probability=0.04),
            sparse_population_study(n=100, loss_probability=0.04),
            sparse_population_study(n=100, loss_probability=0.10,
                                    hidden_loss_probability=1.0),
        ],
        "unequal_clusters": unequal_cluster_example(),
    }


if __name__ == "__main__":
    print(json.dumps(study_report(), indent=2, allow_nan=False))
