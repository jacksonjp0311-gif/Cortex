"""v6.25 Controller write firewall — adaptive operations consult this boundary.

Write classes:
  AUDIT_APPEND | EVIDENCE_REFRESH | SESSION_STATE | ADAPTIVE_WRITE | HOST_MUTATION

HOST_MUTATION is never granted by Cortex memory controllers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA = "cortex-controller-scope/1.0"

AUDIT_APPEND = "AUDIT_APPEND"
EVIDENCE_REFRESH = "EVIDENCE_REFRESH"
SESSION_STATE = "SESSION_STATE"
ADAPTIVE_WRITE = "ADAPTIVE_WRITE"
HOST_MUTATION = "HOST_MUTATION"

WRITE_CLASSES = frozenset(
    {AUDIT_APPEND, EVIDENCE_REFRESH, SESSION_STATE, ADAPTIVE_WRITE, HOST_MUTATION}
)

# Policy matrix: controller → allowed write classes
_POLICY: dict[str, frozenset[str]] = {
    "advanced": frozenset({AUDIT_APPEND, EVIDENCE_REFRESH, SESSION_STATE, ADAPTIVE_WRITE}),
    "evidence_baseline": frozenset({AUDIT_APPEND, EVIDENCE_REFRESH, SESSION_STATE}),
    "quarantine": frozenset({AUDIT_APPEND, SESSION_STATE}),
    "repair": frozenset({AUDIT_APPEND, SESSION_STATE, ADAPTIVE_WRITE}),  # scoped only
}

# Adaptive operations that require ADAPTIVE_WRITE
ADAPTIVE_OPS = frozenset(
    {
        "ranker_train",
        "ranker_unfreeze",
        "spectral_promote",
        "shadow_calibration",
        "structure_invent",
        "fusion_open",
        "fusion_tick",
        "auto_distill",
        "prefetch_write",
        "adaptive_budget",
        "learned_summary",
        "foreign_emerge",
        "auto_prune",
        "organism_learning_state",
        "plasticity_apply",
        "concept_route_mutate",
    }
)

CLAIM = (
    "Controller scope is a write firewall for adaptive memory operations. "
    "Never host source mutation. Not consciousness."
)


@dataclass
class ScopeDecision:
    allowed: bool
    controller: str
    write_class: str
    operation: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "controller": self.controller,
            "write_class": self.write_class,
            "operation": self.operation,
            "reason": self.reason,
            "claim_boundary": CLAIM,
        }


def normalize_controller(name: str | None) -> str:
    n = (name or "advanced").casefold().strip()
    if n in {"evidence_baseline", "evidence", "trusted", "baseline_controller"}:
        return "evidence_baseline"
    if n in {"quarantine", "quarantined"}:
        return "quarantine"
    if n in {"repair", "repairing"}:
        return "repair"
    return "advanced"


def allowed_write_classes(controller: str | None) -> list[str]:
    c = normalize_controller(controller)
    return sorted(_POLICY.get(c, _POLICY["evidence_baseline"]))


def check_write(
    controller: str | None,
    write_class: str,
    *,
    operation: str = "",
) -> ScopeDecision:
    c = normalize_controller(controller)
    wc = (write_class or "").strip()
    if wc == HOST_MUTATION:
        return ScopeDecision(
            False, c, wc, operation, "HOST_MUTATION never granted by Cortex controllers"
        )
    allowed = wc in _POLICY.get(c, frozenset())
    # evidence_baseline: EVIDENCE_REFRESH only when explicit (caller marks operation)
    if c == "evidence_baseline" and wc == EVIDENCE_REFRESH:
        if operation and operation not in {"explicit_index", "explicit_verify", "manual_refresh"}:
            return ScopeDecision(
                False,
                c,
                wc,
                operation,
                "evidence_baseline allows EVIDENCE_REFRESH only when explicit",
            )
    if c == "evidence_baseline" and wc == ADAPTIVE_WRITE:
        return ScopeDecision(
            False, c, wc, operation, "evidence_baseline forbids ADAPTIVE_WRITE"
        )
    if c == "quarantine" and wc == ADAPTIVE_WRITE:
        return ScopeDecision(False, c, wc, operation, "quarantine forbids ADAPTIVE_WRITE")
    if not allowed:
        return ScopeDecision(
            False, c, wc, operation, f"controller {c} cannot perform {wc}"
        )
    return ScopeDecision(True, c, wc, operation, "permitted")


def check_adaptive_op(controller: str | None, operation: str) -> ScopeDecision:
    """Gate a named adaptive subsystem operation."""
    op = (operation or "").strip()
    if op in ADAPTIVE_OPS or op.startswith("adaptive_"):
        return check_write(controller, ADAPTIVE_WRITE, operation=op)
    return check_write(controller, AUDIT_APPEND, operation=op or "audit")


def require_adaptive(controller: str | None, operation: str) -> None:
    d = check_adaptive_op(controller, operation)
    if not d.allowed:
        raise PermissionError(
            f"controller_scope denied {operation} under {d.controller}: {d.reason}"
        )


def scope_receipt(controller: str | None, blocked: list[str] | None = None) -> dict[str, Any]:
    c = normalize_controller(controller)
    return {
        "schema_version": SCHEMA,
        "controller": c,
        "allowed_write_classes": allowed_write_classes(c),
        "blocked_operations": list(blocked or []),
        "claim_boundary": CLAIM,
    }
