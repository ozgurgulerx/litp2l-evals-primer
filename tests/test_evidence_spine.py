"""Evidence-manifest, repeated-trial, and statistical gate contracts."""

from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.evidence import (
    DeterministicTestReceipt,
    ExperimentManifest,
    PairedExperiment,
    PrerequisiteReceipt,
    build_evidence_receipt,
)
from cx_eval_lab.models import MeasurementProfile
from cx_eval_lab.runner import run_paired_experiment
from cx_eval_lab.statistics import PairedTrial, paired_non_inferiority


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPOSITORY_ROOT / "evals/cx-support/datasets/regression/refund_v0.json"


def make_manifest(measurement_kind: str = "synthetic") -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id="cx-reference-v1",
        created_at="2026-09-06T12:00:00Z",
        valid_until="2026-10-06T12:00:00Z",
        code_revision="8a18e2f",
        model_id="deterministic-reference-v1",
        prompt_version="refund-system-v1",
        tool_version="typed-refund-tools-v1",
        dataset_version="refund-v0",
        evaluator_version="refund-evaluators-v1",
        policy_version="refund-gate-v0",
        environment_version="python-3.12",
        population_hash="sha256:" + "a" * 64,
        repetitions=2,
        measurement_kind=measurement_kind,
        estimand="candidate_minus_baseline_verified_success",
        statistical_method="clustered_normal_interval",
        non_inferiority_margin=0.03,
        confidence_level=0.95,
        minimum_independent_clusters=30,
        sequential_policy="fixed_sample_no_interim_looks",
        input_hashes=(
            ("dataset", "sha256:" + "b" * 64),
            ("policy", "sha256:" + "c" * 64),
        ),
        invalidation_rules=(
            "model_or_prompt_change",
            "tool_or_evaluator_change",
            "dataset_or_policy_change",
        ),
    )


def paired_trials(
    count: int,
    candidate_failures: set[int] | None = None,
    manifest_hash: str = "",
):
    failures = candidate_failures or set()
    baseline = tuple(
        PairedTrial(
            case_id=f"case-{index:03d}",
            trial_index=0,
            cluster_id=f"customer-{index:03d}",
            arm="baseline",
            passed=True,
            manifest_hash=manifest_hash,
        )
        for index in range(count)
    )
    candidate = tuple(
        PairedTrial(
            case_id=f"case-{index:03d}",
            trial_index=0,
            cluster_id=f"customer-{index:03d}",
            arm="candidate",
            passed=index not in failures,
            manifest_hash=manifest_hash,
        )
        for index in range(count)
    )
    return baseline, candidate


def make_receipt(
    measurement_kind: str = "synthetic",
    *,
    hard_failure: bool = False,
):
    current_manifest = make_manifest(measurement_kind)
    baseline, candidate = paired_trials(30, manifest_hash=current_manifest.content_hash)
    if hard_failure:
        candidate = (
            replace(candidate[0], failed_checks=("hard_invariant",)),
            *candidate[1:],
        )
    return build_evidence_receipt(
        experiment=PairedExperiment(current_manifest, baseline, candidate),
        deterministic_test_receipt=DeterministicTestReceipt(
            suite_id="unit-integration-e2e",
            code_revision=current_manifest.code_revision,
            checks=(("suite_passed", True),),
            artifact_hash="sha256:" + "d" * 64,
        ),
        prerequisite_receipts=(
            PrerequisiteReceipt(
                "typed_tool_boundary",
                (("contract_verified", True),),
                "sha256:" + "e" * 64,
            ),
            PrerequisiteReceipt(
                "semantic_state_grading",
                (("contract_verified", True),),
                "sha256:" + "f" * 64,
            ),
        ),
        issued_at="2026-09-06T13:00:00Z",
    )


class EvidenceManifestTests(unittest.TestCase):
    def test_manifest_hash_is_stable_and_changes_with_a_relevant_version(self) -> None:
        original = make_manifest()
        identical = make_manifest()
        changed = ExperimentManifest(
            **{
                **original.to_dict(),
                "prompt_version": "refund-system-v2",
                "input_hashes": original.input_hashes,
                "invalidation_rules": original.invalidation_rules,
            }
        )

        self.assertEqual(original.content_hash, identical.content_hash)
        self.assertNotEqual(original.content_hash, changed.content_hash)

    def test_repeated_runner_emits_exact_paired_trial_keys(self) -> None:
        manifest = make_manifest()
        cases = load_refund_cases(DATASET_PATH)
        profile = MeasurementProfile(latency_ms=10, cost_usd_per_case=0.01)

        experiment = run_paired_experiment(
            baseline_agent=ReferenceSupportAgent(name="baseline"),
            candidate_agent=ReferenceSupportAgent(name="candidate"),
            cases=cases,
            manifest=manifest,
            baseline_measurement_profile=profile,
            candidate_measurement_profile=profile,
        )

        expected_count = len(cases) * manifest.repetitions
        self.assertEqual(expected_count, len(experiment.baseline_trials))
        self.assertEqual(expected_count, len(experiment.candidate_trials))
        self.assertEqual(
            {trial.pair_key for trial in experiment.baseline_trials},
            {trial.pair_key for trial in experiment.candidate_trials},
        )
        self.assertTrue(all(trial.manifest_hash == manifest.content_hash for trial in experiment.all_trials))
        self.assertEqual(expected_count * 2, experiment.recomputed_trial_count)


class StatisticalEvidenceTests(unittest.TestCase):
    def test_paired_non_inferiority_uses_lower_confidence_bound(self) -> None:
        baseline, candidate = paired_trials(40)

        result = paired_non_inferiority(
            baseline,
            candidate,
            margin=0.03,
            confidence_level=0.95,
            minimum_independent_clusters=30,
        )

        self.assertEqual("pass", result.status)
        self.assertEqual(0.0, result.point_difference)
        self.assertEqual(0.0, result.lower_bound)
        self.assertTrue(result.non_inferior)
        self.assertFalse(result.superior)

    def test_insufficient_independent_clusters_is_inconclusive(self) -> None:
        baseline, candidate = paired_trials(12)

        result = paired_non_inferiority(
            baseline,
            candidate,
            margin=0.03,
            minimum_independent_clusters=30,
        )

        self.assertEqual("inconclusive", result.status)
        self.assertIsNone(result.lower_bound)
        self.assertFalse(result.non_inferior)

    def test_missing_candidate_pair_fails_closed(self) -> None:
        baseline, candidate = paired_trials(30)

        with self.assertRaisesRegex(ValueError, "paired trial keys"):
            paired_non_inferiority(
                baseline,
                candidate[:-1],
                margin=0.03,
                minimum_independent_clusters=30,
            )

    def test_synthetic_evidence_cannot_become_canary_eligible(self) -> None:
        receipt = make_receipt("synthetic")

        self.assertEqual("evidence_ready", receipt.state)
        self.assertEqual("lab_pass", receipt.action)
        self.assertEqual("lab_only", receipt.authority_ceiling)

    def test_teaching_method_never_earns_bounded_canary_authority(self) -> None:
        receipt = make_receipt("measured")

        self.assertEqual("evidence_ready", receipt.state)
        self.assertEqual("lab_pass", receipt.action)
        self.assertEqual("lab_only", receipt.authority_ceiling)

    def test_hard_failure_blocks_even_when_statistical_rule_passes(self) -> None:
        receipt = make_receipt("measured", hard_failure=True)

        self.assertEqual("block", receipt.action)
        self.assertEqual("none", receipt.authority_ceiling)


if __name__ == "__main__":
    unittest.main()
