"""Predictive self-model trained only on measured activation deltas."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .measured import METRICS

SCHEMA = "cortex-predictive-self-model/1.0"
HISTORY_CAP = 128
ALPHA = 0.15
MIN_CALIBRATION_SAMPLES = 16
MAX_CALIBRATION_ECE = 0.15
MAX_CALIBRATION_BRIER = 0.25


def _key(repo: str) -> str:
    return f"predictive_self_model:{repo}"


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def load_model(store: Any, repo: str) -> dict[str, Any]:
    state = store.get_setting(_key(repo), {}) or {}
    return dict(state) if isinstance(state, dict) else {}


def calibration_report(history: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [item for item in history if item.get("confidence") is not None]
    if not scored:
        return {
            "n": 0,
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
    mean = dict(state.get("mean_delta") or {})
    n = int(state.get("n_updates") or 0)
    history = list(state.get("history") or [])
    calibration = calibration_report(history)
    empirical_error = state.get("ema_error")
    confidence = 0.25 if empirical_error is None else 1.0 / (1.0 + float(empirical_error))
    confidence *= min(1.0, n / 16.0) if n else 0.0
    predicted = {name: float(mean.get(name, 0.0)) for name in METRICS}
    material = {"repo": repo, "action": action, "n": n, "predicted": predicted}
    return {
        "schema_version": SCHEMA,
        "forecast_id": "forecast_" + _sha({**material, "at": time.time()})[:20],
        "action": action,
        "predicted_normalized_delta": predicted,
        "confidence": round(max(0.0, min(1.0, confidence)), 6),
        "model_n": n,
        "calibration_before": calibration,
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
    score = {
        "forecast_id": forecast.get("forecast_id"),
        "event_id": measured.get("event_id"),
        "normalized_mae": round(mae, 6),
        "accurate": accurate,
        "confidence": confidence,
        "brier": round((confidence - float(accurate)) ** 2, 6),
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
        "ema_error": ema_error,
        "n_updates": n + 1,
        "history": history[-HISTORY_CAP:],
        "updated_at": time.time(),
    }
    store.set_setting(_key(repo), new_state)
    return {
        **score,
        "model_n_after": n + 1,
        "calibration_after": calibration_report(new_state["history"]),
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
        "calibration": calibration_report(history),
        "latest_score": history[-1] if history else None,
        "advisory_only": True,
        "claim_boundary": (
            "The self-model predicts local operational variables. Predictive accuracy "
            "is not evidence of consciousness or subjective experience."
        ),
    }
