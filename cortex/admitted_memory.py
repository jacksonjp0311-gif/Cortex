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
from collections.abc import Mapping
from typing import Any

from . import __version__
from .provenance import verify_candidate_provenance

SCHEMA = "cortex-admitted-memory/1.0"
VERSION = "8.9.3"
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
    or any canonical provenance/invention counter is non-zero.

    Prefer reloading the membrane admission from the immutable ledger by hash
    when present — do not trust a fabricated in-memory mapping alone.
    """
    admission = dict(admission or {})
    will = dict(will or {})
    session = dict(session or {})
    # Independent re-load of membrane receipt when hash is known.
    membrane_hash = str(admission.get("receipt_hash") or "")
    if membrane_hash and hasattr(store, "get_membrane_admission_by_hash"):
        canonical = store.get_membrane_admission_by_hash(repo, membrane_hash)
        if canonical is None:
            return {
                "schema_version": SCHEMA,
                "version": VERSION,
                "kind": "admitted_memory_commit_batch",
                "repo": repo,
                "committed": [],
                "committed_count": 0,
                "skipped_count": 0,
                "status": "blocked_membrane_not_in_ledger",
                "durable_write_authorized": False,
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "claim_boundary": CLAIM_BOUNDARY,
            }
        admission = dict(canonical)
    invented = int(admission.get("invented_count") or 0)
    provenance_fail = int(admission.get("provenance_fail_count") or 0)
    provenance_unknown = int(admission.get("provenance_unknown_count") or 0)
    provenance_legacy = int(admission.get("provenance_legacy_partial_count") or 0)
    noncanonical = int(admission.get("noncanonical_candidate_count") or 0)
    durable = bool(admission.get("durable_write_authorized"))
    will_ok = bool(admission.get("will_verified"))
    if any(value != 0 for value in (invented, provenance_fail, provenance_unknown, provenance_legacy, noncanonical)):
        return {
            "schema_version": SCHEMA,
            "version": VERSION,
            "kind": "admitted_memory_commit_batch",
            "repo": repo,
            "committed": [],
            "committed_count": 0,
            "skipped_count": 0,
            "status": "blocked_unresolved_or_noncanonical_candidates",
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
        candidate_material = {
            key: raw.get(key)
            for key in (
                "candidate_type", "kind", "summary", "support_level", "source",
                "evidence", "session_id", "turn_id", "repo", "index", "candidate_id",
            )
            if key in raw
        }
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
            "candidate_batch_hash": raw.get("batch_receipt_hash")
            or admission.get("candidate_batch_hash"),
            "candidate_material": candidate_material,
            "candidate_type": ctype,
            "kind_alias": ctype,
            "summary": str(raw.get("summary") or ""),
            "support_level": str(raw.get("support_level") or "none"),
            "evidence": dict(raw.get("evidence") or {}),
            "source": {
                "prior_frame_hash": source.get("prior_frame_hash"),
                "next_frame_hash": source.get("next_frame_hash"),
                "transition_hash": source.get("transition_hash"),
                "measurement_cohort_id": source.get("measurement_cohort_id"),
                "coordinate_schema_digest": source.get("coordinate_schema_digest"),
                "outcome_hash": source.get("outcome_hash"),
                "outcome_id": source.get("outcome_id"),
                "activation_id": source.get("activation_id"),
                "witness_result_hash": source.get("witness_result_hash"),
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
                    state_error = None
                    try:
                        from .memory_state import ensure_active_state

                        ensure_active_state(store, repo, receipt, persist=True)
                    except Exception as exc:
                        state_error = f"{type(exc).__name__}:{exc}"
                    committed.append({
                        **receipt,
                        "duplicate": False,
                        "inserted": True,
                        **({"state_error": state_error} if state_error else {}),
                    })
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
        if any(c.get("error") or c.get("state_error") for c in committed):
            batch["status"] = "partial" if inserted else "failed"
            batch["canonical_persistence"] = "partial" if inserted else "failed"
        else:
            batch["canonical_persistence"] = "committed" if inserted else "duplicate"
        # A mutable tip is a compatibility projection only; it must never
        # turn a canonical append failure into an apparent success.
        if batch["canonical_persistence"] in {"committed", "duplicate"}:
            store.set_setting(f"admitted_memory_latest:{repo}", batch)
    else:
        batch["canonical_persistence"] = "not_requested"
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


def _recompute_memory_receipt_hash(row: Mapping[str, Any]) -> str:
    material = {
        k: row.get(k)
        for k in (
            "schema_version",
            "version",
            "glyph",
            "kind",
            "repo",
            "repository_id",
            "session_id",
            "turn_id",
            "body_epoch_id",
            "candidate_id",
            "candidate_batch_hash",
            "candidate_material",
            "candidate_type",
            "kind_alias",
            "summary",
            "support_level",
            "evidence",
            "source",
            "will_id",
            "will_receipt_hash",
            "membrane_receipt_hash",
            "admission_reason",
            "retain",
            "from_trajectory",
            "from_chat_text",
            "invented",
            "advisory_only",
            "policy_effect",
            "update_authorized",
            "memory_write_authorized",
            "durable_write_authorized",
            "host_mutate_authorized",
            "execution_authorized",
            "claim_boundary",
            "cortex_version",
        )
    }
    return _sha(
        {
            **material,
            "event_id": row.get("event_id"),
            "memory_id": row.get("memory_id"),
        }
    )


def deep_verify_admitted_memory(
    store: Any, repo: str, memory: Mapping[str, Any]
) -> dict[str, Any]:
    """Independently re-check hash, membrane ledger presence, will presence, flags."""
    errors: list[str] = []
    structural = True
    lineage = True
    evidence = True
    will_ok = True

    if not memory.get("receipt_hash") or len(str(memory.get("receipt_hash"))) != 64:
        structural = False
        errors.append("bad_receipt_hash")
    if not memory.get("candidate_id"):
        structural = False
        errors.append("missing_candidate_id")
    if memory.get("host_mutate_authorized") or memory.get("execution_authorized"):
        structural = False
        errors.append("forbidden_authority_bits")
    if memory.get("from_chat_text") or memory.get("invented"):
        evidence = False
        errors.append("chat_or_invented_origin")

    expected = _recompute_memory_receipt_hash(memory)
    if str(memory.get("receipt_hash") or "") != expected:
        structural = False
        errors.append("receipt_hash_recompute_mismatch")

    membrane_hash = str(memory.get("membrane_receipt_hash") or "")
    membrane = None
    if not membrane_hash:
        lineage = False
        errors.append("missing_membrane")
    elif hasattr(store, "get_membrane_admission_by_hash"):
        membrane = store.get_membrane_admission_by_hash(repo, membrane_hash)
        if membrane is None:
            lineage = False
            errors.append("membrane_not_in_ledger")
        else:
            if not membrane.get("durable_write_authorized"):
                lineage = False
                errors.append("membrane_not_durable")
            if int(membrane.get("invented_count") or 0) != 0:
                lineage = False
                errors.append("membrane_invented_nonzero")
            admitted_ids = {
                str(a.get("candidate_id"))
                for a in (membrane.get("admitted") or ())
                if isinstance(a, Mapping)
            }
            if str(memory.get("candidate_id")) not in admitted_ids:
                lineage = False
                errors.append("candidate_not_in_membrane_admitted")

    will_hash = str(memory.get("will_receipt_hash") or "")
    will_row = None
    if not will_hash:
        will_ok = False
        errors.append("missing_will")
    elif hasattr(store, "get_will_receipt_by_hash"):
        will_row = store.get_will_receipt_by_hash(repo, will_hash)
        if will_row is None:
            will_ok = False
            errors.append("will_not_in_ledger")
        else:
            if will_row.get("host_mutate_authorized") or will_row.get(
                "execution_authorized"
            ):
                will_ok = False
                errors.append("will_forbidden_authority")
            try:
                now = time.time()
                if not (float(will_row.get("not_before") or 0) <= now <= float(will_row.get("not_after") or 0)):
                    will_ok = False
                    errors.append("will_not_current")
            except (TypeError, ValueError, OverflowError):
                will_ok = False
                errors.append("will_time_invalid")
            if membrane is not None and membrane.get("will_verified") is not True:
                will_ok = False
                errors.append("membrane_will_not_verified")
            try:
                from .will import verify_will

                structural_will = verify_will(store, repo, will_row, secret=None)
                structural_checks = dict(structural_will.get("checks") or {})
                # The HMAC secret is intentionally not persisted.  The
                # membrane's immutable ``will_verified`` records that it was
                # checked at admission; all non-secret structural checks must
                # still pass now.
                structural_checks.pop("signature", None)
                structural_checks.pop("signature_deferred", None)
                if not all(structural_checks.values()):
                    will_ok = False
                    errors.append("will_structural_verification_failed")
            except Exception:
                will_ok = False
                errors.append("will_verifier_unavailable")

    provenance = verify_candidate_provenance(store, repo, memory, membrane=membrane)
    if provenance.get("lineage_state") != "pass":
        lineage = False
        errors.extend(str(e) for e in provenance.get("errors") or ())

    # Applicability tip (not mutation of row)
    try:
        from .memory_state import current_memory_state

        tip = current_memory_state(store, repo, str(memory.get("memory_id") or ""))
        current_applicability = str(tip.get("state") or "active")
    except Exception:
        current_applicability = "unknown"

    return {
        "memory_id": memory.get("memory_id"),
        "structural_validity": structural,
        "lineage_validity": lineage,
        "evidence_validity": evidence,
        "will_validity": will_ok,
        "lineage_state": provenance.get("lineage_state"),
        "canonical_lineage_valid": provenance.get("canonical_lineage_valid", False),
        "provenance": provenance,
        "current_applicability": current_applicability,
        "errors": errors,
        "valid": structural and lineage and evidence and will_ok,
    }


def verify_admitted_memories(
    store: Any,
    repo: str,
    *,
    session_id: str | None = None,
    deep: bool = False,
) -> dict[str, Any]:
    """Structural (and optional deep) verification of ledger rows."""
    rows = list_admitted_memories(store, repo, session_id=session_id, limit=10_000)
    errors: list[str] = []
    deep_reports: list[dict[str, Any]] = []
    structural_ok = True
    lineage_ok = True
    evidence_ok = True
    will_ok = True
    for index, row in enumerate(rows):
        if not row.get("receipt_hash") or len(str(row.get("receipt_hash"))) != 64:
            errors.append(f"row_{index}_bad_receipt_hash")
            structural_ok = False
        if not row.get("candidate_id"):
            errors.append(f"row_{index}_missing_candidate_id")
            structural_ok = False
        if row.get("host_mutate_authorized"):
            errors.append(f"row_{index}_host_mutate_true")
            structural_ok = False
        if row.get("execution_authorized"):
            errors.append(f"row_{index}_execution_true")
            structural_ok = False
        if row.get("from_chat_text"):
            errors.append(f"row_{index}_from_chat_text")
            evidence_ok = False
        if row.get("invented"):
            errors.append(f"row_{index}_invented")
            evidence_ok = False
        if not row.get("membrane_receipt_hash"):
            errors.append(f"row_{index}_missing_membrane")
            lineage_ok = False
        if not row.get("will_receipt_hash"):
            errors.append(f"row_{index}_missing_will")
            will_ok = False
        if deep:
            report = deep_verify_admitted_memory(store, repo, row)
            deep_reports.append(report)
            if not report.get("structural_validity"):
                structural_ok = False
            if not report.get("lineage_validity"):
                lineage_ok = False
            if not report.get("evidence_validity"):
                evidence_ok = False
            if not report.get("will_validity"):
                will_ok = False
            for err in report.get("errors") or ():
                errors.append(f"row_{index}_{err}")
    return {
        "schema_version": "cortex-admitted-memory-verify/1.1",
        "version": VERSION,
        "repo": repo,
        "session_id": session_id,
        "row_count": len(rows),
        "deep": deep,
        "structural_validity": structural_ok,
        "lineage_validity": lineage_ok,
        "evidence_validity": evidence_ok,
        "will_validity": will_ok,
        "valid": structural_ok and lineage_ok and evidence_ok and will_ok,
        "errors": errors,
        "deep_reports": deep_reports if deep else [],
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
    "deep_verify_admitted_memory",
    "list_admitted_memories",
    "verify_admitted_memories",
]
