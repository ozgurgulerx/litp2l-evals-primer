"""A small, executable CX-agent evaluation system used by the primer."""

from cx_eval_lab.agents import MutantSupportAgent, ReferenceSupportAgent
from cx_eval_lab.dataset import load_refund_cases
from cx_eval_lab.gate import GatePolicy, apply_release_gate
from cx_eval_lab.runner import evaluate_agent

__all__ = (
    "GatePolicy",
    "MutantSupportAgent",
    "ReferenceSupportAgent",
    "apply_release_gate",
    "evaluate_agent",
    "load_refund_cases",
)
