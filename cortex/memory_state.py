"""v8.7 — Append-only memory state overlays (applicability ≠ existence)."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA = "cortex-memory-state/1.0"
VERSION = "8.7.0"
GLYPH = "⧉◇"
CLAIM_BOUNDARY = (
    "Memory state overlays never mutate admitted memory rows. Immutability of "
    "history is preserved; only current applicability changes. State tips do not "
    "authorize host mutation or execution."
)

MEMORY_STATES = frozenset(
    {
        "active",
        "contested",
        "superseded",
        "revoked",
        "expired",
        "epoch_stale",
        "quarantined",
    }
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def issue_memory_state(
    store: Any,
    repo: str,
    *,
    memory_id: str,
    state: str,
    reason: str = "",
    evidence_hashes: Sequence[str] | None = None,
    challenger_memory_ids: Sequence[str] | None = None,
    replacement_memory_id: str | None = None,
    effective_epoch_id: str | None = None,
    will_receipt_hash: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    state = str(state or "").strip()
    if state not in MEMORY_STATES:
        raise ValueError(f"unknown memory state: {state}")
    memory_id = str(memory_id or "").strip()
    if not memory_id:
        raise ValueError("memory_id required")
    prior_list = store.list_memory_state_receipts(repo, memory_id)
    prior = prior_list[-1] if prior_list else None
    seq = int((prior or {}).get("state_sequence") or 0) + 1
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "memory_state",
        "repo": repo,
        "memory_id": memory_id,
        "state": state,
        "state_sequence": seq,
        "prior_state_receipt_hash": (prior or {}).get("receipt_hash"),
        "reason": str(reason or ""),
        "evidence_hashes": [str(h) for h in (evidence_hashes or ()) if str(h)],
        "challenger_memory_ids": [
            str(h) for h in (challenger_memory_ids or ()) if str(h)
        ],
        "replacement_memory_id": replacement_memory_id,
        "effective_epoch_id": effective_epoch_id,
        "will_receipt_hash": will_receipt_hash,
        "advisory_only": True,
        "policy_effect": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    event_id = "evt_" + _sha(
        {"kind": "memory_state", "memory_id": memory_id, "seq": seq, "state": state}
    )[:24]
    receipt_hash = _sha({**material, "event_id": event_id})
    receipt = {
        **material,
        "event_id": event_id,
        "receipt_hash": receipt_hash,
        "created_at": time.time(),
    }
    if persist:
        store.append_memory_state_receipt(repo, receipt)
    return receipt


def ensure_active_state(
    store: Any, repo: str, memory: Mapping[str, Any], *, persist: bool = True
) -> dict[str, Any]:
    """Seed active state for a newly admitted memory if none exists."""
    memory_id = str(memory.get("memory_id") or "")
    existing = store.list_memory_state_receipts(repo, memory_id)
    if existing:
        return existing[-1]
    return issue_memory_state(
        store,
        repo,
        memory_id=memory_id,
        state="active",
        reason="initial_admission",
        evidence_hashes=[
            str(memory.get("receipt_hash") or ""),
            str(memory.get("membrane_receipt_hash") or ""),
        ],
        effective_epoch_id=str(memory.get("body_epoch_id") or "") or None,
        will_receipt_hash=str(memory.get("will_receipt_hash") or "") or None,
        persist=persist,
    )


def current_memory_state(
    store: Any, repo: str, memory_id: str
) -> dict[str, Any]:
    history = store.list_memory_state_receipts(repo, str(memory_id))
    if not history:
        return {
            "memory_id": memory_id,
            "state": "active",
            "state_sequence": 0,
            "implicit_default": True,
            "receipt_hash": None,
        }
    tip = dict(history[-1])
    tip["implicit_default"] = False
    tip["history_len"] = len(history)
    return tip


def mark_epoch_stale_if_needed(
    store: Any,
    repo: str,
    memory: Mapping[str, Any],
    *,
    live_epoch_id: str,
    persist: bool = True,
) -> dict[str, Any] | None:
    """If memory epoch differs from live, append epoch_stale when currently active."""
    mem_epoch = str(memory.get("body_epoch_id") or "")
    live = str(live_epoch_id or "")
    if not mem_epoch or not live or mem_epoch == live:
        return None
    tip = current_memory_state(store, repo, str(memory.get("memory_id") or ""))
    if tip.get("state") in {"superseded", "revoked", "epoch_stale"}:
        return tip
    return issue_memory_state(
        store,
        repo,
        memory_id=str(memory.get("memory_id") or ""),
        state="epoch_stale",
        reason="body_epoch_mismatch_vs_live",
        evidence_hashes=[mem_epoch, live],
        effective_epoch_id=live,
        persist=persist,
    )


__all__ = [
    "CLAIM_BOUNDARY",
    "MEMORY_STATES",
    "SCHEMA",
    "VERSION",
    "current_memory_state",
    "ensure_active_state",
    "issue_memory_state",
    "mark_epoch_stale_if_needed",
]
