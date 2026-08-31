from __future__ import annotations

import copy
import json
import unittest

from cortex.open_response_calibration import (
    build_open_response_latent_bundle,
    evaluate_atomic_causal_response,
    verify_open_response_latent_bundle,
)


class Alpha20OpenResponseCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = build_open_response_latent_bundle(secret_seed="alpha20-test-seed")

    def test_public_geometry_is_answer_free_and_private_contract_is_bound(self) -> None:
        check = verify_open_response_latent_bundle(self.bundle)
        self.assertTrue(check["valid"], check["errors"])
        manifest = self.bundle["manifest"]
        self.assertEqual(manifest["case_count"], 16)
        self.assertEqual(manifest["levels"], [1, 2, 3, 4])
        self.assertFalse(manifest["answers_present"])
        serialized = json.dumps(manifest)
        self.assertNotIn("required_cause_clauses", serialized)
        self.assertNotIn("reference_response", serialized)

    def test_reference_response_passes_and_missing_cause_fails(self) -> None:
        contract = next(iter(self.bundle["private_key"]["contracts"].values()))
        reference = json.dumps(contract["reference_response"])
        passed = evaluate_atomic_causal_response(contract, reference)
        self.assertTrue(passed["success"], passed)
        broken = dict(contract["reference_response"])
        broken["cause"] = "something happened"
        failed = evaluate_atomic_causal_response(contract, json.dumps(broken))
        self.assertFalse(failed["success"])
        self.assertIn("required_cause_atoms_missing", failed["errors"])

    def test_evidence_replay_forbidden_claim_and_extra_key_fail(self) -> None:
        contract = next(iter(self.bundle["private_key"]["contracts"].values()))
        replay = dict(contract["reference_response"])
        replay["evidence_ids"] = list(reversed(replay["evidence_ids"]))
        self.assertIn(
            "causal_evidence_binding_invalid",
            evaluate_atomic_causal_response(contract, json.dumps(replay))["errors"],
        )
        forbidden = dict(contract["reference_response"])
        forbidden["repair"] += " and retry"
        self.assertIn(
            "forbidden_unsupported_claim",
            evaluate_atomic_causal_response(contract, json.dumps(forbidden))["errors"],
        )
        extra = dict(contract["reference_response"])
        extra["success"] = True
        self.assertIn(
            "response_keys_invalid",
            evaluate_atomic_causal_response(contract, json.dumps(extra))["errors"],
        )

    def test_public_or_private_tampering_breaks_bundle(self) -> None:
        public = copy.deepcopy(self.bundle)
        public["manifest"]["cases"][0]["events"][0] = "tampered"
        self.assertFalse(verify_open_response_latent_bundle(public)["valid"])
        private = copy.deepcopy(self.bundle)
        contract = next(iter(private["private_key"]["contracts"].values()))
        contract["required_evidence_ids"] = ["D1"]
        self.assertFalse(verify_open_response_latent_bundle(private)["valid"])

    def test_malformed_response_is_unknown_not_pass(self) -> None:
        contract = next(iter(self.bundle["private_key"]["contracts"].values()))
        result = evaluate_atomic_causal_response(contract, "not-json")
        self.assertIsNone(result["success"])
        self.assertEqual(result["state"], "unknown")


if __name__ == "__main__":
    unittest.main()
