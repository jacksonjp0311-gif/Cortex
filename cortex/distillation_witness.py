"""v9.8 independent, tri-state semantic distillation witnesses.

The verifier is deliberately conservative.  It proves exact support from the
canonical public outcome/evaluation surface; it does not ask a model whether a
model-authored abstraction is true and it never turns similarity into proof.
Generalizations that cannot be reconstructed remain UNKNOWN.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from .competence import SCHEMA as CURRENT_COMPETENCE_SCHEMA
from .competence import get_competence_candidate, verify_competence_candidate
from .model_circulation import verify_model_circulation

SCHEMA = "cortex-distillation-witness/1.0"
VERSION = "9.8.0"
VERIFIER = "canonical-exact-support/1.0"
CLAIM_FIELDS = (
    "capability",
    "intended_outcome",
    "prerequisites",
    "applicability_conditions",
    "environmental_assumptions",
    "required_tools",
    "failure_conditions",
    "counterevidence",
    "uncertainty",
)
_LABEL_KEYS = frozenset({"id", "capability_id", "outcome_id", "key", "name", "code"})
_NONCLAIM_KEYS = frozenset({"description", "summary", "rationale", "prose"})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _atom(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _leaves(value: Any, path: str, *, skip_labels: bool = False) -> list[tuple[str, str]]:
    if isinstance(value, Mapping):
        result: list[tuple[str, str]] = []
        for key in sorted(value, key=lambda item: str(item)):
            name = str(key)
            if skip_labels and name.lower() in (_LABEL_KEYS | _NONCLAIM_KEYS):
                continue
            result.extend(_leaves(value[key], f"{path}.{name}", skip_labels=skip_labels))
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        result = []
        for index, item in enumerate(value):
            result.extend(_leaves(item, f"{path}[{index}]", skip_labels=skip_labels))
        return result
    atom = _atom(value)
    return [(path, atom)] if atom else []


def _origin(candidate: Mapping[str, Any]) -> tuple[str, int]:
    lineage = candidate.get("evidence_lineage")
    trajectories = lineage.get("originating_trajectories") if isinstance(lineage, Mapping) else None
    if not isinstance(trajectories, Sequence) or not trajectories or not isinstance(trajectories[0], Mapping):
        return "", 0
    return str(trajectories[0].get("session_id") or ""), int(trajectories[0].get("turn_id") or 0)


def ensure_distillation_witness_tables(store: Any) -> None:
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS distillation_witness_receipts(
            witness_id TEXT PRIMARY KEY,
            receipt_hash TEXT NOT NULL UNIQUE,
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            competence_id TEXT NOT NULL,
            competence_receipt_hash TEXT NOT NULL,
            status TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS distillation_witness_no_update
        BEFORE UPDATE ON distillation_witness_receipts BEGIN
            SELECT RAISE(ABORT, 'distillation witnesses are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS distillation_witness_no_delete
        BEFORE DELETE ON distillation_witness_receipts BEGIN
            SELECT RAISE(ABORT, 'distillation witnesses are immutable');
        END;
        """
    )


def get_distillation_witness(store: Any, repo: str, witness_id: str) -> dict[str, Any] | None:
    ensure_distillation_witness_tables(store)
    row = store.db.execute(
        "SELECT receipt_json FROM distillation_witness_receipts WHERE repo=? AND witness_id=?",
        (str(repo), str(witness_id)),
    ).fetchone()
    return json.loads(str(row["receipt_json"])) if row is not None else None


def create_distillation_witness(
    store: Any,
    repo: str,
    competence_id: str,
    *,
    persist: bool = True,
) -> dict[str, Any]:
    """Reconstruct exact public support without accepting caller truth values."""
    candidate = get_competence_candidate(store, repo, competence_id)
    candidate_check = verify_competence_candidate(store, repo, competence_id)
    if candidate is None:
        raise ValueError("canonical competence candidate is missing")
    session_id, turn_id = _origin(candidate)
    circulation = verify_model_circulation(store, repo, session_id, turn_id=turn_id)
    rows = store.symbiotic_session_receipts(repo, session_id)
    source_rows = [
        row
        for row in rows
        if int(row.get("turn_id") or 0) == turn_id
        and str(row.get("kind") or "") in {"model_evaluation", "model_outcome", "model_witness"}
    ]
    source_atoms: set[str] = set()
    for row in source_rows:
        kind = str(row.get("kind") or "")
        if kind == "model_outcome":
            semantic_source = {
                "observed_result": row.get("observed_result"),
                "success": row.get("success"),
                "status": row.get("status"),
            }
        elif kind == "model_evaluation":
            semantic_source = {
                "task_contract": row.get("task_contract"),
                "evaluation": row.get("evaluation"),
            }
        else:
            # Witness identity proves chronology/binding, not semantic content.
            semantic_source = {}
        for _, atom in _leaves(semantic_source, kind or "source"):
            source_atoms.add(atom)

    claims: list[dict[str, Any]] = []
    for field in CLAIM_FIELDS:
        for path, atom in _leaves(candidate.get(field), field, skip_labels=True):
            state = "SUPPORTED" if atom in source_atoms else "UNKNOWN"
            claims.append(
                {
                    "claim_id": _sha({"field": field, "path": path, "atom": atom}),
                    "field": field,
                    "path": path,
                    "claim_hash": _sha(atom),
                    "state": state,
                    "proof": "exact_canonical_public_match" if state == "SUPPORTED" else "no_exact_canonical_support",
                }
            )

    outcome_success = candidate.get("outcome_evidence", {}).get("success")
    candidate_type = str(candidate.get("candidate_type") or "")
    type_state = (
        "SUPPORTED"
        if (candidate_type == "successful_procedure" and outcome_success is True)
        or (candidate_type in {"failed_hypothesis", "counterevidence"} and outcome_success is False)
        else "UNKNOWN"
    )
    claims.append(
        {
            "claim_id": _sha({"field": "candidate_type", "value": candidate_type}),
            "field": "candidate_type",
            "path": "candidate_type",
            "claim_hash": _sha(candidate_type),
            "state": type_state,
            "proof": "canonical_outcome_classification" if type_state == "SUPPORTED" else "outcome_does_not_establish_type",
        }
    )
    unsupported = [item for item in claims if item["state"] != "SUPPORTED"]
    identity_state = "pass" if candidate.get("schema_version") == CURRENT_COMPETENCE_SCHEMA else "legacy_partial"
    status = (
        "SUPPORTED"
        if candidate_check.get("valid") is True
        and circulation.get("valid") is True
        and identity_state == "pass"
        and not unsupported
        else "UNKNOWN"
    )
    source_bindings = [
        {"kind": row.get("kind"), "receipt_hash": row.get("receipt_hash"), "content_hash": row.get("content_hash")}
        for row in source_rows
    ]
    identity = {
        "schema_version": SCHEMA,
        "repository_id": str(candidate.get("repository_id") or ""),
        "repo": str(repo),
        "competence_id": str(competence_id),
        "competence_receipt_hash": str(candidate.get("receipt_hash") or ""),
        "trajectory_receipt_hash": str((candidate.get("originating_trajectories") or [{}])[0].get("trajectory_receipt_hash") or ""),
        "verifier": VERIFIER,
    }
    witness_id = _sha(identity)
    receipt: dict[str, Any] = {
        **identity,
        "witness_id": witness_id,
        "status": status,
        "semantic_identity_state": identity_state,
        "candidate_valid": candidate_check.get("valid") is True,
        "circulation_valid": circulation.get("valid") is True,
        "claim_results": claims,
        "supported_count": len(claims) - len(unsupported),
        "unknown_count": len(unsupported),
        "contradicted_count": 0,
        "source_bindings": source_bindings,
        "counterevidence_completeness": "UNKNOWN",
        "prerequisite_completeness": "UNKNOWN",
        "generalization_authorized": False,
        "distribution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "execution_authorized": False,
        "host_mutate_authorized": False,
        "advisory_only": True,
        "created_at": time.time(),
    }
    receipt["receipt_hash"] = _sha(receipt)
    if not persist:
        return receipt
    ensure_distillation_witness_tables(store)
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT receipt_json FROM distillation_witness_receipts WHERE witness_id=?",
            (witness_id,),
        ).fetchone()
        if existing is not None:
            return json.loads(str(existing["receipt_json"]))
        conn.execute(
            "INSERT INTO distillation_witness_receipts VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                witness_id,
                receipt["receipt_hash"],
                receipt["repository_id"],
                repo,
                competence_id,
                receipt["competence_receipt_hash"],
                status,
                _canonical(receipt),
                receipt["created_at"],
            ),
        )
    return receipt


def verify_distillation_witness(store: Any, repo: str, witness_id: str) -> dict[str, Any]:
    stored = get_distillation_witness(store, repo, witness_id)
    if stored is None:
        return {"valid": False, "state": "unknown", "errors": ["witness_missing"]}
    expected_hash = _sha({key: value for key, value in stored.items() if key != "receipt_hash"})
    errors = [] if expected_hash == stored.get("receipt_hash") else ["receipt_hash_invalid"]
    rebuilt = create_distillation_witness(store, repo, str(stored.get("competence_id") or ""), persist=False)
    for key in ("witness_id", "status", "semantic_identity_state", "claim_results", "source_bindings"):
        if rebuilt.get(key) != stored.get(key):
            errors.append(f"{key}_recomputation_mismatch")
    return {
        "valid": not errors,
        "state": "pass" if not errors and stored.get("status") == "SUPPORTED" else "unknown" if not errors else "fail",
        "errors": sorted(set(errors)),
        "status": stored.get("status"),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "advisory_only": True,
    }


__all__ = [
    "CLAIM_FIELDS",
    "SCHEMA",
    "VERIFIER",
    "VERSION",
    "create_distillation_witness",
    "ensure_distillation_witness_tables",
    "get_distillation_witness",
    "verify_distillation_witness",
]
