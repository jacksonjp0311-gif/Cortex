"""v9.1 transferable competence distillation.

Competence is a portable operational abstraction, not a renamed memory.  This
module keeps the abstraction in its own immutable ledger and derives it only
from a canonically verified v9.0 model trajectory.  The originating model is
recorded as provenance; it is never required to verify the candidate and it
never grants authority.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "cortex-competence/1.0"
VERSION = "9.1.0"
GLYPH = "⟡◇"
CLAIM_BOUNDARY = (
    "A competence candidate is a portable, advisory abstraction derived from "
    "independently verified external model experience. It is not proof of "
    "universal transfer, authority, execution, learning, or cognition."
)

LIFECYCLE_STATES = frozenset(
    {
        "candidate",
        "origin_verified",
        "transfer_pending",
        "transfer_verified",
        "contested",
        "superseded",
        "revoked",
    }
)
PORTABILITY_STATES = frozenset(
    {
        "pending_transfer_verification",
        "portable_candidate",
        "transfer_verified",
        "model_specific_blocked",
        "blocked",
    }
)
TERMINAL_STATES = frozenset({"superseded", "revoked"})


class CompetenceError(ValueError):
    """Raised when a competence boundary cannot be established."""


class CompetenceAdmissionError(CompetenceError):
    """Raised when a candidate has no independently verified origin."""


# The canonical representation is JSON-backed for ledger portability.  This
# alias gives callers a useful type name without introducing a second mutable
# object model over the immutable receipt.
CompetenceCandidate = dict[str, Any]


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value.decode() if isinstance(value, bytes) else value]
    if isinstance(value, Mapping):
        return [dict(value)]
    if isinstance(value, Sequence):
        return [item for item in value]
    return [value]


def _stable_items(value: Any) -> list[Any]:
    """Normalize set-like semantic fields without discarding their content."""
    normalized: list[Any] = []
    for item in _items(value):
        if isinstance(item, Mapping):
            normalized.append(
                {str(key): item[key] for key in sorted(item, key=lambda key: str(key))}
            )
        else:
            normalized.append(_text(item))
    return sorted(normalized, key=_canonical)


def _semantic_atom(value: Any) -> Any:
    """Return identity-bearing meaning while ignoring prose/model provenance."""
    if isinstance(value, Mapping):
        for key in ("id", "capability_id", "outcome_id", "key", "name", "code"):
            if value.get(key):
                return _text(value[key])
        # A structured condition without an explicit key remains meaningful;
        # descriptions/rationales are deliberately excluded from identity.
        return {
            str(key): _semantic_atom(value[key])
            for key in sorted(value, key=lambda item: str(item))
            if str(key).lower()
            not in {"description", "summary", "rationale", "prose", "text"}
        }
    return _text(value)


def semantic_material(
    *,
    candidate_type: str,
    capability: Any,
    intended_outcome: Any,
    prerequisites: Any,
    applicability_conditions: Any,
    environmental_assumptions: Any,
    required_tools: Any,
    failure_conditions: Any,
) -> dict[str, Any]:
    """Build semantic identity material; model and wording are excluded."""
    return {
        "candidate_type": _text(candidate_type),
        "capability": _semantic_atom(capability),
        "intended_outcome": _semantic_atom(intended_outcome),
        "prerequisites": _stable_items(prerequisites),
        "applicability_conditions": _stable_items(applicability_conditions),
        "environmental_assumptions": _stable_items(environmental_assumptions),
        "required_tools": _stable_items(required_tools),
        "failure_conditions": _stable_items(failure_conditions),
    }


def _repository_id(store: Any, repo: str) -> str:
    row = store.db.execute(
        "SELECT repository_id FROM repositories WHERE name=?", (str(repo),)
    ).fetchone()
    if row is None or not str(row["repository_id"] or ""):
        raise CompetenceError(f"Unknown repository: {repo}")
    return str(row["repository_id"])


def _body_hash(candidate: Mapping[str, Any]) -> str:
    material = {
        str(key): value
        for key, value in candidate.items()
        if key
        not in {
            "receipt_hash",
            "created_at",
            "inserted",
            "duplicate",
            "ledger_receipt_hash",
            "ledger_state",
            "ledger_portability_status",
        }
    }
    return _sha(material)


def _candidate_row_body(row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        raw = row["candidate_json"]
    except (KeyError, IndexError, TypeError):
        raw = row.get("candidate_json") if hasattr(row, "get") else None
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        value = json.loads(str(raw or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return dict(value) if isinstance(value, Mapping) else {}


def ensure_competence_tables(store: Any) -> None:
    """Install the append-only competence ledger for a Store."""
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS competence_candidates(
            competence_id TEXT PRIMARY KEY CHECK(length(competence_id) = 64),
            receipt_hash TEXT NOT NULL CHECK(length(receipt_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            semantic_identity_hash TEXT NOT NULL CHECK(length(semantic_identity_hash) = 64),
            state TEXT NOT NULL,
            portability_status TEXT NOT NULL,
            evidence_lineage_hash TEXT NOT NULL CHECK(length(evidence_lineage_hash) = 64),
            candidate_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, semantic_identity_hash),
            UNIQUE(repository_id, receipt_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_competence_candidates_repo
            ON competence_candidates(repo, created_at DESC);
        CREATE TRIGGER IF NOT EXISTS competence_candidates_no_delete
        BEFORE DELETE ON competence_candidates
        BEGIN
            SELECT RAISE(ABORT, 'canonical competence candidates cannot be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_candidates_no_update
        BEFORE UPDATE ON competence_candidates
        BEGIN
            SELECT RAISE(ABORT, 'canonical competence candidates cannot be updated');
        END;
        """
    )
    store.db.commit()


def _origin_rows(store: Any, repo: str, session_id: str, turn_id: int) -> list[dict[str, Any]]:
    return [
        row
        for row in store.symbiotic_session_receipts(repo, session_id)
        if int(row.get("turn_id") or -1) == int(turn_id)
        and str(row.get("kind") or "") in {
            "model_invocation",
            "model_proposal",
            "model_evaluation",
            "model_outcome",
            "model_witness",
            "model_trajectory",
        }
    ]


def _requirements(candidate_type: str) -> dict[str, str]:
    if candidate_type in {"persistent_constraint", "regime_warning", "unresolved_ambiguity"}:
        return {"outcome": "not_applicable", "witness": "required"}
    return {"outcome": "required", "witness": "required"}


def _verified_origin(
    store: Any, repo: str, session_id: str, turn_id: int
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from .model_circulation import verify_model_circulation

    verification = verify_model_circulation(store, repo, session_id, turn_id=turn_id)
    rows = _origin_rows(store, repo, session_id, turn_id)
    if verification.get("valid") is not True:
        raise CompetenceAdmissionError(
            "no independently verified model trajectory: "
            + ",".join(str(error) for error in verification.get("errors") or ())
        )
    if len(rows) != 6:
        raise CompetenceAdmissionError("model trajectory is incomplete")
    return verification, rows


def _canonical_origin(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_kind = {str(row.get("kind")): row for row in rows}
    invocation = by_kind["model_invocation"]
    proposal = by_kind["model_proposal"]
    evaluation = by_kind["model_evaluation"]
    outcome = by_kind["model_outcome"]
    witness = by_kind["model_witness"]
    trajectory = by_kind["model_trajectory"]
    model_origin = {
        key: invocation.get(key)
        for key in (
            "provider_family",
            "model_id",
            "model_version",
            "adapter_id",
            "adapter_version",
        )
    }
    # Evidence-class fields were introduced in v9.4.  Preserve the exact
    # model-origin body of older immutable candidates instead of injecting
    # modern fields during lineage reconstruction.
    for key in ("evidence_class", "adapter_provenance"):
        if key in invocation:
            model_origin[key] = invocation.get(key)
    return {
        "repository_id": str(trajectory.get("repository_id") or ""),
        "repo": str(trajectory.get("repo") or ""),
        "session_id": str(trajectory.get("session_id") or ""),
        "turn_id": int(trajectory.get("turn_id") or 0),
        "body_epoch_id": str(trajectory.get("body_epoch_id") or ""),
        "trajectory_receipt_hash": str(trajectory.get("receipt_hash") or ""),
        "invocation_receipt_hash": str(invocation.get("receipt_hash") or ""),
        "proposal_receipt_hash": str(proposal.get("receipt_hash") or ""),
        "evaluation_receipt_hash": str(evaluation.get("receipt_hash") or ""),
        "outcome_receipt_hash": str(outcome.get("receipt_hash") or ""),
        "witness_receipt_hash": str(witness.get("receipt_hash") or ""),
        "outcome_content_hash": str(outcome.get("content_hash") or ""),
        "witness_result_hash": str(witness.get("witness_result_hash") or ""),
        "evaluation_state": str(outcome.get("evaluation_state") or "unknown"),
        "outcome_status": str(outcome.get("status") or "unknown"),
        "outcome_success": outcome.get("success"),
        "model_origin": model_origin,
    }


def _lineage_check(
    store: Any, repo: str, candidate: Mapping[str, Any]
) -> tuple[bool, list[str]]:
    """Resolve candidate lineage against the canonical model receipts."""
    lineage = candidate.get("evidence_lineage")
    if not isinstance(lineage, Mapping):
        return False, ["canonical_lineage_missing"]
    trajectories = lineage.get("originating_trajectories")
    if (
        not isinstance(trajectories, Sequence)
        or isinstance(trajectories, (str, bytes))
        or not trajectories
        or not isinstance(trajectories[0], Mapping)
    ):
        return False, ["origin_trajectory_missing"]
    origin_ref = trajectories[0]
    try:
        verification, rows = _verified_origin(
            store,
            repo,
            str(origin_ref.get("session_id") or ""),
            int(origin_ref.get("turn_id") or 0),
        )
    except CompetenceError as exc:
        return False, [f"origin_trajectory_invalid:{exc}"]
    canonical = _canonical_origin(rows)
    errors: list[str] = []
    for key in (
        "repo",
        "repository_id",
        "session_id",
        "turn_id",
        "body_epoch_id",
        "trajectory_receipt_hash",
    ):
        if str(origin_ref.get(key) or "") != str(canonical.get(key) or ""):
            errors.append(f"origin_{key}_binding_invalid")
    outcome = lineage.get("outcome_evidence")
    witness = lineage.get("witness_evidence")
    if not isinstance(outcome, Mapping) or not isinstance(witness, Mapping):
        errors.append("evidence_planes_missing")
    else:
        for key in ("receipt_hash", "content_hash", "status"):
            if str(outcome.get(key) or "") != str(
                canonical.get("outcome_receipt_hash" if key == "receipt_hash" else "outcome_content_hash" if key == "content_hash" else "outcome_status")
                or ""
            ):
                errors.append(f"outcome_{key}_binding_invalid")
        if outcome.get("success") != canonical.get("outcome_success"):
            errors.append("outcome_success_binding_invalid")
        if str(witness.get("receipt_hash") or "") != str(canonical.get("witness_receipt_hash") or ""):
            errors.append("witness_receipt_binding_invalid")
        if str(witness.get("witness_result_hash") or "") != str(canonical.get("witness_result_hash") or ""):
            errors.append("witness_result_binding_invalid")
    if dict(lineage.get("model_origin") or {}) != dict(canonical.get("model_origin") or {}):
        errors.append("model_origin_binding_invalid")
    if verification.get("valid") is not True:
        errors.append("origin_verification_invalid")
    return not errors, sorted(set(errors))


def build_competence_candidate(
    *,
    repo: str,
    repository_id: str,
    origin: Mapping[str, Any],
    capability: Any,
    intended_outcome: Any,
    prerequisites: Any = (),
    applicability_conditions: Any = (),
    environmental_assumptions: Any = (),
    required_tools: Any = (),
    failure_conditions: Any = (),
    counterevidence: Any = (),
    uncertainty: Any = (),
    candidate_type: str = "successful_procedure",
    public_description: str = "",
    rationale_public: str = "",
) -> dict[str, Any]:
    """Build a candidate from already verified canonical origin material."""
    kind = _text(candidate_type) or "unresolved_ambiguity"
    if kind not in {
        "verified_fact",
        "successful_procedure",
        "failed_hypothesis",
        "counterevidence",
        "useful_route",
        "persistent_constraint",
        "regime_warning",
        "unresolved_ambiguity",
        "model_specific_preference",
    }:
        kind = "unresolved_ambiguity"
    if origin.get("outcome_success") is False and kind == "successful_procedure":
        raise CompetenceAdmissionError(
            "verified failure cannot be represented as a successful procedure"
        )
    semantic = semantic_material(
        candidate_type=kind,
        capability=capability,
        intended_outcome=intended_outcome,
        prerequisites=prerequisites,
        applicability_conditions=applicability_conditions,
        environmental_assumptions=environmental_assumptions,
        required_tools=required_tools,
        failure_conditions=failure_conditions,
    )
    semantic_id = _sha(semantic)
    preserved_counterevidence = [item for item in _items(counterevidence)]
    if kind == "model_specific_preference":
        state = "contested"
        portability = "model_specific_blocked"
    elif origin.get("outcome_success") is False:
        state = "origin_verified"
        portability = "portable_candidate" if preserved_counterevidence else "pending_transfer_verification"
    else:
        state = "transfer_pending" if preserved_counterevidence else "origin_verified"
        portability = "portable_candidate" if preserved_counterevidence else "pending_transfer_verification"
    body = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "competence_candidate",
        "repo": str(repo),
        "repository_id": str(repository_id),
        "competence_id": semantic_id,
        "semantic_identity_hash": semantic_id,
        "candidate_type": kind,
        "capability": capability,
        "intended_outcome": intended_outcome,
        "prerequisites": list(_items(prerequisites)),
        "applicability_conditions": list(_items(applicability_conditions)),
        "environmental_assumptions": list(_items(environmental_assumptions)),
        "required_tools": list(_items(required_tools)),
        "failure_conditions": list(_items(failure_conditions)),
        "counterevidence": preserved_counterevidence,
        "uncertainty": list(_items(uncertainty)),
        "public_description": str(public_description or ""),
        "rationale_public": str(rationale_public or ""),
        "revision_state": state,
        "portability_status": portability,
        "requirements": _requirements(kind),
        "evidence_lineage": {
            "canonical": True,
            "origin_verification": {"valid": True},
            "originating_trajectories": [
                {
                    "repo": origin.get("repo"),
                    "repository_id": origin.get("repository_id"),
                    "session_id": origin.get("session_id"),
                    "turn_id": origin.get("turn_id"),
                    "body_epoch_id": origin.get("body_epoch_id"),
                    "trajectory_receipt_hash": origin.get("trajectory_receipt_hash"),
                }
            ],
            "outcome_evidence": {
                "receipt_hash": origin.get("outcome_receipt_hash"),
                "content_hash": origin.get("outcome_content_hash"),
                "status": origin.get("outcome_status"),
                "success": origin.get("outcome_success"),
            },
            "witness_evidence": {
                "receipt_hash": origin.get("witness_receipt_hash"),
                "witness_result_hash": origin.get("witness_result_hash"),
            },
            "model_origin": dict(origin.get("model_origin") or {}),
            "origin_model_required_for_verification": False,
        },
        "counterevidence_conserved": True,
        "distribution_authorized": False,
        "memory_admission_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    # Keep the important evidence planes easy to inspect without making them
    # a second source of truth; the nested lineage object remains canonical.
    body["originating_trajectories"] = list(
        body["evidence_lineage"]["originating_trajectories"]
    )
    body["outcome_evidence"] = dict(body["evidence_lineage"]["outcome_evidence"])
    body["witness_evidence"] = dict(body["evidence_lineage"]["witness_evidence"])
    body["model_origin_provenance"] = dict(body["evidence_lineage"]["model_origin"])
    body["evidence_lineage_hash"] = _sha(body["evidence_lineage"])
    body["receipt_hash"] = _body_hash(body)
    body["created_at"] = time.time()
    return body


def append_competence_candidate(store: Any, repo: str, candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Append one immutable candidate; duplicate semantic identity is stable."""
    ensure_competence_tables(store)
    body = dict(candidate)
    repository_id = _repository_id(store, repo)
    if str(body.get("repo") or "") != str(repo) or str(body.get("repository_id") or "") != repository_id:
        raise CompetenceError("candidate repository binding is invalid")
    competence_id = str(body.get("competence_id") or "")
    semantic_id = str(body.get("semantic_identity_hash") or "")
    if len(competence_id) != 64 or competence_id != semantic_id:
        raise CompetenceError("candidate semantic identity is invalid")
    material = semantic_material(
        candidate_type=str(body.get("candidate_type") or ""),
        capability=body.get("capability"),
        intended_outcome=body.get("intended_outcome"),
        prerequisites=body.get("prerequisites"),
        applicability_conditions=body.get("applicability_conditions"),
        environmental_assumptions=body.get("environmental_assumptions"),
        required_tools=body.get("required_tools"),
        failure_conditions=body.get("failure_conditions"),
    )
    if _sha(material) != semantic_id:
        raise CompetenceError("candidate semantic identity does not match content")
    if _body_hash(body) != str(body.get("receipt_hash") or ""):
        raise CompetenceError("candidate receipt hash is invalid")
    if str(body.get("evidence_lineage_hash") or "") != _sha(body.get("evidence_lineage") or {}):
        raise CompetenceError("candidate evidence lineage hash is invalid")
    if str(body.get("revision_state") or "") not in LIFECYCLE_STATES:
        raise CompetenceError("candidate lifecycle state is invalid")
    if str(body.get("portability_status") or "") not in PORTABILITY_STATES:
        raise CompetenceError("candidate portability state is invalid")
    lineage_valid, lineage_errors = _lineage_check(store, repo, body)
    if not lineage_valid:
        raise CompetenceAdmissionError(
            "candidate lineage is not independently verified: "
            + ",".join(lineage_errors)
        )
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT * FROM competence_candidates WHERE repository_id=? AND semantic_identity_hash=?",
            (repository_id, semantic_id),
        ).fetchone()
        if existing is not None:
            existing_body = _candidate_row_body(existing)
            if existing_body and _body_hash(existing_body) != str(existing["receipt_hash"]):
                raise CompetenceError("canonical competence candidate is corrupt")
            return {**existing_body, "inserted": False, "duplicate": True, "ledger_receipt_hash": existing["receipt_hash"]}
        conn.execute(
            """INSERT INTO competence_candidates(
                competence_id, receipt_hash, repository_id, repo,
                semantic_identity_hash, state, portability_status,
                evidence_lineage_hash, candidate_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                competence_id,
                str(body["receipt_hash"]),
                repository_id,
                repo,
                semantic_id,
                str(body["revision_state"]),
                str(body["portability_status"]),
                str(body["evidence_lineage_hash"]),
                _canonical(body),
                float(body.get("created_at") or time.time()),
            ),
        )
    return {**body, "inserted": True, "duplicate": False, "ledger_receipt_hash": body["receipt_hash"]}


def get_competence_candidate(store: Any, repo: str, competence_id: str) -> dict[str, Any] | None:
    """Resolve a candidate without creating or mutating any durable state."""
    repository_id = _repository_id(store, repo)
    row = store.db.execute(
        "SELECT * FROM competence_candidates WHERE repository_id=? AND repo=? AND competence_id=?",
        (repository_id, repo, str(competence_id)),
    ).fetchone()
    if row is None:
        return None
    body = _candidate_row_body(row)
    body["ledger_receipt_hash"] = str(row["receipt_hash"])
    body["ledger_state"] = str(row["state"])
    body["ledger_portability_status"] = str(row["portability_status"])
    return body


def list_competence_candidates(store: Any, repo: str) -> list[dict[str, Any]]:
    repository_id = _repository_id(store, repo)
    rows = store.db.execute(
        "SELECT * FROM competence_candidates WHERE repository_id=? AND repo=? ORDER BY created_at ASC",
        (repository_id, repo),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        body = _candidate_row_body(row)
        body["ledger_receipt_hash"] = str(row["receipt_hash"])
        result.append(body)
    return result


def verify_competence_candidate(store: Any, repo: str, competence_id: str) -> dict[str, Any]:
    """Verify a canonical candidate and its origin without loading its model."""
    if isinstance(competence_id, Mapping):
        competence_id = str(competence_id.get("competence_id") or "")
    try:
        candidate = get_competence_candidate(store, repo, str(competence_id))
    except CompetenceError as exc:
        return {
            "valid": False,
            "state": "unknown",
            "errors": [f"candidate_resolution_failed:{exc}"],
            "advisory_only": True,
        }
    if candidate is None:
        return {"valid": False, "state": "unknown", "errors": ["candidate_missing"], "advisory_only": True}
    errors: list[str] = []
    if str(candidate.get("receipt_hash") or "") != str(candidate.get("ledger_receipt_hash") or ""):
        errors.append("ledger_receipt_hash_mismatch")
    if str(candidate.get("revision_state") or "") != str(candidate.get("ledger_state") or ""):
        errors.append("ledger_state_mismatch")
    if str(candidate.get("portability_status") or "") != str(candidate.get("ledger_portability_status") or ""):
        errors.append("ledger_portability_status_mismatch")
    if _body_hash(candidate) != str(candidate.get("receipt_hash") or ""):
        errors.append("candidate_receipt_hash_invalid")
    if str(candidate.get("semantic_identity_hash") or "") != str(competence_id):
        errors.append("semantic_identity_invalid")
    material = semantic_material(
        candidate_type=str(candidate.get("candidate_type") or ""),
        capability=candidate.get("capability"),
        intended_outcome=candidate.get("intended_outcome"),
        prerequisites=candidate.get("prerequisites"),
        applicability_conditions=candidate.get("applicability_conditions"),
        environmental_assumptions=candidate.get("environmental_assumptions"),
        required_tools=candidate.get("required_tools"),
        failure_conditions=candidate.get("failure_conditions"),
    )
    if _sha(material) != str(candidate.get("semantic_identity_hash") or ""):
        errors.append("semantic_identity_recomputed_mismatch")
    if str(candidate.get("evidence_lineage_hash") or "") != _sha(candidate.get("evidence_lineage") or {}):
        errors.append("evidence_lineage_hash_invalid")
    lineage = candidate.get("evidence_lineage")
    if not isinstance(lineage, Mapping) or lineage.get("canonical") is not True:
        errors.append("canonical_lineage_missing")
        lineage = {}
    trajectories = lineage.get("originating_trajectories") if isinstance(lineage, Mapping) else None
    if (
        not isinstance(trajectories, Sequence)
        or isinstance(trajectories, (str, bytes))
        or not trajectories
        or not isinstance(trajectories[0], Mapping)
    ):
        errors.append("origin_trajectory_missing")
    else:
        origin = trajectories[0]
        try:
            from .model_circulation import verify_model_circulation

            check = verify_model_circulation(
                store,
                repo,
                str(origin.get("session_id") or ""),
                turn_id=int(origin.get("turn_id") or 0),
            )
            if not check.get("valid"):
                errors.append("origin_trajectory_invalid")
        except Exception as exc:
            errors.append(f"origin_trajectory_unavailable:{type(exc).__name__}")
    lineage_valid, lineage_errors = _lineage_check(store, repo, candidate)
    if not lineage_valid:
        errors.extend(lineage_errors)
    if candidate.get("counterevidence_conserved") is not True:
        errors.append("counterevidence_not_conserved")
    flags = ("distribution_authorized", "memory_admission_authorized", "host_mutate_authorized", "execution_authorized", "policy_effect", "update_authorized")
    for flag in flags:
        if candidate.get(flag) is not False:
            errors.append(f"authority_flag_{flag}")
    return {
        "valid": not errors,
        "state": "fail" if errors else str(candidate.get("revision_state") or "candidate"),
        "errors": sorted(set(errors)),
        "competence_id": competence_id,
        "semantic_identity_hash": candidate.get("semantic_identity_hash"),
        "model_independent_verification": True,
        "origin_model_required": False,
        "counterevidence_conserved": candidate.get("counterevidence_conserved") is True,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
    }


def competence_is_applicable(candidate: Mapping[str, Any], context: Mapping[str, Any]) -> dict[str, Any]:
    """Read-only applicability projection; it never writes a stale transition."""
    reasons: list[str] = []
    state = str(candidate.get("revision_state") or candidate.get("ledger_state") or "candidate")
    portability = str(candidate.get("portability_status") or candidate.get("ledger_portability_status") or "blocked")
    if state != "transfer_verified" or state in TERMINAL_STATES:
        reasons.append("lifecycle_not_transfer_verified")
    if portability in {"model_specific_blocked", "blocked", "pending_transfer_verification"}:
        reasons.append("portability_not_verified")
    conditions = candidate.get("applicability_conditions") or []
    current_epoch = str(context.get("body_epoch_id") or "")
    current_repo = str(context.get("repository_id") or context.get("repo") or "")
    for condition in conditions if isinstance(conditions, Sequence) and not isinstance(conditions, (str, bytes)) else [conditions]:
        if isinstance(condition, Mapping):
            if condition.get("body_epoch_id") and str(condition["body_epoch_id"]) != current_epoch:
                reasons.append("epoch_incompatible")
            if condition.get("repository_id") and str(condition["repository_id"]) != current_repo:
                reasons.append("repository_incompatible")
            if condition.get("required") is False:
                continue
    return {
        "applicable": not reasons,
        "selected": not reasons,
        "reasons": sorted(set(reasons)),
        "read_only": True,
        "state_transition_persisted": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
    }


def derive_competence_candidate(
    store: Any,
    repo: str,
    *,
    session_id: str,
    turn_id: int,
    capability: Any,
    intended_outcome: Any,
    prerequisites: Any = (),
    applicability_conditions: Any = (),
    environmental_assumptions: Any = (),
    required_tools: Any = (),
    failure_conditions: Any = (),
    counterevidence: Any = (),
    uncertainty: Any = (),
    candidate_type: str = "successful_procedure",
    public_description: str = "",
    rationale_public: str = "",
    persist: bool = True,
) -> dict[str, Any]:
    """Derive one candidate from a verified model circulation only."""
    _, rows = _verified_origin(store, repo, str(session_id), int(turn_id))
    origin = _canonical_origin(rows)
    candidate = build_competence_candidate(
        repo=repo,
        repository_id=_repository_id(store, repo),
        origin=origin,
        capability=capability,
        intended_outcome=intended_outcome,
        prerequisites=prerequisites,
        applicability_conditions=applicability_conditions,
        environmental_assumptions=environmental_assumptions,
        required_tools=required_tools,
        failure_conditions=failure_conditions,
        counterevidence=counterevidence,
        uncertainty=uncertainty,
        candidate_type=candidate_type,
        public_description=public_description,
        rationale_public=rationale_public,
    )
    # The verifier result is diagnostic and deliberately does not enter the
    # candidate hash: canonical lineage is already represented by the hashes
    # inside ``evidence_lineage``.  This keeps the identity stable if a future
    # verifier adds diagnostics without changing the competence.
    if persist:
        return append_competence_candidate(store, repo, candidate)
    return {**candidate, "persisted": False, "advisory_only": True}


# Friendly architecture-native aliases for callers that use the phase terms.
distill_competence_candidate = derive_competence_candidate
verify_competence = verify_competence_candidate
competence_active = competence_is_applicable


__all__ = [
    "CLAIM_BOUNDARY",
    "CompetenceCandidate",
    "CompetenceAdmissionError",
    "CompetenceError",
    "GLYPH",
    "LIFECYCLE_STATES",
    "PORTABILITY_STATES",
    "SCHEMA",
    "VERSION",
    "append_competence_candidate",
    "build_competence_candidate",
    "competence_active",
    "competence_is_applicable",
    "derive_competence_candidate",
    "distill_competence_candidate",
    "ensure_competence_tables",
    "get_competence_candidate",
    "list_competence_candidates",
    "semantic_material",
    "verify_competence",
    "verify_competence_candidate",
]
