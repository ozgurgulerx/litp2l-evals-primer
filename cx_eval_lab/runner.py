"""Evaluation runner for isolated, resettable CX cases."""

from __future__ import annotations

import math
import time
from typing import Protocol

from cx_eval_lab.evaluators import evaluate_case
from cx_eval_lab.models import (
    AgentOutput,
    EvaluationReport,
    MeasurementProfile,
    RefundAgentInput,
    RefundCase,
)
from cx_eval_lab.world import RefundTools, RefundWorld


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
