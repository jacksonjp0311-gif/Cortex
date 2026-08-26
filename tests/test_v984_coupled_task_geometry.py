from __future__ import annotations

import unittest

from cortex.discriminative_forge import (
    COUPLED_FAMILIES,
    build_coupled_dependency_corpus,
    evaluate_case,
)


class V984CoupledTaskGeometryTests(unittest.TestCase):
    def test_corpus_is_deterministic_bounded_and_model_neutral(self):
        first = build_coupled_dependency_corpus(seed="fixed", maximum_level=2, variants_per_level=3)
        second = build_coupled_dependency_corpus(seed="fixed", maximum_level=2, variants_per_level=3)
        self.assertEqual(first, second)
        self.assertEqual(len(first["cases"]), len(COUPLED_FAMILIES) * 2 * 3)
        self.assertTrue(first["development_only"])
        self.assertFalse(first["confirmatory_eligible"])
        self.assertFalse(first["model_identity_in_ontology"])

    def test_every_case_has_real_dependency_depth_and_exact_answer(self):
        corpus = build_coupled_dependency_corpus(maximum_level=2, variants_per_level=2)
        for case in corpus["cases"]:
            self.assertGreaterEqual(case["dependency_depth"], 10)
            self.assertNotEqual(case["difficulty_mechanism"], "composed_exact_subcases")
            self.assertTrue(evaluate_case(case, case["expected_public_output"]))
            self.assertFalse(evaluate_case(case, "definitely-wrong"))

    def test_levels_change_semantic_material_not_only_identity(self):
        corpus = build_coupled_dependency_corpus(seed="semantic", maximum_level=3, variants_per_level=2)
        for family in COUPLED_FAMILIES:
            rows = [case for case in corpus["cases"] if case["family"] == family and case["variant"] == 0]
            self.assertEqual(len({case["prompt"] for case in rows}), 3)
            depths = [case["dependency_depth"] for case in rows]
            self.assertEqual(depths, sorted(depths))
            self.assertEqual(len(set(depths)), 3)


if __name__ == "__main__":
    unittest.main()
