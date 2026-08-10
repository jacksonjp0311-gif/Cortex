"""Canonical evidence resolution and gate derivation for v8.9.3.

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

# Candidate types deliberately have different evidence obligations.  The
# distinction is explicit so ``not_applicable`` cannot masquerade as proof.
EVIDENCE_REQUIREMENTS: dict[str, dict[str, str]] = {
    "verified_fact": {"outcome": "required", "witness": "required"},
    "successful_procedure": {"outcome": "required", "witness": "required"},
    "failed_hypothesis": {"outcome": "required", "witness": "required"},
    "counterevidence": {"outcome": "required", "witness": "required"},
    "useful_route": {"outcome": "required", "witness": "required"},
    "persistent_constraint": {"outcome": "not_applicable", "witness": "optional"},
    "regime_warning": {"outcome": "not_applicable", "witness": "optional"},
    "unresolved_ambiguity": {"outcome": "not_applicable", "witness": "optional"},
}


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
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False


def _schema_receipt_hash_valid(
    receipt: Mapping[str, Any], kind: str
) -> bool:
    """Verify a receipt using its producer's explicit hash law.

    Historical Cortex receipts do not all hash the same envelope.  This
    dispatcher therefore refuses to apply the generic ``all-fields`` rule to
    a schema whose producer defines a narrower material set.
    """
    expected = str(receipt.get("receipt_hash") or "")
    if len(expected) != 64:
        return False
    try:
        if kind == "will":
            ignored = {
                "receipt_hash",
                "issued",
                "created_at",
                "persisted",
                "canonical_persistence",
                "canonical_persistence_error",
            }
            material = {k: v for k, v in receipt.items() if k not in ignored}
        elif kind in {"membrane", "candidate_batch", "transition"}:
            material = {
                k: v for k, v in receipt.items() if k not in {"receipt_hash", "created_at"}
            }
        elif kind == "frame":
            material = {
                k: v
                for k, v in receipt.items()
                if k not in {"receipt_hash", "captured_at"}
            }
        else:
            return False
        return sha(material) == expected
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False


def _load_outcome(store: Any, repo: str, outcome_id: str) -> dict[str, Any] | None:
    if not outcome_id or not hasattr(store, "db"):
        return None
    try:
        row = store.db.execute(
            "SELECT * FROM task_outcomes WHERE repo=? AND outcome_id=?",
            (str(repo), str(outcome_id)),
        ).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    out = dict(row)
    try:
        out["verification_payload"] = json.loads(
            str(out.get("verification_payload_json") or "{}")
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        out["verification_payload"] = None
    return out


def _verify_canonical_outcome(
    store: Any,
    repo: str,
    outcome: Mapping[str, Any] | None,
    *,
    expected_transition_hash: str | None = None,
) -> dict[str, Any]:
    """Resolve and verify an outcome row; caller fields are references only."""
    supplied = dict(outcome or {})
    outcome_id = str(supplied.get("outcome_id") or "")
    row = _load_outcome(store, repo, outcome_id)
    errors: list[str] = []
    present = row is not None
    if not present:
        return {
            "outcome_id": outcome_id,
            "outcome_present": False,
            "outcome_identity_valid": False,
            "outcome_binding_valid": False,
            "outcome_closed": False,
            "outcome_verified": False,
            "outcome_verification_state": "unknown",
            "errors": ["outcome_not_in_ledger"],
        }
    identity_valid = str(row.get("repo") or "") == str(repo) and bool(
        row.get("outcome_id")
    )
    if not identity_valid:
        errors.append("outcome_identity_invalid")

    # A non-empty status closes the row; a verification type explicitly marked
    # independent/canonical is the semantic verification surface.  A caller's
    # ``verified`` bit is never consulted.
    status = str(row.get("status") or "").strip().lower()
    verification_type = str(row.get("verification_type") or "").strip().lower()
    closed = status not in {"", "open", "pending", "unknown", "unwitnessed"}
    verified = verification_type in {
        "independent",
        "canonical",
        "human_review",
        "test",
        "witnessed",
    }
    if not closed:
        errors.append("outcome_not_closed")
    if not verified:
        errors.append("outcome_not_independently_verified")

    binding_valid = True
    for field in ("activation_id", "session_id", "repo", "status", "reward"):
        if field not in supplied:
            continue
        if field == "reward":
            try:
                equal = float(supplied[field]) == float(row.get(field))
            except (TypeError, ValueError, OverflowError):
                equal = False
        else:
            equal = str(supplied.get(field)) == str(row.get(field))
        if not equal:
            binding_valid = False
            errors.append(f"outcome_{field}_binding_mismatch")
    if expected_transition_hash:
        # The canonical outcome schema has no transition column.  A declared
        # transition binding must therefore be present in the immutable
        # verification payload, otherwise it is unknown rather than inferred.
        payload = row.get("verification_payload")
        if not isinstance(payload, Mapping) or str(
            payload.get("transition_hash") or ""
        ) != str(expected_transition_hash):
            binding_valid = False
            errors.append("outcome_transition_binding_missing_or_mismatch")
    if not str(supplied.get("activation_id") or ""):
        binding_valid = False
        errors.append("outcome_activation_binding_missing")

    state = "pass" if identity_valid and closed and verified and binding_valid and not errors else (
        "fail" if any("mismatch" in error or "invalid" in error for error in errors) else "unknown"
    )
    return {
        "outcome_id": outcome_id,
        "outcome_present": True,
        "outcome_identity_valid": identity_valid,
        "outcome_binding_valid": binding_valid,
        "outcome_closed": closed,
        "outcome_verified": verified,
        "outcome_verification_state": state,
        "status": status,
        "verification_type": verification_type,
        "activation_id": row.get("activation_id"),
        "session_id": row.get("session_id"),
        "errors": sorted(set(errors)),
        "row": row,
    }


def _verify_constitutional_receipt(
    store: Any, repo: str, reference: str, body_epoch_id: str | None
) -> dict[str, Any]:
    """Use the canonical activation-conformance ledger as Γ evidence."""
    receipt = None
    if reference and hasattr(store, "get_activation_conformance_receipt"):
        receipt = store.get_activation_conformance_receipt(reference, repo=repo)
    if receipt is None:
        return {
            "state": "unknown",
            "source": "activation_conformance_ledger",
            "reason": "constitutional_receipt_not_in_ledger",
            "identity_valid": False,
            "content_valid": False,
            "binding_valid": False,
            "semantic_valid": False,
            "receipt_hash": reference or None,
        }
    try:
        chain = store.verify_activation_conformance_chain(
            repo,
            str(receipt.get("operator_id") or ""),
            str(receipt.get("body_epoch_id") or ""),
            str(receipt.get("measurement_cohort_id") or ""),
            str(receipt.get("coordinate_schema_digest") or ""),
        )
    except Exception:
        chain = {"chain_valid": False, "valid": False, "errors": ["chain_verifier_error"]}
    identity_valid = bool(
        str(receipt.get("receipt_hash") or "") == str(reference)
        and str(receipt.get("repo") or "") == str(repo)
        and receipt.get("receipt_decode_error") is None
    )
    body = receipt.get("receipt_body") or receipt
    invariants = body.get("invariant_results") or []
    invariant_ok = bool(
        isinstance(invariants, list)
        and invariants
        and all(isinstance(item, Mapping) and item.get("passed") is True for item in invariants)
    )
    try:
        from .ostt.independent_verifier import validate_conformance_payload

        scientific_validation = validate_conformance_payload(body)
    except Exception:
        scientific_validation = {"valid": False, "errors": ["scientific_validator_error"]}
    content_valid = bool(
        str(receipt.get("status") or "") == "conformance_measured"
        and invariant_ok
        and scientific_validation.get("valid") is True
    )
    epoch_ok = bool(body_epoch_id and str(receipt.get("body_epoch_id") or "") == str(body_epoch_id))
    cohort_ok = bool(receipt.get("measurement_cohort_id") and receipt.get("coordinate_schema_digest"))
    binding_valid = bool(epoch_ok and cohort_ok and chain.get("chain_valid") is True)
    semantic_valid = bool(
        body.get("conformance_ready") is True
        and body.get("policy_effect") is False
        and body.get("update_authorized") is False
    )
    errors = list(chain.get("errors") or [])
    errors.extend(str(error) for error in scientific_validation.get("errors") or ())
    if not identity_valid:
        errors.append("constitutional_identity_invalid")
    if not content_valid:
        errors.append("constitutional_content_invalid")
    if not binding_valid:
        errors.append("constitutional_binding_invalid")
    if not semantic_valid:
        errors.append("constitutional_property_not_proved")
    state = "pass" if all((identity_valid, content_valid, binding_valid, semantic_valid)) else (
        "fail" if any("invalid" in error for error in errors) else "unknown"
    )
    return {
        "state": state,
        "source": "activation_conformance_ledger",
        "reason": "canonical_activation_conformance_verified" if state == "pass" else "constitutional_receipt_not_proven",
        "receipt_hash": reference,
        "identity_valid": identity_valid,
        "content_valid": content_valid,
        "binding_valid": binding_valid,
        "semantic_valid": semantic_valid,
        "epoch_current": epoch_ok,
        "cohort_current": cohort_ok,
        "chain_valid": bool(chain.get("chain_valid")),
        "errors": sorted(set(errors)),
    }


def _verify_stability_surface(
    store: Any, repo: str, reference: str | None, body_epoch_id: str | None
) -> dict[str, Any]:
    """Verify current operational stability from canonical telemetry surfaces."""
    try:
        from .epoch import observe_current_epoch

        epoch = observe_current_epoch(store, repo)
    except Exception:
        epoch = {}
    sense = store.get_setting(f"self_sensing_latest:{repo}", {}) or {}
    binding = store.get_setting(f"binding_field_latest:{repo}", {}) or {}
    resonance = store.get_setting(f"resonance_sweep_latest:{repo}", {}) or {}
    if not isinstance(sense, Mapping) or not isinstance(binding, Mapping):
        return {"state": "unknown", "source": "canonical_runtime_telemetry", "reason": "stability_surface_missing"}
    sense_class = str(sense.get("classification") or sense.get("status") or "").upper()
    binding_class = str(binding.get("classification") or "").upper()
    frame_class = str(
        binding.get("signals", {}).get("last_frame_classification")
        if isinstance(binding.get("signals"), Mapping)
        else binding.get("last_frame_classification") or ""
    ).upper()
    stable_classes = {"QUIESCENT", "COHERENT_DIFFERENTIATED"}
    epoch_ok = bool(epoch.get("verified") is True and body_epoch_id and str(epoch.get("epoch_id") or epoch.get("live_epoch_id") or "") == str(body_epoch_id))
    try:
        sense_material = {
            key: sense.get(key)
            for key in (
                "repo", "classification", "reasons", "z_vector", "residual_r",
                "F_t", "gates", "baseline_n_updates", "version",
            )
        }
        binding_material = {
            key: binding.get(key)
            for key in ("repo", "classification", "reasons", "field_vector", "version")
        }
        sense_hash_valid = bool(
            sense.get("observation_hash") and sha(sense_material) == str(sense.get("observation_hash"))
        )
        binding_hash_valid = bool(
            binding.get("observation_hash") and sha(binding_material) == str(binding.get("observation_hash"))
        )
    except (TypeError, ValueError, OverflowError, RecursionError):
        sense_hash_valid = False
        binding_hash_valid = False
    identity_valid = bool(sense_hash_valid and binding_hash_valid)
    repo_identity_valid = bool(
        str(sense.get("repo") or "") == str(repo)
        and str(binding.get("repo") or "") == str(repo)
    )
    identity_valid = bool(identity_valid and repo_identity_valid)
    content_valid = bool(
        sense.get("observation_id")
        and repo_identity_valid
        and sense_class == "NOMINAL"
        and binding_class == "VERIFIED_REGIME"
        and frame_class in stable_classes
        and isinstance(sense.get("gates"), Mapping)
        and sense.get("gates", {}).get("epoch_current") is True
        and sense.get("gates", {}).get("phase_bound") is True
    )
    blocked = sense_class in {"STRESSED", "UNBOUND", "DRIFT", "COLD", "INDETERMINATE"} or binding_class in {
        "BINDING_GAP", "BUFFER_PENDING", "COLD_FIELD", "TRANSITION_REGIME", "DRIFT_REGIME", "INDETERMINATE"
    } or str(resonance.get("status") or "") in {"no_stable_peak", "transitional", "candidate"}
    binding_valid = bool(epoch_ok and not blocked)
    semantic_valid = bool(content_valid and binding_valid)
    if reference and reference not in {str(sense.get("observation_hash") or ""), str(binding.get("observation_hash") or "")}:
        identity_valid = False
        semantic_valid = False
    errors: list[str] = []
    if not identity_valid:
        errors.append("stability_observation_identity_invalid")
    if not epoch_ok:
        errors.append("stability_epoch_not_current")
    if blocked:
        errors.append("stability_operational_regime_blocked")
    if not content_valid:
        errors.append("stability_property_not_proved")
    state = "pass" if all((identity_valid, content_valid, binding_valid, semantic_valid)) else (
        "fail" if blocked or (reference and not identity_valid) else "unknown"
    )
    return {
        "state": state,
        "source": "canonical_runtime_telemetry",
        "reason": "stable_operational_regime_verified" if state == "pass" else "stability_not_independently_proven",
        "identity_valid": identity_valid,
        "content_valid": content_valid,
        "binding_valid": binding_valid,
        "semantic_valid": semantic_valid,
        "epoch_current": epoch_ok,
        "self_sensing_classification": sense_class,
        "binding_classification": binding_class,
        "frame_classification": frame_class,
        "observation_hashes": [str(sense.get("observation_hash") or ""), str(binding.get("observation_hash") or "")],
        "sense_hash_valid": sense_hash_valid,
        "binding_hash_valid": binding_hash_valid,
        "repository_identity_valid": repo_identity_valid,
        "errors": errors,
    }
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
    try:
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
    except (TypeError, ValueError, OverflowError):
        return False


def verify_candidate_provenance(
    store: Any,
    repo: str,
    memory: Mapping[str, Any],
    *,
    membrane: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a memory from canonical candidate, trajectory, and evidence rows."""
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
    # Always resolve the canonical row; a supplied in-memory membrane is only
    # useful as a compatibility fallback when no hash is declared.
    membrane_row = _load(store, "get_membrane_admission_by_hash", repo, membrane_hash) if membrane_hash else None
    if membrane_row is None and membrane is not None and not membrane_hash:
        membrane_row = dict(membrane)
    membrane_present = bool(membrane_row)
    membrane_hash_ok = bool(
        membrane_present
        and str(membrane_row.get("receipt_hash") or "") == membrane_hash
        and _schema_receipt_hash_valid(membrane_row, "membrane")
    )
    membrane_repo_ok = bool(
        membrane_row and _identity_match(membrane_row, repo=repo, repository_id=repository_id)
    )
    if not membrane_hash:
        errors.append("missing_membrane")
    elif not membrane_present:
        errors.append("membrane_not_in_ledger")
    elif not membrane_hash_ok:
        errors.append("membrane_hash_or_content_invalid")
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
    batch_hash_ok = bool(
        batch_present
        and str(batch_row.get("receipt_hash") or "") == batch_hash
        and _schema_receipt_hash_valid(batch_row, "candidate_batch")
    )
    try:
        memory_turn = int(m.get("turn_id") or 0)
    except (TypeError, ValueError, OverflowError):
        memory_turn = -1
        errors.append("memory_turn_invalid")
    batch_identity_ok = bool(
        batch_row
        and _identity_match(
            batch_row,
            repo=repo,
            repository_id=repository_id,
            session_id=str(m.get("session_id") or ""),
            turn_id=memory_turn,
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
        errors.append("candidate_batch_hash_or_content_invalid")
    elif not batch_identity_ok:
        errors.append("candidate_batch_identity_mismatch")
    if batch_present and not canonical_candidate:
        errors.append("candidate_not_in_canonical_batch")

    memory_material = m.get("candidate_material")
    if canonical_candidate is not None and isinstance(memory_material, Mapping):
        core_fields = (
            "candidate_id", "candidate_type", "kind", "summary", "support_level",
            "source", "evidence", "session_id", "turn_id", "repo", "index",
        )
        if any(
            key in canonical_candidate
            and (key not in memory_material or not _same(memory_material.get(key), canonical_candidate.get(key)))
            for key in core_fields
        ):
            errors.append("candidate_batch_material_mismatch")
            candidate_content_valid = False
    if canonical_candidate is not None and admitted_candidate is not None:
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
    transition_present, prior_present, next_present = bool(transition), bool(prior_frame), bool(next_frame)
    transition_valid = bool(
        transition
        and str(transition.get("receipt_hash") or "") == transition_hash
        and _schema_receipt_hash_valid(transition, "transition")
        and _identity_match(transition, repo=repo, repository_id=repository_id,
                            session_id=str(m.get("session_id") or ""), turn_id=memory_turn)
        and str(transition.get("prior_frame_hash") or "") == prior_hash
        and str(transition.get("next_frame_hash") or "") == next_hash
    )
    prior_valid = bool(
        prior_frame
        and str(prior_frame.get("receipt_hash") or "") == prior_hash
        and _schema_receipt_hash_valid(prior_frame, "frame")
        and _identity_match(prior_frame, repo=repo, repository_id=repository_id,
                            epoch_id=str(m.get("body_epoch_id") or ""))
    )
    next_valid = bool(
        next_frame
        and str(next_frame.get("receipt_hash") or "") == next_hash
        and _schema_receipt_hash_valid(next_frame, "frame")
        and _identity_match(next_frame, repo=repo, repository_id=repository_id,
                            epoch_id=str(m.get("body_epoch_id") or ""))
    )
    if not transition_hash or not prior_hash or not next_hash:
        errors.append("trajectory_provenance_missing")
    else:
        if not transition_present:
            errors.append("transition_not_in_ledger")
        elif not transition_valid:
            errors.append("transition_or_frame_binding_invalid")
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
        and str(m.get("session_id") or "") == str((batch_row or {}).get("session_id") or "")
    )
    turn_match = bool(batch_row is not None and memory_turn == int(batch_row.get("turn_id") or 0))
    epoch_match = bool(
        str(m.get("body_epoch_id") or "")
        and str(m.get("body_epoch_id") or "") == str((batch_row or {}).get("body_epoch_id") or "")
    )
    transition_hash_match = bool(
        transition
        and str(transition.get("prior_frame_hash") or "") == prior_hash
        and str(transition.get("next_frame_hash") or "") == next_hash
    )

    # Cohort/schema compatibility is an actual comparison, not a default.
    cohort_values = [
        str(
            m.get("measurement_cohort_id")
            or source.get("measurement_cohort_id")
            or canonical_source.get("measurement_cohort_id")
            or ""
        ),
        str((batch_row or {}).get("measurement_cohort_id") or ""),
        str((prior_frame or {}).get("measurement_cohort_id") or ""),
        str((next_frame or {}).get("measurement_cohort_id") or ""),
    ]
    schema_values = [
        str(
            m.get("coordinate_schema_digest")
            or source.get("coordinate_schema_digest")
            or canonical_source.get("coordinate_schema_digest")
            or ""
        ),
        str((batch_row or {}).get("coordinate_schema_digest") or ""),
        str((prior_frame or {}).get("coordinate_schema_digest") or ""),
        str((next_frame or {}).get("coordinate_schema_digest") or ""),
    ]
    cohort_values_nonempty = [v for v in cohort_values if v]
    schema_values_nonempty = [v for v in schema_values if v]
    cohort_state = (
        "pass" if len(cohort_values_nonempty) == len(cohort_values) and len(set(cohort_values_nonempty)) == 1
        else "fail" if len(set(cohort_values_nonempty)) > 1
        else "unknown"
    )
    schema_state = (
        "pass" if len(schema_values_nonempty) == len(schema_values) and len(set(schema_values_nonempty)) == 1
        else "fail" if len(set(schema_values_nonempty)) > 1
        else "unknown"
    )
    if cohort_state != "pass":
        errors.append("cohort_mismatch" if cohort_state == "fail" else "cohort_missing")
    if schema_state != "pass":
        errors.append("coordinate_schema_mismatch" if schema_state == "fail" else "coordinate_schema_missing")

    candidate_type = str(
        m.get("candidate_type")
        or (canonical_candidate or {}).get("candidate_type")
        or (canonical_candidate or {}).get("kind")
        or ""
    )
    requirements = dict(EVIDENCE_REQUIREMENTS.get(candidate_type, {"outcome": "required", "witness": "required"}))
    outcome_id = str(
        m.get("outcome_id")
        or source.get("outcome_id")
        or canonical_source.get("outcome_id")
        or (m.get("outcome") or {}).get("outcome_id")
        or ""
    )
    outcome_ref = dict(m.get("outcome") or {}) if isinstance(m.get("outcome"), Mapping) else {"outcome_id": outcome_id}
    if requirements["outcome"] == "not_applicable":
        outcome_plane = {
            "requirement": "not_applicable",
            "state": "pass",
            "reason": "candidate_type_has_no_outcome_requirement",
            "outcome_present": False,
            "outcome_identity_valid": False,
            "outcome_binding_valid": False,
            "outcome_verification_state": "not_applicable",
        }
    else:
        outcome_verification = _verify_canonical_outcome(
            store, repo, outcome_ref, expected_transition_hash=transition_hash or None
        )
        outcome_plane = {
            "requirement": requirements["outcome"],
            "state": "pass" if outcome_verification.get("outcome_verification_state") == "pass" else outcome_verification.get("outcome_verification_state", "unknown"),
            **outcome_verification,
        }
        if outcome_plane["state"] != "pass":
            errors.extend(str(e) for e in outcome_verification.get("errors") or ())

    witness_hash = str(
        m.get("witness_result_hash")
        or source.get("witness_result_hash")
        or canonical_source.get("witness_result_hash")
        or ""
    )
    if requirements["witness"] == "not_applicable":
        witness_plane = {"requirement": "not_applicable", "state": "pass", "reason": "candidate_type_has_no_witness_requirement", "witness_result_state": "not_applicable"}
    elif not witness_hash and requirements["witness"] == "optional":
        witness_plane = {"requirement": "optional", "state": "pass", "reason": "optional_witness_not_declared", "witness_result_state": "not_applicable"}
    else:
        from .witness import verify_witness_result

        witness_verification = verify_witness_result(
            store,
            repo,
            witness_hash,
            expected_controller=str(m.get("controller") or "evidence_baseline") or None,
            expected_witness_id=str(m.get("witness_id") or "") or None,
            expected_outcome_id=outcome_id or None,
            expected_transition_hash=transition_hash or None,
            expected_body_epoch_id=str(m.get("body_epoch_id") or "") or None,
            expected_session_id=str(m.get("session_id") or "") or None,
        )
        witness_plane = {
            "requirement": requirements["witness"],
            "state": "pass" if witness_verification.get("verified") else witness_verification.get("result_state", "unknown"),
            "witness_result_state": witness_verification.get("result_state", "unknown"),
            "witness_result_present": witness_verification.get("witness_result_present", False),
            "witness_identity_valid": witness_verification.get("identity_valid", False),
            "witness_chronology_valid": witness_verification.get("chronology_valid", False),
            "witness_binding_valid": witness_verification.get("binding_valid", False),
            "errors": witness_verification.get("errors") or [],
            "witness_result_hash": witness_hash,
        }
        if witness_plane["state"] != "pass":
            errors.extend(str(e) for e in witness_plane["errors"])

    modern_fields = bool(batch_hash and transition_hash and prior_hash and next_hash and membrane_hash)
    legacy_missing = {
        "memory_repository_id_missing",
        "candidate_batch_hash_missing",
        "trajectory_provenance_missing",
        "cohort_missing",
        "coordinate_schema_missing",
    }
    structural_errors = [
        error for error in errors
        if error not in legacy_missing and error not in {
            "outcome_not_in_ledger", "outcome_not_closed", "outcome_not_independently_verified",
            "witness_result_not_in_ledger", "witness_success_criterion_not_met",
        }
    ]
    core_ok = all(
        (
            repo_present,
            repository_match,
            membrane_present,
            membrane_hash_ok,
            membrane_repo_ok,
            candidate_present,
            candidate_content_valid,
            batch_present,
            batch_hash_ok,
            batch_identity_ok,
            transition_valid,
            prior_valid,
            next_valid,
            session_match,
            turn_match,
            epoch_match,
            transition_hash_match,
            cohort_state == "pass",
            schema_state == "pass",
        )
    )
    if structural_errors:
        lineage_state = "fail"
    elif not modern_fields or any(error in legacy_missing for error in errors):
        lineage_state = "legacy_partial"
    elif not core_ok:
        lineage_state = "unknown"
    elif any(
        plane.get("requirement") not in {"optional", "not_applicable"}
        and plane.get("state") != "pass"
        for plane in (outcome_plane, witness_plane)
    ):
        lineage_state = "unknown"
    else:
        lineage_state = "pass"
    if lineage_state not in LINEAGE_STATES:
        lineage_state = "unknown"
    return {
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "evidence_requirements": requirements,
        "candidate_batch_hash": batch_hash,
        "candidate_present": candidate_present,
        "candidate_content_valid": candidate_content_valid,
        "batch_present": batch_present,
        "batch_hash_valid": batch_hash_ok,
        "batch_identity_valid": batch_identity_ok,
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
        "outcome_binding_state": outcome_plane.get("state"),
        "outcome_present": outcome_plane.get("outcome_present", False),
        "outcome_identity_valid": outcome_plane.get("outcome_identity_valid", False),
        "outcome_binding_valid": outcome_plane.get("outcome_binding_valid", False),
        "outcome_verification_state": outcome_plane.get("outcome_verification_state", "unknown"),
        "outcome_plane": outcome_plane,
        "witness_state": witness_plane.get("state"),
        "witness_commitment_present": witness_plane.get("commitment_present", False),
        "witness_result_present": witness_plane.get("witness_result_present", False),
        "witness_identity_valid": witness_plane.get("witness_identity_valid", False),
        "witness_chronology_valid": witness_plane.get("witness_chronology_valid", False),
        "witness_binding_valid": witness_plane.get("witness_binding_valid", False),
        "witness_result_state": witness_plane.get("witness_result_state", "unknown"),
        "witness_plane": witness_plane,
        "repository_match": repository_match,
        "session_match": session_match,
        "turn_match": turn_match,
        "epoch_match": epoch_match,
        "cohort_match": cohort_state == "pass",
        "cohort_state": cohort_state,
        "coordinate_schema_state": schema_state,
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


def _legacy_derive_gate_state(
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
    candidate_type: str | None = None,
    measurement_cohort_id: str | None = None,
) -> dict[str, Any]:
    """Derive ΓΞWOS from canonical evidence; caller True never opens a gate."""
    # Compatibility name only.  Keep all callers on the v8.9.3 resolver so
    # the retired Boolean-shaped implementation below cannot be reached.
    return derive_gate_state(
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
        gate_evidence=gate_evidence,
        caller_constraints=caller_constraints,
        candidate_type=candidate_type,
        measurement_cohort_id=measurement_cohort_id,
    )
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
    candidate_type: str | None = None,
    measurement_cohort_id: str | None = None,
) -> dict[str, Any]:
    """Resolve the v8.9.3 GateProofReceipt from canonical evidence objects."""
    from .epoch import observe_current_epoch
    from .will import verify_will

    evidence = dict(gate_evidence or {})
    constraints = dict(caller_constraints or {})
    candidate_type = str(candidate_type or evidence.get("candidate_type") or "")
    requirements = dict(EVIDENCE_REQUIREMENTS.get(candidate_type, {"outcome": "required", "witness": "required"}))
    w = dict(will or {})
    verified_will = (
        verify_will(
            store,
            repo,
            w,
            secret=will_secret,
            require_session_id=session_id,
            require_body_epoch_id=body_epoch_id,
        )
        if w
        else {"verified": False, "errors": ["will_missing"]}
    )

    def closed(value: Any, name: str) -> dict[str, Any] | None:
        return _caller_constraint(value, name) or _caller_constraint(
            constraints.get(name), name
        )

    c = closed(constitutional_gate, "constitutional")
    constitutional = c or _verify_constitutional_receipt(
        store,
        repo,
        str(evidence.get("constitutional_receipt_hash") or ""),
        body_epoch_id or w.get("body_epoch_id"),
    )
    constitutional.setdefault("requirement", "required")

    c = closed(epoch_compatible, "epoch_cohort")
    if c:
        epoch_plane = {**c, "requirement": "required"}
    else:
        try:
            observed = observe_current_epoch(store, repo)
        except Exception:
            observed = {}
        live = str(observed.get("live_epoch_id") or observed.get("epoch_id") or "")
        requested = str(body_epoch_id or w.get("body_epoch_id") or "")
        epoch_ok = bool(observed.get("verified") is True and live and requested and live == requested)
        requested_cohort = str(
            measurement_cohort_id
            or evidence.get("measurement_cohort_id")
            or evidence.get("cohort_id")
            or ""
        )
        latest_cohort = None
        if requested_cohort and hasattr(store, "latest_activation_conformance_receipt"):
            try:
                latest_cohort = store.latest_activation_conformance_receipt(
                    repo,
                    body_epoch_id=requested,
                    measurement_cohort_id=requested_cohort,
                )
            except Exception:
                latest_cohort = None
        cohort_ok = bool(
            requested_cohort
            and latest_cohort is not None
            and str(latest_cohort.get("measurement_cohort_id") or "") == requested_cohort
            and str(latest_cohort.get("body_epoch_id") or "") == requested
        )
        epoch_state = "pass" if epoch_ok and cohort_ok else "unknown"
        if requested_cohort and latest_cohort is not None and not cohort_ok:
            epoch_state = "fail"
        epoch_plane = _plane(
            epoch_state,
            "current_epoch_and_cohort_verifier",
            "current_epoch_and_cohort_match" if epoch_state == "pass" else "epoch_or_cohort_not_independently_verified",
            requirement="required",
            live_epoch_id=live,
            requested_epoch_id=requested,
            measurement_cohort_id=requested_cohort or None,
            epoch_current=epoch_ok,
            cohort_current=cohort_ok,
        )

    c = closed(witness_present, "witness")
    witness_hash = str(
        (witness or {}).get("witness_result_hash")
        or evidence.get("witness_result_hash")
        or ""
    )
    if c:
        witness_plane = {**c, "requirement": requirements["witness"]}
    elif requirements["witness"] == "not_applicable":
        witness_plane = _plane(
            "pass",
            "candidate_requirement_matrix",
            "witness_not_applicable_for_candidate",
            requirement="not_applicable",
            witness_result_state="not_applicable",
        )
    elif requirements["witness"] == "optional" and not witness_hash:
        witness_plane = _plane(
            "pass",
            "candidate_requirement_matrix",
            "optional_witness_not_declared",
            requirement="optional",
            witness_result_state="not_applicable",
        )
    else:
        from .witness import verify_witness_result

        witness_verification = verify_witness_result(
            store,
            repo,
            witness_hash,
            expected_controller=str(
                (witness or {}).get("controller") or evidence.get("controller") or ""
            )
            or None,
            expected_outcome_id=str((outcome or {}).get("outcome_id") or "") or None,
            expected_activation_id=str((outcome or {}).get("activation_id") or "") or None,
            expected_transition_hash=str(evidence.get("transition_hash") or "") or None,
            expected_body_epoch_id=str(body_epoch_id or w.get("body_epoch_id") or "") or None,
            expected_session_id=str(session_id or w.get("session_id") or "") or None,
        )
        witness_plane = _plane(
            "pass" if witness_verification.get("verified") else witness_verification.get("result_state", "unknown"),
            "canonical_witness_result",
            "canonical_witness_result_verified" if witness_verification.get("verified") else "witness_result_not_proven",
            requirement=requirements["witness"],
            witness_result_hash=witness_hash,
            witness_commitment_present=witness_verification.get("commitment_present", False),
            witness_result_present=witness_verification.get("witness_result_present", False),
            witness_identity_valid=witness_verification.get("identity_valid", False),
            witness_chronology_valid=witness_verification.get("chronology_valid", False),
            witness_binding_valid=witness_verification.get("binding_valid", False),
            witness_result_state=witness_verification.get("result_state", "unknown"),
            errors=witness_verification.get("errors") or [],
        )

    c = closed(outcome_closed, "outcome")
    if c:
        outcome_plane = {**c, "requirement": requirements["outcome"]}
    elif requirements["outcome"] == "not_applicable":
        outcome_plane = _plane(
            "pass",
            "candidate_requirement_matrix",
            "outcome_not_applicable_for_candidate",
            requirement="not_applicable",
            outcome_verification_state="not_applicable",
        )
    else:
        outcome_verification = _verify_canonical_outcome(
            store,
            repo,
            dict(outcome or {}),
            expected_transition_hash=str(evidence.get("transition_hash") or "") or None,
        )
        outcome_plane = _plane(
            outcome_verification.get("outcome_verification_state", "unknown"),
            "canonical_outcome_ledger",
            "canonical_outcome_verified" if outcome_verification.get("outcome_verification_state") == "pass" else "outcome_not_proven",
            requirement=requirements["outcome"],
            **outcome_verification,
        )

    c = closed(stable_regime, "stability")
    stability = c or _verify_stability_surface(
        store,
        repo,
        str(evidence.get("stability_receipt_hash") or "") or None,
        body_epoch_id or w.get("body_epoch_id"),
    )
    stability.setdefault("requirement", "required")

    if not verified_will.get("verified"):
        will_plane = _plane(
            "fail",
            "will_verifier",
            "principal_will_not_verified",
            requirement="required",
            errors=verified_will.get("errors"),
            principal_secret_match=(verified_will.get("checks") or {}).get("principal_secret_match", False),
        )
    else:
        will_plane = _plane(
            "pass",
            "will_verifier",
            "principal_will_verified",
            requirement="required",
            receipt_hash=w.get("receipt_hash"),
            principal_secret_match=(verified_will.get("checks") or {}).get("principal_secret_match", False),
            signature_valid=verified_will.get("signature_valid", False),
            receipt_hash_valid=verified_will.get("receipt_hash_valid", False),
        )

    planes = {
        "constitutional": constitutional,
        "epoch_cohort": epoch_plane,
        "witness": witness_plane,
        "outcome": outcome_plane,
        "stability": stability,
        "will": will_plane,
    }
    states = [
        str(plane.get("state"))
        for plane in planes.values()
        if plane.get("requirement") not in {"not_applicable", "optional"}
    ]
    if "fail" in states:
        overall = "fail"
    elif states and all(state == "pass" for state in states):
        overall = "pass"
    else:
        overall = "unknown"
    return {
        **planes,
        "authority": will_plane,
        "requirements": requirements,
        "overall": overall,
        "durable_admission": overall == "pass",
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "policy_effect": False,
        "caller_true_is_not_evidence": True,
        "proof_law": "resolve -> identity -> content -> binding -> semantic_property -> gate",
    }


__all__ = [
    "EVIDENCE_REQUIREMENTS",
    "GATE_STATES",
    "LINEAGE_STATES",
    "canonical",
    "derive_gate_state",
    "receipt_hash_valid",
    "sha",
    "verify_candidate_provenance",
]
