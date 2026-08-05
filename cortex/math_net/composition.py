"""Noncompensatory composition law shared across Cortex measurement domains.

This module does not invent a new equation of cognition.  It freezes the
composition rule already used by query bridges, source admission, and the
evidence–learning–outcome interlock so no domain can silently compensate for a
missing essential factor.

The general form is:

    Φ = Γ · (∏ x_i^{w_i}) · (∏ (1 − d_j))

with ∑ w_i = 1, x_i ∈ [0,1], d_j ∈ [0,1], and Γ ∈ {0,1}.

When Γ = 1 this is equivalent to the additive defect potential:

    𝒟 = ∑ w_i (−log x_i) + ∑ (−log(1 − d_j)),  Φ = e^{−𝒟}

Interpretation:
* Γ decides admissibility (hard gate);
* x_i are necessary positive contributions;
* d_j are defect / concentration penalties;
* geometric composition prevents one excellent dimension from fully compensating
  for a missing essential dimension.

Φ is not a calibrated probability unless each factor is separately calibrated
and the dependency structure is established.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "cortex-noncompensatory-composition/1.0"
EPSILON = 1e-12


def _clip01(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def geometric_mean(
    factors: Mapping[str, Any] | Sequence[tuple[str, Any]],
    weights: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Weighted geometric mean of factors in [0, 1]."""
    if isinstance(factors, Mapping):
        items = [(str(name), factors[name]) for name in factors]
    else:
        items = [(str(name), value) for name, value in factors]
    if not items:
        return {
            "value": 0.0,
            "factors": {},
            "weights": {},
            "log_defect": None,
            "missing": True,
        }
    if weights is None:
        weight_map = {name: 1.0 / len(items) for name, _ in items}
    else:
        raw = {name: max(0.0, float(weights.get(name, 0.0))) for name, _ in items}
        total = sum(raw.values())
        weight_map = (
            {name: value / total for name, value in raw.items()}
            if total > 0.0
            else {name: 1.0 / len(items) for name, _ in items}
        )
    clipped = {name: _clip01(value) for name, value in items}
    # A zero essential factor collapses the geometric mean exactly.  Soft
    # flooring would let a missing dimension impersonate a tiny positive score.
    if any(value <= 0.0 for value in clipped.values()):
        return {
            "value": 0.0,
            "factors": clipped,
            "weights": weight_map,
            "log_defect": float("inf"),
            "missing": False,
            "collapsed": True,
        }
    log_sum = 0.0
    for name, value in clipped.items():
        log_sum += weight_map[name] * (-math.log(value))
    value = math.exp(-log_sum)
    return {
        "value": value,
        "factors": clipped,
        "weights": weight_map,
        "log_defect": log_sum,
        "missing": False,
        "collapsed": False,
    }


def noncompensatory_compose(
    *,
    gate: Any = 1,
    factors: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None,
    weights: Mapping[str, float] | None = None,
    defects: Mapping[str, Any] | Sequence[tuple[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate Φ = Γ · (∏ x_i^{w_i}) · (∏ (1 − d_j))."""
    gamma = 1 if bool(gate) else 0
    mean = geometric_mean(factors or {}, weights=weights)
    if isinstance(defects, Mapping):
        defect_items = [(str(name), defects[name]) for name in defects]
    elif defects is None:
        defect_items = []
    else:
        defect_items = [(str(name), value) for name, value in defects]
    defect_map = {name: _clip01(value) for name, value in defect_items}
    survival = 1.0
    defect_log = 0.0
    for value in defect_map.values():
        term = max(0.0, 1.0 - value)
        survival *= term
        defect_log += -math.log(max(term, EPSILON))
    phi = float(gamma) * float(mean["value"]) * survival
    total_defect = None if mean["missing"] and not defect_map else (
        float(mean["log_defect"] or 0.0) + defect_log
    )
    return {
        "schema_version": SCHEMA,
        "gate": gamma,
        "factors": mean["factors"],
        "weights": mean["weights"],
        "geometric_mean": mean["value"],
        "defects": defect_map,
        "defect_survival": survival,
        "phi": phi,
        "defect_potential": total_defect,
        "admissible": gamma == 1 and phi > 0.0,
        "claim_boundary": (
            "Noncompensatory composition is a measurement gate, not a probability "
            "and not an authorization signal."
        ),
    }


def typed_residual_energy(
    residuals: Mapping[str, Any],
    *,
    metrics: Mapping[str, Mapping[str, float]] | None = None,
) -> dict[str, Any]:
    """Block-diagonal diagnostic energy over a typed residual bundle.

    residuals maps residual type → scalar or vector.  Types are never added
    across domains unless an explicit metric block is supplied.  The returned
    energy is diagnostic only and must not become authority.
    """
    blocks: dict[str, float] = {}
    for name, value in residuals.items():
        key = str(name)
        metric = (metrics or {}).get(key) or {}
        scale = float(metric.get("scale", 1.0) or 1.0)
        if isinstance(value, Mapping):
            squares = []
            for item in value.values():
                try:
                    number = float(item)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(number):
                    squares.append(number * number)
            energy = sum(squares) / max(scale * scale, EPSILON)
        elif isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            squares = []
            for item in value:
                try:
                    number = float(item)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(number):
                    squares.append(number * number)
            energy = sum(squares) / max(scale * scale, EPSILON)
        else:
            try:
                number = float(value)
            except (TypeError, ValueError):
                number = math.nan
            energy = (
                (number * number) / max(scale * scale, EPSILON)
                if math.isfinite(number)
                else 0.0
            )
        blocks[key] = energy
    return {
        "schema_version": "cortex-typed-residual-bundle/1.0",
        "blocks": blocks,
        "total_diagnostic_energy": sum(blocks.values()),
        "direct_sum": True,
        "authority": False,
        "claim_boundary": (
            "Typed residual energy is a diagnostic direct sum.  Residual types "
            "cannot impersonate each other and cannot authorize policy."
        ),
    }


__all__ = [
    "SCHEMA",
    "geometric_mean",
    "noncompensatory_compose",
    "typed_residual_energy",
]
