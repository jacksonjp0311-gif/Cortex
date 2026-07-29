"""Proactive/predictive context — recommend-only prefetch."""

from .prefetch import predict_context, record_prediction_outcome

__all__ = ["predict_context", "record_prediction_outcome"]
