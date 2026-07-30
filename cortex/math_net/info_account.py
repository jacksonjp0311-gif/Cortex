"""M7 — Information accounting: budget → ΔU proxy → promotion gate.

Information accounting: budget bits spent on retrieval and learning decisions;
delta-U efficiency and promotion gate (recommend-only).
"""

from __future__ import annotations

from typing import Any

from .uncertainty import compute_uncertainty

SCHEMA = "cortex-info-account/1.0"


def info_account(
    *,
    u_before: float,
    u_after: float | None = None,
    budget_tokens: int = 0,
    evidence_fidelity: float = 0.0,
    reversibility: float = 1.0,
    retrieval_confidence: float = 0.0,
) -> dict[str, Any]:
    """ΔU = u_before - u_after (positive ⇒ uncertainty reduced).

    efficiency ≈ ΔU / log(1 + tokens); promotion_score multiplies fidelity × rev × gain.
    """
    ua = float(u_after) if u_after is not None else float(u_before)
    delta_u = float(u_before) - ua
    tokens = max(0, int(budget_tokens))
    denom = math_log1p(tokens)
    efficiency = delta_u / denom if denom > 0 else 0.0
    # Real promotion product (not checklist alone)
    promotion = max(0.0, delta_u) * max(0.0, min(1.0, evidence_fidelity)) * max(0.0, min(1.0, reversibility))
    # gate: need positive information gain or high fidelity with low U
    gate_open = (delta_u > 0.02 and evidence_fidelity >= 0.5) or (
        ua < 0.25 and evidence_fidelity >= 0.75 and reversibility >= 0.8
    )
    return {
        "schema_version": SCHEMA,
        "u_before": round(float(u_before), 6),
        "u_after": round(ua, 6),
        "delta_u": round(delta_u, 6),
        "budget_tokens": tokens,
        "efficiency_delta_u_per_log_token": round(efficiency, 8),
        "evidence_fidelity": round(float(evidence_fidelity), 6),
        "reversibility": round(float(reversibility), 6),
        "promotion_score": round(promotion, 6),
        "promotion_gate_open": bool(gate_open),
        "claim_boundary": (
            "ΔU is a proxy, not Shannon bits from the environment; gate is recommend-only."
        ),
    }


def math_log1p(x: float) -> float:
    import math

    return math.log1p(max(0.0, float(x)))


def account_from_confidences(
    *,
    conf_before: float,
    conf_after: float,
    budget_tokens: int,
    evidence_fidelity: float = 0.7,
    reversibility: float = 1.0,
) -> dict[str, Any]:
    ub = compute_uncertainty(retrieval_confidence=conf_before)["u"]
    ua = compute_uncertainty(retrieval_confidence=conf_after)["u"]
    return info_account(
        u_before=ub,
        u_after=ua,
        budget_tokens=budget_tokens,
        evidence_fidelity=evidence_fidelity,
        reversibility=reversibility,
        retrieval_confidence=conf_after,
    )
