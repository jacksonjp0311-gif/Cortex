from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from cortex.adapter_provenance import register_adapter_provenance
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.intermediate_relational_forge import build_intermediate_relational_bundle
from cortex.native_agent import CapabilityGrant, ToolRegistry
from cortex.relational_equivalence import build_equivalence_evaluator_bundle
from cortex.relational_final_screen import (
    execute_final_relational_screen,
    freeze_final_relational_screen,
    verify_final_relational_screen,
)
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


class ExternalFinalAdapter:
    __slots__ = ("answers",)
    provider_family = "external-final-provider"
    model_id = "final-frontier-model"
    model_version = "2026-09"
    adapter_id = "tests.external-final-adapter"
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


class Alpha30FinalRelationalScreenTests(unittest.TestCase):
    def _fixture(self, temp: str, *, malformed: bool = False):
        root = Path(temp)
        home = ensure_home(root / "home")
        host = root / "host"
        host.mkdir()
        (host / "README.md").write_text("alpha30\n", encoding="utf-8")
        store = Store(home / "cortex.db")
        repo = "Alpha30Host"
        bootstrap_repository(home, store, host, repo)
        corpus = build_intermediate_relational_bundle(secret_seed="alpha30-corpus")
        evaluator = build_equivalence_evaluator_bundle(corpus)
        session = open_symbiotic_session(store, repo, task="alpha30 source", persist=True)
        source_prereg = store.append_symbiotic_receipt(
            repo,
            {
                "schema_version": "cortex-relational-live-preregistration/1.0",
                "kind": "relational_live_preregistration",
                "difficulty_band": "bridge_low",
                "cases": [
                    case
                    for case in corpus["manifest"]["cases"]
                    if case["difficulty_band"] == "bridge_low"
                ],
                "session_id": session["session_id"],
                "turn_id": 0,
                "event_id": "alpha30_source_prereg",
                "body_epoch_id": session["body_epoch_id"],
            },
        )
        source_result = store.append_symbiotic_receipt(
            repo,
            {
                "schema_version": "cortex-relational-live-result/1.0",
                "kind": "relational_live_result",
                "preregistration_receipt_hash": source_prereg["receipt_hash"],
                "session_id": session["session_id"],
                "turn_id": 1,
                "event_id": "alpha30_source_result",
                "body_epoch_id": session["body_epoch_id"],
            },
        )
        preflight = store.append_symbiotic_receipt(
            repo,
            {
                "schema_version": "cortex-relational-equivalence-preflight/4.0",
                "kind": "relational_equivalence_preflight",
                "state": "RELATIONAL_EQUIVALENCE_V4_READY",
                "ruler_building_closed": True,
                "additional_model_calls": 0,
                "historical_scores_rewritten": False,
                "source_result_receipt_hash": source_result["receipt_hash"],
                "evaluator_manifest": evaluator["manifest"],
                "session_id": session["session_id"],
                "turn_id": 2,
                "event_id": "alpha30_equivalence_preflight",
                "body_epoch_id": session["body_epoch_id"],
            },
        )
        contracts = evaluator["private_key"]["contracts"]
        answers = []
        for case_id in corpus["manifest"]["band_case_ids"]["bridge_mid"]:
            if malformed:
                answers.append("not-json")
                continue
            contract = contracts[case_id]
            answers.append(
                json.dumps(
                    {
                        "cause": "bounded public rationale",
                        "repair": "bounded public rationale",
                        "causal_relations": [
                            proposition[-1]
                            for proposition in contract["required_causal_propositions"]
                        ],
                        "repair_relations": [
                            proposition[-1]
                            for proposition in contract["required_repair_propositions"]
                        ],
                        "evidence_ids": ["E1", "E2", "E3", "E4", "E5", "D1"],
                        "uncertainty": "low",
                    }
                )
            )
        adapter = ExternalFinalAdapter(answers)
        register_will_principal(
            store,
            repo,
            "alpha30-operator",
            "Alpha.30 test operator",
            secret="alpha30-principal-secret",
        )
        register_adapter_provenance(
            store,
            repo,
            adapter,
            boundary_kind="external_api",
            principal_id="alpha30-operator",
            principal_secret="alpha30-principal-secret",
            endpoint_descriptor={"transport": "test_external_boundary"},
            model_family="final-frontier-family",
            capability_class="general_reasoning",
        )
        return store, repo, host, corpus, evaluator, preflight, adapter

    def _run(self, fixture):
        store, repo, host, corpus, evaluator, preflight, adapter = fixture
        prereg = freeze_final_relational_screen(
            store,
            repo,
            equivalence_preflight_receipt_hash=preflight["receipt_hash"],
            corpus_bundle=corpus,
            evaluator_bundle=evaluator,
            adapter=adapter,
        )
        grant = CapabilityGrant(
            workspace_root=str(host),
            allowed_tools=(),
            principal_id="alpha30-test",
            purpose="final prospective screen",
            issued_at=time.time(),
            expires_at=time.time() + 60,
            max_tool_calls=0,
            max_total_tool_seconds=0.0,
        )
        result = execute_final_relational_screen(
            store,
            repo,
            preregistration=prereg,
            corpus_bundle=corpus,
            evaluator_bundle=evaluator,
            adapter=adapter,
            tools=ToolRegistry(),
            grant=grant,
        )
        return prereg, result

    def test_final_screen_is_prospective_reconstructed_and_retires_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp)
            store, repo, _, corpus, evaluator, _, _ = fixture
            try:
                prereg, result = self._run(fixture)
                self.assertEqual(prereg["difficulty_band"], "bridge_mid")
                self.assertTrue(prereg["prospective_case_disjointness"])
                self.assertFalse(prereg["ruler_revision_permitted"])
                self.assertEqual(result["screen"]["state"], "screening_ceiling")
                self.assertTrue(result["synthetic_semantic_benchmark_retired"])
                self.assertEqual(
                    result["next_action"],
                    "forge_executable_code_tasks_with_frozen_external_tests",
                )
                audit = verify_final_relational_screen(
                    store,
                    repo,
                    result_receipt_hash=result["receipt_hash"],
                    corpus_bundle=corpus,
                    evaluator_bundle=evaluator,
                )
                self.assertTrue(audit["valid"], audit["errors"])
                caller_copy = dict(result, synthetic_semantic_benchmark_retired=False)
                self.assertTrue(
                    verify_final_relational_screen(
                        store,
                        repo,
                        result_receipt_hash=caller_copy["receipt_hash"],
                        corpus_bundle=corpus,
                        evaluator_bundle=evaluator,
                    )["valid"]
                )
            finally:
                store.close()

    def test_unknown_retires_line_instead_of_becoming_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            fixture = self._fixture(temp, malformed=True)
            store = fixture[0]
            try:
                _, result = self._run(fixture)
                self.assertEqual(result["screen"]["state"], "screening_held_unknown")
                self.assertEqual(result["screen"]["unknown_count"], 4)
                self.assertTrue(result["synthetic_semantic_benchmark_retired"])
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
