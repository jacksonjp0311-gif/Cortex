"""M5 — Calibration: fit constitutional / Governor weights from outcome logs (shadow).

Map predicted confidence to observed hit rates and clamp drift floor after
outcomes. Shadow calibration only until explicitly promoted.
"""

from __future__ import annotations

import json
import time
from typing import Any

SCHEMA = "cortex-calibration/1.0"

# Default priors (same as current code) — shadow fit updates a *shadow* profile only.
CONST_KEYS = (
    "drift",
    "uncertainty",
    "authority_pressure",
    "illegitimacy",
    "integrity_loss",
    "evidence_loss",
    "continuation_debt",
    "recovery_loss",
)
GOV_KEYS = ("integrity", "focus", "freshness", "confidence", "continuity")


def _uniform(keys: tuple[str, ...]) -> dict[str, float]:
    w = 1.0 / len(keys)
    return {k: w for k in keys}


def load_shadow_calibration(store: Any, repo: str) -> dict[str, Any]:
    raw = store.get_setting(f"calibration_shadow:{repo}", None) if hasattr(store, "get_setting") else None
    if isinstance(raw, dict) and raw.get("schema_version") == SCHEMA:
        return raw
    return {
        "schema_version": SCHEMA,
        "mode": "shadow",
        "constitutional_weights": _uniform(CONST_KEYS),
        "governor_weights": {
            "integrity": 0.30,
            "focus": 0.25,
            "freshness": 0.20,
            "confidence": 0.15,
            "continuity": 0.10,
        },
        "n_outcomes": 0,
        "updated_at": 0.0,
        "claim_boundary": "Shadow only until explicitly promoted; live paths keep priors.",
    }


def observe_outcome_for_calibration(
    store: Any,
    repo: str,
    *,
    reward: float,
    features: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Online shadow update: nudge weights toward features present on good/bad outcomes.

    Very small learning rate; does not replace live Governor/constitutional until promote.
    """
    cal = load_shadow_calibration(store, repo)
    feats = features or {}
    lr = 0.02
    # Positive reward → increase weight on features that were high; negative reverse
    sign = 1.0 if reward > 0 else -1.0 if reward < 0 else 0.0
    cw = dict(cal["constitutional_weights"])
    for k in CONST_KEYS:
        x = float(feats.get(k, 0.0))
        cw[k] = max(0.02, cw[k] + lr * sign * (x - 0.5))
    # renormalize
    s = sum(cw.values()) or 1.0
    cw = {k: v / s for k, v in cw.items()}

    gw = dict(cal["governor_weights"])
    for k in GOV_KEYS:
        x = float(feats.get(f"gov_{k}", feats.get(k, 0.5)))
        gw[k] = max(0.02, gw[k] + lr * sign * (x - 0.5))
    s2 = sum(gw.values()) or 1.0
    gw = {k: v / s2 for k, v in gw.items()}

    cal = {
        **cal,
        "constitutional_weights": {k: round(v, 6) for k, v in cw.items()},
        "governor_weights": {k: round(v, 6) for k, v in gw.items()},
        "n_outcomes": int(cal.get("n_outcomes") or 0) + 1,
        "updated_at": time.time(),
        "mode": "shadow",
    }
    try:
        store.set_setting(f"calibration_shadow:{repo}", cal)
    except Exception:
        pass
    return cal
