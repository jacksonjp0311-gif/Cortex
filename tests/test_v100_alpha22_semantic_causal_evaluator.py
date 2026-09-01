from __future__ import annotations

import copy
import json
import unittest

from cortex.open_response_calibration import build_open_response_latent_bundle
from cortex.semantic_causal_evaluator import (
    build_semantic_evaluator_bundle,
    evaluate_semantic_causal_response,
    semantic_evaluator_self_test,
    verify_semantic_evaluator_bundle,
)


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


if __name__ == "__main__":
    unittest.main()
