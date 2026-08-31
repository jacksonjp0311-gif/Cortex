from __future__ import annotations

import copy
import json
import unittest

from cortex.open_response_calibration import (
    HostCalibrationContractVault,
    audit_atomic_evaluator_response,
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

    def test_private_contract_vault_chunks_and_reconstructs_exactly(self) -> None:
        class FakeKeyring:
            def __init__(self):
                self.values = {}

            def set_password(self, service, username, value):
                self.values[(service, username)] = value

            def get_password(self, service, username):
                return self.values.get((service, username))

            def delete_password(self, service, username):
                self.values.pop((service, username), None)

        fake = FakeKeyring()

        class Vault(HostCalibrationContractVault):
            def _keyring(self):
                return fake

        vault = Vault()
        corpus_hash = self.bundle["manifest"]["corpus_hash"]
        vault.set(corpus_hash, self.bundle["private_key"])
        self.assertEqual(vault.get(corpus_hash), self.bundle["private_key"])
        self.assertGreater(len(fake.values), 2)
        vault.delete(corpus_hash)
        self.assertIsNone(vault.get(corpus_hash))

    def test_lexical_near_miss_audit_holds_without_rewriting_failure(self) -> None:
        contracts = list(self.bundle["private_key"]["contracts"].values())
        contract = next(
            row
            for row in contracts
            if len(row["required_evidence_ids"]) == 5
            and any("before commit" in clause for clause in row["required_cause_clauses"])
        )
        response = {
            "cause": (
                "cache invalidation occurs before the database commit, allowing a "
                "concurrent reader to recache the stale old value"
            ),
            "repair": "invalidate the cache only after a successful commit",
            "evidence_ids": list(contract["required_evidence_ids"]),
            "uncertainty": "low",
        }
        audit = audit_atomic_evaluator_response(contract, json.dumps(response))
        self.assertFalse(audit["original_success"])
        self.assertTrue(audit["brittleness_signal"])
        self.assertFalse(audit["changes_original_verdict"])
        self.assertFalse(audit["semantic_correctness_established"])


if __name__ == "__main__":
    unittest.main()
