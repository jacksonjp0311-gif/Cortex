"""v10.0-alpha.6 governed tool-fabric adversarial tests."""

from __future__ import annotations

import dataclasses
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.chat_service import CortexChatService
from cortex.config import ensure_home
from cortex.native_agent import (
    AgentToolCall,
    CapabilityGrant,
    NativeAgentRuntime,
    ScriptedAgentAdapter,
    ToolRegistry,
    verify_native_agent_trajectory,
)
from cortex.store import Store
from cortex.tool_fabric import ToolCatalog, ToolManifest, verify_execution_receipt


class V100Alpha6ToolFabricTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("TOOL_FABRIC_TOKEN\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "ToolFabricHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _grant(self, *tools: str, **values) -> CapabilityGrant:
        return CapabilityGrant(workspace_root=str(self.host), allowed_tools=tools, **values)

    def test_manifest_identity_is_content_addressed_and_registration_is_host_owned(self) -> None:
        registry = ToolRegistry()
        original = registry.catalog.resolve("filesystem.read")
        self.assertIsNotNone(original)
        clone = ToolManifest.from_descriptor(original.descriptor())
        self.assertEqual(clone.manifest_hash, original.manifest_hash)
        changed = dataclasses.replace(original, version="2.0")
        self.assertNotEqual(changed.manifest_hash, original.manifest_hash)
        with self.assertRaisesRegex(ValueError, "different manifest content"):
            registry.catalog.register(changed)

    def test_unknown_tool_and_caller_approval_boolean_cannot_open_authority(self) -> None:
        registry = ToolRegistry()
        call = AgentToolCall("unknown-1", "model.registered.tool", {"approved": True})
        receipt = registry.execute(call, self._grant("model.registered.tool"))
        self.assertEqual(receipt["status"], "denied")
        self.assertEqual(receipt["manifest_hash"], "")
        self.assertFalse(receipt["execution_authorized"])
        self.assertFalse(receipt["host_mutate_authorized"])

    def test_schema_rejects_unknown_boolean_shaped_approval(self) -> None:
        call = AgentToolCall(
            "read-unknown",
            "filesystem.read",
            {"path": "README.md", "verified": True},
        )
        receipt = ToolRegistry().execute(call, self._grant("filesystem.read"))
        self.assertEqual(receipt["status"], "denied")
        self.assertIn("argument_unknown:verified", receipt["output"]["argument_errors"])

    def test_inactive_grant_blocks_before_provider_invocation(self) -> None:
        called = []

        class NeverAdapter(ScriptedAgentAdapter):
            def invoke_agent(self, request):
                called.append(request)
                return super().invoke_agent(request)

        with self.assertRaisesRegex(Exception, "grant_expired"):
            NativeAgentRuntime(self.store, self.repo).run(
                "blocked",
                adapter=NeverAdapter([{"public_output": "must not run", "finish_reason": "stop"}]),
                grant=self._grant(expires_at=time.time() - 1),
            )
        self.assertEqual(called, [])

    def test_execution_receipt_binds_manifest_grant_arguments_output_and_trajectory(self) -> None:
        argv = [sys.executable, "-c", "print('receipt-bound')"]
        grant = self._grant(
            "terminal.execute",
            allowed_commands=(json.dumps(argv, separators=(",", ":")),),
        )
        adapter = ScriptedAgentAdapter([
            {"tool_calls": [{"id": "exec-1", "name": "terminal.execute", "arguments": {"argv": argv}}], "finish_reason": "tool_calls"},
            {"public_output": "observed", "finish_reason": "stop"},
        ])
        result = NativeAgentRuntime(self.store, self.repo).run("execute", adapter=adapter, grant=grant)
        receipt = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        execution = receipt["tool_results"][0]
        catalog = ToolCatalog(tuple(ToolManifest.from_descriptor(item) for item in receipt["tool_manifests"]))
        verified = verify_execution_receipt(execution, catalog, receipt["capability_grant"])
        self.assertTrue(verified["valid"], verified)
        self.assertEqual(execution["output"]["stdout"].strip(), "receipt-bound")
        self.assertTrue(verify_native_agent_trajectory(self.store, self.repo, result["trajectory_receipt_hash"])["valid"])

    def test_tampered_execution_body_fails_hash_verification(self) -> None:
        registry = ToolRegistry()
        grant = self._grant("filesystem.read")
        receipt = registry.execute(AgentToolCall("read-1", "filesystem.read", {"path": "README.md"}), grant)
        receipt["output"]["text"] = "tampered"
        verified = verify_execution_receipt(receipt, registry.catalog, grant.material())
        self.assertFalse(verified["valid"])
        self.assertIn("execution_hash_invalid", verified["errors"])
        self.assertIn("output_hash_invalid", verified["errors"])

    def test_tool_budget_denies_second_request_without_widening_grant(self) -> None:
        adapter = ScriptedAgentAdapter([
            {"tool_calls": [{"id": "one", "name": "filesystem.read", "arguments": {"path": "README.md"}}], "finish_reason": "tool_calls"},
            {"tool_calls": [{"id": "two", "name": "filesystem.read", "arguments": {"path": "README.md"}}], "finish_reason": "tool_calls"},
            {"public_output": "budget observed", "finish_reason": "stop"},
        ])
        result = NativeAgentRuntime(self.store, self.repo).run(
            "bounded reads", adapter=adapter, grant=self._grant("filesystem.read", max_tool_calls=1)
        )
        trajectory = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        self.assertEqual([item["status"] for item in trajectory["tool_results"]], ["completed", "denied"])
        self.assertEqual(trajectory["tool_results"][1]["output"], "tool_call_budget_exhausted")
        self.assertTrue(result["verification"]["valid"], result["verification"])

    def test_terminal_cancellation_stops_process_and_emits_cancelled_receipt(self) -> None:
        argv = [sys.executable, "-c", "import time; time.sleep(10)"]
        grant = self._grant(
            "terminal.execute",
            allowed_commands=(json.dumps(argv, separators=(",", ":")),),
            max_command_seconds=20,
        )
        cancel = threading.Event()
        timer = threading.Timer(0.15, cancel.set)
        timer.start()
        started = time.monotonic()
        try:
            receipt = ToolRegistry().execute(
                AgentToolCall("cancel-1", "terminal.execute", {"argv": argv}), grant, cancel
            )
        finally:
            timer.cancel()
        self.assertEqual(receipt["status"], "cancelled")
        self.assertLess(time.monotonic() - started, 3.0)
        self.assertFalse(receipt["execution_authorized"])

    def test_service_catalog_is_truthful_and_non_authorizing(self) -> None:
        surface = CortexChatService(self.store, self.repo).tools()
        self.assertEqual(surface["registration_authority"], "host_only")
        self.assertFalse(surface["model_registration_authorized"])
        self.assertFalse(surface["execution_authorized"])
        self.assertEqual({item["tool_id"] for item in surface["tools"]}, {
            "filesystem.list", "filesystem.read", "terminal.execute", "workspace.propose_patch",
        })
        self.assertTrue(all(item["manifest_hash"] for item in surface["tools"]))


if __name__ == "__main__":
    unittest.main()
