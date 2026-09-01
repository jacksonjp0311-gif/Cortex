from __future__ import annotations

import copy
import json
import tempfile
import time
import unittest
from pathlib import Path

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, ToolRegistry
from cortex.open_response_calibration import build_open_response_latent_bundle
from cortex.semantic_causal_evaluator import (
    audit_harder_live_semantic_screen_v2,
    build_semantic_evaluator_bundle,
    evaluate_semantic_causal_response,
    execute_live_semantic_screen_v2,
    freeze_harder_live_semantic_screen_v2,
    freeze_live_semantic_screen_v2,
    semantic_evaluator_self_test,
    verify_live_semantic_screen_v2,
    verify_semantic_evaluator_bundle,
)
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


class ExternalSemanticAdapter:
    __slots__ = ("answers",)

    provider_family = "external-semantic-provider"
    model_id = "semantic-frontier-model"
    model_version = "2026-08"
    adapter_id = "tests.external-semantic-adapter"
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


class Alpha22SemanticCausalEvaluatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = build_open_response_latent_bundle(secret_seed="alpha22-test-seed")
        self.bundle = build_semantic_evaluator_bundle(
            self.source["manifest"], self.source["private_key"]
        )

    def test_bundle_is_bound_answer_private_and_model_independent(self) -> None:
        check = verify_semantic_evaluator_bundle(self.bundle)
        self.assertTrue(check["valid"], check["errors"])
        manifest = self.bundle["manifest"]
        self.assertFalse(manifest["private_contracts_present"])
        self.assertFalse(manifest["model_identity_in_scoring"])
        self.assertNotIn("cause_atom_groups", json.dumps(manifest))

    def test_reference_paraphrase_and_adversarial_panel(self) -> None:
        result = semantic_evaluator_self_test(self.bundle, self.source["private_key"])
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(result["check_count"], 67)

    def test_wrong_order_negation_and_caller_success_fail_closed(self) -> None:
        contract = next(
            row
            for row in self.bundle["private_key"]["contracts"].values()
            if any("pre_commit" in group for group in row["cause_atom_groups"])
        )
        response = {
            "cause": "the cache is not invalidated before commit and a reader never recaches the old value",
            "repair": "clear the cache before commit",
            "evidence_ids": list(contract["required_evidence_ids"]),
            "uncertainty": "low",
            "success": True,
        }
        verdict = evaluate_semantic_causal_response(contract, json.dumps(response))
        self.assertFalse(verdict["success"])
        self.assertIn("response_keys_invalid", verdict["errors"])
        self.assertIn("required_cause_semantics_missing", verdict["errors"])
        self.assertIn("required_repair_semantics_missing", verdict["errors"])

    def test_tampered_contract_or_bundle_is_unknown_or_invalid(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        contract = next(iter(tampered["private_key"]["contracts"].values()))
        contract["cause_atom_groups"] = [["cache"]]
        self.assertFalse(verify_semantic_evaluator_bundle(tampered)["valid"])
        verdict = evaluate_semantic_causal_response(contract, "{}")
        self.assertIsNone(verdict["success"])
        self.assertEqual(verdict["state"], "unknown")

    def test_fresh_live_screen_is_bound_and_reconstructed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = ensure_home(root / "home")
            host = root / "host"
            host.mkdir()
            (host / "README.md").write_text("alpha23\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            try:
                repo = "Alpha23Host"
                bootstrap_repository(home, store, host, repo)
                session = open_symbiotic_session(
                    store, repo, task="test semantic evaluator preflight", persist=True
                )
                preflight = store.append_symbiotic_receipt(
                    repo,
                    {
                        "schema_version": "cortex-semantic-causal-evaluator-preflight/2.0",
                        "kind": "semantic_causal_evaluator_preflight",
                        "state": "SEMANTIC_CAUSAL_EVALUATOR_V2_READY",
                        "evaluator_manifest": self.bundle["manifest"],
                        "planned_live_calls": 0,
                        "baseline_difficulty_established": False,
                        "session_id": session["session_id"],
                        "turn_id": 0,
                        "event_id": "alpha23_test_preflight",
                        "body_epoch_id": session["body_epoch_id"],
                    },
                )
                level_three = [
                    row
                    for row in self.source["manifest"]["cases"]
                    if row["difficulty_level"] == 3
                ]
                source_contracts = self.source["private_key"]["contracts"]
                adapter = ExternalSemanticAdapter(
                    json.dumps(source_contracts[row["case_id"]]["reference_response"])
                    for row in level_three
                )
                register_will_principal(
                    store,
                    repo,
                    "alpha23-operator",
                    "Alpha.23 test operator",
                    secret="alpha23-principal-secret",
                )
                register_adapter_provenance(
                    store,
                    repo,
                    adapter,
                    boundary_kind="external_api",
                    principal_id="alpha23-operator",
                    principal_secret="alpha23-principal-secret",
                    endpoint_descriptor={"transport": "test_external_boundary"},
                    model_family="semantic-frontier-family",
                    capability_class="general_reasoning",
                )
                prereg = freeze_live_semantic_screen_v2(
                    store,
                    repo,
                    evaluator_preflight_receipt_hash=preflight["receipt_hash"],
                    corpus_manifest=self.source["manifest"],
                    evaluator_bundle=self.bundle,
                    adapter=adapter,
                )
                grant = CapabilityGrant(
                    workspace_root=str(host),
                    allowed_tools=(),
                    principal_id="alpha23-test",
                    purpose="bounded four-call v2 screen",
                    issued_at=time.time(),
                    expires_at=time.time() + 60,
                    max_tool_calls=0,
                    max_total_tool_seconds=0.0,
                )
                result = execute_live_semantic_screen_v2(
                    store,
                    repo,
                    preregistration=prereg,
                    corpus_manifest=self.source["manifest"],
                    evaluator_bundle=self.bundle,
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

                audit = verify_live_semantic_screen_v2(
                    store,
                    repo,
                    result_receipt_hash=result["receipt_hash"],
                    evaluator_bundle=self.bundle,
                )
                self.assertTrue(audit["valid"], audit["errors"])
                self.assertEqual(audit["difficulty_levels"], [3])

                level_four = [
                    row
                    for row in self.source["manifest"]["cases"]
                    if row["difficulty_level"] == 4
                ]
                harder_answers = []
                for index, row in enumerate(level_four):
                    answer = copy.deepcopy(
                        source_contracts[row["case_id"]]["reference_response"]
                    )
                    if index < 3:
                        answer["evidence_ids"] = answer["evidence_ids"][:-1]
                    else:
                        answer["repair"] = (
                            "require rebuilds to read a snapshot matching the committed "
                            "source generation and refuse sealing on mismatch"
                        )
                    harder_answers.append(json.dumps(answer))
                adapter.answers.extend(harder_answers)
                harder_prereg = freeze_harder_live_semantic_screen_v2(
                    store,
                    repo,
                    prior_result_receipt_hash=result["receipt_hash"],
                    corpus_manifest=self.source["manifest"],
                    evaluator_bundle=self.bundle,
                    adapter=adapter,
                )
                harder_result = execute_live_semantic_screen_v2(
                    store,
                    repo,
                    preregistration=harder_prereg,
                    corpus_manifest=self.source["manifest"],
                    evaluator_bundle=self.bundle,
                    adapter=adapter,
                    tools=ToolRegistry(),
                    grant=grant,
                )
                harder_audit = verify_live_semantic_screen_v2(
                    store,
                    repo,
                    result_receipt_hash=harder_result["receipt_hash"],
                    evaluator_bundle=self.bundle,
                )
                self.assertTrue(harder_audit["valid"], harder_audit["errors"])
                self.assertEqual(harder_audit["difficulty_levels"], [4])
                self.assertEqual(harder_audit["screen"]["state"], "screening_floor")
                self.assertEqual(
                    harder_prereg["prior_result_receipt_hash"], result["receipt_hash"]
                )
                instrument_audit = audit_harder_live_semantic_screen_v2(
                    store,
                    repo,
                    result_receipt_hash=harder_result["receipt_hash"],
                    evaluator_bundle=self.bundle,
                )
                self.assertEqual(
                    instrument_audit["state"], "DIFFICULTY_INTERPOLATION_HELD"
                )
                self.assertEqual(
                    instrument_audit["evidence_binding_rejection_count"], 3
                )
                self.assertGreaterEqual(
                    instrument_audit["semantic_clause_rejection_count"], 1
                )
                self.assertEqual(instrument_audit["additional_model_calls"], 0)
                self.assertFalse(instrument_audit["historical_scores_rewritten"])

                caller_copy = dict(result)
                caller_copy["screen"] = {"state": "calibrated", "success_count": 2}
                self.assertTrue(
                    verify_live_semantic_screen_v2(
                        store,
                        repo,
                        result_receipt_hash=caller_copy["receipt_hash"],
                        evaluator_bundle=self.bundle,
                    )["valid"]
                )
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
