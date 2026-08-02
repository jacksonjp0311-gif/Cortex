"""v7.3 advisory field policy."""

from __future__ import annotations

import unittest

from cortex.field_policy import apply_field_policy_advisory, policy_for_classification


class FieldPolicyTests(unittest.TestCase):
    def test_advisory_only_always(self) -> None:
        for c in (
            "QUIESCENT",
            "TRANSITION",
            "STALE_ECHO",
            "OVERBOUND",
            "FRAGMENTED",
            "COHERENT_DIFFERENTIATED",
            "INDETERMINATE",
        ):
            p = policy_for_classification(c)
            self.assertTrue(p.advisory_only)
            d = p.to_dict()
            self.assertTrue(d["advisory_only"])

    def test_gcmt_map(self) -> None:
        self.assertEqual(
            policy_for_classification("STALE_ECHO").recommended_gcmt_regime, "evidence"
        )
        self.assertEqual(
            policy_for_classification("COHERENT_DIFFERENTIATED").recommended_gcmt_regime,
            "local",
        )
        self.assertEqual(
            policy_for_classification("INDETERMINATE").recommended_gcmt_regime, "abstain"
        )

    def test_stale_disables_learned_rerank(self) -> None:
        p = policy_for_classification("STALE_ECHO")
        self.assertTrue(p.disable_learned_rerank_once)
        self.assertTrue(p.prefer_evidence)

    def test_shadow_not_applied(self) -> None:
        p = policy_for_classification("FRAGMENTED")
        ctx = apply_field_policy_advisory({}, p, advisory_mode=False)
        self.assertFalse(ctx.get("field_policy_applied"))
        self.assertIn("resonant_frame_policy", ctx)

    def test_advisory_applied(self) -> None:
        p = policy_for_classification("FRAGMENTED")
        ctx = apply_field_policy_advisory({}, p, advisory_mode=True)
        self.assertTrue(ctx.get("field_policy_applied"))
        self.assertEqual(ctx.get("retrieval_width_delta"), 2)

    def test_modeled_measurement_cannot_influence_policy(self) -> None:
        p = policy_for_classification("FRAGMENTED").to_dict()
        p["policy_eligible"] = False
        ctx = apply_field_policy_advisory({}, p, advisory_mode=True)
        self.assertFalse(ctx.get("field_policy_applied"))
        self.assertIn("modeled", ctx.get("field_policy_note", ""))


if __name__ == "__main__":
    unittest.main()
