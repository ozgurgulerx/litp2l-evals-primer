"""Adversarial tests for evidence-authority forgery and expiry."""

from __future__ import annotations

import unittest

from cx_eval_lab.evidence import (
    DeterministicTestReceipt,
    ExperimentManifest,
    PairedExperiment,
    PrerequisiteReceipt,
    build_evidence_receipt,
    resolve_evidence_authority,
)
from cx_eval_lab.statistics import PairedTrial


def manifest() -> ExperimentManifest:
    return ExperimentManifest(
        experiment_id="authority-adversarial-v1",
        created_at="2026-09-06T12:00:00Z",
        valid_until="2026-10-06T12:00:00Z",
        code_revision="abc1234",
        model_id="model-pinned-v1",
        prompt_version="prompt-v1",
        tool_version="tools-v1",
        dataset_version="refund-v1",
        evaluator_version="evaluator-v1",
        policy_version="policy-v1",
        environment_version="environment-v1",
        population_hash="sha256:" + "b" * 64,
        repetitions=1,
        measurement_kind="measured",
        estimand="candidate_minus_baseline_verified_success",
        statistical_method="clustered_normal_interval",
        non_inferiority_margin=0.03,
        confidence_level=0.95,
        minimum_independent_clusters=30,
        sequential_policy="fixed_sample_no_interim_looks",
        input_hashes=(("dataset", "sha256:" + "c" * 64),),
        invalidation_rules=("model_or_prompt_change", "population_or_data_change"),
    )


def experiment(*, corrupt_manifest_hash: bool = False) -> PairedExperiment:
    current = manifest()
    observed_hash = "sha256:" + "0" * 64 if corrupt_manifest_hash else current.content_hash
    baseline = tuple(
        PairedTrial(
            case_id=f"case-{index:03d}",
            trial_index=0,
            cluster_id=f"customer-{index:03d}",
            arm="baseline",
            passed=True,
            manifest_hash=observed_hash,
        )
        for index in range(30)
    )
    candidate = tuple(
        PairedTrial(
            case_id=f"case-{index:03d}",
            trial_index=0,
            cluster_id=f"customer-{index:03d}",
            arm="candidate",
            passed=True,
            manifest_hash=observed_hash,
        )
        for index in range(30)
    )
    return PairedExperiment(current, baseline, candidate)


def test_receipt() -> DeterministicTestReceipt:
    return DeterministicTestReceipt(
        suite_id="unit-integration-e2e",
        code_revision="abc1234",
        checks=(("suite_passed", True),),
        artifact_hash="sha256:" + "d" * 64,
    )


def prerequisites(state: str = "qualified") -> tuple[PrerequisiteReceipt, ...]:
    passed = state == "qualified"
    return (
        PrerequisiteReceipt(
            "typed_tool_boundary", (("contract_verified", passed),), "sha256:" + "e" * 64
        ),
        PrerequisiteReceipt(
            "semantic_state_grading", (("contract_verified", passed),), "sha256:" + "f" * 64
        ),
    )


class AuthorityIntegrityTests(unittest.TestCase):
    def test_teaching_method_cannot_grant_canary_even_when_measured_and_passing(self) -> None:
        receipt = build_evidence_receipt(
            experiment=experiment(),
            deterministic_test_receipt=test_receipt(),
            prerequisite_receipts=prerequisites(),
            issued_at="2026-09-06T13:00:00Z",
        )

        self.assertEqual("evidence_ready", receipt.state)
        self.assertEqual("lab_pass", receipt.action)
        self.assertEqual("lab_only", receipt.authority_ceiling)
        self.assertEqual("clustered_normal_interval", receipt.comparison.method)
        self.assertEqual(30, receipt.comparison.pair_count)
        self.assertTrue(receipt.raw_artifact_hash.startswith("sha256:"))

    def test_trial_with_wrong_manifest_hash_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "trial manifest hash"):
            build_evidence_receipt(
                experiment=experiment(corrupt_manifest_hash=True),
                deterministic_test_receipt=test_receipt(),
                prerequisite_receipts=prerequisites(),
                issued_at="2026-09-06T13:00:00Z",
            )

    def test_unqualified_prerequisite_locks_the_receipt(self) -> None:
        receipt = build_evidence_receipt(
            experiment=experiment(),
            deterministic_test_receipt=test_receipt(),
            prerequisite_receipts=prerequisites("buildable"),
            issued_at="2026-09-06T13:00:00Z",
        )

        self.assertEqual("locked", receipt.state)
        self.assertEqual("block", receipt.action)

    def test_unrelated_prerequisite_cannot_substitute_for_required_receipts(self) -> None:
        receipt = build_evidence_receipt(
            experiment=experiment(),
            deterministic_test_receipt=test_receipt(),
            prerequisite_receipts=(
                PrerequisiteReceipt(
                    "unrelated_check",
                    (("passed", True),),
                    "sha256:" + "8" * 64,
                ),
            ),
            issued_at="2026-09-06T13:00:00Z",
        )

        self.assertEqual("locked", receipt.state)
        self.assertEqual("none", receipt.authority_ceiling)

    def test_receipt_expires_on_time_or_component_drift(self) -> None:
        receipt = build_evidence_receipt(
            experiment=experiment(),
            deterministic_test_receipt=test_receipt(),
            prerequisite_receipts=prerequisites(),
            issued_at="2026-09-06T13:00:00Z",
        )
        current_hashes = receipt.component_hashes

        valid = resolve_evidence_authority(
            receipt,
            current_component_hashes=current_hashes,
            as_of="2026-09-07T00:00:00Z",
        )
        time_expired = resolve_evidence_authority(
            receipt,
            current_component_hashes=current_hashes,
            as_of="2026-11-01T00:00:00Z",
        )
        changed = resolve_evidence_authority(
            receipt,
            current_component_hashes=(("dataset", "sha256:" + "9" * 64),),
            as_of="2026-09-07T00:00:00Z",
        )

        self.assertEqual("evidence_ready", valid.state)
        self.assertEqual("expired", time_expired.state)
        self.assertEqual("expired", changed.state)
        self.assertEqual("block", changed.action)

    def test_unpinned_revision_cannot_describe_measured_evidence(self) -> None:
        values = manifest().to_dict()
        values["code_revision"] = "working-tree-unpinned"

        with self.assertRaisesRegex(ValueError, "pinned code revision"):
            ExperimentManifest(**values)


if __name__ == "__main__":
    unittest.main()
