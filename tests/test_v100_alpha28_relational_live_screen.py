from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.intermediate_relational_forge import (
    build_intermediate_relational_bundle,
    freeze_intermediate_relational_forge,
)
from cortex.native_agent import CapabilityGrant, ToolRegistry
from cortex.open_response_calibration import build_open_response_latent_bundle
from cortex.relational_causal_evaluator import build_relational_evaluator_bundle
from cortex.relational_live_screen import (
    execute_bridge_low_screen,
    freeze_bridge_low_screen,
    verify_bridge_low_screen,
)
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


class ExternalRelationalAdapter:
    __slots__ = ("answers",)

    provider_family = "external-relational-provider"
    model_id = "relational-frontier-model"
    model_version = "2026-09"
    adapter_id = "tests.external-relational-adapter"
    adapter_version = "1"

    def __init__(self, answers):
        self.answers = list(answers)

    def invoke_agent(self, request):
        return {
            "request_hash": request.request_hash,
            "public_output": self.answers.pop(0),
            "finish_reason": "stop",
            "token_usage": {"input_tokens": 1, "output_tokens": 1},
        }


class Alpha28RelationalLiveScreenTests(unittest.TestCase):
    def test_four_call_screen_is_frozen_executed_and_reconstructed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = ensure_home(root / "home")
            host = root / "host"
            host.mkdir()
            (host / "README.md").write_text("alpha28\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            try:
                repo = "Alpha28Host"
                bootstrap_repository(home, store, host, repo)
                source = build_open_response_latent_bundle(secret_seed="alpha28-source")
                evaluator_bundle = build_relational_evaluator_bundle(source["manifest"])
                corpus_bundle = build_intermediate_relational_bundle(
                    secret_seed="alpha28-corpus"
                )
                session = open_symbiotic_session(
                    store, repo, task="alpha28 evaluator prerequisite", persist=True
                )
                evaluator_preflight = store.append_symbiotic_receipt(
                    repo,
                    {
                        "schema_version": "cortex-relational-causal-preflight/3.0",
                        "kind": "relational_causal_evaluator_preflight",
                        "state": "RELATIONAL_CAUSAL_EVALUATOR_V3_READY",
                        "planned_live_calls": 0,
                        "historical_scores_rewritten": False,
                        "difficulty_interpolation_ready": True,
                        "evaluator_manifest": evaluator_bundle["manifest"],
                        "session_id": session["session_id"],
                        "turn_id": 0,
                        "event_id": "alpha28_evaluator_preflight",
                        "body_epoch_id": session["body_epoch_id"],
                    },
                )
                forge = freeze_intermediate_relational_forge(
                    store,
                    repo,
                    relational_preflight_receipt_hash=evaluator_preflight["receipt_hash"],
                    bundle=corpus_bundle,
                )
                contracts = corpus_bundle["private_key"]["contracts"]
                answers = [
                    json.dumps(
                        contracts[case_id]["reference_response"]
                    )
                    for case_id in corpus_bundle["manifest"]["band_case_ids"]["bridge_low"]
                ]
                adapter = ExternalRelationalAdapter(answers)
                register_will_principal(
                    store,
                    repo,
                    "alpha28-operator",
                    "Alpha.28 test operator",
                    secret="alpha28-principal-secret",
                )
                register_adapter_provenance(
                    store,
                    repo,
                    adapter,
                    boundary_kind="external_api",
                    principal_id="alpha28-operator",
                    principal_secret="alpha28-principal-secret",
                    endpoint_descriptor={"transport": "test_external_boundary"},
                    model_family="relational-frontier-family",
                    capability_class="general_reasoning",
                )
                prereg = freeze_bridge_low_screen(
                    store,
                    repo,
                    forge_preflight_receipt_hash=forge["receipt_hash"],
                    corpus_bundle=corpus_bundle,
                    evaluator_bundle=evaluator_bundle,
                    adapter=adapter,
                )
                self.assertEqual(prereg["planned_calls"], 4)
                self.assertEqual(prereg["difficulty_band"], "bridge_low")
                self.assertFalse(prereg["execution_authorized"])
                grant = CapabilityGrant(
                    workspace_root=str(host),
                    allowed_tools=(),
                    principal_id="alpha28-test",
                    purpose="bounded relational screen",
                    issued_at=time.time(),
                    expires_at=time.time() + 60,
                    max_tool_calls=0,
                    max_total_tool_seconds=0.0,
                )
                result = execute_bridge_low_screen(
                    store,
                    repo,
                    preregistration=prereg,
                    corpus_bundle=corpus_bundle,
                    adapter=adapter,
                    tools=ToolRegistry(),
                    grant=grant,
                )
                self.assertEqual(result["calls_executed"], 4)
                self.assertEqual(result["screen"]["state"], "screening_ceiling")
                self.assertFalse(result["semantic_transfer_established"])
                audit = verify_bridge_low_screen(
                    store,
                    repo,
                    result_receipt_hash=result["receipt_hash"],
                    corpus_bundle=corpus_bundle,
                )
                self.assertTrue(audit["valid"], audit["errors"])
                caller_copy = dict(result, screen={"state": "calibrated"})
                self.assertTrue(
                    verify_bridge_low_screen(
                        store,
                        repo,
                        result_receipt_hash=caller_copy["receipt_hash"],
                        corpus_bundle=corpus_bundle,
                    )["valid"]
                )
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
