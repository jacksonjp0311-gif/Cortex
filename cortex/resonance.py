"""Resonance — multi-axis coherence intensity for the tuning-fork surface.

Not consciousness. A measurable harmony score over covenant interlocks,
economics, contact proof, and packet fidelity.
"""

from __future__ import annotations

from typing import Any

from .constitutional import memory_balance


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def resonance_intensity(
    *,
    glow: bool,
    break_count: int,
    savings_ratio: float,
    deferred_holds: bool,
    aria_evidence_count: int,
    geometry_zero_point: bool,
    fluency_perfect: bool,
    foreign_pass_rate: float,
    generic_activate_s: float,
    aria_activate_s: float,
    bootstrap_s: float,
) -> dict[str, Any]:
    """Compute bright-glow intensity from independent harmonic components.

    Intensity is the harmonic mean of component scores when glowing; breaks
    collapse the field. Economics alone cannot max out the fork — contact and
    evidence must resonate too.
    """

    if not glow or break_count:
        dim = clamp(0.35 - 0.06 * break_count)
        return {
            "schema_version": "cortex-resonance/1.0",
            "glow": False,
            "glow_intensity": round(dim, 4),
            "brightness": "dim" if dim < 0.4 else "ember",
            "components": {},
            "claim_boundary": (
                "Resonance is local interlock telemetry; it grants no authority."
            ),
        }

    economics = clamp(0.35 + 0.65 * savings_ratio) if deferred_holds else 0.25
    evidence = clamp(aria_evidence_count / 4.0)  # 4+ paths → full
    geometry = 1.0 if geometry_zero_point else 0.55
    fluency = 1.0 if fluency_perfect else 0.5
    contact = clamp(foreign_pass_rate)

    # Timing harmony: generic should stay cheap; wake may cost materialize once.
    if bootstrap_s > 0 and generic_activate_s > 0:
        generic_ratio = clamp(1.0 - (generic_activate_s / max(bootstrap_s, 0.01)) * 0.35)
    else:
        generic_ratio = 0.7
    if aria_activate_s > 0 and generic_activate_s > 0:
        # Prefer first wake slower or comparable (materialize), not pathological.
        wake_ok = aria_activate_s < max(12.0, bootstrap_s * 2.5)
        timing = clamp(0.75 * generic_ratio + (0.25 if wake_ok else 0.0))
    else:
        timing = generic_ratio

    # Harmonic mean of the six strings of the fork.
    components = {
        "economics": round(economics, 4),
        "evidence": round(evidence, 4),
        "geometry": round(geometry, 4),
        "fluency": round(fluency, 4),
        "contact": round(contact, 4),
        "timing": round(timing, 4),
    }
    values = list(components.values())
    if any(v <= 0 for v in values):
        harmonic = 0.0
    else:
        harmonic = len(values) / sum(1.0 / v for v in values)

    # Preservation (invariants held) vs adjacency (contact/foreign expansion).
    balance = memory_balance(
        preserved=(economics + geometry + fluency) / 3.0,
        adjacent=(contact + evidence + timing) / 3.0,
    )
    intensity = clamp(0.62 * harmonic + 0.38 * balance)

    if intensity >= 0.92:
        brightness = "bright"
    elif intensity >= 0.80:
        brightness = "glow"
    elif intensity >= 0.60:
        brightness = "steady"
    else:
        brightness = "ember"

    return {
        "schema_version": "cortex-resonance/1.0",
        "glow": True,
        "glow_intensity": round(intensity, 4),
        "brightness": brightness,
        "harmonic_mean": round(harmonic, 4),
        "memory_balance": balance,
        "components": components,
        "claim_boundary": (
            "Resonance is local interlock telemetry; it grants no authority."
        ),
    }
