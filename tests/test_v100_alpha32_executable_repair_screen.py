"""Alpha.32 frozen executable repair live-screen tests."""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.executable_repair_forge import build_executable_repair_bundle
from cortex.executable_repair_screen import (
    execute_executable_repair_screen,
    freeze_executable_repair_screen,
    verify_executable_repair_screen,
)
from cortex.native_agent import CapabilityGrant, ToolRegistry
from cortex.store import Store
from cortex.will import register_will_principal


def _unit_specs():
    return [
        {
            "case_id": f"screen_{index}",
            "task": "Return the declared fixture value.",
            "source": "def value():\n    return 0\n",
            "test": "from module import value\nassert value() == 1\n",
            "patch": "diff --git a/module.py b/module.py\n--- a/module.py\n+++ b/module.py\n@@ -1,2 +1,2 @@\n def value():\n-    return 0\n+    return 1\n",
        }
        for index in range(4)
    ]


class ExternalRepairAdapter:
    provider_family = "external-repair-provider"
    model_id = "frontier-repair-model"
    model_version = "2026-09"
    adapter_id = "tests.external-repair-adapter"
    adapter_version = "1"

    def __init__(self, answers):
        self.answers = list(answers)

    def invoke_agent(self, request):
        return {
            "request_hash": request.request_hash,
            "public_output": self.answers.pop(0),
            "finish_reason": "stop",
            "token_usage": {"input_tokens": 10, "output_tokens": 10},
        }


class Alpha32ExecutableRepairScreenTests(unittest.TestCase):
    def _fixture(self, temp: str, *, valid_answers: bool = True):
        root = Path(temp)
        home = ensure_home(root / "home")
        host = root / "host"
        host.mkdir()
        (host / "README.md").write_text("alpha32\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        repo = "Alpha32Host"
        bootstrap_repository(home, store, host, repo)
        public, private = build_executable_repair_bundle(
            secret_seed="alpha32-test-secret", case_specs=_unit_specs()
        )
        answers = [case["reference_patch"] for case in private["cases"]] if valid_answers else ["no patch"] * 4
        adapter = ExternalRepairAdapter(answers)
        register_will_principal(store, repo, "alpha32-operator", "Alpha.32 test operator", secret="alpha32-secret")
        register_adapter_provenance(
            store, repo, adapter, boundary_kind="external_api",
            principal_id="alpha32-operator", principal_secret="alpha32-secret",
            endpoint_descriptor={"transport": "test_external_boundary"},
            model_family="frontier-repair-family", capability_class="code_repair",
        )
        forge = {"state": "EXECUTABLE_REPAIR_FORGE_READY", "result_hash": "a" * 64, "corpus_hash": public["corpus_hash"], "public_corpus": public}
        return store, repo, host, forge, private, adapter

    def _run(self, fixture):
        store, repo, host, forge, private, adapter = fixture
        prereg = freeze_executable_repair_screen(store, repo, forge_artifact=forge, private_bundle=private, adapter=adapter)
        grant = CapabilityGrant(
            workspace_root=str(host), allowed_tools=(), principal_id="alpha32-test",
            purpose="four-call executable screen", issued_at=time.time(), expires_at=time.time() + 120,
            max_tool_calls=0, max_total_tool_seconds=0.0,
        )
        result = execute_executable_repair_screen(
            store, repo, preregistration=prereg, private_bundle=private,
            adapter=adapter, tools=ToolRegistry(), grant=grant,
        )
        return prereg, result

    def test_reference_outputs_produce_reconstructed_ceiling_without_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp)
            store, repo, _, _, _, _ = fixture
            try:
                prereg, result = self._run(fixture)
                self.assertEqual(prereg["planned_calls"], 4)
                self.assertEqual(prereg["tools"], [])
                self.assertEqual(result["screen"]["success_count"], 4)
                self.assertEqual(result["screen"]["state"], "screening_ceiling")
                self.assertFalse(result["semantic_transfer_established"])
                audit = verify_executable_repair_screen(store, repo, result_receipt_hash=result["receipt_hash"])
                self.assertTrue(audit["valid"], audit["errors"])
            finally:
                store.close()

    def test_malformed_model_outputs_are_measured_failures_not_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp, valid_answers=False)
            store, repo, _, _, _, _ = fixture
            try:
                _, result = self._run(fixture)
                self.assertEqual(result["screen"]["success_count"], 0)
                self.assertEqual(result["screen"]["state"], "screening_floor")
                self.assertTrue(verify_executable_repair_screen(store, repo, result_receipt_hash=result["receipt_hash"])["valid"])
                for field in ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"):
                    self.assertFalse(result[field])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
