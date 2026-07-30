"""Kernel filter state Λ_g — real state updated on connect (not labels only)."""

from __future__ import annotations

import math
import time
from typing import Any

from .regimes import PRIOR_DELTAS, REGIMES, rho_from_delta

SCHEMA = "cortex-kernel-state/1.0"


def _load_state(store: Any, repo: str) -> dict[str, Any]:
    raw = store.get_setting(f"kernel_state:{repo}", None) if hasattr(store, "get_setting") else None
    if isinstance(raw, dict) and raw.get("schema_version") == SCHEMA:
        return raw
    return {
        "schema_version": SCHEMA,
        "Lambda": {g: 0.0 for g in REGIMES},
        "updated_at": 0.0,
        "pulses": 0,
    }


def update_lambda_on_pulse(
    store: Any,
    repo: str,
    *,
    class_mass: dict[str, float] | None = None,
    interval: float = 1.0,
    multi_pole: bool = True,
) -> dict[str, Any]:
    """Λ_g ← ρ_g Λ_g + input_g  (and optional 2-mode mixture).

    input_g defaults to normalized synapse mass by regime class.
    """
    state = _load_state(store, repo)
    Lambda = {g: float((state.get("Lambda") or {}).get(g) or 0.0) for g in REGIMES}

    # Measure input mass from graph if not provided
    if class_mass is None:
        class_mass = {g: 0.0 for g in REGIMES}
        try:
            import json

            for row in store.neural_synapses(repo) or []:
                meta = json.loads(row["metadata"] or "{}")
                klass = meta.get("kernel_class") or meta.get("retention_regime") or "reset"
                if klass not in class_mass:
                    klass = "integrate"
                class_mass[klass] = class_mass.get(klass, 0.0) + float(row["weight"] or 0)
        except Exception:
            pass

    total = sum(class_mass.values()) or 1.0
    inputs = {g: class_mass.get(g, 0.0) / total for g in REGIMES}

    new_L: dict[str, float] = {}
    poles: dict[str, Any] = {}
    for g in REGIMES:
        delta = PRIOR_DELTAS[g]
        rho = rho_from_delta(delta, interval)
        if multi_pole:
            # 2–3 shared modes: fast + slow mixture around regime prior
            taus = [1.0 / max(delta, 1e-6), 2.5 / max(delta, 1e-6)]
            weights = [0.65, 0.35]
            rho_mix = sum(w * math.exp(-interval / tau) for w, tau in zip(weights, taus))
            poles[g] = {"taus": taus, "weights": weights, "rho_mix": round(rho_mix, 6)}
            rho_eff = rho_mix
        else:
            rho_eff = rho
        new_L[g] = rho_eff * Lambda[g] + inputs[g]
        # soft cap
        new_L[g] = min(new_L[g], 5.0)

    state = {
        "schema_version": SCHEMA,
        "Lambda": {g: round(new_L[g], 6) for g in REGIMES},
        "rho_used": {g: round(rho_from_delta(PRIOR_DELTAS[g], interval), 6) for g in REGIMES},
        "input": {g: round(inputs[g], 6) for g in REGIMES},
        "multi_pole": multi_pole,
        "poles": poles,
        "updated_at": time.time(),
        "pulses": int(state.get("pulses") or 0) + 1,
        "claim_boundary": (
            "Λ_g is filter state with prior ρ; δ not yet MLE-fitted from outcomes."
        ),
    }
    try:
        store.set_setting(f"kernel_state:{repo}", state)
    except Exception:
        pass
    return state
