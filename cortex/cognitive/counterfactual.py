"""Bounded counterfactual simulations over the predictive self-model."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .measured import METRICS

SCHEMA = "cortex-counterfactual-self-simulation/1.0"


def simulate_counterfactuals(
    forecast: dict[str, Any],
    *,
    realized_action: str = "bounded_adapt",
) -> dict[str, Any]:
    learned = dict(forecast.get("predicted_normalized_delta") or {})
    adaptive = {"synapse_mass", "ranker_train_count", "outcomes", "epochs"}
    candidates = {
        "abstain": {name: 0.0 for name in METRICS},
        "evidence_only": {
            name: (0.0 if name in adaptive else float(learned.get(name, 0.0)))
            for name in METRICS
        },
        "bounded_adapt": {name: float(learned.get(name, 0.0)) for name in METRICS},
    }
    simulations = []
    for action, delta in candidates.items():
        change_mass = sum(abs(value) for value in delta.values()) / max(1, len(delta))
        adaptive_mass = sum(abs(delta[name]) for name in adaptive)
        simulations.append({
            "action": action,
            "predicted_normalized_delta": delta,
            "predicted_change_mass": round(change_mass, 6),
            "predicted_adaptive_mass": round(adaptive_mass, 6),
            "is_realized_action": action == realized_action,
            "simulated_not_observed": True,
        })
    material = {
        "forecast_id": forecast.get("forecast_id"),
        "realized_action": realized_action,
        "simulations": simulations,
    }
    return {
        "schema_version": SCHEMA,
        **material,
        "simulation_hash": hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "minimum_change_projection": min(
            simulations, key=lambda item: (item["predicted_adaptive_mass"], item["predicted_change_mass"])
        )["action"],
        "comparison_only": True,
        "no_action_recommendation_without_task_utility": True,
        "claim_boundary": (
            "Counterfactuals are model projections, not executed branches, experiences, "
            "intentions, task utility, recommendations, or authority."
        ),
    }
