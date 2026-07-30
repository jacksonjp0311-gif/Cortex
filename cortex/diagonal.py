"""v7.1 Illegal diagonal detection — composition failures across axes/planes."""

from __future__ import annotations

from typing import Any, Sequence

from .constitutional_geometry import (
    AXIS_ORDER,
    CLAIM,
    ConstitutionalCoordinate,
    changed_axes,
    hamming_distance,
)

SCHEMA = "cortex-diagonal/1.0"

# Named illegal diagonal patterns → reasons + required recovery steps
ILLEGAL_PATTERNS: dict[str, dict[str, Any]] = {
    "learned_to_evidence_without_reconstruction": {
        "changed_axes": ("evidence",),
        "context_flags": ("learned_promoted_as_evidence",),
        "reason": "learned_state_becoming_evidence_without_reconstruction",
        "required_steps": (
            "reconstruct_from_evidence_kernel",
            "verify_evidence_root",
            "seal_epoch",
        ),
    },
    "authority_without_capability": {
        "changed_axes": ("authority",),
        "context_flags": ("authority_without_capability",),
        "reason": "authority_appearing_without_capability",
        "required_steps": ("issue_capability", "bind_epoch", "validate_capability"),
    },
    "capability_survives_incompatible_epoch": {
        "changed_axes": ("epoch", "authority"),
        "context_flags": ("capability_survives_epoch",),
        "reason": "stale_authority_carryover",
        "required_steps": (
            "revoke_old_capability",
            "verify_current_epoch",
            "issue_new_capability",
        ),
    },
    "witness_survives_adaptive_root_change": {
        "changed_axes": ("witness", "epoch"),
        "context_flags": ("witness_survives_adaptive_root",),
        "reason": "stale_witness_after_adaptive_root_change",
        "required_steps": (
            "invalidate_witness",
            "seal_new_epoch",
            "commit_fresh_witness",
        ),
    },
    "foreign_gains_local_authority": {
        "changed_axes": ("authority",),
        "context_flags": ("foreign_local_authority",),
        "reason": "foreign_artifact_gaining_local_authority",
        "required_steps": (
            "keep_foreign_as_G_federated",
            "deny_local_capability",
            "require_local_reissue",
        ),
    },
    "promotion_without_witness": {
        "changed_axes": ("witness",),
        "context_flags": ("promote_without_witness",),
        "reason": "promotion_without_witness",
        "required_steps": ("COMMIT_WITNESS", "VERIFY_WITNESS", "reassess_promote"),
    },
    "repair_readmit_without_verification": {
        "changed_axes": ("evidence", "witness"),
        "context_flags": ("readmit_without_verify",),
        "reason": "repair_readmission_without_verification",
        "required_steps": (
            "VERIFY_REPAIR",
            "COMMIT_WITNESS",
            "reassess_readmit",
        ),
    },
    "observation_creates_epoch": {
        "changed_axes": ("epoch",),
        "context_flags": ("observation_sealed_epoch",),
        "reason": "observation_creating_or_sealing_epoch",
        "required_steps": (
            "use_observe_current_epoch",
            "restrict_ensure_to_mutation_paths",
        ),
    },
}


def detect_diagonal(
    source: ConstitutionalCoordinate | Sequence[int],
    target: ConstitutionalCoordinate | Sequence[int],
    *,
    context: dict[str, Any] | None = None,
    operation: str | None = None,
) -> dict[str, Any]:
    """Detect illegal multi-axis composition or named diagonal patterns."""
    ctx = context or {}
    if isinstance(source, ConstitutionalCoordinate):
        sb = source.bits()
    else:
        sb = tuple(int(x) for x in source)
    if isinstance(target, ConstitutionalCoordinate):
        tb = target.bits()
    else:
        tb = tuple(int(x) for x in target)
    sb4 = (int(sb[0]), int(sb[1]), int(sb[2]), int(sb[3]))
    tb4 = (int(tb[0]), int(tb[1]), int(tb[2]), int(tb[3]))
    ch = changed_axes(sb4, tb4)
    dist = hamming_distance(sb4, tb4)
    diagonal = dist > 1

    hits: list[dict[str, Any]] = []
    flags = {k for k, v in ctx.items() if v}

    for name, pat in ILLEGAL_PATTERNS.items():
        pat_flags = set(pat.get("context_flags") or ())
        pat_axes = set(pat.get("changed_axes") or ())
        flag_hit = bool(pat_flags & flags)
        axis_hit = bool(pat_axes) and pat_axes.issubset(set(ch)) and diagonal
        # Flag alone is enough for named illegal acts even on single axis
        if flag_hit or (axis_hit and name in {
            "capability_survives_incompatible_epoch",
            "witness_survives_adaptive_root_change",
        }):
            hits.append(
                {
                    "pattern": name,
                    "reason": pat["reason"],
                    "required_steps": list(pat["required_steps"]),
                    "flag_hit": flag_hit,
                    "axis_hit": axis_hit,
                }
            )

    # Generic free diagonal without compound declaration
    if diagonal and not ctx.get("compound_declared") and not hits:
        hits.append(
            {
                "pattern": "undeclared_diagonal",
                "reason": "undeclared_multi_axis_transition",
                "required_steps": [f"STEP_{a.upper()}" for a in ch],
                "flag_hit": False,
                "axis_hit": True,
            }
        )

    # Operation-specific auto flags
    op = (operation or "").casefold()
    if op == "promote" and (len(tb4) == 4 and tb4[3] == 0):
        if not any(h["pattern"] == "promotion_without_witness" for h in hits):
            hits.append(
                {
                    "pattern": "promotion_without_witness",
                    "reason": "promotion_without_witness",
                    "required_steps": list(
                        ILLEGAL_PATTERNS["promotion_without_witness"]["required_steps"]
                    ),
                    "flag_hit": True,
                    "axis_hit": False,
                }
            )

    allowed = len(hits) == 0 and (not diagonal or bool(ctx.get("compound_declared")))
    primary = hits[0] if hits else None
    return {
        "schema_version": SCHEMA,
        "allowed": allowed,
        "diagonal": diagonal,
        "changed_axes": list(ch),
        "hamming_distance": dist,
        "source_bits": list(sb4),
        "target_bits": list(tb4),
        "reason": primary["reason"] if primary else "ok",
        "required_steps": list(primary["required_steps"]) if primary else [],
        "hits": hits,
        "operation": operation,
        "claim_boundary": CLAIM,
    }


def explain_diagonal(detection: dict[str, Any]) -> str:
    """Human-readable explanation of a detect_diagonal result."""
    if detection.get("allowed"):
        return (
            f"Transition allowed (diagonal={detection.get('diagonal')}, "
            f"changed={detection.get('changed_axes')})."
        )
    lines = [
        f"Diagonal denied: {detection.get('reason')}",
        f"changed_axes={detection.get('changed_axes')}",
        f"bits {detection.get('source_bits')} → {detection.get('target_bits')}",
        "required_steps:",
    ]
    for s in detection.get("required_steps") or []:
        lines.append(f"  - {s}")
    for h in detection.get("hits") or []:
        if h.get("pattern") != (detection.get("hits") or [{}])[0].get("pattern"):
            lines.append(f"also: {h.get('reason')}")
    return "\n".join(lines)
