"""v7.1 illegal diagonal detection."""

from __future__ import annotations

import unittest

from cortex.constitutional_geometry import coordinate_from_bits
from cortex.constitutional_transition import assess_transition
from cortex.diagonal import detect_diagonal, explain_diagonal


class ForbiddenDiagonalTests(unittest.TestCase):
    def test_stale_witness_after_epoch_change(self) -> None:
        src = coordinate_from_bits((1, 1, 0, 1))
        dst = coordinate_from_bits((1, 1, 1, 1))
        d = detect_diagonal(
            src,
            dst,
            context={"witness_survives_adaptive_root": True},
        )
        self.assertFalse(d["allowed"])
        self.assertIn("witness", d["reason"] + "".join(d.get("changed_axes") or []))
        self.assertTrue(d["required_steps"])

    def test_old_capability_after_incompatible_epoch(self) -> None:
        d = detect_diagonal(
            (1, 1, 0, 0),
            (1, 1, 1, 0),
            context={"capability_survives_epoch": True},
        )
        self.assertFalse(d["allowed"])
        self.assertEqual(d["reason"], "stale_authority_carryover")
        self.assertIn("revoke_old_capability", d["required_steps"])

    def test_learned_cannot_become_evidence_directly(self) -> None:
        d = detect_diagonal(
            (0, 1, 1, 0),
            (1, 1, 1, 0),
            context={"learned_promoted_as_evidence": True},
        )
        self.assertFalse(d["allowed"])
        self.assertIn("learned", d["reason"])

    def test_foreign_cannot_gain_local_authority(self) -> None:
        d = detect_diagonal(
            (1, 0, 1, 0),
            (1, 1, 1, 0),
            context={"foreign_local_authority": True},
        )
        self.assertFalse(d["allowed"])
        self.assertIn("foreign", d["reason"])

    def test_compound_requires_internal_steps(self) -> None:
        src = coordinate_from_bits((1, 1, 1, 0))
        dst = coordinate_from_bits((1, 1, 1, 1))
        # multi-axis free diagonal denied
        multi = assess_transition(
            "promote",
            coordinate_from_bits((0, 0, 0, 0)),
            coordinate_from_bits((1, 1, 1, 1)),
            compound=False,
        )
        self.assertFalse(multi.allowed)
        self.assertTrue(multi.diagonal)
        # compound with steps allowed
        ok = assess_transition(
            "promote",
            coordinate_from_bits((0, 0, 0, 0)),
            coordinate_from_bits((1, 1, 1, 1)),
            compound=True,
            compound_steps=(
                "VERIFY_EVIDENCE",
                "ISSUE_CAPABILITY",
                "VERIFY_EPOCH",
                "COMMIT_WITNESS",
            ),
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.diagonal)
        self.assertEqual(len(ok.required_steps), 4)

    def test_promotion_without_witness_flag(self) -> None:
        d = detect_diagonal(
            (1, 1, 1, 0),
            (1, 1, 1, 0),
            operation="promote",
            context={"promote_without_witness": True},
        )
        self.assertFalse(d["allowed"])
        self.assertTrue(explain_diagonal(d))


if __name__ == "__main__":
    unittest.main()
