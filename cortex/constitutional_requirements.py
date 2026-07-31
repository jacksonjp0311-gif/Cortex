"""v7.1 Operation requirements over four-axis constitutional coordinates."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .constitutional_geometry import (
    AXIS_ORDER,
    CLAIM,
    ConstitutionalCoordinate,
    coordinate_from_bits,
)

SCHEMA = "cortex-constitutional-requirements/1.0"

# Required axes per operation: 1 = required valid, None = not required
# Order: evidence, authority, epoch, witness
OPERATION_REQUIREMENTS: dict[str, tuple[int | None, int | None, int | None, int | None]] = {
    "retrieve": (1, None, 1, None),
    "adapt": (1, 1, 1, None),
    "promote": (1, 1, 1, 1),
    "repair": (None, 1, 1, None),
    "repair_readmit": (1, 1, 1, 1),
    "federate": (1, 1, 1, None),
}

KNOWN_OPERATIONS = frozenset(OPERATION_REQUIREMENTS.keys())


def required_bits(operation: str) -> tuple[int | None, ...]:
    op = (operation or "").casefold().strip()
    if op not in OPERATION_REQUIREMENTS:
        raise KeyError(f"unknown_operation:{operation}")
    return OPERATION_REQUIREMENTS[op]


def coordinate_satisfies(
    operation: str,
    coordinate: ConstitutionalCoordinate,
    *,
    live_gate: bool = False,
) -> bool:
    """Whether coordinate meets requirements.

    live_gate=True uses gate_bits (MEASURED/RECEIPT_VERIFIED only) for promote,
    repair_readmit, and federate. Simulated/operator axes never satisfy live gates.
    """
    try:
        req = required_bits(operation)
    except KeyError:
        return False
    bits = coordinate.gate_bits() if live_gate else coordinate.bits()
    for i, r in enumerate(req):
        if r is None:
            continue
        if bits[i] != r:
            return False
    return True


def missing_axes(
    operation: str,
    coordinate: ConstitutionalCoordinate,
    *,
    live_gate: bool = False,
) -> list[str]:
    try:
        req = required_bits(operation)
    except KeyError:
        return ["unknown_operation"]
    bits = coordinate.gate_bits() if live_gate else coordinate.bits()
    missing: list[str] = []
    for i, r in enumerate(req):
        if r is None:
            continue
        if bits[i] != r:
            missing.append(AXIS_ORDER[i])
            # Tag ineligible truth when raw valid but not gate-eligible
            if live_gate and coordinate.bits()[i] == 1 and bits[i] == 0:
                ax = coordinate.axis(AXIS_ORDER[i])
                if ax.valid and not ax.gate_eligible():
                    missing.append(f"{AXIS_ORDER[i]}_truth_ineligible")
    return missing


def requirements_hash() -> str:
    material = json.dumps(
        {k: list(v) for k, v in sorted(OPERATION_REQUIREMENTS.items())},
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def requirements_report() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "operations": {
            k: {
                "required_bits": list(v),
                "required_axes": [
                    AXIS_ORDER[i] for i, r in enumerate(v) if r is not None
                ],
            }
            for k, v in sorted(OPERATION_REQUIREMENTS.items())
        },
        "requirements_hash": requirements_hash(),
        "claim_boundary": CLAIM,
    }


def assess_operation(
    operation: str,
    coordinate: ConstitutionalCoordinate,
    *,
    live_gate: bool | None = None,
) -> dict[str, Any]:
    """Gate check: does coordinate satisfy operation requirements?"""
    op = (operation or "").casefold().strip()
    if op not in KNOWN_OPERATIONS:
        return {
            "allowed": False,
            "operation": operation,
            "coordinate": list(coordinate.bits()),
            "gate_bits": list(coordinate.gate_bits()),
            "required": None,
            "missing_axes": ["unknown_operation"],
            "reasons": [f"unknown_operation:{operation}"],
            "claim_boundary": CLAIM,
        }
    # live_gate must be explicit (True at promote/repair/federate boundaries only)
    if live_gate is None:
        live_gate = False
    req = required_bits(op)
    missing = missing_axes(op, coordinate, live_gate=live_gate)
    allowed = coordinate_satisfies(op, coordinate, live_gate=live_gate)
    reasons: list[str] = []
    if not allowed:
        for ax in missing:
            reasons.append(f"missing_{ax}")
            if ax.endswith("_truth_ineligible"):
                reasons.append("axis_truth_not_gate_eligible")
    return {
        "allowed": allowed,
        "operation": op,
        "coordinate": list(coordinate.bits()),
        "gate_bits": list(coordinate.gate_bits()),
        "live_gate": live_gate,
        "coordinate_detail": coordinate.to_dict(),
        "required": list(req),
        "missing_axes": [m for m in missing if not m.endswith("_truth_ineligible")],
        "truth_ineligible_axes": [
            m.replace("_truth_ineligible", "")
            for m in missing
            if m.endswith("_truth_ineligible")
        ],
        "reasons": list(dict.fromkeys(reasons)),
        "claim_boundary": CLAIM,
    }
