"""Fixed rotation sweep for four-dimensional geometric echo alignment.

This is a bounded sensitivity analysis around :mod:`cortex.geometric_echo`.
It rotates the observed vector through a fixed set of quarter-turns, scores
how much energy remains in the evidence-backed active subspace, and returns a
reversible next-step recommendation.  It never changes routing or telemetry.
"""

from __future__ import annotations

from math import cos, pi, sin
from pathlib import Path
from typing import Any, Mapping, Sequence

from .geometric_echo import AXES, CLAIM, geometric_echo_report, run_geometric_echo


SCHEMA = "cortex-rotated-geometric-echo/1.0"
VERSION = "8.2.7"
GLYPH = "⤨"
PLANE_INDICES = {
    "evidence_geometry": (0, 1),
    "evidence_temporal": (0, 2),
    "evidence_interlock": (0, 3),
    "geometry_temporal": (1, 2),
    "geometry_interlock": (1, 3),
    "temporal_interlock": (2, 3),
}
ROTATION_PLAN: tuple[tuple[str, str | None, int], ...] = (
    ("identity", None, 0),
    *tuple(
        (f"{plane}_{quarter * 90}", plane, quarter)
        for plane in PLANE_INDICES
        for quarter in (1, 2, 3)
    ),
)


def rotate_vector(vector: Sequence[float], plane: str | None, quarter_turn: int) -> list[float]:
    """Apply one fixed quarter-turn in a named coordinate plane."""
    result = [float(value) for value in vector]
    if plane is None:
        return result
    i, j = PLANE_INDICES[plane]
    angle = (int(quarter_turn) % 4) * (pi / 2.0)
    x, y = result[i], result[j]
    result[i] = cos(angle) * x - sin(angle) * y
    result[j] = sin(angle) * x + cos(angle) * y
    return [round(value, 8) for value in result]


def _energy(vector: Sequence[float], indexes: Sequence[int] | None = None) -> float:
    selected = indexes if indexes is not None else range(len(vector))
    return sum(float(vector[index]) ** 2 for index in selected)


def rotated_echo_report(base: Mapping[str, Any]) -> dict[str, Any]:
    """Sweep fixed rotations and identify the best supported-subspace echo."""
    vector = [float(value) for value in (base.get("state_vector") or [])]
    if len(vector) != 4:
        vector = [0.0, 0.0, 0.0, 0.0]
    active_axes = [str(axis) for axis in (base.get("active_axes") or [])]
    support = [index for index, axis in enumerate(AXES) if axis in active_axes]
    if not support:
        support = list(range(4))
    total_energy = _energy(vector)
    rotations: list[dict[str, Any]] = []
    for name, plane, quarter in ROTATION_PLAN:
        rotated = rotate_vector(vector, plane, quarter)
        support_energy = _energy(rotated, support)
        alignment = support_energy / total_energy if total_energy > 1e-12 else 0.0
        norm = total_energy ** 0.5
        concentration = max((abs(value) for value in rotated), default=0.0) / norm if norm else 0.0
        echoed = geometric_echo_report({"vector": rotated, "values": dict(zip(AXES, rotated))})
        rotations.append({
            "name": name,
            "plane": plane,
            "quarter_turn": quarter,
            "angle_degrees": quarter * 90,
            "vector": rotated,
            "alignment": round(alignment, 8),
            "concentration": round(concentration, 8),
            "reconstruction_error": echoed["reconstruction_error"],
            "echo_energy": echoed["echo_energy"],
        })
    ordered = sorted(
        rotations,
        key=lambda item: (-float(item["alignment"]), abs(int(item["quarter_turn"])), str(item["name"])),
    )
    best = ordered[0] if ordered else None
    second = ordered[1] if len(ordered) > 1 else None
    best_alignment = float((best or {}).get("alignment") or 0.0)
    second_alignment = float((second or {}).get("alignment") or 0.0)
    silent_axes = [axis for axis in AXES if axis not in active_axes]
    if total_energy <= 1e-12:
        status = "silent_field"
    elif best_alignment >= 0.95:
        status = "aligned_subspace"
    else:
        status = "mixed_subspace"
    surgery = (
        ["collect_same_epoch_frames"] if "temporal" in silent_axes else []
    ) + (
        ["resolve_interlock_outcomes"] if "interlock" in silent_axes else []
    )
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "axes": list(AXES),
        "base_vector": vector,
        "active_axes": active_axes,
        "support_axes": [AXES[index] for index in support],
        "silent_axes": silent_axes,
        "total_energy": round(total_energy, 8),
        "rotation_count": len(rotations),
        "rotations": rotations,
        "best": best,
        "alignment_margin": round(best_alignment - second_alignment, 8),
        "alignment_unique": bool(best and best_alignment - second_alignment >= 0.05),
        "status": status,
        "surgery": {
            "actions": surgery,
            "mode": "measurement_only" if surgery else "hold_and_observe",
            "policy_effect": False,
            "reversible": True,
        },
        "advisory_only": True,
        "policy_effect": False,
        "claim_boundary": CLAIM + " Rotation alignment is a sensitivity result, not self-organization or subjective perception.",
    }


def run_rotated_echo(
    store: Any,
    repo: str,
    *,
    home: Path | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Run the base echo and fixed rotation sweep; optionally cache telemetry."""
    base = run_geometric_echo(store, repo, home=home, persist=False)
    report = rotated_echo_report(base)
    report["repo"] = repo
    report["body_epoch_id"] = base.get("body_epoch_id")
    report["base_input_fingerprint"] = base.get("input_fingerprint")
    if persist:
        store.set_setting(f"rotated_echo_latest:{repo}", report)
        if home is not None:
            path = Path(home) / "logs" / f"rotated-echo-{repo}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            import json

            path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            report["report_path"] = str(path)
    return report


__all__ = [
    "GLYPH", "PLANE_INDICES", "ROTATION_PLAN", "SCHEMA", "VERSION",
    "rotate_vector", "rotated_echo_report", "run_rotated_echo",
]
