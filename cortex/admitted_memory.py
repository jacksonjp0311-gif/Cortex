"""v8.6 — Will-bound admitted memory ledger.

Closes the gap after membrane admission:

    membrane.admit(retain=true)  →  immutable AdmittedMemory rows

Still:
  * never from arbitrary chat text
  * never invents facts
  * never host.mutate / auto-execute
  * exactly-once per candidate_id
  * reconstructable across sessions for next-session brief
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA = "cortex-admitted-memory/1.0"
VERSION = "8.6.0"
GLYPH = "⧉◆"
CLAIM_BOUNDARY = (
    "Admitted memories are will-bound, trajectory-derived durable lessons. "
    "They are written only after membrane admission under open ΓΞWOS gates. "
    "They do not mutate host source, execute tools, invent facts, or grant "
    "authority. durable_memory ≠ host mutation ≠ execution."
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def commit_admitted_memories(
    store: Any,
    repo: str,
    *,
    admission: Mapping[str, Any],
    will: Mapping[str, Any] | None = None,
    session: Mapping[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Persist each membrane-admitted candidate as an immutable memory row.

    No-op (and no authority) when admission.durable_write_authorized is false
    or invented_count is non-zero.
    """
    admission = dict(admission or {})
    will = dict(will or {})
    session = dict(session or {})
    invented = int(admission.get("invented_count") or 0)
    durable = bool(admission.get("durable_write_authorized"))
    will_ok = bool(admission.get("will_verified"))
    if invented != 0:
        return {
            "schema_version": SCHEMA,
            "version": VERSION,
            "kind": "admitted_memory_commit_batch",
            "repo": repo,
            "committed": [],
            "committed_count": 0,
            "skipped_count": 0,
            "status": "blocked_invented_candidates",
            "durable_write_authorized": False,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "claim_boundary": CLAIM_BOUNDARY,
        }
    if not durable or not will_ok:
        return {
            "schema_version": SCHEMA,
            "version": VERSION,
            "kind": "admitted_memory_commit_batch",
            "repo": repo,
            "committed": [],
            "committed_count": 0,
            "skipped_count": len(admission.get("admitted") or ()),
            "status": "blocked_gates_or_will",
            "durable_write_authorized": False,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "claim_boundary": CLAIM_BOUNDARY,
        }

    committed: list[dict[str, Any]] = []
    skipped = 0
    for raw in admission.get("admitted") or ():
        if not isinstance(raw, Mapping):
            skipped += 1
            continue
        if raw.get("retain") is not True:
            skipped += 1
            continue
        candidate_id = str(raw.get("candidate_id") or "").strip()
        if not candidate_id:
            skipped += 1
            continue
        ctype = str(raw.get("candidate_type") or raw.get("kind") or "unresolved_ambiguity")
        source = dict(raw.get("source") or {})
        material = {
            "schema_version": SCHEMA,
            "version": VERSION,
            "glyph": GLYPH,
            "kind": "admitted_memory",
            "repo": repo,
            "repository_id": str(
                admission.get("repository_id")
                or will.get("repository_id")
                or session.get("repository_id")
                or ""
            ),
            "session_id": str(
                admission.get("session_id")
                or session.get("session_id")
                or will.get("session_id")
                or ""
            ),
            "turn_id": int(
                admission.get("turn_id")
                or raw.get("turn_id")
                or session.get("current_turn_id")
                or 0
            ),
            "body_epoch_id": str(
                admission.get("body_epoch_id")
                or session.get("body_epoch_id")
                or will.get("body_epoch_id")
                or ""
            ),
            "candidate_id": candidate_id,
            "candidate_type": ctype,
            "kind_alias": ctype,
            "summary": str(raw.get("summary") or ""),
            "support_level": str(raw.get("support_level") or "none"),
            "evidence": dict(raw.get("evidence") or {}),
            "source": {
                "prior_frame_hash": source.get("prior_frame_hash"),
                "next_frame_hash": source.get("next_frame_hash"),
                "transition_hash": source.get("transition_hash"),
                "outcome_hash": source.get("outcome_hash"),
                "proposal_hash": source.get("proposal_hash"),
                "evaluation_hash": source.get("evaluation_hash"),
                "joint_action_hash": source.get("joint_action_hash"),
                "context_delta_hash": source.get("context_delta_hash"),
            },
            "will_id": will.get("will_id") or admission.get("will_id"),
            "will_receipt_hash": will.get("receipt_hash")
            or admission.get("will_receipt_hash"),
            "membrane_receipt_hash": admission.get("receipt_hash"),
            "admission_reason": raw.get("admission_reason"),
            "retain": True,
            "from_trajectory": True,
            "from_chat_text": False,
            "invented": False,
            "advisory_only": False,
            "policy_effect": False,
            "update_authorized": False,
            "memory_write_authorized": True,
            "durable_write_authorized": True,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "cortex_version": __version__,
        }
        event_id = "evt_" + _sha(
            {
                "kind": "admitted_memory",
                "candidate_id": candidate_id,
                "membrane": material["membrane_receipt_hash"],
            }
        )[:24]
        memory_id = "mem_" + _sha(
            {
                "repo": repo,
                "candidate_id": candidate_id,
                "membrane": material["membrane_receipt_hash"],
            }
        )[:24]
        receipt_hash = _sha({**material, "event_id": event_id, "memory_id": memory_id})
        receipt = {
            **material,
            "memory_id": memory_id,
            "event_id": event_id,
            "receipt_hash": receipt_hash,
            "created_at": time.time(),
        }
        if persist:
            try:
                result = store.append_admitted_memory(repo, receipt)
                if result.get("duplicate"):
                    skipped += 1
                    committed.append({**receipt, "duplicate": True, "inserted": False})
                else:
                    committed.append({**receipt, "duplicate": False, "inserted": True})
            except Exception as exc:
                skipped += 1
                committed.append(
                    {
                        "candidate_id": candidate_id,
                        "error": f"{type(exc).__name__}:{exc}",
                        "inserted": False,
                    }
                )
        else:
            committed.append({**receipt, "inserted": False, "persisted": False})

    inserted = [c for c in committed if c.get("inserted")]
    batch = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "admitted_memory_commit_batch",
        "repo": repo,
        "repository_id": admission.get("repository_id") or will.get("repository_id"),
        "session_id": admission.get("session_id") or session.get("session_id"),
        "body_epoch_id": admission.get("body_epoch_id") or session.get("body_epoch_id"),
        "membrane_receipt_hash": admission.get("receipt_hash"),
        "will_receipt_hash": will.get("receipt_hash") or admission.get("will_receipt_hash"),
        "committed": committed,
        "committed_count": len(inserted),
        "skipped_count": skipped,
        "status": "committed" if inserted else "empty_or_duplicate",
        "durable_write_authorized": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "policy_effect": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
        "created_at": time.time(),
    }
    batch["receipt_hash"] = _sha(
        {
            "membrane": batch["membrane_receipt_hash"],
            "memory_ids": [c.get("memory_id") for c in inserted],
            "count": batch["committed_count"],
        }
    )
    if persist:
        store.set_setting(f"admitted_memory_latest:{repo}", batch)
    return batch


def list_admitted_memories(
    store: Any,
    repo: str,
    *,
    session_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    if hasattr(store, "list_admitted_memories"):
        return store.list_admitted_memories(repo, session_id=session_id, limit=limit)
    return []


def verify_admitted_memories(
    store: Any,
    repo: str,
    *,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Structural verification of ledger rows (hashes present, no host bits)."""
    rows = list_admitted_memories(store, repo, session_id=session_id, limit=10_000)
    errors: list[str] = []
    for index, row in enumerate(rows):
        if not row.get("receipt_hash") or len(str(row.get("receipt_hash"))) != 64:
            errors.append(f"row_{index}_bad_receipt_hash")
        if not row.get("candidate_id"):
            errors.append(f"row_{index}_missing_candidate_id")
        if row.get("host_mutate_authorized"):
            errors.append(f"row_{index}_host_mutate_true")
        if row.get("execution_authorized"):
            errors.append(f"row_{index}_execution_true")
        if row.get("from_chat_text"):
            errors.append(f"row_{index}_from_chat_text")
        if row.get("invented"):
            errors.append(f"row_{index}_invented")
        if not row.get("membrane_receipt_hash"):
            errors.append(f"row_{index}_missing_membrane")
        if not row.get("will_receipt_hash"):
            errors.append(f"row_{index}_missing_will")
    return {
        "schema_version": "cortex-admitted-memory-verify/1.0",
        "version": VERSION,
        "repo": repo,
        "session_id": session_id,
        "row_count": len(rows),
        "valid": not errors,
        "errors": errors,
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "policy_effect": False,
    }


def admitted_memory_status(store: Any, repo: str) -> dict[str, Any]:
    latest = store.get_setting(f"admitted_memory_latest:{repo}", None) or {}
    rows = list_admitted_memories(store, repo, limit=500)
    by_type: dict[str, int] = {}
    for row in rows:
        t = str(row.get("candidate_type") or "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "schema_version": "cortex-admitted-memory-status/1.0",
        "version": VERSION,
        "repo": repo,
        "total": len(rows),
        "by_type": by_type,
        "latest_batch_hash": latest.get("receipt_hash"),
        "latest_committed_count": latest.get("committed_count"),
        "claim_boundary": CLAIM_BOUNDARY,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "advisory_only": True,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "GLYPH",
    "SCHEMA",
    "VERSION",
    "admitted_memory_status",
    "commit_admitted_memories",
    "list_admitted_memories",
    "verify_admitted_memories",
]
