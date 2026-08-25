from __future__ import annotations

import copy
import hashlib
import json
import unittest

from cortex.calibration_commissioning import (
    OBSERVATION_SCHEMA,
    commission_calibration_panel,
    verify_calibration_commissioning,
)
from cortex.discriminative_forge import build_difficulty_ladder_corpus
from cortex.information_calibration import (
    assess_sequential_level,
    attainable_success_rates,
    eligible_success_counts,
)


def _sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class V983CalibrationCommissioningTests(unittest.TestCase):
    def _observation(self, case, index, success, evidence_class="live_empirical"):
        material = {
            "schema_version": OBSERVATION_SCHEMA,
            "version": "9.8.3",
            "repo": "fixture-repo",
            "case_id": case["case_id"],
            "family": case["family"],
            "difficulty_level": str(case["difficulty_level"]),
            "session_id": f"session-{index}",
            "turn_id": 1,
            "invocation_id": f"invocation-{index}",
            "invocation_receipt_hash": "a" * 64,
            "outcome_receipt_hash": "b" * 64,
            "witness_result_hash": "c" * 64,
            "evidence_class": evidence_class,
            "success": bool(success),
            "state": "observed",
            "errors": [],
            "development_only": True,
            "confirmatory_eligible": False,
            "private_chain_of_thought_stored": False,
            "authority": {
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "memory_admission_authorized": False,
                "policy_effect": False,
                "update_authorized": False,
            },
        }
        return {**material, "observation_hash": _sha(material)}

    def test_probability_lattice_makes_four_cases_screening_only(self):
        self.assertEqual(attainable_success_rates(4), [0.0, 0.25, 0.5, 0.75, 1.0])
        self.assertEqual(eligible_success_counts(4), [2])
        self.assertEqual(eligible_success_counts(8), [3, 4, 5])
        screen = assess_sequential_level([1, 1, 0, 0])
        self.assertEqual(screen["state"], "screening_candidate")
        self.assertFalse(screen["confirmatory_eligible"])
        confirmed = assess_sequential_level([1, 1, 1, 0, 0, 0, 0, 1])
        self.assertEqual(confirmed["state"], "calibrated")

    def test_empty_panel_is_honestly_not_executed(self):
        corpus = build_difficulty_ladder_corpus(maximum_level=2, variants_per_level=4)
        receipt = commission_calibration_panel(corpus=corpus, observations=[])
        self.assertEqual(receipt["status"], "CALIBRATION_NOT_EXECUTED")
        self.assertFalse(receipt["empirical_trial_executed"])
        self.assertTrue(verify_calibration_commissioning(receipt)["valid"])

    def test_eight_outcomes_have_a_real_confirmation_band(self):
        confirmed = assess_sequential_level([1, 1, 1, 0, 0, 0, 0, 1])
        self.assertEqual(confirmed["state"], "calibrated")
        self.assertEqual(confirmed["eligible_success_counts"], [3, 4, 5])

    def test_fixture_label_cannot_open_live_calibration(self):
        corpus = build_difficulty_ladder_corpus(maximum_level=1, variants_per_level=4)
        case = corpus["cases"][0]
        forged = self._observation(case, 1, True, evidence_class="synthetic_fixture")
        receipt = commission_calibration_panel(corpus=corpus, observations=[forged])
        self.assertEqual(receipt["status"], "CALIBRATION_NOT_EXECUTED")
        self.assertTrue(any("canonical_store_required" in error for error in receipt["errors"]))

    def test_duplicate_invocation_and_tampering_fail_closed(self):
        corpus = build_difficulty_ladder_corpus(maximum_level=1, variants_per_level=4)
        first, second = corpus["cases"][:2]
        one = self._observation(first, 1, True)
        two = self._observation(second, 1, False)
        two["invocation_id"] = one["invocation_id"]
        two_material = {key: value for key, value in two.items() if key != "observation_hash"}
        two["observation_hash"] = _sha(two_material)
        receipt = commission_calibration_panel(corpus=corpus, observations=[one, two])
        self.assertTrue(any("canonical_store_required" in error for error in receipt["errors"]))
        tampered = copy.deepcopy(receipt)
        tampered["protocol"]["model_identity_used_in_selection"] = True
        tampered_material = {key: value for key, value in tampered.items() if key != "commissioning_hash"}
        tampered["commissioning_hash"] = _sha(tampered_material)
        self.assertIn("model_identity_selection_forbidden", verify_calibration_commissioning(tampered)["errors"])


if __name__ == "__main__":
    unittest.main()
