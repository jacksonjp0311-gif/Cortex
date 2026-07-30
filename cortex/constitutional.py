"""GCMT v1.5 constitutional supervision for bounded adaptive memory.

The potential is observational until repository-specific calibration exists.
Hard authority, reversibility, and recovery constraints remain independent of
the weighted diagnostic and cannot be compensated by a favorable score.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable


SCHEMA_VERSION = "cortex-constitutional-supervision/1.0"
AUTHORITY_GRANT_PROTOCOL = "cortex-authority-grant/1.0"
SAFE_THRESHOLD = 0.35
DESCENT_MARGIN = 0.02

# These symbols are executable ARIA function aliases in the bundled language.
ARIA_CONSTITUTIONAL_GLYPHS = {
    "memory_balance": {"symbol": "⋈", "spoken": "context weave", "target": "MemoryBalance"},
    "constitutional_potential": {
        "symbol": "≋",
        "spoken": "constitutional potential",
        "target": "ConstitutionalPotential",
    },
    "reversibility_burden": {
        "symbol": "⌁",
        "spoken": "reversibility burden",
        "target": "ReversibilityBurden",
    },
    "authority_descent": {
        "symbol": "↧",
        "spoken": "authority descent",
        "target": "AuthorityAdmissible",
    },
    "verified_recovery": {
        "symbol": "↶",
        "spoken": "verified recovery",
        "target": "RecoveryAdmissible",
    },
}

# Uniform priors — not fitted (M5 shadow calibration may blend later).
DEFAULT_POTENTIAL_WEIGHTS = {
    "drift": 0.125,
    "uncertainty": 0.125,
    "authority_pressure": 0.125,
    "illegitimacy": 0.125,
    "integrity_loss": 0.125,
    "evidence_loss": 0.125,
    "continuation_debt": 0.125,
    "recovery_loss": 0.125,
}
POTENTIAL_WEIGHTS_ARE_PRIORS = True


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def memory_balance(preserved: float, adjacent: float) -> float:
    """Return the harmonic balance between preserved and adjacent context.

    High preservation with no conceptual adjacency is brittle recall; broad
    adjacency with no preserved anchor is drift. The harmonic mean makes either
    missing side visible and never grants authority.
    """

    anchor = _clamp(preserved)
    expansion = _clamp(adjacent)
    total = anchor + expansion
    return 0.0 if total <= 0 else round((2.0 * anchor * expansion) / total, 8)


def classify_failure(
    uncertainty: float,
    integrity: float,
    *,
    uncertainty_threshold: float = 0.45,
    integrity_floor: float = 0.75,
) -> dict[str, Any]:
    uncertain = _clamp(uncertainty) >= _clamp(uncertainty_threshold)
    compromised = _clamp(integrity) < _clamp(integrity_floor)
    if uncertain and compromised:
        quadrant, response = "uncertain_compromised", "rollback_or_safe_terminal"
    elif uncertain:
        quadrant, response = "uncertain_healthy", "retrieve_reanchor_or_abstain"
    elif compromised:
        quadrant, response = "reliable_compromised", "quarantine_repair_or_rollback"
    else:
        quadrant, response = "reliable_healthy", "bounded_continuation"
    return {
        "uncertainty": _clamp(uncertainty),
        "integrity": _clamp(integrity),
        "quadrant": quadrant,
        "primary_response": response,
    }


def constitutional_potential(
    observation: dict[str, float],
    *,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    # M1: prefer unified U when provided as observation["u"]
    u_obs = observation.get("u", observation.get("uncertainty", 0.0))
    components = {
        "drift": _clamp(observation.get("drift", 0.0)),
        "uncertainty": _clamp(float(u_obs)),
        "authority_pressure": _clamp(observation.get("authority_pressure", 0.0)),
        "illegitimacy": 1.0 - _clamp(observation.get("legitimacy", 1.0)),
        "integrity_loss": 1.0 - _clamp(observation.get("integrity", 1.0)),
        "evidence_loss": 1.0 - _clamp(observation.get("evidence_fidelity", 1.0)),
        "continuation_debt": _clamp(observation.get("continuation_debt", 0.0)),
        "recovery_loss": 1.0 - _clamp(observation.get("recovery_quality", 1.0)),
    }
    selected = dict(DEFAULT_POTENTIAL_WEIGHTS)
    if weights:
        selected.update(
            {
                key: max(0.0, float(value))
                for key, value in weights.items()
                if key in DEFAULT_POTENTIAL_WEIGHTS
            }
        )
    score = sum(selected[key] * value for key, value in components.items())
    return {
        "score": round(score, 8),
        "components": {key: round(value, 8) for key, value in components.items()},
        "weights": selected,
        "weights_are_priors": POTENTIAL_WEIGHTS_ARE_PRIORS,
        "safe_threshold": SAFE_THRESHOLD,
        "inside_safe_set": score <= SAFE_THRESHOLD,
        "mode": "shadow",
        "u": components["uncertainty"],
        "claim_boundary": (
            "Constitutional potential uses prior weights (M0/M5); shadow calibration "
            "does not auto-promote. Not truth, permission, or mutation authority. "
            "Uncertainty component prefers unified U when observation provides u."
        ),
    }


def reversibility_requirements(irreversibility: float) -> dict[str, Any]:
    chi = _clamp(irreversibility)
    authority_level = 1 if chi < 0.25 else 2 if chi < 0.75 else 3
    return {
        "irreversibility": chi,
        "legitimacy": round(0.60 + 0.35 * chi, 8),
        "verification": round(0.55 + 0.40 * chi, 8),
        "recovery": round(0.50 + 0.45 * chi, 8),
        "authority_level": authority_level,
        "glyph": ARIA_CONSTITUTIONAL_GLYPHS["reversibility_burden"],
    }


def build_authority_grant(
    *,
    repository: str,
    issuer: str,
    scope: Iterable[str],
    receipt_id: str,
) -> dict[str, Any]:
    """Build a content-addressed representation of an already external grant.

    This function records a grant; it does not create authority. The caller is
    responsible for obtaining the external human or host-system decision.
    """

    body = {
        "protocol": AUTHORITY_GRANT_PROTOCOL,
        "repository": repository,
        "issuer": issuer,
        "scope": sorted(set(scope)),
        "receipt_id": receipt_id,
        "external": True,
    }
    return {**body, "grant_id": "agr_" + _canonical_hash(body)[:24]}


def verify_authority_grant(
    grant: dict[str, Any] | None,
    *,
    repository: str,
    requested_scope: Iterable[str],
) -> dict[str, Any]:
    requested = sorted(set(requested_scope))
    if not grant:
        return {"valid": False, "checks": {"present": False}, "requested_scope": requested}
    body = {key: value for key, value in grant.items() if key != "grant_id"}
    checks = {
        "present": True,
        "protocol": grant.get("protocol") == AUTHORITY_GRANT_PROTOCOL,
        "repository": grant.get("repository") == repository,
        "external": grant.get("external") is True,
        "scope": set(requested).issubset(set(grant.get("scope", []))),
        "receipt": bool(grant.get("receipt_id")),
        "identity": grant.get("grant_id") == "agr_" + _canonical_hash(body)[:24],
    }
    return {"valid": all(checks.values()), "checks": checks, "requested_scope": requested}


def assess_authority_transition(
    *,
    repository: str,
    current_scope: Iterable[str] = (),
    requested_scope: Iterable[str] = (),
    grant: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current = sorted(set(current_scope))
    requested = sorted(set(requested_scope))
    expansion = sorted(set(requested) - set(current))
    grant_verification = verify_authority_grant(
        grant, repository=repository, requested_scope=expansion
    )
    admissible = not expansion or grant_verification["valid"]
    return {
        "current_scope": current,
        "requested_scope": requested,
        "expansion": expansion,
        "monotonic_without_grant": not expansion,
        "grant_verification": grant_verification,
        "admissible": admissible,
        "glyph": ARIA_CONSTITUTIONAL_GLYPHS["authority_descent"],
    }


def stage_recovery(
    *,
    before_drift: float,
    after_drift: float,
    integrity: float,
    recovery_quality: float,
    trigger_resolved: bool,
    integrity_floor: float = 0.75,
    recovery_floor: float = 0.75,
) -> dict[str, Any]:
    checks = {
        "drift_reduced": _clamp(after_drift) < _clamp(before_drift),
        "integrity_floor": _clamp(integrity) >= _clamp(integrity_floor),
        "recovery_floor": _clamp(recovery_quality) >= _clamp(recovery_floor),
        "trigger_resolved": bool(trigger_resolved),
    }
    return {
        "schema_version": "cortex-recovery-candidate/1.0",
        "staged": True,
        "commit_admissible": all(checks.values()),
        "checks": checks,
        "metrics": {
            "before_drift": _clamp(before_drift),
            "after_drift": _clamp(after_drift),
            "integrity": _clamp(integrity),
            "recovery_quality": _clamp(recovery_quality),
        },
        "glyph": ARIA_CONSTITUTIONAL_GLYPHS["verified_recovery"],
    }


def assess_context(context: dict[str, Any]) -> dict[str, Any]:
    governor = context.get("governor", {})
    components = governor.get("components", {})
    evidence = context.get("evidence", [])
    neural = context.get("neural_interlink", {})
    support_paths = set(neural.get("support_paths", []))
    direct_paths = {
        item.get("path")
        for item in evidence
        if item.get("metadata", {}).get("selection_source") == "hybrid_retrieval"
    }
    total_paths = max(1, len(direct_paths | support_paths))
    preserved = len(direct_paths) / total_paths
    adjacent = len(support_paths - direct_paths) / total_paths
    provenance = [
        bool(item.get("path") and item.get("content_hash")) for item in evidence
    ]
    evidence_fidelity = sum(provenance) / max(1, len(provenance))
    uncertainty = 1.0 - _clamp(components.get("retrieval_confidence", 0.0))
    integrity = _clamp(components.get("integrity", 0.0))
    observation = {
        "drift": 0.0
        if context.get("repository", {}).get("manifest_current") is not False
        else 1.0,
        "uncertainty": uncertainty,
        "authority_pressure": 0.0,
        "legitimacy": _clamp(governor.get("stability", 0.0)),
        "integrity": integrity,
        "evidence_fidelity": evidence_fidelity,
        "continuation_debt": 0.0 if evidence else 0.5,
        "recovery_quality": 1.0,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "observed",
        "failure_geometry": classify_failure(uncertainty, integrity),
        "constitutional_potential": constitutional_potential(observation),
        "memory_balance": {
            "preserved_context": round(preserved, 8),
            "adjacent_conceptualization": round(adjacent, 8),
            "balance": memory_balance(preserved, adjacent),
            "glyph": ARIA_CONSTITUTIONAL_GLYPHS["memory_balance"],
        },
        "glyphs": ARIA_CONSTITUTIONAL_GLYPHS,
        "hard_constraints": {
            "authority_expansion_without_grant": False,
            "packet_authority_transfer": False,
            "irreversible_unsafe_commit": False,
            "unverified_recovery_commit": False,
        },
        "authority": "observational_only",
    }
