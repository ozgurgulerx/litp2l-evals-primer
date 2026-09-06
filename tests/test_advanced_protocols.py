"""Executable contracts for modern agent and eval-service failure modes."""

from __future__ import annotations

import unittest

from cx_eval_lab.advanced import (
    FactorialObservation,
    IntegrityObservation,
    KnowledgeActionTrial,
    MultiAgentTrial,
    PersistenceObservation,
    RunFragment,
    ServingFailureObservation,
    SimulatorPrediction,
    SkillTrial,
    VoiceTrial,
    backtest_simulator,
    evaluate_integrity,
    evaluate_knowledge_action,
    evaluate_multi_agent,
    evaluate_persistence,
    evaluate_serving_failure,
    evaluate_skill_trial,
    evaluate_voice_trial,
    factorial_attribution,
    resume_run,
)


class PersistenceAndServingTests(unittest.TestCase):
    def test_resume_preserves_constraints_approvals_work_and_exactly_once_effects(self) -> None:
        result = evaluate_persistence(
            PersistenceObservation(
                variant="restart_and_resume",
                constraints_before=("verify_identity", "max_refund_4000_usd"),
                constraints_after=("verify_identity", "max_refund_4000_usd"),
                approvals_before=("approval:order-1:4000:USD",),
                approvals_after=("approval:order-1:4000:USD",),
                completed_effects_before=("refund:order-1",),
                completed_effects_after=("refund:order-1",),
                unfinished_work_before=("notify_customer",),
                unfinished_work_after=("notify_customer",),
                transaction_ids=("refund:order-1",),
            )
        )

        self.assertTrue(result.passed)
        self.assertEqual(0, result.metric("duplicate_effect_count"))

    def test_compaction_that_loses_approval_and_duplicates_effect_fails(self) -> None:
        result = evaluate_persistence(
            PersistenceObservation(
                variant="compacted",
                constraints_before=("verify_identity",),
                constraints_after=("verify_identity",),
                approvals_before=("approval:order-1",),
                approvals_after=(),
                completed_effects_before=("refund:order-1",),
                completed_effects_after=("refund:order-1",),
                unfinished_work_before=("notify_customer",),
                unfinished_work_after=(),
                transaction_ids=("refund:order-1", "refund:order-1"),
            )
        )

        self.assertFalse(result.passed)
        self.assertEqual(
            {"approvals_preserved", "unfinished_work_preserved", "exactly_once_effects"},
            {check.name for check in result.checks if not check.passed},
        )

    def test_serving_failure_rejects_post_stream_fallback_and_blind_retry(self) -> None:
        result = evaluate_serving_failure(
            ServingFailureObservation(
                provider_failure="timeout_after_commit",
                stream_started=True,
                fallback_started=True,
                ambiguous_commit=True,
                inspected_state_before_retry=False,
                transaction_ids=("refund:1", "refund:2"),
            )
        )

        self.assertFalse(result.passed)
        self.assertEqual(
            {"no_fallback_after_stream_start", "inspect_before_retry", "exactly_once_effect"},
            {check.name for check in result.checks if not check.passed},
        )


class ModernAgentArchitectureTests(unittest.TestCase):
    def test_skill_selection_and_execution_failures_are_separate(self) -> None:
        selection = evaluate_skill_trial(
            SkillTrial(
                expected_skill="refund-policy",
                selected_skill="generic-support",
                instructions_current=True,
                execution_passed=True,
            )
        )
        execution = evaluate_skill_trial(
            SkillTrial(
                expected_skill="refund-policy",
                selected_skill="refund-policy",
                instructions_current=True,
                execution_passed=False,
            )
        )

        self.assertEqual("selection_error", selection.error_stage)
        self.assertEqual("execution_error", execution.error_stage)

    def test_oracle_documents_do_not_guarantee_correct_action(self) -> None:
        result = evaluate_knowledge_action(
            KnowledgeActionTrial(
                interface="oracle_documents",
                required_knowledge_present=True,
                retrieved_correctly=True,
                reasoning_correct=True,
                action_correct=False,
                final_state_correct=False,
            )
        )

        self.assertFalse(result.passed)
        self.assertTrue(result.metric("retrieval_success"))
        self.assertFalse(result.metric("action_success"))
        self.assertEqual("action", result.failure_stage)

    def test_voice_action_before_utterance_end_is_a_hard_failure(self) -> None:
        result = evaluate_voice_trial(
            VoiceTrial(
                task_id="voice-refund-1",
                utterance_end_ms=4_200,
                action_started_ms=3_900,
                expected_identifier="order-817",
                heard_identifier="order-817",
                interruption_recovered=True,
                packet_loss_recovered=True,
                task_completed=True,
            )
        )

        self.assertFalse(result.passed)
        self.assertIn(
            "action_after_user_finished",
            {check.name for check in result.checks if not check.passed},
        )

    def test_multi_agent_protocol_detects_coverage_duplicates_merges_and_budget(self) -> None:
        result = evaluate_multi_agent(
            MultiAgentTrial(
                required_subtasks=("policy", "ledger", "customer-message"),
                assignments=(
                    ("agent-a", "policy"),
                    ("agent-b", "policy"),
                    ("agent-c", "ledger"),
                ),
                completed_subtasks=("policy", "ledger"),
                side_effect_keys=("refund:817", "refund:817"),
                merge_conflict_count=1,
                information_loss_count=1,
                cost_usd=0.90,
                matched_budget_usd=0.60,
            )
        )

        self.assertFalse(result.passed)
        self.assertAlmostEqual(2 / 3, result.metric("coverage"))
        self.assertEqual(1, result.metric("duplicate_assignment_count"))
        self.assertEqual(1, result.metric("duplicate_effect_count"))
        self.assertFalse(result.metric("within_matched_budget"))


class AttributionIntegrityAndOperationsTests(unittest.TestCase):
    def test_factorial_attribution_holds_model_and_harness_separately(self) -> None:
        result = factorial_attribution(
            (
                FactorialObservation("model-a", "harness-1", 0.70, 0.10),
                FactorialObservation("model-a", "harness-2", 0.80, 0.12),
                FactorialObservation("model-b", "harness-1", 0.75, 0.11),
                FactorialObservation("model-b", "harness-2", 0.85, 0.13),
            )
        )

        self.assertAlmostEqual(0.05, result.model_effect("model-b", "model-a"))
        self.assertAlmostEqual(0.10, result.harness_effect("harness-2", "harness-1"))

    def test_development_judge_gain_with_independent_regression_is_rejected(self) -> None:
        result = evaluate_integrity(
            IntegrityObservation(
                development_judge_delta=0.12,
                independent_verifier_delta=-0.08,
                answer_artifact_accessed=False,
                sealed_labels_accessed=False,
                grader_modified_by_candidate=False,
            )
        )

        self.assertFalse(result.passed)
        self.assertTrue(result.metric("moving_target_divergence"))
        self.assertEqual("independent_verification_regressed", result.reason)

    def test_contaminated_run_is_rejected_even_when_scores_improve(self) -> None:
        result = evaluate_integrity(
            IntegrityObservation(
                development_judge_delta=0.20,
                independent_verifier_delta=0.10,
                answer_artifact_accessed=True,
                sealed_labels_accessed=False,
                grader_modified_by_candidate=False,
            )
        )

        self.assertFalse(result.passed)
        self.assertEqual("evaluation_contaminated", result.reason)

    def test_simulator_backtest_reports_probability_error(self) -> None:
        result = backtest_simulator(
            (
                SimulatorPrediction("case-1", 0.9, True),
                SimulatorPrediction("case-2", 0.8, False),
                SimulatorPrediction("case-3", 0.2, False),
                SimulatorPrediction("case-4", 0.1, True),
            ),
            decision_threshold=0.5,
        )

        self.assertEqual(0.5, result.accuracy)
        self.assertAlmostEqual(0.425, result.brier_score)

    def test_resumable_run_is_idempotent_and_rejects_conflicting_fragments(self) -> None:
        first = RunFragment("run-1", "case-1", 0, "manifest-a", "hash-a")
        same = RunFragment("run-1", "case-1", 0, "manifest-a", "hash-a")
        conflicting = RunFragment("run-1", "case-1", 0, "manifest-a", "hash-b")

        resumed = resume_run((first,), (same,), expected_manifest_hash="manifest-a")

        self.assertEqual((first,), resumed)
        with self.assertRaisesRegex(ValueError, "conflicting fragment"):
            resume_run((first,), (conflicting,), expected_manifest_hash="manifest-a")


if __name__ == "__main__":
    unittest.main()
