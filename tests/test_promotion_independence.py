"""Coupling cannot alone certify promotion; witness optional block."""

from __future__ import annotations

import unittest

from cortex.promote_gate import evaluate_promotion


class PromotionIndependenceTests(unittest.TestCase):
    def test_coupling_on_without_holdout_denies(self) -> None:
        r = evaluate_promotion(
            holdout_report={
                "winner": "baseline",
                "gate": {"baseline_is_winner": True},
                "ablations": {"baseline": {"recall_at_k": 0.2}},
            },
            foreign_report={
                "repo": "Other",
                "ablations": {"baseline": {"recall_at_k": 0.9}},
            },
            emergent_coupling=True,
            governance_mode="normal",
        )
        self.assertFalse(r["allow_promote"])
        self.assertEqual(r.get("coupling_role"), "safety_prerequisite_only")

    def test_critical_wound_blocks(self) -> None:
        r = evaluate_promotion(
            holdout_report={
                "winner": "baseline",
                "gate": {
                    "baseline_is_winner": True,
                    "advanced_beats_evidence_baseline": True,
                },
                "ablations": {"baseline": {"recall_at_k": 1.0}},
            },
            foreign_report={
                "repo": "Other",
                "ablations": {"baseline": {"recall_at_k": 0.8}},
            },
            emergent_coupling=True,
            governance_mode="normal",
            has_critical_wound=True,
        )
        self.assertFalse(r["allow_promote"])
        self.assertIn("active_critical_wound", r["reasons_if_denied"])

    def test_require_witness(self) -> None:
        r = evaluate_promotion(
            holdout_report={
                "winner": "baseline",
                "gate": {
                    "baseline_is_winner": True,
                    "advanced_beats_evidence_baseline": True,
                },
                "ablations": {"baseline": {"recall_at_k": 1.0}},
            },
            foreign_report={
                "repo": "Other",
                "ablations": {"baseline": {"recall_at_k": 0.8}},
            },
            emergent_coupling=True,
            governance_mode="normal",
            require_witness=True,
            witness_report=None,
        )
        self.assertFalse(r["allow_promote"])


if __name__ == "__main__":
    unittest.main()
