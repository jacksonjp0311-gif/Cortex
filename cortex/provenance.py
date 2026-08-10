"""Canonical provenance and gate derivation for v8.9.2.

This module is deliberately boring.  It resolves already persisted evidence;
it does not create evidence, promote a caller assertion, or grant authority.
The public result keeps diagnostic planes separate so ``unknown`` cannot be
silently treated as ``pass``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

LINEAGE_STATES = frozenset({"pass", "fail", "unknown", "legacy_partial"})
GATE_STATES = frozenset({"pass", "fail", "unknown"})
EPSILON = 1e-12


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _without_receipt_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(k): v for k, v in value.items() if str(k) != "receipt_hash"}


def receipt_hash_valid(receipt: Mapping[str, Any]) -> bool:
    """Validate the common non-circular receipt envelope hash."""
    expected = str(receipt.get("receipt_hash") or "")
    if len(expected) != 64:
        return False
    try:
        return expected == sha(_without_receipt_hash(receipt))
    except (TypeError, ValueError, OverflowError):
        return False


def _repo_identity(store: Any, repo: str) -> tuple[str, bool]:
    try:
        row = store.repo(repo)
    except Exception:
        row = None
    if row is None:
        return "", False
    try:
        return str(row["repository_id"] or ""), True
    except (KeyError, IndexError, TypeError):
        return str(getattr(row, "repository_id", "") or ""), True


def _same(value: Any, other: Any) -> bool:
    try:
        return canonical(value) == canonical(other)
    except (TypeError, ValueError, OverflowError):
        return False


def _find_candidate(batch: Mapping[str, Any], candidate_id: str) -> Mapping[str, Any] | None:
    for candidate in batch.get("candidates") or ():
        if isinstance(candidate, Mapping) and str(candidate.get("candidate_id") or "") == candidate_id:
            return candidate
    return None


def _load(store: Any, method: str, *args: Any) -> dict[str, Any] | None:
    fn = getattr(store, method, None)
    if fn is None:
        return None
    try:
        row = fn(*args)
    except Exception:
        return None
    return dict(row) if isinstance(row, Mapping) else None


def _identity_match(row: Mapping[str, Any], *, repo: str, repository_id: str,
                    session_id: str = "", turn_id: int | None = None,
                    epoch_id: str = "") -> bool:
    if str(row.get("repo") or "") != str(repo):
        return False
    if repository_id and str(row.get("repository_id") or "") != repository_id:
        return False
    if session_id and str(row.get("session_id") or "") != session_id:
        return False
    if turn_id is not None and int(row.get("turn_id") or 0) != int(turn_id):
        return False
    if epoch_id and str(row.get("body_epoch_id") or "") != epoch_id:
        return False
    return True


def verify_candidate_provenance(
    store: Any,
    repo: str,
    memory: Mapping[str, Any],
    *,
    membrane: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve one admitted memory against canonical membrane/trajectory rows.

    Missing modern provenance is reported as ``legacy_partial``.  Explicit
    mismatches are ``fail``.  Neither state is eligible for model-facing use.
    """
    m = dict(memory or {})
    errors: list[str] = []
    repository_id, repo_present = _repo_identity(store, repo)
    requested_repo_id = str(m.get("repository_id") or "")
    repository_match = bool(repo_present and requested_repo_id and requested_repo_id == repository_id)
    if not requested_repo_id:
        errors.append("memory_repository_id_missing")
    elif not repository_match:
        errors.append("repository_mismatch")

    membrane_hash = str(m.get("membrane_receipt_hash") or "")
    membrane_row = dict(membrane or {}) if membrane is not None else None
    if membrane_row is None and membrane_hash:
        membrane_row = _load(store, "get_membrane_admission_by_hash", repo, membrane_hash)
    membrane_present = bool(membrane_row)
    membrane_hash_ok = bool(membrane_present and str(membrane_row.get("receipt_hash") or "") == membrane_hash)
    membrane_repo_ok = bool(
        membrane_row and _identity_match(membrane_row, repo=repo, repository_id=repository_id)
    )
    if not membrane_hash:
        errors.append("missing_membrane")
    elif not membrane_present:
        errors.append("membrane_not_in_ledger")
    elif not membrane_hash_ok:
        errors.append("membrane_hash_mismatch")
    elif not membrane_repo_ok:
        errors.append("membrane_repository_mismatch")

    candidate_id = str(m.get("candidate_id") or "")
    admitted_candidate: Mapping[str, Any] | None = None
    if membrane_row:
        for candidate in membrane_row.get("admitted") or ():
            if isinstance(candidate, Mapping) and str(candidate.get("candidate_id") or "") == candidate_id:
                admitted_candidate = candidate
                break
    candidate_present = admitted_candidate is not None
    if membrane_present and not candidate_present:
        errors.append("candidate_not_in_membrane_admitted")

    batch_hash = str(
        m.get("candidate_batch_hash")
        or (admitted_candidate or {}).get("batch_receipt_hash")
        or (m.get("source") or {}).get("candidate_batch_hash")
        or ""
    )
    batch_row = _load(store, "get_distillation_candidate_batch_by_hash", repo, batch_hash) if batch_hash else None
    batch_present = bool(batch_row)
    batch_hash_ok = bool(batch_present and str(batch_row.get("receipt_hash") or "") == batch_hash)
    batch_identity_ok = bool(
        batch_row
        and _identity_match(
            batch_row,
            repo=repo,
            repository_id=repository_id,
            session_id=str(m.get("session_id") or ""),
            turn_id=int(m.get("turn_id") or 0),
            epoch_id=str(m.get("body_epoch_id") or ""),
        )
    )
    canonical_candidate = _find_candidate(batch_row or {}, candidate_id)
    candidate_content_valid = bool(canonical_candidate)
    if not batch_hash:
        errors.append("candidate_batch_hash_missing")
    elif not batch_present:
        errors.append("candidate_batch_not_in_ledger")
    elif not batch_hash_ok:
        errors.append("candidate_batch_hash_mismatch")
    elif not batch_identity_ok:
        errors.append("candidate_batch_identity_mismatch")
    if batch_present and not canonical_candidate:
        errors.append("candidate_not_in_canonical_batch")

    # Compare the exact candidate material where a modern memory preserved it.
    memory_material = m.get("candidate_material")
    if canonical_candidate is not None and isinstance(memory_material, Mapping):
        core_fields = (
            "candidate_id", "candidate_type", "kind", "summary", "support_level",
            "source", "evidence", "session_id", "turn_id", "repo", "index",
        )
        if any(
            key in canonical_candidate
            and (key not in memory_material
                 or not _same(memory_material.get(key), canonical_candidate.get(key)))
            for key in core_fields
        ):
            errors.append("candidate_batch_material_mismatch")
            candidate_content_valid = False
    if canonical_candidate is not None and admitted_candidate is not None:
        # Admission may add policy flags, but source/identity/content must agree.
        for field in ("candidate_type", "summary", "support_level", "source", "evidence"):
            if field in canonical_candidate and field in admitted_candidate and not _same(
                canonical_candidate.get(field), admitted_candidate.get(field)
            ):
                errors.append(f"candidate_{field}_mismatch")
                candidate_content_valid = False

    source = dict(m.get("source") or {})
    canonical_source = dict((canonical_candidate or {}).get("source") or {})
    transition_hash = str(source.get("transition_hash") or canonical_source.get("transition_hash") or "")
    prior_hash = str(source.get("prior_frame_hash") or canonical_source.get("prior_frame_hash") or "")
    next_hash = str(source.get("next_frame_hash") or canonical_source.get("next_frame_hash") or "")
    transition = _load(store, "get_interconnect_transition_by_hash", repo, transition_hash) if transition_hash else None
    prior_frame = _load(store, "get_interconnect_frame_by_hash", repo, prior_hash) if prior_hash else None
    next_frame = _load(store, "get_interconnect_frame_by_hash", repo, next_hash) if next_hash else None
    transition_present = bool(transition)
    prior_present = bool(prior_frame)
    next_present = bool(next_frame)
    transition_valid = bool(
        transition
        and str(transition.get("receipt_hash") or "") == transition_hash
        and _identity_match(transition, repo=repo, repository_id=repository_id,
                            session_id=str(m.get("session_id") or ""),
                            turn_id=int(m.get("turn_id") or 0))
        and str(transition.get("prior_frame_hash") or "") == prior_hash
        and str(transition.get("next_frame_hash") or "") == next_hash
    )
    prior_valid = bool(
        prior_frame
        and str(prior_frame.get("receipt_hash") or "") == prior_hash
        and _identity_match(prior_frame, repo=repo, repository_id=repository_id,
                            epoch_id=str(m.get("body_epoch_id") or ""))
    )
    next_valid = bool(
        next_frame
        and str(next_frame.get("receipt_hash") or "") == next_hash
        and _identity_match(next_frame, repo=repo, repository_id=repository_id,
                            epoch_id=str(m.get("body_epoch_id") or ""))
    )
    if not transition_hash or not prior_hash or not next_hash:
        errors.append("trajectory_provenance_missing")
    else:
        if not transition_present:
            errors.append("transition_not_in_ledger")
        elif not transition_valid:
            errors.append("transition_frame_binding_mismatch")
        if not prior_present:
            errors.append("prior_frame_not_in_ledger")
        elif not prior_valid:
            errors.append("prior_frame_invalid")
        if not next_present:
            errors.append("next_frame_not_in_ledger")
        elif not next_valid:
            errors.append("next_frame_invalid")

    session_match = bool(
        str(m.get("session_id") or "")
        and str(m.get("session_id") or "")
        == str((batch_row or {}).get("session_id") or m.get("session_id") or "")
    )
    turn_match = bool(
        batch_row is not None
        and int(m.get("turn_id") or 0) == int(batch_row.get("turn_id") or 0)
    )
    epoch_match = bool(
        str(m.get("body_epoch_id") or "")
        and str(m.get("body_epoch_id") or "")
        == str((batch_row or {}).get("body_epoch_id") or m.get("body_epoch_id") or "")
    )
    transition_hash_match = bool(
        transition
        and str(transition.get("prior_frame_hash") or "") == prior_hash
        and str(transition.get("next_frame_hash") or "") == next_hash
    )
    modern_fields = bool(batch_hash and transition_hash and prior_hash and next_hash)
    legacy_missing = {
        "candidate_batch_hash_missing",
        "trajectory_provenance_missing",
    }
    explicit_errors = [error for error in errors if error not in legacy_missing]
    if explicit_errors:
        lineage_state = "fail"
    elif not modern_fields or any(error in legacy_missing for error in errors):
        lineage_state = "legacy_partial"
    elif not all((repo_present, repository_match, membrane_present, membrane_hash_ok,
                  membrane_repo_ok, candidate_present, candidate_content_valid,
                  batch_present, batch_hash_ok, batch_identity_ok, transition_valid,
                  prior_valid, next_valid, session_match, turn_match, epoch_match,
                  transition_hash_match)):
        lineage_state = "fail"
    else:
        lineage_state = "pass"
    if lineage_state not in LINEAGE_STATES:
        lineage_state = "unknown"
    return {
        "candidate_id": candidate_id,
        "candidate_batch_hash": batch_hash,
        "candidate_present": candidate_present,
        "candidate_content_valid": candidate_content_valid,
        "batch_present": batch_present,
        "batch_hash_valid": batch_hash_ok,
        "trajectory_verified": bool(transition_valid and prior_valid and next_valid),
        "transition_hash": transition_hash,
        "transition_present": transition_present,
        "transition_valid": transition_valid,
        "prior_frame_hash": prior_hash,
        "prior_frame_present": prior_present,
        "prior_frame_valid": prior_valid,
        "next_frame_hash": next_hash,
        "next_frame_present": next_present,
        "next_frame_valid": next_valid,
        "proposal_hash": source.get("proposal_hash") or canonical_source.get("proposal_hash"),
        "evaluation_hash": source.get("evaluation_hash") or canonical_source.get("evaluation_hash"),
        "joint_action_hash": source.get("joint_action_hash") or canonical_source.get("joint_action_hash"),
        "outcome_hash": source.get("outcome_hash") or canonical_source.get("outcome_hash"),
        "outcome_binding_state": "pass" if source.get("outcome_hash") else "unknown",
        "witness_state": "unknown",
        "repository_match": repository_match,
        "session_match": session_match,
        "turn_match": turn_match,
        "epoch_match": epoch_match,
        "cohort_match": True,
        "lineage_state": lineage_state,
        "canonical_lineage_valid": lineage_state == "pass",
        "errors": sorted(set(errors)),
    }


def _plane(state: str, source: str, reason: str, **extra: Any) -> dict[str, Any]:
    if state not in GATE_STATES:
        state = "unknown"
    return {"state": state, "source": source, "reason": reason, **extra}


def _caller_constraint(value: Any, name: str) -> dict[str, Any] | None:
    if value is False:
        return _plane("fail", "caller_constraint", f"caller_closed:{name}")
    return None


def derive_gate_state(
    store: Any,
    repo: str,
    *,
    will: Mapping[str, Any] | None = None,
    will_secret: str | None = None,
    session_id: str | None = None,
    body_epoch_id: str | None = None,
    constitutional_gate: bool | None = None,
    epoch_compatible: bool | None = None,
    witness_present: bool | None = None,
    outcome_closed: bool | None = None,
    stable_regime: bool | None = None,
    witness: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
    gate_evidence: Mapping[str, Any] | None = None,
    caller_constraints: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive ΓΞWOS from canonical evidence; caller True never opens a gate."""
    from .epoch import observe_current_epoch
    from .will import verify_will

    w = dict(will or {})
    verified_will = verify_will(
        store, repo, w, secret=will_secret,
        require_session_id=session_id,
        require_body_epoch_id=body_epoch_id,
    ) if w else {"verified": False, "errors": ["will_missing"]}
    evidence = dict(gate_evidence or {})
    constraints = dict(caller_constraints or {})
    planes: dict[str, dict[str, Any]] = {}
    # A true assertion is only a request.  A false request is a hard close.
    closed = _caller_constraint(constitutional_gate, "constitutional") or _caller_constraint(
        constraints.get("constitutional"), "constitutional"
    )
    if closed:
        planes["constitutional"] = closed
    elif evidence.get("constitutional_receipt_hash") and evidence.get("constitutional_verified") is True:
        planes["constitutional"] = _plane("pass", "canonical_gate_evidence", "verified_constitutional_receipt",
                                            receipt_hash=evidence.get("constitutional_receipt_hash"))
    else:
        planes["constitutional"] = _plane("unknown", "canonical_gate_evidence", "no_independent_constitutional_receipt")

    closed = _caller_constraint(epoch_compatible, "epoch_cohort") or _caller_constraint(
        constraints.get("epoch_cohort"), "epoch_cohort"
    )
    if closed:
        planes["epoch_cohort"] = closed
    else:
        try:
            observed = observe_current_epoch(store, repo)
        except Exception:
            observed = {}
        live = str(observed.get("live_epoch_id") or observed.get("epoch_id") or "")
        requested = str(body_epoch_id or w.get("body_epoch_id") or "")
        epoch_ok = bool(observed.get("verified") is True and live and requested and live == requested)
        planes["epoch_cohort"] = _plane(
            "pass" if epoch_ok else "unknown", "current_epoch_verifier",
            "current_epoch_matches" if epoch_ok else "epoch_not_independently_verified",
            live_epoch_id=live, requested_epoch_id=requested,
        )

    closed = _caller_constraint(witness_present, "witness") or _caller_constraint(
        constraints.get("witness"), "witness"
    )
    if closed:
        planes["witness"] = closed
    else:
        witness_id = str((witness or {}).get("witness_id") or evidence.get("witness_id") or "")
        witness_ok = bool(witness and witness.get("passed") is True and witness_id)
        # Caller-supplied true is intentionally insufficient; a canonical row
        # is required when the store exposes witness commitments.
        if witness_ok and hasattr(store, "db"):
            try:
                row = store.db.execute(
                    "SELECT witness_id FROM witness_commitments WHERE witness_id=?",
                    (witness_id,),
                ).fetchone()
                witness_ok = row is not None
            except Exception:
                witness_ok = False
        planes["witness"] = _plane(
            "pass" if witness_ok else "unknown", "canonical_witness" if witness_ok else "witness_ledger",
            "independent_witness_verified" if witness_ok else "witness_missing_or_unresolved",
            witness_id=witness_id,
        )

    closed = _caller_constraint(outcome_closed, "outcome") or _caller_constraint(
        constraints.get("outcome"), "outcome"
    )
    if closed:
        planes["outcome"] = closed
    else:
        out = dict(outcome or {})
        outcome_id = str(out.get("outcome_id") or "")
        outcome_ok = bool(outcome_id and out.get("verified") is True)
        if outcome_ok and hasattr(store, "db"):
            try:
                row = store.db.execute(
                    "SELECT outcome_id FROM task_outcomes WHERE repo=? AND outcome_id=?",
                    (repo, outcome_id),
                ).fetchone()
                outcome_ok = row is not None
            except Exception:
                outcome_ok = False
        planes["outcome"] = _plane(
            "pass" if outcome_ok else "unknown", "canonical_outcome" if outcome_ok else "outcome_ledger",
            "outcome_closed_and_verified" if outcome_ok else "outcome_not_independently_closed",
            outcome_id=outcome_id,
        )

    closed = _caller_constraint(stable_regime, "stability") or _caller_constraint(
        constraints.get("stability"), "stability"
    )
    if closed:
        planes["stability"] = closed
    elif evidence.get("stability_receipt_hash") and evidence.get("stability_verified") is True:
        planes["stability"] = _plane("pass", "canonical_gate_evidence", "stability_receipt_verified",
                                      receipt_hash=evidence.get("stability_receipt_hash"))
    else:
        planes["stability"] = _plane("unknown", "canonical_gate_evidence", "stability_not_independently_verified")

    if not verified_will.get("verified"):
        planes["will"] = _plane("fail", "will_verifier", "principal_will_not_verified",
                                 errors=verified_will.get("errors"))
    else:
        planes["will"] = _plane("pass", "will_verifier", "principal_will_verified",
                                 receipt_hash=w.get("receipt_hash"))

    states = [str(p.get("state")) for p in planes.values()]
    if "fail" in states:
        overall = "fail"
    elif states and all(s == "pass" for s in states):
        overall = "pass"
    else:
        overall = "unknown"
    return {
        "constitutional": planes["constitutional"],
        "epoch_cohort": planes["epoch_cohort"],
        "witness": planes["witness"],
        "outcome": planes["outcome"],
        "stability": planes["stability"],
        "will": planes["will"],
        "overall": overall,
        "durable_admission": overall == "pass",
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "policy_effect": False,
        "caller_true_is_not_evidence": True,
    }


__all__ = [
    "GATE_STATES",
    "LINEAGE_STATES",
    "canonical",
    "derive_gate_state",
    "receipt_hash_valid",
    "sha",
    "verify_candidate_provenance",
]
