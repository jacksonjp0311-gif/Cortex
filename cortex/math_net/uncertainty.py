"""M1 — Single uncertainty U ∈ [0,1] consumed everywhere.

Unified uncertainty: a single scalar that may only decrease when immune stress
rises — never inflate certainty for the Governor. Confidence C = 1 - U.
U = 1 means max uncertainty (abstain/constrain); U = 0 means high certainty.
Derived once from retrieval, certificate, governor components, drift flags.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "cortex-unified-uncertainty/1.0"


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def compute_uncertainty(
    *,
    retrieval_confidence: float = 0.0,
    certificate_status: str | None = None,
    manifest_current: bool | None = None,
    governor_stability: float | None = None,
    lane_entropy: float | None = None,
    drift_score: float | None = None,
    evidence_count: int | None = None,
    budget_tokens: int | None = None,
) -> dict[str, Any]:
    """Compute unified U and confidence C = 1 - U with component breakdown."""

    conf = _clip01(retrieval_confidence)
    # Base: invert retrieval confidence
    u_ret = 1.0 - conf

    u_cert = 0.0
    st = (certificate_status or "unknown").casefold()
    if st in {"failed", "unknown", ""}:
        u_cert = 0.85
    elif st == "degraded":
        u_cert = 0.45

    u_drift = 0.0
    if manifest_current is False:
        u_drift = 0.70
    elif drift_score is not None:
        u_drift = _clip01(float(drift_score))

    u_gov = 0.0
    if governor_stability is not None:
        u_gov = 1.0 - _clip01(governor_stability)

    u_entropy = _clip01(lane_entropy) if lane_entropy is not None else 0.0

    u_sparse = 0.0
    if evidence_count is not None and evidence_count <= 0:
        u_sparse = 0.80
    elif evidence_count is not None and evidence_count < 3:
        u_sparse = 0.35

    # Conservative blend: max of hard risk terms with soft average of sensors
    soft = 0.40 * u_ret + 0.20 * u_gov + 0.15 * u_entropy + 0.15 * u_drift + 0.10 * u_sparse
    hard = max(u_cert, u_drift if manifest_current is False else 0.0)
    u = _clip01(max(hard * 0.55 + soft * 0.45, hard * 0.7, soft))

    components = {
        "retrieval": round(u_ret, 6),
        "certificate": round(u_cert, 6),
        "drift": round(u_drift, 6),
        "governor": round(u_gov, 6),
        "lane_entropy": round(u_entropy, 6),
        "sparse_evidence": round(u_sparse, 6),
        "soft_blend": round(soft, 6),
        "hard": round(hard, 6),
    }
    return {
        "schema_version": SCHEMA,
        "u": round(u, 6),
        "confidence": round(1.0 - u, 6),
        "components": components,
        "budget_tokens": budget_tokens,
        "claim_boundary": (
            "U is a unified heuristic until calibration (M5) fits to outcomes; "
            "single number for Governor, control_error, constitutional, promotion."
        ),
    }


def attach_uncertainty(payload: dict[str, Any], u_packet: dict[str, Any]) -> dict[str, Any]:
    """Embed U into a packet dict without mutating caller's structure unexpectedly."""
    out = dict(payload)
    out["uncertainty"] = u_packet
    out["u"] = u_packet.get("u")
    out["unified_confidence"] = u_packet.get("confidence")
    return out
