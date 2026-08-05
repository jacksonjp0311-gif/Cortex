"""Bounded four-dimensional geometric pulse/echo telemetry.

The echo field projects already-persisted, advisory Cortex measurements onto
four operational axes: evidence (E), geometry (G), temporal coordination (T),
and informational interlock (I).  Pulses are fixed unit directions; echoes are
dot products with the observed state.  This is a read-only diagnostic, not a
controller, learner, or claim of subjective sensing.
"""

from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA = "cortex-geometric-echo/1.0"
VERSION = "8.2.6"
GLYPH = "⟊"
AXES = ("evidence", "geometry", "temporal", "interlock")
CLAIM = (
    "Four-dimensional geometric echo is read-only operational telemetry. "
    "Pulse/echo alignment is not consciousness, experience, authority, or "
    "permission to mutate host or runtime state."
)

# Four orthogonal probes plus four tetrahedral cross-checks.  Keeping this
# table fixed makes results comparable across runs and prevents an optimizer
# from selecting directions after seeing the response.
PULSE_DIRECTIONS: tuple[tuple[str, tuple[float, float, float, float]], ...] = (
    ("evidence_axis", (1.0, 0.0, 0.0, 0.0)),
    ("geometry_axis", (0.0, 1.0, 0.0, 0.0)),
    ("temporal_axis", (0.0, 0.0, 1.0, 0.0)),
    ("interlock_axis", (0.0, 0.0, 0.0, 1.0)),
    ("tetra_all_plus", (0.5, 0.5, 0.5, 0.5)),
    ("tetra_eg_plus_ti_minus", (0.5, 0.5, -0.5, -0.5)),
    ("tetra_et_plus_gi_minus", (0.5, -0.5, 0.5, -0.5)),
    ("tetra_ei_plus_gt_minus", (0.5, -0.5, -0.5, 0.5)),
)


def _clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return low
    if not math.isfinite(number):
        return low
    return round(max(low, min(high, number)), 8)


def _mean(values: Sequence[Any]) -> float:
    clean: list[float] = []
    for value in values:
        try:
            number = float(value)
            if math.isfinite(number):
                clean.append(number)
        except (TypeError, ValueError):
            continue
    return sum(clean) / len(clean) if clean else 0.0


def _source_axis(report: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    candidate = report.get("candidate_stage") or {}
    source = candidate.get("source_reserve") or {}
    final = report.get("final_stage") or {}
    source_final = final.get("source_reserve") or {}
    value = source.get("recall")
    if value is None:
        value = source_final.get("recall")
    available = value is not None
    return _clamp(value) if available else 0.0, {
        "candidate_recall": _clamp(source.get("recall")) if source.get("recall") is not None else None,
        "final_recall": _clamp(source_final.get("recall")) if source_final.get("recall") is not None else None,
        "available": available,
        "gate": 1 if available else 0,
        "silence_reason": None if available else "source_admission_unmeasured",
    }


def _geometry_axis(report: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    share_present = report.get("top_decile_degree_share") is not None
    share = _clamp(report.get("top_decile_degree_share")) if share_present else 0.0
    deconcentration = _clamp(1.0 - share) if share_present else 0.0
    candidates = report.get("candidates") or report.get("top_candidates") or []
    bridge_values = [
        item.get("bridge_potential") for item in candidates if isinstance(item, Mapping)
    ]
    bridge_present = any(value is not None for value in bridge_values)
    bridge_potential = _clamp(_mean(bridge_values)) if bridge_present else 0.0
    # Geometry is intentionally split: dispersion penalizes hubs while bridge
    # potential rewards cross-region connectors.  Neither component mutates
    # the graph or implies that a hub is harmful.
    available = share_present or bridge_present
    value = _clamp(0.5 * deconcentration + 0.5 * bridge_potential) if available else 0.0
    return value, {
        "top_decile_degree_share": share if share_present else None,
        "deconcentration": deconcentration if share_present else None,
        "mean_bridge_potential": bridge_potential if bridge_present else None,
        "candidate_count": len(candidates),
        "available": available,
        "gate": 1 if available else 0,
        "silence_reason": None if available else "geometry_unmeasured",
    }


def _temporal_axis(report: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    best = report.get("best") or {}
    status = str(report.get("status") or "missing")
    # A non-candidate peak is deliberately silenced by the gate mask, not
    # recorded as a measured zero.  Unmeasured ≠ measured-and-equal-to-zero.
    gated = status == "resonant_candidate"
    value = best.get("coherence") if gated else 0.0
    return _clamp(value), {
        "status": status,
        "frame_count": int(report.get("frame_count") or 0),
        "all_frame_count": int(report.get("all_frame_count") or 0),
        "best_frequency": best.get("frequency"),
        "available": gated,
        "gate": 1 if gated else 0,
        "silence_reason": None if gated else "no_stable_temporal_peak",
    }


def _interlock_axis(report: Mapping[str, Any]) -> tuple[float, dict[str, Any]]:
    ready = bool(report.get("data_ready"))
    value = report.get("mean_alignment") if ready else 0.0
    counts = report.get("counts") or {}
    return _clamp(value), {
        "data_ready": ready,
        "mean_alignment": _clamp(report.get("mean_alignment")),
        "resolved": int(counts.get("resolved") or 0),
        "valid": int(counts.get("valid") or 0),
        "candidates": int(counts.get("candidates") or 0),
        "available": ready,
        "gate": 1 if ready else 0,
        "silence_reason": None if ready else "outcome_evidence_not_ready",
    }


def operational_state(store: Any, repo: str) -> dict[str, Any]:
    """Read the four latest advisory surfaces and return a bounded state."""
    source = store.get_setting(f"source_admission_latest:{repo}", {}) or {}
    geometry = store.get_setting(f"bridge_shadow_latest:{repo}", {}) or {}
    temporal = store.get_setting(f"resonance_sweep_latest:{repo}", {}) or {}
    interlock = store.get_setting(f"interlock_shadow_latest:{repo}", {}) or {}
    values = {}
    components = {}
    gate_mask: dict[str, int] = {}
    for axis, fn, report in (
        ("evidence", _source_axis, source),
        ("geometry", _geometry_axis, geometry),
        ("temporal", _temporal_axis, temporal),
        ("interlock", _interlock_axis, interlock),
    ):
        values[axis], components[axis] = fn(report)
        gate_mask[axis] = int(
            components[axis].get("gate", 1 if components[axis].get("available") else 0)
        )
    vector = [values[axis] for axis in AXES]
    mask = [gate_mask[axis] for axis in AXES]
    masked = [float(mask[index]) * float(vector[index]) for index in range(4)]
    return {
        "axes": list(AXES),
        "vector": vector,
        "masked_vector": masked,
        "values": values,
        "gate_mask": gate_mask,
        "gate_vector": mask,
        "observability_rank": int(sum(mask)),
        "components": components,
        "sources": {
            "evidence": f"source_admission_latest:{repo}",
            "geometry": f"bridge_shadow_latest:{repo}",
            "temporal": f"resonance_sweep_latest:{repo}",
            "interlock": f"interlock_shadow_latest:{repo}",
        },
        "observability_law": (
            "y = P D_g x reconstructs the evidence-backed active subspace; "
            "silenced-because-unmeasured ≠ measured-and-equal-to-zero"
        ),
    }


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(left, right))


def _norm(vector: Sequence[float]) -> float:
    return math.sqrt(sum(float(value) ** 2 for value in vector))


def geometric_echo_report(
    state: Mapping[str, Any],
    *,
    pulse_directions: Sequence[tuple[str, Sequence[float]]] = PULSE_DIRECTIONS,
) -> dict[str, Any]:
    """Pulse fixed directions through a state and return the measured echoes."""
    vector = [_clamp(value) for value in state.get("vector", [])]
    if len(vector) != 4:
        vector = [0.0, 0.0, 0.0, 0.0]
    gate = state.get("gate_vector") or state.get("gate_mask")
    if isinstance(gate, Mapping):
        gate_vector = [1 if gate.get(axis) else 0 for axis in AXES]
    elif isinstance(gate, Sequence) and len(gate) == 4:
        gate_vector = [1 if value else 0 for value in gate]
    else:
        # Absent gates: treat nonzero coordinates as available (legacy path).
        gate_vector = [1 if abs(value) > 1e-12 else 0 for value in vector]
        if all(value == 0 for value in gate_vector) and any(
            abs(value) <= 1e-12 for value in vector
        ):
            # Fully silent state with no mask still has rank 0.
            gate_vector = [0, 0, 0, 0]
    masked = [float(gate_vector[index]) * float(vector[index]) for index in range(4)]
    field_norm = _norm(masked)
    echoes: list[dict[str, Any]] = []
    echo_energy = 0.0
    for name, direction in pulse_directions:
        norm = _norm(direction)
        unit = [float(value) / norm for value in direction] if norm else [0.0] * 4
        # Observe the gated state: y = P D_g x.
        echo = _dot(unit, masked)
        echo_energy += echo * echo
        echoes.append({
            "name": str(name),
            "direction": [round(value, 8) for value in unit],
            "echo": round(echo, 8),
            "magnitude": round(abs(echo), 8),
            "polarity": "positive" if echo > 1e-8 else "negative" if echo < -1e-8 else "silent",
        })
    axis_echoes = echoes[:4]
    # Axis probes alone reconstruct the masked state; the tetrahedral probes
    # form the second orthonormal basis of the unit-norm 2-tight frame.
    reconstruction = [item["echo"] for item in axis_echoes]
    reconstruction_error = _norm([a - b for a, b in zip(masked, reconstruction)])
    # For the eight unit probes, P^T P = 2 I ⇒ ||y||² = 2 ||D_g x||².
    tight_frame_expected = 2.0 * (field_norm ** 2)
    tight_frame_residual = abs(echo_energy - tight_frame_expected)
    magnitudes = [abs(value) for value in masked]
    dominant_index = max(range(4), key=lambda index: magnitudes[index]) if masked else 0
    active = [
        axis
        for axis, value, open_gate in zip(AXES, masked, gate_vector)
        if open_gate and value >= 0.25
    ]
    silent_unmeasured = [
        axis for axis, open_gate in zip(AXES, gate_vector) if not open_gate
    ]
    silent_zero = [
        axis
        for axis, value, open_gate in zip(AXES, masked, gate_vector)
        if open_gate and value < 0.05
    ]
    silent = silent_unmeasured + silent_zero
    observability_rank = int(sum(gate_vector))
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "axes": list(AXES),
        "state_vector": vector,
        "masked_state_vector": [round(value, 8) for value in masked],
        "gate_mask": {axis: gate_vector[index] for index, axis in enumerate(AXES)},
        "observability_rank": observability_rank,
        "state": state.get("values") or dict(zip(AXES, vector)),
        "pulses": echoes,
        "axis_echoes": {axis: item["echo"] for axis, item in zip(AXES, axis_echoes)},
        "field_norm": round(field_norm, 8),
        "echo_energy": round(echo_energy, 8),
        "tight_frame": {
            "property": "P^T P = 2 I_4",
            "expected_echo_energy": round(tight_frame_expected, 8),
            "observed_echo_energy": round(echo_energy, 8),
            "residual": round(tight_frame_residual, 8),
            "holds": tight_frame_residual <= 1e-8,
        },
        "reconstruction": reconstruction,
        "reconstruction_error": round(reconstruction_error, 8),
        "dominant_axis": AXES[dominant_index] if observability_rank else None,
        "active_axes": active,
        "silent_axes": silent,
        "silent_unmeasured_axes": silent_unmeasured,
        "silent_zero_axes": silent_zero,
        "field_condition": (
            "silent" if observability_rank == 0 or field_norm <= 1e-8 else
            "sparse" if len(active) <= 1 else
            "partial" if observability_rank < 4 else "full"
        ),
        "pulse_count": len(echoes),
        "advisory_only": True,
        "policy_effect": False,
        "claim_boundary": CLAIM,
    }


def run_geometric_echo(
    store: Any,
    repo: str,
    *,
    home: Path | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Run the read-only pulse/echo probe; optionally cache its report."""
    state = operational_state(store, repo)
    report = geometric_echo_report(state)
    report["repo"] = repo
    report["body_epoch_id"] = (
        (store.get_setting(f"resonance_sweep_latest:{repo}", {}) or {}).get("body_epoch_id")
        or None
    )
    report["input_fingerprint"] = sha256(
        repr((state.get("vector"), state.get("sources"))).encode("utf-8")
    ).hexdigest()
    if persist:
        store.set_setting(f"geometric_echo_latest:{repo}", report)
        if home is not None:
            path = Path(home) / "logs" / f"geometric-echo-{repo}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            import json

            path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            report["report_path"] = str(path)
    return report


__all__ = [
    "AXES", "CLAIM", "GLYPH", "PULSE_DIRECTIONS", "SCHEMA", "VERSION",
    "geometric_echo_report", "operational_state", "run_geometric_echo",
]
