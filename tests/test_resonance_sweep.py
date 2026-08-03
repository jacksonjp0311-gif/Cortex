"""Read-only frequency response sweep tests."""

from __future__ import annotations

import math

from cortex.resonance_sweep import frequency_sweep_report, run_frequency_sweep, score_frequency_field


def _frames(n: int = 32) -> list[dict[str, object]]:
    return [
        {
            "metrics": {
                "mean_activity": 0.5 + 0.4 * math.sin(2 * math.pi * i / n),
                "nonrandomness": 0.5 + 0.3 * math.sin(2 * math.pi * i / n),
                "evidence_participation": 0.4 + 0.2 * math.sin(2 * math.pi * i / n),
                "memory_participation": 0.4 + 0.2 * math.sin(2 * math.pi * i / n),
                "transition_pressure": 0.5 + 0.2 * math.sin(2 * math.pi * i / n),
                "participation_entropy": 0.5 + 0.1 * math.sin(2 * math.pi * i / n),
            }
        }
        for i in range(n)
    ]


def test_frequency_score_finds_one_cycle_per_window() -> None:
    frames = _frames()
    one = score_frequency_field(frames, 1.0)
    half = score_frequency_field(frames, 0.5)
    assert one["coherence"] > half["coherence"]
    assert one["signal_count"] == 6


def test_sweep_is_advisory_and_requires_peak() -> None:
    report = frequency_sweep_report(_frames(), frequencies=(0.5, 1.0, 2.0))
    assert report["status"] == "resonant_candidate"
    assert report["best"]["frequency"] == 1.0
    assert report["advisory_only"] is True
    assert report["policy_effect"] is False


def test_flat_field_holds_cadence() -> None:
    frames = [{"metrics": {"mean_activity": 0.5}} for _ in range(32)]
    report = frequency_sweep_report(frames)
    assert report["status"] == "no_stable_peak"
    assert report["recommendation"] == "hold_cadence_and_collect_more_same_epoch_frames"


def test_run_sweep_excludes_cross_epoch_frames() -> None:
    frames = _frames(16)
    frames = [
        {**frame, "body_epoch_id": "old"} for frame in frames[:8]
    ] + [
        {**frame, "body_epoch_id": "latest"} for frame in frames[8:]
    ]

    class FakeStore:
        def get_setting(self, key: str, default: object = None) -> object:
            if key == "field_frame_index:R":
                return [str(index) for index in range(len(frames))]
            if key.startswith("field_frame:R:"):
                return frames[int(key.rsplit(":", 1)[-1])]
            return default

    report = run_frequency_sweep(FakeStore(), "R", persist=False)
    assert report["all_frame_count"] == 16
    assert report["frame_count"] == 8
    assert report["body_epoch_id"] == "latest"
