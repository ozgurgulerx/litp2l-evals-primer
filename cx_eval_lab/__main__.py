"""Command-line entry point for reproducible local CX eval runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cx_eval_lab.agents import MutantSupportAgent, ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.gate import apply_release_gate, load_gate_policy
from cx_eval_lab.openai_runtime import OpenAIAgentsRuntime
from cx_eval_lab.runner import DEFAULT_MEASUREMENT_PROFILE, evaluate_agent


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = (
    REPOSITORY_ROOT / "evals/cx-support/datasets/regression/refund_v0.json"
)
DEFAULT_POLICY = REPOSITORY_ROOT / "evals/cx-support/policies/refund_gate_v0.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the CX eval lab")
    subparsers = parser.add_subparsers(dest="command", required=True)
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
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
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
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    failed = ", ".join(artifact["decision"]["failed_rules"]) or "none"
    print(f"release action: {decision.action}; failed rules: {failed}")
    return 0 if decision.allowed else 2


def _select_agent(name: str):
    if name == "reference":
        return ReferenceSupportAgent()
    if name == "openai":
        return OpenAIAgentsRuntime.from_environment()
    return MutantSupportAgent(name)


if __name__ == "__main__":
    raise SystemExit(main())
