"""Regression tests for the primer's evidence-authority claims."""

from __future__ import annotations

import unittest
from pathlib import Path

from cx_eval_lab.agents import ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.gate import (
    GatePolicy,
    apply_release_gate,
    assess_non_inferiority,
)
from cx_eval_lab.runner import evaluate_agent


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPOSITORY_ROOT / "evals/cx-support/datasets/regression/refund_v1.json"


class TrustRepairTests(unittest.TestCase):
    def test_registered_interval_supports_non_inferiority_not_superiority(self) -> None:
        decision = assess_non_inferiority(
            lower_bound=-0.02,
            upper_bound=0.10,
            margin=0.03,
        )

        self.assertTrue(decision.non_inferior)
        self.assertFalse(decision.superior)

    def test_interval_below_margin_does_not_support_non_inferiority(self) -> None:
        decision = assess_non_inferiority(
            lower_bound=-0.031,
            upper_bound=0.10,
            margin=0.03,
        )

        self.assertFalse(decision.non_inferior)

    def test_exact_margin_boundary_is_registered_as_non_inferior(self) -> None:
        decision = assess_non_inferiority(
            lower_bound=-0.03,
            upper_bound=0.04,
            margin=0.03,
        )

        self.assertTrue(decision.non_inferior)

    def test_scalar_demo_gate_uses_lab_authority_and_honest_rule_name(self) -> None:
        report = evaluate_agent(
            ReferenceSupportAgent(),
            load_refund_cases(DATASET_PATH),
        )

        decision = apply_release_gate(
            report,
            GatePolicy.for_initial_refund_slice(),
            baseline_task_success=0.80,
        )

        self.assertEqual("lab_pass", decision.action)
        self.assertEqual("lab_only", decision.authority_ceiling)
        rule_names = {rule.name for rule in decision.rules}
        self.assertIn("illustrative_point_floor:task_success", rule_names)
        self.assertFalse(any(name.startswith("non_inferiority:") for name in rule_names))

    def test_metrics_chapter_states_the_correct_numerical_conclusion(self) -> None:
        chapter = (REPOSITORY_ROOT / "docs/metrics.md").read_text(encoding="utf-8")

        self.assertIn("−2 points is above the registered −3-point margin", chapter)
        self.assertIn("non-inferiority is established", chapter)
        self.assertIn("superiority is not established", chapter)

    def test_sample_report_labels_synthetic_evidence_and_authority_ceiling(self) -> None:
        chapter = (REPOSITORY_ROOT / "docs/build-the-system.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Evidence kind: **synthetic deterministic lab**", chapter)
        self.assertIn("Authority ceiling: **lab pass only**", chapter)
        self.assertIn("cannot establish canary eligibility", chapter)


if __name__ == "__main__":
    unittest.main()
