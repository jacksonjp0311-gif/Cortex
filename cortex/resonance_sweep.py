"""Bounded frequency-response sweep for the Resonant Frame field.

The sweep reads sealed frame metrics, centers each typed signal, and evaluates
phase-locked response at a small set of cycles-per-frame-window. It never
appends samples, changes cadence, seals an epoch, or changes routing policy.
"""

from __future__ import annotations

from hashlib import sha256
import json
import math
from pathlib import Path
from typing import Any, Sequence


SCHEMA = "cortex-resonance-frequency-sweep/1.0"
GLYPH = "∿"
VERSION = "8.2.5"
SIGNALS = (
    "mean_activity",
    "nonrandomness",
    "evidence_participation",
    "memory_participation",
    "transition_pressure",
    "participation_entropy",
)
DEFAULT_FREQUENCIES = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0)
CLAIM = (
    "Frequency sweep is read-only temporal telemetry. A spectral peak is an "
    "operational coordination signal, not consciousness, experience, authority, "
    "or permission to mutate host or runtime state."
)


def _frame_metrics(frame: Any) -> dict[str, Any]:
    if isinstance(frame, dict):
        return dict(frame.get("metrics") or frame.get("frame_vector") or {})
    return {}


def _series(frames: Sequence[Any], key: str) -> list[float]:
    values: list[float] = []
    for frame in frames:
        value = _frame_metrics(frame).get(key)
        try:
            if value is not None and math.isfinite(float(value)):
                values.append(float(value))
        except (TypeError, ValueError):
            continue
    return values


def score_frequency_field(
    frames: Sequence[Any],
    frequency: float,
    *,
    signals: Sequence[str] = SIGNALS,
) -> dict[str, Any]:
    """Score phase-locked response at one cycles-per-window frequency."""
    f = max(0.0, float(frequency))
    phasors: list[complex] = []
    amplitudes: list[float] = []
    signal_count = 0
    for key in signals:
        values = _series(frames, key)
        if len(values) < 4:
            continue
        mean = sum(values) / len(values)
        centered = [value - mean for value in values]
        scale = sum(abs(value) for value in centered)
        if scale <= 1e-12:
            continue
        n = len(centered)
        phasor = sum(
            value * complex(
                math.cos(-2.0 * math.pi * f * index / n),
                math.sin(-2.0 * math.pi * f * index / n),
            )
            for index, value in enumerate(centered)
        )
        phasors.append(phasor)
        amplitudes.append(min(1.0, abs(phasor) / scale))
        signal_count += 1
    if not phasors:
        return {
            "frequency": round(f, 6),
            "cycle_period_frames": None,
            "signal_count": 0,
            "response": 0.0,
            "phase_lock": 0.0,
            "coherence": 0.0,
        }
    unit_phasors = [phasor / abs(phasor) for phasor in phasors if abs(phasor) > 1e-12]
    phase_lock = abs(sum(unit_phasors)) / max(1, len(unit_phasors))
    response = sum(amplitudes) / max(1, len(amplitudes))
    coherence = 0.5 * response + 0.5 * phase_lock
    return {
        "frequency": round(f, 6),
        "cycle_period_frames": round(1.0 / f, 6) if f > 0.0 else None,
        "signal_count": signal_count,
        "response": round(response, 8),
        "phase_lock": round(phase_lock, 8),
        "coherence": round(coherence, 8),
    }


def frequency_sweep_report(
    frames: Sequence[Any],
    *,
    frequencies: Sequence[float] = DEFAULT_FREQUENCIES,
    minimum_frames: int = 16,
) -> dict[str, Any]:
    """Return a bounded sweep and an advisory peak recommendation."""
    frame_count = len(frames)
    scores = [score_frequency_field(frames, frequency) for frequency in frequencies]
    scores.sort(key=lambda item: (-float(item["coherence"]), float(item["frequency"])))
    best = scores[0] if scores else None
    second = scores[1] if len(scores) > 1 else None
    best_coherence = float((best or {}).get("coherence") or 0.0)
    second_coherence = float((second or {}).get("coherence") or 0.0)
    peak_delta = best_coherence - second_coherence
    ready = bool(
        frame_count >= max(4, int(minimum_frames))
        and best
        and best_coherence >= 0.25
        and peak_delta >= 0.03
    )
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": VERSION,
        "frame_count": frame_count,
        "signals": list(SIGNALS),
        "frequency_grid": [float(value) for value in frequencies],
        "scores": scores,
        "best": best,
        "peak_delta": round(peak_delta, 8),
        "status": "resonant_candidate" if ready else "no_stable_peak",
        "recommendation": (
            "observe_candidate_frequency_without_changing_cadence"
            if ready
            else "hold_cadence_and_collect_more_same_epoch_frames"
        ),
        "advisory_only": True,
        "policy_effect": False,
        "claim_boundary": CLAIM,
    }


def run_frequency_sweep(
    store: Any,
    repo: str,
    *,
    home: Path | None = None,
    frequencies: Sequence[float] = DEFAULT_FREQUENCIES,
    minimum_frames: int = 16,
    persist: bool = False,
) -> dict[str, Any]:
    """Sweep sealed field frames for one repository; optionally cache telemetry."""
    index = list(store.get_setting(f"field_frame_index:{repo}", []) or [])
    all_frames = [
        store.get_setting(f"field_frame:{repo}:{frame_id}", {}) or {}
        for frame_id in index
    ]
    latest_epoch = ""
    for frame in reversed(all_frames):
        if frame.get("body_epoch_id"):
            latest_epoch = str(frame["body_epoch_id"])
            break
    frames = [
        frame for frame in all_frames
        if not latest_epoch or str(frame.get("body_epoch_id") or "") == latest_epoch
    ]
    report = frequency_sweep_report(
        frames,
        frequencies=frequencies,
        minimum_frames=minimum_frames,
    )
    report["repo"] = repo
    report["all_frame_count"] = len(all_frames)
    report["body_epoch_id"] = latest_epoch or None
    report["body_epoch_ids"] = sorted({
        str(frame.get("body_epoch_id")) for frame in all_frames if frame.get("body_epoch_id")
    })
    report["frame_index_hash"] = sha256(
        "|".join(str(frame_id) for frame_id in index).encode("utf-8")
    ).hexdigest()
    if persist:
        store.set_setting(f"resonance_sweep_latest:{repo}", report)
        if home is not None:
            log_dir = Path(home) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / f"resonance-sweep-{repo}.json"
            path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            report["report_path"] = str(path)
    return report


__all__ = [
    "CLAIM", "DEFAULT_FREQUENCIES", "GLYPH", "SCHEMA", "VERSION",
    "frequency_sweep_report", "run_frequency_sweep", "score_frequency_field",
]
