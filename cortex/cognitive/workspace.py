"""Capacity-bounded global availability for operational signals."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

SCHEMA = "cortex-global-workspace/1.0"
CAPACITY = 4
HISTORY_CAP = 64


def _clip(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _candidate(
    signal_id: str,
    value: Any,
    *,
    urgency: float,
    reliability: float,
    novelty: float,
    source: str,
) -> dict[str, Any]:
    score = _clip(urgency) * _clip(reliability) * (0.5 + 0.5 * _clip(novelty))
    return {
        "signal_id": signal_id,
        "source": source,
        "value": value,
        "urgency": _clip(urgency),
        "reliability": _clip(reliability),
        "novelty": _clip(novelty),
        "workspace_score": round(score, 6),
    }


def compete_and_broadcast(
    store: Any,
    repo: str,
    *,
    measured: dict[str, Any],
    prediction_score: dict[str, Any],
    self_sensing: dict[str, Any],
    frame: dict[str, Any] | None,
    epoch_delta: dict[str, Any] | None,
) -> dict[str, Any]:
    changed = list(measured.get("changed_metrics") or [])
    residual = float(self_sensing.get("residual_r") or 0.0)
    pred_error = float(prediction_score.get("normalized_mae") or 0.0)
    candidates = [
        _candidate(
            "self_sensing_residual", self_sensing.get("classification"),
            urgency=min(1.0, residual / 4.0), reliability=1.0,
            novelty=min(1.0, residual / 6.0), source="self_sensing",
        ),
        _candidate(
            "prediction_error", pred_error,
            urgency=min(1.0, pred_error * 2.0), reliability=1.0,
            novelty=min(1.0, pred_error), source="predictive_self_model",
        ),
        _candidate(
            "measured_change", changed,
            urgency=min(1.0, len(changed) / 6.0), reliability=1.0,
            novelty=min(1.0, len(changed) / 8.0), source="measured_event_field",
        ),
        _candidate(
            "epoch_transition", (epoch_delta or {}).get("changed_roots") or [],
            urgency=1.0 if (epoch_delta or {}).get("material_change") else 0.1,
            reliability=1.0, novelty=1.0 if (epoch_delta or {}).get("material_change") else 0.0,
            source="body_epoch",
        ),
        _candidate(
            "temporal_frame", (frame or {}).get("classification"),
            urgency=0.8 if (frame or {}).get("classification") in {"TRANSITION", "STALE_ECHO", "FRAGMENTED"} else 0.2,
            reliability=1.0 if (frame or {}).get("measurement_basis") == "measured_delta" else 0.5,
            novelty=0.5, source="resonant_frame",
        ),
    ]
    ranked = sorted(candidates, key=lambda item: (-item["workspace_score"], item["signal_id"]))
    selected = ranked[:CAPACITY]
    material = {
        "repo": repo,
        "selected": selected,
        "capacity": CAPACITY,
        "measured_receipt": measured.get("receipt_hash"),
    }
    broadcast_hash = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()
    report = {
        "schema_version": SCHEMA,
        "repo": repo,
        "capacity": CAPACITY,
        "candidate_count": len(ranked),
        "selected": selected,
        "suppressed": ranked[CAPACITY:],
        "broadcast_hash": broadcast_hash,
        "globally_available_to": [
            "activation_report", "interconnect", "autobiography", "operator"
        ],
        "broadcast_at": time.time(),
        "advisory_only": True,
        "claim_boundary": (
            "Global availability means bounded cross-module reporting, not phenomenal "
            "awareness, executive authority, or unrestricted attention."
        ),
    }
    key = f"global_workspace:{repo}"
    history = list(store.get_setting(key, []) or [])
    history.append(report)
    store.set_setting(key, history[-HISTORY_CAP:])
    return report


def workspace_status(store: Any, repo: str) -> dict[str, Any]:
    history = list(store.get_setting(f"global_workspace:{repo}", []) or [])
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "broadcast_count": len(history),
        "latest": history[-1] if history else None,
        "capacity": CAPACITY,
        "advisory_only": True,
    }
