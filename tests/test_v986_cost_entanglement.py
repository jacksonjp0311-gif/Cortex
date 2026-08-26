from __future__ import annotations

import unittest

from cortex.calibration_commissioning import (
    _invocation_cost_metrics,
    summarize_evidence_geometry,
    summarize_observation_costs,
)
from cortex.discriminative_forge import (
    LATENT_CAUSE_FAMILIES,
    build_cost_entanglement_corpus,
    build_latent_cause_corpus,
)


class V986CostEntanglementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = build_cost_entanglement_corpus(
            seed="v986-tests", maximum_level=2, variants_per_level=2
        )

    def test_v985_default_corpus_remains_immutable(self):
        corpus = build_latent_cause_corpus(
            seed="cortex-v985-latent-development", maximum_level=4, variants_per_level=8
        )
        self.assertEqual(
            corpus["corpus_hash"],
            "c7b38b4811567987f118125ad5d8394ce77d833e83d2722d0bc011ab418520bc",
        )

    def test_structural_entanglement_is_bounded_and_outcome_independent(self):
        second = build_cost_entanglement_corpus(
            seed="v986-tests", maximum_level=2, variants_per_level=2
        )
        self.assertEqual(self.corpus, second)
        self.assertEqual(self.corpus["version"], "9.8.6")
        for case in self.corpus["cases"]:
            self.assertGreaterEqual(case["evidence_entanglement_ratio"], 0.0)
            self.assertLessEqual(case["evidence_entanglement_ratio"], 1.0)
            self.assertGreaterEqual(case["minimum_resolving_coordinate_count"], 1)
            self.assertLessEqual(
                case["minimum_resolving_coordinate_count"], case["evidence_coordinate_count"]
            )
            self.assertEqual(
                case["metric_scope"], "structural_evidence_geometry_not_model_difficulty"
            )

    def test_rebalance_is_explicit_and_model_neutral(self):
        architecture = [
            case for case in self.corpus["cases"]
            if case["family"] == "architecture_reconstruction"
        ]
        self.assertTrue(all("Candidate historical signature table" in case["prompt"] for case in architecture))
        baseline = build_latent_cause_corpus(
            seed="same", maximum_level=1, variants_per_level=2, repair_transfer_multiplier=1
        )
        rebalanced = build_latent_cause_corpus(
            seed="same", maximum_level=1, variants_per_level=2, repair_transfer_multiplier=2
        )
        base_depth = next(case["dependency_depth"] for case in baseline["cases"] if case["family"] == "multi_step_code_repair")
        new_depth = next(case["dependency_depth"] for case in rebalanced["cases"] if case["family"] == "multi_step_code_repair")
        self.assertGreater(new_depth, base_depth)
        self.assertFalse(self.corpus["model_identity_in_ontology"])
        self.assertEqual(tuple(self.corpus["task_families"]), LATENT_CAUSE_FAMILIES)

    def test_cost_metrics_reconstruct_canonical_coordinates_without_false_zeroes(self):
        metrics = _invocation_cost_metrics({
            "requested_at": 10.0,
            "completed_at": 12.5,
            "token_usage": {
                "input_tokens": 100,
                "output_tokens": 25,
                "reasoning_tokens": 20,
                "total_tokens": 125,
            },
            "cost": {"amount": 0.0125, "currency": "usd"},
        })
        self.assertEqual(metrics["latency_seconds"], 2.5)
        self.assertEqual(metrics["total_tokens"], 125.0)
        self.assertEqual(metrics["cost_currency"], "USD")
        self.assertTrue(all(metrics["validity"].values()))
        missing = _invocation_cost_metrics({"requested_at": 20.0, "completed_at": 19.0})
        self.assertIsNone(missing["latency_seconds"])
        self.assertIsNone(missing["total_tokens"])
        self.assertFalse(missing["validity"]["latency"])
        self.assertFalse(missing["validity"]["total_tokens"])

    def test_cost_and_geometry_panels_are_diagnostic_only(self):
        case = self.corpus["cases"][0]
        observations = [{
            "case_id": case["case_id"],
            "cost_metrics": {
                "latency_seconds": 2.0,
                "total_tokens": 100.0,
                "cost_amount": 0.01,
                "cost_currency": "USD",
            },
        }]
        cost = summarize_observation_costs(observations, {case["case_id"]: case})
        geometry = summarize_evidence_geometry([case])
        self.assertAlmostEqual(
            cost["resolved_information_bits_per_second"]["median"],
            case["resolved_information_bits"] / 2.0,
            places=6,
        )
        self.assertFalse(cost["repeatability_established"])
        self.assertFalse(cost["gate_effect"])
        self.assertTrue(geometry["outcome_independent"])
        self.assertFalse(geometry["gate_effect"])


if __name__ == "__main__":
    unittest.main()
