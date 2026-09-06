"""Typed scorer fixtures for advanced agent-evaluation failure modes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


MetricValue = bool | int | float | str


@dataclass(frozen=True)
class ProtocolCheck:
    name: str
    passed: bool
    observed: str


@dataclass(frozen=True)
class ProtocolResult:
    subject: str
    passed: bool
    checks: tuple[ProtocolCheck, ...]
    metrics: tuple[tuple[str, MetricValue], ...]
    failure_stage: str | None = None
    error_stage: str | None = None
    reason: str | None = None

    def metric(self, name: str) -> MetricValue:
        values = dict(self.metrics)
        if name not in values:
            raise KeyError(name)
        return values[name]

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "passed": self.passed,
            "checks": [asdict(check) for check in self.checks],
            "metrics": dict(self.metrics),
            "failure_stage": self.failure_stage,
            "error_stage": self.error_stage,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PersistenceObservation:
    variant: str
    constraints_before: tuple[str, ...]
    constraints_after: tuple[str, ...]
    approvals_before: tuple[str, ...]
    approvals_after: tuple[str, ...]
    completed_effects_before: tuple[str, ...]
    completed_effects_after: tuple[str, ...]
    unfinished_work_before: tuple[str, ...]
    unfinished_work_after: tuple[str, ...]
    transaction_ids: tuple[str, ...]


def evaluate_persistence(observation: PersistenceObservation) -> ProtocolResult:
    checks = (
        _preservation_check(
            "constraints_preserved",
            observation.constraints_before,
            observation.constraints_after,
        ),
        _preservation_check(
            "approvals_preserved",
            observation.approvals_before,
            observation.approvals_after,
        ),
        _preservation_check(
            "completed_effects_preserved",
            observation.completed_effects_before,
            observation.completed_effects_after,
        ),
        _preservation_check(
            "unfinished_work_preserved",
            observation.unfinished_work_before,
            observation.unfinished_work_after,
        ),
        ProtocolCheck(
            "exactly_once_effects",
            len(observation.transaction_ids) == len(set(observation.transaction_ids)),
            f"transactions={len(observation.transaction_ids)}; unique={len(set(observation.transaction_ids))}",
        ),
    )
    duplicate_count = len(observation.transaction_ids) - len(
        set(observation.transaction_ids)
    )
    return _result(
        f"persistence:{observation.variant}",
        checks,
        (("duplicate_effect_count", duplicate_count),),
        failure_stage="persistence" if not all(item.passed for item in checks) else None,
    )


def _preservation_check(
    name: str,
    before: tuple[str, ...],
    after: tuple[str, ...],
) -> ProtocolCheck:
    missing = set(before) - set(after)
    return ProtocolCheck(name, not missing, f"missing={sorted(missing)}")


@dataclass(frozen=True)
class ServingFailureObservation:
    provider_failure: str
    stream_started: bool
    fallback_started: bool
    ambiguous_commit: bool
    inspected_state_before_retry: bool
    transaction_ids: tuple[str, ...]


def evaluate_serving_failure(observation: ServingFailureObservation) -> ProtocolResult:
    checks = (
        ProtocolCheck(
            "no_fallback_after_stream_start",
            not (observation.stream_started and observation.fallback_started),
            f"stream_started={observation.stream_started}; fallback_started={observation.fallback_started}",
        ),
        ProtocolCheck(
            "inspect_before_retry",
            not observation.ambiguous_commit or observation.inspected_state_before_retry,
            f"ambiguous={observation.ambiguous_commit}; inspected={observation.inspected_state_before_retry}",
        ),
        ProtocolCheck(
            "exactly_once_effect",
            len(observation.transaction_ids) <= 1,
            f"transaction_count={len(observation.transaction_ids)}",
        ),
    )
    return _result(
        f"serving_failure:{observation.provider_failure}",
        checks,
        (("extra_effect_count", max(0, len(observation.transaction_ids) - 1)),),
        failure_stage="serving_or_recovery" if not all(item.passed for item in checks) else None,
    )


@dataclass(frozen=True)
class SkillTrial:
    expected_skill: str
    selected_skill: str | None
    instructions_current: bool
    execution_passed: bool


def evaluate_skill_trial(trial: SkillTrial) -> ProtocolResult:
    selection_passed = trial.selected_skill == trial.expected_skill
    current_passed = selection_passed and trial.instructions_current
    execution_passed = current_passed and trial.execution_passed
    checks = (
        ProtocolCheck(
            "skill_selected",
            selection_passed,
            f"expected={trial.expected_skill}; selected={trial.selected_skill}",
        ),
        ProtocolCheck(
            "instructions_current",
            current_passed,
            f"current={trial.instructions_current}",
        ),
        ProtocolCheck(
            "skill_execution",
            execution_passed,
            f"passed={trial.execution_passed}",
        ),
    )
    if not selection_passed:
        error_stage = "selection_error"
    elif not trial.instructions_current:
        error_stage = "stale_instruction_error"
    elif not trial.execution_passed:
        error_stage = "execution_error"
    else:
        error_stage = None
    return _result(
        "skill_selection_and_execution",
        checks,
        (("selection_passed", selection_passed), ("execution_passed", execution_passed)),
        error_stage=error_stage,
    )


@dataclass(frozen=True)
class KnowledgeActionTrial:
    interface: str
    required_knowledge_present: bool
    retrieved_correctly: bool
    reasoning_correct: bool
    action_correct: bool
    final_state_correct: bool


def evaluate_knowledge_action(trial: KnowledgeActionTrial) -> ProtocolResult:
    checks = (
        ProtocolCheck(
            "required_knowledge_available",
            trial.required_knowledge_present,
            trial.interface,
        ),
        ProtocolCheck("retrieval", trial.retrieved_correctly, trial.interface),
        ProtocolCheck("reasoning", trial.reasoning_correct, trial.interface),
        ProtocolCheck("action", trial.action_correct, trial.interface),
        ProtocolCheck("final_state", trial.final_state_correct, trial.interface),
    )
    if not trial.required_knowledge_present or not trial.retrieved_correctly:
        failure_stage = "knowledge"
    elif not trial.reasoning_correct:
        failure_stage = "reasoning"
    elif not trial.action_correct:
        failure_stage = "action"
    elif not trial.final_state_correct:
        failure_stage = "outcome"
    else:
        failure_stage = None
    return _result(
        f"knowledge_action:{trial.interface}",
        checks,
        (
            ("retrieval_success", trial.retrieved_correctly),
            ("action_success", trial.action_correct),
            ("state_success", trial.final_state_correct),
        ),
        failure_stage=failure_stage,
    )


@dataclass(frozen=True)
class VoiceTrial:
    task_id: str
    utterance_end_ms: int
    action_started_ms: int | None
    expected_identifier: str
    heard_identifier: str
    interruption_recovered: bool
    packet_loss_recovered: bool
    task_completed: bool


def evaluate_voice_trial(trial: VoiceTrial) -> ProtocolResult:
    action_after_end = (
        trial.action_started_ms is None or trial.action_started_ms >= trial.utterance_end_ms
    )
    checks = (
        ProtocolCheck(
            "action_after_user_finished",
            action_after_end,
            f"utterance_end={trial.utterance_end_ms}; action_start={trial.action_started_ms}",
        ),
        ProtocolCheck(
            "identifier_preserved",
            trial.heard_identifier == trial.expected_identifier,
            f"expected={trial.expected_identifier}; heard={trial.heard_identifier}",
        ),
        ProtocolCheck(
            "interruption_recovered",
            trial.interruption_recovered,
            str(trial.interruption_recovered),
        ),
        ProtocolCheck(
            "packet_loss_recovered",
            trial.packet_loss_recovered,
            str(trial.packet_loss_recovered),
        ),
        ProtocolCheck("task_completed", trial.task_completed, str(trial.task_completed)),
    )
    return _result(
        f"voice:{trial.task_id}",
        checks,
        (
            ("premature_action", not action_after_end),
            ("identifier_correct", trial.heard_identifier == trial.expected_identifier),
        ),
        failure_stage="voice_timeline" if not all(item.passed for item in checks) else None,
    )


@dataclass(frozen=True)
class MultiAgentTrial:
    required_subtasks: tuple[str, ...]
    assignments: tuple[tuple[str, str], ...]
    completed_subtasks: tuple[str, ...]
    side_effect_keys: tuple[str, ...]
    merge_conflict_count: int
    information_loss_count: int
    cost_usd: float
    matched_budget_usd: float


def evaluate_multi_agent(trial: MultiAgentTrial) -> ProtocolResult:
    required = set(trial.required_subtasks)
    completed = set(trial.completed_subtasks)
    assigned_subtasks = tuple(task for _, task in trial.assignments)
    duplicate_assignments = len(assigned_subtasks) - len(set(assigned_subtasks))
    duplicate_effects = len(trial.side_effect_keys) - len(set(trial.side_effect_keys))
    coverage = len(required & completed) / len(required) if required else 1.0
    within_budget = trial.cost_usd <= trial.matched_budget_usd
    checks = (
        ProtocolCheck("complete_coverage", coverage == 1.0, f"coverage={coverage:.3f}"),
        ProtocolCheck(
            "no_duplicate_assignments",
            duplicate_assignments == 0,
            f"count={duplicate_assignments}",
        ),
        ProtocolCheck(
            "no_duplicate_effects",
            duplicate_effects == 0,
            f"count={duplicate_effects}",
        ),
        ProtocolCheck(
            "conflict_free_merge",
            trial.merge_conflict_count == 0,
            f"count={trial.merge_conflict_count}",
        ),
        ProtocolCheck(
            "lossless_handoff",
            trial.information_loss_count == 0,
            f"count={trial.information_loss_count}",
        ),
        ProtocolCheck(
            "within_matched_budget",
            within_budget,
            f"observed={trial.cost_usd}; budget={trial.matched_budget_usd}",
        ),
    )
    return _result(
        "multi_agent_coordination",
        checks,
        (
            ("coverage", coverage),
            ("duplicate_assignment_count", duplicate_assignments),
            ("duplicate_effect_count", duplicate_effects),
            ("merge_conflict_count", trial.merge_conflict_count),
            ("information_loss_count", trial.information_loss_count),
            ("within_matched_budget", within_budget),
        ),
        failure_stage="coordination" if not all(item.passed for item in checks) else None,
    )


@dataclass(frozen=True)
class FactorialObservation:
    model: str
    harness: str
    success_rate: float
    cost_usd: float


@dataclass(frozen=True)
class FactorialAttribution:
    model_means: tuple[tuple[str, float], ...]
    harness_means: tuple[tuple[str, float], ...]
    cell_count: int

    def model_effect(self, candidate: str, baseline: str) -> float:
        values = dict(self.model_means)
        return values[candidate] - values[baseline]

    def harness_effect(self, candidate: str, baseline: str) -> float:
        values = dict(self.harness_means)
        return values[candidate] - values[baseline]


def factorial_attribution(
    observations: tuple[FactorialObservation, ...],
) -> FactorialAttribution:
    if not observations:
        raise ValueError("factorial observations are required")
    models = {item.model for item in observations}
    harnesses = {item.harness for item in observations}
    cells = {(item.model, item.harness) for item in observations}
    if len(cells) != len(observations) or cells != {
        (model, harness) for model in models for harness in harnesses
    }:
        raise ValueError("factorial design must contain one observation per model-harness cell")
    model_means = tuple(
        sorted(
            (
                model,
                sum(item.success_rate for item in observations if item.model == model)
                / len(harnesses),
            )
            for model in models
        )
    )
    harness_means = tuple(
        sorted(
            (
                harness,
                sum(item.success_rate for item in observations if item.harness == harness)
                / len(models),
            )
            for harness in harnesses
        )
    )
    return FactorialAttribution(model_means, harness_means, len(observations))


@dataclass(frozen=True)
class IntegrityObservation:
    development_judge_delta: float
    independent_verifier_delta: float
    answer_artifact_accessed: bool
    sealed_labels_accessed: bool
    grader_modified_by_candidate: bool


def evaluate_integrity(observation: IntegrityObservation) -> ProtocolResult:
    contaminated = any(
        (
            observation.answer_artifact_accessed,
            observation.sealed_labels_accessed,
            observation.grader_modified_by_candidate,
        )
    )
    divergence = (
        observation.development_judge_delta > 0
        and observation.independent_verifier_delta < 0
    )
    checks = (
        ProtocolCheck("evaluation_uncontaminated", not contaminated, str(contaminated)),
        ProtocolCheck("independent_verification_non_regressing", not divergence, str(divergence)),
    )
    if contaminated:
        reason = "evaluation_contaminated"
    elif divergence:
        reason = "independent_verification_regressed"
    else:
        reason = None
    return _result(
        "evaluation_integrity",
        checks,
        (
            ("contaminated", contaminated),
            ("moving_target_divergence", divergence),
        ),
        failure_stage="integrity" if reason else None,
        reason=reason,
    )


@dataclass(frozen=True)
class SimulatorPrediction:
    case_id: str
    predicted_success_probability: float
    observed_human_success: bool


@dataclass(frozen=True)
class SimulatorBacktest:
    sample_size: int
    decision_threshold: float
    accuracy: float
    brier_score: float


def backtest_simulator(
    predictions: tuple[SimulatorPrediction, ...],
    *,
    decision_threshold: float,
) -> SimulatorBacktest:
    if not predictions:
        raise ValueError("simulator predictions are required")
    if not 0 <= decision_threshold <= 1:
        raise ValueError("decision_threshold must be in [0, 1]")
    if any(not 0 <= item.predicted_success_probability <= 1 for item in predictions):
        raise ValueError("predicted probabilities must be in [0, 1]")
    correct = sum(
        (item.predicted_success_probability >= decision_threshold)
        == item.observed_human_success
        for item in predictions
    )
    brier = sum(
        (item.predicted_success_probability - float(item.observed_human_success)) ** 2
        for item in predictions
    ) / len(predictions)
    return SimulatorBacktest(
        sample_size=len(predictions),
        decision_threshold=decision_threshold,
        accuracy=correct / len(predictions),
        brier_score=brier,
    )


@dataclass(frozen=True)
class RunFragment:
    run_id: str
    case_id: str
    trial_index: int
    manifest_hash: str
    content_hash: str

    @property
    def key(self) -> tuple[str, str, int]:
        return self.run_id, self.case_id, self.trial_index


def resume_run(
    existing: tuple[RunFragment, ...],
    incoming: tuple[RunFragment, ...],
    *,
    expected_manifest_hash: str,
) -> tuple[RunFragment, ...]:
    indexed: dict[tuple[str, str, int], RunFragment] = {}
    for fragment in (*existing, *incoming):
        if fragment.manifest_hash != expected_manifest_hash:
            raise ValueError("fragment manifest does not match the resumed run")
        prior = indexed.get(fragment.key)
        if prior is not None and prior.content_hash != fragment.content_hash:
            raise ValueError(f"conflicting fragment for {fragment.key}")
        indexed = {**indexed, fragment.key: fragment}
    return tuple(indexed[key] for key in sorted(indexed))


def _result(
    subject: str,
    checks: tuple[ProtocolCheck, ...],
    metrics: tuple[tuple[str, MetricValue], ...],
    *,
    failure_stage: str | None = None,
    error_stage: str | None = None,
    reason: str | None = None,
) -> ProtocolResult:
    return ProtocolResult(
        subject=subject,
        passed=all(check.passed for check in checks),
        checks=checks,
        metrics=metrics,
        failure_stage=failure_stage,
        error_stage=error_stage,
        reason=reason,
    )
