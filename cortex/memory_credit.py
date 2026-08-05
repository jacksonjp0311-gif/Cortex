"""v8.7 — Memory use binding and append-only credit (utility ≠ truth)."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA_USE = "cortex-memory-use/1.0"
SCHEMA_CREDIT = "cortex-memory-credit/1.0"
VERSION = "8.7.0"
CLAIM_BOUNDARY = (
    "Memory-use and credit receipts bind projection → citation → outcome. "
    "They never rewrite admitted memory truth, authorize host mutation, or "
    "treat retrieval frequency as correctness. available ≠ cited ≠ useful."
)

CREDIT_STATUS = frozenset(
    {"unmeasured", "temporally_associated", "outcome_bound", "comparison_supported"}
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def record_memory_use(
    store: Any,
    repo: str,
    *,
    projection: Mapping[str, Any],
    proposal: Mapping[str, Any] | None = None,
    evaluation: Mapping[str, Any] | None = None,
    action: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
    memory_ids_cited: Sequence[str] | None = None,
    operator_corrections: int = 0,
    latency_ms: float | None = None,
    token_cost: float | None = None,
    rollback_count: int = 0,
    persist: bool = True,
) -> dict[str, Any]:
    proposal = proposal or {}
    evaluation = evaluation or {}
    action = action or {}
    outcome = outcome or {}
    available = list(projection.get("selected_memory_ids") or ())
    cited = [str(x) for x in (memory_ids_cited or ()) if str(x)]
    # also pull citations from proposal if present
    for key in ("evidence_citations", "memory_citations"):
        for item in proposal.get(key) or ():
            s = str(item)
            if s.startswith("mem_") and s not in cited:
                cited.append(s)
    success = outcome.get("success")
    witnessed = bool(outcome.get("witnessed"))
    material = {
        "schema_version": SCHEMA_USE,
        "version": VERSION,
        "kind": "memory_use",
        "repo": repo,
        "projection_id": projection.get("projection_id"),
        "memory_projection_hash": projection.get("receipt_hash"),
        "memory_ids_available": available,
        "memory_ids_cited_by_proposal": cited,
        "proposal_hash": proposal.get("receipt_hash"),
        "evaluation_hash": evaluation.get("receipt_hash"),
        "action_hash": action.get("receipt_hash"),
        "outcome_hash": outcome.get("receipt_hash"),
        "success": success,
        "witnessed": witnessed,
        "task_family": str(proposal.get("interpreted_objective") or "")[:120],
        "operator_corrections": int(operator_corrections),
        "latency_ms": latency_ms,
        "token_cost": token_cost,
        "rollback_count": int(rollback_count),
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    event_id = "evt_" + _sha(
        {
            "kind": "memory_use",
            "projection": material["projection_id"],
            "outcome": material["outcome_hash"],
        }
    )[:24]
    receipt_hash = _sha({**material, "event_id": event_id})
    receipt = {
        **material,
        "event_id": event_id,
        "receipt_hash": receipt_hash,
        "created_at": time.time(),
    }
    if persist:
        store.append_memory_use_receipt(repo, receipt)
    return receipt


def issue_memory_credit(
    store: Any,
    repo: str,
    *,
    memory_id: str,
    use_receipt: Mapping[str, Any],
    baseline_success: bool | None = None,
    weight: float = 1.0,
    persist: bool = True,
) -> dict[str, Any]:
    """Append-only credit. comparison_supported only with matched baseline."""
    use_receipt = dict(use_receipt or {})
    cited = set(use_receipt.get("memory_ids_cited_by_proposal") or ())
    available = set(use_receipt.get("memory_ids_available") or ())
    used = memory_id in cited
    available_only = memory_id in available and not used
    witnessed = bool(use_receipt.get("witnessed"))
    success = use_receipt.get("success")

    if not witnessed or success is None:
        status = "unmeasured"
        delta = None
    elif used and baseline_success is not None:
        status = "comparison_supported"
        delta = (1.0 if success else 0.0) - (1.0 if baseline_success else 0.0)
    elif used:
        status = "outcome_bound"
        delta = 1.0 if success else -1.0
    elif available_only:
        status = "temporally_associated"
        delta = None
    else:
        status = "unmeasured"
        delta = None

    material = {
        "schema_version": SCHEMA_CREDIT,
        "version": VERSION,
        "kind": "memory_credit",
        "repo": repo,
        "memory_id": memory_id,
        "use_receipt_hash": use_receipt.get("receipt_hash"),
        "credit_status": status,
        "used": used,
        "available": memory_id in available,
        "weight": float(weight),
        "delta_utility": delta,
        "weighted_credit": (float(weight) * delta) if delta is not None else None,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    event_id = "evt_" + _sha(
        {
            "kind": "memory_credit",
            "memory_id": memory_id,
            "use": material["use_receipt_hash"],
            "status": status,
        }
    )[:24]
    receipt_hash = _sha({**material, "event_id": event_id})
    receipt = {
        **material,
        "event_id": event_id,
        "receipt_hash": receipt_hash,
        "created_at": time.time(),
    }
    if persist:
        store.append_memory_credit_receipt(repo, receipt)
    return receipt


def credit_projection_memories(
    store: Any,
    repo: str,
    *,
    use_receipt: Mapping[str, Any],
    persist: bool = True,
) -> list[dict[str, Any]]:
    """Issue credit rows for all available and cited memories on a use receipt."""
    ids = set(use_receipt.get("memory_ids_available") or ()) | set(
        use_receipt.get("memory_ids_cited_by_proposal") or ()
    )
    out: list[dict[str, Any]] = []
    for mid in sorted(ids):
        out.append(
            issue_memory_credit(
                store,
                repo,
                memory_id=str(mid),
                use_receipt=use_receipt,
                persist=persist,
            )
        )
    return out


__all__ = [
    "CLAIM_BOUNDARY",
    "CREDIT_STATUS",
    "VERSION",
    "credit_projection_memories",
    "issue_memory_credit",
    "record_memory_use",
]
