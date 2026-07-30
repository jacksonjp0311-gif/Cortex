"""v6.25.1 Capability-based controller boundary.

Strings describe state; only ExecutionCapability grants authority.
Unknown controller / operation / missing capability → deny.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass, field
from typing import Any, FrozenSet

from .controller_scope import (
    ADAPTIVE_WRITE,
    AUDIT_APPEND,
    EVIDENCE_REFRESH,
    HOST_MUTATION,
    SESSION_STATE,
    WRITE_CLASSES,
)

SCHEMA = "cortex-capabilities/1.1"
GLYPH = "⌘"

CLAIM = (
    "Execution capabilities authorize bounded adaptive operations. "
    "Missing/invalid/expired capability denies. Not host mutation. Not consciousness."
)

# Central operation registry — unregistered operations are denied
OPERATION_REGISTRY: dict[str, str] = {
    # adaptive
    "ranker_train": ADAPTIVE_WRITE,
    "ranker_unfreeze": ADAPTIVE_WRITE,
    "ranker_rebuild": ADAPTIVE_WRITE,
    "structure_invent": ADAPTIVE_WRITE,
    "spectral_promote": ADAPTIVE_WRITE,
    "shadow_calibration": ADAPTIVE_WRITE,
    "fusion_open": ADAPTIVE_WRITE,
    "fusion_tick": ADAPTIVE_WRITE,
    "auto_distill": ADAPTIVE_WRITE,
    "prefetch_write": ADAPTIVE_WRITE,
    "adaptive_budget": ADAPTIVE_WRITE,
    "learned_summary": ADAPTIVE_WRITE,
    "foreign_emerge": ADAPTIVE_WRITE,
    "auto_prune": ADAPTIVE_WRITE,
    "organism_learning_state": ADAPTIVE_WRITE,
    "plasticity_apply": ADAPTIVE_WRITE,
    "connect_pass_write": ADAPTIVE_WRITE,
    "stream_adaptive": ADAPTIVE_WRITE,
    "self_org": ADAPTIVE_WRITE,
    # session / audit
    "session_begin": SESSION_STATE,
    "session_end": SESSION_STATE,
    "audit_append": AUDIT_APPEND,
    "controller_resolved": AUDIT_APPEND,
    "evidence_kernel_queried": AUDIT_APPEND,
    "certificate_observed": AUDIT_APPEND,
    "manifest_observed": AUDIT_APPEND,
    "activation_completed": AUDIT_APPEND,
    "activation_failed": AUDIT_APPEND,
    # evidence
    "explicit_index": EVIDENCE_REFRESH,
    "explicit_verify": EVIDENCE_REFRESH,
    "manual_refresh": EVIDENCE_REFRESH,
    # repair allowlist only
    "repair_snapshot_create": ADAPTIVE_WRITE,
    "repair_quarantine": ADAPTIVE_WRITE,
    "repair_invalidate": ADAPTIVE_WRITE,
    "repair_synapse_remove": ADAPTIVE_WRITE,
    "repair_ranker_rebuild": ADAPTIVE_WRITE,
    "repair_calibration_invalidate": ADAPTIVE_WRITE,
    "repair_fusion_reset": ADAPTIVE_WRITE,
    "repair_reconstruct": ADAPTIVE_WRITE,
    "repair_verify": AUDIT_APPEND,
    "repair_rollback": ADAPTIVE_WRITE,
    "repair_readmit": ADAPTIVE_WRITE,
    # read-only classified
    "read_only_query": AUDIT_APPEND,
}

REPAIR_ALLOWLIST: FrozenSet[str] = frozenset(
    {
        "repair_snapshot_create",
        "repair_quarantine",
        "repair_invalidate",
        "repair_synapse_remove",
        "repair_ranker_rebuild",
        "repair_calibration_invalidate",
        "repair_fusion_reset",
        "repair_reconstruct",
        "repair_verify",
        "repair_rollback",
        "repair_readmit",
        "audit_append",
    }
)

ADVANCED_OPS: FrozenSet[str] = frozenset(
    k for k, v in OPERATION_REGISTRY.items() if v == ADAPTIVE_WRITE and not k.startswith("repair_")
) | frozenset(
    {
        "session_begin",
        "session_end",
        "audit_append",
        "explicit_index",
        "explicit_verify",
        "manual_refresh",
        "read_only_query",
    }
)

BASELINE_OPS: FrozenSet[str] = frozenset(
    {
        "audit_append",
        "controller_resolved",
        "evidence_kernel_queried",
        "certificate_observed",
        "manifest_observed",
        "activation_completed",
        "activation_failed",
        "read_only_query",
        "explicit_index",
        "explicit_verify",
        "manual_refresh",
        "session_begin",  # minimal — activation may avoid
    }
)


@dataclass(frozen=True)
class ExecutionCapability:
    capability_id: str
    repo: str
    controller: str
    allowed_operations: tuple[str, ...]
    allowed_write_classes: tuple[str, ...]
    issued_by: str
    issued_at: float
    expires_at: float
    reason: str
    nonce: str
    configuration_hash: str
    receipt_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ExecutionCapability":
        return ExecutionCapability(
            capability_id=str(d["capability_id"]),
            repo=str(d["repo"]),
            controller=str(d["controller"]),
            allowed_operations=tuple(d.get("allowed_operations") or ()),
            allowed_write_classes=tuple(d.get("allowed_write_classes") or ()),
            issued_by=str(d.get("issued_by") or "system"),
            issued_at=float(d.get("issued_at") or 0),
            expires_at=float(d.get("expires_at") or 0),
            reason=str(d.get("reason") or ""),
            nonce=str(d.get("nonce") or ""),
            configuration_hash=str(d.get("configuration_hash") or ""),
            receipt_hash=str(d.get("receipt_hash") or ""),
        )


@dataclass
class CapabilityDecision:
    allowed: bool
    reason: str
    capability_id: str | None = None
    operation: str = ""
    write_class: str = ""
    controller: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "capability_id": self.capability_id,
            "operation": self.operation,
            "write_class": self.write_class,
            "controller": self.controller,
            "claim_boundary": CLAIM,
        }


def _ops_for_controller(controller: str) -> tuple[str, ...]:
    c = (controller or "evidence_baseline").casefold().strip()
    if c in {"unknown", ""}:
        c = "evidence_baseline"
    if c == "repair":
        return tuple(sorted(REPAIR_ALLOWLIST))
    if c == "quarantine":
        return tuple(sorted(BASELINE_OPS | {"repair_quarantine", "repair_invalidate"}))
    if c in {"evidence_baseline", "evidence", "trusted"}:
        return tuple(sorted(BASELINE_OPS))
    if c == "advanced":
        return tuple(sorted(ADVANCED_OPS | REPAIR_ALLOWLIST))
    # unknown controller → baseline ops only
    return tuple(sorted(BASELINE_OPS))


def _classes_for_controller(controller: str) -> tuple[str, ...]:
    c = (controller or "evidence_baseline").casefold().strip()
    if c == "advanced":
        return (AUDIT_APPEND, EVIDENCE_REFRESH, SESSION_STATE, ADAPTIVE_WRITE)
    if c == "repair":
        return (AUDIT_APPEND, SESSION_STATE, ADAPTIVE_WRITE)
    if c == "quarantine":
        return (AUDIT_APPEND, SESSION_STATE)
    # baseline / unknown
    return (AUDIT_APPEND, EVIDENCE_REFRESH, SESSION_STATE)


class CapabilityIssuer:
    """Issues immutable capabilities."""

    def __init__(self, issuer: str = "governor") -> None:
        self.issuer = issuer

    def issue(
        self,
        *,
        repo: str,
        controller: str,
        reason: str = "activation",
        ttl_s: float = 3600.0,
        operations: list[str] | None = None,
        write_classes: list[str] | None = None,
    ) -> ExecutionCapability:
        c = (controller or "evidence_baseline").casefold().strip()
        if c in {"unknown", ""}:
            c = "evidence_baseline"
        if c not in {"advanced", "evidence_baseline", "quarantine", "repair", "evidence", "trusted"}:
            c = "evidence_baseline"
        if c in {"evidence", "trusted"}:
            c = "evidence_baseline"
        ops = tuple(operations) if operations else _ops_for_controller(c)
        wcs = tuple(write_classes) if write_classes else _classes_for_controller(c)
        now = time.time()
        nonce = secrets.token_hex(8)
        body = {
            "repo": repo,
            "controller": c,
            "ops": ops,
            "wcs": wcs,
            "issued_by": self.issuer,
            "issued_at": now,
            "expires_at": now + ttl_s,
            "reason": reason,
            "nonce": nonce,
        }
        cfg = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        cid = "cap_" + cfg[:20]
        receipt = hashlib.sha256(f"{cid}|{cfg}".encode()).hexdigest()
        return ExecutionCapability(
            capability_id=cid,
            repo=repo,
            controller=c,
            allowed_operations=ops,
            allowed_write_classes=wcs,
            issued_by=self.issuer,
            issued_at=now,
            expires_at=now + ttl_s,
            reason=reason,
            nonce=nonce,
            configuration_hash=cfg,
            receipt_hash=receipt,
        )


def validate_capability(
    capability: ExecutionCapability | None,
    *,
    repo: str,
    operation: str,
    now: float | None = None,
) -> CapabilityDecision:
    """Strict capability validation — failures deny."""
    op = (operation or "").strip()
    if not op:
        return CapabilityDecision(False, "missing_operation", operation=op)
    if op not in OPERATION_REGISTRY:
        return CapabilityDecision(False, "unknown_operation", operation=op)
    write_class = OPERATION_REGISTRY[op]
    if write_class == HOST_MUTATION:
        return CapabilityDecision(
            False, "HOST_MUTATION_never", operation=op, write_class=write_class
        )
    if capability is None:
        return CapabilityDecision(
            False, "missing_capability", operation=op, write_class=write_class
        )
    if not isinstance(capability, ExecutionCapability):
        try:
            capability = ExecutionCapability.from_dict(capability)  # type: ignore[arg-type]
        except Exception:
            return CapabilityDecision(False, "invalid_capability_type", operation=op)

    t = now if now is not None else time.time()
    ctrl = (capability.controller or "").casefold().strip()
    if ctrl not in {"advanced", "evidence_baseline", "quarantine", "repair"}:
        return CapabilityDecision(
            False,
            "unknown_controller",
            capability_id=capability.capability_id,
            operation=op,
            controller=ctrl,
        )
    if capability.repo != repo:
        return CapabilityDecision(
            False,
            "capability_repo_mismatch",
            capability_id=capability.capability_id,
            operation=op,
            controller=ctrl,
        )
    if t > float(capability.expires_at):
        return CapabilityDecision(
            False,
            "capability_expired",
            capability_id=capability.capability_id,
            operation=op,
            controller=ctrl,
        )
    if op not in capability.allowed_operations:
        return CapabilityDecision(
            False,
            "operation_not_in_capability",
            capability_id=capability.capability_id,
            operation=op,
            write_class=write_class,
            controller=ctrl,
        )
    if write_class not in capability.allowed_write_classes:
        return CapabilityDecision(
            False,
            "write_class_not_in_capability",
            capability_id=capability.capability_id,
            operation=op,
            write_class=write_class,
            controller=ctrl,
        )
    if ctrl == "repair" and op not in REPAIR_ALLOWLIST:
        return CapabilityDecision(
            False,
            "repair_allowlist_denied",
            capability_id=capability.capability_id,
            operation=op,
            controller=ctrl,
        )
    if ctrl == "evidence_baseline" and write_class == ADAPTIVE_WRITE:
        return CapabilityDecision(
            False,
            "evidence_baseline_forbids_adaptive",
            capability_id=capability.capability_id,
            operation=op,
            controller=ctrl,
        )
    return CapabilityDecision(
        True,
        "authorized",
        capability_id=capability.capability_id,
        operation=op,
        write_class=write_class,
        controller=ctrl,
    )


def require_capability(
    capability: ExecutionCapability | None,
    *,
    repo: str,
    operation: str,
) -> CapabilityDecision:
    d = validate_capability(capability, repo=repo, operation=operation)
    if not d.allowed:
        raise PermissionError(
            f"capability denied op={operation} reason={d.reason} "
            f"cap={d.capability_id}"
        )
    return d


def issue_for_controller(
    repo: str,
    controller: str,
    *,
    reason: str = "runtime",
    issuer: str = "governor",
    ttl_s: float = 3600.0,
) -> ExecutionCapability:
    return CapabilityIssuer(issuer).issue(
        repo=repo, controller=controller, reason=reason, ttl_s=ttl_s
    )
