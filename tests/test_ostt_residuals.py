"""v8.3.1 typed residual receipt and review-gate tests."""

from __future__ import annotations

import math
import unittest

from cortex.ostt import OperatorContract
from cortex.ostt.residuals import ResidualReceipt, residual_evidence_report


class OsttResidualTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = OperatorContract(
            "demo_operator",
            "Input",
            "Output",
            ("ready",),
            ("observed",),
            ("safe",),
        )

    def _receipt(
        self,
        *,
        mode: str = "ostt",
        witness: bool = True,
        invariant_ok: bool = True,
        input_type: str = "Input",
        output_type: str = "Output",
    ) -> ResidualReceipt:
        return ResidualReceipt.measure(
            operator_id="demo_operator",
            input_type=input_type,
            output_type=output_type,
            known_output=[1.0, 2.0],
            observed_output=[1.01, 2.01],
            uncertainty=0.1,
            uncertainty_calibrated=True,
            invariant_projection={"ok": invariant_ok, "projection": "safe"},
            validation={"independent_outcome": witness},
            epoch_id="epoch-1",
            cohort_id="cohort-1",
            independent_witness=witness,
            approximation_mode="exact",
            comparison_mode=mode,
        )

    def test_measurement_computes_bounded_burden_and_hash(self) -> None:
        receipt = self._receipt()
        self.assertEqual(receipt.status, "measured")
        self.assertAlmostEqual(receipt.residual_norm or 0.0, math.sqrt(0.0002), places=8)
        self.assertGreater(receipt.burden or 0.0, 0.0)
        self.assertLess(receipt.burden or 0.0, 1.0)
        self.assertFalse(receipt.validation_errors())
        payload = receipt.to_dict()
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["evidence_ready"])
        self.assertEqual(len(payload["receipt_hash"]), 64)

    def test_shape_mismatch_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            ResidualReceipt.measure(
                operator_id="demo_operator",
                input_type="Input",
                output_type="Output",
                known_output=[1.0, 2.0],
                observed_output=[1.0],
                uncertainty=0.1,
                uncertainty_calibrated=True,
                invariant_projection={"ok": True},
            )

    def test_unmeasured_receipt_is_safe_and_explicit(self) -> None:
        receipt = ResidualReceipt.unmeasured(
            operator_id="demo_operator",
            input_type="Input",
            output_type="Output",
        )
        self.assertFalse(receipt.evidence_ready)
        self.assertEqual(receipt.to_dict()["status"], "unmeasured")
        self.assertIn("typed_operator_output_not_recorded", receipt.to_dict()["reason"])

    def test_review_report_requires_all_declared_gates(self) -> None:
        report = residual_evidence_report(
            (self.contract,),
            [
                self._receipt(mode=mode)
                for mode in ("ostt", "black_box", "operator_only", "residual_only", "untyped")
            ],
        )
        self.assertEqual(report["status"], "ready_for_review")
        self.assertTrue(report["gates"]["typed_compatibility"])
        self.assertTrue(report["gates"]["comparison_matrix"])
        self.assertTrue(report["gates"]["independent_witness"])
        self.assertTrue(report["update_authorized"] is False)
        self.assertFalse(report["policy_effect"])

    def test_failure_injection_blocks_invariant_and_type_gate(self) -> None:
        invariant_report = residual_evidence_report(
            (self.contract,),
            [self._receipt(invariant_ok=False)]
            + [
                self._receipt(mode=mode)
                for mode in ("black_box", "operator_only", "residual_only", "untyped")
            ],
        )
        self.assertNotEqual(invariant_report["status"], "ready_for_review")
        self.assertFalse(invariant_report["gates"]["invariant_projection"])

        type_report = residual_evidence_report(
            (self.contract,),
            [
                self._receipt(
                    mode="ostt", input_type="WrongInput", output_type="WrongOutput"
                )
            ],
        )
        self.assertFalse(type_report["gates"]["typed_compatibility"])
        self.assertTrue(type_report["type_mismatches"])


if __name__ == "__main__":
    unittest.main()
