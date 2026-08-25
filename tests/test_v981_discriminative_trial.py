from __future__ import annotations

import unittest

from cortex.discriminability import (
    DiscriminabilityError,
    assess_binary_task_family,
    assess_paired_information,
    assess_task_panel,
    binary_entropy,
    evidence_geometry,
    verify_task_panel,
)
from cortex.discriminative_forge import TASK_FAMILIES, build_discriminative_corpus, evaluate_case


class V981DiscriminativeTrialTests(unittest.TestCase):
    def test_entropy_exposes_ceiling_and_floor_measurement_collapse(self) -> None:
        self.assertEqual(binary_entropy(0.0), 0.0)
        self.assertEqual(binary_entropy(1.0), 0.0)
        self.assertEqual(binary_entropy(0.5), 1.0)
        self.assertEqual(assess_binary_task_family([1, 1, 1, 1])["classification"], "ceiling")
        self.assertEqual(assess_binary_task_family([0, 0, 0, 0])["classification"], "floor")
        self.assertEqual(assess_binary_task_family([0, 1, 0, 1])["state"], "pass")

    def test_insufficient_calibration_stays_unknown(self) -> None:
        report = assess_binary_task_family([0, 1], minimum_cases=4)
        self.assertEqual(report["state"], "unknown")
        self.assertFalse(report["confirmatory_candidate"])

    def test_effective_causal_sample_is_discordance_not_raw_n(self) -> None:
        collapsed = assess_paired_information([1, 1, 1, 1], [1, 1, 1, 1])
        self.assertEqual(collapsed["case_count"], 4)
        self.assertEqual(collapsed["effective_causal_sample"], 0)
        self.assertEqual(collapsed["reason"], "measurement_collapse")
        informative = assess_paired_information([0, 1, 0, 1], [1, 1, 1, 0])
        self.assertEqual(informative["effective_causal_sample"], 3)
        self.assertEqual(informative["benefit_pairs"], 2)
        self.assertEqual(informative["harm_pairs"], 1)

    def test_evidence_geometry_is_noncompensatory(self) -> None:
        report = evidence_geometry(
            semantic_evidence="pass",
            discriminability="fail",
            independent_replication="pass",
            diagnostic_strengths={"semantic_evidence": 1.0, "discriminability": 0.9, "independent_replication": 1.0},
        )
        self.assertEqual(report["readiness"], "fail")
        self.assertGreater(report["diagnostic_geometric_mean"], 0.9)
        self.assertFalse(report["diagnostic_can_open_gate"])
        with self.assertRaises(DiscriminabilityError):
            evidence_geometry(semantic_evidence="pass", discriminability="claimed", independent_replication="pass")

    def test_task_panel_selects_only_informative_families(self) -> None:
        report = assess_task_panel({"ceiling": [1, 1, 1, 1], "informative": [0, 1, 0, 1]})
        self.assertEqual(report["overall_state"], "fail")
        self.assertEqual(report["selected_families"], ["informative"])
        self.assertFalse(report["confirmatory_eligible"])
        self.assertFalse(report["authority"]["execution_authorized"])
        self.assertTrue(verify_task_panel(report)["valid"])
        tampered = {**report, "overall_state": "pass"}
        self.assertFalse(verify_task_panel(tampered)["valid"])

    def test_forge_is_deterministic_model_neutral_and_development_only(self) -> None:
        first = build_discriminative_corpus(seed="fixed", variants_per_family=4)
        second = build_discriminative_corpus(seed="fixed", variants_per_family=4)
        self.assertEqual(first, second)
        self.assertEqual(first["task_families"], list(TASK_FAMILIES))
        self.assertEqual(len(first["cases"]), 20)
        self.assertFalse(first["confirmatory_eligible"])
        self.assertFalse(first["model_identity_in_ontology"])
        self.assertNotIn("provider", str(first).lower())
        case = first["cases"][0]
        self.assertTrue(evaluate_case(case, case["expected_public_output"]))
        self.assertFalse(evaluate_case(case, "wrong"))


if __name__ == "__main__":
    unittest.main()
