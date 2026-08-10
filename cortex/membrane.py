"""v8.5 — Will-bound unified distillation membrane.

Single admission surface:

    candidates + authenticated will + ΓΞWOS gates → admission receipt

The membrane:
  * never invents candidates (sources only from trajectory extraction)
  * never mutates host source
  * never auto-executes
  * may mark retain=true only when will admits AND gates open AND
    candidate support is sufficient for the type

Direction ranks; evidence decides what is true.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__
from .provenance import derive_gate_state
from .will import SUPPORT_ORDER, verify_will

SCHEMA = "cortex-distillation-membrane/1.0"
VERSION = "8.9.3"
GLYPH = "⧉⚖"
CLAIM_BOUNDARY = (
    "The unified distillation membrane admits trajectory-derived candidates "
    "only under authenticated will direction and open constitutional gates. "
    "It does not invent facts, alter evidence digests, authorize host mutation, "
    "or execute tools. admitted ≠ executed."
)

# Outcome-linked types require at least medium support (outcome_bound+).
OUTCOME_LINKED_TYPES = frozenset(
    {
        "verified_fact",
        "successful_procedure",
        "failed_hypothesis",
        "counterevidence",
        "useful_route",
    }
)
# Structural types may admit at low support when will directs.
STRUCTURAL_TYPES = frozenset(
    {
        "persistent_constraint",
        "regime_warning",
        "unresolved_ambiguity",
    }
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


def _gate_product(
    *,
    constitutional_gate: bool,
    epoch_compatible: bool,
    witness_present: bool,
    outcome_closed: bool,
    stable_regime: bool,
) -> dict[str, Any]:
    gamma = 1 if constitutional_gate else 0
    xi = 1 if epoch_compatible else 0
    w = 1 if witness_present else 0
    o = 1 if outcome_closed else 0
    s = 1 if stable_regime else 0
    product = gamma * xi * w * o * s
    return {
        "constitutional_admissibility": gamma,
        "epoch_cohort_compatibility": xi,
        "witness": w,
        "outcome_closure": o,
        "stability": s,
        "product": product,
        "open": product == 1,
    }


def _collect_candidates(
    candidates: Sequence[Mapping[str, Any]] | None,
    batches: Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in candidates or ():
        if not isinstance(raw, Mapping):
            continue
        item = dict(raw)
        cid = str(item.get("candidate_id") or _sha(item)[:20])
        item["candidate_id"] = cid
        if cid in seen:
            continue
        seen.add(cid)
        out.append(item)
    for batch in batches or ():
        if not isinstance(batch, Mapping):
            continue
        if batch.get("trajectory_verified") is False:
            continue
        for raw in batch.get("candidates") or ():
            if not isinstance(raw, Mapping):
                continue
            item = dict(raw)
            cid = str(item.get("candidate_id") or _sha(item)[:20])
            item["candidate_id"] = cid
            item.setdefault(
                "batch_receipt_hash", batch.get("receipt_hash")
            )
            if cid in seen:
                continue
            seen.add(cid)
            out.append(item)
    return out


def _will_directives(will: Mapping[str, Any]) -> dict[str, Any]:
    forbid_types: set[str] = set()
    admit_types: set[str] = set()
    prioritize_types: set[str] = set()
    deprioritize_types: set[str] = set()
    admit_ids: set[str] = set()
    max_retain: int | None = None
    min_support: str | None = None
    for clause in will.get("clauses") or ():
        if not isinstance(clause, Mapping):
            continue
        kind = str(clause.get("kind") or "")
        types = {str(t) for t in (clause.get("candidate_types") or ())}
        ids = {str(i) for i in (clause.get("candidate_ids") or ())}
        if kind == "forbid_type":
            forbid_types |= types
        elif kind == "admit_type":
            admit_types |= types
        elif kind == "prioritize_type":
            prioritize_types |= types
            admit_types |= types  # prioritize implies eligible for admit
        elif kind == "deprioritize_type":
            deprioritize_types |= types
        elif kind == "admit_candidate":
            admit_ids |= ids
        elif kind == "cap_retain":
            try:
                cap = int(clause.get("max_retain"))
                max_retain = cap if max_retain is None else min(max_retain, cap)
            except (TypeError, ValueError):
                pass
        elif kind == "prefer_support_min":
            ms = str(clause.get("min_support") or "").lower()
            if ms in SUPPORT_ORDER:
                if min_support is None or SUPPORT_ORDER[ms] > SUPPORT_ORDER.get(
                    min_support, 0
                ):
                    min_support = ms
    return {
        "forbid_types": forbid_types,
        "admit_types": admit_types,
        "prioritize_types": prioritize_types,
        "deprioritize_types": deprioritize_types,
        "admit_ids": admit_ids,
        "max_retain": max_retain,
        "min_support": min_support or "low",
    }


def apply_will_bound_membrane(
    store: Any,
    repo: str,
    *,
    will: Mapping[str, Any],
    will_secret: str,
    candidates: Sequence[Mapping[str, Any]] | None = None,
    batches: Sequence[Mapping[str, Any]] | None = None,
    constitutional_gate: bool = False,
    epoch_compatible: bool = False,
    witness_present: bool = False,
    outcome_closed: bool = False,
    stable_regime: bool = False,
    witness: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
    gate_evidence: Mapping[str, Any] | None = None,
    caller_constraints: Mapping[str, Any] | None = None,
    session_id: str | None = None,
    body_epoch_id: str | None = None,
    turn_id: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Admit distillation candidates under authenticated will + open gates.

    Never invents candidates. Never authorizes host mutation or execution.
    """
    verification = verify_will(
        store,
        repo,
        will,
        secret=will_secret,
        require_session_id=session_id,
        require_body_epoch_id=body_epoch_id,
    )
    pool = _collect_candidates(candidates, batches)
    pool_types = {
        str(item.get("candidate_type") or item.get("kind") or "")
        for item in pool
        if isinstance(item, Mapping)
    }
    derived_evidence = dict(gate_evidence or {})
    if len(pool_types) == 1:
        derived_evidence.setdefault("candidate_type", next(iter(pool_types)))
    derived = derive_gate_state(
        store,
        repo,
        will=will,
        will_secret=will_secret,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        constitutional_gate=constitutional_gate,
        epoch_compatible=epoch_compatible,
        witness_present=witness_present,
        outcome_closed=outcome_closed,
        stable_regime=stable_regime,
        witness=witness,
        outcome=outcome,
        gate_evidence=derived_evidence,
        caller_constraints=caller_constraints,
    )
    # Keep the historical numeric projection for callers, but derive it only
    # from canonical gate planes.  A caller True is never evidence.
    gates = {
        "constitutional_admissibility": int(derived["constitutional"]["state"] == "pass"),
        "epoch_cohort_compatibility": int(derived["epoch_cohort"]["state"] == "pass"),
        "witness": int(derived["witness"]["state"] == "pass"),
        "outcome_closure": int(derived["outcome"]["state"] == "pass"),
        "stability": int(derived["stability"]["state"] == "pass"),
        "planes": {k: dict(v) for k, v in derived.items() if k in {"constitutional", "epoch_cohort", "witness", "outcome", "stability", "will"}},
        "overall": derived.get("overall"),
        "product": 1 if derived.get("overall") == "pass" else 0,
        "open": derived.get("overall") == "pass",
    }
    directives = _will_directives(will)
    scopes = set(str(s) for s in (will.get("scopes") or ()))
    has_admit = "will.admit" in scopes and verification.get("verified") is True

    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    # Provenance accounting is derived from the supplied candidate pool.  The
    # old ``invented_count = 0`` invariant hid unresolved/naked candidates.
    provenance_pass_count = 0
    provenance_fail_count = 0
    provenance_unknown_count = 0
    provenance_legacy_partial_count = 0
    noncanonical_candidate_count = 0

    # Sort: prioritize directed types first, then higher support.
    def sort_key(c: Mapping[str, Any]) -> tuple[int, int, str]:
        ctype = str(c.get("candidate_type") or c.get("kind") or "")
        pri = 0 if ctype in directives["prioritize_types"] else 1
        if ctype in directives["deprioritize_types"]:
            pri = 2
        support = str(c.get("support_level") or "none")
        return (pri, -SUPPORT_ORDER.get(support, 0), str(c.get("candidate_id") or ""))

    ordered = sorted(pool, key=sort_key)
    retain_budget = directives["max_retain"]

    for cand in ordered:
        ctype = str(cand.get("candidate_type") or cand.get("kind") or "unresolved_ambiguity")
        cid = str(cand.get("candidate_id") or "")
        support = str(cand.get("support_level") or "none")
        item = {
            **cand,
            "kind": ctype,
            "candidate_type": ctype,
            "retain": False,
            "memory_write_authorized": False,
            "durable_write_authorized": False,
            "policy_effect": False,
            "update_authorized": False,
        }

        # A will-level prohibition is itself sufficient to reject a candidate;
        # retain the precise policy reason before provenance accounting.
        if ctype in directives["forbid_types"]:
            item["rejection_reason"] = "will_forbid_type"
            rejected.append(item)
            continue

        # A candidate without a canonical batch/body is unresolved evidence,
        # not an invented fact and not a candidate that may merely wait for
        # gates.  Count it explicitly and close it before any caller gates.
        batch_hash = str(item.get("batch_receipt_hash") or "")
        canonical_candidate = None
        batch_row = None
        if batch_hash and hasattr(store, "get_distillation_candidate_batch_by_hash"):
            batch_row = store.get_distillation_candidate_batch_by_hash(repo, batch_hash)
            for canonical in (batch_row or {}).get("candidates") or ():
                if isinstance(canonical, Mapping) and str(canonical.get("candidate_id") or "") == cid:
                    canonical_candidate = canonical
                    break
        if canonical_candidate is None:
            noncanonical_candidate_count += 1
            provenance_unknown_count += 1
            item["provenance_state"] = "unknown"
            item["rejection_reason"] = "canonical_trajectory_unresolved"
            rejected.append(item)
            continue
        if any(
            field in canonical_candidate
            and (field not in item or _canonical(canonical_candidate.get(field)) != _canonical(item.get(field)))
            for field in ("candidate_type", "summary", "support_level", "source", "evidence")
        ):
            provenance_fail_count += 1
            item["provenance_state"] = "fail"
            item["rejection_reason"] = "canonical_candidate_mismatch"
            rejected.append(item)
            continue
        provenance_pass_count += 1
        item["provenance_state"] = "pass"

        if ctype in directives["forbid_types"]:
            item["rejection_reason"] = "will_forbid_type"
            rejected.append(item)
            continue
        if not verification.get("verified"):
            item["rejection_reason"] = "will_unverified"
            rejected.append(item)
            continue
        if not has_admit:
            item["rejection_reason"] = "will_admit_scope_missing_or_unverified"
            rejected.append(item)
            continue

        directed = (
            ctype in directives["admit_types"]
            or ctype in directives["prioritize_types"]
            or cid in directives["admit_ids"]
        )
        if not directed:
            item["rejection_reason"] = "not_directed_by_will"
            rejected.append(item)
            continue

        min_support = directives["min_support"]
        if ctype in OUTCOME_LINKED_TYPES:
            # Outcome-linked lessons need medium+ regardless of lower min_support.
            need = max(SUPPORT_ORDER.get(min_support, 1), SUPPORT_ORDER["medium"])
        else:
            need = SUPPORT_ORDER.get(min_support, 1)
        if SUPPORT_ORDER.get(support, 0) < need:
            item["rejection_reason"] = "insufficient_support"
            item["required_support_rank"] = need
            rejected.append(item)
            continue

        if not gates["open"]:
            item["rejection_reason"] = "gates_closed"
            item["gates"] = gates
            deferred.append(item)
            continue

        if retain_budget is not None and len(admitted) >= retain_budget:
            item["rejection_reason"] = "will_cap_retain"
            rejected.append(item)
            continue

        # Admit under will + gates. Still not host mutate / execute.
        admitted_item = {
            **item,
            "retain": True,
            "admission_reason": "will_directed_gates_open",
            "memory_write_authorized": True,
            "durable_write_authorized": True,
            "will_id": will.get("will_id"),
            "will_receipt_hash": will.get("receipt_hash"),
        }
        admitted.append(admitted_item)

    provenance_closed = (
        provenance_fail_count == 0
        and provenance_unknown_count == 0
        and provenance_legacy_partial_count == 0
        and noncanonical_candidate_count == 0
    )
    durable = (
        bool(admitted)
        and gates["open"]
        and verification.get("verified") is True
        and provenance_closed
    )
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "distillation_membrane_admission",
        "repo": repo,
        "repository_id": will.get("repository_id"),
        "session_id": session_id or will.get("session_id") or "",
        "body_epoch_id": body_epoch_id or will.get("body_epoch_id") or "",
        "turn_id": int(turn_id if turn_id is not None else 0),
        "will_id": will.get("will_id"),
        "will_receipt_hash": will.get("receipt_hash"),
        "will_verified": bool(verification.get("verified")),
        "will_verification": {
            "verified": verification.get("verified"),
            "errors": verification.get("errors"),
            "has_admit_scope": verification.get("has_admit_scope"),
        },
        "gates": gates,
        "gate_derivation": derived,
        "directives": {
            "forbid_types": sorted(directives["forbid_types"]),
            "admit_types": sorted(directives["admit_types"]),
            "prioritize_types": sorted(directives["prioritize_types"]),
            "deprioritize_types": sorted(directives["deprioritize_types"]),
            "admit_ids": sorted(directives["admit_ids"]),
            "max_retain": directives["max_retain"],
            "min_support": directives["min_support"],
        },
        "input_candidate_count": len(pool),
        "admitted": admitted,
        "rejected": rejected,
        "deferred": deferred,
        "admitted_count": len(admitted),
        "rejected_count": len(rejected),
        "deferred_count": len(deferred),
        "provenance_pass_count": provenance_pass_count,
        "provenance_fail_count": provenance_fail_count,
        "provenance_unknown_count": provenance_unknown_count,
        "provenance_legacy_partial_count": provenance_legacy_partial_count,
        "noncanonical_candidate_count": noncanonical_candidate_count,
        "invented_or_unresolved_count": (
            provenance_fail_count
            + provenance_unknown_count
            + provenance_legacy_partial_count
        ),
        # Compatibility alias; unlike v8.9.2 this is derived, not invariant.
        "invented_count": noncanonical_candidate_count,
        "sources_only_from_candidates": True,
        "durable_write_authorized": durable,
        "memory_write_authorized": durable,
        "adaptation_authorized": False,
        "execution_authorized": False,
        "host_mutate_authorized": False,
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": not durable,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
        "law": (
            "retain only if will.admits ∧ ΓΞWOS=1 ∧ trajectory_candidate "
            "∧ support_sufficient; will never invents facts"
        ),
    }
    event_id = "evt_" + _sha(
        {
            "kind": "distillation_membrane_admission",
            "will": material["will_receipt_hash"],
            "admitted": [c.get("candidate_id") for c in admitted],
            "gates": gates["product"],
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
        try:
            append_result = store.append_membrane_admission(repo, receipt)
        except Exception as exc:
            receipt = {
                **receipt,
                "canonical_persistence": "failed",
                "canonical_persistence_error": f"{type(exc).__name__}:{exc}",
                "persisted": False,
                "durable_write_authorized": False,
                "memory_write_authorized": False,
                "advisory_only": True,
            }
            return receipt
        receipt = {**receipt, "canonical_persistence": "duplicate" if append_result.get("duplicate") else "committed", "persisted": True}
        store.set_setting(f"membrane_latest:{repo}", receipt)
    else:
        receipt = {**receipt, "canonical_persistence": "not_requested", "persisted": False}
    return receipt


__all__ = [
    "CLAIM_BOUNDARY",
    "GLYPH",
    "OUTCOME_LINKED_TYPES",
    "SCHEMA",
    "STRUCTURAL_TYPES",
    "VERSION",
    "apply_will_bound_membrane",
]
