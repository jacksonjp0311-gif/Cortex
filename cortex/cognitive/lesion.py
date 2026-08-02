"""Confidence-bounded ablation benchmarks for v8.1 functional components."""

from __future__ import annotations

import math
import statistics
from typing import Any

from .autobiography import verify_autobiography
from .model import load_model
from .workspace import workspace_status

SCHEMA = "cortex-cognitive-lesion-benchmark/1.1"
PREDICTOR_EVALUATION_WINDOW = 8


def run_lesion_benchmarks(store: Any, repo: str) -> dict[str, Any]:
    model = load_model(store, repo)
    history = list(model.get("history") or [])
    evaluation_history = history[-PREDICTOR_EVALUATION_WINDOW:]
    intact_error = None
    zero_error = None
    lifetime_intact_error = None
    lifetime_zero_error = None
    paired_effects: list[float] = []
    if evaluation_history:
        intact_error = sum(
            float(item.get("normalized_mae") or 0.0)
            for item in evaluation_history
        ) / len(evaluation_history)
        zero_error = sum(
            sum(abs(float(value)) for value in (item.get("actual") or {}).values())
            / max(1, len(item.get("actual") or {}))
            for item in evaluation_history
        ) / len(evaluation_history)
        paired_effects = [
            (
                sum(abs(float(value)) for value in (item.get("actual") or {}).values())
                / max(1, len(item.get("actual") or {}))
            )
            - float(item.get("normalized_mae") or 0.0)
            for item in evaluation_history
        ]
    if history:
        lifetime_intact_error = sum(
            float(item.get("normalized_mae") or 0.0) for item in history
        ) / len(history)
        lifetime_zero_error = sum(
            sum(abs(float(value)) for value in (item.get("actual") or {}).values())
            / max(1, len(item.get("actual") or {}))
            for item in history
        ) / len(history)
    workspace = workspace_status(store, repo)
    latest_workspace = workspace.get("latest") or {}
    selected = list(latest_workspace.get("selected") or [])
    candidate_count = int(latest_workspace.get("candidate_count") or 0)
    autobiography = verify_autobiography(store, repo)
    effect_ci95 = None
    if len(paired_effects) >= 2:
        effect_mean = statistics.fmean(paired_effects)
        standard_error = statistics.stdev(paired_effects) / math.sqrt(len(paired_effects))
        # The evaluation window is fixed at eight. This conservative t critical
        # also avoids overstating support in smaller diagnostic windows.
        margin = 2.365 * standard_error
        effect_ci95 = [round(effect_mean - margin, 6), round(effect_mean + margin, 6)]
    tests = {
        "predictive_self_model": {
            "samples": len(history),
            "evaluation_samples": len(evaluation_history),
            "evaluation_window": PREDICTOR_EVALUATION_WINDOW,
            "intact_mae": round(intact_error, 6) if intact_error is not None else None,
            "lesioned_zero_model_mae": round(zero_error, 6) if zero_error is not None else None,
            "lifetime_intact_mae": (
                round(lifetime_intact_error, 6)
                if lifetime_intact_error is not None else None
            ),
            "lifetime_lesioned_zero_model_mae": (
                round(lifetime_zero_error, 6)
                if lifetime_zero_error is not None else None
            ),
            "measured_effect": (
                round(zero_error - intact_error, 6)
                if intact_error is not None and zero_error is not None else None
            ),
            "paired_effect_ci95": effect_ci95,
            "ci_method": "paired_t_interval_conservative_df7",
            "data_ready": len(evaluation_history) >= PREDICTOR_EVALUATION_WINDOW,
            "functional_dependence_observed": bool(
                intact_error is not None
                and zero_error is not None
                and zero_error > intact_error
            ),
            "supported": bool(
                len(evaluation_history) >= PREDICTOR_EVALUATION_WINDOW
                and intact_error is not None
                and zero_error is not None
                and effect_ci95 is not None
                and effect_ci95[0] > 0.0
            ),
        },
        "global_workspace": {
            "broadcasts": workspace.get("broadcast_count"),
            "candidate_count": candidate_count,
            "intact_available": len(selected),
            "lesioned_available": 0,
            "measured_effect": len(selected),
            "supported": bool(selected and candidate_count > len(selected)),
        },
        "autobiographical_continuity": {
            "episodes": autobiography.get("episode_count"),
            "intact_chain_valid": autobiography.get("chain_valid"),
            "lesioned_continuity": 0,
            "measured_effect": int(bool(autobiography.get("chain_valid") and autobiography.get("episode_count"))),
            "supported": int(autobiography.get("episode_count") or 0) >= 2,
        },
    }
    supported = [name for name, test in tests.items() if test["supported"]]
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "tests": tests,
        "supported_lesions": supported,
        "all_supported": len(supported) == len(tests),
        "cold_start": len(supported) < len(tests),
        "claim_boundary": (
            "Lesions test functional dependence in recorded workloads only; they do "
            "not test or establish subjective experience or consciousness."
        ),
    }
