"""M6 — Ranker-primary scoring: heuristics as feature priors; loss + ECE helpers."""

from __future__ import annotations

import math
from typing import Any, Iterable

SCHEMA = "cortex-ranker-primary/1.0"


def sigmoid(x: float) -> float:
    if x >= 20:
        return 1.0
    if x <= -20:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def score_primary(
    weights: list[float],
    bias: float,
    features: list[float],
    *,
    heuristic_prior: float = 0.0,
    prior_mix: float = 0.15,
) -> dict[str, Any]:
    """Primary score = sigmoid(w·x + b); heuristic_prior mixed as feature only.

    prior_mix: how much of the final display blends residual heuristic (default low).
    """
    n = min(len(weights), len(features))
    logit = float(bias)
    for i in range(n):
        logit += float(weights[i]) * float(features[i])
    # heuristic enters as additive prior feature (not multiplicative stack)
    logit += prior_mix * float(heuristic_prior)
    p = sigmoid(logit)
    return {
        "schema_version": SCHEMA,
        "logit": round(logit, 6),
        "probability": round(p, 6),
        "heuristic_prior": round(float(heuristic_prior), 6),
        "prior_mix": prior_mix,
        "primary": True,
    }


def log_loss(y_true: Iterable[float], y_prob: Iterable[float]) -> float:
    eps = 1e-9
    total = 0.0
    n = 0
    for y, p in zip(y_true, y_prob):
        p = min(1.0 - eps, max(eps, float(p)))
        y = float(y)
        total += -(y * math.log(p) + (1.0 - y) * math.log(1.0 - p))
        n += 1
    return total / max(1, n)


def expected_calibration_error(
    y_true: list[float],
    y_prob: list[float],
    *,
    n_bins: int = 10,
) -> dict[str, Any]:
    """ECE with equal-width bins on [0,1]."""
    if not y_true:
        return {"ece": 0.0, "bins": [], "n": 0}
    bins: list[dict[str, Any]] = []
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idx = [i for i, p in enumerate(y_prob) if lo <= p < hi or (b == n_bins - 1 and p == 1.0)]
        if not idx:
            bins.append({"lo": lo, "hi": hi, "count": 0})
            continue
        conf = sum(y_prob[i] for i in idx) / len(idx)
        acc = sum(y_true[i] for i in idx) / len(idx)
        gap = abs(acc - conf)
        ece += (len(idx) / n) * gap
        bins.append(
            {
                "lo": lo,
                "hi": hi,
                "count": len(idx),
                "avg_confidence": round(conf, 6),
                "avg_accuracy": round(acc, 6),
                "gap": round(gap, 6),
            }
        )
    return {"ece": round(ece, 6), "bins": bins, "n": n, "schema_version": SCHEMA}
