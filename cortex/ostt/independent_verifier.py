"""Independent activation-transition recomputation for v8.3.3.

This module deliberately does not import or call ``measured_delta``.  It
reconstructs the transition from raw snapshots and the frozen coordinate
definitions, then compares that reconstruction with the persisted vector.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any

from ..cognitive.measured import (
    COORDINATE_SCHEMA,
    COORDINATE_SCHEMA_VERSION,
    STATE_SCHEMA,
    coordinate_schema_payload,
)

VERIFIER_SCHEMA = "cortex-independent-activation-verifier/1.0"
VERIFIER_IMPLEMENTATION_VERSION = "v8.3.3-independent-recompute/1"
VERIFIER_ALGORITHM = (
    "ordered nullable float64 snapshots; delta=after-before; "
    "normalized=clip(delta/declared_scale,-1,1); weighted residual panel"
)
VERIFIER_DIGEST = ""
CONFORMANCE_TOLERANCE = 1e-12
EPSILON = 1e-12
MEASUREMENT_SUBJECT_FIELDS = (
    "schema_version",
    "operator_id",
    "input_type",
    "output_type",
    "input",
    "measured_transition",
    "observed_output",
    "reference_output",
    "residual_panel",
    "B_rms",
    "B_max",
    "B_invalid",
    "channel_burdens",
    "verifier_implementation_version",
    "verifier_digest",
    "repository_id",
    "repo",
    "event_id",
    "case_id",
    "comparison_arm",
    "controller",
    "realized_action",
    "task_hash",
    "body_epoch_id",
    "measurement_cohort_id",
    "coordinate_schema_version",
    "coordinate_schema_digest",
    "ordered_coordinate_names",
    "ordered_shape_signature",
    "scale_digest",
    "valid_fraction",
)
REQUIRED_CONFORMANCE_INVARIANTS = frozenset(
    {
        "host_immutable",
        "epoch_current",
        "cohort_current",
        "coordinate_schema_match",
        "measurement_complete",
        "before_hash_valid",
        "after_hash_valid",
        "delta_recomputed",
        "exactly_once_event",
        "receipt_hash_valid",
    }
)


def _sha(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def measurement_subject(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the immutable scientific subject covered by the witness."""
    return {field: payload.get(field) for field in MEASUREMENT_SUBJECT_FIELDS}


def measurement_subject_hash(payload: Mapping[str, Any]) -> str:
    """Hash the complete activation-measurement subject deterministically."""
    return _sha(measurement_subject(payload))


def _same_payload(left: Any, right: Any) -> bool:
    try:
        return json.dumps(
            left,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        ) == json.dumps(
            right,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            default=str,
        )
    except (TypeError, ValueError):
        return False


def _same_number(left: Any, right: Any, *, tolerance: float = EPSILON) -> bool:
    if not _finite_number(left) or not _finite_number(right):
        return False
    return math.isclose(
        float(left),
        float(right),
        rel_tol=0.0,
        abs_tol=float(tolerance),
    )


def _state_material(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "repo": snapshot.get("repo"),
        "repository_id": snapshot.get("repository_id"),
        "coordinate_schema_digest": snapshot.get("coordinate_schema_digest"),
        "values": dict(snapshot.get("values") or {}),
        "validity_mask": dict(snapshot.get("validity_mask") or {}),
        "failure_reasons": dict(snapshot.get("failure_reasons") or {}),
    }


def verify_state_hash(snapshot: Mapping[str, Any]) -> bool:
    claimed = str(snapshot.get("state_hash") or "")
    return bool(claimed) and claimed == _sha(_state_material(snapshot))


def structural_shape_signature(value: Any) -> Any:
    """Return a type-preserving signature; equal flat length is insufficient."""
    if isinstance(value, bool):
        return {"kind": "bool"}
    if isinstance(value, Real):
        return {"kind": "number", "type": type(value).__name__}
    if isinstance(value, Mapping):
        return {
            "kind": "mapping",
            "items": [
                [str(key), structural_shape_signature(value[key])]
                for key in value
            ],
        }
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return {
            "kind": "sequence",
            "length": len(value),
            "items": [structural_shape_signature(item) for item in value],
        }
    if value is None:
        return {"kind": "null"}
    return {"kind": type(value).__name__}


def _finite_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, Real) and math.isfinite(float(value))


def _finite_float64(value: Any) -> bool:
    """Python ``float`` is the runtime's IEEE-754 binary64 representation."""
    return type(value) is float and math.isfinite(value)


def independently_recompute_transition(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute from raw typed state only; never consume persisted deltas."""
    metadata = coordinate_schema_payload()
    expected_digest = str(metadata["coordinate_schema_digest"])
    before_values = before.get("values")
    after_values = after.get("values")
    before_mask = before.get("validity_mask")
    after_mask = after.get("validity_mask")
    mapping_shape = all(
        isinstance(value, Mapping)
        for value in (before_values, after_values, before_mask, after_mask)
    )
    before_values = dict(before_values or {}) if isinstance(before_values, Mapping) else {}
    after_values = dict(after_values or {}) if isinstance(after_values, Mapping) else {}
    before_mask = dict(before_mask or {}) if isinstance(before_mask, Mapping) else {}
    after_mask = dict(after_mask or {}) if isinstance(after_mask, Mapping) else {}

    ordered_names = [coordinate.coordinate_id for coordinate in COORDINATE_SCHEMA]
    ordered_shape = list(metadata["ordered_shape_signature"])
    exact_keys = (
        list(before_values) == ordered_names
        and list(after_values) == ordered_names
        and list(before_mask) == ordered_names
        and list(after_mask) == ordered_names
        and list(before.get("ordered_coordinate_names") or ()) == ordered_names
        and list(after.get("ordered_coordinate_names") or ()) == ordered_names
    )
    schema_match = (
        before.get("coordinate_schema_digest") == expected_digest
        and after.get("coordinate_schema_digest") == expected_digest
    )
    metadata_match = bool(
        before.get("schema_version") == STATE_SCHEMA
        and after.get("schema_version") == STATE_SCHEMA
        and before.get("coordinate_schema_version") == COORDINATE_SCHEMA_VERSION
        and after.get("coordinate_schema_version") == COORDINATE_SCHEMA_VERSION
        and list(before.get("ordered_shape_signature") or ()) == ordered_shape
        and list(after.get("ordered_shape_signature") or ()) == ordered_shape
        and before.get("scale_digest") == metadata["scale_digest"]
        and after.get("scale_digest") == metadata["scale_digest"]
    )
    raw_delta: dict[str, float | None] = {}
    normalized_delta: dict[str, float | None] = {}
    validity: dict[str, bool] = {}
    failure_reasons: dict[str, str | None] = {}
    for coordinate in COORDINATE_SCHEMA:
        name = coordinate.coordinate_id
        valid = (
            before_mask.get(name) is True
            and after_mask.get(name) is True
            and _finite_float64(before_values.get(name))
            and _finite_float64(after_values.get(name))
        )
        validity[name] = valid
        if not valid:
            raw_delta[name] = None
            normalized_delta[name] = None
            reasons = []
            if before_mask.get(name) is not True or not _finite_float64(
                before_values.get(name)
            ):
                reasons.append("before_invalid")
            if after_mask.get(name) is not True or not _finite_float64(
                after_values.get(name)
            ):
                reasons.append("after_invalid")
            failure_reasons[name] = "+".join(reasons) or "invalid"
            continue
        delta = float(after_values[name]) - float(before_values[name])
        raw_delta[name] = delta
        normalized_delta[name] = max(
            -1.0,
            min(1.0, delta / coordinate.normalization_scale),
        )
        failure_reasons[name] = None

    required = [
        coordinate.coordinate_id
        for coordinate in COORDINATE_SCHEMA
        if coordinate.required_for_conformance
    ]
    valid_required = sum(1 for name in required if validity[name])
    complete = (
        mapping_shape
        and exact_keys
        and schema_match
        and metadata_match
        and valid_required == len(required)
    )
    signed_channel_mass: dict[str, dict[str, float]] = {}
    for channel in sorted(
        {coordinate.channel_family for coordinate in COORDINATE_SCHEMA}
    ):
        values = [
            float(normalized_delta[coordinate.coordinate_id])
            for coordinate in COORDINATE_SCHEMA
            if coordinate.channel_family == channel
            and normalized_delta[coordinate.coordinate_id] is not None
        ]
        # Always emit IEEE float zeros so empty channels never drift to int 0.
        signed_channel_mass[channel] = {
            "positive": float(sum(max(0.0, value) for value in values)),
            "negative": float(sum(max(0.0, -value) for value in values)),
            "net": float(sum(values)),
        }
    return {
        "schema_version": VERIFIER_SCHEMA,
        "verifier_implementation_version": VERIFIER_IMPLEMENTATION_VERSION,
        "verifier_digest": VERIFIER_DIGEST,
        "coordinate_schema_digest": expected_digest,
        "mapping_shape_valid": mapping_shape,
        "ordered_shape_valid": exact_keys,
        "coordinate_schema_match": schema_match,
        "snapshot_metadata_match": metadata_match,
        "before_hash_valid": verify_state_hash(before),
        "after_hash_valid": verify_state_hash(after),
        "raw_delta": raw_delta,
        "normalized_delta": normalized_delta,
        "coordinate_validity": validity,
        "signed_channel_mass": signed_channel_mass,
        "failure_reasons": failure_reasons,
        "valid_required_coordinates": valid_required,
        "required_coordinates": len(required),
        "valid_fraction": valid_required / max(1, len(required)),
        "measurement_complete": complete,
    }


def _ordered_coordinate_map(
    value: Any, ordered_names: Sequence[str]
) -> dict[str, Any] | None:
    """Project a coordinate map onto schema order without treating key order as data.

    Canonical JSON may sort keys; that must not break structural conformance.
    Missing/extra coordinates remain a hard structural failure.
    """
    if not isinstance(value, Mapping):
        return None
    keys = [str(key) for key in value]
    if len(keys) != len(ordered_names) or set(keys) != set(ordered_names):
        return None
    return {name: value[name] for name in ordered_names}


def residual_panel(
    persisted_normalized: Any,
    independently_recomputed: Mapping[str, float | None],
    coordinate_validity: Mapping[str, bool],
    *,
    tolerance: float = CONFORMANCE_TOLERANCE,
) -> dict[str, Any]:
    """Compute coordinate, channel, RMS, max, and invalid burdens."""
    ordered_names = [coordinate.coordinate_id for coordinate in COORDINATE_SCHEMA]
    ordered_persisted = _ordered_coordinate_map(persisted_normalized, ordered_names)
    ordered_reference = _ordered_coordinate_map(
        independently_recomputed, ordered_names
    )
    structural_match = ordered_persisted is not None and ordered_reference is not None
    persisted = ordered_persisted or {}
    reference_map = ordered_reference or {}
    residual_vector: dict[str, float | None] = {}
    absolute_error: dict[str, float | None] = {}
    weighted_square_sum = 0.0
    total_weight = 0.0
    max_burden = 0.0
    channel_squares: dict[str, float] = {}
    channel_weights: dict[str, float] = {}
    valid_required = 0
    required_count = 0
    numeric_match = True
    for coordinate in COORDINATE_SCHEMA:
        name = coordinate.coordinate_id
        if coordinate.required_for_conformance:
            required_count += 1
        valid = coordinate_validity.get(name) is True
        observed = persisted.get(name)
        reference = reference_map.get(name)
        if (
            not valid
            or not _finite_float64(observed)
            or not _finite_float64(reference)
        ):
            residual_vector[name] = None
            absolute_error[name] = None
            if coordinate.required_for_conformance:
                numeric_match = False
            continue
        if coordinate.required_for_conformance:
            valid_required += 1
        error = float(observed) - float(reference)
        scaled = error / (coordinate.normalization_scale + EPSILON)
        absolute = abs(error)
        residual_vector[name] = scaled
        absolute_error[name] = absolute
        weight = float(coordinate.criticality_weight)
        weighted_square_sum += weight * scaled * scaled
        total_weight += weight
        max_burden = max(max_burden, abs(scaled))
        channel = coordinate.channel_family
        channel_squares[channel] = channel_squares.get(channel, 0.0) + (
            weight * scaled * scaled
        )
        channel_weights[channel] = channel_weights.get(channel, 0.0) + weight
        if absolute > float(tolerance):
            numeric_match = False

    b_rms = math.sqrt(weighted_square_sum / (total_weight + EPSILON))
    b_invalid = 1.0 - (valid_required / max(1, required_count))
    channel_burdens = {
        channel: math.sqrt(
            channel_squares[channel] / (channel_weights[channel] + EPSILON)
        )
        for channel in sorted(channel_squares)
    }
    conforms = (
        structural_match
        and numeric_match
        and valid_required == required_count
        and b_rms <= float(tolerance)
        and max_burden <= float(tolerance)
        and b_invalid == 0.0
    )
    return {
        "schema_version": "cortex-activation-residual-panel/1.0",
        "tolerance": float(tolerance),
        "structural_shape_match": structural_match,
        "persisted_shape_signature": structural_shape_signature(
            persisted_normalized
        ),
        "reference_shape_signature": structural_shape_signature(
            independently_recomputed
        ),
        "residual_vector": residual_vector,
        "per_coordinate_absolute_error": absolute_error,
        "channel_burdens": channel_burdens,
        "B_rms": b_rms,
        "B_max": max_burden,
        "B_invalid": b_invalid,
        "conforms": conforms,
    }


def validate_conformance_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Independently validate the scientific content of a Gate-B receipt.

    This function has no store or epoch access.  It proves that the raw
    snapshots, persisted transition, residual panel, schema binding, witness,
    and structured invariant claims agree internally.  The caller must still
    verify the canonical ledger chain and current epoch/cohort separately.
    """
    errors: list[str] = []
    if not isinstance(payload, Mapping):
        return {
            "valid": False,
            "errors": ["receipt_not_mapping"],
            "recomputed": {},
            "residual_panel": {"conforms": False},
        }

    transition = payload.get("measured_transition")
    if not isinstance(transition, Mapping):
        transition = {}
        errors.append("measured_transition_missing")
    before = transition.get("before_state")
    after = transition.get("after_state")
    if not isinstance(before, Mapping):
        before = {}
        errors.append("before_state_missing")
    if not isinstance(after, Mapping):
        after = {}
        errors.append("after_state_missing")

    try:
        recomputed = independently_recompute_transition(before, after)
        panel = residual_panel(
            payload.get("observed_output"),
            recomputed.get("normalized_delta") or {},
            recomputed.get("coordinate_validity") or {},
        )
    except Exception as exc:
        recomputed = {"error": f"{type(exc).__name__}:{exc}"}
        panel = {"conforms": False}
        errors.append("independent_recomputation_failed")

    metadata = coordinate_schema_payload()
    expected_digest = str(metadata["coordinate_schema_digest"])
    expected_names = list(metadata["ordered_coordinate_names"])
    expected_shape = list(metadata["ordered_shape_signature"])
    expected_scale_digest = str(metadata["scale_digest"])
    expected_schema_version = str(metadata["coordinate_schema_version"])
    schema_checks = {
        "coordinate_schema_digest": payload.get("coordinate_schema_digest")
        == expected_digest,
        "coordinate_schema_version": payload.get("coordinate_schema_version")
        == expected_schema_version,
        "ordered_coordinate_names": list(
            payload.get("ordered_coordinate_names") or ()
        )
        == expected_names,
        "ordered_shape_signature": list(
            payload.get("ordered_shape_signature") or ()
        )
        == expected_shape,
        "scale_digest": payload.get("scale_digest") == expected_scale_digest,
    }
    errors.extend(
        f"schema_binding_invalid:{name}"
        for name, passed in schema_checks.items()
        if not passed
    )

    repository_id = str(payload.get("repository_id") or "")
    repo = str(payload.get("repo") or "")
    observation_input = payload.get("input")
    if not isinstance(observation_input, Mapping):
        observation_input = {}
        errors.append("activation_observation_input_missing")
    identity_checks = {
        "repository_id": bool(repository_id)
        and observation_input.get("repository_id") == repository_id
        and before.get("repository_id") == repository_id
        and after.get("repository_id") == repository_id,
        "repo": bool(repo)
        and before.get("repo") == repo
        and after.get("repo") == repo,
        "input_schema": observation_input.get("coordinate_schema_digest")
        == expected_digest,
        "input_type": observation_input.get("type_id")
        == "ActivationObservationInput",
        "input_valid": observation_input.get("valid") is True,
        "input_epoch": bool(observation_input.get("pre_epoch_id"))
        and bool(payload.get("body_epoch_id")),
    }
    errors.extend(
        f"identity_binding_invalid:{name}"
        for name, passed in identity_checks.items()
        if not passed
    )

    transition_checks = {
        "raw_delta": _same_payload(
            transition.get("raw_delta"), recomputed.get("raw_delta")
        ),
        "normalized_delta": _same_payload(
            transition.get("normalized_delta"),
            recomputed.get("normalized_delta"),
        ),
        "coordinate_validity": _same_payload(
            transition.get("coordinate_validity"),
            recomputed.get("coordinate_validity"),
        ),
        "signed_channel_mass": _same_payload(
            transition.get("signed_channel_mass"),
            recomputed.get("signed_channel_mass"),
        ),
        "transition_type": transition.get("type_id")
        == "MeasuredActivationTransition",
        "transition_valid": transition.get("valid") is True,
        "observed_output": _same_payload(
            payload.get("observed_output"), transition.get("normalized_delta")
        ),
        "reference_output": _same_payload(
            payload.get("reference_output"),
            recomputed.get("normalized_delta"),
        ),
        "event_id": bool(payload.get("event_id"))
        and transition.get("event_id") == payload.get("event_id"),
        "verifier_version": payload.get("verifier_implementation_version")
        == VERIFIER_IMPLEMENTATION_VERSION,
        "verifier_digest": payload.get("verifier_digest") == VERIFIER_DIGEST,
    }
    errors.extend(
        f"transition_conformance_invalid:{name}"
        for name, passed in transition_checks.items()
        if not passed
    )

    stored_panel = payload.get("residual_panel")
    if not isinstance(stored_panel, Mapping):
        stored_panel = {}
        errors.append("residual_panel_missing")
    panel_checks = {
        "tolerance": _same_number(
            stored_panel.get("tolerance"), CONFORMANCE_TOLERANCE
        ),
        "residual_vector": _same_payload(
            stored_panel.get("residual_vector"), panel.get("residual_vector")
        ),
        "per_coordinate_absolute_error": _same_payload(
            stored_panel.get("per_coordinate_absolute_error"),
            panel.get("per_coordinate_absolute_error"),
        ),
        "channel_burdens": _same_payload(
            stored_panel.get("channel_burdens"), panel.get("channel_burdens")
        )
        and _same_payload(payload.get("channel_burdens"), panel.get("channel_burdens")),
        "B_rms": _same_number(payload.get("B_rms"), panel.get("B_rms"))
        and _same_number(stored_panel.get("B_rms"), panel.get("B_rms")),
        "B_max": _same_number(payload.get("B_max"), panel.get("B_max"))
        and _same_number(stored_panel.get("B_max"), panel.get("B_max")),
        "B_invalid": _same_number(
            payload.get("B_invalid"), panel.get("B_invalid")
        )
        and _same_number(stored_panel.get("B_invalid"), panel.get("B_invalid")),
        "conforms": stored_panel.get("conforms") is True
        and panel.get("conforms") is True,
        "valid_fraction": _same_number(
            payload.get("valid_fraction"), recomputed.get("valid_fraction")
        )
        and _same_number(payload.get("valid_fraction"), 1.0),
    }
    errors.extend(
        f"residual_panel_invalid:{name}"
        for name, passed in panel_checks.items()
        if not passed
    )

    claimed_subject_hash = str(payload.get("measurement_subject_hash") or "")
    expected_subject_hash = measurement_subject_hash(payload)
    if not claimed_subject_hash or claimed_subject_hash != expected_subject_hash:
        errors.append("measurement_subject_hash_invalid")

    witness = payload.get("measurement_witness")
    if not isinstance(witness, Mapping):
        witness = {}
        errors.append("measurement_witness_missing")
    expected_evidence_hashes = [
        str(before.get("state_hash") or ""),
        str(after.get("state_hash") or ""),
        VERIFIER_DIGEST,
        expected_digest,
    ]
    witness_material = {
        "witness_kind": "MEASUREMENT",
        "verifier": "cortex.ostt.independent_verifier",
        "subject_receipt_hash": expected_subject_hash,
        "evidence_hashes": expected_evidence_hashes,
        "passed": True,
    }
    witness_checks = {
        "kind": witness.get("witness_kind") == "MEASUREMENT",
        "verifier": witness.get("verifier")
        == "cortex.ostt.independent_verifier",
        "subject": witness.get("subject_receipt_hash") == expected_subject_hash,
        "evidence": _same_payload(
            witness.get("evidence_hashes"), expected_evidence_hashes
        ),
        "passed": witness.get("passed") is True,
        "witness_id": witness.get("witness_id")
        == "mw_" + _sha(witness_material)[:24],
        "issued_at": _finite_number(witness.get("issued_at")),
    }
    errors.extend(
        f"measurement_witness_invalid:{name}"
        for name, passed in witness_checks.items()
        if not passed
    )

    invariant_values = payload.get("invariant_results")
    if not isinstance(invariant_values, Sequence) or isinstance(
        invariant_values, (str, bytes, bytearray)
    ):
        invariant_values = ()
        errors.append("invariant_results_invalid")
    invariant_map: dict[str, Mapping[str, Any]] = {}
    for item in invariant_values:
        if not isinstance(item, Mapping):
            errors.append("invariant_result_not_mapping")
            continue
        invariant_id = str(item.get("invariant_id") or "")
        if not invariant_id:
            errors.append("invariant_id_missing")
            continue
        if invariant_id in invariant_map:
            errors.append(f"invariant_duplicate:{invariant_id}")
            continue
        invariant_map[invariant_id] = item
        if item.get("passed") is not True:
            errors.append(f"invariant_failed:{invariant_id}")
        if not isinstance(item.get("evidence_ids"), Sequence) or isinstance(
            item.get("evidence_ids"), (str, bytes, bytearray)
        ):
            errors.append(f"invariant_evidence_invalid:{invariant_id}")
        if not str(item.get("reason") or "").strip():
            errors.append(f"invariant_reason_missing:{invariant_id}")
        for field_name in ("expected", "observed"):
            if field_name not in item:
                errors.append(
                    f"invariant_structure_invalid:{invariant_id}:{field_name}"
                )
    errors.extend(
        f"invariant_missing:{invariant_id}"
        for invariant_id in sorted(
            REQUIRED_CONFORMANCE_INVARIANTS - set(invariant_map)
        )
    )

    host_invariant = invariant_map.get("host_immutable") or {}
    if not (
        bool(host_invariant.get("expected"))
        and host_invariant.get("expected") == host_invariant.get("observed")
    ):
        errors.append("invariant_evidence_mismatch:host_immutable")
    schema_invariant = invariant_map.get("coordinate_schema_match") or {}
    if not (
        schema_invariant.get("expected") == expected_digest
        and schema_invariant.get("observed") == expected_digest
    ):
        errors.append("invariant_evidence_mismatch:coordinate_schema_match")
    complete_invariant = invariant_map.get("measurement_complete") or {}
    if not (
        _same_number(complete_invariant.get("expected"), 1.0)
        and _same_number(
            complete_invariant.get("observed"), recomputed.get("valid_fraction")
        )
    ):
        errors.append("invariant_evidence_mismatch:measurement_complete")
    for invariant_id, recomputed_key in (
        ("before_hash_valid", "before_hash_valid"),
        ("after_hash_valid", "after_hash_valid"),
    ):
        item = invariant_map.get(invariant_id) or {}
        if not (
            item.get("expected") is True
            and item.get("observed") is recomputed.get(recomputed_key) is True
        ):
            errors.append(f"invariant_evidence_mismatch:{invariant_id}")
    delta_invariant = invariant_map.get("delta_recomputed") or {}
    delta_observed = delta_invariant.get("observed")
    if not isinstance(delta_observed, Mapping) or not (
        _same_number(delta_observed.get("B_rms"), panel.get("B_rms"))
        and _same_number(delta_observed.get("B_max"), panel.get("B_max"))
    ):
        errors.append("invariant_evidence_mismatch:delta_recomputed")
    receipt_hash_invariant = invariant_map.get("receipt_hash_valid") or {}
    if claimed_subject_hash not in set(
        str(value) for value in receipt_hash_invariant.get("evidence_ids") or ()
    ):
        errors.append("invariant_evidence_mismatch:receipt_hash_valid")

    boundary_checks = {
        "status": payload.get("status") == "conformance_measured",
        "policy_effect": payload.get("policy_effect") is False,
        "update_authorized": payload.get("update_authorized") is False,
        "advisory_only": payload.get("advisory_only") is True,
    }
    errors.extend(
        f"claim_boundary_invalid:{name}"
        for name, passed in boundary_checks.items()
        if not passed
    )
    return {
        "valid": not errors,
        "errors": errors,
        "recomputed": recomputed,
        "residual_panel": panel,
        "measurement_subject_hash": expected_subject_hash,
        "schema_checks": schema_checks,
        "identity_checks": identity_checks,
        "transition_checks": transition_checks,
        "panel_checks": panel_checks,
        "witness_checks": witness_checks,
    }


def _implementation_digest() -> str:
    material = {
        "version": VERIFIER_IMPLEMENTATION_VERSION,
        "algorithm": VERIFIER_ALGORITHM,
        "coordinate_schema_digest": coordinate_schema_payload()[
            "coordinate_schema_digest"
        ],
        "implementation": "\n".join(
            inspect.getsource(function)
            for function in (
                independently_recompute_transition,
                residual_panel,
                validate_conformance_payload,
            )
        ),
    }
    return _sha(material)


VERIFIER_DIGEST = _implementation_digest()


__all__ = [
    "CONFORMANCE_TOLERANCE",
    "EPSILON",
    "MEASUREMENT_SUBJECT_FIELDS",
    "REQUIRED_CONFORMANCE_INVARIANTS",
    "VERIFIER_DIGEST",
    "VERIFIER_IMPLEMENTATION_VERSION",
    "VERIFIER_SCHEMA",
    "independently_recompute_transition",
    "measurement_subject",
    "measurement_subject_hash",
    "residual_panel",
    "structural_shape_signature",
    "validate_conformance_payload",
    "verify_state_hash",
]
