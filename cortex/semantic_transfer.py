"""Lightweight readiness and adaptive policy for semantic-transfer trials.

This module spends no model calls.  It may close a future experiment when the
canonical lesson/corpus geometry is insufficient; it can never open empirical
legitimacy or promote a memory.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__
from .admitted_memory import deep_verify_admitted_memory, list_admitted_memories
from .memory_projection import evaluate_memory_eligibility

SCHEMA = "cortex-semantic-transfer-readiness/1.0"
VERSION = "10.0.0-alpha.15"
CLAIM_BOUNDARY = (
    "Readiness is an advisory experiment preflight. It may prevent model calls; "
    "it cannot establish transfer, rewrite memory, or authorize execution."
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _historical_valid(report: Mapping[str, Any]) -> bool:
    blocking = {
        str(item)
        for item in report.get("errors") or ()
        if str(item) != "will_not_current"
    }
    return bool(
        report.get("structural_validity") is True
        and report.get("lineage_validity") is True
        and report.get("evidence_validity") is True
        and not blocking
    )


def _semantic_binding(memory: Mapping[str, Any]) -> tuple[str, list[str]]:
    material = memory.get("candidate_material")
    if not isinstance(material, Mapping):
        return "legacy_partial", ["candidate_material_missing"]
    reasons: list[str] = []
    for field in ("candidate_id", "candidate_type", "summary", "support_level"):
        if field not in material:
            reasons.append(f"candidate_material_{field}_missing")
        elif material.get(field) != memory.get(field):
            reasons.append(f"candidate_material_{field}_mismatch")
    if not str(memory.get("summary") or "").strip():
        reasons.append("semantic_summary_missing")
    return ("fail" if reasons else "pass"), reasons


def assess_semantic_transfer_readiness(
    store: Any,
    repo: str,
    *,
    task_families: Sequence[str] = (),
    body_epoch_id: str = "",
    minimum_ready_lessons: int = 2,
    maximum_next_run_calls: int = 6,
    persist: bool = False,
) -> dict[str, Any]:
    """Audit canonical lesson geometry and derive a fail-closed next-run plan."""
    current_will = store.get_setting(f"will_latest:{repo}", None) or None
    memories = list_admitted_memories(store, repo, limit=10_000)
    rows: list[dict[str, Any]] = []
    counts = {
        "canonical_ready": 0,
        "failed": 0,
        "unknown": 0,
        "legacy_partial": 0,
        "stale_or_inactive": 0,
    }
    semantic_hashes: set[str] = set()

    for memory in memories:
        deep = deep_verify_admitted_memory(store, repo, memory)
        semantic_state, semantic_reasons = _semantic_binding(memory)
        eligibility = evaluate_memory_eligibility(
            store,
            repo,
            memory,
            live_epoch_id=body_epoch_id or None,
            current_will=current_will,
            task="",
            min_support="low",
            require_deep_lineage=True,
        )
        historical = _historical_valid(deep)
        active = eligibility.get("eligible") is True
        reasons = sorted(
            set(
                semantic_reasons
                + [str(item) for item in deep.get("errors") or ()]
                + [str(item) for item in eligibility.get("exclusions") or ()]
            )
        )
        if semantic_state == "legacy_partial":
            state = "legacy_partial"
        elif not historical or semantic_state == "fail":
            state = "failed"
        elif not active:
            state = "stale_or_inactive"
        else:
            state = "canonical_ready"
            semantic_hashes.add(
                _sha(
                    {
                        "candidate_type": memory.get("candidate_type"),
                        "summary": memory.get("summary"),
                        "evidence": memory.get("evidence"),
                    }
                )
            )
        counts[state] += 1
        rows.append(
            {
                "memory_id": str(memory.get("memory_id") or ""),
                "candidate_type": str(memory.get("candidate_type") or ""),
                "support_level": str(memory.get("support_level") or "none"),
                "semantic_binding_state": semantic_state,
                "readiness_state": state,
                "reasons": reasons,
                "memory_receipt_hash": str(memory.get("receipt_hash") or ""),
            }
        )

    families = sorted({str(item).strip() for item in task_families if str(item).strip()})
    enough_lessons = counts["canonical_ready"] >= max(2, int(minimum_ready_lessons))
    distinct_lessons = len(semantic_hashes) >= 2
    corpus_declared = len(families) > 0
    # Names describe intent; they are not canonical calibration evidence.
    # Alpha.15 deliberately cannot open this gate from caller declarations.
    corpus_calibrated = False
    ready = enough_lessons and distinct_lessons and corpus_calibrated

    blockers: list[str] = []
    if counts["canonical_ready"] == 0:
        blockers.append("no_canonical_semantic_lesson")
    elif not enough_lessons:
        blockers.append("relevant_and_sham_pair_missing")
    if not distinct_lessons:
        blockers.append("semantic_distinctness_insufficient")
    if not corpus_calibrated:
        blockers.append("non_ceiling_target_corpus_missing")
    if counts["legacy_partial"]:
        blockers.append("legacy_lessons_require_revalidation")

    if counts["canonical_ready"] == 0:
        next_action = "generate_modern_verified_source_experience"
    elif not enough_lessons or not distinct_lessons:
        next_action = "forge_relevant_and_sham_lesson_pair"
    elif not corpus_calibrated:
        next_action = "calibrate_non_ceiling_target_corpus"
    else:
        next_action = "run_bounded_three_arm_pulse"

    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "kind": "semantic_transfer_readiness",
        "repo": repo,
        "body_epoch_id": body_epoch_id,
        "state": "SEMANTIC_TRANSFER_READY" if ready else "SEMANTIC_TRANSFER_HELD",
        "memory_count": len(memories),
        "counts": counts,
        "memory_diagnostics": rows,
        "task_families": families,
        "gates": {
            "canonical_relevant_and_sham_lessons": "pass" if enough_lessons else "unknown",
            "semantic_distinctness": "pass" if distinct_lessons else "unknown",
            "task_families_declared": "pass" if corpus_declared else "unknown",
            "non_ceiling_target_corpus": "unknown",
        },
        "blockers": sorted(set(blockers)),
        "next_run_policy": {
            "action": next_action,
            "maximum_live_calls": max(0, int(maximum_next_run_calls)) if ready else 0,
            "required_arms": ["task_only", "verified_irrelevant_sham", "verified_relevant"],
            "baseline_success_band": [0.30, 0.70],
            "primary_effect": "G_relevance=U_relevant-U_sham",
            "result_may_only_narrow_next_run": True,
            "automatic_memory_promotion": False,
            "automatic_policy_expansion": False,
        },
        "calls_executed": 0,
        "empirical_transfer_established": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    receipt = {**material, "receipt_hash": _sha(material)}
    if persist:
        store.set_setting(f"semantic_transfer_readiness_latest:{repo}", receipt)
        receipt["persistence"] = "advisory_tip_only"
    else:
        receipt["persistence"] = "not_requested"
    return receipt


__all__ = [
    "CLAIM_BOUNDARY",
    "SCHEMA",
    "VERSION",
    "assess_semantic_transfer_readiness",
]
