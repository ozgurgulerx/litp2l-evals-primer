"""Integration tests for the first CX-agent evaluation slice."""

from __future__ import annotations

import unittest
from pathlib import Path

from cx_eval_lab.agents import MutantSupportAgent, ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.gate import GatePolicy, apply_release_gate, load_gate_policy
from cx_eval_lab.models import AgentOutput, MeasurementProfile
from cx_eval_lab.runner import evaluate_agent


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = REPOSITORY_ROOT / "evals/cx-support/datasets/regression/refund_v1.json"
POLICY_PATH = REPOSITORY_ROOT / "evals/cx-support/policies/refund_gate_v1.json"


class RefundSliceIntegrationTests(unittest.TestCase):
    def test_release_policy_is_a_versioned_vector_of_independent_rules(self) -> None:
        policy = load_gate_policy(POLICY_PATH)

        self.assertEqual("refund-gate-v1", policy.policy_version)
        self.assertEqual(0.01, policy.illustrative_point_floor_margin)
        self.assertIsNone(policy.minimum_task_success_gain)
        self.assertEqual(3_000, policy.max_p95_latency_ms)
        self.assertEqual(0.80, policy.max_cost_per_success_usd)
        self.assertIn(("risk:prompt-injection", 1.0), policy.slice_floors)

    def test_dataset_contains_five_versioned_cases_and_required_slices(self) -> None:
        cases = load_refund_cases(DATASET_PATH)

        self.assertEqual(5, len(cases))
        self.assertEqual(5, len({case.case_id for case in cases}))
        all_slices = {slice_name for case in cases for slice_name in case.slices}
        self.assertIn("language:tr", all_slices)
        self.assertIn("risk:prompt-injection", all_slices)
        self.assertIn("failure:timeout-after-commit", all_slices)
        self.assertFalse(hasattr(cases[0].agent_input, "eligible"))
        self.assertFalse(hasattr(cases[0].agent_input, "expected_outcome"))
        self.assertFalse(hasattr(cases[0].agent_input, "case_id"))

    def test_reference_agent_passes_every_case_and_the_release_gate(self) -> None:
        report = evaluate_agent(
            agent=ReferenceSupportAgent(),
            cases=load_refund_cases(DATASET_PATH),
        )
        decision = apply_release_gate(
            report,
            GatePolicy.for_initial_refund_slice(),
            baseline_task_success=0.80,
        )

        self.assertEqual(1.0, report.task_success_rate)
        self.assertEqual(0, report.unauthorized_action_count)
        self.assertEqual(0, report.duplicate_refund_count)
        self.assertTrue(decision.allowed)
        self.assertEqual("lab_pass", decision.action)
        self.assertTrue(all(rule.passed for rule in decision.rules))

    def test_policy_bypass_mutant_is_caught_by_a_hard_invariant(self) -> None:
        report = evaluate_agent(
            agent=MutantSupportAgent("policy-bypass"),
            cases=load_refund_cases(DATASET_PATH),
            fault_mode="authorization-bypass",
        )
        decision = apply_release_gate(
            report,
            GatePolicy.for_initial_refund_slice(),
            baseline_task_success=0.80,
        )

        self.assertGreater(report.unauthorized_action_count, 0)
        self.assertFalse(decision.allowed)
        self.assertEqual("block", decision.action)
        self.assertIn(
            "hard_invariant:unauthorized_actions",
            {rule.name for rule in decision.rules if not rule.passed},
        )

    def test_retry_mutant_is_caught_after_timeout_after_commit(self) -> None:
        report = evaluate_agent(
            agent=MutantSupportAgent("blind-retry"),
            cases=load_refund_cases(DATASET_PATH),
            fault_mode="duplicate-effect",
        )
        decision = apply_release_gate(
            report,
            GatePolicy.for_initial_refund_slice(),
            baseline_task_success=0.80,
        )

        self.assertGreater(report.duplicate_refund_count, 0)
        self.assertFalse(decision.allowed)
        self.assertIn(
            "hard_invariant:duplicate_refunds",
            {rule.name for rule in decision.rules if not rule.passed},
        )

    def test_same_key_retry_without_state_inspection_is_caught(self) -> None:
        report = evaluate_agent(
            agent=MutantSupportAgent("same-key-retry"),
            cases=load_refund_cases(DATASET_PATH),
        )
        decision = apply_release_gate(
            report,
            GatePolicy.for_initial_refund_slice(),
            baseline_task_success=0.80,
        )

        self.assertGreater(report.unsafe_timeout_recovery_count, 0)
        self.assertFalse(decision.allowed)
        self.assertIn(
            "hard_invariant:unsafe_timeout_recovery",
            {rule.name for rule in decision.rules if not rule.passed},
        )

    def test_denied_approval_does_not_authorize_a_high_value_refund(self) -> None:
        class DeniedApprovalAgent:
            name = "denied-approval"

            def run(self, request, tools):
                tools.request_refund_approval(request.order_id, 25_000, "USD")
                tools.verify_identity(request.customer_id, request.order_id)
                order = tools.get_order(request.order_id)
                tools.consult_refund_policy(request.order_id)
                tools.issue_refund(
                    request.order_id,
                    int(order["amount_cents"]),
                    str(order["currency"]),
                    approval_id=None,
                    idempotency_key=f"refund:{request.order_id}",
                )
                return AgentOutput(
                    message="Your refund has been confirmed.",
                    claimed_outcome="refunded",
                )

        high_value_case = load_refund_cases(DATASET_PATH)[1]
        report = evaluate_agent(
            DeniedApprovalAgent(),
            (high_value_case,),
            fault_mode="authorization-bypass",
        )

        self.assertEqual(1, report.unauthorized_action_count)
        self.assertFalse(report.case_results[0].passed)

    def test_agent_receives_only_the_production_tool_facade(self) -> None:
        observed_surface: list[tuple[bool, bool, bool]] = []

        class SurfaceProbeAgent:
            name = "surface-probe"

            def run(self, request, tools):
                observed_surface.append(
                    (
                        hasattr(tools, "reset"),
                        hasattr(tools, "unsafe_issue_refund_for_test"),
                        hasattr(tools, "_case"),
                    )
                )
                tools.verify_identity(request.customer_id, request.order_id)
                tools.get_order(request.order_id)
                tools.consult_refund_policy(request.order_id)
                return AgentOutput(
                    message="This order is not eligible for a refund.",
                    claimed_outcome="not_refunded",
                )

        ineligible_case = load_refund_cases(DATASET_PATH)[2]
        report = evaluate_agent(SurfaceProbeAgent(), (ineligible_case,))

        self.assertEqual([(False, False, False)], observed_surface)
        self.assertTrue(report.case_results[0].passed)

    def test_customer_message_must_agree_with_authoritative_state(self) -> None:
        class FalseSuccessAgent:
            name = "false-success"

            def run(self, request, tools):
                tools.verify_identity(request.customer_id, request.order_id)
                tools.get_order(request.order_id)
                tools.consult_refund_policy(request.order_id)
                return AgentOutput(
                    message="İadeniz başarıyla onaylandı.",
                    claimed_outcome="refunded",
                )

        ineligible_case = load_refund_cases(DATASET_PATH)[2]
        report = evaluate_agent(FalseSuccessAgent(), (ineligible_case,))

        result = report.case_results[0]
        self.assertFalse(result.passed)
        self.assertIn(
            "claimed_outcome_matches_state",
            {check.name for check in result.checks if not check.passed},
        )

    def test_order_must_be_read_before_a_committed_refund(self) -> None:
        class LateOrderReadAgent:
            name = "late-order-read"

            def run(self, request, tools):
                tools.verify_identity(request.customer_id, request.order_id)
                tools.consult_refund_policy(request.order_id)
                tools.issue_refund(
                    request.order_id,
                    4_000,
                    "USD",
                    approval_id=None,
                    idempotency_key=f"refund:{request.order_id}",
                )
                tools.get_order(request.order_id)
                return AgentOutput(
                    message="Your refund has been confirmed.",
                    claimed_outcome="refunded",
                )

        eligible_case = load_refund_cases(DATASET_PATH)[0]
        report = evaluate_agent(
            LateOrderReadAgent(),
            (eligible_case,),
            fault_mode="authorization-bypass",
        )

        self.assertEqual(1, report.unauthorized_action_count)
        self.assertFalse(report.case_results[0].passed)

    def test_identity_revocation_immediately_before_commit_is_caught(self) -> None:
        class RevokedIdentityAgent:
            name = "revoked-identity"

            def run(self, request, tools):
                tools.verify_identity(request.customer_id, request.order_id)
                order = tools.get_order(request.order_id)
                tools.consult_refund_policy(request.order_id)
                tools.issue_refund(
                    request.order_id,
                    int(order["amount_cents"]),
                    str(order["currency"]),
                    approval_id=None,
                    idempotency_key=f"refund:{request.order_id}",
                )
                return AgentOutput(
                    message="Your refund has been confirmed.",
                    claimed_outcome="refunded",
                )

        eligible_case = load_refund_cases(DATASET_PATH)[0]
        report = evaluate_agent(
            RevokedIdentityAgent(),
            (eligible_case,),
            fault_mode="identity-revoked-before-commit",
        )

        self.assertEqual(1, report.unauthorized_action_count)
        self.assertFalse(report.case_results[0].passed)

    def test_policy_failure_immediately_before_commit_is_caught(self) -> None:
        class InvalidatedPolicyAgent:
            name = "invalidated-policy"

            def run(self, request, tools):
                tools.verify_identity(request.customer_id, request.order_id)
                order = tools.get_order(request.order_id)
                tools.consult_refund_policy(request.order_id)
                tools.issue_refund(
                    request.order_id,
                    int(order["amount_cents"]),
                    str(order["currency"]),
                    approval_id=None,
                    idempotency_key=f"refund:{request.order_id}",
                )
                return AgentOutput(
                    message="Your refund has been confirmed.",
                    claimed_outcome="refunded",
                )

        eligible_case = load_refund_cases(DATASET_PATH)[0]
        report = evaluate_agent(
            InvalidatedPolicyAgent(),
            (eligible_case,),
            fault_mode="policy-invalid-before-commit",
        )

        self.assertEqual(1, report.unauthorized_action_count)
        self.assertFalse(report.case_results[0].passed)

    def test_agent_exception_becomes_a_failed_case_instead_of_losing_the_run(
        self,
    ) -> None:
        class CrashingAgent:
            name = "crashing-agent"

            def run(self, request, tools):
                del request, tools
                raise RuntimeError("synthetic tool failure")

        report = evaluate_agent(CrashingAgent(), load_refund_cases(DATASET_PATH))

        self.assertEqual(5, len(report.case_results))
        self.assertTrue(all(not result.passed for result in report.case_results))
        self.assertTrue(
            all(
                result.execution_error.startswith("RuntimeError:")
                for result in report.case_results
            )
        )

    def test_operational_bounds_do_not_get_averaged_into_quality(self) -> None:
        report = evaluate_agent(
            agent=ReferenceSupportAgent(),
            cases=load_refund_cases(DATASET_PATH),
            measurement_profile=MeasurementProfile(
                latency_ms=4_200,
                cost_usd_per_case=0.95,
            ),
        )
        decision = apply_release_gate(
            report,
            GatePolicy.for_initial_refund_slice(),
            baseline_task_success=0.80,
        )

        self.assertEqual(1.0, report.task_success_rate)
        self.assertFalse(decision.allowed)
        failed_rules = {rule.name for rule in decision.rules if not rule.passed}
        self.assertIn("operational_bound:p95_latency_ms", failed_rules)
        self.assertIn("operational_bound:cost_per_success_usd", failed_rules)


if __name__ == "__main__":
    unittest.main()
