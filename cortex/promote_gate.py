"""Promotion gate — holdout + foreign transfer required for big claims (v6.20).

System learning / calibration observe / KEEP-style claims must not fire on
train-set or perfect-ceiling victories alone.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "cortex-promote-gate/1.0"
GLYPH = "⌗⌘"

# Holdout corpus freeze id — bump when HOLDOUT_CORPUS intentionally changes.
HOLDOUT_FREEZE_ID = "holdout-v1-2026-07-30"


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
) -> dict[str, Any]:
    """Decide whether promotion / shadow-calibrate / big KEEP claims may fire."""

    if governance_mode == "read_only":
        return _deny("governor_read_only")

    ho = holdout_report or {}
    ho_gate = ho.get("gate") or {}
    ho_base = (ho.get("ablations") or {}).get("baseline") or {}
    ho_recall = float(ho_base.get("recall_at_k") or 0.0)
    ho_winner = str(ho.get("winner") or "")
    ho_ceiling = bool(ho_gate.get("perfect_recall_ceiling"))

    reasons: list[str] = []
    if ho_recall < min_holdout_recall:
        reasons.append(f"holdout_recall<{min_holdout_recall}")
    if ho_winner != "baseline" and not ho_gate.get("baseline_is_winner"):
        reasons.append("holdout_baseline_not_winner")
    if ho_ceiling and ho_recall >= 0.999:
        # Perfect holdout is ok for promote; perfect *train-only* is not.
        pass
    if not emergent_coupling:
        reasons.append("emergent_coupling_off")

    foreign_ok = True
    fr_recall = None
    if require_foreign:
        if not foreign_report or foreign_report.get("error"):
            foreign_ok = False
            reasons.append("foreign_suite_missing_or_error")
        else:
            fr_base = (foreign_report.get("ablations") or {}).get("baseline") or {}
            fr_recall = float(fr_base.get("recall_at_k") or 0.0)
            if fr_recall < min_foreign_recall:
                foreign_ok = False
                reasons.append(f"foreign_recall<{min_foreign_recall}")
            if foreign_report.get("repo") == (holdout_report or {}).get("repo"):
                # Same repo is not a transfer proof
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
        # Refuse if only train is perfect and holdout is weak (already covered)
        if train_recall >= 0.999 and ho_recall < min_holdout_recall:
            reasons.append("train_perfect_holdout_weak")

    if not (ho_winner == "baseline" or ho_gate.get("baseline_is_winner")):
        reasons.append("holdout_baseline_not_winner")
    if governance_mode not in {"normal", "constrained"}:
        reasons.append(f"governance_mode={governance_mode}")

    allow = (
        ho_recall >= min_holdout_recall
        and bool(ho_gate.get("baseline_is_winner") or ho_winner == "baseline")
        and emergent_coupling
        and foreign_ok
        and governance_mode in {"normal", "constrained"}
    )

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "allow_promote": allow,
        "allow_shadow_calibration": allow,
        "allow_system_learning_claim": allow,
        "holdout_recall": ho_recall,
        "foreign_recall": fr_recall,
        "train_recall": train_recall,
        "emergent_coupling": emergent_coupling,
        "holdout_freeze_id": HOLDOUT_FREEZE_ID,
        "reasons_if_denied": [] if allow else (reasons or ["denied"]),
        "law": (
            "Promote only when sealed holdout utility holds AND foreign transfer "
            "suite holds AND emergent coupling is on. Train-set wins never suffice."
        ),
        "claim_boundary": (
            "Promotion gate is evaluation policy, not host authority or consciousness."
        ),
    }


def _deny(reason: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "allow_promote": False,
        "allow_shadow_calibration": False,
        "allow_system_learning_claim": False,
        "reasons_if_denied": [reason],
        "claim_boundary": (
            "Promotion gate is evaluation policy, not host authority or consciousness."
        ),
    }


def _deny_reasons(
    ho_recall: float,
    min_ho: float,
    foreign_ok: bool,
    emergent: bool,
    mode: str,
) -> list[str]:
    r = []
    if ho_recall < min_ho:
        r.append(f"holdout_recall<{min_ho}")
    if not foreign_ok:
        r.append("foreign_transfer_failed")
    if not emergent:
        r.append("emergent_coupling_off")
    if mode == "read_only":
        r.append("governor_read_only")
    return r or ["denied"]
