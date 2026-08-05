"""Measured OSTT residual receipts and review gates.

The residual layer is deliberately a measurement surface.  It can describe
the difference between a declared operator output and an observed output, but
it cannot execute the operator, change routing, or authorize learning.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Integral, Real
from typing import Any, Iterable

RESIDUAL_SCHEMA = "cortex-ostt-residual/1.0"
RESIDUAL_GLYPH = "▥"
DEFAULT_EPSILON = 1e-9
DEFAULT_MAX_BURDEN = 1.0
VALID_STATUSES = frozenset(
    {
        "measured",
        "conformance_measured",
        "observed",
        "observed_incomplete",
        "unmeasured",
    }
)
VALID_APPROXIMATION_MODES = frozenset({"exact", "approximate"})
VALID_COMPARISON_MODES = frozenset(
    {"black_box", "operator_only", "residual_only", "untyped", "ostt"}
)
REQUIRED_COMPARISON_MODES = frozenset(
    {"black_box", "operator_only", "residual_only", "untyped", "ostt"}
)
REQUIRED_COMPARISON_ARMS = frozenset({"evidence_baseline", "advanced"})
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
REQUIRED_WITNESS_FIELDS = frozenset(
    {
        "witness_id",
        "witness_kind",
        "verifier",
        "subject_receipt_hash",
        "evidence_hashes",
        "passed",
        "issued_at",
    }
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


def _shape_signature(value: Any) -> tuple[Any, ...]:
    """Return a structural numeric signature without erasing containers.

    Flattened length is not a type.  In particular, a two-coordinate mapping
    and a two-element list remain different outputs even if both flatten to two
    finite numbers.
    """

    if isinstance(value, bool):
        raise TypeError("boolean is not a numeric output")
    if isinstance(value, Integral):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite numeric output")
        return ("scalar", "integer")
    if isinstance(value, Real):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("non-finite numeric output")
        return ("scalar", "real")
    if isinstance(value, Mapping):
        return (
            "mapping",
            tuple(
                (str(key), _shape_signature(value[key]))
                for key in sorted(value, key=str)
            ),
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return ("sequence", len(value), tuple(_shape_signature(item) for item in value))
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


def _structured_invariants(value: Any) -> tuple[Mapping[str, Any], ...]:
    """Normalize list- and id-keyed invariant panels without blessing them."""

    if isinstance(value, Mapping):
        results: list[Mapping[str, Any]] = []
        for invariant_id, result in value.items():
            if not isinstance(result, Mapping):
                continue
            item = dict(result)
            item.setdefault("invariant_id", str(invariant_id))
            results.append(item)
        return tuple(results)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _conformance_invariant_errors(
    results: Sequence[Mapping[str, Any]],
) -> list[str]:
    errors: list[str] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for item in results:
        invariant_id = str(item.get("invariant_id") or "")
        if not invariant_id:
            errors.append("invariant_id_missing")
            continue
        if invariant_id in by_id:
            errors.append(f"invariant_duplicate:{invariant_id}")
            continue
        by_id[invariant_id] = item
        missing_fields = [
            name
            for name in ("passed", "evidence_ids", "expected", "observed", "reason")
            if name not in item
        ]
        if missing_fields:
            errors.append(
                f"invariant_structure_invalid:{invariant_id}:{','.join(missing_fields)}"
            )
        if item.get("passed") is not True:
            errors.append(f"invariant_failed:{invariant_id}")
        evidence_ids = item.get("evidence_ids")
        if not isinstance(evidence_ids, Sequence) or isinstance(
            evidence_ids, (str, bytes, bytearray)
        ):
            errors.append(f"invariant_evidence_invalid:{invariant_id}")
        if not str(item.get("reason") or "").strip():
            errors.append(f"invariant_reason_missing:{invariant_id}")
    for invariant_id in sorted(REQUIRED_CONFORMANCE_INVARIANTS - set(by_id)):
        errors.append(f"invariant_missing:{invariant_id}")
    return errors


def _measurement_witness_errors(witness: Mapping[str, Any]) -> list[str]:
    if not isinstance(witness, Mapping) or not witness:
        return ["measurement_witness_missing"]
    errors = [
        f"measurement_witness_field_missing:{name}"
        for name in sorted(REQUIRED_WITNESS_FIELDS)
        if name not in witness
    ]
    if str(witness.get("witness_kind") or "").strip().casefold() != "measurement":
        errors.append("measurement_witness_kind_invalid")
    if witness.get("passed") is not True:
        errors.append("measurement_witness_failed")
    for name in ("witness_id", "verifier", "subject_receipt_hash"):
        if not str(witness.get(name) or "").strip():
            errors.append(f"measurement_witness_field_empty:{name}")
    evidence_hashes = witness.get("evidence_hashes")
    if not isinstance(evidence_hashes, Sequence) or isinstance(
        evidence_hashes, (str, bytes, bytearray)
    ):
        errors.append("measurement_witness_evidence_invalid")
    return errors


@dataclass(frozen=True)
class ResidualReceipt:
    """A typed, serializable observation of one operator residual."""

    operator_id: str
    input_type: str
    output_type: str
    status: str = "unmeasured"
    known_output: Any = None
    reference_output: Any = None
    observed_output: Any = None
    residual_norm: float | None = None
    reference_norm: float | None = None
    burden: float | None = None
    uncertainty: float | None = None
    uncertainty_calibrated: bool = False
    invariant_projection: Mapping[str, Any] = field(default_factory=dict)
    invariant_results: tuple[Mapping[str, Any], ...] = ()
    validation: Mapping[str, Any] = field(default_factory=dict)
    epoch_id: str | None = None
    cohort_id: str | None = None
    coordinate_schema_digest: str | None = None
    repository_id: str | None = None
    repo: str | None = None
    case_id: str | None = None
    comparison_arm: str | None = None
    independent_witness: bool = False
    measurement_witness: Mapping[str, Any] = field(default_factory=dict)
    approximation_mode: str = "exact"
    comparison_mode: str = "ostt"
    valid_fraction: float | None = None
    b_rms: float | None = None
    b_max: float | None = None
    b_invalid: float | None = None
    channel_burdens: Mapping[str, Any] = field(default_factory=dict)
    canonical_receipt_hash: str | None = None
    measurement_subject_hash: str | None = None
    previous_receipt_hash: str | None = None
    chain_sequence: int | None = None
    canonical_verification: Mapping[str, Any] = field(default_factory=dict)
    conformance_payload: Mapping[str, Any] = field(default_factory=dict)
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
        coordinate_schema_digest: str | None = None,
        repository_id: str | None = None,
        repo: str | None = None,
        case_id: str | None = None,
        comparison_arm: str | None = None,
        independent_witness: bool = False,
        approximation_mode: str = "exact",
        comparison_mode: str = "ostt",
        epsilon: float = DEFAULT_EPSILON,
    ) -> "ResidualReceipt":
        """Create a measured receipt without executing an operator."""
        known = _flatten_numeric(known_output)
        observed = _flatten_numeric(observed_output)
        if _shape_signature(known_output) != _shape_signature(observed_output):
            raise ValueError("known and observed outputs have different structural shapes")
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
            coordinate_schema_digest=coordinate_schema_digest,
            repository_id=repository_id,
            repo=repo,
            case_id=case_id,
            comparison_arm=comparison_arm,
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
        coordinate_schema_digest: str | None = None,
        case_id: str | None = None,
        comparison_arm: str | None = None,
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
            coordinate_schema_digest=coordinate_schema_digest,
            case_id=case_id,
            comparison_arm=comparison_arm,
            approximation_mode=approximation_mode,
            comparison_mode=comparison_mode,
            reason=reason,
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResidualReceipt":
        """Rehydrate a receipt from a JSON-compatible mapping."""
        source = dict(payload)
        transition = source.get("transition") or source.get("measured_transition") or {}
        if not isinstance(transition, Mapping):
            transition = {}
        residual_panel = source.get("residual_panel") or {}
        if not isinstance(residual_panel, Mapping):
            residual_panel = {}
        persisted = source.get("observed_output")
        if persisted is None:
            persisted = source.get("persisted_normalized_vector")
        if persisted is None:
            persisted = source.get("persisted_normalized_delta")
        if persisted is None:
            persisted = transition.get("normalized_delta")
        reference = source.get("reference_output")
        if reference is None:
            reference = source.get("independently_recomputed_normalized_vector")
        if reference is None:
            reference = source.get("recomputed_normalized_delta")
        invariants = _structured_invariants(source.get("invariant_results"))
        fields = {
            "operator_id",
            "input_type",
            "output_type",
            "status",
            "known_output",
            "observed_output",
            "reference_output",
            "residual_norm",
            "reference_norm",
            "burden",
            "uncertainty",
            "uncertainty_calibrated",
            "invariant_projection",
            "invariant_results",
            "validation",
            "epoch_id",
            "cohort_id",
            "coordinate_schema_digest",
            "repository_id",
            "repo",
            "case_id",
            "comparison_arm",
            "independent_witness",
            "measurement_witness",
            "approximation_mode",
            "comparison_mode",
            "valid_fraction",
            "b_rms",
            "b_max",
            "b_invalid",
            "channel_burdens",
            "canonical_receipt_hash",
            "measurement_subject_hash",
            "previous_receipt_hash",
            "chain_sequence",
            "canonical_verification",
            "conformance_payload",
            "epsilon",
            "reason",
        }
        values = {key: source[key] for key in fields if key in source}
        if persisted is not None:
            values["observed_output"] = persisted
        if reference is not None:
            values["reference_output"] = reference
        if "invariant_results" in source:
            values["invariant_results"] = invariants
        values.setdefault("epoch_id", source.get("body_epoch_id"))
        values.setdefault("cohort_id", source.get("measurement_cohort_id"))
        values.setdefault(
            "coordinate_schema_digest", source.get("coordinate_schema_digest")
        )
        values.setdefault("b_rms", source.get("B_rms", residual_panel.get("B_rms")))
        values.setdefault("b_max", source.get("B_max", residual_panel.get("B_max")))
        values.setdefault(
            "b_invalid", source.get("B_invalid", residual_panel.get("B_invalid"))
        )
        values.setdefault(
            "channel_burdens",
            source.get("channel_burdens", residual_panel.get("channel_burdens", {})),
        )
        values.setdefault("canonical_receipt_hash", source.get("receipt_hash"))
        values.setdefault(
            "canonical_verification", source.get("canonical_verification") or {}
        )
        if source.get("status") == "conformance_measured":
            values.setdefault("conformance_payload", source)
        return cls(**values)

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
        if self.status in {"observed", "observed_incomplete"}:
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
        if self.status == "conformance_measured":
            reference = (
                self.reference_output
                if self.reference_output is not None
                else self.known_output
            )
            if reference is None or self.observed_output is None:
                errors.append("output_pair_missing")
            else:
                try:
                    _flatten_numeric(reference)
                    _flatten_numeric(self.observed_output)
                    if _shape_signature(reference) != _shape_signature(
                        self.observed_output
                    ):
                        errors.append("output_structural_shape_mismatch")
                except (TypeError, ValueError):
                    errors.append("output_not_numeric")
            for name, value in (
                ("B_rms", self.b_rms),
                ("B_max", self.b_max),
                ("B_invalid", self.b_invalid),
            ):
                try:
                    number = float(value) if value is not None else math.nan
                except (TypeError, ValueError):
                    number = math.nan
                if not math.isfinite(number) or number < 0.0:
                    errors.append(f"{name}_invalid")
            try:
                valid_fraction = float(self.valid_fraction)
            except (TypeError, ValueError):
                valid_fraction = -1.0
            if valid_fraction != 1.0:
                errors.append("required_measurement_incomplete")
            try:
                invalid_fraction = float(self.b_invalid)
            except (TypeError, ValueError):
                invalid_fraction = -1.0
            if invalid_fraction != 0.0:
                errors.append("invalid_required_coordinate")
            if not isinstance(self.channel_burdens, Mapping) or not self.channel_burdens:
                errors.append("channel_burdens_missing")
            else:
                for channel, value in self.channel_burdens.items():
                    try:
                        number = float(value)
                    except (TypeError, ValueError):
                        number = math.nan
                    if not math.isfinite(number) or number < 0.0:
                        errors.append(f"channel_burden_invalid:{channel}")
            errors.extend(
                _conformance_invariant_errors(
                    _structured_invariants(self.invariant_results)
                )
            )
            errors.extend(_measurement_witness_errors(self.measurement_witness))
            for name, value in (
                ("epoch_id", self.epoch_id),
                ("cohort_id", self.cohort_id),
                ("coordinate_schema_digest", self.coordinate_schema_digest),
                ("case_id", self.case_id),
                ("comparison_arm", self.comparison_arm),
            ):
                if not str(value or "").strip():
                    errors.append(f"{name}_missing")
            try:
                epsilon = float(self.epsilon)
                if not math.isfinite(epsilon) or epsilon <= 0.0:
                    errors.append("epsilon_invalid")
            except (TypeError, ValueError):
                errors.append("epsilon_invalid")
            conformance_payload = (
                self.conformance_payload
                if isinstance(self.conformance_payload, Mapping)
                else {}
            )
            canonical_hash = str(self.canonical_receipt_hash or "").strip()
            ledger_bound = bool(canonical_hash)
            # In-memory residual receipts may assert structured Gate-B fields
            # without a ledger envelope. Ledger-bound receipts require the full
            # scientific subject plus canonical verification.
            if ledger_bound:
                if not conformance_payload:
                    errors.append("conformance_payload_missing")
                else:
                    try:
                        from .independent_verifier import validate_conformance_payload

                        scientific = validate_conformance_payload(
                            conformance_payload
                        )
                        errors.extend(
                            f"scientific:{error}"
                            for error in scientific.get("errors") or ()
                        )
                    except Exception as exc:
                        errors.append(
                            "scientific:validation_exception:"
                            f"{type(exc).__name__}:{exc}"
                        )
                if (
                    len(canonical_hash) != 64
                    or any(
                        character not in "0123456789abcdef"
                        for character in canonical_hash
                    )
                    or str(conformance_payload.get("receipt_hash") or "")
                    != canonical_hash
                ):
                    errors.append("canonical_receipt_hash_invalid")
                verification = self.canonical_verification
                if not isinstance(verification, Mapping) or not verification:
                    errors.append("canonical_verification_missing")
                else:
                    required_verification = {
                        "verification_status": "verified",
                        "receipt_hash_valid": True,
                        "chain_valid": True,
                        "measurement_conformance_valid": True,
                        "scientific_payload_valid": True,
                        "independent_recomputation_matches": True,
                        "reference_output_matches": True,
                        "measurement_witness_valid": True,
                        "measurement_subject_hash_valid": True,
                        "host_projection_valid": True,
                        "invariant_panel_valid": True,
                        "repository_binding_valid": True,
                        "epoch_current": True,
                        "cohort_current": True,
                        "exactly_once_event": True,
                    }
                    for name, expected in required_verification.items():
                        if verification.get(name) != expected:
                            errors.append(f"canonical_verification_failed:{name}")
                    if verification.get("receipt_hash") != canonical_hash:
                        errors.append("canonical_verification_hash_mismatch")
            elif conformance_payload:
                try:
                    from .independent_verifier import validate_conformance_payload

                    scientific = validate_conformance_payload(conformance_payload)
                    errors.extend(
                        f"scientific:{error}"
                        for error in scientific.get("errors") or ()
                    )
                except Exception as exc:
                    errors.append(
                        "scientific:validation_exception:"
                        f"{type(exc).__name__}:{exc}"
                    )
            return errors
        if self.known_output is None or self.observed_output is None:
            errors.append("output_pair_missing")
        else:
            try:
                _flatten_numeric(self.known_output)
                _flatten_numeric(self.observed_output)
                if _shape_signature(self.known_output) != _shape_signature(
                    self.observed_output
                ):
                    errors.append("output_structural_shape_mismatch")
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
        return self.status in {"measured", "conformance_measured"} and not self.validation_errors()

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "schema_version": RESIDUAL_SCHEMA,
            "operator_id": self.operator_id,
            "input_type": self.input_type,
            "output_type": self.output_type,
            "status": self.status,
            "known_output": _safe_payload(self.known_output),
            "reference_output": _safe_payload(self.reference_output),
            "observed_output": _safe_payload(self.observed_output),
            "residual_norm": self.residual_norm,
            "reference_norm": self.reference_norm,
            "burden": self.burden,
            "uncertainty": self.uncertainty,
            "uncertainty_calibrated": self.uncertainty_calibrated,
            "invariant_projection": _safe_payload(self.invariant_projection),
            "invariant_results": _safe_payload(self.invariant_results),
            "validation": _safe_payload(self.validation),
            "epoch_id": self.epoch_id,
            "cohort_id": self.cohort_id,
            "coordinate_schema_digest": self.coordinate_schema_digest,
            "repository_id": self.repository_id,
            "repo": self.repo,
            "case_id": self.case_id,
            "comparison_arm": self.comparison_arm,
            "independent_witness": self.independent_witness,
            "measurement_witness": _safe_payload(self.measurement_witness),
            "approximation_mode": self.approximation_mode,
            "comparison_mode": self.comparison_mode,
            "valid_fraction": self.valid_fraction,
            "B_rms": self.b_rms,
            "B_max": self.b_max,
            "B_invalid": self.b_invalid,
            "channel_burdens": _safe_payload(self.channel_burdens),
            "canonical_receipt_hash": self.canonical_receipt_hash,
            "measurement_subject_hash": self.measurement_subject_hash,
            "previous_receipt_hash": self.previous_receipt_hash,
            "chain_sequence": self.chain_sequence,
            "canonical_verification": _safe_payload(self.canonical_verification),
            "conformance_payload": _safe_payload(self.conformance_payload),
            "epsilon": self.epsilon,
            "reason": self.reason,
        }

    def receipt_hash(self) -> str:
        encoded = json.dumps(self._hash_payload(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        payload = self._hash_payload()
        serialization_hash = self.receipt_hash()
        payload.update(
            {
                "glyph": RESIDUAL_GLYPH,
                "receipt_hash": self.canonical_receipt_hash or serialization_hash,
                "residual_serialization_hash": serialization_hash,
                "valid": not self.validation_errors(),
                "evidence_ready": self.evidence_ready,
            }
        )
        return payload


def _grouping_errors(receipt: ResidualReceipt) -> list[str]:
    return [
        f"{name}_missing"
        for name, value in (
            ("case_id", receipt.case_id),
            ("comparison_arm", receipt.comparison_arm),
            ("repository_id", receipt.repository_id),
            ("repo", receipt.repo),
            ("epoch_id", receipt.epoch_id),
            ("cohort_id", receipt.cohort_id),
            ("coordinate_schema_digest", receipt.coordinate_schema_digest),
        )
        if not str(value or "").strip()
    ]


def _reference_output(receipt: ResidualReceipt) -> Any:
    return (
        receipt.reference_output
        if receipt.reference_output is not None
        else receipt.known_output
    )


def residual_evidence_report(
    contracts: Iterable[Any],
    receipts: Iterable[ResidualReceipt | Mapping[str, Any]] = (),
    *,
    max_burden: float = DEFAULT_MAX_BURDEN,
) -> dict[str, Any]:
    """Build a partitioned shadow report without discarding later receipts.

    Individual conformance is intentionally separate from global readiness.  A
    production activation receipt can make ``activation_observation`` ready
    while every other declared operator remains unmeasured and the system-wide
    gate remains closed.
    """

    declared = tuple(contracts)
    contract_by_operator = {contract.operator_id: contract for contract in declared}
    supplied = [
        receipt
        if isinstance(receipt, ResidualReceipt)
        else ResidualReceipt.from_dict(receipt)
        for receipt in receipts
    ]

    type_mismatches: list[str] = []
    incompatible_indices: set[int] = set()
    grouping_failures: list[dict[str, Any]] = []
    candidate_indices: list[int] = []
    case_partitions: dict[
        tuple[str, str, str, str], set[tuple[str, str, str]]
    ] = defaultdict(set)
    repository_partitions: set[tuple[str, str]] = set()

    for index, receipt in enumerate(supplied):
        contract = contract_by_operator.get(receipt.operator_id)
        if contract is None:
            incompatible_indices.add(index)
            type_mismatches.append(f"undeclared_operator:{receipt.operator_id}")
            continue
        if (
            receipt.input_type != contract.domain_type
            or receipt.output_type != contract.codomain_type
        ):
            incompatible_indices.add(index)
            type_mismatches.append(
                f"{receipt.operator_id}:{receipt.input_type}->{receipt.output_type}"
                f":case={receipt.case_id or 'missing'}:arm={receipt.comparison_arm or 'missing'}"
            )
            continue
        missing = _grouping_errors(receipt)
        if missing:
            incompatible_indices.add(index)
            grouping_failures.append(
                {
                    "operator_id": receipt.operator_id,
                    "case_id": receipt.case_id,
                    "comparison_arm": receipt.comparison_arm,
                    "errors": missing,
                }
            )
            continue
        candidate_indices.append(index)
        repository_partition = (str(receipt.repository_id), str(receipt.repo))
        repository_partitions.add(repository_partition)
        case_partitions[
            (
                repository_partition[0],
                repository_partition[1],
                receipt.operator_id,
                str(receipt.case_id),
            )
        ].add(
            (
                str(receipt.epoch_id),
                str(receipt.cohort_id),
                str(receipt.coordinate_schema_digest),
            )
        )

    cross_partition_cases = {
        key: partitions
        for key, partitions in case_partitions.items()
        if len(partitions) > 1
    }
    for index in candidate_indices:
        receipt = supplied[index]
        if (
            len(repository_partitions) > 1
            or (
                str(receipt.repository_id),
                str(receipt.repo),
                receipt.operator_id,
                str(receipt.case_id),
            )
            in cross_partition_cases
        ):
            incompatible_indices.add(index)

    full_groups: dict[
        tuple[str, str, str, str, str, str, str, str],
        list[tuple[int, ResidualReceipt]],
    ] = defaultdict(list)
    partition_cases: dict[
        tuple[str, str, str, str, str, str],
        dict[str, dict[str, list[tuple[int, ResidualReceipt]]]],
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for index in candidate_indices:
        receipt = supplied[index]
        full_key = (
            str(receipt.repository_id),
            str(receipt.repo),
            receipt.operator_id,
            str(receipt.case_id),
            str(receipt.comparison_arm),
            str(receipt.epoch_id),
            str(receipt.cohort_id),
            str(receipt.coordinate_schema_digest),
        )
        full_groups[full_key].append((index, receipt))
        partition_key = (
            str(receipt.repository_id),
            str(receipt.repo),
            receipt.operator_id,
            str(receipt.epoch_id),
            str(receipt.cohort_id),
            str(receipt.coordinate_schema_digest),
        )
        partition_cases[partition_key][str(receipt.case_id)][
            str(receipt.comparison_arm)
        ].append((index, receipt))

    cohort_statuses: list[dict[str, Any]] = []
    paired_case_count = 0
    unpaired_case_count = 0
    paired_mode_matrix_complete = True
    for partition_key in sorted(partition_cases):
        repository_id, repo, operator_id, epoch_id, cohort_id, schema_digest = (
            partition_key
        )
        cases = partition_cases[partition_key]
        partition_paired = 0
        partition_unpaired = 0
        partition_incompatible = 0
        partition_ready = 0
        case_statuses: list[dict[str, Any]] = []
        for case_id in sorted(cases):
            arms = cases[case_id]
            arm_names = set(arms)
            paired = REQUIRED_COMPARISON_ARMS.issubset(arm_names)
            if paired:
                paired_case_count += 1
                partition_paired += 1
            else:
                unpaired_case_count += 1
                partition_unpaired += 1
            modes_by_arm = {
                arm: sorted({receipt.comparison_mode for _, receipt in members})
                for arm, members in sorted(arms.items())
            }
            mode_matrix_complete = bool(paired) and all(
                all(
                    any(
                        index not in incompatible_indices
                        and receipt.evidence_ready
                        and receipt.comparison_mode == mode
                        for index, receipt in arms.get(arm, ())
                    )
                    for mode in REQUIRED_COMPARISON_MODES
                )
                for arm in REQUIRED_COMPARISON_ARMS
            )
            if paired and not mode_matrix_complete:
                paired_mode_matrix_complete = False
            member_indices = [index for members in arms.values() for index, _ in members]
            incompatible_here = sum(
                1 for index in member_indices if index in incompatible_indices
            )
            ready_here = sum(
                1
                for members in arms.values()
                for index, receipt in members
                if index not in incompatible_indices and receipt.evidence_ready
            )
            partition_incompatible += incompatible_here
            partition_ready += ready_here
            case_statuses.append(
                {
                    "case_id": case_id,
                    "status": (
                        "incompatible"
                        if incompatible_here
                        else "paired"
                        if paired
                        else "unpaired"
                    ),
                    "arms": sorted(arm_names),
                    "missing_arms": sorted(REQUIRED_COMPARISON_ARMS - arm_names),
                    "comparison_modes_by_arm": modes_by_arm,
                    "comparison_mode_matrix_complete": mode_matrix_complete,
                    "receipt_count": len(member_indices),
                    "ready_receipt_count": ready_here,
                }
            )
        cohort_statuses.append(
            {
                "repository_id": repository_id,
                "repo": repo,
                "operator_id": operator_id,
                "epoch_id": epoch_id,
                "cohort_id": cohort_id,
                "coordinate_schema_digest": schema_digest,
                "status": (
                    "incompatible"
                    if partition_incompatible
                    else "paired"
                    if partition_paired and not partition_unpaired
                    else "partially_paired"
                    if partition_paired
                    else "unpaired"
                ),
                "case_count": len(cases),
                "paired_case_count": partition_paired,
                "unpaired_case_count": partition_unpaired,
                "incompatible_receipt_count": partition_incompatible,
                "ready_receipt_count": partition_ready,
                "cases": case_statuses,
            }
        )

    operator_statuses: dict[str, dict[str, Any]] = {}
    compatible_by_operator: dict[str, list[ResidualReceipt]] = defaultdict(list)
    for index, receipt in enumerate(supplied):
        if index not in incompatible_indices and not _grouping_errors(receipt):
            compatible_by_operator[receipt.operator_id].append(receipt)

    ready_operator_ids: set[str] = set()
    measured_operator_ids: set[str] = set()
    observed_operator_ids: set[str] = set()
    for contract in declared:
        all_for_operator = [
            receipt for receipt in supplied if receipt.operator_id == contract.operator_id
        ]
        compatible = compatible_by_operator.get(contract.operator_id, [])
        ready_receipts = [receipt for receipt in compatible if receipt.evidence_ready]
        conformance_ready = [
            receipt
            for receipt in ready_receipts
            if receipt.status == "conformance_measured"
        ]
        measured_receipts = [
            receipt
            for receipt in all_for_operator
            if receipt.status in {"measured", "conformance_measured"}
        ]
        observed_receipts = [
            receipt
            for receipt in all_for_operator
            if receipt.status in {"observed", "observed_incomplete"}
        ]
        if measured_receipts:
            measured_operator_ids.add(contract.operator_id)
        if observed_receipts:
            observed_operator_ids.add(contract.operator_id)
        if contract.operator_id == "activation_observation" and conformance_ready:
            operator_status = "conformance_ready"
            ready_operator_ids.add(contract.operator_id)
        elif contract.operator_id == "activation_observation" and measured_receipts:
            # Legacy aggregate receipts cannot satisfy the activation Gate-B
            # contract, even when their old boolean gates happen to pass.
            operator_status = "measured_incomplete"
        elif ready_receipts:
            operator_status = "evidence_ready"
            ready_operator_ids.add(contract.operator_id)
        elif measured_receipts:
            operator_status = "measured_incomplete"
        elif observed_receipts:
            operator_status = (
                "observed_incomplete"
                if all(receipt.status == "observed_incomplete" for receipt in observed_receipts)
                else "observed"
            )
        else:
            operator_status = "unmeasured"
        operator_partitions = {
            (
                str(receipt.repository_id),
                str(receipt.repo),
                str(receipt.epoch_id),
                str(receipt.cohort_id),
                str(receipt.coordinate_schema_digest),
            )
            for receipt in compatible
        }
        operator_statuses[contract.operator_id] = {
            "status": operator_status,
            "receipt_count": len(all_for_operator),
            "compatible_receipt_count": len(compatible),
            "ready_receipt_count": len(ready_receipts),
            "conformance_ready_receipt_count": len(conformance_ready),
            "cohort_count": len(operator_partitions),
        }

    placeholder_receipts = [
        ResidualReceipt.unmeasured(
            operator_id=contract.operator_id,
            input_type=contract.domain_type,
            output_type=contract.codomain_type,
        )
        for contract in declared
        if not any(receipt.operator_id == contract.operator_id for receipt in supplied)
    ]
    report_receipts = supplied + placeholder_receipts
    measured = [
        receipt
        for receipt in supplied
        if receipt.status in {"measured", "conformance_measured"}
    ]
    observed = [
        receipt
        for receipt in supplied
        if receipt.status in {"observed", "observed_incomplete"}
    ]
    legacy_burden_values = [
        float(receipt.burden)
        for receipt in measured
        if receipt.status == "measured" and receipt.burden is not None
    ]
    conformance_b_rms = [
        float(receipt.b_rms)
        for receipt in measured
        if receipt.status == "conformance_measured" and receipt.b_rms is not None
    ]
    modes = {receipt.comparison_mode for receipt in supplied}
    all_operators_ready = bool(declared) and len(ready_operator_ids) == len(declared)
    matrix_ready = bool(paired_case_count) and not unpaired_case_count
    matrix_ready = matrix_ready and paired_mode_matrix_complete

    ready_compatible_receipts = [
        receipt
        for receipts_for_operator in compatible_by_operator.values()
        for receipt in receipts_for_operator
        if receipt.evidence_ready
    ]
    gate_values = {
        "known_output_declared": all_operators_ready
        and all(_reference_output(receipt) is not None for receipt in ready_compatible_receipts),
        "typed_compatibility": all_operators_ready and not type_mismatches,
        "residual_bound": all_operators_ready
        and all(value <= float(max_burden) for value in legacy_burden_values)
        and all(
            receipt.evidence_ready
            for receipt in ready_compatible_receipts
            if receipt.status == "conformance_measured"
        ),
        "invariant_projection": all_operators_ready
        and all(receipt.evidence_ready for receipt in ready_compatible_receipts),
        "uncertainty_calibration": all_operators_ready
        and all(
            receipt.status == "conformance_measured" or receipt.uncertainty_calibrated
            for receipt in ready_compatible_receipts
        ),
        "approximation_disclosure": all_operators_ready
        and all(
            receipt.approximation_mode in VALID_APPROXIMATION_MODES
            for receipt in ready_compatible_receipts
        ),
        "epoch_cohort_binding": all_operators_ready
        and all(not _grouping_errors(receipt) for receipt in ready_compatible_receipts),
        "independent_witness": all_operators_ready
        and all(
            (
                not _measurement_witness_errors(receipt.measurement_witness)
                if receipt.status == "conformance_measured"
                else receipt.independent_witness
            )
            for receipt in ready_compatible_receipts
        ),
        "comparison_matrix": matrix_ready,
        "global_operator_evidence": all_operators_ready,
    }
    eligible = bool(declared) and all(gate_values.values())
    if eligible:
        status = "ready_for_review"
    elif any(
        details["status"] == "conformance_ready"
        for details in operator_statuses.values()
    ):
        status = "conformance_measured_shadow"
    elif measured:
        status = "measured_shadow"
    elif observed:
        status = "observed_shadow"
    else:
        status = "unmeasured"
    next_actions = [name for name, passed in gate_values.items() if not passed]
    if observed and not measured and "independent_recomputation" not in next_actions:
        next_actions.append("independent_recomputation")

    return {
        "schema_version": RESIDUAL_SCHEMA,
        "glyph": RESIDUAL_GLYPH,
        "mode": "shadow",
        "status": status,
        "operator_count": len(declared),
        "measured_count": len(measured_operator_ids),
        "observed_count": len(observed_operator_ids - measured_operator_ids),
        "unmeasured_count": len(declared)
        - len(measured_operator_ids | observed_operator_ids),
        "ready_count": len(ready_operator_ids),
        "ready_receipt_count": len(ready_compatible_receipts),
        "operator_statuses": operator_statuses,
        "cohort_statuses": cohort_statuses,
        "paired_case_count": paired_case_count,
        "unpaired_case_count": unpaired_case_count,
        "incompatible_receipt_count": len(incompatible_indices),
        "cross_partition_cases": [
            {
                "repository_id": repository_id,
                "repo": repo,
                "operator_id": operator_id,
                "case_id": case_id,
                "partitions": [list(partition) for partition in sorted(partitions)],
            }
            for (
                repository_id,
                repo,
                operator_id,
                case_id,
            ), partitions in sorted(cross_partition_cases.items())
        ],
        "repository_partition_count": len(repository_partitions),
        "grouping_failures": grouping_failures,
        "burden": {
            "mean": round(sum(legacy_burden_values) / len(legacy_burden_values), 8)
            if legacy_burden_values
            else None,
            "max": round(max(legacy_burden_values), 8)
            if legacy_burden_values
            else None,
            "bound": float(max_burden),
            "sample_count": len(legacy_burden_values),
            "scope": "legacy_operator_residual_only",
        },
        "conformance_burden": {
            "B_rms_mean": round(sum(conformance_b_rms) / len(conformance_b_rms), 12)
            if conformance_b_rms
            else None,
            "B_rms_max": round(max(conformance_b_rms), 12)
            if conformance_b_rms
            else None,
            "sample_count": len(conformance_b_rms),
            "threshold_source": "receipt_declared_conformance_tolerance",
        },
        "gates": gate_values,
        "next_actions": next_actions,
        "comparison_modes": sorted(modes),
        "required_comparison_arms": sorted(REQUIRED_COMPARISON_ARMS),
        "required_comparison_modes_per_arm": sorted(REQUIRED_COMPARISON_MODES),
        "type_mismatches": type_mismatches,
        "receipts": [receipt.to_dict() for receipt in report_receipts],
        "policy_effect": False,
        "advisory_only": True,
        "update_authorized": False,
        "claim_boundary": (
            "Activation conformance is independently reconstructed measurement "
            "telemetry. It is not prediction accuracy, task utility, learning "
            "authority, cognition, consciousness, or agency."
        ),
    }


__all__ = [
    "DEFAULT_EPSILON",
    "DEFAULT_MAX_BURDEN",
    "REQUIRED_COMPARISON_ARMS",
    "REQUIRED_COMPARISON_MODES",
    "REQUIRED_CONFORMANCE_INVARIANTS",
    "RESIDUAL_GLYPH",
    "RESIDUAL_SCHEMA",
    "ResidualReceipt",
    "residual_evidence_report",
]
