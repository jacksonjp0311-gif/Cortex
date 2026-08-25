from __future__ import annotations

import copy
import hashlib
import json
import unittest

from cortex.discriminative_forge import (
    TASK_FAMILIES,
    build_difficulty_ladder_corpus,
    build_held_out_bundle,
    verify_held_out_bundle,
    verify_held_out_manifest,
)
from cortex.information_calibration import (
    calibrate_difficulty_ladders,
    estimate_difficulty,
    item_information,
    rasch_success_probability,
    verify_difficulty_calibration,
)


class V982InformationCalibrationTests(unittest.TestCase):
    def _calibration(self):
        return calibrate_difficulty_ladders({
            family: {
                "1": [1, 1, 1, 1],
                "2": [1, 0, 1, 0],
                "3": [0, 0, 0, 0],
            }
            for family in TASK_FAMILIES
        })

    def test_rasch_information_peaks_at_capability_boundary(self) -> None:
        self.assertEqual(rasch_success_probability(ability=0.0, difficulty=0.0), 0.5)
        self.assertEqual(item_information(ability=0.0, difficulty=0.0), 0.25)
        self.assertLess(item_information(ability=0.0, difficulty=4.0), 0.02)
        self.assertAlmostEqual(
            rasch_success_probability(ability=1.0, difficulty=2.0),
            1.0 - rasch_success_probability(ability=2.0, difficulty=1.0),
        )

    def test_difficulty_estimate_remains_finite_at_floor_and_ceiling(self) -> None:
        floor = estimate_difficulty([0, 0, 0, 0])
        ceiling = estimate_difficulty([1, 1, 1, 1])
        self.assertEqual(floor["state"], "estimated")
        self.assertGreater(floor["estimated_difficulty"], 0)
        self.assertLess(ceiling["estimated_difficulty"], 0)
        self.assertGreater(floor["item_information"], 0)

    def test_ladder_selects_information_boundary_not_easiest_level(self) -> None:
        receipt = self._calibration()
        self.assertEqual(receipt["overall_state"], "pass")
        self.assertEqual(set(receipt["selected"]), set(TASK_FAMILIES))
        self.assertTrue(all(row["difficulty_level"] == "2" for row in receipt["selected"].values()))
        self.assertTrue(verify_difficulty_calibration(receipt)["valid"])
        tampered = {**receipt, "overall_state": "held"}
        self.assertFalse(verify_difficulty_calibration(tampered)["valid"])
        injected = {**receipt, "model_id": "preferred-model"}
        material = {key: value for key, value in injected.items() if key != "calibration_hash"}
        injected["calibration_hash"] = hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertIn("model_provider_identity_forbidden", verify_difficulty_calibration(injected)["errors"])

    def test_all_ceiling_ladder_requests_more_difficulty(self) -> None:
        receipt = calibrate_difficulty_ladders({"family": {"1": [1, 1, 1, 1], "2": [1, 1, 1, 1]}})
        self.assertEqual(receipt["overall_state"], "held")
        self.assertEqual(receipt["families"]["family"]["recommended_action"], "increase_difficulty")

    def test_ladder_generation_is_deterministic_and_compositional(self) -> None:
        first = build_difficulty_ladder_corpus(seed="fixed", maximum_level=3, variants_per_level=2)
        second = build_difficulty_ladder_corpus(seed="fixed", maximum_level=3, variants_per_level=2)
        self.assertEqual(first, second)
        self.assertEqual(len(first["cases"]), len(TASK_FAMILIES) * 3 * 2)
        level_three = next(row for row in first["cases"] if row["difficulty_level"] == 3)
        self.assertEqual(len(level_three["component_case_ids"]), 3)
        self.assertEqual(level_three["expected_public_output"].count("|"), 2)

    def test_heldout_bundle_is_disjoint_sealed_and_answer_free_publicly(self) -> None:
        development = build_difficulty_ladder_corpus(seed="development", maximum_level=3, variants_per_level=2)
        bundle = build_held_out_bundle(self._calibration(), development, secret_seed="unpublished-seed", cases_per_family=3)
        manifest = bundle["manifest"]
        self.assertTrue(verify_held_out_bundle(bundle)["valid"])
        self.assertTrue(verify_held_out_manifest(manifest)["valid"])
        self.assertEqual(manifest["case_count"], len(TASK_FAMILIES) * 3)
        self.assertTrue(all("expected_public_output" not in row for row in manifest["cases"]))
        development_ids = {row["case_id"] for row in development["cases"]}
        self.assertFalse(development_ids & {row["case_id"] for row in manifest["cases"]})
        self.assertFalse(manifest["confirmatory_evidence"])
        self.assertFalse(manifest["authority"]["execution_authorized"])

        tampered = copy.deepcopy(bundle)
        tampered["manifest"]["cases"][0]["prompt"] += " changed"
        self.assertFalse(verify_held_out_bundle(tampered)["valid"])

    def test_caller_cannot_mark_unexecuted_manifest_as_evidence(self) -> None:
        development = build_difficulty_ladder_corpus(seed="development", maximum_level=3, variants_per_level=2)
        bundle = build_held_out_bundle(self._calibration(), development, secret_seed="unpublished-seed", cases_per_family=2)
        forged = {**bundle["manifest"], "confirmatory_evidence": True}
        self.assertFalse(verify_held_out_manifest(forged)["valid"])
        leaked = copy.deepcopy(bundle["manifest"])
        leaked["cases"][0]["answer"] = "caller supplied"
        public_material = {key: value for key, value in leaked.items() if key != "corpus_hash"}
        leaked["corpus_hash"] = hashlib.sha256(
            json.dumps(public_material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.assertIn("public_case_schema_not_closed", verify_held_out_manifest(leaked)["errors"])


if __name__ == "__main__":
    unittest.main()
