"""v9.5 independently verified competence revision and explicit promotion.

Assimilation is allowed to propose a revision, but it cannot certify that
proposal or mutate a competence.  This module reloads the immutable cohort and
analysis, recomputes the analysis from the cohort, verifies the proposed
changes, and records a separate verification receipt.  Promotion is an
explicit operation over that canonical verification.  It creates a new
immutable competence body; the parent is never updated.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import time
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from .competence import (
    LIFECYCLE_STATES,
    PORTABILITY_STATES,
    _lineage_check,
    get_competence_candidate,
    semantic_material,
    verify_competence_candidate,
)
from .competence import _body_hash as _competence_body_hash
from .competence_assimilation import (
    analyze_evidence_cohort,
    get_evidence_cohort,
    resolve_feedback_observation,
    verify_assimilation_analysis,
    verify_evidence_cohort,
)

SCHEMA = "cortex-competence-revision-candidate/1.0"
VERIFICATION_SCHEMA = "cortex-competence-revision-verification/1.0"
PROMOTION_SCHEMA = "cortex-competence-revision-promotion/1.0"
SUCCESSOR_SCHEMA = "cortex-competence/1.1"
APPLICABILITY_REVISION_SCHEMA = "cortex-competence-applicability-revision/1.0"
VERSION = "9.5.0"

REVISION_TYPES = frozenset(
    {
        "preserve",
        "annotate",
        "narrow_applicability",
        "broaden_applicability_candidate",
        "specialize",
        "challenge",
        "quarantine_candidate",
        "supersede_candidate",
        "revoke_candidate",
        "unresolved",
    }
)
SUCCESSOR_TYPES = frozenset(
    {"narrow_applicability", "specialize", "supersede_candidate"}
)
RELATION_BY_TYPE = {
    "preserve": "supports",
    "annotate": "annotates",
    "narrow_applicability": "narrows",
    "broaden_applicability_candidate": "generalizes",
    "specialize": "specializes",
    "challenge": "challenges",
    "quarantine_candidate": "challenges",
    "supersede_candidate": "supersedes",
    "revoke_candidate": "challenges",
}
AUTHORITY_FIELDS = (
    "host_mutate_authorized",
    "execution_authorized",
    "memory_admission_authorized",
    "policy_effect",
    "automatic_broadcast",
    "automatic_global_revision",
    "update_authorized",
)
AUTHORITY_FALSE = {
    **{field: False for field in AUTHORITY_FIELDS},
    "advisory_only": True,
}
CLAIM_BOUNDARY = (
    "A revision candidate and its verification are advisory evidence. Only an "
    "explicit promotion operation may append a successor competence. Promotion "
    "does not grant execution, host mutation, memory admission, policy, or "
    "automatic distribution authority."
)
_ACTIVE_PROMOTION_VERIFICATIONS: ContextVar[frozenset[str]] = ContextVar(
    "cortex_active_promotion_verifications", default=frozenset()
)
_ACTIVE_SUCCESSOR_LINEAGES: ContextVar[frozenset[str]] = ContextVar(
    "cortex_active_successor_lineages", default=frozenset()
)


class CompetenceRevisionError(ValueError):
    """Raised when a canonical revision boundary cannot be established."""


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _json(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    try:
        parsed = json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return dict(parsed) if isinstance(parsed, Mapping) else None


def _repo_identity(store: Any, repo: str) -> str:
    row = store.db.execute(
        "SELECT repository_id FROM repositories WHERE name=?", (str(repo),)
    ).fetchone()
    if row is None or not str(row["repository_id"] or ""):
        raise CompetenceRevisionError(f"Unknown repository: {repo}")
    return str(row["repository_id"])


def _revision_table_present(store: Any, table: str) -> bool:
    """Inspect schema without creating it or ending the caller's transaction."""

    row = store.db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (str(table),),
    ).fetchone()
    return row is not None


@contextmanager
def _observational_store(store: Any):
    """Isolate deep verification from a caller-owned SQLite transaction."""

    if not bool(getattr(store.db, "in_transaction", False)):
        yield store
        return
    path = Path(store.path).resolve()
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    view = copy.copy(store)
    view.db = connection
    try:
        yield view
    finally:
        connection.close()


def _without_runtime(body: Mapping[str, Any], *identity_fields: str) -> dict[str, Any]:
    excluded = {
        "created_at",
        "inserted",
        "duplicate",
        "ledger_hash",
        "commit_state",
        *identity_fields,
    }
    return {str(key): value for key, value in body.items() if key not in excluded}


def _stable_union(*groups: Any) -> list[Any]:
    by_hash: dict[str, Any] = {}
    for group in groups:
        if group is None:
            continue
        values = (
            list(group)
            if isinstance(group, Sequence) and not isinstance(group, (str, bytes))
            else [group]
        )
        for item in values:
            by_hash.setdefault(_sha(item), item)
    return [by_hash[key] for key in sorted(by_hash)]


def _canonical_source_binding_errors(
    *,
    source: Mapping[str, Any],
    cohort: Mapping[str, Any],
    analysis: Mapping[str, Any],
    recomputed_analysis: Mapping[str, Any],
    candidate: Mapping[str, Any] | None = None,
) -> list[str]:
    """Require every modern evidence surface to name the same competence body."""

    errors: list[str] = []
    source_id = str(source.get("competence_id") or "")
    source_receipt = str(source.get("receipt_hash") or "")
    surfaces: list[tuple[str, Mapping[str, Any], tuple[str, ...], tuple[str, ...]]] = [
        (
            "cohort",
            cohort,
            ("competence_id", "source_competence_id"),
            ("competence_receipt_hash", "source_competence_receipt_hash"),
        ),
        (
            "analysis",
            analysis,
            ("competence_id", "source_competence_id"),
            ("competence_receipt_hash", "source_competence_receipt_hash"),
        ),
        (
            "recomputed_analysis",
            recomputed_analysis,
            ("competence_id", "source_competence_id"),
            ("competence_receipt_hash", "source_competence_receipt_hash"),
        ),
    ]
    if candidate is not None:
        surfaces.append(
            (
                "candidate",
                candidate,
                ("source_competence_id",),
                ("source_competence_receipt_hash",),
            )
        )
    for label, surface, identity_fields, receipt_fields in surfaces:
        for field in identity_fields:
            if str(surface.get(field) or "") != source_id:
                errors.append(f"{label}_{field}_source_mismatch")
        for field in receipt_fields:
            if str(surface.get(field) or "") != source_receipt:
                errors.append(f"{label}_{field}_source_receipt_mismatch")

    cohort_id = str(cohort.get("cohort_id") or "")
    cohort_hash = str(cohort.get("cohort_hash") or "")
    for label, surface in (
        ("analysis", analysis),
        ("recomputed_analysis", recomputed_analysis),
    ):
        if str(surface.get("cohort_id") or "") != cohort_id:
            errors.append(f"{label}_cohort_id_mismatch")
        for field in ("cohort_hash", "cohort_receipt_hash"):
            if str(surface.get(field) or "") != cohort_hash:
                errors.append(f"{label}_{field}_mismatch")
    if candidate is not None:
        if str(candidate.get("cohort_id") or "") != cohort_id:
            errors.append("candidate_cohort_id_mismatch")
        if str(candidate.get("cohort_hash") or "") != cohort_hash:
            errors.append("candidate_cohort_hash_mismatch")
    return sorted(set(errors))


def _production_selection_errors(
    cohort: Mapping[str, Any],
    analysis: Mapping[str, Any],
    recomputed_analysis: Mapping[str, Any],
) -> list[str]:
    """Keep post-hoc structural subsets outside the promotion boundary."""

    errors: list[str] = []
    selection = dict(cohort.get("selection_policy") or {})
    if selection.get("selection_mode") != "all_canonical_before_cutoff":
        errors.append("selection_mode_not_canonical_all_before_cutoff")
    if cohort.get("selection_integrity") != "canonical_all_before_cutoff":
        errors.append("selection_integrity_not_canonical_all")
    if cohort.get("selection_integrity_state") != "pass":
        errors.append("selection_integrity_not_pass")
    if cohort.get("selection_production_eligible") is not True:
        errors.append("selection_not_production_eligible")
    for label, surface in (
        ("analysis", analysis),
        ("recomputed_analysis", recomputed_analysis),
    ):
        if surface.get("selection_integrity") != "canonical_all_before_cutoff":
            errors.append(f"{label}_selection_integrity_not_canonical_all")
        if surface.get("selection_integrity_state") != "pass":
            errors.append(f"{label}_selection_integrity_not_pass")
        if surface.get("selection_production_eligible") is not True:
            errors.append(f"{label}_selection_not_production_eligible")
        if surface.get("production_revision_eligible") is not True:
            errors.append(f"{label}_not_production_revision_eligible")
        proposed = surface.get("proposed_revision")
        proposed = dict(proposed) if isinstance(proposed, Mapping) else {}
        if proposed.get("production_revision_eligible") is not True:
            errors.append(f"{label}_proposal_not_production_revision_eligible")
    return sorted(set(errors))


def ensure_revision_tables(store: Any) -> None:
    """Install append-only revision, verification, and promotion ledgers."""

    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS competence_revision_candidates(
            revision_candidate_id TEXT PRIMARY KEY CHECK(length(revision_candidate_id) = 64),
            candidate_hash TEXT NOT NULL CHECK(length(candidate_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            source_competence_id TEXT NOT NULL CHECK(length(source_competence_id) = 64),
            cohort_id TEXT NOT NULL CHECK(length(cohort_id) = 64),
            analysis_id TEXT NOT NULL CHECK(length(analysis_id) = 64),
            revision_type TEXT NOT NULL,
            candidate_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, candidate_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_revision_candidates_source
            ON competence_revision_candidates(repo, source_competence_id, created_at ASC);

        CREATE TABLE IF NOT EXISTS competence_revision_verifications(
            verification_receipt_hash TEXT PRIMARY KEY CHECK(length(verification_receipt_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            revision_candidate_id TEXT NOT NULL CHECK(length(revision_candidate_id) = 64),
            candidate_hash TEXT NOT NULL CHECK(length(candidate_hash) = 64),
            verification_state TEXT NOT NULL,
            verification_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, revision_candidate_id, candidate_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_revision_verifications_candidate
            ON competence_revision_verifications(repo, revision_candidate_id, created_at ASC);

        CREATE TABLE IF NOT EXISTS competence_revision_promotions(
            promotion_receipt_hash TEXT PRIMARY KEY CHECK(length(promotion_receipt_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            source_competence_id TEXT NOT NULL CHECK(length(source_competence_id) = 64),
            successor_competence_id TEXT,
            revision_candidate_id TEXT NOT NULL CHECK(length(revision_candidate_id) = 64),
            verification_receipt_hash TEXT NOT NULL CHECK(length(verification_receipt_hash) = 64),
            relationship TEXT NOT NULL,
            promotion_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, revision_candidate_id),
            UNIQUE(repository_id, source_competence_id, successor_competence_id, relationship)
        );
        CREATE INDEX IF NOT EXISTS idx_revision_promotions_source
            ON competence_revision_promotions(repo, source_competence_id, created_at ASC);

        CREATE TRIGGER IF NOT EXISTS competence_revision_candidates_no_update
        BEFORE UPDATE ON competence_revision_candidates BEGIN
            SELECT RAISE(ABORT, 'competence revision candidates cannot be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_revision_candidates_no_delete
        BEFORE DELETE ON competence_revision_candidates BEGIN
            SELECT RAISE(ABORT, 'competence revision candidates cannot be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_revision_verifications_no_update
        BEFORE UPDATE ON competence_revision_verifications BEGIN
            SELECT RAISE(ABORT, 'competence revision verifications cannot be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_revision_verifications_no_delete
        BEFORE DELETE ON competence_revision_verifications BEGIN
            SELECT RAISE(ABORT, 'competence revision verifications cannot be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_revision_promotions_no_update
        BEFORE UPDATE ON competence_revision_promotions BEGIN
            SELECT RAISE(ABORT, 'competence revision promotions cannot be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_revision_promotions_no_delete
        BEFORE DELETE ON competence_revision_promotions BEGIN
            SELECT RAISE(ABORT, 'competence revision promotions cannot be deleted');
        END;
        """
    )
    store.db.commit()


def _contradiction_additions(scope: Mapping[str, Any], cohort_id: str) -> list[dict[str, Any]]:
    return [
        {
            "kind": "verified_distributed_contradiction",
            "observation_identity": str(identity),
            "assimilation_cohort_id": str(cohort_id),
        }
        for identity in sorted(
            str(item)
            for item in scope.get("contradiction_observation_ids") or ()
            if str(item)
        )
    ]


def _derived_change_material(
    scope: Mapping[str, Any],
    dependence: Mapping[str, Any],
    cohort_id: str,
) -> dict[str, list[Any]]:
    """Derive every semantic change from canonical analysis output.

    Public callers may supply rationale, but never new failure conditions or
    uncertainty that the independently recomputed evidence did not produce.
    """

    contradictions = [
        str(item)
        for item in scope.get("contradiction_observation_ids") or ()
        if str(item)
    ]
    failures: list[Any] = []
    if contradictions:
        failures.append(
            {
                "kind": "verified_distributed_failure_scope",
                "derived_scope": str(scope.get("derived_scope") or "unresolved"),
                "observation_ids": sorted(contradictions),
                "assimilation_cohort_id": str(cohort_id),
            }
        )
    uncertainty: list[Any] = []
    unresolved = sorted(
        str(item)
        for item in dependence.get("unresolved_dependence") or ()
        if str(item)
    )
    if unresolved or str(scope.get("derived_scope") or "") == "unresolved":
        uncertainty.append(
            {
                "kind": "distributed_evidence_unresolved",
                "unresolved_observation_ids": unresolved,
                "scope_reason": str(scope.get("scope_reason") or ""),
                "assimilation_cohort_id": str(cohort_id),
            }
        )
    return {
        "failure_conditions": failures,
        "counterevidence": _contradiction_additions(scope, cohort_id),
        "uncertainty": uncertainty,
    }


def build_revision_candidate(
    store: Any,
    repo: str,
    *,
    analysis_id: str,
    proposed_failure_condition_additions: Sequence[Any] | None = None,
    proposed_uncertainty_additions: Sequence[Any] | None = None,
    public_rationale: str = "",
    persist: bool = False,
) -> dict[str, Any]:
    """Build a non-authorizing proposal from one canonical frozen analysis."""

    if not persist and bool(getattr(store.db, "in_transaction", False)):
        with _observational_store(store) as read_store:
            return build_revision_candidate(
                read_store,
                repo,
                analysis_id=analysis_id,
                proposed_failure_condition_additions=(
                    proposed_failure_condition_additions
                ),
                proposed_uncertainty_additions=proposed_uncertainty_additions,
                public_rationale=public_rationale,
                persist=False,
            )
    analysis_check = verify_assimilation_analysis(store, repo, str(analysis_id))
    if analysis_check.get("valid") is not True:
        raise CompetenceRevisionError("assimilation analysis failed canonical verification")
    analysis = dict(analysis_check.get("analysis") or {})
    recomputed = analyze_evidence_cohort(
        store, repo, str(analysis.get("cohort_id") or ""), persist=False
    )
    for key in ("counts", "dependence", "diversity", "scope", "evidence_roots"):
        if analysis.get(key) != recomputed.get(key):
            raise CompetenceRevisionError(f"analysis recomputation mismatch: {key}")
    cohort_check = verify_evidence_cohort(
        store, repo, str(analysis.get("cohort_id") or "")
    )
    if cohort_check.get("valid") is not True:
        raise CompetenceRevisionError("assimilation cohort failed canonical verification")
    cohort = dict(cohort_check.get("cohort") or {})
    source_id = str(analysis.get("competence_id") or "")
    source = get_competence_candidate(store, repo, source_id)
    source_check = verify_competence_candidate(store, repo, source_id)
    if source is None or source_check.get("valid") is not True:
        raise CompetenceRevisionError("source competence failed canonical verification")
    binding_errors = _canonical_source_binding_errors(
        source=source,
        cohort=cohort,
        analysis=analysis,
        recomputed_analysis=recomputed,
    )
    if binding_errors:
        raise CompetenceRevisionError(
            "assimilation evidence belongs to a different source competence: "
            + ",".join(binding_errors)
        )
    scope = dict(recomputed.get("scope") or {})
    revision_type = str(scope.get("proposed_revision_type") or "unresolved")
    if revision_type not in REVISION_TYPES:
        revision_type = "unresolved"
    if revision_type == "broaden_applicability_candidate":
        # The v9.5 assimilation classifier intentionally never infers
        # broadening from a clean failure record.  Positive controlled evidence
        # needs a future, separately declared law.
        raise CompetenceRevisionError(
            "applicability broadening lacks independently derived positive proof"
        )
    if proposed_failure_condition_additions or proposed_uncertainty_additions:
        raise CompetenceRevisionError(
            "semantic revision changes are derived from canonical evidence, not caller input"
        )
    derived_changes = _derived_change_material(
        scope,
        dict(recomputed.get("dependence") or {}),
        str(cohort.get("cohort_id") or ""),
    )
    parent_counterevidence = list(source.get("counterevidence") or ())
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "repo": repo,
        "repository_id": _repo_identity(store, repo),
        "source_competence_id": source_id,
        "source_competence_receipt_hash": source.get("receipt_hash"),
        "source_counterevidence_hashes": sorted(
            _sha(item) for item in parent_counterevidence
        ),
        "cohort_id": cohort.get("cohort_id"),
        "cohort_hash": cohort.get("cohort_hash"),
        "selection_integrity": cohort.get("selection_integrity"),
        "selection_integrity_state": cohort.get("selection_integrity_state"),
        "selection_production_eligible": cohort.get(
            "selection_production_eligible"
        ),
        "analysis_production_revision_eligible": analysis.get(
            "production_revision_eligible"
        ),
        "analysis_id": analysis.get("analysis_id"),
        "analysis_hash": analysis.get("analysis_hash"),
        "evidence_roots": list(recomputed.get("evidence_roots") or ()),
        "dependence_analysis": dict(recomputed.get("dependence") or {}),
        "diversity_analysis": dict(recomputed.get("diversity") or {}),
        "scope_classification": scope,
        "causal_strength_class": recomputed.get("causal_strength_class"),
        "proposed_revision_type": revision_type,
        "proposed_applicability_change": dict(
            scope.get("proposed_applicability_change") or {}
        ),
        "proposed_failure_condition_additions": derived_changes[
            "failure_conditions"
        ],
        "proposed_counterevidence_additions": derived_changes[
            "counterevidence"
        ],
        "proposed_counterevidence_removals": [],
        "proposed_uncertainty_additions": derived_changes["uncertainty"],
        "public_rationale": str(public_rationale or scope.get("scope_reason") or ""),
        "verification_state": "pending_independent_verification",
        "self_verification_authorizing": False,
        "counterevidence_conserved": True,
        "causal_effect_established": False,
        "successor_created": False,
        "promotion_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        **AUTHORITY_FALSE,
    }
    candidate_hash = _sha(material)
    body = {
        **material,
        "revision_candidate_id": candidate_hash,
        "candidate_hash": candidate_hash,
        "created_at": time.time(),
    }
    if not persist:
        return {**body, "persisted": False}
    return persist_revision_candidate(store, repo, body)


def persist_revision_candidate(
    store: Any, repo: str, candidate: Mapping[str, Any]
) -> dict[str, Any]:
    """Append one immutable proposal after structural and canonical binding checks."""

    ensure_revision_tables(store)
    body = dict(candidate)
    material = _without_runtime(
        body, "revision_candidate_id", "candidate_hash", "persisted"
    )
    expected = _sha(material)
    if str(body.get("revision_candidate_id") or "") != expected:
        raise CompetenceRevisionError("revision candidate identity is invalid")
    if str(body.get("candidate_hash") or "") != expected:
        raise CompetenceRevisionError("revision candidate hash is invalid")
    if str(body.get("repo") or "") != repo or str(
        body.get("repository_id") or ""
    ) != _repo_identity(store, repo):
        raise CompetenceRevisionError("revision candidate repository binding is invalid")
    if str(body.get("proposed_revision_type") or "") not in REVISION_TYPES:
        raise CompetenceRevisionError("revision type is invalid")
    if body.get("proposed_counterevidence_removals"):
        raise CompetenceRevisionError("revision candidate cannot remove counterevidence")
    if str(body.get("proposed_revision_type")) == "broaden_applicability_candidate":
        raise CompetenceRevisionError("unsupported applicability broadening")
    for field in AUTHORITY_FIELDS:
        if body.get(field) is not False:
            raise CompetenceRevisionError(f"revision candidate authority flag is open: {field}")
    analysis_check = verify_assimilation_analysis(
        store, repo, str(body.get("analysis_id") or "")
    )
    if analysis_check.get("valid") is not True:
        raise CompetenceRevisionError("candidate analysis binding is invalid")
    analysis = dict(analysis_check.get("analysis") or {})
    if str(analysis.get("analysis_hash") or "") != str(body.get("analysis_hash") or ""):
        raise CompetenceRevisionError("candidate analysis hash binding is invalid")
    preflight = _verify_candidate_body(
        store,
        repo,
        body,
        require_production_selection=False,
    )
    if preflight.get("valid") is not True:
        raise CompetenceRevisionError(
            "revision candidate is not independently reproducible: "
            + ",".join(str(item) for item in preflight.get("errors") or ())
        )
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT candidate_json, candidate_hash FROM competence_revision_candidates WHERE repository_id=? AND revision_candidate_id=?",
            (str(body["repository_id"]), expected),
        ).fetchone()
        if existing is not None:
            if str(existing["candidate_hash"]) != expected:
                raise CompetenceRevisionError("revision identity has conflicting content")
            return {**(_json(existing["candidate_json"]) or body), "inserted": False, "duplicate": True}
        conn.execute(
            """INSERT INTO competence_revision_candidates(
                revision_candidate_id, candidate_hash, repository_id, repo,
                source_competence_id, cohort_id, analysis_id, revision_type,
                candidate_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                expected,
                expected,
                body["repository_id"],
                repo,
                body["source_competence_id"],
                body["cohort_id"],
                body["analysis_id"],
                body["proposed_revision_type"],
                _canonical(body),
                float(body.get("created_at") or time.time()),
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def get_revision_candidate(
    store: Any, repo: str, revision_candidate_id: str
) -> dict[str, Any] | None:
    if not _revision_table_present(store, "competence_revision_candidates"):
        return None
    row = store.db.execute(
        "SELECT candidate_hash, candidate_json FROM competence_revision_candidates WHERE repository_id=? AND repo=? AND revision_candidate_id=?",
        (_repo_identity(store, repo), repo, str(revision_candidate_id)),
    ).fetchone()
    if row is None:
        return None
    body = _json(row["candidate_json"])
    if body is not None:
        body["ledger_hash"] = str(row["candidate_hash"])
    return body


def _verify_candidate_body(
    store: Any,
    repo: str,
    candidate: Mapping[str, Any],
    *,
    require_production_selection: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    material = _without_runtime(
        candidate, "revision_candidate_id", "candidate_hash", "persisted"
    )
    expected_hash = _sha(material)
    candidate_id = str(candidate.get("revision_candidate_id") or "")
    if candidate_id != expected_hash or str(candidate.get("candidate_hash") or "") != expected_hash:
        errors.append("candidate_hash_invalid")
    if candidate.get("ledger_hash") not in {None, expected_hash}:
        errors.append("candidate_ledger_hash_invalid")
    source_id = str(candidate.get("source_competence_id") or "")
    source = get_competence_candidate(store, repo, source_id)
    source_check = verify_competence_candidate(store, repo, source_id)
    if source is None or source_check.get("valid") is not True:
        errors.append("source_competence_invalid")
    elif str(source.get("receipt_hash") or "") != str(
        candidate.get("source_competence_receipt_hash") or ""
    ):
        errors.append("source_competence_receipt_mismatch")
    cohort_id = str(candidate.get("cohort_id") or "")
    cohort_check = verify_evidence_cohort(store, repo, cohort_id)
    if cohort_check.get("valid") is not True:
        errors.append("cohort_invalid")
        cohort = {}
    else:
        cohort = dict(cohort_check.get("cohort") or {})
        if str(cohort.get("cohort_hash") or "") != str(candidate.get("cohort_hash") or ""):
            errors.append("cohort_hash_mismatch")
    analysis_id = str(candidate.get("analysis_id") or "")
    analysis_check = verify_assimilation_analysis(store, repo, analysis_id)
    if analysis_check.get("valid") is not True:
        errors.append("analysis_invalid")
        analysis = {}
        recomputed = {}
    else:
        analysis = dict(analysis_check.get("analysis") or {})
        # This is the independent edge: rebuild from the frozen cohort rather
        # than accepting the analysis or candidate's cached assertions.
        recomputed = analyze_evidence_cohort(store, repo, cohort_id, persist=False)
        if str(analysis.get("analysis_hash") or "") != str(candidate.get("analysis_hash") or ""):
            errors.append("analysis_hash_mismatch")
        for key in ("counts", "dependence", "diversity", "scope", "evidence_roots"):
            if analysis.get(key) != recomputed.get(key):
                errors.append(f"analysis_{key}_not_independently_recomputed")
    if source is not None:
        errors.extend(
            _canonical_source_binding_errors(
                source=source,
                cohort=cohort,
                analysis=analysis,
                recomputed_analysis=recomputed,
                candidate=candidate,
            )
        )
    for field in (
        "selection_integrity",
        "selection_integrity_state",
        "selection_production_eligible",
    ):
        if candidate.get(field) != cohort.get(field):
            errors.append(f"candidate_{field}_mismatch")
        if candidate.get(field) != analysis.get(field):
            errors.append(f"candidate_{field}_analysis_mismatch")
    if candidate.get("analysis_production_revision_eligible") != analysis.get(
        "production_revision_eligible"
    ):
        errors.append("candidate_analysis_production_revision_eligible_mismatch")
    selection_errors = _production_selection_errors(
        cohort, analysis, recomputed
    )
    if require_production_selection:
        errors.extend(selection_errors)
    scope = dict(recomputed.get("scope") or {})
    if dict(candidate.get("scope_classification") or {}) != scope:
        errors.append("scope_classification_mismatch")
    derived_type = str(scope.get("proposed_revision_type") or "unresolved")
    revision_type = str(candidate.get("proposed_revision_type") or "")
    if revision_type != derived_type:
        errors.append("revision_type_not_independently_derived")
    if dict(candidate.get("proposed_applicability_change") or {}) != dict(
        scope.get("proposed_applicability_change") or {}
    ):
        errors.append("applicability_change_not_independently_derived")
    if revision_type in {"narrow_applicability", "specialize"}:
        try:
            _applicability_surfaces(candidate, "0" * 64)
        except CompetenceRevisionError as exc:
            errors.append(f"applicability_change_invalid:{exc}")
    if list(candidate.get("evidence_roots") or ()) != list(
        recomputed.get("evidence_roots") or ()
    ):
        errors.append("evidence_roots_mismatch")
    required_contradictions = {
        str(item) for item in scope.get("contradiction_observation_ids") or ()
    }
    supplied_contradictions = {
        str(item.get("observation_identity") or "")
        for item in candidate.get("proposed_counterevidence_additions") or ()
        if isinstance(item, Mapping)
    }
    if not required_contradictions.issubset(supplied_contradictions):
        errors.append("counterevidence_additions_incomplete")
    expected_changes = _derived_change_material(
        scope,
        dict(recomputed.get("dependence") or {}),
        cohort_id,
    )
    if list(candidate.get("proposed_failure_condition_additions") or ()) != list(
        expected_changes["failure_conditions"]
    ):
        errors.append("failure_condition_changes_not_independently_derived")
    if list(candidate.get("proposed_counterevidence_additions") or ()) != list(
        expected_changes["counterevidence"]
    ):
        errors.append("counterevidence_changes_not_independently_derived")
    if list(candidate.get("proposed_uncertainty_additions") or ()) != list(
        expected_changes["uncertainty"]
    ):
        errors.append("uncertainty_changes_not_independently_derived")
    if candidate.get("proposed_counterevidence_removals"):
        errors.append("counterevidence_removal_forbidden")
    parent_hashes = sorted(
        _sha(item) for item in (source or {}).get("counterevidence") or ()
    )
    if list(candidate.get("source_counterevidence_hashes") or ()) != parent_hashes:
        errors.append("parent_counterevidence_binding_invalid")
    if candidate.get("counterevidence_conserved") is not True:
        errors.append("counterevidence_conservation_not_declared")
    if revision_type == "broaden_applicability_candidate":
        errors.append("broadening_without_positive_controlled_evidence")
    if candidate.get("causal_effect_established") is not False:
        errors.append("observational_evidence_causal_claim_invalid")
    # Self-asserted state is never an input to validity.  A candidate may only
    # be pending; a separate canonical receipt below supplies verification.
    if str(candidate.get("verification_state") or "") != "pending_independent_verification":
        errors.append("candidate_self_verification_forbidden")
    if candidate.get("self_verification_authorizing") is not False:
        errors.append("candidate_self_verification_authorizing")
    if candidate.get("promotion_authorized") is not False:
        errors.append("candidate_self_promotion_authorizing")
    if candidate.get("successor_created") is not False:
        errors.append("candidate_self_successor_claim")
    for field in AUTHORITY_FIELDS:
        if candidate.get(field) is not False:
            errors.append(f"authority_flag_open:{field}")
    return {
        "valid": not errors,
        "state": "pass" if not errors else "fail",
        "errors": sorted(set(errors)),
        "candidate_id": candidate_id,
        "candidate_hash": expected_hash,
        "source": source,
        "cohort": cohort,
        "analysis": analysis,
        "recomputed_analysis": recomputed,
        "selection_errors": selection_errors,
    }


def verify_revision_candidate(
    store: Any,
    repo: str,
    revision_candidate_id: str,
    *,
    persist: bool = False,
) -> dict[str, Any]:
    """Independently verify a canonical revision proposal; read-only by default."""

    if not persist and bool(getattr(store.db, "in_transaction", False)):
        with _observational_store(store) as read_store:
            return verify_revision_candidate(
                read_store,
                repo,
                revision_candidate_id,
                persist=False,
            )
    candidate = get_revision_candidate(store, repo, str(revision_candidate_id))
    if candidate is None:
        return {
            "valid": False,
            "state": "unknown",
            "errors": ["revision_candidate_missing"],
            "persisted": False,
            **AUTHORITY_FALSE,
        }
    check = _verify_candidate_body(store, repo, candidate)
    material = {
        "schema_version": VERIFICATION_SCHEMA,
        "version": VERSION,
        "repo": repo,
        "repository_id": _repo_identity(store, repo),
        "revision_candidate_id": revision_candidate_id,
        "candidate_hash": candidate.get("candidate_hash"),
        "source_competence_id": candidate.get("source_competence_id"),
        "cohort_id": candidate.get("cohort_id"),
        "cohort_hash": candidate.get("cohort_hash"),
        "analysis_id": candidate.get("analysis_id"),
        "analysis_hash": candidate.get("analysis_hash"),
        "verifier": "cortex.competence_revision.independent_recompute",
        "verifier_version": VERSION,
        "verification_state": check["state"],
        "valid": bool(check["valid"]),
        "errors": list(check["errors"]),
        "recomputed_scope": dict(
            (check.get("recomputed_analysis") or {}).get("scope") or {}
        ),
        "recomputed_evidence_roots": list(
            (check.get("recomputed_analysis") or {}).get("evidence_roots") or ()
        ),
        "counterevidence_conserved": "counterevidence_additions_incomplete"
        not in check["errors"]
        and "counterevidence_removal_forbidden" not in check["errors"]
        and "parent_counterevidence_binding_invalid" not in check["errors"],
        "self_assertion_used": False,
        "promotion_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        **AUTHORITY_FALSE,
    }
    receipt_hash = _sha(material)
    body = {
        **material,
        "verification_receipt_hash": receipt_hash,
        "created_at": time.time(),
    }
    if not persist:
        return {**body, "persisted": False}
    ensure_revision_tables(store)
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT verification_json FROM competence_revision_verifications WHERE repository_id=? AND verification_receipt_hash=?",
            (body["repository_id"], receipt_hash),
        ).fetchone()
        if existing is not None:
            return {**(_json(existing["verification_json"]) or body), "inserted": False, "duplicate": True}
        conn.execute(
            """INSERT INTO competence_revision_verifications(
                verification_receipt_hash, repository_id, repo,
                revision_candidate_id, candidate_hash, verification_state,
                verification_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                receipt_hash,
                body["repository_id"],
                repo,
                revision_candidate_id,
                body["candidate_hash"],
                body["verification_state"],
                _canonical(body),
                body["created_at"],
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def get_revision_verification(
    store: Any, repo: str, verification_receipt_hash: str
) -> dict[str, Any] | None:
    if not _revision_table_present(store, "competence_revision_verifications"):
        return None
    row = store.db.execute(
        "SELECT verification_json FROM competence_revision_verifications WHERE repository_id=? AND repo=? AND verification_receipt_hash=?",
        (_repo_identity(store, repo), repo, str(verification_receipt_hash)),
    ).fetchone()
    return _json(row["verification_json"]) if row is not None else None


def _applicability_surfaces(
    candidate: Mapping[str, Any], verification_hash: str
) -> dict[str, Any]:
    """Translate derived scope keys into target-enforceable typed constraints."""

    change = dict(candidate.get("proposed_applicability_change") or {})
    evidence_binding = {
        "cohort_id": candidate.get("cohort_id"),
        "cohort_hash": candidate.get("cohort_hash"),
        "analysis_id": candidate.get("analysis_id"),
        "analysis_hash": candidate.get("analysis_hash"),
    }
    exclusion_keys = {
        "exclude_target_ids": "target_id",
        "exclude_target_classes": "target_class",
        "exclude_environment_hashes": "environment_fingerprint",
        "exclude_model_families": "model_family",
    }
    axis_dimensions = {
        "target_id": "target_id",
        "target_class": "target_class",
        "environment_hash": "environment_fingerprint",
        "model_family": "model_family",
    }
    specialization_keys = {
        "target_id": (
            "supported_target_ids",
            "contradicted_target_ids",
            "target_id",
        ),
        "target_class": (
            "supported_target_classes",
            "contradicted_target_classes",
            "target_class",
        ),
        "environment_hash": (
            "supported_environment_hashes",
            "contradicted_environment_hashes",
            "environment_fingerprint",
        ),
        "model_family": (
            "supported_model_families",
            "contradicted_model_families",
            "model_family",
        ),
    }
    exclusions: list[dict[str, Any]] = []
    constraints: list[dict[str, Any]] = []
    for key, dimension in exclusion_keys.items():
        values = sorted(
            {
                str(value)
                for value in (change.get(key) or ())
                if str(value or "")
            }
        )
        if not values:
            continue
        basis = (
            "independently_verified_contradiction"
            if key == "contradicted_environment_hashes"
            else "independently_verified_scope_exception"
        )
        exclusions.append(
            {
                "dimension": dimension,
                "excluded_values": values,
                "source_change_key": key,
                "reason": basis,
                **evidence_binding,
            }
        )
        constraints.append(
            {
                "dimension": dimension,
                "operator": "exclude",
                "values": values,
                "source_change_key": key,
                "evidence_basis": basis,
                **evidence_binding,
            }
        )
    revision_type = str(candidate.get("proposed_revision_type") or "")
    if revision_type == "specialize":
        discriminator = dict(
            (candidate.get("scope_classification") or {}).get("discriminator")
            or {}
        )
        axis = str(discriminator.get("axis") or "")
        key_spec = specialization_keys.get(axis)
        dimension = axis_dimensions.get(axis)
        if key_spec is None or dimension is None or discriminator.get("state") != "pass":
            raise CompetenceRevisionError(
                "specialization discriminator is not canonically resolved"
            )
        supported_key, contradicted_key, dimension = key_spec
        supported_values = sorted(
            {
                str(value)
                for value in (change.get(supported_key) or ())
                if str(value or "")
            }
        )
        contradicted_values = sorted(
            {
                str(value)
                for value in (change.get(contradicted_key) or ())
                if str(value or "")
            }
        )
        if not supported_values or not contradicted_values:
            raise CompetenceRevisionError(
                "specialization requires nonempty supported and contradicted values"
            )
        if set(supported_values) & set(contradicted_values):
            raise CompetenceRevisionError(
                "specialization supported and contradicted values overlap"
            )
        if supported_values != sorted(
            str(value) for value in discriminator.get("supported_values") or ()
        ) or contradicted_values != sorted(
            str(value) for value in discriminator.get("contradicted_values") or ()
        ):
            raise CompetenceRevisionError(
                "specialization change does not match its canonical discriminator"
            )
        binding = {
            "dimension": dimension,
            "source_change_key": contradicted_key,
            **evidence_binding,
        }
        exclusions.append(
            {
                **binding,
                "excluded_values": contradicted_values,
                "reason": "independently_verified_contradiction",
            }
        )
        constraints.extend(
            [
                {
                    "dimension": dimension,
                    "operator": "allow_only",
                    "values": supported_values,
                    "source_change_key": supported_key,
                    "evidence_basis": "independently_verified_support",
                    **evidence_binding,
                },
                {
                    **binding,
                    "operator": "exclude",
                    "values": contradicted_values,
                    "evidence_basis": "independently_verified_contradiction",
                },
            ]
        )
    exclusions.sort(key=lambda item: (item["dimension"], item["source_change_key"]))
    constraints.sort(
        key=lambda item: (
            item["dimension"],
            item["operator"],
            item["source_change_key"],
        )
    )
    if revision_type == "narrow_applicability" and not exclusions:
        raise CompetenceRevisionError(
            "narrowing requires at least one typed applicability exclusion"
        )
    mode = "specialization" if revision_type == "specialize" else "narrowing"
    semantic_revision = {
        "mode": mode,
        "derived_scope": (candidate.get("scope_classification") or {}).get(
            "derived_scope"
        ),
        "exclusions": [
            {
                "dimension": item["dimension"],
                "excluded_values": item["excluded_values"],
            }
            for item in exclusions
        ],
        "constraints": [
            {
                "dimension": item["dimension"],
                "operator": item["operator"],
                "values": item["values"],
            }
            for item in constraints
        ],
    }
    revision = {
        "schema_version": APPLICABILITY_REVISION_SCHEMA,
        "mode": mode,
        "derived_scope": semantic_revision["derived_scope"],
        "scope_reason": (candidate.get("scope_classification") or {}).get(
            "scope_reason"
        ),
        "source_competence_id": candidate.get("source_competence_id"),
        "source_competence_receipt_hash": candidate.get(
            "source_competence_receipt_hash"
        ),
        "revision_candidate_id": candidate.get("revision_candidate_id"),
        "candidate_hash": candidate.get("candidate_hash"),
        "verification_receipt_hash": verification_hash,
        **evidence_binding,
        "exclusions_hash": _sha(exclusions),
        "constraints_hash": _sha(constraints),
    }
    return {
        "semantic_revision": semantic_revision,
        "applicability_exclusions": exclusions,
        "applicability_constraints": constraints,
        "applicability_revision": revision,
    }


def _successor_body(
    parent: Mapping[str, Any],
    candidate: Mapping[str, Any],
    verification_hash: str,
    promotion_freshness: Mapping[str, Any],
    *,
    created_at: float,
) -> dict[str, Any]:
    revision_type = str(candidate.get("proposed_revision_type") or "")
    if revision_type not in SUCCESSOR_TYPES:
        raise CompetenceRevisionError("revision type does not create a successor competence")
    applicability = list(parent.get("applicability_conditions") or ())
    change = dict(candidate.get("proposed_applicability_change") or {})
    applicability_surfaces = _applicability_surfaces(candidate, verification_hash)
    applicability_exclusions = _stable_union(
        parent.get("applicability_exclusions") or (),
        applicability_surfaces["applicability_exclusions"],
    )
    applicability_constraints = _stable_union(
        parent.get("applicability_constraints") or (),
        applicability_surfaces["applicability_constraints"],
    )
    if change:
        applicability = _stable_union(
            applicability,
            [
                {
                    "v9.5_scope_revision": applicability_surfaces[
                        "semantic_revision"
                    ]
                }
            ],
        )
    failure_conditions = _stable_union(
        parent.get("failure_conditions") or (),
        candidate.get("proposed_failure_condition_additions") or (),
    )
    counterevidence = _stable_union(
        parent.get("counterevidence") or (),
        candidate.get("proposed_counterevidence_additions") or (),
    )
    uncertainty = _stable_union(
        parent.get("uncertainty") or (),
        candidate.get("proposed_uncertainty_additions") or (),
    )
    semantic = semantic_material(
        candidate_type=str(parent.get("candidate_type") or ""),
        capability=parent.get("capability"),
        intended_outcome=parent.get("intended_outcome"),
        prerequisites=parent.get("prerequisites"),
        applicability_conditions=applicability,
        environmental_assumptions=parent.get("environmental_assumptions"),
        required_tools=parent.get("required_tools"),
        failure_conditions=failure_conditions,
    )
    successor_id = _sha(semantic)
    parent_id = str(parent.get("competence_id") or "")
    if successor_id == parent_id:
        raise CompetenceRevisionError(
            "revision does not change semantic competence identity; use an annotation event"
        )
    body = {
        key: value
        for key, value in parent.items()
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
    body.update(
        {
            "schema_version": SUCCESSOR_SCHEMA,
            "version": VERSION,
            "competence_id": successor_id,
            "semantic_identity_hash": successor_id,
            "applicability_conditions": applicability,
            "applicability_exclusions": applicability_exclusions,
            "applicability_constraints": applicability_constraints,
            "applicability_revision": applicability_surfaces[
                "applicability_revision"
            ],
            "revision_evidence_freshness": dict(promotion_freshness),
            "failure_conditions": failure_conditions,
            "counterevidence": counterevidence,
            "uncertainty": uncertainty,
            "revision_state": "transfer_pending",
            "portability_status": "pending_transfer_verification",
            "counterevidence_conserved": True,
            "revision_lineage": {
                "source_competence_id": parent_id,
                "source_competence_receipt_hash": parent.get("receipt_hash"),
                "revision_candidate_id": candidate.get("revision_candidate_id"),
                "candidate_hash": candidate.get("candidate_hash"),
                "assimilation_cohort_id": candidate.get("cohort_id"),
                "assimilation_cohort_hash": candidate.get("cohort_hash"),
                "assimilation_analysis_id": candidate.get("analysis_id"),
                "assimilation_analysis_hash": candidate.get("analysis_hash"),
                "revision_verification_receipt_hash": verification_hash,
                "evidence_cutoff": promotion_freshness.get("evidence_cutoff"),
                "evidence_expiry_at": promotion_freshness.get(
                    "evidence_expiry_at"
                ),
                "promotion_freshness_proof_hash": promotion_freshness.get(
                    "proof_hash"
                ),
                "relationship": RELATION_BY_TYPE[revision_type],
            },
            "distribution_authorized": False,
            "memory_admission_authorized": False,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "policy_effect": False,
            "update_authorized": False,
            "advisory_only": True,
            **{field: False for field in AUTHORITY_FIELDS},
        }
    )
    if str(body.get("revision_state")) not in LIFECYCLE_STATES or str(
        body.get("portability_status")
    ) not in PORTABILITY_STATES:
        raise CompetenceRevisionError("successor lifecycle is invalid")
    body["receipt_hash"] = _competence_body_hash(body)
    body["created_at"] = float(created_at)
    return body


def _promotion_freshness_proof(
    store: Any,
    repo: str,
    candidate: Mapping[str, Any],
    *,
    checked_at: float,
) -> dict[str, Any]:
    """Re-evaluate every contributing observation at promotion time.

    Cohort validity remains a historical proposition at ``evidence_cutoff``.
    This separate proof asks whether the exact package uses and feedback are
    *still* current under each frozen target policy when promotion is
    requested.  A delayed operator therefore cannot turn expired evidence
    into fresh successor applicability.
    """

    cohort_id = str(candidate.get("cohort_id") or "")
    cohort = get_evidence_cohort(store, repo, cohort_id)
    errors: list[str] = []
    unknown: list[str] = []
    observation_proofs: list[dict[str, Any]] = []
    expiries: list[float] = []
    if cohort is None:
        unknown.append("promotion_freshness_cohort_missing")
    else:
        if str(cohort.get("cohort_hash") or "") != str(
            candidate.get("cohort_hash") or ""
        ):
            errors.append("promotion_freshness_cohort_hash_mismatch")
        contributors = [
            dict(item)
            for item in cohort.get("observations") or ()
            if isinstance(item, Mapping)
            and item.get("empirically_eligible") is True
            and item.get("duplicate_observation") is not True
        ]
        if not contributors:
            unknown.append("promotion_freshness_no_empirical_observations")
        for frozen in sorted(
            contributors,
            key=lambda item: str(item.get("observation_identity") or ""),
        ):
            feedback_id = str(frozen.get("feedback_id") or "")
            current = resolve_feedback_observation(
                store,
                repo,
                feedback_id,
                competence_id=str(candidate.get("source_competence_id") or ""),
                as_of=float(checked_at),
                _ignore_revision_candidate_id=str(
                    candidate.get("revision_candidate_id") or ""
                ),
            )
            identity = str(frozen.get("observation_identity") or "")
            current_identity = str(current.get("observation_identity") or "")
            currentness = dict(current.get("feedback_currentness") or {})
            planes = dict(currentness.get("freshness_planes") or {})
            plane_expiries = [
                float(plane.get("expires_at") or 0.0)
                for plane in planes.values()
                if isinstance(plane, Mapping)
                and float(plane.get("expires_at") or 0.0) > 0
            ]
            observation_expiry = min(plane_expiries) if plane_expiries else None
            if observation_expiry is not None:
                expiries.append(observation_expiry)
            observation_errors: list[str] = []
            if identity != current_identity:
                observation_errors.append("observation_identity_changed")
            if current.get("empirically_eligible") is not True:
                observation_errors.append("observation_not_currently_empirically_eligible")
            if str(currentness.get("state") or "unknown") != "pass":
                observation_errors.append("distribution_evidence_not_current")
                observation_errors.extend(
                    f"currentness:{item}"
                    for item in list(currentness.get("errors") or ())
                    + list(currentness.get("unknown") or ())
                )
            if current.get("outcome_success") != frozen.get("outcome_success"):
                observation_errors.append("canonical_outcome_changed")
            if dict(current.get("binding_roots") or {}) != dict(
                frozen.get("binding_roots") or {}
            ):
                observation_errors.append("canonical_binding_roots_changed")
            if observation_expiry is None:
                observation_errors.append("promotion_evidence_expiry_unknown")
            elif float(checked_at) > observation_expiry:
                observation_errors.append("promotion_evidence_expired")
            if observation_errors:
                if any("unknown" in item for item in observation_errors):
                    unknown.extend(observation_errors)
                else:
                    errors.extend(observation_errors)
            observation_proofs.append(
                {
                    "observation_identity": identity,
                    "feedback_id": feedback_id,
                    "feedback_created_at": current.get("feedback_created_at"),
                    "package_use_receipt_hash": current.get(
                        "package_use_receipt_hash"
                    ),
                    "package_use_created_at": current.get(
                        "package_use_created_at"
                    ),
                    "profile_id": current.get("profile_id"),
                    "profile_hash": current.get("profile_hash"),
                    "evidence_class": current.get("evidence_class"),
                    "outcome_success": current.get("outcome_success"),
                    "binding_roots": dict(current.get("binding_roots") or {}),
                    "freshness_planes": planes,
                    "expires_at": observation_expiry,
                    "state": (
                        "pass"
                        if not observation_errors
                        else "unknown"
                        if any("unknown" in item for item in observation_errors)
                        else "fail"
                    ),
                    "errors": sorted(set(observation_errors)),
                }
            )
    state = "fail" if errors else "unknown" if unknown else "pass"
    material = {
        "schema_version": "cortex-promotion-evidence-freshness/1.0",
        "repo": repo,
        "repository_id": _repo_identity(store, repo),
        "revision_candidate_id": candidate.get("revision_candidate_id"),
        "candidate_hash": candidate.get("candidate_hash"),
        "cohort_id": cohort_id,
        "cohort_hash": candidate.get("cohort_hash"),
        "evidence_cutoff": (cohort or {}).get("evidence_cutoff"),
        "checked_at": float(checked_at),
        "evidence_expiry_at": min(expiries) if expiries else None,
        "observation_proofs": observation_proofs,
        "state": state,
        "valid": state == "pass",
        "errors": sorted(set(errors)),
        "unknown": sorted(set(unknown)),
        "historical_cohort_remains_inspectable": True,
        "currentness_recomputed_for_promotion": True,
        "freshness_authority": "frozen_target_policy",
        **AUTHORITY_FALSE,
    }
    return {**material, "proof_hash": _sha(material)}


def _validate_successor(store: Any, repo: str, successor: Mapping[str, Any]) -> None:
    if _competence_body_hash(successor) != str(successor.get("receipt_hash") or ""):
        raise CompetenceRevisionError("successor receipt hash is invalid")
    lineage_valid, lineage_errors = _lineage_check(store, repo, successor)
    if not lineage_valid:
        raise CompetenceRevisionError(
            "successor origin lineage invalid: " + ",".join(lineage_errors)
        )
    for field in AUTHORITY_FIELDS:
        if successor.get(field) is not False:
            raise CompetenceRevisionError(f"successor authority flag is open: {field}")
    parent_hashes = {
        _sha(item)
        for item in (
            get_competence_candidate(
                store,
                repo,
                str((successor.get("revision_lineage") or {}).get("source_competence_id") or ""),
            )
            or {}
        ).get("counterevidence", ())
    }
    successor_hashes = {_sha(item) for item in successor.get("counterevidence") or ()}
    if not parent_hashes.issubset(successor_hashes):
        raise CompetenceRevisionError("successor dropped parent counterevidence")


def promote_revision_candidate(
    store: Any,
    repo: str,
    revision_candidate_id: str,
    *,
    verification_receipt_hash: str,
    promotion_reason: str,
    persist: bool = False,
) -> dict[str, Any]:
    """Explicitly promote a separately verified revision; never automatic."""

    if not persist and bool(getattr(store.db, "in_transaction", False)):
        with _observational_store(store) as read_store:
            return promote_revision_candidate(
                read_store,
                repo,
                revision_candidate_id,
                verification_receipt_hash=verification_receipt_hash,
                promotion_reason=promotion_reason,
                persist=False,
            )
    if persist:
        ensure_revision_tables(store)
    if not str(promotion_reason or "").strip():
        raise CompetenceRevisionError("explicit promotion reason is required")
    candidate = get_revision_candidate(store, repo, revision_candidate_id)
    verification = get_revision_verification(
        store, repo, str(verification_receipt_hash)
    )
    if candidate is None or verification is None:
        raise CompetenceRevisionError("canonical candidate/verification missing")
    # Re-run the independent verifier at the promotion boundary.  The stored
    # receipt is necessary but not sufficient.
    current = verify_revision_candidate(
        store, repo, revision_candidate_id, persist=False
    )
    if verification.get("valid") is not True or current.get("valid") is not True:
        raise CompetenceRevisionError("revision verification is not passing")
    if str(verification.get("revision_candidate_id") or "") != str(
        revision_candidate_id
    ) or str(verification.get("candidate_hash") or "") != str(
        candidate.get("candidate_hash") or ""
    ):
        raise CompetenceRevisionError("verification does not bind this candidate")
    canonical_verification_material = _without_runtime(
        verification, "verification_receipt_hash"
    )
    if _sha(canonical_verification_material) != str(verification_receipt_hash):
        raise CompetenceRevisionError("verification receipt identity is invalid")
    revision_type = str(candidate.get("proposed_revision_type") or "")
    if revision_type in {"unresolved", "broaden_applicability_candidate"}:
        raise CompetenceRevisionError("revision type is not promotable")
    parent = get_competence_candidate(
        store, repo, str(candidate.get("source_competence_id") or "")
    )
    if parent is None:
        raise CompetenceRevisionError("source competence missing")
    promotion_time = time.time()
    promotion_freshness = _promotion_freshness_proof(
        store,
        repo,
        candidate,
        checked_at=promotion_time,
    )
    if promotion_freshness.get("valid") is not True:
        reasons = list(promotion_freshness.get("errors") or ()) + list(
            promotion_freshness.get("unknown") or ()
        )
        raise CompetenceRevisionError(
            "promotion evidence is no longer current: "
            + ",".join(str(item) for item in reasons)
        )
    successor = (
        _successor_body(
            parent,
            candidate,
            verification_receipt_hash,
            promotion_freshness,
            created_at=promotion_time,
        )
        if revision_type in SUCCESSOR_TYPES
        else None
    )
    if successor is not None:
        _validate_successor(store, repo, successor)
    relationship = RELATION_BY_TYPE.get(revision_type, "challenges")
    material = {
        "schema_version": PROMOTION_SCHEMA,
        "version": VERSION,
        "repo": repo,
        "repository_id": _repo_identity(store, repo),
        "source_competence_id": candidate.get("source_competence_id"),
        "source_competence_receipt_hash": candidate.get(
            "source_competence_receipt_hash"
        ),
        "successor_competence_id": (
            successor.get("competence_id") if successor is not None else None
        ),
        "successor_competence_receipt_hash": (
            successor.get("receipt_hash") if successor is not None else None
        ),
        "revision_candidate_id": revision_candidate_id,
        "candidate_hash": candidate.get("candidate_hash"),
        "verification_receipt_hash": verification_receipt_hash,
        "cohort_id": candidate.get("cohort_id"),
        "cohort_hash": candidate.get("cohort_hash"),
        "analysis_id": candidate.get("analysis_id"),
        "analysis_hash": candidate.get("analysis_hash"),
        "promotion_evidence_freshness": promotion_freshness,
        "revision_type": revision_type,
        "relationship": relationship,
        "promotion_reason": str(promotion_reason).strip(),
        "explicit_promotion": True,
        "automatic_promotion": False,
        "parent_immutable": True,
        "counterevidence_conserved": True,
        "existing_packages_rewritten": False,
        "successor_requires_new_transfer_and_projection": successor is not None,
        "claim_boundary": CLAIM_BOUNDARY,
        **AUTHORITY_FALSE,
    }
    promotion_hash = _sha(material)
    body = {
        **material,
        "promotion_receipt_hash": promotion_hash,
        "created_at": promotion_time,
    }
    if not persist:
        return {
            **body,
            "successor": successor,
            "persisted": False,
            "commit_state": "prepared",
        }
    repository_id = str(body["repository_id"])
    # Successor + promotion are one SQLite transaction.  A crash cannot expose
    # a half-promoted successor as a committed revision.
    with store.transaction() as conn:
        existing_promotion = conn.execute(
            "SELECT promotion_json FROM competence_revision_promotions WHERE repository_id=? AND revision_candidate_id=?",
            (repository_id, revision_candidate_id),
        ).fetchone()
        if existing_promotion is not None:
            prior = _json(existing_promotion["promotion_json"]) or body
            return {
                **prior,
                "successor": successor,
                "inserted": False,
                "duplicate": True,
                "commit_state": "committed",
            }
        if successor is not None:
            successor_id = str(successor["competence_id"])
            existing_successor = conn.execute(
                "SELECT receipt_hash, candidate_json FROM competence_candidates WHERE competence_id=?",
                (successor_id,),
            ).fetchone()
            if existing_successor is not None:
                if str(existing_successor["receipt_hash"]) != str(
                    successor["receipt_hash"]
                ):
                    raise CompetenceRevisionError(
                        "successor semantic identity has conflicting content"
                    )
            else:
                conn.execute(
                    """INSERT INTO competence_candidates(
                        competence_id, receipt_hash, repository_id, repo,
                        semantic_identity_hash, state, portability_status,
                        evidence_lineage_hash, candidate_json, created_at
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        successor_id,
                        successor["receipt_hash"],
                        repository_id,
                        repo,
                        successor_id,
                        successor["revision_state"],
                        successor["portability_status"],
                        successor["evidence_lineage_hash"],
                        _canonical(successor),
                        successor["created_at"],
                    ),
                )
        conn.execute(
            """INSERT INTO competence_revision_promotions(
                promotion_receipt_hash, repository_id, repo,
                source_competence_id, successor_competence_id,
                revision_candidate_id, verification_receipt_hash,
                relationship, promotion_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                promotion_hash,
                repository_id,
                repo,
                body["source_competence_id"],
                body["successor_competence_id"],
                revision_candidate_id,
                verification_receipt_hash,
                relationship,
                _canonical(body),
                body["created_at"],
            ),
        )
    return {
        **body,
        "successor": successor,
        "inserted": True,
        "duplicate": False,
        "commit_state": "committed",
    }


def get_revision_promotion(
    store: Any, repo: str, promotion_receipt_hash: str
) -> dict[str, Any] | None:
    if not _revision_table_present(store, "competence_revision_promotions"):
        return None
    row = store.db.execute(
        "SELECT promotion_json FROM competence_revision_promotions WHERE repository_id=? AND repo=? AND promotion_receipt_hash=?",
        (_repo_identity(store, repo), repo, str(promotion_receipt_hash)),
    ).fetchone()
    return _json(row["promotion_json"]) if row is not None else None


def verify_revision_promotion(
    store: Any, repo: str, promotion_receipt_hash: str
) -> dict[str, Any]:
    """Verify a promotion, its independent proof, and successor lineage."""

    if bool(getattr(store.db, "in_transaction", False)):
        with _observational_store(store) as read_store:
            return verify_revision_promotion(
                read_store, repo, promotion_receipt_hash
            )
    if not _revision_table_present(store, "competence_revision_promotions"):
        return {
            "valid": False,
            "state": "unknown",
            "errors": ["promotion_ledger_missing"],
            **AUTHORITY_FALSE,
        }
    active = _ACTIVE_PROMOTION_VERIFICATIONS.get()
    deep_recompute = str(promotion_receipt_hash) not in active
    token = _ACTIVE_PROMOTION_VERIFICATIONS.set(
        active | {str(promotion_receipt_hash)}
    )
    try:
        return _verify_revision_promotion_body(
            store,
            repo,
            promotion_receipt_hash,
            deep_recompute=deep_recompute,
            verify_successor_competence=True,
        )
    finally:
        _ACTIVE_PROMOTION_VERIFICATIONS.reset(token)


def _verify_revision_promotion_body(
    store: Any,
    repo: str,
    promotion_receipt_hash: str,
    *,
    deep_recompute: bool,
    verify_successor_competence: bool,
) -> dict[str, Any]:
    repository_id = _repo_identity(store, repo)
    row = store.db.execute(
        "SELECT * FROM competence_revision_promotions WHERE repository_id=? AND repo=? AND promotion_receipt_hash=?",
        (repository_id, repo, str(promotion_receipt_hash)),
    ).fetchone()
    if row is None:
        return {
            "valid": False,
            "state": "unknown",
            "errors": ["promotion_missing"],
            **AUTHORITY_FALSE,
        }
    body = _json(row["promotion_json"])
    if body is None:
        return {
            "valid": False,
            "state": "fail",
            "errors": ["promotion_json_invalid"],
            **AUTHORITY_FALSE,
        }
    errors: list[str] = []
    expected_hash = _sha(
        _without_runtime(body, "promotion_receipt_hash")
    )
    if expected_hash != str(promotion_receipt_hash):
        errors.append("promotion_hash_invalid")
    indexed = {
        "repository_id": row["repository_id"],
        "repo": row["repo"],
        "source_competence_id": row["source_competence_id"],
        "successor_competence_id": row["successor_competence_id"],
        "revision_candidate_id": row["revision_candidate_id"],
        "verification_receipt_hash": row["verification_receipt_hash"],
        "relationship": row["relationship"],
    }
    for key, value in indexed.items():
        if body.get(key) != value:
            errors.append(f"promotion_{key}_index_mismatch")
    if float(row["created_at"] or 0.0) != float(body.get("created_at") or 0.0):
        errors.append("promotion_created_at_index_mismatch")
    candidate_id = str(body.get("revision_candidate_id") or "")
    candidate = get_revision_candidate(store, repo, candidate_id)
    if candidate is None:
        errors.append("promotion_candidate_missing")
    else:
        candidate_material = _without_runtime(
            candidate,
            "revision_candidate_id",
            "candidate_hash",
            "persisted",
        )
        if _sha(candidate_material) != str(candidate.get("candidate_hash") or ""):
            errors.append("promotion_candidate_identity_invalid")
        if candidate.get("ledger_hash") not in {
            None,
            candidate.get("candidate_hash"),
        }:
            errors.append("promotion_candidate_ledger_hash_invalid")
        if str(candidate.get("candidate_hash") or "") != str(
            body.get("candidate_hash") or ""
        ):
            errors.append("promotion_candidate_hash_mismatch")
        if deep_recompute:
            current_candidate_check = verify_revision_candidate(
                store, repo, candidate_id, persist=False
            )
            if current_candidate_check.get("valid") is not True:
                errors.append("promotion_candidate_reverification_failed")
    freshness_proof = (
        dict(body.get("promotion_evidence_freshness") or {})
        if isinstance(body.get("promotion_evidence_freshness"), Mapping)
        else {}
    )
    if not freshness_proof:
        errors.append("promotion_evidence_freshness_missing")
    else:
        proof_hash = str(freshness_proof.get("proof_hash") or "")
        if _sha(_without_runtime(freshness_proof, "proof_hash")) != proof_hash:
            errors.append("promotion_evidence_freshness_hash_invalid")
        if float(freshness_proof.get("checked_at") or 0.0) != float(
            body.get("created_at") or 0.0
        ):
            errors.append("promotion_evidence_freshness_time_mismatch")
        if freshness_proof.get("valid") is not True or str(
            freshness_proof.get("state") or ""
        ) != "pass":
            errors.append("promotion_evidence_was_not_current")
        if candidate is not None:
            recomputed_freshness = _promotion_freshness_proof(
                store,
                repo,
                candidate,
                checked_at=float(body.get("created_at") or 0.0),
            )
            if recomputed_freshness != freshness_proof:
                errors.append("promotion_evidence_freshness_not_reproducible")
    verification_hash = str(body.get("verification_receipt_hash") or "")
    verification = get_revision_verification(store, repo, verification_hash)
    if verification is None:
        errors.append("promotion_verification_missing")
    else:
        if _sha(
            _without_runtime(verification, "verification_receipt_hash")
        ) != verification_hash:
            errors.append("promotion_verification_hash_invalid")
        if verification.get("valid") is not True or str(
            verification.get("verification_state") or ""
        ) != "pass":
            errors.append("promotion_verification_not_passing")
        if str(verification.get("revision_candidate_id") or "") != candidate_id:
            errors.append("promotion_verification_candidate_mismatch")
        if str(verification.get("candidate_hash") or "") != str(
            body.get("candidate_hash") or ""
        ):
            errors.append("promotion_verification_candidate_hash_mismatch")
    parent_id = str(body.get("source_competence_id") or "")
    parent = get_competence_candidate(store, repo, parent_id)
    parent_check = verify_competence_candidate(store, repo, parent_id)
    if parent is None or parent_check.get("valid") is not True:
        errors.append("promotion_parent_invalid")
    elif str(parent.get("receipt_hash") or "") != str(
        body.get("source_competence_receipt_hash") or ""
    ):
        errors.append("promotion_parent_receipt_mismatch")
    successor_id = str(body.get("successor_competence_id") or "")
    successor: dict[str, Any] | None = None
    if successor_id:
        successor = get_competence_candidate(store, repo, successor_id)
        successor_valid = False
        if successor is not None:
            if verify_successor_competence:
                successor_valid = (
                    verify_competence_candidate(store, repo, successor_id).get(
                        "valid"
                    )
                    is True
                )
            else:
                successor_valid = (
                    str(successor.get("competence_id") or "") == successor_id
                    and _competence_body_hash(successor)
                    == str(successor.get("receipt_hash") or "")
                )
        if successor is None or not successor_valid:
            errors.append("promotion_successor_invalid")
        else:
            if str(successor.get("receipt_hash") or "") != str(
                body.get("successor_competence_receipt_hash") or ""
            ):
                errors.append("promotion_successor_receipt_mismatch")
            if candidate is not None:
                expected_applicability = _applicability_surfaces(
                    candidate, verification_hash
                )
                expected_fields = {
                    "applicability_exclusions": _stable_union(
                        (parent or {}).get("applicability_exclusions") or (),
                        expected_applicability["applicability_exclusions"],
                    ),
                    "applicability_constraints": _stable_union(
                        (parent or {}).get("applicability_constraints") or (),
                        expected_applicability["applicability_constraints"],
                    ),
                    "applicability_revision": expected_applicability[
                        "applicability_revision"
                    ],
                    "revision_evidence_freshness": freshness_proof,
                }
                for field, expected_value in expected_fields.items():
                    if successor.get(field) != expected_value:
                        errors.append(f"promotion_successor_{field}_mismatch")
                semantic_condition = {
                    "v9.5_scope_revision": expected_applicability[
                        "semantic_revision"
                    ]
                }
                if semantic_condition not in list(
                    successor.get("applicability_conditions") or ()
                ):
                    errors.append(
                        "promotion_successor_semantic_applicability_missing"
                    )
            lineage = (
                dict(successor.get("revision_lineage") or {})
                if isinstance(successor.get("revision_lineage"), Mapping)
                else {}
            )
            expected_lineage = {
                "source_competence_id": parent_id,
                "source_competence_receipt_hash": body.get(
                    "source_competence_receipt_hash"
                ),
                "revision_candidate_id": candidate_id,
                "candidate_hash": body.get("candidate_hash"),
                "assimilation_cohort_id": body.get("cohort_id"),
                "assimilation_cohort_hash": body.get("cohort_hash"),
                "assimilation_analysis_id": body.get("analysis_id"),
                "assimilation_analysis_hash": body.get("analysis_hash"),
                "revision_verification_receipt_hash": verification_hash,
                "evidence_cutoff": freshness_proof.get("evidence_cutoff"),
                "evidence_expiry_at": freshness_proof.get(
                    "evidence_expiry_at"
                ),
                "promotion_freshness_proof_hash": freshness_proof.get(
                    "proof_hash"
                ),
                "relationship": body.get("relationship"),
            }
            if lineage != expected_lineage:
                errors.append("promotion_successor_lineage_mismatch")
            parent_counterevidence = {
                _sha(item) for item in (parent or {}).get("counterevidence") or ()
            }
            successor_counterevidence = {
                _sha(item) for item in successor.get("counterevidence") or ()
            }
            if not parent_counterevidence.issubset(successor_counterevidence):
                errors.append("promotion_successor_dropped_counterevidence")
            if str(successor.get("revision_state") or "") != "transfer_pending":
                errors.append("promotion_successor_lifecycle_invalid")
            if str(successor.get("portability_status") or "") != "pending_transfer_verification":
                errors.append("promotion_successor_portability_invalid")
    elif str(body.get("revision_type") or "") in SUCCESSOR_TYPES:
        errors.append("promotion_required_successor_missing")
    if body.get("explicit_promotion") is not True or body.get("automatic_promotion") is not False:
        errors.append("promotion_explicit_boundary_invalid")
    if body.get("parent_immutable") is not True:
        errors.append("promotion_parent_immutability_not_preserved")
    if body.get("counterevidence_conserved") is not True:
        errors.append("promotion_counterevidence_not_conserved")
    for field in AUTHORITY_FIELDS:
        if body.get(field) is not False:
            errors.append(f"promotion_authority_flag_open:{field}")
    return {
        "valid": not errors,
        "state": "pass" if not errors else "fail",
        "errors": sorted(set(errors)),
        "promotion_receipt_hash": promotion_receipt_hash,
        "source_competence_id": parent_id,
        "successor_competence_id": successor_id or None,
        "relationship": body.get("relationship"),
        "promotion": body,
        "successor": successor,
        "deep_recomputed": deep_recompute,
        **AUTHORITY_FALSE,
    }


def verify_successor_lineage(
    store: Any,
    repo: str,
    candidate_or_id: Mapping[str, Any] | str,
) -> dict[str, Any]:
    """Resolve a v1.1 successor to its exact independently verified promotion."""

    if bool(getattr(store.db, "in_transaction", False)):
        with _observational_store(store) as read_store:
            return verify_successor_lineage(read_store, repo, candidate_or_id)
    supplied = (
        dict(candidate_or_id)
        if isinstance(candidate_or_id, Mapping)
        else None
    )
    competence_id = str(
        (supplied or {}).get("competence_id")
        if supplied is not None
        else candidate_or_id
    )
    active = _ACTIVE_SUCCESSOR_LINEAGES.get()
    if competence_id in active:
        return {
            "valid": False,
            "state": "fail",
            "errors": ["successor_lineage_cycle"],
            "competence_id": competence_id,
            "read_only": True,
            **AUTHORITY_FALSE,
        }
    canonical = get_competence_candidate(store, repo, competence_id)
    errors: list[str] = []
    if canonical is None:
        return {
            "valid": False,
            "state": "unknown",
            "errors": ["successor_competence_missing"],
            "competence_id": competence_id,
            "read_only": True,
            **AUTHORITY_FALSE,
        }
    if str(canonical.get("schema_version") or "") != SUCCESSOR_SCHEMA:
        errors.append("successor_schema_invalid")
    if _competence_body_hash(canonical) != str(canonical.get("receipt_hash") or ""):
        errors.append("successor_receipt_hash_invalid")
    if supplied is not None and _canonical(supplied) != _canonical(canonical):
        errors.append("supplied_successor_differs_from_canonical")
    lineage = (
        dict(canonical.get("revision_lineage") or {})
        if isinstance(canonical.get("revision_lineage"), Mapping)
        else {}
    )
    required_lineage = (
        "source_competence_id",
        "source_competence_receipt_hash",
        "revision_candidate_id",
        "candidate_hash",
        "assimilation_cohort_id",
        "assimilation_cohort_hash",
        "assimilation_analysis_id",
        "assimilation_analysis_hash",
        "revision_verification_receipt_hash",
        "relationship",
    )
    for field in required_lineage:
        if not str(lineage.get(field) or ""):
            errors.append(f"successor_lineage_missing:{field}")
    if not _revision_table_present(store, "competence_revision_promotions"):
        errors.append("promotion_ledger_missing")
        rows = []
    else:
        rows = store.db.execute(
            """SELECT promotion_receipt_hash
               FROM competence_revision_promotions
               WHERE repository_id=? AND repo=?
                 AND source_competence_id=? AND successor_competence_id=?
                 AND revision_candidate_id=? AND verification_receipt_hash=?
                 AND relationship=?""",
            (
                _repo_identity(store, repo),
                repo,
                str(lineage.get("source_competence_id") or ""),
                competence_id,
                str(lineage.get("revision_candidate_id") or ""),
                str(lineage.get("revision_verification_receipt_hash") or ""),
                str(lineage.get("relationship") or ""),
            ),
        ).fetchall()
    if len(rows) != 1:
        errors.append(
            "successor_promotion_missing"
            if not rows
            else "successor_promotion_ambiguous"
        )
        promotion_check: dict[str, Any] | None = None
        promotion_hash = ""
    else:
        promotion_hash = str(rows[0]["promotion_receipt_hash"] or "")
        active_promotions = _ACTIVE_PROMOTION_VERIFICATIONS.get()
        deep_recompute = promotion_hash not in active_promotions
        promotion_token = _ACTIVE_PROMOTION_VERIFICATIONS.set(
            active_promotions | {promotion_hash}
        )
        lineage_token = _ACTIVE_SUCCESSOR_LINEAGES.set(active | {competence_id})
        try:
            promotion_check = _verify_revision_promotion_body(
                store,
                repo,
                promotion_hash,
                deep_recompute=deep_recompute,
                verify_successor_competence=False,
            )
        finally:
            _ACTIVE_SUCCESSOR_LINEAGES.reset(lineage_token)
            _ACTIVE_PROMOTION_VERIFICATIONS.reset(promotion_token)
        if promotion_check.get("valid") is not True:
            errors.append("successor_promotion_invalid")
        promotion = dict(promotion_check.get("promotion") or {})
        if str(promotion.get("successor_competence_id") or "") != competence_id:
            errors.append("successor_promotion_competence_mismatch")
        if str(promotion.get("successor_competence_receipt_hash") or "") != str(
            canonical.get("receipt_hash") or ""
        ):
            errors.append("successor_promotion_receipt_mismatch")
    return {
        "valid": not errors,
        "state": "pass" if not errors else "fail",
        "errors": sorted(set(errors)),
        "competence_id": competence_id,
        "successor_receipt_hash": canonical.get("receipt_hash"),
        "promotion_receipt_hash": promotion_hash or None,
        "promotion_verification": promotion_check,
        "deep_recomputed": bool(
            promotion_check and promotion_check.get("deep_recomputed")
        ),
        "read_only": True,
        **AUTHORITY_FALSE,
    }


def list_revision_promotions(
    store: Any, repo: str, source_competence_id: str | None = None
) -> list[dict[str, Any]]:
    if not _revision_table_present(store, "competence_revision_promotions"):
        return []
    repository_id = _repo_identity(store, repo)
    if source_competence_id:
        rows = store.db.execute(
            "SELECT promotion_json FROM competence_revision_promotions WHERE repository_id=? AND repo=? AND source_competence_id=? ORDER BY created_at ASC",
            (repository_id, repo, str(source_competence_id)),
        ).fetchall()
    else:
        rows = store.db.execute(
            "SELECT promotion_json FROM competence_revision_promotions WHERE repository_id=? AND repo=? ORDER BY created_at ASC",
            (repository_id, repo),
        ).fetchall()
    return [body for row in rows if (body := _json(row["promotion_json"])) is not None]


def competence_successor_state(
    store: Any, repo: str, competence_id: str
) -> dict[str, Any]:
    """Read-only package-currentness input derived from explicit promotions."""

    if bool(getattr(store.db, "in_transaction", False)):
        with _observational_store(store) as read_store:
            return competence_successor_state(read_store, repo, competence_id)
    if not _revision_table_present(store, "competence_revision_promotions"):
        return {
            "valid": False,
            "state": "unknown",
            "errors": ["promotion_ledger_missing"],
            "source_competence_id": competence_id,
            "successor_competence_ids": [],
            "promotion_receipt_hashes": [],
            "invalid_promotion_receipt_hashes": [],
            "package_rewrite_performed": False,
            "read_only": True,
            **AUTHORITY_FALSE,
        }
    promotions = list_revision_promotions(store, repo, competence_id)
    semantic: list[dict[str, Any]] = []
    invalid_promotions: list[str] = []
    for item in promotions:
        receipt_hash = str(item.get("promotion_receipt_hash") or "")
        # Package currentness needs only immutable promotion-ledger validity.
        # It deliberately avoids re-entering cohort -> feedback -> package
        # verification, which would be circular.  The stored independent
        # verification receipt is still hash/binding checked below.
        check = _verify_revision_promotion_body(
            store,
            repo,
            receipt_hash,
            deep_recompute=False,
            verify_successor_competence=False,
        )
        if check.get("valid") is not True:
            invalid_promotions.append(receipt_hash)
            continue
        if str(item.get("relationship") or "") in {
            "narrows",
            "specializes",
            "supersedes",
            "generalizes",
        } and item.get("successor_competence_id"):
            semantic.append(item)
    if invalid_promotions:
        state = "unknown"
        valid = False
        errors = ["promotion_verification_failed"]
    elif semantic:
        state = "superseded"
        valid = True
        errors = []
    else:
        state = "current"
        valid = True
        errors = []
    return {
        "valid": valid,
        "state": state,
        "errors": errors,
        "source_competence_id": competence_id,
        "successor_competence_ids": sorted(
            {str(item.get("successor_competence_id")) for item in semantic}
        ),
        "promotion_receipt_hashes": sorted(
            str(item.get("promotion_receipt_hash")) for item in semantic
        ),
        "invalid_promotion_receipt_hashes": sorted(invalid_promotions),
        "package_rewrite_performed": False,
        "read_only": True,
        **AUTHORITY_FALSE,
    }


__all__ = [
    "APPLICABILITY_REVISION_SCHEMA",
    "CLAIM_BOUNDARY",
    "PROMOTION_SCHEMA",
    "REVISION_TYPES",
    "SCHEMA",
    "SUCCESSOR_SCHEMA",
    "VERIFICATION_SCHEMA",
    "VERSION",
    "CompetenceRevisionError",
    "build_revision_candidate",
    "competence_successor_state",
    "ensure_revision_tables",
    "get_revision_candidate",
    "get_revision_promotion",
    "get_revision_verification",
    "list_revision_promotions",
    "persist_revision_candidate",
    "promote_revision_candidate",
    "verify_revision_candidate",
    "verify_revision_promotion",
    "verify_successor_lineage",
]
