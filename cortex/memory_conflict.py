"""v8.7 — Memory challenge and supersession (history preserved)."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from typing import Any

from . import __version__
from .memory_state import issue_memory_state

SCHEMA_CHALLENGE = "cortex-memory-challenge/1.0"
SCHEMA_SUPERSEDE = "cortex-memory-supersession/1.0"
VERSION = "8.7.0"
CLAIM_BOUNDARY = (
    "Challenges and supersessions never delete admitted memories. They change "
    "applicability state only. Current will cannot erase historically valid "
    "counterevidence. Review-only unless evidence + will + authorization present."
)

CONTRADICTION_KINDS = frozenset(
    {
        "direct_disconfirmation",
        "scope_narrowing",
        "condition_changed",
        "epoch_obsolete",
        "procedure_regression",
        "newer_stronger_evidence",
        "unresolved_conflict",
    }
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def challenge_memory(
    store: Any,
    repo: str,
    *,
    challenged_memory_id: str,
    challenger_candidate_id: str,
    contradiction_kind: str = "unresolved_conflict",
    evidence_hashes: list[str] | None = None,
    scope_comparison: str = "",
    epoch_comparison: str = "",
    support_comparison: str = "",
    recommended_state: str = "contested",
    will_receipt_hash: str | None = None,
    auto_contest: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    kind = str(contradiction_kind or "unresolved_conflict")
    if kind not in CONTRADICTION_KINDS:
        kind = "unresolved_conflict"
    material = {
        "schema_version": SCHEMA_CHALLENGE,
        "version": VERSION,
        "kind": "memory_challenge",
        "repo": repo,
        "challenged_memory_id": str(challenged_memory_id),
        "challenger_candidate_id": str(challenger_candidate_id),
        "contradiction_kind": kind,
        "evidence_hashes": [str(h) for h in (evidence_hashes or ()) if str(h)],
        "scope_comparison": str(scope_comparison or ""),
        "epoch_comparison": str(epoch_comparison or ""),
        "support_comparison": str(support_comparison or ""),
        "recommended_state": recommended_state,
        "will_receipt_hash": will_receipt_hash,
        "auto_revoke": False,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    event_id = "evt_" + _sha(
        {
            "kind": "memory_challenge",
            "challenged": material["challenged_memory_id"],
            "challenger": material["challenger_candidate_id"],
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
        store.append_memory_challenge_receipt(repo, receipt)
        if auto_contest:
            issue_memory_state(
                store,
                repo,
                memory_id=str(challenged_memory_id),
                state="contested",
                reason=f"challenge:{kind}",
                evidence_hashes=list(receipt["evidence_hashes"]) + [receipt_hash],
                challenger_memory_ids=[],
                will_receipt_hash=will_receipt_hash,
                persist=True,
            )
    return receipt


def supersede_memory(
    store: Any,
    repo: str,
    *,
    superseded_memory_id: str,
    replacement_memory_id: str,
    basis: str = "newer_stronger_evidence",
    comparison_receipt_hash: str | None = None,
    effective_epoch_id: str | None = None,
    principal_will_hash: str | None = None,
    authorized: bool = False,
    persist: bool = True,
) -> dict[str, Any]:
    """Supersession preserves lineage; requires authorization flag for state change."""
    material = {
        "schema_version": SCHEMA_SUPERSEDE,
        "version": VERSION,
        "kind": "memory_supersession",
        "repo": repo,
        "superseded_memory_id": str(superseded_memory_id),
        "replacement_memory_id": str(replacement_memory_id),
        "basis": str(basis or "newer_stronger_evidence"),
        "comparison_receipt_hash": comparison_receipt_hash,
        "effective_epoch_id": effective_epoch_id,
        "principal_will_hash": principal_will_hash,
        "authorized": bool(authorized),
        "advisory_only": not bool(authorized),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    event_id = "evt_" + _sha(
        {
            "kind": "memory_supersession",
            "old": material["superseded_memory_id"],
            "new": material["replacement_memory_id"],
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
        store.append_memory_supersession_receipt(repo, receipt)
        if authorized:
            issue_memory_state(
                store,
                repo,
                memory_id=str(superseded_memory_id),
                state="superseded",
                reason=f"superseded_by:{replacement_memory_id}",
                evidence_hashes=[receipt_hash, str(comparison_receipt_hash or "")],
                replacement_memory_id=str(replacement_memory_id),
                effective_epoch_id=effective_epoch_id,
                will_receipt_hash=principal_will_hash,
                persist=True,
            )
    return receipt


__all__ = [
    "CLAIM_BOUNDARY",
    "CONTRADICTION_KINDS",
    "VERSION",
    "challenge_memory",
    "supersede_memory",
]
