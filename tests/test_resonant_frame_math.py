"""v7.3 Resonant Frame mathematics — deterministic, epsilon-safe."""

from __future__ import annotations

import math
import unittest

from cortex.field_channels import CHANNEL_FAMILIES, sample_tick_channels
from cortex.resonant_frame import (
    FrameClassification,
    FrameThresholds,
    classify_frame,
    close_resonant_frame,
    compute_frame_metrics,
    differentiation_common_mode,
    jsd_normalized,
    lagged_pair_stats,
    operational_nonrandomness,
    pearson,
)


def _synth(
    ticks: int = 12,
    *,
    mode: str = "coherent",
    epoch: str = "e1",
) -> list:
    samples = []
    for t in range(ticks):
        acts = {}
        truths = {}
        paths = {}
        for i, fam in enumerate(CHANNEL_FAMILIES):
            if mode == "quiescent":
                acts[fam] = 0.02
            elif mode == "fragmented":
                acts[fam] = 0.6 if i % 2 == (t % 2) else 0.05
            elif mode == "overbound":
                # all channels identical → high common mode
                acts[fam] = 0.3 + 0.4 * math.sin(t / 2.0)
            else:
                # coherent differentiated: shared + unique component
                shared = 0.4 + 0.3 * math.sin(t / 3.0)
                uniq = 0.2 * math.sin((t + i) / 2.5)
                acts[fam] = max(0.05, min(1.0, shared + uniq))
            if fam in {"E_HOST", "E_RUNTIME"}:
                truths[fam] = "MEASURED"
                paths[fam] = [f"src/mod{i % 3}.py"]
            elif fam.startswith("M_"):
                truths[fam] = "INFERRED"
                paths[fam] = [f"src/mod{i % 3}.py"]
            else:
                truths[fam] = "MEASURED"
        samples.extend(
            sample_tick_channels(
                repo="R",
                body_epoch_id=epoch,
                tick=t,
                activities=acts,
                truth_sources=truths,
                paths_by_channel=paths,
                reliabilities={f: 0.9 for f in CHANNEL_FAMILIES},
            )
        )
    return samples


class ResonantMathTests(unittest.TestCase):
    def test_jsd_bounds(self) -> None:
        p = {"a": 1.0}
        q = {"a": 1.0}
        self.assertAlmostEqual(jsd_normalized(p, q), 0.0, places=6)
        r = {"b": 1.0}
        v = jsd_normalized(p, r)
        self.assertGreater(v, 0.9)
        self.assertLessEqual(v, 1.0)

    def test_pearson_perfect(self) -> None:
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertAlmostEqual(pearson(a, a) or 0, 1.0, places=6)
        b = [-x for x in a]
        self.assertAlmostEqual(pearson(a, b) or 0, -1.0, places=6)

    def test_lag_tiebreak_deterministic(self) -> None:
        series = {
            "A": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            "B": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
        }
        rel = {"A": 1.0, "B": 1.0}
        p1 = lagged_pair_stats(series, rel, l_max=3)
        p2 = lagged_pair_stats(series, rel, l_max=3)
        self.assertEqual(p1, p2)
        self.assertEqual(p1[0]["lag"], 0)

    def test_differentiation_common_mode(self) -> None:
        # identical series → D low, M high
        row = [0.1 * i for i in range(10)]
        series = {f"C{i}": list(row) for i in range(4)}
        d, m, k = differentiation_common_mode(series)
        self.assertEqual(k, 4)
        self.assertIsNotNone(d)
        self.assertIsNotNone(m)
        self.assertGreater(float(m), 0.9)
        self.assertLess(float(d), 0.3)

    def test_nonrandomness_null_without_baseline(self) -> None:
        samples = _synth(10)
        m, _, warm = compute_frame_metrics(samples, baseline_dist={})
        self.assertIsNone(m.nonrandomness)
        self.assertFalse(warm)

    def test_nonrandomness_with_baseline(self) -> None:
        samples = _synth(10)
        # baseline different distribution
        base = {
            fam: {"default|0": 1.0}
            for fam in CHANNEL_FAMILIES
        }
        n = operational_nonrandomness(
            {fam: {"default|4": 1.0} for fam in CHANNEL_FAMILIES},
            base,
            {fam: 1.0 for fam in CHANNEL_FAMILIES},
        )
        self.assertIsNotNone(n)
        self.assertGreater(n or 0, 0.0)

    def test_channel_order_stability(self) -> None:
        s1 = _synth(10)
        s2 = list(reversed(s1))
        # rebuild same by re-sorting inside compute
        m1, _, _ = compute_frame_metrics(s1, epoch_current=True)
        m2, _, _ = compute_frame_metrics(s2, epoch_current=True)
        self.assertEqual(m1.integration, m2.integration)
        self.assertEqual(m1.differentiation, m2.differentiation)

    def test_close_frame_identity(self) -> None:
        samples = _synth(10)
        f1 = close_resonant_frame(samples, repo="R", body_epoch_id="e1")
        f2 = close_resonant_frame(samples, repo="R", body_epoch_id="e1")
        self.assertEqual(f1.frame_id, f2.frame_id)
        self.assertTrue(f1.frame_id.startswith("frame_"))

    def test_classify_indeterminate_short(self) -> None:
        samples = _synth(4)
        m, _, warm = compute_frame_metrics(samples)
        c, reasons = classify_frame(m, thresholds=FrameThresholds(), baseline_warm=warm)
        self.assertEqual(c, FrameClassification.INDETERMINATE.value)
        self.assertTrue(any("W_min" in r or "W <" in r for r in reasons))

    def test_classify_quiescent(self) -> None:
        samples = _synth(12, mode="quiescent")
        m, _, warm = compute_frame_metrics(
            samples, baseline_dist={f: {"x|0": 1.0} for f in CHANNEL_FAMILIES}
        )
        # force low activity path
        m.mean_activity = 0.02
        m.nonrandomness = 0.1
        m.eligible_channel_count = 5
        m.tick_count = 12
        m.integration = 0.5
        m.differentiation = 0.5
        m.common_mode = 0.5
        m.participation_entropy = 0.5
        m.giant_component_fraction = 0.5
        m.evidence_participation = 0.1
        m.memory_participation = 0.1
        m.transition_pressure = 0.1
        c, _ = classify_frame(m, thresholds=FrameThresholds(), baseline_warm=True)
        self.assertEqual(c, FrameClassification.QUIESCENT.value)


if __name__ == "__main__":
    unittest.main()
