"""Contract tests for the optional OpenAI Agents SDK runtime."""

from __future__ import annotations

import json
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from cx_eval_lab.models import RefundCase, ResolutionResponse
from cx_eval_lab.openai_runtime import OpenAIAgentsRuntime, RuntimeConfigurationError
from cx_eval_lab.world import RefundTools, RefundWorld


class OpenAIAgentsRuntimeTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_live_runtime_requires_api_key_and_explicit_model(self) -> None:
        with self.assertRaisesRegex(RuntimeConfigurationError, "OPENAI_API_KEY"):
            OpenAIAgentsRuntime.from_environment()

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_live_runtime_requires_a_pinned_model(self) -> None:
        with self.assertRaisesRegex(RuntimeConfigurationError, "OPENAI_MODEL"):
            OpenAIAgentsRuntime.from_environment()

    @patch.dict(
        "os.environ",
        {"OPENAI_API_KEY": "test-key", "OPENAI_MODEL": "test-model"},
        clear=True,
    )
    def test_configuration_reads_secrets_without_storing_the_key(self) -> None:
        runtime = OpenAIAgentsRuntime.from_environment()

        self.assertEqual("test-model", runtime.model)
        self.assertNotIn("test-key", repr(runtime))
        self.assertFalse(hasattr(runtime, "api_key"))

    def test_runtime_wraps_the_mock_world_without_making_a_network_call(self) -> None:
        case = RefundCase(
            case_id="openai-adapter-001",
            customer_id="customer-001",
            order_id="order-001",
            utterance="Please refund this eligible order.",
            amount_cents=4_000,
            eligible=True,
            approval_threshold_cents=10_000,
            expected_outcome="refunded",
            slices=("language:en",),
        )
        world = RefundWorld.from_case(case)
        tools = RefundTools(world)
        fake_agents = self._fake_agents_module()

        with patch.dict("sys.modules", {"agents": fake_agents}):
            output = OpenAIAgentsRuntime(model="test-model").run(
                case.agent_input,
                tools,
            )

        self.assertEqual("Refund confirmed.", output.message)
        self.assertEqual("refunded", output.claimed_outcome)
        self.assertEqual(1, world.snapshot.refund_transaction_count)
        self.assertEqual(
            ("verify_identity", "get_order", "consult_refund_policy", "issue_refund"),
            tuple(event.tool for event in world.events),
        )

    @staticmethod
    def _fake_agents_module() -> ModuleType:
        fake_module = ModuleType("agents")

        class FakeAgent:
            def __init__(self, **configuration):
                self.tools = configuration["tools"]
                self.model_settings = configuration["model_settings"]
                self.output_type = configuration["output_type"]

        class FakeRunner:
            @staticmethod
            def run_sync(agent, utterance, max_turns, run_config):
                request = json.loads(utterance)
                del max_turns
                assert agent.model_settings.parallel_tool_calls is False
                assert run_config.trace_include_sensitive_data is False
                customer_id = request["customer_id"]
                order_id = request["target_order_id"]
                agent.tools[0](customer_id, order_id)
                order = json.loads(agent.tools[1](order_id))
                policy = json.loads(agent.tools[2](order_id))
                if policy["eligible"]:
                    agent.tools[4](
                        order_id,
                        order["amount_cents"],
                        order["currency"],
                        None,
                        f"refund:{order_id}",
                    )
                return SimpleNamespace(
                    final_output=ResolutionResponse(
                        message="Refund confirmed.",
                        claimed_outcome="refunded",
                    )
                )

        fake_module.Agent = FakeAgent
        fake_module.ModelSettings = lambda **values: SimpleNamespace(**values)
        fake_module.RunConfig = lambda **values: SimpleNamespace(**values)
        fake_module.Runner = FakeRunner
        fake_module.function_tool = lambda function: function
        return fake_module


if __name__ == "__main__":
    unittest.main()
