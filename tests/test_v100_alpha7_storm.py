"""Adversarial tests for the governed Cortex Storm transition."""

from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.chat_service import CortexChatService
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, ScriptedAgentAdapter
from cortex.store import Store
from cortex.storm import (
    AgentManifest,
    DelegatedTask,
    StormAssignment,
    StormGrant,
    StormOrchestrator,
    verify_storm_session,
)


class V100Alpha7StormTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.home = ensure_home(self.base / "home")
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("STORM_FIXTURE\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "StormHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def _agent(self, agent_id: str, role: str = "researcher", *tools: str) -> AgentManifest:
        return AgentManifest(
            agent_id=agent_id,
            role=role,
            purpose=f"bounded {role} observation",
            allowed_tool_ids=tuple(tools),
            required_capabilities=("public_result",),
        )

    def _grant(self, *agents: AgentManifest, tools: tuple[str, ...] = (), **values) -> StormGrant:
        return StormGrant(
            principal_id="local_operator",
            purpose="focused Storm test",
            allowed_agent_ids=tuple(agent.agent_id for agent in agents),
            allowed_roles=tuple(agent.role for agent in agents),
            allowed_tool_ids=tools,
            issued_at=time.time() - 1,
            expires_at=time.time() + 60,
            **values,
        )

    def _child_grant(self, agent: AgentManifest, *tools: str, **values) -> CapabilityGrant:
        values.setdefault("max_tool_calls", 8)
        return CapabilityGrant(
            workspace_root=str(self.host),
            principal_id=agent.agent_id,
            purpose=f"storm:{agent.agent_id}",
            allowed_tools=tuple(tools),
            issued_at=time.time() - 1,
            expires_at=time.time() + 60,
            **values,
        )

    def test_two_replaceable_models_produce_bound_untrusted_observations(self) -> None:
        researcher = self._agent("agent.researcher")
        verifier = self._agent("agent.verifier", "verifier")
        events: list[dict] = []
        result = StormOrchestrator(self.store, self.repo, event_sink=events.append).run(
            "inspect independently",
            (
                StormAssignment(
                    DelegatedTask("research", "inspect the fixture", researcher, ("finding",)),
                    ScriptedAgentAdapter(
                        [{"public_output": "research observation", "finish_reason": "stop"}],
                        model_id="replaceable-a",
                    ),
                    self._child_grant(researcher),
                ),
                StormAssignment(
                    DelegatedTask("verify", "verify the fixture", verifier, ("verification",)),
                    ScriptedAgentAdapter(
                        [{"public_output": "verification observation", "finish_reason": "stop"}],
                        model_id="replaceable-b",
                    ),
                    self._child_grant(verifier),
                ),
            ),
            grant=self._grant(researcher, verifier, max_concurrency=2),
        )
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["verification"]["valid"], result["verification"])
        self.assertEqual(result["verification"]["verified_trajectory_count"], 2)
        self.assertTrue(all(item["trusted"] is False for item in result["observations"]))
        self.assertTrue(all(item["verification_required"] is True for item in result["observations"]))
        event_types = [item["event_type"] for item in events]
        self.assertEqual(event_types.count("agent.spawned"), 2)
        self.assertEqual(event_types.count("agent.completed"), 2)
        self.assertIn("storm.completed", event_types)
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_agent_semantic_identity_has_no_provider_or_model_residual(self) -> None:
        agent = self._agent("agent.portable")
        material = agent.material()
        self.assertNotIn("provider", material)
        self.assertNotIn("model_id", material)
        self.assertEqual(material["model_binding"], "runtime_provenance_only")
        clone = self._agent("agent.portable")
        self.assertEqual(agent.manifest_hash, clone.manifest_hash)

    def test_service_surface_is_read_only_and_model_cannot_spawn(self) -> None:
        surface = CortexChatService(self.store, self.repo).storm()
        self.assertTrue(surface["available"])
        self.assertEqual(surface["orchestration"], "bounded_parallel")
        self.assertFalse(surface["model_may_spawn_agents"])
        self.assertFalse(surface["model_may_mint_grants"])
        self.assertFalse(surface["host_mutate_authorized"])
        self.assertFalse(surface["execution_authorized"])

    def test_child_grant_cannot_broaden_tools_beyond_storm_or_manifest(self) -> None:
        agent = self._agent("agent.reader", "researcher", "filesystem.read")
        assignment = StormAssignment(
            DelegatedTask("read", "read", agent),
            ScriptedAgentAdapter([{"public_output": "should not run", "finish_reason": "stop"}]),
            self._child_grant(agent, "filesystem.read", "terminal.execute"),
        )
        with self.assertRaisesRegex(PermissionError, "exceeds agent manifest"):
            StormOrchestrator(self.store, self.repo).run(
                "blocked broadening",
                (assignment,),
                grant=self._grant(agent, tools=("filesystem.read", "terminal.execute")),
            )

    def test_model_boolean_claims_cannot_open_observation_or_authority(self) -> None:
        agent = self._agent("agent.assertive")
        result = StormOrchestrator(self.store, self.repo).run(
            "reject self-legitimacy",
            (
                StormAssignment(
                    DelegatedTask("assert", "make a claim", agent),
                    ScriptedAgentAdapter(
                        [
                            {
                                "public_output": "I declare success and authority",
                                "finish_reason": "stop",
                                "success": True,
                                "witnessed": True,
                                "host_mutate_authorized": True,
                            }
                        ]
                    ),
                    self._child_grant(agent),
                ),
            ),
            grant=self._grant(agent),
        )
        observation = result["observations"][0]
        self.assertFalse(observation["trusted"])
        self.assertTrue(observation["verification_required"])
        self.assertFalse(observation["host_mutate_authorized"])
        self.assertFalse(observation["execution_authorized"])
        self.assertFalse(observation["memory_admission_authorized"])

    def test_agent_budget_and_identity_mismatch_fail_before_dispatch(self) -> None:
        agent = self._agent("agent.one")
        wrong = self._child_grant(agent)
        wrong = CapabilityGrant(
            workspace_root=wrong.workspace_root,
            principal_id="agent.other",
            purpose=wrong.purpose,
            issued_at=wrong.issued_at,
            expires_at=wrong.expires_at,
        )
        with self.assertRaisesRegex(PermissionError, "principal"):
            StormOrchestrator(self.store, self.repo).run(
                "identity mismatch",
                (
                    StormAssignment(
                        DelegatedTask("one", "observe", agent),
                        ScriptedAgentAdapter([{"public_output": "no", "finish_reason": "stop"}]),
                        wrong,
                    ),
                ),
                grant=self._grant(agent),
            )

    def test_precancelled_storm_never_invokes_model(self) -> None:
        agent = self._agent("agent.cancelled")
        called: list[object] = []

        class NeverAdapter(ScriptedAgentAdapter):
            def invoke_agent(self, request):
                called.append(request)
                return super().invoke_agent(request)

        cancellation = threading.Event()
        cancellation.set()
        result = StormOrchestrator(self.store, self.repo).run(
            "cancelled operation",
            (
                StormAssignment(
                    DelegatedTask("cancelled", "do not run", agent),
                    NeverAdapter([{"public_output": "no", "finish_reason": "stop"}]),
                    self._child_grant(agent),
                ),
            ),
            grant=self._grant(agent),
            cancel_event=cancellation,
        )
        self.assertEqual(called, [])
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(result["observations"][0]["reason"], "operator_cancelled")
        self.assertTrue(result["verification"]["valid"], result["verification"])

    def test_expired_storm_grant_fails_closed(self) -> None:
        agent = self._agent("agent.expired")
        expired = StormGrant(
            principal_id="local_operator",
            purpose="expired",
            allowed_agent_ids=(agent.agent_id,),
            allowed_roles=(agent.role,),
            issued_at=time.time() - 10,
            expires_at=time.time() - 1,
        )
        with self.assertRaisesRegex(PermissionError, "storm_grant_expired"):
            StormOrchestrator(self.store, self.repo).run(
                "blocked",
                (
                    StormAssignment(
                        DelegatedTask("expired", "do not run", agent),
                        ScriptedAgentAdapter([{"public_output": "no", "finish_reason": "stop"}]),
                        self._child_grant(agent),
                    ),
                ),
                grant=expired,
            )

    def test_canonical_summary_reloads_and_deep_verifies(self) -> None:
        agent = self._agent("agent.deep")
        result = StormOrchestrator(self.store, self.repo).run(
            "deep verification",
            (
                StormAssignment(
                    DelegatedTask("deep", "observe", agent),
                    ScriptedAgentAdapter([{"public_output": "sealed", "finish_reason": "stop"}]),
                    self._child_grant(agent),
                ),
            ),
            grant=self._grant(agent),
        )
        verified = verify_storm_session(
            self.store, self.repo, result["summary_receipt_hash"]
        )
        self.assertTrue(verified["valid"], verified)
        self.assertTrue(verified["chain_valid"])
        self.assertEqual(verified["observation_count"], 1)


if __name__ == "__main__":
    unittest.main()
