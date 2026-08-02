"""Measured pre/post activation state and Resonant Field projection."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import replace
from typing import Any

from ..field_channels import (
    CHANNEL_FAMILIES,
    MEASUREMENT_MEASURED_DELTA,
    ChannelTruthSource,
    FieldSample,
    sample_tick_channels,
)

SCHEMA = "cortex-measured-event-field/1.0"

METRICS: dict[str, tuple[str, str, float]] = {
    "indexed_files": ("SELECT COUNT(*) AS v FROM files WHERE repo=? AND status='indexed'", "E_HOST", 10.0),
    "evidence_items": ("SELECT COUNT(*) AS v FROM memories WHERE repo=?", "E_HOST", 20.0),
    "prediction_traces": ("SELECT COUNT(*) AS v FROM prediction_traces WHERE repo=?", "E_RUNTIME", 2.0),
    "neural_nodes": ("SELECT COUNT(*) AS v FROM neural_nodes WHERE repo=?", "S_STRUCTURE", 10.0),
    "neural_synapses": ("SELECT COUNT(*) AS v FROM neural_synapses WHERE repo=?", "S_STRUCTURE", 20.0),
    "synapse_mass": ("SELECT COALESCE(SUM(weight),0) AS v FROM neural_synapses WHERE repo=?", "M_LEARNED", 5.0),
    "ranker_train_count": ("SELECT COALESCE(SUM(train_count),0) AS v FROM ranker_models WHERE repo=?", "M_LEARNED", 2.0),
    "outcomes": ("SELECT COUNT(*) AS v FROM task_outcomes WHERE repo=?", "M_CONSOLIDATED", 2.0),
    "mean_reward": ("SELECT COALESCE(AVG(reward),0) AS v FROM task_outcomes WHERE repo=?", "G_GOVERNOR", 0.25),
    "sessions": ("SELECT COUNT(*) AS v FROM sessions WHERE repo=?", "T_TASK", 1.0),
    "events": ("SELECT COUNT(*) AS v FROM events WHERE repo=?", "O_OPERATIONS", 5.0),
    "controller_events": ("SELECT COUNT(*) AS v FROM controller_audit_events WHERE repo=?", "O_OPERATIONS", 3.0),
    "epochs": ("SELECT COUNT(*) AS v FROM body_epochs WHERE repo=?", "C_CONSTITUTIONAL", 1.0),
    "witnesses": ("SELECT COUNT(*) AS v FROM witness_commitments WHERE repo=?", "W_WITNESS", 1.0),
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def capture_measured_state(store: Any, repo: str) -> dict[str, Any]:
    """Read bounded scalar state directly from local persistence."""
    values: dict[str, float] = {}
    unavailable: list[str] = []
    for name, (sql, _channel, _scale) in METRICS.items():
        try:
            row = store.db.execute(sql, (repo,)).fetchone()
            values[name] = float(row["v"] if row is not None else 0.0)
        except Exception:
            values[name] = 0.0
            unavailable.append(name)
    material = {"repo": repo, "values": values, "unavailable": unavailable}
    return {
        "schema_version": "cortex-measured-state/1.0",
        **material,
        "state_hash": _sha(material),
        "captured_at": time.time(),
        "direct_measurement": True,
    }


def measured_delta(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    event_id: str,
    event_kind: str = "activation_transaction",
) -> dict[str, Any]:
    """Compute an auditable signed delta over the fixed state coordinates."""
    b = dict(before.get("values") or {})
    a = dict(after.get("values") or {})
    delta = {name: float(a.get(name, 0.0)) - float(b.get(name, 0.0)) for name in METRICS}
    normalized = {
        name: max(-1.0, min(1.0, value / METRICS[name][2]))
        for name, value in delta.items()
    }
    material = {
        "event_id": event_id,
        "event_kind": event_kind,
        "before_hash": before.get("state_hash"),
        "after_hash": after.get("state_hash"),
        "delta": delta,
    }
    return {
        "schema_version": SCHEMA,
        **material,
        "normalized_delta": normalized,
        "changed_metrics": [name for name, value in delta.items() if abs(value) > 1e-12],
        "measurement_basis": MEASUREMENT_MEASURED_DELTA,
        "policy_eligible": True,
        "baseline_eligible": True,
        "receipt_hash": _sha(material),
        "measured_at": time.time(),
        "claim_boundary": (
            "Measured deltas describe local persisted state changes; they do not "
            "establish causation, experience, authority, or permission to mutate."
        ),
    }


def delta_field_samples(
    delta_report: dict[str, Any],
    *,
    repo: str,
    body_epoch_id: str,
    tick: int,
    governor_mode: str = "unknown",
) -> list[FieldSample]:
    """Project measured scalar deltas into the fixed field channel vocabulary."""
    normalized = dict(delta_report.get("normalized_delta") or {})
    grouped: dict[str, list[tuple[str, float]]] = {name: [] for name in CHANNEL_FAMILIES}
    for name, value in normalized.items():
        grouped[METRICS[name][1]].append((name, float(value)))
    activities: dict[str, float] = {}
    for channel, values in grouped.items():
        magnitude = sum(abs(value) for _, value in values)
        activities[channel] = 1.0 - math.exp(-magnitude)
    samples = sample_tick_channels(
        repo=repo,
        body_epoch_id=body_epoch_id,
        tick=tick,
        activities=activities,
        reliabilities={
            name: (1.0 if grouped[name] else 0.1) for name in CHANNEL_FAMILIES
        },
        truth_sources={
            name: (
                ChannelTruthSource.MEASURED.value
                if grouped[name]
                else ChannelTruthSource.UNKNOWN.value
            )
            for name in CHANNEL_FAMILIES
        },
        event_keys={name: "activation_transaction" for name in CHANNEL_FAMILIES},
        governor_mode=governor_mode,
        timestamp=delta_report.get("measured_at"),
    )
    event_id = str(delta_report.get("event_id") or delta_report.get("receipt_hash") or "")
    return [
        replace(
            sample,
            source_ids=(event_id,),
            metadata={
                "measurement_basis": MEASUREMENT_MEASURED_DELTA,
                "policy_eligible": True,
                "baseline_eligible": True,
                "delta_receipt_hash": delta_report.get("receipt_hash"),
                "before_hash": delta_report.get("before_hash"),
                "after_hash": delta_report.get("after_hash"),
                "metric_deltas": {name: value for name, value in grouped[sample.channel_family]},
            },
        )
        for sample in samples
    ]
