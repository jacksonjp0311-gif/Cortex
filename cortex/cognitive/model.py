"""Predictive self-model trained only on measured activation deltas."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .measured import METRICS

SCHEMA = "cortex-predictive-self-model/1.1"
HISTORY_CAP = 128
ALPHA = 0.15
MIN_CALIBRATION_SAMPLES = 16
MAX_CALIBRATION_ECE = 0.15
CONFIDENCE_DEFINITION = "beta_posterior_probability_mae_at_most_0.20"
MAX_CALIBRATION_BRIER = 0.25


def classify_regime(measured: dict[str, Any]) -> str:
    """Classify the observed plant transition without granting it authority."""
    delta = dict(measured.get("normalized_delta") or {})
    if (
        float(delta.get("neural_synapses", 0.0)) < -1e-12
        or float(delta.get("synapse_mass", 0.0)) < -1e-12
    ):
        return "scheduled_decay"
    if any(
        abs(float(delta.get(name, 0.0))) > 1e-12
        for name in ("indexed_files", "neural_nodes", "neural_synapses")
    ):
        return "refresh_recompile"
    if any(
        abs(float(delta.get(name, 0.0))) > 1e-12
        for name in ("ranker_train_count", "outcomes", "mean_reward")
    ):
        return "adaptive_learning"
    if any(abs(float(value)) > 1e-12 for value in delta.values()):
        return "evidence_only"
    return "steady"


def _forecast_regime(state: dict[str, Any], action: str) -> str:
    regimes = dict(state.get("regimes") or {})
    last = str(state.get("last_regime") or "")
    outgoing = dict((state.get("transition_counts") or {}).get(last) or {})
    if outgoing:
        return min(outgoing, key=lambda name: (-int(outgoing[name]), name))
    if last and last in regimes:
        return last
    if action in regimes:
        return action
    if regimes:
        return min(
            regimes,
            key=lambda name: (-int((regimes[name] or {}).get("n_updates") or 0), name),
        )
    return "cold_start"


def _probability_of_accuracy(history: list[dict[str, Any]]) -> float:
    """Beta(1,1) posterior mean for P(normalized MAE <= 0.20)."""
    successes = sum(1 for item in history if bool(item.get("accurate")))
    return (successes + 1.0) / (len(history) + 2.0)


def _key(repo: str) -> str:
    return f"predictive_self_model:{repo}"


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def load_model(store: Any, repo: str) -> dict[str, Any]:
    state = store.get_setting(_key(repo), {}) or {}
    return dict(state) if isinstance(state, dict) else {}


def calibration_report(
    history: list[dict[str, Any]],
    *,
    confidence_definition: str | None = None,
) -> dict[str, Any]:
    scored = [
        item
        for item in history
        if item.get("confidence") is not None
        and (
            confidence_definition is None
            or item.get("confidence_definition") == confidence_definition
        )
    ]
    excluded_incompatible = len(history) - len(scored)
    if not scored:
        return {
            "n": 0,
            "history_n": len(history),
            "excluded_incompatible": excluded_incompatible,
            "confidence_definition": confidence_definition,
            "brier": None,
            "ece": None,
            "bins": [],
            "data_ready": False,
            "thresholds": {
                "minimum_samples": MIN_CALIBRATION_SAMPLES,
                "maximum_brier": MAX_CALIBRATION_BRIER,
                "maximum_ece": MAX_CALIBRATION_ECE,
            },
            "calibrated": False,
        }
    brier = sum(
        (float(item["confidence"]) - float(bool(item.get("accurate")))) ** 2
        for item in scored
    ) / len(scored)
    bins: list[dict[str, Any]] = []
    ece = 0.0
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        bucket = [
            item for item in scored
            if lower <= float(item["confidence"]) < lower + 0.2 + (1e-12 if lower == 0.8 else 0.0)
        ]
        if not bucket:
            continue
        confidence = sum(float(item["confidence"]) for item in bucket) / len(bucket)
        accuracy = sum(float(bool(item.get("accurate"))) for item in bucket) / len(bucket)
        ece += (len(bucket) / len(scored)) * abs(confidence - accuracy)
        bins.append({
            "lower": lower,
            "n": len(bucket),
            "mean_confidence": round(confidence, 6),
            "accuracy": round(accuracy, 6),
        })
    data_ready = len(scored) >= MIN_CALIBRATION_SAMPLES
    return {
        "n": len(scored),
        "history_n": len(history),
        "excluded_incompatible": excluded_incompatible,
        "confidence_definition": confidence_definition,
        "brier": round(brier, 6),
        "ece": round(ece, 6),
        "bins": bins,
        "data_ready": data_ready,
        "thresholds": {
            "minimum_samples": MIN_CALIBRATION_SAMPLES,
            "maximum_brier": MAX_CALIBRATION_BRIER,
            "maximum_ece": MAX_CALIBRATION_ECE,
        },
        "calibrated": bool(
            data_ready
            and brier <= MAX_CALIBRATION_BRIER
            and ece <= MAX_CALIBRATION_ECE
        ),
    }


def predict_next_delta(store: Any, repo: str, *, action: str) -> dict[str, Any]:
    state = load_model(store, repo)
    predicted_regime = _forecast_regime(state, action)
    regime_state = dict((state.get("regimes") or {}).get(predicted_regime) or {})
    mean = dict(regime_state.get("mean_delta") or state.get("mean_delta") or {})
    variance = dict(regime_state.get("variance") or state.get("variance") or {})
    n = int(state.get("n_updates") or 0)
    history = list(state.get("history") or [])
    calibration = calibration_report(
        history, confidence_definition=CONFIDENCE_DEFINITION
    )
    regime_history = [
        item for item in history
        if item.get("observed_regime") == predicted_regime
    ]
    confidence = _probability_of_accuracy(regime_history)
    predicted = {name: float(mean.get(name, 0.0)) for name in METRICS}
    material = {
        "repo": repo,
        "action": action,
        "regime": predicted_regime,
        "n": n,
        "predicted": predicted,
    }
    return {
        "schema_version": SCHEMA,
        "forecast_id": "forecast_" + _sha({**material, "at": time.time()})[:20],
        "action": action,
        "predicted_regime": predicted_regime,
        "predicted_normalized_delta": predicted,
        "predictive_stddev": {
            name: float(variance.get(name, 0.05)) ** 0.5 for name in METRICS
        },
        "confidence": round(max(0.0, min(1.0, confidence)), 6),
        "model_n": n,
        "regime_n": int(regime_state.get("n_updates") or 0),
        "calibration_before": calibration,
        "regime_calibration_before": calibration_report(
            regime_history, confidence_definition=CONFIDENCE_DEFINITION
        ),
        "confidence_definition": CONFIDENCE_DEFINITION,
        "issued_at": time.time(),
        "advisory_only": True,
    }


def score_and_update(
    store: Any,
    repo: str,
    forecast: dict[str, Any],
    measured: dict[str, Any],
) -> dict[str, Any]:
    state = load_model(store, repo)
    predicted = dict(forecast.get("predicted_normalized_delta") or {})
    actual = dict(measured.get("normalized_delta") or {})
    errors = {name: float(actual.get(name, 0.0)) - float(predicted.get(name, 0.0)) for name in METRICS}
    mae = sum(abs(value) for value in errors.values()) / max(1, len(errors))
    accurate = mae <= 0.20
    confidence = float(forecast.get("confidence") or 0.0)
    predicted_regime = str(forecast.get("predicted_regime") or "cold_start")
    observed_regime = classify_regime(measured)
    score = {
        "forecast_id": forecast.get("forecast_id"),
        "event_id": measured.get("event_id"),
        "normalized_mae": round(mae, 6),
        "accurate": accurate,
        "confidence": confidence,
        "confidence_definition": forecast.get("confidence_definition"),
        "brier": round((confidence - float(accurate)) ** 2, 6),
        "predicted_regime": predicted_regime,
        "observed_regime": observed_regime,
        "regime_match": predicted_regime == observed_regime,
        "errors": errors,
        "scored_at": time.time(),
    }
    n = int(state.get("n_updates") or 0)
    mean = dict(state.get("mean_delta") or {})
    variance = dict(state.get("variance") or {})
    for name in METRICS:
        x = float(actual.get(name, 0.0))
        old = float(mean.get(name, 0.0))
        new = x if n == 0 else (1.0 - ALPHA) * old + ALPHA * x
        mean[name] = new
        variance[name] = (
            0.05 if n == 0 else (1.0 - ALPHA) * float(variance.get(name, 0.05)) + ALPHA * (x - old) ** 2
        )
    regimes = dict(state.get("regimes") or {})
    regime_state = dict(regimes.get(observed_regime) or {})
    regime_n = int(regime_state.get("n_updates") or 0)
    regime_mean = dict(regime_state.get("mean_delta") or {})
    regime_variance = dict(regime_state.get("variance") or {})
    for name in METRICS:
        x = float(actual.get(name, 0.0))
        old = float(regime_mean.get(name, 0.0))
        new = x if regime_n == 0 else (1.0 - ALPHA) * old + ALPHA * x
        regime_mean[name] = new
        regime_variance[name] = (
            0.05
            if regime_n == 0
            else (1.0 - ALPHA) * float(regime_variance.get(name, 0.05))
            + ALPHA * (x - old) ** 2
        )
    regimes[observed_regime] = {
        "mean_delta": regime_mean,
        "variance": regime_variance,
        "n_updates": regime_n + 1,
        "updated_at": time.time(),
    }
    transitions = {
        key: dict(value) for key, value in (state.get("transition_counts") or {}).items()
    }
    previous_regime = str(state.get("last_regime") or "")
    if previous_regime:
        row = transitions.setdefault(previous_regime, {})
        row[observed_regime] = int(row.get(observed_regime) or 0) + 1
    history = list(state.get("history") or [])
    history.append({
        **score,
        "predicted": predicted,
        "actual": actual,
        "changed_metrics": measured.get("changed_metrics") or [],
    })
    ema_error = mae if state.get("ema_error") is None else (
        0.85 * float(state["ema_error"]) + 0.15 * mae
    )
    new_state = {
        "schema_version": SCHEMA,
        "mean_delta": mean,
        "variance": variance,
        "regimes": regimes,
        "transition_counts": transitions,
        "last_regime": observed_regime,
        "ema_error": ema_error,
        "n_updates": n + 1,
        "history": history[-HISTORY_CAP:],
        "updated_at": time.time(),
    }
    store.set_setting(_key(repo), new_state)
    return {
        **score,
        "model_n_after": n + 1,
        "calibration_after": calibration_report(
            new_state["history"], confidence_definition=CONFIDENCE_DEFINITION
        ),
        "regime_n_after": regime_n + 1,
        "prediction_error_is_not_subjective_surprise": True,
        "advisory_only": True,
    }


def model_status(store: Any, repo: str) -> dict[str, Any]:
    state = load_model(store, repo)
    history = list(state.get("history") or [])
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "n_updates": int(state.get("n_updates") or 0),
        "ema_error": state.get("ema_error"),
        "mean_delta": state.get("mean_delta") or {},
        "regimes": state.get("regimes") or {},
        "last_regime": state.get("last_regime"),
        "transition_counts": state.get("transition_counts") or {},
        "calibration": calibration_report(
            history, confidence_definition=CONFIDENCE_DEFINITION
        ),
        "latest_score": history[-1] if history else None,
        "advisory_only": True,
        "claim_boundary": (
            "The self-model predicts local operational variables. Predictive accuracy "
            "is not evidence of consciousness or subjective experience."
        ),
    }
