from __future__ import annotations

import copy
import json
import unittest

from cortex.intermediate_relational_forge import build_intermediate_relational_bundle
from cortex.relational_equivalence import (
    build_equivalence_evaluator_bundle,
    equivalence_evaluator_self_test,
    evaluate_equivalent_relational_response,
    verify_equivalence_evaluator_bundle,
)


class Alpha29RelationalEquivalenceTests(unittest.TestCase):
    def setUp(self) -> None:
        source = build_intermediate_relational_bundle(secret_seed="alpha29-test")
        self.bundle = build_equivalence_evaluator_bundle(source)

    def test_bundle_and_adversarial_panel(self) -> None:
        check = verify_equivalence_evaluator_bundle(self.bundle)
        self.assertTrue(check["valid"], check["errors"])
        self_test = equivalence_evaluator_self_test(self.bundle)
        self.assertTrue(self_test["passed"], self_test["checks"])
        self.assertEqual(self_test["check_count"], 9)
        self.assertFalse(self.bundle["manifest"]["private_contracts_present"])
        self.assertFalse(self.bundle["manifest"]["model_identity_in_scoring"])

    def test_finite_equivalence_and_grounded_supersets_do_not_open_claims(self) -> None:
        contract = next(iter(self.bundle["private_key"]["contracts"].values()))
        response = {
            "cause": "words do not determine the score",
            "repair": "words do not determine the score",
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
        verdict = evaluate_equivalent_relational_response(
            contract, json.dumps(response)
        )
        self.assertTrue(verdict["success"], verdict["errors"])
        self.assertFalse(verdict["submitted_evidence_is_minimal"])

        response["causal_relations"] = response["causal_relations"][:-1]
        missing = evaluate_equivalent_relational_response(
            contract, json.dumps(response)
        )
        self.assertFalse(missing["success"])
        self.assertIn("required_causal_propositions_missing", missing["errors"])

    def test_tamper_and_caller_success_fail_closed(self) -> None:
        tampered = copy.deepcopy(self.bundle)
        contract = next(iter(tampered["private_key"]["contracts"].values()))
        contract["required_causal_propositions"] = []
        self.assertFalse(verify_equivalence_evaluator_bundle(tampered)["valid"])
        original = next(iter(self.bundle["private_key"]["contracts"].values()))
        response = {
            "cause": "x",
            "repair": "y",
            "causal_relations": [p[0] for p in original["required_causal_propositions"]],
            "repair_relations": [p[0] for p in original["required_repair_propositions"]],
            "evidence_ids": ["E1", "E2", "E3", "E4"],
            "uncertainty": "low",
            "success": True,
        }
        verdict = evaluate_equivalent_relational_response(original, json.dumps(response))
        self.assertFalse(verdict["success"])
        self.assertIn("response_keys_invalid", verdict["errors"])


if __name__ == "__main__":
    unittest.main()
