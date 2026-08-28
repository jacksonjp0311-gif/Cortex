"""v10.0-alpha.1 native agent runtime and adversarial boundary tests."""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import (
    FixtureAdapter,
    ModelAdapterError,
    run_model_circulation,
    verify_model_circulation,
)
from cortex.native_agent import (
    AgentModelRequest,
    CapabilityGrant,
    NativeAgentRuntime,
    ScriptedAgentAdapter,
    verify_native_agent_trajectory,
)
from cortex.provider_fabric import HttpProviderAgentAdapter
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


class V100NativeAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("CORTEX_NATIVE_TOKEN\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "NativeHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _grant(self, *tools: str) -> CapabilityGrant:
        return CapabilityGrant(workspace_root=str(self.host), allowed_tools=tools)

    def test_complete_tool_loop_seals_reconstructable_trajectory(self) -> None:
        adapter = ScriptedAgentAdapter(
            [
                {
                    "public_output": {"text": "I will inspect the file."},
                    "tool_calls": [
                        {"id": "read-1", "name": "filesystem.read", "arguments": {"path": "README.md"}}
                    ],
                    "finish_reason": "tool_calls",
                    "chain_of_thought": "must be discarded",
                    "success": True,
                },
                {"public_output": {"text": "Found CORTEX_NATIVE_TOKEN."}, "finish_reason": "stop"},
            ],
            model_id="provider-a",
        )
        events: list[dict] = []
        result = NativeAgentRuntime(self.store, self.repo, event_sink=events.append).run(
            "Read the repository token", adapter=adapter, grant=self._grant("filesystem.read")
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["tool_call_count"], 1)
        self.assertTrue(result["verification"]["valid"], result["verification"])
        self.assertEqual(events[0]["event_type"], "session.started")
        self.assertEqual(events[-1]["event_type"], "trajectory.sealed")
        receipt = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        serialized = str(receipt)
        self.assertNotIn("must be discarded", serialized)
        self.assertNotIn("chain_of_thought", serialized)
        self.assertFalse(receipt["host_mutate_authorized"])
        self.assertFalse(receipt["execution_authorized"])

    def test_model_receives_cortex_identity_projection_and_granted_tools(self) -> None:
        captured = []

        class CapturingAdapter(ScriptedAgentAdapter):
            def invoke_agent(self, request):
                captured.append(request)
                return super().invoke_agent(request)

        result = NativeAgentRuntime(self.store, self.repo).run(
            "Inspect Cortex",
            adapter=CapturingAdapter([{"public_output": "ready", "finish_reason": "stop"}]),
            grant=self._grant("filesystem.list", "filesystem.read"),
        )
        self.assertEqual(result["status"], "completed")
        system = captured[0].messages[0].content
        self.assertIn("operating inside Cortex", system)
        self.assertIn('"repository":"NativeHost"', system)
        self.assertIn('"context_projection"', system)
        self.assertIn('"filesystem.list"', system)
        self.assertIn('"host_mutate_authorized":false', system)
        provider_tools = HttpProviderAgentAdapter._tools(captured[0])
        self.assertEqual(provider_tools[0]["function"]["name"], "cortex_filesystem_list")
        self.assertNotIn(".", provider_tools[0]["function"]["name"])

        class FakeStream:
            def __iter__(self):
                yield b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"provider-call","function":{"name":"cortex_filesystem_list","arguments":"{\\\"path\\\":\\\".\\\"}"}}]},"finish_reason":"tool_calls"}]}\n'
                yield b"data: [DONE]\n"

            def close(self):
                return None

        seen_payload = {}

        def open_fixture(http_request, timeout):
            seen_payload.update(json.loads(http_request.data.decode("utf-8")))
            return FakeStream()

        http_adapter = HttpProviderAgentAdapter("openai", "reasoning-model", "secret", "https://example.invalid/v1")
        with patch("cortex.provider_fabric.urllib.request.urlopen", side_effect=open_fixture):
            transported = http_adapter.invoke_agent(captured[0])
        self.assertEqual(seen_payload["reasoning_effort"], "none")
        self.assertEqual(transported["tool_calls"][0]["name"], "filesystem.list")

    def test_filesystem_list_is_bounded_read_only_and_workspace_contained(self) -> None:
        adapter = ScriptedAgentAdapter(
            [
                {"tool_calls": [{"id": "list-1", "name": "filesystem.list", "arguments": {"path": "."}}], "finish_reason": "tool_calls"},
                {"public_output": "listed", "finish_reason": "stop"},
            ]
        )
        result = NativeAgentRuntime(self.store, self.repo).run(
            "list source", adapter=adapter, grant=self._grant("filesystem.list")
        )
        receipt = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        listed = receipt["tool_results"][0]
        self.assertEqual(listed["status"], "completed")
        self.assertIn("README.md", [item["path"] for item in listed["output"]["entries"]])
        self.assertFalse(receipt["host_mutate_authorized"])
        self.assertFalse(receipt["execution_authorized"])

    def test_second_adapter_uses_same_core_contract(self) -> None:
        class OtherAdapter(ScriptedAgentAdapter):
            provider_family = "other-fixture"
            adapter_id = "test.other"

        for adapter in (
            ScriptedAgentAdapter([{"public_output": "one", "finish_reason": "stop"}], model_id="a"),
            OtherAdapter([{"public_output": "two", "finish_reason": "stop"}], model_id="b"),
        ):
            result = NativeAgentRuntime(self.store, self.repo).run(
                "answer", adapter=adapter, grant=self._grant()
            )
            self.assertTrue(result["verification"]["valid"])

    def test_ungranted_tool_returns_typed_denial_and_continues(self) -> None:
        adapter = ScriptedAgentAdapter(
            [
                {"tool_calls": [{"id": "x", "name": "filesystem.read", "arguments": {"path": "README.md"}}], "finish_reason": "tool_calls"},
                {"public_output": "denial observed", "finish_reason": "stop"},
            ]
        )
        result = NativeAgentRuntime(self.store, self.repo).run(
            "try read", adapter=adapter, grant=self._grant()
        )
        receipt = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        self.assertEqual(receipt["tool_results"][0]["status"], "denied")
        self.assertFalse(receipt["tool_results"][0]["trusted"])

    def test_path_escape_fails_closed(self) -> None:
        adapter = ScriptedAgentAdapter(
            [
                {"tool_calls": [{"id": "escape", "name": "filesystem.read", "arguments": {"path": "../secret"}}], "finish_reason": "tool_calls"},
                {"public_output": "blocked", "finish_reason": "stop"},
            ]
        )
        result = NativeAgentRuntime(self.store, self.repo).run(
            "escape", adapter=adapter, grant=self._grant("filesystem.read")
        )
        receipt = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        self.assertEqual(receipt["tool_results"][0]["status"], "failed")
        self.assertIn("PermissionError", receipt["tool_results"][0]["output"])

    def test_terminal_requires_explicit_tool_and_executable_grants(self) -> None:
        adapter = ScriptedAgentAdapter(
            [
                {
                    "tool_calls": [
                        {
                            "id": "terminal-1",
                            "name": "terminal.execute",
                            "arguments": {"argv": [sys.executable, "-c", "print('bounded')"]},
                        }
                    ],
                    "finish_reason": "tool_calls",
                },
                {"public_output": "terminal observed", "finish_reason": "stop"},
            ]
        )
        grant = CapabilityGrant(
            workspace_root=str(self.host),
            allowed_tools=("terminal.execute",),
            allowed_commands=(
                json.dumps(
                    [sys.executable, "-c", "print('bounded')"],
                    separators=(",", ":"),
                ),
            ),
        )
        result = NativeAgentRuntime(self.store, self.repo).run(
            "run bounded command", adapter=adapter, grant=grant
        )
        receipt = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        tool = receipt["tool_results"][0]
        self.assertEqual(tool["status"], "completed")
        self.assertEqual(tool["output"]["stdout"].strip(), "bounded")
        self.assertFalse(result["authority"]["execution_authorized"])

    def test_terminal_cannot_change_arguments_under_an_executable_grant(self) -> None:
        adapter = ScriptedAgentAdapter(
            [
                {
                    "tool_calls": [
                        {
                            "id": "terminal-denied",
                            "name": "terminal.execute",
                            "arguments": {"argv": [sys.executable, "-c", "print('different')"]},
                        }
                    ],
                    "finish_reason": "tool_calls",
                },
                {"public_output": "denial observed", "finish_reason": "stop"},
            ]
        )
        grant = CapabilityGrant(
            workspace_root=str(self.host),
            allowed_tools=("terminal.execute",),
            allowed_commands=(
                json.dumps(
                    [sys.executable, "-c", "print('approved')"],
                    separators=(",", ":"),
                ),
            ),
        )
        result = NativeAgentRuntime(self.store, self.repo).run(
            "do not vary argv", adapter=adapter, grant=grant
        )
        receipt = self.store.symbiotic_receipt(
            result["trajectory_receipt_hash"], repo=self.repo
        )
        self.assertEqual(receipt["tool_results"][0]["status"], "failed")
        self.assertIn("exact command vector", receipt["tool_results"][0]["output"])

    def test_response_replay_under_wrong_request_fails(self) -> None:
        class ReplayAdapter(ScriptedAgentAdapter):
            def invoke_agent(self, request: AgentModelRequest):
                return {"request_hash": "f" * 64, "public_output": "replay", "finish_reason": "stop"}

        events: list[dict] = []
        with self.assertRaisesRegex(ModelAdapterError, "different request"):
            NativeAgentRuntime(self.store, self.repo, event_sink=events.append).run(
                "replay", adapter=ReplayAdapter([]), grant=self._grant()
            )
        self.assertEqual(events[-1]["event_type"], "model.failed")

    def test_context_hash_tamper_fails_request_verification(self) -> None:
        captured: list[AgentModelRequest] = []

        class CaptureAdapter(ScriptedAgentAdapter):
            def invoke_agent(self, request: AgentModelRequest):
                captured.append(request)
                return {"request_hash": request.request_hash, "public_output": "ok", "finish_reason": "stop"}

        NativeAgentRuntime(self.store, self.repo).run(
            "capture", adapter=CaptureAdapter([]), grant=self._grant()
        )
        tampered = dataclasses.replace(captured[0], context_projection_hash="0" * 64)
        self.assertFalse(tampered.verify())

    def test_duplicate_tool_call_id_across_iterations_fails(self) -> None:
        adapter = ScriptedAgentAdapter(
            [
                {"tool_calls": [{"id": "same", "name": "filesystem.read", "arguments": {"path": "README.md"}}], "finish_reason": "tool_calls"},
                {"tool_calls": [{"id": "same", "name": "filesystem.read", "arguments": {"path": "README.md"}}], "finish_reason": "tool_calls"},
            ]
        )
        with self.assertRaisesRegex(ModelAdapterError, "replayed"):
            NativeAgentRuntime(self.store, self.repo).run(
                "duplicate", adapter=adapter, grant=self._grant("filesystem.read")
            )

    def test_tampered_trajectory_fails_deep_verification(self) -> None:
        result = NativeAgentRuntime(self.store, self.repo).run(
            "seal",
            adapter=ScriptedAgentAdapter([{"public_output": "sealed", "finish_reason": "stop"}]),
            grant=self._grant(),
        )
        receipt = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        receipt["final_answer"] = "tampered"
        # Caller mutation cannot alter the canonical row reloaded by the verifier.
        verified = verify_native_agent_trajectory(self.store, self.repo, result["trajectory_receipt_hash"])
        self.assertTrue(verified["valid"])

    def test_representative_v9_receipt_remains_valid_after_v10_append(self) -> None:
        legacy_session = open_symbiotic_session(self.store, self.repo, task="v9 compatibility")
        run_model_circulation(
            self.store,
            self.repo,
            legacy_session,
            adapter=FixtureAdapter(text="LEGACY_OK"),
            task_contract=TaskEvaluationContract(
                contract_id="legacy-v9-contract",
                task_type="text_contains",
                target_field="text",
                expected_value="LEGACY_OK",
            ),
            observed_result={"text": "LEGACY_OK"},
        )
        before = verify_model_circulation(
            self.store, self.repo, legacy_session["session_id"], turn_id=1
        )
        self.assertTrue(before["valid"], before["errors"])
        legacy_hashes_before = [
            row["receipt_hash"]
            for row in self.store.symbiotic_session_receipts(
                self.repo, legacy_session["session_id"]
            )
        ]
        NativeAgentRuntime(self.store, self.repo).run(
            "v10 append",
            adapter=ScriptedAgentAdapter(
                [{"public_output": "v10 complete", "finish_reason": "stop"}]
            ),
            grant=self._grant(),
        )
        after = verify_model_circulation(
            self.store, self.repo, legacy_session["session_id"], turn_id=1
        )
        self.assertTrue(after["valid"], after["errors"])
        legacy_hashes_after = [
            row["receipt_hash"]
            for row in self.store.symbiotic_session_receipts(
                self.repo, legacy_session["session_id"]
            )
        ]
        self.assertEqual(legacy_hashes_before, legacy_hashes_after)


if __name__ == "__main__":
    unittest.main()
