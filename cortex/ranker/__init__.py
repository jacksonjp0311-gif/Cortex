"""Tiny local online ranker — verified outcomes only; never grants authority."""

from .model import (
    FEATURE_NAMES,
    ensure_ranker,
    ranker_status,
    score_features,
    train_from_outcome,
)

__all__ = [
    "FEATURE_NAMES",
    "ensure_ranker",
    "ranker_status",
    "score_features",
    "train_from_outcome",
]
