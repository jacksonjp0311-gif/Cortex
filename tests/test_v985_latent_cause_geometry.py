from __future__ import annotations

import math
import json
import unittest

from benchmarks.frontier_calibration_v983 import _prior_case_sessions
from cortex.discriminative_forge import (
    LATENT_CAUSE_FAMILIES,
    build_latent_cause_corpus,
    evaluate_case,
)


class V985LatentCauseGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = build_latent_cause_corpus(seed="v985-tests", maximum_level=2, variants_per_level=2)

    def test_corpus_is_deterministic_bounded_and_model_neutral(self):
        second = build_latent_cause_corpus(seed="v985-tests", maximum_level=2, variants_per_level=2)
        self.assertEqual(self.corpus, second)
        self.assertEqual(len(self.corpus["cases"]), len(LATENT_CAUSE_FAMILIES) * 2 * 2)
        self.assertTrue(self.corpus["development_only"])
        self.assertFalse(self.corpus["confirmatory_eligible"])
        self.assertFalse(self.corpus["model_identity_in_ontology"])

    def test_every_case_has_unique_evidence_resolution(self):
        for case in self.corpus["cases"]:
            count = case["hypothesis_count"]
            self.assertGreaterEqual(count, 7)
            self.assertTrue(case["epistemic_coupling"])
            self.assertTrue(case["evidence_signatures_unique"])
            self.assertEqual(case["posterior_hypothesis_count"], 1)
            self.assertEqual(len(case["hypothesis_evidence_hashes"]), count)
            self.assertEqual(len(set(case["hypothesis_evidence_hashes"].values())), count)
            self.assertAlmostEqual(case["local_hypothesis_entropy_bits"], math.log2(count), places=8)
            self.assertAlmostEqual(case["resolved_information_bits"], math.log2(count), places=8)

    def test_exact_public_evaluator_and_closed_authority(self):
        for case in self.corpus["cases"]:
            self.assertTrue(evaluate_case(case, case["expected_public_output"]))
            self.assertFalse(evaluate_case(case, "UNKNOWN"))
        self.assertNotIn("model", self.corpus["difficulty_law"])

    def test_harder_levels_increase_prior_hypothesis_entropy(self):
        for family in LATENT_CAUSE_FAMILIES:
            rows = [case for case in self.corpus["cases"] if case["family"] == family and case["variant"] == 0]
            entropies = [case["local_hypothesis_entropy_bits"] for case in rows]
            self.assertEqual(entropies, sorted(entropies))
            self.assertGreater(entropies[-1], entropies[0])

    def test_resume_discovers_latest_canonical_case_session_without_trusting_output(self):
        class Connection:
            def execute(self, _sql, _args):
                rows = [
                    {"session_id": "new", "turn_id": 2, "created_at": 2.0, "receipt_json": json.dumps({
                        "request": {"configuration": {"calibration_case_id": "case-a"}}
                    })},
                    {"session_id": "old", "turn_id": 1, "created_at": 1.0, "receipt_json": json.dumps({
                        "request": {"configuration": {"calibration_case_id": "case-a"}}
                    })},
                    {"session_id": "bad", "turn_id": 1, "created_at": 0.0, "receipt_json": "not-json"},
                ]

                class Cursor:
                    def fetchall(self):
                        return rows

                return Cursor()

        class Transaction:
            def __enter__(self):
                return Connection()

            def __exit__(self, *_args):
                return False

        class FakeStore:
            def transaction(self):
                return Transaction()

        self.assertEqual(_prior_case_sessions(FakeStore(), "Cortex"), {"case-a": ("new", 2)})


if __name__ == "__main__":
    unittest.main()
