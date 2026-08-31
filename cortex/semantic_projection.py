"""Verified, task-bound cognitive projections of canonical Cortex memory.

Proof form and cognitive form are deliberately separate:

    canonical memory -> independent verification -> bounded lesson + proof roots

The model receives the bounded lesson.  Cortex retains and verifies the roots.
Neither representation grants execution, mutation, admission, or policy authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__
from .admitted_memory import deep_verify_admitted_memory, list_admitted_memories
from .memory_projection import evaluate_memory_eligibility

SCHEMA = "cortex-semantic-memory-projection/1.0"
VERSION = "10.0.0-alpha.14"
TRI_RANK = {"fail": 0, "unknown": 1, "pass": 2}
CLAIM_BOUNDARY = (
    "A semantic lesson is bounded public guidance reconstructed from an exact "
    "canonical admitted-memory row. It is not universal truth, hidden reasoning, "
    "execution authority, host-mutation authority, or memory-admission authority."
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _state(*states: str) -> str:
    return min(states, key=lambda item: TRI_RANK.get(item, 1)) if states else "unknown"


def _semantic_content(memory: Mapping[str, Any]) -> dict[str, Any]:
    """Return only canonical public fields useful to transient cognition."""
    evidence = dict(memory.get("evidence") or {})
    source = dict(memory.get("source") or {})
    return {
        "memory_id": str(memory.get("memory_id") or ""),
        "candidate_type": str(memory.get("candidate_type") or ""),
        "guidance": str(memory.get("summary") or "").strip(),
        "support_level": str(memory.get("support_level") or "none"),
        "claim_scope": "trajectory_bound",
        "evidence_summary": evidence,
        "prerequisites": [],
        "applicable_when": [],
        "invalid_when": [],
        "unresolved_semantics": [
            "prerequisite_completeness",
            "applicability_completeness",
            "counterevidence_completeness",
        ],
        "evidence_roots": sorted(
            {
                str(value)
                for key, value in source.items()
                if value and (key.endswith("_hash") or key.endswith("_id"))
            }
        ),
        "memory_receipt_hash": str(memory.get("receipt_hash") or ""),
    }


def _semantic_binding_state(memory: Mapping[str, Any]) -> tuple[str, list[str]]:
    material = dict(memory.get("candidate_material") or {})
    errors: list[str] = []
    if not str(memory.get("summary") or "").strip():
        errors.append("semantic_summary_missing")
    if not material:
        return "unknown", ["candidate_material_missing"]
    for field in ("candidate_id", "candidate_type", "summary", "support_level"):
        if field in material and material.get(field) != memory.get(field):
            errors.append(f"candidate_material_{field}_mismatch")
    if "summary" not in material or "candidate_type" not in material:
        errors.append("candidate_semantic_fields_missing")
    return ("fail" if errors else "pass"), errors


def _historical_memory_verified(report: Mapping[str, Any]) -> bool:
    """Verify immutable admission without confusing expiry with invalid history."""
    allowed_historical_errors = {"will_not_current"}
    blocking = {
        str(item)
        for item in report.get("errors") or ()
        if str(item) not in allowed_historical_errors
    }
    return bool(
        report.get("structural_validity") is True
        and report.get("lineage_validity") is True
        and report.get("evidence_validity") is True
        and not blocking
    )


def build_semantic_memory_projection(
    store: Any,
    repo: str,
    *,
    task: str,
    selected_memory_ids: Sequence[str],
    body_epoch_id: str,
    current_will: Mapping[str, Any] | None = None,
    max_lessons: int = 8,
) -> dict[str, Any]:
    """Resolve selected identities and independently construct active lessons."""
    canonical_rows = {
        str(row.get("memory_id") or ""): row
        for row in list_admitted_memories(store, repo, limit=10_000)
    }
    requested = [str(item) for item in selected_memory_ids if str(item)][:max_lessons]
    lessons: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    for memory_id in requested:
        memory = canonical_rows.get(memory_id)
        if memory is None:
            decisions.append(
                {
                    "memory_id": memory_id,
                    "state": "unknown",
                    "reasons": ["canonical_memory_unresolved"],
                }
            )
            continue
        deep = deep_verify_admitted_memory(store, repo, memory)
        eligibility = evaluate_memory_eligibility(
            store,
            repo,
            memory,
            live_epoch_id=body_epoch_id or None,
            current_will=current_will,
            task=task,
            # Selection policy already bounded these canonical identities.
            # Reverification must not silently impose a different budget floor.
            min_support="none",
            require_deep_lineage=True,
        )
        semantic_state, semantic_errors = _semantic_binding_state(memory)
        gates = dict(eligibility.get("gates") or {})
        proof = {
            "V_verification": (
                "pass" if _historical_memory_verified(deep) else "fail"
            ),
            "S_semantic_binding": semantic_state,
            "A_task_applicability": "pass" if gates.get("scope") is True else "fail",
            "F_freshness": (
                "pass"
                if gates.get("epoch") is True and gates.get("state") is True
                else "fail"
            ),
            "C_contradiction_clearance": (
                "pass"
                if str(eligibility.get("current_state") or "unknown") == "active"
                else "fail"
            ),
        }
        overall = _state(*proof.values())
        reasons = sorted(
            set(
                [str(item) for item in deep.get("errors") or ()]
                + [str(item) for item in eligibility.get("exclusions") or ()]
                + semantic_errors
            )
        )
        decisions.append(
            {
                "memory_id": memory_id,
                "state": overall,
                "proof": proof,
                "reasons": reasons,
            }
        )
        if overall != "pass":
            continue
        content = _semantic_content(memory)
        content_hash = _sha(content)
        lesson = {
            **content,
            "semantic_content_hash": content_hash,
            "projection_gate": proof,
            "projection_state": "pass",
            "advisory_only": True,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        }
        lesson["lesson_hash"] = _sha(lesson)
        lessons.append(lesson)

    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "kind": "semantic_memory_projection",
        "repo": repo,
        "task_hash": _sha({"repo": repo, "task": task}),
        "body_epoch_id": body_epoch_id,
        "requested_memory_ids": requested,
        "projected_memory_ids": [item["memory_id"] for item in lessons],
        "lessons": lessons,
        "decisions": decisions,
        "gate_law": "Theta_P=min(V,S,A,F,C); project iff Theta_P=pass",
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    return {**material, "receipt_hash": _sha(material)}


def verify_semantic_memory_projection(
    store: Any, repo: str, projection: Mapping[str, Any], *, task: str
) -> dict[str, Any]:
    """Rebuild from identities; caller-supplied semantic content has no authority."""
    errors: list[str] = []
    expected_hash = _sha({key: value for key, value in projection.items() if key != "receipt_hash"})
    if expected_hash != str(projection.get("receipt_hash") or ""):
        errors.append("projection_receipt_hash_invalid")
    rebuilt = build_semantic_memory_projection(
        store,
        repo,
        task=task,
        selected_memory_ids=projection.get("requested_memory_ids") or (),
        body_epoch_id=str(projection.get("body_epoch_id") or ""),
        current_will=store.get_setting(f"will_latest:{repo}", None) or None,
        max_lessons=max(1, len(projection.get("requested_memory_ids") or ())),
    )
    for field in ("task_hash", "projected_memory_ids", "lessons", "decisions"):
        if projection.get(field) != rebuilt.get(field):
            errors.append(f"{field}_recomputation_mismatch")
    return {
        "valid": not errors,
        "state": "pass" if not errors else "fail",
        "errors": sorted(set(errors)),
        "projected_count": len(rebuilt.get("lessons") or ()),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "SCHEMA",
    "VERSION",
    "build_semantic_memory_projection",
    "verify_semantic_memory_projection",
]
