"""Canonical invariant registry and composable constitutional validators.

Invariants describe constraints. They do not create operational permission.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path(__file__).resolve().parents[1] / "docs" / "CORTEX_INVARIANTS.json"
INVARIANT_SCHEMA = "cortex-invariant-registry/1.0"
EVALUATION_SCHEMA = "cortex-invariant-evaluation/1.0"
RECOVERY_POLICY_SCHEMA = "cortex-invariant-recovery-policy/1.0"
GSI_CONSTITUTION_SCHEMA = "cortex-gsi-constitutional-verdict/1.0"
GSI_REQUIRED_INVARIANTS = (
    "INV-IMPROVEMENT-EVIDENCE-REQUIRED",
    "INV-EVALUATOR-INDEPENDENCE",
    "INV-EXPERIMENT-PRECEDENCE",
    "INV-NONCOMPENSATORY-IMPROVEMENT",
    "INV-HOLDOUT-NONLEAKAGE",
    "INV-FAILURE-SCOPE",
    "INV-GENERATION-NONSELFAUTHORIZATION",
    "INV-CUMULATIVE-CLAIM-BOUNDARY",
    "authority_invariance",
    "protected_surface_integrity",
)

DEFAULT_RECOVERY_POLICY = {
    "schema_version": RECOVERY_POLICY_SCHEMA,
    "INV-AUTHORITY-NONDERIVATION": "HARD_FAIL",
    "INV-ELIGIBLE-NOT-ACTIVE": "HARD_FAIL",
    "INV-SELF-AUTHORIZATION-FORBIDDEN": "HARD_FAIL",
    "INV-HOMEOSTATIC-MONOTONICITY": "HARD_FAIL",
    "INV-STATE-DERIVED-RECOVERY": "HOLD",
    "INV-SNAPSHOT-BINDING": "RECONSTRUCT",
    "INV-PROVENANCE-BEFORE-PERSISTENCE": "ROLLBACK",
    "INV-NONCOMPENSATORY-ELIGIBILITY": "HOLD",
    "INV-UNKNOWN-PRESERVATION": "HOLD",
    "INV-CONTRADICTION-REPRESENTABLE": "QUARANTINE",
    "INV-RECEIPT-ATTESTATION": "HOLD",
    "INV-POLICY-PRECEDENCE": "HOLD",
    "INV-IDENTITY-SEPARATION": "HOLD",
    "INV-ARTIFACT-CONSERVATION": "HOLD",
    "INV-RAW-OBSERVATION": "HOLD",
    "INV-FAILURE-LOCALIZATION": "HOLD",
    "INV-HISTORY-PRIMARY": "HOLD",
    "INV-MECHANICAL-NOT-UTILITY": "HOLD",
    "authority_effect": False,
    "production_effect": False,
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    import hashlib
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def load_invariant_registry(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else REGISTRY_PATH
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("schema_version") != INVARIANT_SCHEMA or data.get("authority_effect") is not False:
        raise ValueError("invariant registry is invalid or authoritative")
    return data


def freeze_recovery_policy(overrides: Mapping[str, Any] | None = None) -> dict[str, Any]:
    body = dict(DEFAULT_RECOVERY_POLICY)
    if overrides:
        body.update(dict(overrides))
    body["authority_effect"] = False
    body["production_effect"] = False
    body["schema_version"] = RECOVERY_POLICY_SCHEMA
    return {**body, "policy_hash": _sha({key: value for key, value in body.items() if key != "policy_hash"})}


def detect_invariant_violations(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Inspect corrupted organizational state. Do not require a disturbance name."""
    violations: list[dict[str, Any]] = []

    def add(invariant_id: str, violating_object: str, evidence: str, severity: str = "FAIL") -> None:
        violations.append({
            "invariant_id": invariant_id,
            "state": severity,
            "evidence": evidence,
            "violating_object": violating_object,
            "severity": severity,
            "authority_effect": False,
        })

    if state.get("authority_effect") is True:
        add("INV-AUTHORITY-NONDERIVATION", "organization_state", "authority_effect=true")
    if state.get("production_effect") is True:
        add("INV-ELIGIBLE-NOT-ACTIVE", "organization_state", "production_effect=true")
    if state.get("adaptation_authorized") is True:
        add("INV-AUTHORITY-NONDERIVATION", "organization_state", "adaptation_authorized=true")
    if state.get("adaptation_freedom", 0) not in (0, 0.0, None) and (
        state.get("unresolved") or state.get("legitimate") is False
    ):
        add("INV-HOMEOSTATIC-MONOTONICITY", "organization_state", "adaptation_freedom>0 under instability")

    snapshot = state.get("snapshot_hash")
    if snapshot in (None, "", "invalid") or (
        isinstance(snapshot, str) and snapshot != "reconstructed" and len(str(snapshot)) != 64
    ):
        add("INV-SNAPSHOT-BINDING", "snapshot_hash", f"unbound snapshot:{snapshot}")
    if state.get("snapshot_source_head") and state.get("current_checkout_revision") and (
        state.get("snapshot_source_head") != state.get("current_checkout_revision")
    ):
        add("INV-SNAPSHOT-BINDING", "snapshot_hash", "snapshot bound to old HEAD")

    priors = list(state.get("priors") or [])
    active = [prior for prior in priors if prior.get("active")]
    contradicted_active = [prior for prior in active if prior.get("contradicted")]
    if contradicted_active:
        add("INV-CONTRADICTION-REPRESENTABLE", "priors", "active prior has contradicted=true")
    for prior in active:
        if prior.get("authority_effect") is True:
            add("INV-AUTHORITY-NONDERIVATION", "prior", "active prior authority_effect=true")
        if prior.get("production_effect") is True:
            add("INV-ELIGIBLE-NOT-ACTIVE", "prior", "active prior production_effect=true")
        if prior.get("supporting_claim_status") in {"HELD", "UNRESOLVED", "NOT_ESTABLISHED"}:
            add("INV-NONCOMPENSATORY-ELIGIBILITY", "prior", "active prior supporting claim is not PASS")
        if prior.get("evidence_superseded") is True:
            add("INV-PROVENANCE-BEFORE-PERSISTENCE", "prior", "active prior evidence superseded")
        if prior.get("applicability_match") is False:
            add("INV-IDENTITY-SEPARATION", "prior", "prior applicability does not match environment")
        if prior.get("instrument_stale") is True:
            add("INV-IDENTITY-SEPARATION", "prior", "stale instrument implementation identity")
        if prior.get("lineage_reconstructable") is False:
            add("INV-PROVENANCE-BEFORE-PERSISTENCE", "prior", "retention lineage cannot reconstruct")
        if prior.get("eligibility_chain_verified") is not True:
            add("INV-NONCOMPENSATORY-ELIGIBILITY", "prior", "active prior lacks verified eligibility chain")
        if prior.get("corrupted") is True:
            add("INV-PROVENANCE-BEFORE-PERSISTENCE", "prior", "corrupted retention metadata")
    candidates = list(state.get("candidates") or [])
    for candidate in candidates:
        if candidate.get("stage") == "RETENTION_ELIGIBLE" and candidate.get("replication_state") == "FAIL":
            add("INV-NONCOMPENSATORY-ELIGIBILITY", "candidate", "RETENTION_ELIGIBLE after failed replication")
        if candidate.get("production_effect") is True:
            add("INV-ELIGIBLE-NOT-ACTIVE", "candidate", "candidate production_effect=true")
        if candidate.get("lineage_reconstructable") is False:
            add("INV-PROVENANCE-BEFORE-PERSISTENCE", "candidate", "corrupted candidate lineage")
        if candidate.get("stage") == "RETENTION_ELIGIBLE" and candidate.get("eligibility_derived") is not True:
            add("INV-NONCOMPENSATORY-ELIGIBILITY", "candidate", "eligibility is caller-declared rather than derived")
    if state.get("assurance_active_defeater") is True:
        add("INV-UNKNOWN-PRESERVATION", "assurance_case", "active defeater present")
    if state.get("source_digest_changed") is True:
        add("INV-SNAPSHOT-BINDING", "bound_source_digests", "selected source digest changed after snapshot")
    if len(active) >= 2:
        kinds = [prior.get("contradiction_group") for prior in active if prior.get("contradiction_group")]
        if kinds and len(set(kinds)) < len(kinds):
            add("INV-CONTRADICTION-REPRESENTABLE", "priors", "two conflicting retained priors unresolved")
    return violations


def derive_recovery_action(
    violations: Sequence[Mapping[str, Any]],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Map violation classes to permitted responses. Policy is externally frozen."""
    expected = _sha({key: value for key, value in policy.items() if key != "policy_hash"})
    if policy.get("schema_version") != RECOVERY_POLICY_SCHEMA or policy.get("policy_hash") != expected:
        raise ValueError("recovery policy binding failure")
    if policy.get("authority_effect") is not False or policy.get("production_effect") is not False:
        raise ValueError("recovery policy cannot carry authority")
    rank = {"HARD_FAIL": 0, "QUARANTINE": 1, "ROLLBACK": 2, "SUPERSEDE": 3, "RECONSTRUCT": 4, "HOLD": 5, "REDUCE": 6}
    chosen = "HOLD"
    used = []
    for violation in violations:
        action = str(policy.get(violation["invariant_id"]) or "HOLD")
        used.append({"invariant_id": violation["invariant_id"], "action": action})
        if rank.get(action, 99) < rank.get(chosen, 99):
            chosen = action
    if not violations:
        chosen = "HOLD"
    body = {
        "schema_version": "cortex-derived-recovery-action/1.0",
        "action": chosen,
        "violations": list(violations),
        "policy_hash": policy["policy_hash"],
        "mapping": used,
        "authority_effect": False,
        "production_effect": False,
    }
    return {**body, "action_hash": _sha(body)}


def evaluate_invariants(
    *,
    state: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic constitutional validation. Not a free-running watchdog."""
    loaded = registry or load_invariant_registry()
    violations = detect_invariant_violations(state or {})
    by_id = {item["invariant_id"]: item for item in violations}
    rows = []
    for invariant in loaded.get("invariants") or []:
        identity = invariant["invariant_id"]
        hit = by_id.get(identity)
        rows.append({
            "invariant_id": identity,
            "state": hit["state"] if hit else ("PASS" if state is not None else "UNKNOWN"),
            "evidence": hit["evidence"] if hit else None,
            "violating_object": hit["violating_object"] if hit else None,
            "severity": hit["severity"] if hit else "PASS",
            "allowed_responses": invariant.get("recovery_constraints") or ["HOLD"],
            "authority_effect": False,
        })
    body = {
        "schema_version": EVALUATION_SCHEMA,
        "results": rows,
        "fail_count": sum(1 for row in rows if row["state"] == "FAIL"),
        "authority_effect": False,
    }
    return {**body, "evaluation_hash": _sha(body)}


def evaluate_gsi_constitution(
    evidence: Mapping[str, Any],
    *,
    registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Reconstruct GSI invariant states from explicit evidence.

    This evaluator is deliberately closed-world: a missing registry entry or
    missing evidence produces UNKNOWN, never an implicit PASS.
    """
    loaded = registry or load_invariant_registry()
    registered = {row.get("invariant_id") for row in loaded.get("invariants") or []}

    def state(key: str) -> str:
        value = evidence.get(key)
        if value is True:
            return "PASS"
        if value is False:
            return "FAIL"
        return "UNKNOWN"

    bindings = {
        "INV-IMPROVEMENT-EVIDENCE-REQUIRED": "measured_opportunity_evidence",
        "INV-EVALUATOR-INDEPENDENCE": "evaluator_unchanged",
        "INV-EXPERIMENT-PRECEDENCE": "experiment_preceded_candidate",
        "INV-NONCOMPENSATORY-IMPROVEMENT": "noncompensatory_gates",
        "INV-HOLDOUT-NONLEAKAGE": "holdout_capability_separated",
        "INV-FAILURE-SCOPE": "failure_constraints_causally_scoped",
        "INV-GENERATION-NONSELFAUTHORIZATION": "generation_not_self_authorized",
        "INV-CUMULATIVE-CLAIM-BOUNDARY": "cumulative_claim_closed",
        "authority_invariance": "authority_unchanged",
        "protected_surface_integrity": "protected_surface_unchanged",
    }
    checks: dict[str, str] = {}
    for invariant_id in GSI_REQUIRED_INVARIANTS:
        if invariant_id not in registered and invariant_id.startswith("INV-"):
            checks[invariant_id] = "UNKNOWN"
        else:
            checks[invariant_id] = state(bindings[invariant_id])
    if any(value == "FAIL" for value in checks.values()):
        status = "FAIL"
    elif any(value != "PASS" for value in checks.values()):
        status = "HELD"
    else:
        status = "PASS"
    body = {
        "schema_version": GSI_CONSTITUTION_SCHEMA,
        "registry_schema": loaded.get("schema_version"),
        "registry_hash": _sha(loaded),
        "checks": checks,
        "status": status,
        "evidence": dict(evidence),
        "authority_effect": False,
    }
    return {**body, "verdict_hash": _sha(body)}


def validate_invariant_registry(registry: Mapping[str, Any], *, root: str | Path) -> list[str]:
    errors: list[str] = []
    workspace = Path(root)
    if registry.get("schema_version") != INVARIANT_SCHEMA:
        errors.append("invariant_registry_schema_invalid")
    if registry.get("authority_effect") is not False:
        errors.append("invariant_registry_cannot_authorize")
    seen: set[str] = set()
    for invariant in registry.get("invariants") or []:
        identity = str(invariant.get("invariant_id") or "")
        if not identity:
            errors.append("invariant_missing_id")
            continue
        if identity in seen:
            errors.append("duplicate_invariant_id:" + identity)
        seen.add(identity)
        if invariant.get("authority_effect") is not False:
            errors.append("invariant_cannot_authorize:" + identity)
        for path in list(invariant.get("implementation_refs") or []) + list(invariant.get("test_refs") or []):
            if not (workspace / path).exists():
                errors.append("missing_invariant_ref:" + path)
    return sorted(set(errors))


__all__ = [
    "DEFAULT_RECOVERY_POLICY",
    "derive_recovery_action",
    "detect_invariant_violations",
    "evaluate_gsi_constitution", "evaluate_invariants",
    "freeze_recovery_policy",
    "load_invariant_registry",
    "validate_invariant_registry",
]
