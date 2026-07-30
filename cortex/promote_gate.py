"""Promotion gate — utility + witness + lineage; coupling is safety only (v6.25).

Coupling health may *block* when unhealthy, but must not alone *certify* utility.
Foreign transfer suite is development_transfer utility, not sealed witness proof.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "cortex-promote-gate/1.1"
GLYPH = "⌗⌘"

# Holdout corpus freeze id — bump when HOLDOUT_CORPUS intentionally changes.
HOLDOUT_FREEZE_ID = "holdout-v1-2026-07-30"

CLAIM = (
    "Promotion gate is evaluation policy: sealed holdout + transfer utility + "
    "governance + lineage/wound hygiene. Coupling is a safety prerequisite only, "
    "not independent utility certification. Not host authority. Not consciousness."
)


def evaluate_promotion(
    *,
    holdout_report: dict[str, Any] | None,
    foreign_report: dict[str, Any] | None = None,
    train_report: dict[str, Any] | None = None,
    emergent_coupling: bool = False,
    governance_mode: str = "normal",
    min_holdout_recall: float = 0.5,
    min_foreign_recall: float = 0.4,
    require_foreign: bool = True,
    witness_report: dict[str, Any] | None = None,
    require_witness: bool = False,
    min_witness_recall: float = 0.5,
    lineage_ok: bool = True,
    has_critical_wound: bool = False,
    body_epoch_id: str | None = None,
    epoch_verified: bool | None = None,
    store: Any = None,
    repo: str | None = None,
    capability: Any | None = None,
    authority_ok: bool | None = None,
    skip_geometry: bool = False,
) -> dict[str, Any]:
    """Decide whether promotion / shadow-calibrate / big KEEP claims may fire."""

    if governance_mode == "read_only":
        return _deny("governor_read_only")
    # v7.0: promotion must not certify a different/stale epoch when bound
    if epoch_verified is False:
        return _deny("body_epoch_not_verified")

    # v7.1 constitutional geometry boundary
    geometry: dict[str, Any] | None = None
    if not skip_geometry and store is not None and repo:
        try:
            from .constitutional_path import assess_operation_at_boundary

            wit_ok = None
            if witness_report is not None:
                wit_ok = bool(
                    not witness_report.get("error")
                    and float(witness_report.get("recall_at_k") or 0) >= min_witness_recall
                )
            elif require_witness:
                wit_ok = False
            geometry = assess_operation_at_boundary(
                store,
                repo,
                "promote",
                capability=capability,
                authority_ok=authority_ok if authority_ok is not None else True,
                witness_ok=wit_ok if wit_ok is not None else (True if not require_witness else False),
                require_witness=True,
            )
            if not geometry.get("allowed"):
                denied = _deny("constitutional_geometry_denied")
                denied["geometry"] = geometry
                denied["coordinate"] = geometry.get("coordinate")
                denied["missing_axes"] = geometry.get("missing_axes")
                denied["required_legal_path"] = geometry.get("required_legal_path")
                denied["reasons_if_denied"] = list(
                    dict.fromkeys(
                        ["constitutional_geometry_denied"]
                        + list(geometry.get("reasons") or [])
                        + [f"missing_{a}" for a in (geometry.get("missing_axes") or [])]
                    )
                )
                return denied
        except Exception as exc:
            geometry = {"error": f"{type(exc).__name__}:{exc}"}

    ho = holdout_report or {}
    ho_gate = ho.get("gate") or {}
    ho_base = (ho.get("ablations") or {}).get("baseline") or {}
    ho_recall = float(ho_base.get("recall_at_k") or 0.0)
    ho_winner = str(ho.get("winner") or "")

    reasons: list[str] = []
    if ho_recall < min_holdout_recall:
        reasons.append(f"holdout_recall<{min_holdout_recall}")
    if ho_winner != "baseline" and not ho_gate.get("baseline_is_winner"):
        reasons.append("holdout_baseline_not_winner")

    # Coupling: safety prerequisite only — blocks when off, never sole proof
    if not emergent_coupling:
        reasons.append("coupling_health_off_safety_block")

    foreign_ok = True
    fr_recall = None
    if require_foreign:
        if not foreign_report or foreign_report.get("error"):
            foreign_ok = False
            reasons.append("development_transfer_suite_missing_or_error")
        else:
            fr_base = (foreign_report.get("ablations") or {}).get("baseline") or {}
            fr_recall = float(fr_base.get("recall_at_k") or 0.0)
            if fr_recall < min_foreign_recall:
                foreign_ok = False
                reasons.append(f"development_transfer_recall<{min_foreign_recall}")
            if foreign_report.get("repo") == (holdout_report or {}).get("repo"):
                foreign_ok = False
                reasons.append("foreign_repo_same_as_body")

    train_recall = None
    if train_report:
        train_recall = float(
            ((train_report.get("ablations") or {}).get("baseline") or {}).get(
                "recall_at_k"
            )
            or 0.0
        )
        if train_recall >= 0.999 and ho_recall < min_holdout_recall:
            reasons.append("train_perfect_holdout_weak")

    if not (ho_winner == "baseline" or ho_gate.get("baseline_is_winner")):
        reasons.append("holdout_baseline_not_winner")
    if governance_mode not in {"normal", "constrained"}:
        reasons.append(f"governance_mode={governance_mode}")

    if not lineage_ok:
        reasons.append("lineage_integrity_failed")
    if has_critical_wound:
        reasons.append("active_critical_wound")

    witness_ok = True
    wit_recall = None
    if require_witness:
        if not witness_report or witness_report.get("error"):
            witness_ok = False
            reasons.append("sealed_witness_missing")
        else:
            wit_recall = float(witness_report.get("recall_at_k") or 0.0)
            if wit_recall < min_witness_recall:
                witness_ok = False
                reasons.append(f"witness_recall<{min_witness_recall}")

    # Advanced must not lose to evidence baseline when simplex present
    if ho_gate.get("advanced_beats_evidence_baseline") is False:
        reasons.append("advanced_loses_to_evidence_baseline")

    allow = (
        ho_recall >= min_holdout_recall
        and bool(ho_gate.get("baseline_is_winner") or ho_winner == "baseline")
        and emergent_coupling  # safety block only when false
        and foreign_ok
        and witness_ok
        and lineage_ok
        and not has_critical_wound
        and governance_mode in {"normal", "constrained"}
        and ho_gate.get("advanced_beats_evidence_baseline") is not False
    )

    out = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "allow_promote": allow,
        "allow_shadow_calibration": allow,
        "allow_system_learning_claim": allow,
        "holdout_recall": ho_recall,
        "foreign_recall": fr_recall,
        "development_transfer_recall": fr_recall,
        "witness_recall": wit_recall,
        "train_recall": train_recall,
        "emergent_coupling": emergent_coupling,
        "coupling_role": "safety_prerequisite_only",
        "holdout_freeze_id": HOLDOUT_FREEZE_ID,
        "body_epoch_id": body_epoch_id,
        "epoch_verified": epoch_verified,
        "reasons_if_denied": [] if allow else list(dict.fromkeys(reasons)),
        "law": (
            "Promote when sealed holdout utility holds AND development-transfer utility "
            "holds AND coupling health is on (safety) AND lineage/wounds clean AND "
            "governance allows AND body epoch is verified when bound AND "
            "constitutional geometry (e,a,t,w)=(1,1,1,1) when store bound. "
            "Coupling does not certify utility. "
            "Optional sealed witness when require_witness=True."
        ),
        "claim_boundary": CLAIM,
    }
    if geometry is not None:
        out["geometry"] = geometry
        out["coordinate"] = geometry.get("coordinate")
    return out


def _deny(reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "allow_promote": False,
        "allow_shadow_calibration": False,
        "allow_system_learning_claim": False,
        "holdout_recall": None,
        "foreign_recall": None,
        "train_recall": None,
        "emergent_coupling": False,
        "coupling_role": "safety_prerequisite_only",
        "holdout_freeze_id": HOLDOUT_FREEZE_ID,
        "reasons_if_denied": [reason],
        "law": "Denied.",
        "claim_boundary": CLAIM,
    }
