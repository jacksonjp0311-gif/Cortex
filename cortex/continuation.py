"""Governed Continuation Memory Theory primitives for Cortex.

Operational state, evidence, and canonical state remain separate. This module
can promote only Cortex-owned canonical memory; it never mutates repository
source, configuration, or external systems.
"""

from __future__ import annotations

from hashlib import sha256
import json
import time
from typing import Any

from .constitutional import (
    assess_authority_transition,
    reversibility_requirements,
    stage_recovery,
)


def _hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(canonical.encode("utf-8")).hexdigest()


def build_continuation_packet(
    store: Any,
    context: dict[str, Any],
    *,
    origin_version: str,
    ttl_seconds: int = 86_400,
) -> dict[str, Any]:
    """Compile a GCMT verified continuation packet from a Cortex context."""
    repo = context["repository"]["name"]
    neural = context.get("neural_interlink", {})
    evidence = [
        {
            "memory_id": item.get("memory_id"),
            "repo": item.get("repo", repo),
            "path": item.get("path"),
            "line_range": item.get("line_range"),
            "content_hash": item.get("content_hash"),
            "selection_source": item.get("metadata", {}).get("selection_source"),
        }
        for item in context.get("evidence", [])
    ]
    canonical_states = [
        {
            "key": row["state_key"],
            "state_hash": row["state_hash"],
            "receipt_id": row["receipt_id"],
        }
        for row in store.canonical_states(repo)
    ]
    governor = context.get("governor", {})
    components = governor.get("components", {})
    retrieval_confidence = float(components.get("retrieval_confidence", 0.0))
    origin_drift = (
        0.0
        if (
            context["repository"].get("bootstrap_status") == "verified"
            and context["repository"].get("manifest_current") is not False
            and context["repository"].get("manifest_hash")
        )
        else 1.0
    )
    contradictions: list[dict[str, Any]] = []
    unknowns = ["Compressed operational state is not a complete evidence record."]
    if not evidence:
        contradictions.append({"kind": "insufficient_evidence", "severity": 1.0})
        unknowns.append("No task-relevant evidence was selected.")
    if governor.get("mode") == "read_only":
        contradictions.append({"kind": "governance_read_only", "severity": 1.0})

    reanchor_reasons: list[str] = []
    if origin_drift > 0:
        reanchor_reasons.append("origin_drift")
    if retrieval_confidence < 0.20:
        reanchor_reasons.append("low_retrieval_confidence")
    if contradictions:
        reanchor_reasons.append("active_contradiction_or_ambiguity")

    created_at = time.time()
    payload = {
        "protocol": "cortex-continuation/1.1",
        "origin": {
            "repository": repo,
            "repository_id": context["repository"].get("repository_id"),
            "manifest_hash": context["repository"].get("manifest_hash"),
            "version": origin_version,
        },
        "operational_state": {
            "task": context.get("task"),
            "active_focus": context.get("active_focus"),
            "evidence_ids": [item["memory_id"] for item in evidence if item["memory_id"]],
            "fired_paths": neural.get("fired_paths", []),
            "support_paths": neural.get("support_paths", []),
            "estimated_tokens": context.get("estimated_tokens", 0),
            "capacity": context.get("context_budget", 0),
            "meta_language": context.get("environment", {}).get("meta_language"),
        },
        "evidence_state": {
            "references": evidence,
            "packet_hash": context.get("packet_hash"),
            "neural_state_hash": neural.get("state_hash"),
        },
        "canonical_state": canonical_states,
        "drift": {
            "origin_deviation": origin_drift,
            "retrieval_uncertainty": round(1.0 - retrieval_confidence, 6),
            "manifest_current": context["repository"].get("manifest_current"),
        },
        "wounds": contradictions,
        "unknowns": unknowns,
        "authority": {
            **governor.get("authority", {}),
            "governor_mode": governor.get("mode", "read_only"),
            "claimed_scope": [],
            "effective_scope": [],
            "claimed_scope_metadata_only": True,
            "application_authorized": False,
            "promotion_authorized": False,
        },
        "constitutional_state": context.get("constitutional_supervision", {}),
        "verification": {
            "bootstrap_verified": context["repository"].get("bootstrap_status") == "verified",
            "database_integrity": bool(components.get("integrity", 0.0) >= 1.0),
            "provenance_complete": all(item["path"] and item["content_hash"] for item in evidence),
            "neural_ledger_valid": neural.get("ledger_valid", True),
        },
        "receipts": {
            "latest": canonical_states[-1]["receipt_id"] if canonical_states else None,
            "rollback_available": True,
        },
        "conditions": {
            "created_at": created_at,
            "expires_at": created_at + max(1, ttl_seconds),
            "reanchor_required": bool(reanchor_reasons),
            "reanchor_reasons": reanchor_reasons,
            "promotion_requires": [
                "source evidence",
                "explicit verification",
                "explicit promotion authority",
                "receipt",
                "rollback path",
            ],
        },
    }
    state_hash = _hash(payload)
    packet_id = "vcp_" + _hash([repo, state_hash])[:24]
    payload["packet_id"] = packet_id
    payload["state_hash"] = state_hash
    store.save_continuation_packet(
        repo,
        packet_id,
        origin_version,
        state_hash,
        payload,
        payload["conditions"]["expires_at"],
    )
    return payload


def verify_continuation_packet(packet: dict[str, Any], *, now: float | None = None) -> dict[str, Any]:
    material = {
        key: value for key, value in packet.items() if key not in {"packet_id", "state_hash"}
    }
    expected = _hash(material)
    current_time = time.time() if now is None else now
    authority = packet.get("authority", {})
    protocol = packet.get("protocol")
    checks = {
        "protocol": protocol in {"cortex-continuation/1.0", "cortex-continuation/1.1"},
        "state_hash": expected == packet.get("state_hash"),
        "origin_identity": bool(packet.get("origin", {}).get("repository_id")),
        "evidence_addressable": all(
            item.get("path") and item.get("content_hash")
            for item in packet.get("evidence_state", {}).get("references", [])
        ),
        "not_expired": current_time <= float(
            packet.get("conditions", {}).get("expires_at", 0)
        ),
        "rollback_declared": bool(
            packet.get("receipts", {}).get("rollback_available", False)
        ),
        "authority_boundary": (
            True
            if protocol == "cortex-continuation/1.0"
            else bool(authority.get("claimed_scope_metadata_only"))
            and not bool(authority.get("application_authorized"))
            and not bool(authority.get("promotion_authorized"))
        ),
    }
    return {"valid": all(checks.values()), "checks": checks, "expected_state_hash": expected}


def rebind_continuation_packet(
    packet: dict[str, Any],
    *,
    local_authority: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import continuity while deriving effective authority only from the receiver."""

    verification = verify_continuation_packet(packet)
    if not verification["valid"]:
        raise ValueError("Continuation packet failed verification")
    local = local_authority or {}
    claimed = packet.get("authority", {})
    payload = {
        "protocol": "cortex-continuation-import/1.0",
        "source": {
            "packet_id": packet.get("packet_id"),
            "state_hash": packet.get("state_hash"),
            "repository": packet.get("origin", {}).get("repository"),
        },
        "continuity": {
            "operational_state": packet.get("operational_state", {}),
            "evidence_state": packet.get("evidence_state", {}),
            "canonical_state": packet.get("canonical_state", []),
            "constitutional_state": packet.get("constitutional_state", {}),
            "receipts": packet.get("receipts", {}),
        },
        "authority": {
            "claimed_scope": claimed.get(
                "claimed_scope", claimed.get("effective_scope", [])
            ),
            "claimed_scope_metadata_only": True,
            "effective_scope": sorted(set(local.get("scope", []))),
            "application_authorized": bool(local.get("application_authorized", False)),
            "promotion_authorized": bool(local.get("promotion_authorized", False)),
            "source": "local_constitution",
        },
        "verification": {
            "source_packet": verification,
            "authority_rebound": True,
            "packet_granted_authority": False,
        },
    }
    payload["state_hash"] = _hash(payload)
    payload["import_id"] = "vci_" + _hash(
        [payload["source"], payload["state_hash"]]
    )[:24]
    return payload


def promote(
    store: Any,
    repo: str,
    *,
    state_key: str,
    candidate: Any,
    evidence: list[dict[str, Any]],
    verification: dict[str, bool],
    authority: dict[str, Any],
    quality: dict[str, float] | None = None,
    threshold: float = 0.80,
    irreversibility: float = 0.0,
    current_scope: list[str] | None = None,
    requested_scope: list[str] | None = None,
    authority_grant: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Promote a value into Cortex canonical memory after all GCMT locks pass."""
    quality = quality or {
        "source": 1.0 if evidence else 0.0,
        "drift": 1.0,
        "boundary": 1.0,
        "repeatability": 1.0 if verification.get("repeatable") else 0.0,
        "authority": 1.0 if authority.get("promotion_authorized") else 0.0,
        "rollback": 1.0,
    }
    normalized = {key: max(0.0, min(1.0, float(value))) for key, value in quality.items()}
    score = 1.0
    for value in normalized.values():
        score *= value
    requirements = reversibility_requirements(irreversibility)
    verification_score = (
        sum(bool(value) for value in verification.values()) / max(1, len(verification))
    )
    authority_level = int(
        authority.get("level", 3 if authority.get("promotion_authorized") else 0)
    )
    authority_transition = assess_authority_transition(
        repository=repo,
        current_scope=current_scope or authority.get("current_scope", []),
        requested_scope=requested_scope or authority.get("requested_scope", []),
        grant=authority_grant or authority.get("grant"),
    )
    reversibility_checks = {
        "legitimacy": normalized.get("boundary", 1.0) >= requirements["legitimacy"],
        "verification": verification_score >= requirements["verification"],
        "recovery": normalized.get("rollback", 1.0) >= requirements["recovery"],
        "authority_level": authority_level >= requirements["authority_level"],
    }
    hard_locks = {
        "source": bool(evidence) and all(item.get("content_hash") for item in evidence),
        "authority": bool(authority.get("promotion_authorized")),
        "verification": bool(verification) and all(bool(value) for value in verification.values()),
        "receipt": store.verify_continuation_receipts(repo),
        "rollback": True,
        "authority_monotonicity": authority_transition["admissible"],
        "reversibility": all(reversibility_checks.values()),
    }
    accepted = score >= threshold and all(hard_locks.values())
    if not accepted:
        return {
            "promoted": False,
            "state_key": state_key,
            "quality_score": round(score, 8),
            "threshold": threshold,
            "hard_locks": hard_locks,
            "constitutional": {
                "authority": authority_transition,
                "reversibility": {
                    "requirements": requirements,
                    "checks": reversibility_checks,
                },
            },
            "reason": "candidate remains operational; promotion gates did not all pass",
        }
    current = store.canonical_state(repo, state_key)
    if current and json.loads(current["value_json"]) == candidate:
        return {
            "promoted": False,
            "state_key": state_key,
            "quality_score": round(score, 8),
            "threshold": threshold,
            "hard_locks": hard_locks,
            "reason": "candidate already matches canonical state",
            "canonical_receipt_id": current["receipt_id"],
            "constitutional": {
                "authority": authority_transition,
                "reversibility": {
                    "requirements": requirements,
                    "checks": reversibility_checks,
                },
            },
        }
    receipt_id = "rcp_" + _hash(
        [
            repo,
            state_key,
            candidate,
            evidence,
        verification,
        {
            **authority,
            "authority_transition": authority_transition,
            "reversibility": {
                "requirements": requirements,
                "checks": reversibility_checks,
            },
        },
            store.continuation_receipt_tail(repo),
        ]
    )[:24]
    receipt = store.promote_canonical_state(
        repo,
        receipt_id=receipt_id,
        state_key=state_key,
        candidate=candidate,
        evidence=evidence,
        verification=verification,
        authority={
            **authority,
            "authority_transition": authority_transition,
            "reversibility": {
                "requirements": requirements,
                "checks": reversibility_checks,
            },
        },
    )
    return {
        "promoted": True,
        "quality_score": round(score, 8),
        "threshold": threshold,
        "hard_locks": hard_locks,
        "constitutional": {
            "authority": authority_transition,
            "reversibility": {
                "requirements": requirements,
                "checks": reversibility_checks,
            },
        },
        **receipt,
    }


def rollback(
    store: Any,
    repo: str,
    receipt_id: str,
    *,
    authorized: bool,
    recovery_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not authorized:
        return {
            "rolled_back": False,
            "receipt_id": receipt_id,
            "reason": "explicit rollback authority is required",
        }
    if not store.verify_continuation_receipts(repo):
        return {
            "rolled_back": False,
            "receipt_id": receipt_id,
            "reason": "continuation receipt ledger integrity failed",
        }
    observation = recovery_observation or {
        "before_drift": 1.0,
        "after_drift": 0.0,
        "integrity": 1.0,
        "recovery_quality": 1.0,
        "trigger_resolved": True,
    }
    candidate = stage_recovery(**observation)
    if not candidate["commit_admissible"]:
        return {
            "rolled_back": False,
            "receipt_id": receipt_id,
            "recovery_candidate": candidate,
            "reason": "staged recovery candidate failed constitutional checks",
        }
    return store.rollback_canonical_state(
        repo,
        receipt_id,
        authority={"rollback_authorized": True, "human_authorized": True},
        recovery_verification=candidate,
    )
