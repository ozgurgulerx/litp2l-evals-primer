"""Evaluation runner for isolated, resettable CX cases."""

from __future__ import annotations

import math
import time
from typing import Protocol

from cx_eval_lab.evaluators import evaluate_case
from cx_eval_lab.evidence import ExperimentManifest, PairedExperiment
from cx_eval_lab.models import (
    AgentOutput,
    EvaluationReport,
    MeasurementProfile,
    RefundAgentInput,
    RefundCase,
)
from cx_eval_lab.world import RefundTools, RefundWorld
from cx_eval_lab.statistics import PairedTrial


DEFAULT_MEASUREMENT_PROFILE = MeasurementProfile(
    latency_ms=250,
    cost_usd_per_case=0.08,
)


class SupportAgent(Protocol):
    name: str

    def run(self, request: RefundAgentInput, tools: RefundTools) -> AgentOutput: ...


def evaluate_agent(
    agent: SupportAgent,
    cases: tuple[RefundCase, ...],
    measurement_profile: MeasurementProfile | None = DEFAULT_MEASUREMENT_PROFILE,
    fault_mode: str | None = None,
) -> EvaluationReport:
    if not cases:
        raise ValueError("at least one evaluation case is required")
    dataset_versions = {case.dataset_version for case in cases}
    if len(dataset_versions) != 1:
        raise ValueError("all cases in one run must share a dataset version")

    case_results = tuple(
        _evaluate_isolated(agent, case, measurement_profile, fault_mode)
        for case in cases
    )
    successful_results = tuple(result for result in case_results if result.passed)
    slice_rates = _calculate_slice_rates(case_results)
    known_costs = tuple(
        result.cost_usd for result in case_results if result.cost_usd is not None
    )
    cost_per_success = None
    if len(known_costs) == len(case_results) and successful_results:
        cost_per_success = round(sum(known_costs) / len(successful_results), 6)

    return EvaluationReport(
        dataset_version=cases[0].dataset_version,
        agent_name=agent.name,
        case_results=case_results,
        task_success_rate=len(successful_results) / len(case_results),
        slice_success_rates=tuple(sorted(slice_rates.items())),
        unauthorized_action_count=sum(
            result.unauthorized_action_count for result in case_results
        ),
        duplicate_refund_count=sum(
            result.duplicate_refund_count for result in case_results
        ),
        unsafe_timeout_recovery_count=sum(
            result.unsafe_timeout_recovery_count for result in case_results
        ),
        false_success_claim_count=sum(
            result.false_success_claim_count for result in case_results
        ),
        p95_latency_ms=_nearest_rank_p95(
            tuple(result.latency_ms for result in case_results)
        ),
        cost_per_success_usd=cost_per_success,
        measurement_kind=(
            "measured" if measurement_profile is None else measurement_profile.evidence_kind
        ),
        measurement_source=(
            "runner wall-clock; cost unavailable"
            if measurement_profile is None
            else measurement_profile.source
        ),
        false_message_claim_count=sum(
            result.false_message_claim_count for result in case_results
        ),
        unjustified_escalation_count=sum(
            result.unjustified_escalation_count for result in case_results
        ),
        human_intervention_count=sum(
            result.human_intervention_count for result in case_results
        ),
        unresolved_work_count=sum(
            result.unresolved_work_count for result in case_results
        ),
    )


def run_paired_experiment(
    *,
    baseline_agent: SupportAgent,
    candidate_agent: SupportAgent,
    cases: tuple[RefundCase, ...],
    manifest: ExperimentManifest,
    baseline_measurement_profile: MeasurementProfile | None,
    candidate_measurement_profile: MeasurementProfile | None,
) -> PairedExperiment:
    """Run registered baseline/candidate repetitions on identical isolated cases."""

    if not cases:
        raise ValueError("at least one evaluation case is required")
    if {case.dataset_version for case in cases} != {manifest.dataset_version}:
        raise ValueError("manifest and case dataset versions must match")
    for profile in (baseline_measurement_profile, candidate_measurement_profile):
        observed_kind = "measured" if profile is None else profile.evidence_kind
        if observed_kind != manifest.measurement_kind:
            raise ValueError("measurement profile and manifest evidence kind must match")

    baseline_trials: list[PairedTrial] = []
    candidate_trials: list[PairedTrial] = []
    for trial_index in range(manifest.repetitions):
        for case in cases:
            baseline_result = _evaluate_isolated(
                baseline_agent,
                case,
                baseline_measurement_profile,
                None,
            )
            candidate_result = _evaluate_isolated(
                candidate_agent,
                case,
                candidate_measurement_profile,
                None,
            )
            baseline_trials.append(
                _to_paired_trial(
                    baseline_result,
                    case,
                    trial_index,
                    "baseline",
                    manifest.content_hash,
                )
            )
            candidate_trials.append(
                _to_paired_trial(
                    candidate_result,
                    case,
                    trial_index,
                    "candidate",
                    manifest.content_hash,
                )
            )
    return PairedExperiment(
        manifest=manifest,
        baseline_trials=tuple(baseline_trials),
        candidate_trials=tuple(candidate_trials),
    )


def _to_paired_trial(
    result,
    case: RefundCase,
    trial_index: int,
    arm: str,
    manifest_hash: str,
) -> PairedTrial:
    return PairedTrial(
        case_id=case.case_id,
        trial_index=trial_index,
        cluster_id=case.customer_id,
        arm=arm,
        passed=result.passed,
        latency_ms=result.latency_ms,
        cost_usd=result.cost_usd,
        manifest_hash=manifest_hash,
        failed_checks=tuple(check.name for check in result.checks if not check.passed),
    )


def _evaluate_isolated(
    agent: SupportAgent,
    case: RefundCase,
    measurement_profile: MeasurementProfile | None,
    fault_mode: str | None,
):
    world = RefundWorld.from_case(case)
    tools = RefundTools(world, fault_mode=fault_mode)
    execution_error = None
    started_at = time.perf_counter()
    try:
        output = agent.run(case.agent_input, tools)
    except Exception as error:
        execution_error = f"{type(error).__name__}: agent execution failed"
        output = AgentOutput(
            message="The agent did not complete this case.",
            claimed_outcome="needs_review",
        )
    measured_latency_ms = round((time.perf_counter() - started_at) * 1_000)
    latency_ms = (
        measured_latency_ms
        if measurement_profile is None
        else measurement_profile.latency_ms
    )
    cost_usd = (
        None if measurement_profile is None else measurement_profile.cost_usd_per_case
    )
    return evaluate_case(
        case,
        output,
        world.events,
        world.snapshot,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        execution_error=execution_error,
    )


def _calculate_slice_rates(case_results) -> dict[str, float]:
    grouped: dict[str, tuple[bool, ...]] = {}
    for result in case_results:
        for slice_name in result.slices:
            grouped = {
                **grouped,
                slice_name: (*grouped.get(slice_name, ()), result.passed),
            }
    return {
        slice_name: sum(outcomes) / len(outcomes)
        for slice_name, outcomes in grouped.items()
    }


def _nearest_rank_p95(latencies: tuple[int, ...]) -> int:
    ordered = tuple(sorted(latencies))
    rank = max(1, math.ceil(0.95 * len(ordered)))
    return ordered[rank - 1]
