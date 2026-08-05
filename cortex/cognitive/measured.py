"""Measured pre/post activation state and Resonant Field projection."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass, replace
from typing import Any

from ..field_channels import (
    CHANNEL_FAMILIES,
    MEASUREMENT_MEASURED_DELTA,
    ChannelTruthSource,
    FieldSample,
    sample_tick_channels,
)

SCHEMA = "cortex-measured-event-field/1.2"
STATE_SCHEMA = "cortex-measured-state/1.1"
COORDINATE_SCHEMA_VERSION = "cortex-activation-coordinates/1.0"

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
    # Witness commitments are home-scoped rather than repo-scoped.  The bound
    # parameter deliberately proves the caller supplied a repository while the
    # operational unit remains an explicit local-store count.
    "witnesses": ("SELECT COUNT(*) AS v FROM witness_commitments WHERE ? IS NOT NULL", "W_WITNESS", 1.0),
}


@dataclass(frozen=True)
class CoordinateDefinition:
    """Immutable scientific definition for one measured state coordinate."""

    coordinate_id: str
    scalar_type: str
    measurement_source: str
    operational_unit: str
    channel_family: str
    normalization_scale: float
    null_allowed: bool
    required_for_conformance: bool
    criticality_weight: float
    schema_version: str = COORDINATE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _unit_for(name: str) -> str:
    if name == "synapse_mass":
        return "summed_synapse_weight"
    if name == "mean_reward":
        return "mean_reward_ratio"
    if name == "witnesses":
        return "local_store_commitment_count"
    return "row_count"


COORDINATE_SCHEMA: tuple[CoordinateDefinition, ...] = tuple(
    CoordinateDefinition(
        coordinate_id=name,
        scalar_type="float64",
        measurement_source=sql,
        operational_unit=_unit_for(name),
        channel_family=channel,
        normalization_scale=float(scale),
        null_allowed=False,
        required_for_conformance=True,
        criticality_weight=1.0,
    )
    for name, (sql, channel, scale) in METRICS.items()
)


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def coordinate_schema_payload() -> dict[str, Any]:
    coordinates = [coordinate.to_dict() for coordinate in COORDINATE_SCHEMA]
    ordered_names = [coordinate.coordinate_id for coordinate in COORDINATE_SCHEMA]
    shape_signature = [
        {
            "coordinate_id": coordinate.coordinate_id,
            "scalar_type": coordinate.scalar_type,
            "nullable": coordinate.null_allowed,
        }
        for coordinate in COORDINATE_SCHEMA
    ]
    scales = [
        {
            "coordinate_id": coordinate.coordinate_id,
            "normalization_scale": coordinate.normalization_scale,
        }
        for coordinate in COORDINATE_SCHEMA
    ]
    return {
        "coordinate_schema_version": COORDINATE_SCHEMA_VERSION,
        "coordinate_schema_digest": _sha(coordinates),
        "ordered_coordinate_names": ordered_names,
        "ordered_shape_signature": shape_signature,
        "shape_signature_digest": _sha(shape_signature),
        "scale_digest": _sha(scales),
        "coordinates": coordinates,
    }


COORDINATE_SCHEMA_METADATA = coordinate_schema_payload()


def capture_measured_state(store: Any, repo: str) -> dict[str, Any]:
    """Read bounded scalar state directly from local persistence."""
    values: dict[str, float | None] = {}
    validity_mask: dict[str, bool] = {}
    failure_reasons: dict[str, str | None] = {}
    store.db.execute("SAVEPOINT cortex_measurement_capture")
    try:
        repository = store.repo(repo)
        repository_id = (
            str(repository["repository_id"] or "") if repository else ""
        )
        for coordinate in COORDINATE_SCHEMA:
            name = coordinate.coordinate_id
            try:
                row = store.db.execute(
                    coordinate.measurement_source, (repo,)
                ).fetchone()
                if row is None or row["v"] is None:
                    raise LookupError("measurement_row_missing")
                value = float(row["v"])
                if not math.isfinite(value):
                    raise ValueError("measurement_not_finite")
                values[name] = value
                validity_mask[name] = True
                failure_reasons[name] = None
            except Exception as exc:
                values[name] = None
                validity_mask[name] = False
                failure_reasons[name] = f"{type(exc).__name__}:{exc}"
    finally:
        store.db.execute("RELEASE SAVEPOINT cortex_measurement_capture")
    metadata = coordinate_schema_payload()
    required = [
        coordinate.coordinate_id
        for coordinate in COORDINATE_SCHEMA
        if coordinate.required_for_conformance
    ]
    valid_count = sum(1 for name in required if validity_mask.get(name) is True)
    material = {
        "repo": repo,
        "repository_id": repository_id,
        "coordinate_schema_digest": metadata["coordinate_schema_digest"],
        "values": values,
        "validity_mask": validity_mask,
        "failure_reasons": failure_reasons,
    }
    return {
        "schema_version": STATE_SCHEMA,
        **material,
        "coordinate_schema_version": COORDINATE_SCHEMA_VERSION,
        "ordered_coordinate_names": list(
            metadata["ordered_coordinate_names"]
        ),
        "ordered_shape_signature": copy.deepcopy(
            metadata["ordered_shape_signature"]
        ),
        "scale_digest": metadata["scale_digest"],
        "valid_count": valid_count,
        "required_count": len(required),
        "valid_fraction": valid_count / max(1, len(required)),
        "unavailable": [name for name in required if not validity_mask.get(name)],
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
    before_validity = dict(before.get("validity_mask") or {})
    after_validity = dict(after.get("validity_mask") or {})
    metadata = coordinate_schema_payload()
    ordered_names = list(metadata["ordered_coordinate_names"])
    before_material = {
        "repo": before.get("repo"),
        "repository_id": before.get("repository_id"),
        "coordinate_schema_digest": before.get("coordinate_schema_digest"),
        "values": b,
        "validity_mask": before_validity,
        "failure_reasons": dict(before.get("failure_reasons") or {}),
    }
    after_material = {
        "repo": after.get("repo"),
        "repository_id": after.get("repository_id"),
        "coordinate_schema_digest": after.get("coordinate_schema_digest"),
        "values": a,
        "validity_mask": after_validity,
        "failure_reasons": dict(after.get("failure_reasons") or {}),
    }
    structural_state_valid = bool(
        isinstance(before.get("values"), dict)
        and isinstance(after.get("values"), dict)
        and isinstance(before.get("validity_mask"), dict)
        and isinstance(after.get("validity_mask"), dict)
        and list(b) == ordered_names
        and list(a) == ordered_names
        and list(before_validity) == ordered_names
        and list(after_validity) == ordered_names
        and before.get("repo") == after.get("repo")
        and bool(before.get("repository_id"))
        and before.get("repository_id") == after.get("repository_id")
        and before.get("coordinate_schema_digest")
        == metadata["coordinate_schema_digest"]
        and after.get("coordinate_schema_digest")
        == metadata["coordinate_schema_digest"]
        and before.get("schema_version") == STATE_SCHEMA
        and after.get("schema_version") == STATE_SCHEMA
        and before.get("coordinate_schema_version") == COORDINATE_SCHEMA_VERSION
        and after.get("coordinate_schema_version") == COORDINATE_SCHEMA_VERSION
        and list(before.get("ordered_coordinate_names") or ()) == ordered_names
        and list(after.get("ordered_coordinate_names") or ()) == ordered_names
        and list(before.get("ordered_shape_signature") or ())
        == metadata["ordered_shape_signature"]
        and list(after.get("ordered_shape_signature") or ())
        == metadata["ordered_shape_signature"]
        and before.get("scale_digest") == metadata["scale_digest"]
        and after.get("scale_digest") == metadata["scale_digest"]
        and before.get("state_hash") == _sha(before_material)
        and after.get("state_hash") == _sha(after_material)
    )
    coordinate_validity: dict[str, bool] = {}
    delta: dict[str, float | None] = {}
    normalized: dict[str, float | None] = {}
    for coordinate in COORDINATE_SCHEMA:
        name = coordinate.coordinate_id
        before_value = b.get(name)
        after_value = a.get(name)
        before_valid = bool(
            before_validity.get(name) is True
            and type(before_value) is float
            and math.isfinite(before_value)
        )
        after_valid = bool(
            after_validity.get(name) is True
            and type(after_value) is float
            and math.isfinite(after_value)
        )
        valid = before_valid and after_valid
        coordinate_validity[name] = valid
        if not valid:
            delta[name] = None
            normalized[name] = None
            continue
        raw_delta = after_value - before_value
        delta[name] = raw_delta
        normalized[name] = max(
            -1.0,
            min(1.0, raw_delta / coordinate.normalization_scale),
        )
    # Only schema-backed channels participate. Empty families (e.g. M_FEDERATED
    # with no coordinates) must not appear as measured zeros — that would
    # impersonate an observed absence as a real zero residual.
    signed_channel_mass: dict[str, dict[str, float]] = {}
    for channel in sorted(
        {coordinate.channel_family for coordinate in COORDINATE_SCHEMA}
    ):
        values = [
            float(normalized[coordinate.coordinate_id])
            for coordinate in COORDINATE_SCHEMA
            if coordinate.channel_family == channel
            and normalized[coordinate.coordinate_id] is not None
        ]
        signed_channel_mass[channel] = {
            "positive": float(sum(max(0.0, value) for value in values)),
            "negative": float(sum(max(0.0, -value) for value in values)),
            "net": float(sum(values)),
        }
    material = {
        "event_id": event_id,
        "event_kind": event_kind,
        "before_hash": before.get("state_hash"),
        "after_hash": after.get("state_hash"),
        "raw_delta": delta,
        "coordinate_validity": coordinate_validity,
        "coordinate_schema_digest": metadata["coordinate_schema_digest"],
    }
    required = [
        coordinate.coordinate_id
        for coordinate in COORDINATE_SCHEMA
        if coordinate.required_for_conformance
    ]
    valid_required = sum(
        1 for name in required if coordinate_validity.get(name) is True
    )
    complete = structural_state_valid and valid_required == len(required)
    return {
        "schema_version": SCHEMA,
        **material,
        "status": "measured" if complete else "observed_incomplete",
        "before_state": before,
        "after_state": after,
        "delta": delta,
        "normalized_delta": normalized,
        "coordinate_schema_version": COORDINATE_SCHEMA_VERSION,
        "ordered_coordinate_names": list(
            metadata["ordered_coordinate_names"]
        ),
        "ordered_shape_signature": copy.deepcopy(
            metadata["ordered_shape_signature"]
        ),
        "scale_digest": metadata["scale_digest"],
        "valid_required_coordinates": valid_required,
        "required_coordinates": len(required),
        "valid_fraction": valid_required / max(1, len(required)),
        "signed_channel_mass": signed_channel_mass,
        "changed_metrics": [
            name
            for name, value in delta.items()
            if value is not None and abs(value) > 1e-12
        ],
        "measurement_basis": MEASUREMENT_MEASURED_DELTA,
        "policy_eligible": complete,
        "baseline_eligible": complete,
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
        if value is None or name not in METRICS:
            continue
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
    signed_mass = dict(delta_report.get("signed_channel_mass") or {})
    return [
        replace(
            sample,
            source_ids=(event_id,),
            metadata={
                "measurement_basis": MEASUREMENT_MEASURED_DELTA,
                "policy_eligible": bool(delta_report.get("policy_eligible")),
                "baseline_eligible": bool(delta_report.get("baseline_eligible")),
                "delta_receipt_hash": delta_report.get("receipt_hash"),
                "before_hash": delta_report.get("before_hash"),
                "after_hash": delta_report.get("after_hash"),
                "metric_deltas": {name: value for name, value in grouped[sample.channel_family]},
                "directional_activity": signed_mass.get(
                    sample.channel_family,
                    {"positive": 0.0, "negative": 0.0, "net": 0.0},
                ),
            },
        )
        for sample in samples
    ]
