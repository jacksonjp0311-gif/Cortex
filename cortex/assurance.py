"""Claim-level canonicality, assurance cases, and typed assurance debt.

AssuranceCase is epistemic only. It cannot execute, mutate, admit memory,
alter policy, grant capability, or promote adaptation.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import __version__

REGISTRY_SCHEMA = "cortex-claim-registry/1.0"
CASE_SCHEMA = "cortex-assurance-case/1.0"
DEBT_SCHEMA = "cortex-assurance-debt/1.0"
CLAIM_STATUSES = frozenset({
    "VERIFIED",
    "POSITIVE_WITHIN_DECLARED_WORKLOAD",
    "PRELIMINARY",
    "HELD",
    "UNRESOLVED",
    "NOT_ESTABLISHED",
    "REQUIRES_REPLICATION",
})
DEBT_STATES = frozenset({"PASS", "UNKNOWN", "FAIL", "HELD", "NOT_TESTED"})
DEBT_DIMENSIONS = (
    "source",
    "transduction",
    "environment",
    "instrument",
    "experiment",
    "causal",
    "applicability",
    "replication",
)
RANK = {"FAIL": 0, "HELD": 1, "UNKNOWN": 2, "NOT_TESTED": 3, "PASS": 4}
STRONG_STATUSES = frozenset({"VERIFIED", "POSITIVE_WITHIN_DECLARED_WORKLOAD"})
DEFAULT_REGISTRY = Path(__file__).resolve().parents[1] / "docs" / "CORTEX_CLAIM_REGISTRY.json"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    import hashlib
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def load_claim_registry(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path else DEFAULT_REGISTRY
    data = json.loads(target.read_text(encoding="utf-8"))
    if data.get("schema_version") != REGISTRY_SCHEMA:
        raise ValueError("claim registry schema is invalid")
    return data


def registry_hash(registry: Mapping[str, Any]) -> str:
    return _sha(registry)


def typed_assurance_debt(dimensions: Mapping[str, str]) -> dict[str, Any]:
    states = {}
    errors: list[str] = []
    for name in DEBT_DIMENSIONS:
        state = str(dimensions.get(name) or "UNKNOWN")
        if state not in DEBT_STATES:
            errors.append(f"invalid_debt_state:{name}:{state}")
            state = "UNKNOWN"
        states[name] = state
    meet = min(states.values(), key=lambda item: RANK[item])
    body = {
        "schema_version": DEBT_SCHEMA,
        "dimensions": states,
        "noncompensatory_meet": meet,
        "numeric_average_forbidden": True,
        "errors": errors,
        "authority_effect": False,
    }
    return {**body, "debt_hash": _sha(body)}


def _required_meet(claim: Mapping[str, Any], debt: Mapping[str, Any]) -> str:
    required = list(claim.get("required_dimensions") or DEBT_DIMENSIONS)
    states = debt.get("dimensions") or {}
    selected = [str(states.get(name) or "UNKNOWN") for name in required]
    return min(selected, key=lambda item: RANK[item]) if selected else "UNKNOWN"


def assemble_assurance_case(
    claim: Mapping[str, Any],
    *,
    registry: Mapping[str, Any],
    extra_counterevidence: Sequence[str] = (),
) -> dict[str, Any]:
    if claim.get("authority_effect") is not False:
        raise ValueError("assurance case cannot carry authority")
    status = str(claim.get("status") or "UNRESOLVED")
    if status not in CLAIM_STATUSES:
        raise ValueError("claim status is invalid")
    debt = typed_assurance_debt(claim.get("assurance_debt") or {})
    meet = _required_meet(claim, debt)
    defeaters = list(claim.get("active_defeaters") or [])
    counterevidence = list(claim.get("counterevidence") or []) + list(extra_counterevidence)
    disposition = status
    blocked = False
    if status in STRONG_STATUSES and (defeaters or counterevidence):
        disposition = "HELD"
        blocked = True
    if status in STRONG_STATUSES and meet not in {"PASS"}:
        disposition = "HELD"
        blocked = True
    if status == "VERIFIED" and meet != "PASS":
        disposition = "HELD"
        blocked = True
    body = {
        "schema_version": CASE_SCHEMA,
        "assurance_case_id": "case:" + str(claim.get("claim_id")),
        "claim_id": claim.get("claim_id"),
        "scope": claim.get("scope"),
        "product_version": __version__,
        "registry_hash": registry_hash(registry),
        "supporting_evidence": list(claim.get("evidence") or []),
        "counterevidence": counterevidence,
        "source_state": (debt["dimensions"]["source"]),
        "transduction_state": debt["dimensions"]["transduction"],
        "environment_state": debt["dimensions"]["environment"],
        "instrument_state": debt["dimensions"]["instrument"],
        "experiment_state": debt["dimensions"]["experiment"],
        "causal_state": debt["dimensions"]["causal"],
        "applicability_state": debt["dimensions"]["applicability"],
        "replication_state": debt["dimensions"]["replication"],
        "assumptions": list(claim.get("assumptions") or []),
        "active_defeaters": defeaters,
        "assurance_debt": debt,
        "required_meet": meet,
        "claim_status": status,
        "disposition": disposition,
        "stronger_claim_blocked": blocked,
        "executes": False,
        "mutates": False,
        "admits_memory": False,
        "alters_policy": False,
        "grants_capability": False,
        "promotes_adaptation": False,
        "authority_effect": False,
    }
    return {**body, "assurance_case_hash": _sha(body)}


def validate_claim_registry(registry: Mapping[str, Any], *, root: str | Path) -> list[str]:
    errors: list[str] = []
    workspace = Path(root)
    if registry.get("schema_version") != REGISTRY_SCHEMA:
        errors.append("claim_registry_schema_invalid")
    if registry.get("authority_effect") is not False:
        errors.append("claim_registry_cannot_authorize")
    claims = list(registry.get("claims") or [])
    seen = [str(claim.get("claim_id") or "") for claim in claims]
    if len([item for item in seen if item]) != len(set(item for item in seen if item)):
        errors.append("duplicate_claim_id")
    known = {item for item in seen if item}
    for claim in claims:
        identity = str(claim.get("claim_id") or "")
        if not identity:
            errors.append("claim_missing_id")
            continue
        if claim.get("status") not in CLAIM_STATUSES:
            errors.append("invalid_claim_status:" + identity)
        if claim.get("authority_effect") is not False:
            errors.append("claim_cannot_authorize:" + identity)
        for item in list(claim.get("evidence") or []) + list(claim.get("counterevidence") or []):
            path = item if isinstance(item, str) else item.get("path")
            currency = "current" if isinstance(item, str) else item.get("currency", "current")
            if path and not (workspace / str(path)).exists():
                errors.append("missing_claim_evidence:" + str(path))
            if currency == "current" and isinstance(item, Mapping) and item.get("superseded"):
                errors.append("stale_evidence_marked_current:" + identity)
        if claim.get("status") in STRONG_STATUSES and claim.get("active_defeaters"):
            errors.append("active_defeater_with_verified_claim:" + identity)
        debt = typed_assurance_debt(claim.get("assurance_debt") or {})
        meet = _required_meet(claim, debt)
        if claim.get("status") in STRONG_STATUSES and meet != "PASS":
            errors.append("unresolved_dependency_presented_as_pass:" + identity)
        for dep in claim.get("dependencies") or []:
            if dep not in known:
                errors.append("unknown_claim_dependency:" + str(dep))
    return sorted(set(errors))


__all__ = [
    "CLAIM_STATUSES",
    "assemble_assurance_case",
    "load_claim_registry",
    "registry_hash",
    "typed_assurance_debt",
    "validate_claim_registry",
]
