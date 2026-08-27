"""v9.8.7 distillation seal and partial resolving-evidence tests."""

from __future__ import annotations

import unittest

from cortex.discriminative_forge import (
    build_cost_entanglement_corpus,
    build_latent_cause_corpus,
    build_partial_evidence_corpus,
)


class V987PartialEvidenceTests(unittest.TestCase):
    def test_prior_corpus_identities_are_unchanged(self) -> None:
        latent = build_latent_cause_corpus(
            seed="cortex-v985-latent-development",
            maximum_level=4,
            variants_per_level=8,
        )
        entangled = build_cost_entanglement_corpus(
            seed="cortex-v986-cost-entanglement-development",
            maximum_level=4,
            variants_per_level=8,
        )
        self.assertEqual(
            latent["corpus_hash"],
            "c7b38b4811567987f118125ad5d8394ce77d833e83d2722d0bc011ab418520bc",
        )
        self.assertEqual(
            entangled["corpus_hash"],
            "1899affd366eb25baf59ee4f3fd2bc6ccb0b9033a7dd6f7085055eaa0cb67316",
        )

    def test_partial_disclosure_is_deterministic_committed_and_answer_free(self) -> None:
        first = build_partial_evidence_corpus(
            seed="v987-tests", maximum_level=2, variants_per_level=2,
            architecture_signature_fraction=0.5,
        )
        second = build_partial_evidence_corpus(
            seed="v987-tests", maximum_level=2, variants_per_level=2,
            architecture_signature_fraction=0.5,
        )
        self.assertEqual(first, second)
        self.assertEqual(first["version"], "9.8.7")
        self.assertFalse(first["evidence_disclosure_policy"]["answers_disclosed"])
        architecture = [
            case for case in first["cases"]
            if case["family"] == "architecture_reconstruction"
        ]
        self.assertTrue(architecture)
        for case in architecture:
            self.assertIn("partial historical signature table", case["prompt"])
            self.assertGreaterEqual(case["disclosed_coordinate_count"], 1)
            self.assertLessEqual(
                case["disclosed_coordinate_count"],
                case["minimum_resolving_coordinate_count"],
            )
            self.assertEqual(len(case["undisclosed_signature_commitment"]), 64)
            self.assertEqual(len(case["complete_signature_commitment"]), 64)
            self.assertNotIn(case["expected_public_output"], str(case["disclosed_signature_table"]))
            self.assertFalse(case.get("model_identity_in_ontology", False))

    def test_disclosure_fraction_is_bounded(self) -> None:
        for invalid in (0.0, -0.1, 1.1):
            with self.assertRaises(ValueError):
                build_partial_evidence_corpus(
                    maximum_level=1,
                    variants_per_level=2,
                    architecture_signature_fraction=invalid,
                )


if __name__ == "__main__":
    unittest.main()
