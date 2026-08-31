from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, ScriptedAgentAdapter, ToolRegistry
from cortex.semantic_calibration import (
    build_semantic_calibration_bundle,
    build_semantic_calibration_preflight,
    execute_live_calibration_screen,
    freeze_live_calibration_screen,
)
from cortex.source_experience import forge_structural_source_experience_pair
from cortex.store import Store
from cortex.will import register_will_principal


class ExternalScreenAdapter:
    provider_family = "external-test-provider"
    model_id = "frontier-test-model"
    model_version = "2026-08"
    adapter_id = "tests.external-screen-adapter"
    adapter_version = "1"

    def __init__(self) -> None:
        self._answers = iter(("A", "B", "C", "D"))

    def invoke_agent(self, request):
        return {
            "request_hash": request.request_hash,
            "public_output": next(self._answers),
            "finish_reason": "stop",
            "token_usage": {"input_tokens": 1, "output_tokens": 1},
        }


class Alpha18LiveSemanticCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.home = ensure_home(root / "home")
        self.host = root / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("alpha18\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        self.repo = "Alpha18Host"
        bootstrap_repository(self.home, self.store, self.host, self.repo)
        self.bundle = build_semantic_calibration_bundle(secret_seed="alpha18-test-seed")
        pair = forge_structural_source_experience_pair(self.store, self.repo)
        self.preflight = build_semantic_calibration_preflight(pair, self.bundle)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_fixture_cannot_freeze_live_screen(self) -> None:
        fixture = ScriptedAgentAdapter(
            [{"public_output": "A", "finish_reason": "stop"}] * 4,
            model_id="renamed-frontier-model",
        )
        with self.assertRaisesRegex(ValueError, "live host-registered"):
            freeze_live_calibration_screen(
                self.store,
                self.repo,
                preflight=self.preflight,
                bundle=self.bundle,
                adapter=fixture,
            )

    def test_registered_external_screen_is_reconstructed_from_four_trajectories(self) -> None:
        adapter = ExternalScreenAdapter()
        register_will_principal(
            self.store,
            self.repo,
            "alpha18-operator",
            "Alpha.18 test operator",
            secret="alpha18-principal-secret",
        )
        register_adapter_provenance(
            self.store,
            self.repo,
            adapter,
            boundary_kind="external_api",
            principal_id="alpha18-operator",
            principal_secret="alpha18-principal-secret",
            endpoint_descriptor={"transport": "test_external_boundary"},
            model_family="frontier-test-family",
            capability_class="general_reasoning",
        )
        preregistration = freeze_live_calibration_screen(
            self.store,
            self.repo,
            preflight=self.preflight,
            bundle=self.bundle,
            adapter=adapter,
        )
        grant = CapabilityGrant(
            workspace_root=str(self.host),
            allowed_tools=(),
            principal_id="alpha18-test",
            purpose="bounded four-call screen",
            issued_at=time.time(),
            expires_at=time.time() + 60,
            max_tool_calls=0,
            max_total_tool_seconds=0.0,
        )
        result = execute_live_calibration_screen(
            self.store,
            self.repo,
            preregistration=preregistration,
            bundle=self.bundle,
            adapter=adapter,
            tools=ToolRegistry(),
            grant=grant,
        )
        self.assertEqual(result["calls_executed"], 4)
        self.assertEqual(result["screen"]["state"], "screening_ceiling")
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["calibration_established"])
        self.assertFalse(result["semantic_transfer_established"])
        self.assertFalse(result["host_mutate_authorized"])
        self.assertFalse(result["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
