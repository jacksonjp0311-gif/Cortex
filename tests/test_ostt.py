"""Tests for the shadow-only OSTT compatibility layer."""

from __future__ import annotations

import unittest

from cortex.ostt import CORE_CONTRACTS, OperatorContract, TypedState, audit_runtime


class OsttContractTests(unittest.TestCase):
    def test_typed_state_serializes_and_validates(self) -> None:
        state = TypedState(
            "EvidenceIndex",
            provenance="manifest:abc",
            uncertainty=0.2,
            metadata={"files": 3},
        )
        self.assertEqual(state.validate(), [])
        payload = state.to_dict()
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["type_id"], "EvidenceIndex")

        invalid = TypedState("", uncertainty=1.2)
        self.assertIn("type_id_missing", invalid.validate())
        self.assertIn("uncertainty_out_of_range", invalid.validate())
        self.assertIn("provenance_missing", invalid.validate())
        self.assertIn(
            "uncertainty_out_of_range",
            TypedState("EvidenceIndex", provenance="x", uncertainty="unknown").validate(),
        )

    def test_contract_holds_on_domain_and_precondition_gaps(self) -> None:
        contract = OperatorContract(
            "demo", "Input", "Output", ("ready",), ("done",), ("safe",)
        )
        trace = contract.evaluate(state_type="Wrong", facts={"ready": False})
        self.assertFalse(trace.admissible)
        self.assertIn("domain_mismatch:Wrong->Input", trace.missing_preconditions)
        self.assertIn("ready", trace.missing_preconditions)
        self.assertEqual(len(CORE_CONTRACTS), 6)

    def test_audit_is_advisory_and_surfaces_residuals(self) -> None:
        report = audit_runtime(
            {
                "manifest_current": True,
                "certificate_status": "verified",
                "epoch_verified": True,
                "phase_bound": True,
                "immune_block": False,
                "evidence_valid": False,
                "same_epoch_frames": 4,
                "resonance_status": "no_stable_peak",
                "self_sensing_classification": "STRESSED",
                "binding_classification": "DRIFT_REGIME",
                "interlock": {
                    "cohort_current": False,
                    "data_ready": False,
                    "promotion_gates": {
                        "witness_gate": False,
                        "eligible": False,
                    },
                    "readiness": {"next_actions": ["collect_frames"]},
                },
            }
        )
        self.assertTrue(report["advisory_only"])
        self.assertFalse(report["policy_effect"])
        self.assertEqual(report["operator_count"], 6)
        self.assertGreater(report["held_count"], 0)
        self.assertIn("observer_regime_residual", report["residuals"]["unresolved"])
        self.assertIn("temporal_resonance_residual", report["residuals"]["unresolved"])
        self.assertIn("outcome_evidence_residual", report["residuals"]["unresolved"])
        self.assertEqual(report["residual_evidence"]["status"], "unmeasured")
        self.assertFalse(report["residual_evidence"]["policy_effect"])

    def test_audit_can_admit_all_declared_boundaries(self) -> None:
        report = audit_runtime(
            {
                "manifest_current": True,
                "certificate_status": "verified",
                "epoch_verified": True,
                "phase_bound": True,
                "immune_block": False,
                "evidence_valid": True,
                "same_epoch_frames": 16,
                "resonance_status": "stable_peak",
                "self_sensing_classification": "NOMINAL",
                "binding_classification": "BOUND",
                "interlock": {
                    "cohort_current": True,
                    "data_ready": True,
                    "promotion_gates": {
                        "witness_gate": True,
                        "eligible": True,
                    },
                },
            }
        )
        self.assertEqual(report["held_count"], 0)
        self.assertEqual(report["admissible_count"], 6)
        self.assertFalse(report["policy_effect"])
        self.assertEqual(report["residual_evidence"]["measured_count"], 0)


if __name__ == "__main__":
    unittest.main()
