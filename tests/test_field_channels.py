"""v7.3 field channel contracts."""

from __future__ import annotations

import unittest

from cortex.field_channels import (
    CHANNEL_FAMILIES,
    K_MAX,
    K_MIN,
    ChannelTruthSource,
    FieldSample,
    assert_k_bounds,
    is_verified_evidence_truth,
    sample_tick_channels,
)


class FieldChannelTests(unittest.TestCase):
    def test_k_bounds(self) -> None:
        self.assertGreaterEqual(len(CHANNEL_FAMILIES), K_MIN)
        self.assertLessEqual(len(CHANNEL_FAMILIES), K_MAX)
        assert_k_bounds(list(CHANNEL_FAMILIES))
        with self.assertRaises(ValueError):
            assert_k_bounds(["A"] * 3)

    def test_verified_truth_only(self) -> None:
        self.assertTrue(is_verified_evidence_truth(ChannelTruthSource.MEASURED))
        self.assertTrue(is_verified_evidence_truth("RECEIPT_VERIFIED"))
        self.assertFalse(is_verified_evidence_truth(ChannelTruthSource.SIMULATED))
        self.assertFalse(is_verified_evidence_truth(ChannelTruthSource.INFERRED))
        self.assertFalse(is_verified_evidence_truth(ChannelTruthSource.OPERATOR_ASSERTED))

    def test_sample_clips_and_truth(self) -> None:
        s = FieldSample(
            repo="R",
            body_epoch_id="e",
            tick=1,
            timestamp=0.0,
            channel_id="E_HOST",
            channel_family="E_HOST",
            activity=2.5,
            reliability=-1.0,
            truth_source="measured",
        )
        self.assertEqual(s.activity, 1.0)
        self.assertEqual(s.reliability, 0.0)
        self.assertEqual(s.truth_source, "MEASURED")
        self.assertTrue(s.is_verified_evidence)

    def test_tick_sample_count(self) -> None:
        samples = sample_tick_channels(
            repo="R",
            body_epoch_id="e",
            tick=0,
            activities={f: 0.5 for f in CHANNEL_FAMILIES},
        )
        self.assertEqual(len(samples), len(CHANNEL_FAMILIES))
        # deterministic order
        self.assertEqual([s.channel_family for s in samples], sorted(CHANNEL_FAMILIES))

    def test_baseline_warmup_display(self) -> None:
        from cortex.resonant_frame import baseline_warmup_status

        w = baseline_warmup_status({"frames_seen": 3, "distributions": {"E_HOST": {"a": 1.0}}})
        self.assertEqual(w["baseline_frames_display"], "3/16")
        self.assertTrue(w["baseline_warming"])
        self.assertFalse(w["baseline_ready"])
        self.assertIn("3/16", w["baseline_message"])


if __name__ == "__main__":
    unittest.main()
