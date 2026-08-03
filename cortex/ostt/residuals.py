"""Measured OSTT residual receipts and review gates.

The residual layer is deliberately a measurement surface.  It can describe
the difference between a declared operator output and an observed output, but
it cannot execute the operator, change routing, or authorize learning.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Real
from typing import Any, Iterable

RESIDUAL_SCHEMA = "cortex-ostt-residual/1.0"
RESIDUAL_GLYPH = "▥"
DEFAULT_EPSILON = 1e-9
DEFAULT_MAX_BURDEN = 1.0
VALID_STATUSES = frozenset({"measured", "observed", "unmeasured"})
VALID_APPROXIMATION_MODES = frozenset({"exact", "approximate"})
VALID_COMPARISON_MODES = frozenset(
    {"black_box", "operator_only", "residual_only", "untyped", "ostt"}
)
REQUIRED_COMPARISON_MODES = frozenset(
    {"black_box", "operator_only", "residual_only", "untyped", "ostt"}
)


def _flatten_numeric(value: Any) -> list[float]:
    """Flatten a scalar, sequence, or mapping into a deterministic vector."""
    if isinstance(value, bool):
        raise TypeError("boolean is not a numeric output")
    if isinstance(value, Real):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite numeric output")
        return [number]
    if isinstance(value, Mapping):
        vector: list[float] = []
        for key in sorted(value, key=str):
            vector.extend(_flatten_numeric(value[key]))
        return vector
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        vector = []
        for item in value:
            vector.extend(_flatten_numeric(item))
        return vector
    raise TypeError(f"unsupported numeric output: {type(value).__name__}")


def _norm(vector: Iterable[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _safe_payload(value: Any) -> Any:
    """Keep receipt output JSON serializable without hiding its type."""
    if isinstance(value, Mapping):
        return {str(key): _safe_payload(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_safe_payload(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


@dataclass(frozen=True)
class ResidualReceipt:
    """A typed, serializable observation of one operator residual."""

    operator_id: str
    input_type: str
    output_type: str
    status: str = "unmeasured"
    known_output: Any = None
    observed_output: Any = None
    residual_norm: float | None = None
    reference_norm: float | None = None
    burden: float | None = None
    uncertainty: float | None = None
    uncertainty_calibrated: bool = False
    invariant_projection: Mapping[str, Any] = field(default_factory=dict)
    validation: Mapping[str, Any] = field(default_factory=dict)
    epoch_id: str | None = None
    cohort_id: str | None = None
    independent_witness: bool = False
    approximation_mode: str = "exact"
    comparison_mode: str = "ostt"
    epsilon: float = DEFAULT_EPSILON
    reason: str = ""

    @classmethod
    def measure(
        cls,
        *,
        operator_id: str,
        input_type: str,
        output_type: str,
        known_output: Any,
        observed_output: Any,
        uncertainty: float,
        uncertainty_calibrated: bool,
        invariant_projection: Mapping[str, Any],
        validation: Mapping[str, Any] | None = None,
        epoch_id: str | None = None,
        cohort_id: str | None = None,
        independent_witness: bool = False,
        approximation_mode: str = "exact",
        comparison_mode: str = "ostt",
        epsilon: float = DEFAULT_EPSILON,
    ) -> "ResidualReceipt":
        """Create a measured receipt without executing an operator."""
        known = _flatten_numeric(known_output)
        observed = _flatten_numeric(observed_output)
        if len(known) != len(observed):
            raise ValueError("known and observed outputs have different shapes")
        epsilon_value = float(epsilon)
        if not math.isfinite(epsilon_value) or epsilon_value <= 0.0:
            raise ValueError("epsilon must be finite and positive")
        residual = _norm(observed[index] - known[index] for index in range(len(known)))
        reference = _norm(known)
        burden = residual / (reference + epsilon_value)
        return cls(
            operator_id=operator_id,
            input_type=input_type,
            output_type=output_type,
            status="measured",
            known_output=known_output,
            observed_output=observed_output,
            residual_norm=residual,
            reference_norm=reference,
            burden=burden,
            uncertainty=float(uncertainty),
            uncertainty_calibrated=bool(uncertainty_calibrated),
            invariant_projection=dict(invariant_projection),
            validation=dict(validation or {}),
            epoch_id=epoch_id,
            cohort_id=cohort_id,
            independent_witness=bool(independent_witness),
            approximation_mode=approximation_mode,
            comparison_mode=comparison_mode,
            epsilon=epsilon_value,
        )

    @classmethod
    def unmeasured(
        cls,
        *,
        operator_id: str,
        input_type: str,
        output_type: str,
        reason: str = "typed_operator_output_not_recorded",
    ) -> "ResidualReceipt":
        return cls(
            operator_id=operator_id,
            input_type=input_type,
            output_type=output_type,
            status="unmeasured",
            reason=reason,
        )

    @classmethod
    def observed(
        cls,
        *,
        operator_id: str,
        input_type: str,
        output_type: str,
        observed_output: Any,
        validation: Mapping[str, Any] | None = None,
        epoch_id: str | None = None,
        cohort_id: str | None = None,
        approximation_mode: str = "exact",
        comparison_mode: str = "ostt",
        reason: str = "known_operator_output_not_declared",
    ) -> "ResidualReceipt":
        """Capture a typed output before a declared known output exists."""
        _flatten_numeric(observed_output)
        return cls(
            operator_id=operator_id,
            input_type=input_type,
            output_type=output_type,
            status="observed",
            observed_output=observed_output,
            validation=dict(validation or {}),
            epoch_id=epoch_id,
            cohort_id=cohort_id,
            approximation_mode=approximation_mode,
            comparison_mode=comparison_mode,
            reason=reason,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResidualReceipt":
        """Rehydrate a receipt from a JSON-compatible mapping."""
        fields = {
            "operator_id",
            "input_type",
            "output_type",
            "status",
            "known_output",
            "observed_output",
            "residual_norm",
            "reference_norm",
            "burden",
            "uncertainty",
            "uncertainty_calibrated",
            "invariant_projection",
            "validation",
            "epoch_id",
            "cohort_id",
            "independent_witness",
            "approximation_mode",
            "comparison_mode",
            "epsilon",
            "reason",
        }
        return cls(**{key: payload[key] for key in fields if key in payload})

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.operator_id:
            errors.append("operator_id_missing")
        if not self.input_type:
            errors.append("input_type_missing")
        if not self.output_type:
            errors.append("output_type_missing")
        if self.status not in VALID_STATUSES:
            errors.append("status_invalid")
        if self.approximation_mode not in VALID_APPROXIMATION_MODES:
            errors.append("approximation_disclosure_missing")
        if self.comparison_mode not in VALID_COMPARISON_MODES:
            errors.append("comparison_mode_invalid")
        if self.status == "unmeasured":
            if not self.reason:
                errors.append("unmeasured_reason_missing")
            return errors
        if self.status == "observed":
            if self.observed_output is None:
                errors.append("observed_output_missing")
            else:
                try:
                    _flatten_numeric(self.observed_output)
                except (TypeError, ValueError):
                    errors.append("observed_output_not_numeric")
            if not self.reason:
                errors.append("observed_reason_missing")
            return errors
        if self.known_output is None or self.observed_output is None:
            errors.append("output_pair_missing")
        else:
            try:
                known = _flatten_numeric(self.known_output)
                observed = _flatten_numeric(self.observed_output)
                if len(known) != len(observed):
                    errors.append("output_shape_mismatch")
            except (TypeError, ValueError):
                errors.append("output_not_numeric")
        for name, value in (
            ("residual_norm", self.residual_norm),
            ("reference_norm", self.reference_norm),
            ("burden", self.burden),
        ):
            if value is None or not math.isfinite(float(value)) or float(value) < 0.0:
                errors.append(f"{name}_invalid")
        if self.uncertainty is None:
            errors.append("uncertainty_missing")
        else:
            try:
                uncertainty = float(self.uncertainty)
            except (TypeError, ValueError):
                uncertainty = -1.0
            if not 0.0 <= uncertainty <= 1.0:
                errors.append("uncertainty_out_of_range")
        if not self.uncertainty_calibrated:
            errors.append("uncertainty_uncalibrated")
        if not self.invariant_projection:
            errors.append("invariant_projection_missing")
        elif self.invariant_projection.get("ok") is not True:
            errors.append("invariant_projection_failed")
        if not self.epoch_id:
            errors.append("epoch_id_missing")
        if not self.cohort_id:
            errors.append("cohort_id_missing")
        if not self.independent_witness:
            errors.append("independent_witness_missing")
        try:
            epsilon = float(self.epsilon)
            if not math.isfinite(epsilon) or epsilon <= 0.0:
                errors.append("epsilon_invalid")
        except (TypeError, ValueError):
            errors.append("epsilon_invalid")
        return errors

    @property
    def evidence_ready(self) -> bool:
        return self.status == "measured" and not self.validation_errors()

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "schema_version": RESIDUAL_SCHEMA,
            "operator_id": self.operator_id,
            "input_type": self.input_type,
            "output_type": self.output_type,
            "status": self.status,
            "known_output": _safe_payload(self.known_output),
            "observed_output": _safe_payload(self.observed_output),
            "residual_norm": self.residual_norm,
            "reference_norm": self.reference_norm,
            "burden": self.burden,
            "uncertainty": self.uncertainty,
            "uncertainty_calibrated": self.uncertainty_calibrated,
            "invariant_projection": _safe_payload(self.invariant_projection),
            "validation": _safe_payload(self.validation),
            "epoch_id": self.epoch_id,
            "cohort_id": self.cohort_id,
            "independent_witness": self.independent_witness,
            "approximation_mode": self.approximation_mode,
            "comparison_mode": self.comparison_mode,
            "epsilon": self.epsilon,
            "reason": self.reason,
        }

    def receipt_hash(self) -> str:
        encoded = json.dumps(self._hash_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = self._hash_payload()
        payload.update(
            {
                "glyph": RESIDUAL_GLYPH,
                "receipt_hash": self.receipt_hash(),
                "valid": not self.validation_errors(),
                "evidence_ready": self.evidence_ready,
            }
        )
        return payload


def residual_evidence_report(
    contracts: Iterable[Any],
    receipts: Iterable[ResidualReceipt | Mapping[str, Any]] = (),
    *,
    max_burden: float = DEFAULT_MAX_BURDEN,
) -> dict[str, Any]:
    """Build a shadow report over declared contracts and residual receipts."""
    supplied: list[ResidualReceipt] = []
    for receipt in receipts:
        supplied.append(
            receipt if isinstance(receipt, ResidualReceipt) else ResidualReceipt.from_dict(receipt)
        )
    by_operator: dict[str, ResidualReceipt] = {}
    for receipt in supplied:
        by_operator.setdefault(receipt.operator_id, receipt)

    expected: list[ResidualReceipt] = []
    type_mismatches: list[str] = []
    for contract in contracts:
        receipt = by_operator.get(contract.operator_id)
        if receipt is None:
            receipt = ResidualReceipt.unmeasured(
                operator_id=contract.operator_id,
                input_type=contract.domain_type,
                output_type=contract.codomain_type,
            )
        elif (
            receipt.input_type != contract.domain_type
            or receipt.output_type != contract.codomain_type
        ):
            type_mismatches.append(
                f"{contract.operator_id}:{receipt.input_type}->{receipt.output_type}"
            )
        expected.append(receipt)

    observed = [receipt for receipt in expected if receipt.status == "observed"]
    measured = [receipt for receipt in expected if receipt.status == "measured"]
    ready = [receipt for receipt in expected if receipt.evidence_ready]
    burden_values = [float(receipt.burden) for receipt in measured if receipt.burden is not None]
    modes = {receipt.comparison_mode for receipt in supplied}
    gate_values = {
        "known_output_declared": bool(measured)
        and len(measured) == len(expected)
        and all(receipt.known_output is not None for receipt in measured),
        "typed_compatibility": bool(measured)
        and len(measured) == len(expected)
        and not type_mismatches,
        "residual_bound": bool(measured)
        and len(measured) == len(expected)
        and all(value <= float(max_burden) for value in burden_values),
        "invariant_projection": bool(measured)
        and len(ready) == len(expected)
        and all(receipt.invariant_projection.get("ok") is True for receipt in measured),
        "uncertainty_calibration": bool(measured)
        and len(ready) == len(expected)
        and all(receipt.uncertainty_calibrated for receipt in measured),
        "approximation_disclosure": bool(measured)
        and len(ready) == len(expected)
        and all(receipt.approximation_mode in VALID_APPROXIMATION_MODES for receipt in measured),
        "epoch_cohort_binding": bool(measured)
        and len(ready) == len(expected)
        and all(receipt.epoch_id and receipt.cohort_id for receipt in measured),
        "independent_witness": bool(measured)
        and len(ready) == len(expected)
        and all(receipt.independent_witness for receipt in measured),
        "comparison_matrix": REQUIRED_COMPARISON_MODES.issubset(modes),
    }
    eligible = bool(expected) and all(gate_values.values())
    if not measured and observed:
        status = "observed_shadow"
    elif not measured:
        status = "unmeasured"
    elif eligible:
        status = "ready_for_review"
    else:
        status = "measured_shadow"
    next_actions = [name for name, passed in gate_values.items() if not passed]
    if observed and "known_output_declared" not in next_actions:
        next_actions.append("declare_known_operator_output")
    return {
        "schema_version": RESIDUAL_SCHEMA,
        "glyph": RESIDUAL_GLYPH,
        "mode": "shadow",
        "status": status,
        "operator_count": len(expected),
        "measured_count": len(measured),
        "observed_count": len(observed),
        "unmeasured_count": len(expected) - len(measured) - len(observed),
        "ready_count": len(ready),
        "burden": {
            "mean": round(sum(burden_values) / len(burden_values), 8)
            if burden_values
            else None,
            "max": round(max(burden_values), 8) if burden_values else None,
            "bound": float(max_burden),
            "sample_count": len(burden_values),
        },
        "gates": gate_values,
        "next_actions": next_actions,
        "comparison_modes": sorted(modes),
        "type_mismatches": type_mismatches,
        "receipts": [receipt.to_dict() for receipt in expected],
        "policy_effect": False,
        "advisory_only": True,
        "update_authorized": False,
        "claim_boundary": (
            "Operator residual burden is measured transition telemetry, not "
            "self-sensing, prediction error, authority, or consciousness."
        ),
    }


__all__ = [
    "DEFAULT_EPSILON",
    "DEFAULT_MAX_BURDEN",
    "RESIDUAL_GLYPH",
    "RESIDUAL_SCHEMA",
    "ResidualReceipt",
    "residual_evidence_report",
]
