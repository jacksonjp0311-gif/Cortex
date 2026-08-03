"""Minimal, read-only OSTT contracts for existing Cortex transitions.

OSTT separates known execution, admissible routing, and unresolved residuals.
This module only audits those boundaries around already-existing Cortex
surfaces. It never runs an operator, trains a model, or changes policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

SCHEMA = "cortex-ostt/1.0"
GLYPH = "▤"
CLAIM = (
    "OSTT contracts are read-only typed execution telemetry. They do not run "
    "operators, grant authority, prove performance, or establish consciousness."
)


@dataclass(frozen=True)
class TypedState:
    """Small serializable state descriptor used for contract admission."""

    type_id: str
    provenance: str = ""
    uncertainty: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.type_id:
            errors.append("type_id_missing")
        try:
            uncertainty = float(self.uncertainty)
        except (TypeError, ValueError):
            uncertainty = -1.0
        if not 0.0 <= uncertainty <= 1.0:
            errors.append("uncertainty_out_of_range")
        if not self.provenance:
            errors.append("provenance_missing")
        return errors

    def to_dict(self) -> dict[str, Any]:
        try:
            uncertainty = round(float(self.uncertainty), 8)
        except (TypeError, ValueError):
            uncertainty = self.uncertainty
        return {
            "type_id": self.type_id,
            "provenance": self.provenance,
            "uncertainty": uncertainty,
            "metadata": dict(self.metadata),
            "valid": not self.validate(),
        }


@dataclass(frozen=True)
class OperatorContract:
    """Declared domain, gates, invariants, uncertainty, and cost for a step."""

    operator_id: str
    domain_type: str
    codomain_type: str
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    uncertainty_rule: str = "bounded_observation"
    cost: float = 1.0
    validation: str = "receipt_and_invariant_check"

    def evaluate(
        self,
        *,
        state_type: str,
        facts: Mapping[str, bool],
        budget: float | None = None,
    ) -> "OperatorTrace":
        missing: list[str] = []
        if state_type != self.domain_type:
            missing.append(f"domain_mismatch:{state_type}->{self.domain_type}")
        missing.extend(
            name for name in self.preconditions if facts.get(name) is not True
        )
        if budget is not None and float(self.cost) > float(budget):
            missing.append("cost_budget_exceeded")
        return OperatorTrace(
            operator_id=self.operator_id,
            domain_type=self.domain_type,
            codomain_type=self.codomain_type,
            admissible=not missing,
            missing_preconditions=tuple(missing),
            postconditions=self.postconditions,
            invariants=self.invariants,
            uncertainty_rule=self.uncertainty_rule,
            cost=float(self.cost),
            validation=self.validation,
        )


@dataclass(frozen=True)
class OperatorTrace:
    """Serializable audit receipt for one declared operator boundary."""

    operator_id: str
    domain_type: str
    codomain_type: str
    admissible: bool
    missing_preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    uncertainty_rule: str = ""
    cost: float = 0.0
    validation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "domain_type": self.domain_type,
            "codomain_type": self.codomain_type,
            "admissible": bool(self.admissible),
            "missing_preconditions": list(self.missing_preconditions),
            "postconditions": list(self.postconditions),
            "invariants": list(self.invariants),
            "uncertainty_rule": self.uncertainty_rule,
            "cost": round(float(self.cost), 8),
            "validation": self.validation,
        }


CORE_CONTRACTS: tuple[OperatorContract, ...] = (
    OperatorContract(
        "repository_assimilation",
        "RepositorySource",
        "EvidenceIndex",
        ("manifest_current",),
        ("indexed_evidence",),
        ("host_immutable",),
        "manifest_and_retrieval_calibration",
        1.0,
    ),
    OperatorContract(
        "epoch_binding",
        "EvidenceIndex",
        "BodyEpoch",
        ("certificate_verified", "manifest_current"),
        ("epoch_current",),
        ("epoch_identity_preserved",),
        "root_hash_receipt",
        0.5,
    ),
    OperatorContract(
        "activation_observation",
        "TaskRequest",
        "ActivationReceipt",
        ("epoch_current", "governor_allows"),
        ("measured_delta",),
        ("host_immutable",),
        "measured_event_field",
        1.0,
    ),
    OperatorContract(
        "temporal_resonance",
        "EpochFrames",
        "ResonanceReport",
        ("same_epoch_frames",),
        ("temporal_classification",),
        ("advisory_only",),
        "bounded_frequency_sweep",
        0.5,
    ),
    OperatorContract(
        "informational_interlock",
        "ActivationReceipt",
        "InterlockReport",
        ("cohort_scoped", "independent_outcomes"),
        ("elo_measurement",),
        ("shadow_only",),
        "cohort_synergy_proxy",
        0.5,
    ),
    OperatorContract(
        "bounded_learning",
        "VerifiedOutcome",
        "BoundedUpdate",
        ("evidence_valid", "epoch_current", "independent_witness", "learning_gate_open"),
        ("receipted_update",),
        ("host_immutable", "no_silent_overwrite"),
        "verified_outcome_only",
        1.0,
    ),
)


def audit_runtime(runtime: Mapping[str, Any]) -> dict[str, Any]:
    """Audit current Cortex telemetry against the OSTT contract registry."""
    self_sensing = str(runtime.get("self_sensing_classification") or "UNKNOWN")
    binding = str(runtime.get("binding_classification") or "UNKNOWN")
    interlock = runtime.get("interlock") or {}
    readiness = interlock.get("readiness") or {}
    facts: dict[str, bool] = {
        "manifest_current": bool(runtime.get("manifest_current")),
        "certificate_verified": str(runtime.get("certificate_status") or "") == "verified",
        "epoch_current": bool(runtime.get("epoch_verified")) and bool(runtime.get("phase_bound")),
        "governor_allows": not bool(runtime.get("immune_block")),
        "same_epoch_frames": int(runtime.get("same_epoch_frames") or 0) >= 16,
        "cohort_scoped": bool(interlock.get("cohort_current")),
        "independent_outcomes": bool(interlock.get("data_ready")),
        "evidence_valid": bool(runtime.get("evidence_valid")),
        "independent_witness": bool((interlock.get("promotion_gates") or {}).get("witness_gate")),
        "learning_gate_open": (
            self_sensing == "NOMINAL"
            and binding not in {"DRIFT_REGIME", "BINDING_GAP", "UNBOUND"}
            and bool((interlock.get("promotion_gates") or {}).get("eligible"))
        ),
    }
    state_types = {
        "repository_assimilation": "RepositorySource",
        "epoch_binding": "EvidenceIndex",
        "activation_observation": "TaskRequest",
        "temporal_resonance": "EpochFrames",
        "informational_interlock": "ActivationReceipt",
        "bounded_learning": "VerifiedOutcome",
    }
    traces = [
        contract.evaluate(
            state_type=state_types[contract.operator_id],
            facts=facts,
        ).to_dict()
        for contract in CORE_CONTRACTS
    ]
    residuals: list[str] = []
    if self_sensing != "NOMINAL":
        residuals.append("observer_regime_residual")
    if str(runtime.get("resonance_status") or "") != "stable_peak":
        residuals.append("temporal_resonance_residual")
    if not bool(interlock.get("data_ready")):
        residuals.append("outcome_evidence_residual")
    if not facts["manifest_current"]:
        residuals.append("source_manifest_residual")
    admissible = sum(1 for trace in traces if trace["admissible"])
    from .residuals import residual_evidence_report

    residual_evidence = residual_evidence_report(
        CORE_CONTRACTS,
        runtime.get("operator_residuals") or (),
    )
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "mode": "shadow",
        "operator_count": len(traces),
        "admissible_count": admissible,
        "held_count": len(traces) - admissible,
        "facts": facts,
        "operators": traces,
        "residuals": {
            "unresolved": residuals,
            "burden_status": residual_evidence["status"],
            "operator_evidence": residual_evidence["status"],
            "claim_boundary": "Self-sensing residual and OSTT residual burden are distinct until a dedicated receipt exists.",
        },
        "residual_evidence": residual_evidence,
        "readiness": {
            "next_actions": list(readiness.get("next_actions") or []),
            "same_epoch_frames_remaining": (readiness.get("remaining") or {}).get("same_epoch_frames"),
            "valid_samples_remaining": (readiness.get("remaining") or {}).get("valid_samples_in_cohort"),
        },
        "policy_effect": False,
        "advisory_only": True,
        "claim_boundary": CLAIM,
    }


__all__ = [
    "CLAIM",
    "CORE_CONTRACTS",
    "GLYPH",
    "OperatorContract",
    "OperatorTrace",
    "SCHEMA",
    "TypedState",
    "audit_runtime",
]
