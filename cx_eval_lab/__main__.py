"""Command-line entry point for reproducible local CX eval runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cx_eval_lab.agents import MutantSupportAgent, ReferenceSupportAgent
from cx_eval_lab.artifacts import replay_packet
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.evidence import (
    DeterministicTestReceipt,
    ExperimentManifest,
    PrerequisiteReceipt,
    build_evidence_receipt,
    canonical_hash,
)
from cx_eval_lab.gate import apply_release_gate, load_gate_policy
from cx_eval_lab.openai_runtime import OpenAIAgentsRuntime
from cx_eval_lab.runner import (
    DEFAULT_MEASUREMENT_PROFILE,
    evaluate_agent,
    run_paired_experiment,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = (
    REPOSITORY_ROOT / "evals/cx-support/datasets/regression/refund_v1.json"
)
DEFAULT_POLICY = REPOSITORY_ROOT / "evals/cx-support/policies/refund_gate_v1.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CX eval lab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    replay_parser = subparsers.add_parser("replay", help="validate and re-grade retained trials offline")
    replay_parser.add_argument("--input", type=Path, required=True)
    eval_parser = subparsers.add_parser("eval", help="run the refund slice and gate")
    eval_parser.add_argument(
        "--agent",
        choices=(
            "reference",
            "policy-bypass",
            "blind-retry",
            "same-key-retry",
            "openai",
        ),
        default="reference",
    )
    eval_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    eval_parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    eval_parser.add_argument("--output", type=Path, required=True)
    eval_parser.add_argument("--baseline-task-success", type=float, default=0.80)
    experiment_parser = subparsers.add_parser(
        "experiment",
        help="run a repeated paired deterministic experiment and write its receipt",
    )
    deterministic_agents = (
        "reference",
        "policy-bypass",
        "blind-retry",
        "same-key-retry",
    )
    experiment_parser.add_argument(
        "--baseline-agent",
        choices=deterministic_agents,
        default="reference",
    )
    experiment_parser.add_argument(
        "--candidate-agent",
        choices=deterministic_agents,
        default="reference",
    )
    experiment_parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    experiment_parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    experiment_parser.add_argument("--output", type=Path, required=True)
    experiment_parser.add_argument("--experiment-id", default="cx-paired-local-v1")
    experiment_parser.add_argument("--repetitions", type=int, default=2)
    experiment_parser.add_argument("--margin", type=float, default=0.03)
    experiment_parser.add_argument("--confidence-level", type=float, default=0.95)
    experiment_parser.add_argument(
        "--minimum-independent-clusters",
        type=int,
        default=30,
    )
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    if arguments.command == "replay":
        try:
            packet = json.loads(arguments.input.read_text(encoding="utf-8"))
            results = replay_packet(packet.get("experiment", packet))
        except (OSError, ValueError, AttributeError) as error:
            print(f"replay rejected: {error}")
            return 2
        print(f"replayed {len(results)} trials; authority: lab_only; no model calls")
        return 0
    if arguments.command == "experiment":
        return _run_experiment(arguments)
    if arguments.command != "eval":
        raise ValueError(f"unsupported command: {arguments.command}")

    agent = _select_agent(arguments.agent)
    measurement_profile = (
        None if arguments.agent == "openai" else DEFAULT_MEASUREMENT_PROFILE
    )
    fault_mode = {
        "policy-bypass": "authorization-bypass",
        "blind-retry": "duplicate-effect",
    }.get(arguments.agent)
    report = evaluate_agent(
        agent,
        load_refund_cases(arguments.dataset),
        measurement_profile=measurement_profile,
        fault_mode=fault_mode,
    )
    decision = apply_release_gate(
        report,
        load_gate_policy(arguments.policy),
        baseline_task_success=arguments.baseline_task_success,
    )
    artifact = {
        "evaluation": report.to_dict(),
        "decision": decision.to_dict(),
    }
    _write_json_immutable(arguments.output, artifact)
    failed = ", ".join(artifact["decision"]["failed_rules"]) or "none"
    print(f"release action: {decision.action}; failed rules: {failed}")
    return 0 if decision.allowed else 2


def _run_experiment(arguments: argparse.Namespace) -> int:
    cases = load_refund_cases(arguments.dataset)
    created_at = datetime.now(timezone.utc)
    code_revision = os.environ.get("CXLAB_CODE_REVISION", "working-tree-unpinned")
    manifest = ExperimentManifest(
        experiment_id=arguments.experiment_id,
        created_at=created_at.isoformat(),
        valid_until=(created_at + timedelta(days=30)).isoformat(),
        code_revision=code_revision,
        model_id=(
            f"baseline:{arguments.baseline_agent}|candidate:{arguments.candidate_agent}"
        ),
        prompt_version="deterministic-agent-code",
        tool_version="typed-refund-tools-v1",
        dataset_version=cases[0].dataset_version,
        evaluator_version="refund-evaluators-v1",
        policy_version=load_gate_policy(arguments.policy).policy_version,
        environment_version="python-3.12-local-lab",
        population_hash=canonical_hash(
            [[case.case_id, case.customer_id, list(case.slices)] for case in cases]
        ),
        repetitions=arguments.repetitions,
        measurement_kind="synthetic",
        estimand="candidate_minus_baseline_verified_task_success",
        statistical_method="clustered_normal_interval",
        non_inferiority_margin=arguments.margin,
        confidence_level=arguments.confidence_level,
        minimum_independent_clusters=arguments.minimum_independent_clusters,
        sequential_policy="fixed_sample_no_interim_looks",
        input_hashes=(
            ("dataset", _hash_file(arguments.dataset)),
            ("policy", _hash_file(arguments.policy)),
        ),
        invalidation_rules=(
            "model_or_prompt_change",
            "tool_or_evaluator_change",
            "dataset_or_policy_change",
        ),
    )
    baseline_agent = _select_agent(arguments.baseline_agent)
    candidate_agent = _select_agent(arguments.candidate_agent)
    experiment = run_paired_experiment(
        baseline_agent=baseline_agent,
        candidate_agent=candidate_agent,
        cases=cases,
        manifest=manifest,
        baseline_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
        candidate_measurement_profile=DEFAULT_MEASUREMENT_PROFILE,
    )
    receipt = build_evidence_receipt(
        experiment=experiment,
        deterministic_test_receipt=DeterministicTestReceipt(
            suite_id="paired-experiment-runtime-validation",
            code_revision=code_revision,
            checks=(
                ("all_trials_manifest_bound", all(
                    trial.manifest_hash == manifest.content_hash
                    for trial in experiment.all_trials
                )),
                ("paired_keys_match", {
                    trial.pair_key for trial in experiment.baseline_trials
                } == {
                    trial.pair_key for trial in experiment.candidate_trials
                }),
                ("registered_cases_executed", bool(experiment.all_trials)),
            ),
            artifact_hash=canonical_hash(experiment.to_dict()),
        ),
        prerequisite_receipts=(
            PrerequisiteReceipt(
                prerequisite_id="typed_tool_boundary",
                checks=(("implementation_present", True),),
                evidence_hash=_hash_file(REPOSITORY_ROOT / "cx_eval_lab/world.py"),
            ),
            PrerequisiteReceipt(
                prerequisite_id="semantic_state_grading",
                checks=(("implementation_present", True),),
                evidence_hash=_hash_file(
                    REPOSITORY_ROOT / "cx_eval_lab/evaluators.py"
                ),
            ),
        ),
        issued_at=created_at.isoformat(),
    )
    comparison = receipt.comparison
    artifact = {
        "experiment": experiment.to_dict(),
        "comparison": comparison.to_dict(),
        "receipt": receipt.to_dict(),
    }
    _write_json_immutable(arguments.output, artifact)
    print(
        f"evidence action: {receipt.action}; "
        f"independent clusters: {comparison.independent_cluster_count}"
    )
    if receipt.action == "lab_pass":
        return 0
    if receipt.action == "hold":
        return 3
    return 2


def _hash_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _write_json_immutable(path: Path, value: dict) -> None:
    """Create a packet once; refuse silent replacement of evidence artifacts."""

    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _select_agent(name: str):
    if name == "reference":
        return ReferenceSupportAgent()
    if name == "openai":
        return OpenAIAgentsRuntime.from_environment()
    return MutantSupportAgent(name)


if __name__ == "__main__":
    raise SystemExit(main())
