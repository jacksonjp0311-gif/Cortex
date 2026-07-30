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
    operation: str, coordinate: ConstitutionalCoordinate
) -> bool:
    try:
        req = required_bits(operation)
    except KeyError:
        return False
    bits = coordinate.bits()
    for i, r in enumerate(req):
        if r is None:
            continue
        if bits[i] != r:
            return False
    return True


def missing_axes(
    operation: str, coordinate: ConstitutionalCoordinate
) -> list[str]:
    try:
        req = required_bits(operation)
    except KeyError:
        return ["unknown_operation"]
    bits = coordinate.bits()
    missing: list[str] = []
    for i, r in enumerate(req):
        if r is None:
            continue
        if bits[i] != r:
            missing.append(AXIS_ORDER[i])
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
) -> dict[str, Any]:
    """Gate check: does coordinate satisfy operation requirements?"""
    op = (operation or "").casefold().strip()
    if op not in KNOWN_OPERATIONS:
        return {
            "allowed": False,
            "operation": operation,
            "coordinate": list(coordinate.bits()),
            "required": None,
            "missing_axes": ["unknown_operation"],
            "reasons": [f"unknown_operation:{operation}"],
            "claim_boundary": CLAIM,
        }
    req = required_bits(op)
    missing = missing_axes(op, coordinate)
    allowed = coordinate_satisfies(op, coordinate)
    reasons: list[str] = []
    if not allowed:
        for ax in missing:
            reasons.append(f"missing_{ax}")
    return {
        "allowed": allowed,
        "operation": op,
        "coordinate": list(coordinate.bits()),
        "coordinate_detail": coordinate.to_dict(),
        "required": list(req),
        "missing_axes": missing,
        "reasons": reasons,
        "claim_boundary": CLAIM,
    }
