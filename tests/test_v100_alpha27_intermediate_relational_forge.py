from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.intermediate_relational_forge import (
    BANDS,
    build_intermediate_relational_bundle,
    freeze_intermediate_relational_forge,
    verify_intermediate_relational_bundle,
)
from cortex.relational_causal_evaluator import evaluate_relational_causal_response
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session


class Alpha27IntermediateRelationalForgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = build_intermediate_relational_bundle(
            secret_seed="alpha27-test-seed"
        )

    def test_bundle_is_answer_private_progressive_and_valid(self) -> None:
        check = verify_intermediate_relational_bundle(self.bundle)
        self.assertTrue(check["valid"], check["errors"])
        manifest = self.bundle["manifest"]
        self.assertEqual(len(manifest["cases"]), 12)
        self.assertEqual(tuple(manifest["bands"]), BANDS)
        self.assertTrue(manifest["evidence_policy_constant_across_bands"])
        public = json.dumps(manifest)
        self.assertNotIn("required_causal_relations", public)
        self.assertNotIn("reference_response", public)
        edge_counts = []
        for band in BANDS:
            case_id = manifest["band_case_ids"][band][0]
            contract = self.bundle["private_key"]["contracts"][case_id]
            edge_counts.append(
                len(contract["required_causal_relations"])
                + len(contract["required_repair_relations"])
            )
            verdict = evaluate_relational_causal_response(
                contract, json.dumps(contract["reference_response"])
            )
            self.assertTrue(verdict["success"], verdict["errors"])
            self.assertEqual(
                contract["minimal_evidence_proof_sets"],
                [["E1", "E2", "E3", "E4"], ["E2", "E3", "E4", "E5"]],
            )
        self.assertEqual(edge_counts, sorted(edge_counts))
        self.assertEqual(len(set(edge_counts)), 3)

    def test_tampering_and_caller_verdict_fail_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        tampered["manifest"]["initial_screen_band"] = "bridge_high"
        self.assertFalse(verify_intermediate_relational_bundle(tampered)["valid"])
        contract = next(iter(self.bundle["private_key"]["contracts"].values()))
        response = dict(contract["reference_response"], success=True)
        verdict = evaluate_relational_causal_response(contract, json.dumps(response))
        self.assertFalse(verdict["success"])
        self.assertIn("response_keys_invalid", verdict["errors"])

    def test_forge_requires_canonical_alpha26_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = ensure_home(root / "home")
            host = root / "host"
            host.mkdir()
            (host / "README.md").write_text("alpha27\n", encoding="utf-8")
            store = Store(home / "cortex.db")
            try:
                repo = "Alpha27Host"
                bootstrap_repository(home, store, host, repo)
                session = open_symbiotic_session(
                    store, repo, task="alpha27 prerequisite", persist=True
                )
                prerequisite = store.append_symbiotic_receipt(
                    repo,
                    {
                        "schema_version": "cortex-relational-causal-preflight/3.0",
                        "kind": "relational_causal_evaluator_preflight",
                        "state": "RELATIONAL_CAUSAL_EVALUATOR_V3_READY",
                        "planned_live_calls": 0,
                        "historical_scores_rewritten": False,
                        "difficulty_interpolation_ready": True,
                        "evaluator_manifest": {"evaluator_hash": "e" * 64},
                        "session_id": session["session_id"],
                        "turn_id": 0,
                        "event_id": "alpha27_prerequisite",
                        "body_epoch_id": session["body_epoch_id"],
                    },
                )
                preflight = freeze_intermediate_relational_forge(
                    store,
                    repo,
                    relational_preflight_receipt_hash=prerequisite["receipt_hash"],
                    bundle=self.bundle,
                )
                self.assertEqual(
                    preflight["state"], "INTERMEDIATE_RELATIONAL_FORGE_READY"
                )
                self.assertEqual(preflight["planned_live_calls"], 0)
                self.assertEqual(preflight["maximum_future_calls_without_new_authority"], 0)
                self.assertFalse(preflight["host_mutate_authorized"])
                self.assertFalse(preflight["execution_authorized"])
                with self.assertRaises(ValueError):
                    freeze_intermediate_relational_forge(
                        store,
                        repo,
                        relational_preflight_receipt_hash="f" * 64,
                        bundle=self.bundle,
                    )
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
