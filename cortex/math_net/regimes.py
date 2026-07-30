"""M0 — Retention regimes (not spectral kernels).

Honest naming: fixed exponential priors ρ = e^{-δT} are *regime priors*,
not the spectrum of a graph Laplacian. True spectral objects live in spectral.py.
"""

from __future__ import annotations

import math
from typing import Any

SCHEMA = "cortex-retention-regimes/1.0"
GLYPH = "≋"
REGIMES = ("reset", "integrate", "retain")

# Prior degradation rates per unit interval T=1: ρ = exp(-δ T)
# These are *priors*, not fitted from data (see calibration / outcomes for fits).
PRIOR_DELTAS: dict[str, float] = {
    "reset": 2.3,  # ρ ≈ 0.10
    "integrate": 0.35,  # ρ ≈ 0.70
    "retain": 0.023,  # ρ ≈ 0.977
}

CLAIM = (
    "Regime priors are hand-set multi-rate filters. They are not Laplacian "
    "eigenvalues, not heat kernels e^{-tL}, and not identified δ from data "
    "until calibration logs exist. Docs continuous integral form is motivational."
)


def rho_from_delta(delta: float, interval: float = 1.0) -> float:
    return float(math.exp(-max(0.0, float(delta)) * max(0.0, float(interval))))


def prior_regime_profile() -> dict[str, Any]:
    classes: dict[str, Any] = {}
    for name, delta in PRIOR_DELTAS.items():
        classes[name] = {
            "delta": delta,
            "rho": round(rho_from_delta(delta), 6),
            "kind": "prior_not_fitted",
            "role": {
                "reset": "ephemeral_hits_and_prune_candidates",
                "integrate": "connect_ranker_prefetch",
                "retain": "cards_canonical_hierarchy",
            }[name],
        }
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "terminology": {
            "preferred": "retention_regime",
            "legacy_alias": "kernel_class",
            "not_spectral_until": "math_net.spectral builds L and λ",
        },
        "regimes": classes,
        "priors": True,
        "claim_boundary": CLAIM,
    }


def m0_status() -> dict[str, Any]:
    return {
        "phase": "M0",
        "title": "Rename + claim hygiene: regimes vs spectral",
        "ok": True,
        "profile": prior_regime_profile(),
        "claim_boundary": CLAIM,
    }
