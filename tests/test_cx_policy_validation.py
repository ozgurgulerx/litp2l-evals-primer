"""Boundary tests for release-policy and dataset configuration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cx_eval_lab.gate import GatePolicy, apply_release_gate, load_gate_policy
from cx_eval_lab.models import MeasurementProfile, RefundCase
from cx_eval_lab.runner import evaluate_agent
from cx_eval_lab.agents import ReferenceSupportAgent


class PolicyValidationTests(unittest.TestCase):
    def test_gate_rejects_an_invalid_baseline_instead_of_weakening_the_bar(
        self,
    ) -> None:
        case = RefundCase(
            case_id="validation-001",
            customer_id="customer-001",
            order_id="order-001",
            utterance="Refund this.",
            amount_cents=100,
            eligible=True,
            approval_threshold_cents=10_000,
            expected_outcome="refunded",
            slices=("language:en",),
        )
        report = evaluate_agent(ReferenceSupportAgent(), (case,))

        with self.assertRaisesRegex(ValueError, "baseline_task_success"):
            apply_release_gate(report, GatePolicy.for_initial_refund_slice(), -1.0)

    def test_gate_rejects_out_of_range_policy_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "illustrative_point_floor_margin"):
            GatePolicy(
                policy_version="invalid-policy",
                illustrative_point_floor_margin=1.5,
                minimum_task_success_gain=None,
                slice_floors=(("language:tr", 0.8),),
                max_p95_latency_ms=3_000,
                max_cost_per_success_usd=0.80,
            )

    def test_hard_invariants_cannot_be_given_a_nonzero_error_budget(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "hard-invariant limits must equal zero"
        ):
            GatePolicy(
                policy_version="invalid-hard-invariant",
                illustrative_point_floor_margin=0.01,
                minimum_task_success_gain=None,
                slice_floors=(("language:tr", 0.8),),
                max_p95_latency_ms=3_000,
                max_cost_per_success_usd=0.80,
                max_unauthorized_action_count=1,
            )

    def test_measurement_profile_rejects_negative_or_nonfinite_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "latency_ms"):
            MeasurementProfile(latency_ms=-1, cost_usd_per_case=0.10)
        with self.assertRaisesRegex(ValueError, "cost_usd_per_case"):
            MeasurementProfile(latency_ms=10, cost_usd_per_case=float("nan"))

    def test_policy_loader_rejects_a_string_slice_floor(self) -> None:
        invalid_policy = {
            "policy_version": "invalid-policy",
            "illustrative_point_floor_margin": 0.01,
            "minimum_task_success_gain": None,
            "slice_floors": {"language:tr": "not-a-number"},
            "max_p95_latency_ms": 3_000,
            "max_cost_per_success_usd": 0.80,
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            policy_path = Path(temporary_directory) / "policy.json"
            policy_path.write_text(json.dumps(invalid_policy), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "slice floor"):
                load_gate_policy(policy_path)

    def test_dataset_case_rejects_string_booleans_and_string_slices(self) -> None:
        common = {
            "case_id": "validation-002",
            "customer_id": "customer-002",
            "order_id": "order-002",
            "utterance": "Refund this.",
            "amount_cents": 100,
            "approval_threshold_cents": 10_000,
            "expected_outcome": "refunded",
        }

        with self.assertRaisesRegex(ValueError, "eligible"):
            RefundCase(**common, eligible="false", slices=("language:en",))
        with self.assertRaisesRegex(ValueError, "slices"):
            RefundCase(**common, eligible=False, slices="language:en")


if __name__ == "__main__":
    unittest.main()
