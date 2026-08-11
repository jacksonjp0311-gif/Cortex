"""v9.5 distributed evidence assimilation.

The module freezes exact v9.4 package-use feedback before interpreting it.  It
never treats feedback volume, caller scope labels, or a continuous score as
authority.  Synthetic evidence remains visible, but only complete live
empirical observations may enter the empirical analysis plane.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

from .adapter_provenance import EVIDENCE_ATTESTED, EVIDENCE_LIVE
from .competence import get_competence_candidate, verify_competence_candidate
from .competence_distribution import (
    BLOCKING_EVENTS,
    get_distribution_package,
    get_target_profile,
    list_distribution_feedback,
    verify_distribution_feedback,
    verify_package_use,
)

SCHEMA = "cortex-evidence-assimilation/1.0"
ANALYSIS_SCHEMA = "cortex-evidence-assimilation-analysis/1.0"
VERSION = "9.5.0"

PASS = "pass"
FAIL = "fail"
UNKNOWN = "unknown"

SELECTION_CANONICAL_ALL = "canonical_all_before_cutoff"
SELECTION_STRUCTURAL_SUBSET = "structural_explicit_subset"
SELECTION_STRUCTURAL_CUTOFF = "structural_explicit_cutoff"

DEFAULT_SELECTION_POLICY: dict[str, Any] = {
    "selection_mode": "all_canonical_before_cutoff",
    "required_evidence_classes": [EVIDENCE_LIVE, EVIDENCE_ATTESTED],
    "deduplication_root": "package_use_outcome_witness",
    "retain_negative_evidence": True,
    "retain_excluded_evidence": True,
}
DEFAULT_ANALYSIS_POLICY: dict[str, Any] = {
    "dependence_axes": [
        "competence_lineage_hash",
        "principal_id",
        "adapter_registration_id",
        "model_identity_hash",
        "provider_family",
        "target_class",
        "environment_hash",
        "task_contract_hash",
        "witness_suite",
        "transfer_trial_root",
    ],
    "independence_axes": [
        "principal_id",
        "adapter_registration_id",
        "model_identity_hash",
        "provider_family",
        "target_class",
        "environment_hash",
        "task_contract_hash",
        "witness_suite",
        "transfer_trial_root",
    ],
    "dependence_admission": {
        "strongly_dependent": "collapse",
        "partially_dependent": "collapse",
        "unresolved": "collapse_and_block_global",
    },
    # Global contradiction remains unavailable until the host freezes an
    # explicit threshold policy.  No hidden numeric threshold is supplied.
    "global_contradiction": {
        "minimum_complete_clusters": None,
        "minimum_diversity": {},
    },
    "causal_interpretation": "observational_exposure_bound",
    "broaden_applicability": False,
}

AUTHORITY_FALSE = {
    "host_mutate_authorized": False,
    "execution_authorized": False,
    "memory_admission_authorized": False,
    "policy_effect": False,
    "automatic_broadcast": False,
    "automatic_global_revision": False,
    "advisory_only": True,
}


class AssimilationError(ValueError):
    """Raised when a frozen evidence boundary cannot be established."""


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
        raise AssimilationError(f"Unknown repository: {repo}")
    return str(row["repository_id"])


def _without_runtime(body: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in body.items()
        if key not in {"created_at", "inserted", "duplicate", "ledger_hash"}
    }


def _merge_policy(base: Mapping[str, Any], supplied: Mapping[str, Any] | None) -> dict[str, Any]:
    result = json.loads(_canonical(base))
    for key, value in dict(supplied or {}).items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = {**dict(result[key]), **dict(value)}
        else:
            result[str(key)] = value
    return result


def _tri_state(states: Sequence[str]) -> str:
    if any(state == FAIL for state in states):
        return FAIL
    if states and all(state == PASS for state in states):
        return PASS
    return UNKNOWN


def ensure_assimilation_tables(store: Any) -> None:
    """Install immutable cohort and analysis ledgers."""

    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS competence_assimilation_cohorts(
            cohort_id TEXT PRIMARY KEY CHECK(length(cohort_id) = 64),
            cohort_hash TEXT NOT NULL CHECK(length(cohort_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            competence_id TEXT NOT NULL CHECK(length(competence_id) = 64),
            competence_receipt_hash TEXT NOT NULL CHECK(length(competence_receipt_hash) = 64),
            evidence_cutoff REAL NOT NULL,
            selection_policy_hash TEXT NOT NULL CHECK(length(selection_policy_hash) = 64),
            analysis_policy_hash TEXT NOT NULL CHECK(length(analysis_policy_hash) = 64),
            cohort_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, cohort_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_assimilation_cohorts_competence
            ON competence_assimilation_cohorts(repo, competence_id, created_at ASC);
        CREATE TRIGGER IF NOT EXISTS competence_assimilation_cohorts_no_update
        BEFORE UPDATE ON competence_assimilation_cohorts BEGIN
            SELECT RAISE(ABORT, 'assimilation cohorts cannot be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_assimilation_cohorts_no_delete
        BEFORE DELETE ON competence_assimilation_cohorts BEGIN
            SELECT RAISE(ABORT, 'assimilation cohorts cannot be deleted');
        END;

        CREATE TABLE IF NOT EXISTS competence_assimilation_analyses(
            analysis_id TEXT PRIMARY KEY CHECK(length(analysis_id) = 64),
            analysis_hash TEXT NOT NULL CHECK(length(analysis_hash) = 64),
            cohort_id TEXT NOT NULL CHECK(length(cohort_id) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            competence_id TEXT NOT NULL CHECK(length(competence_id) = 64),
            analysis_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, analysis_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_assimilation_analyses_cohort
            ON competence_assimilation_analyses(repo, cohort_id, created_at ASC);
        CREATE TRIGGER IF NOT EXISTS competence_assimilation_analyses_no_update
        BEFORE UPDATE ON competence_assimilation_analyses BEGIN
            SELECT RAISE(ABORT, 'assimilation analyses cannot be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_assimilation_analyses_no_delete
        BEFORE DELETE ON competence_assimilation_analyses BEGIN
            SELECT RAISE(ABORT, 'assimilation analyses cannot be deleted');
        END;
        """
    )
    store.db.commit()


def _feedback_body(store: Any, repo: str, feedback_id: str) -> dict[str, Any] | None:
    repository_id = _repo_identity(store, repo)
    row = store.db.execute(
        """SELECT feedback_json FROM competence_usage_feedback
           WHERE repository_id=? AND repo=? AND feedback_id=?""",
        (repository_id, repo, str(feedback_id)),
    ).fetchone()
    return _json(row["feedback_json"]) if row is not None else None


def _target_class(profile: Mapping[str, Any]) -> str:
    identity = profile.get("identity")
    identity = identity if isinstance(identity, Mapping) else {}
    # Only explicit class declarations are class evidence.  A target ID,
    # system name, or role must not be silently promoted into a class axis.
    for key in ("target_class", "class", "type"):
        if identity.get(key):
            return str(identity[key])
    if profile.get("target_class"):
        return str(profile["target_class"])
    return ""


def _feedback_freshness(
    feedback: Mapping[str, Any],
    profile: Mapping[str, Any],
    *,
    as_of: float,
    package_use_created_at: float,
) -> dict[str, Any]:
    policy = profile.get("freshness_policy")
    policy = policy if isinstance(policy, Mapping) else {}
    limit = policy.get("feedback_max_age_seconds")
    created = float(feedback.get("created_at") or 0.0)
    exposure_created = float(package_use_created_at or 0.0)
    if limit in {None, ""} or created <= 0 or exposure_created <= 0:
        return {"state": UNKNOWN, "reason": "feedback_freshness_policy_missing"}
    if created > float(as_of):
        return {
            "state": FAIL,
            "reason": "feedback_created_after_evidence_cutoff",
            "created_at": created,
            "as_of": float(as_of),
        }
    if exposure_created > float(as_of):
        return {
            "state": FAIL,
            "reason": "package_use_created_after_evidence_cutoff",
            "package_use_created_at": exposure_created,
            "as_of": float(as_of),
        }
    feedback_age = float(as_of) - created
    exposure_age = float(as_of) - exposure_created
    return {
        "state": (
            PASS
            if feedback_age <= float(limit) and exposure_age <= float(limit)
            else FAIL
        ),
        "age_seconds": max(feedback_age, exposure_age),
        "feedback_age_seconds": feedback_age,
        "package_use_age_seconds": exposure_age,
        "freshness_basis": "canonical_package_use_and_feedback",
        "max_age_seconds": float(limit),
        "as_of": float(as_of),
    }


def _historical_distribution_currentness(
    store: Any,
    repo: str,
    *,
    feedback: Mapping[str, Any],
    package: Mapping[str, Any] | None,
    profile: Mapping[str, Any] | None,
    package_use: Mapping[str, Any],
    package_use_check: Mapping[str, Any],
    as_of: float,
    ignore_revision_candidate_id: str | None = None,
) -> dict[str, Any]:
    """Reconstruct package/profile currentness at one immutable cutoff.

    Present-time distribution verification is intentionally not used here: a
    later target profile, revocation, expiry, or competence promotion must not
    rewrite what was current at the cohort cutoff.  Every input below resolves
    from an immutable ledger and every age limit comes from the package's
    frozen target profile.
    """

    errors: list[str] = []
    unknown: list[str] = []
    cutoff = float(as_of)
    if package is None:
        errors.append("historical_package_missing")
    if profile is None:
        errors.append("historical_profile_missing")
    if package_use_check.get("valid") is not True:
        errors.append("historical_package_use_binding_invalid")
    feedback_created = float(feedback.get("created_at") or 0.0)
    use_created = float(package_use.get("created_at") or 0.0)
    package_created = float((package or {}).get("created_at") or 0.0)
    profile_created = float((profile or {}).get("created_at") or 0.0)
    chronology = {
        "profile_created_at": profile_created,
        "package_created_at": package_created,
        "package_use_created_at": use_created,
        "feedback_created_at": feedback_created,
        "as_of": cutoff,
    }
    if not all(value > 0 for value in chronology.values()):
        unknown.append("historical_currentness_time_missing")
    elif not (
        profile_created <= package_created <= use_created <= feedback_created <= cutoff
    ):
        errors.append("historical_currentness_chronology_invalid")

    if package is not None and profile is not None:
        if str(package.get("profile_id") or "") != str(
            profile.get("profile_id") or ""
        ) or str(package.get("profile_hash") or "") != str(
            profile.get("profile_hash") or ""
        ):
            errors.append("historical_package_profile_binding_invalid")
        if str(package.get("package_id") or "") != str(
            feedback.get("package_id") or ""
        ):
            errors.append("historical_feedback_package_binding_invalid")

    # Latest-registered is evaluated at the declared cutoff, not now.
    if profile is not None:
        if str(profile.get("currentness_policy") or "") != "latest_registered":
            unknown.append("historical_profile_currentness_policy_missing")
        else:
            rows = store.db.execute(
                """SELECT profile_id FROM competence_target_profiles
                   WHERE repository_id=? AND repo=? AND target_id=?
                     AND created_at<=?
                   ORDER BY created_at DESC, profile_id DESC""",
                (
                    _repo_identity(store, repo),
                    repo,
                    str(profile.get("target_id") or ""),
                    cutoff,
                ),
            ).fetchall()
            if not rows:
                unknown.append("historical_profile_not_resolvable")
            elif str(rows[0]["profile_id"] or "") != str(
                profile.get("profile_id") or ""
            ):
                errors.append("historical_profile_not_current")

    freshness_policy = (
        dict(profile.get("freshness_policy") or {})
        if profile is not None
        and isinstance(profile.get("freshness_policy"), Mapping)
        else {}
    )
    freshness_planes: dict[str, dict[str, Any]] = {}
    frozen_freshness = (
        dict((package or {}).get("freshness") or {})
        if isinstance((package or {}).get("freshness"), Mapping)
        else {}
    )
    frozen_planes = (
        dict(frozen_freshness.get("planes") or {})
        if isinstance(frozen_freshness.get("planes"), Mapping)
        else {}
    )
    policy_keys = {
        "competence": "competence_max_age_seconds",
        "transfer_evidence": "transfer_max_age_seconds",
        "target_profile": "profile_max_age_seconds",
    }
    for plane_name, policy_key in policy_keys.items():
        plane = (
            dict(frozen_planes.get(plane_name) or {})
            if isinstance(frozen_planes.get(plane_name), Mapping)
            else {}
        )
        raw_limit = freshness_policy.get(policy_key)
        expires_at = float(plane.get("expires_at") or 0.0)
        if raw_limit in {None, ""} or expires_at <= 0:
            unknown.append(f"historical_freshness_missing:{plane_name}")
            state = UNKNOWN
        elif float(plane.get("max_age_seconds") or -1.0) != float(raw_limit):
            errors.append(f"historical_freshness_policy_mismatch:{plane_name}")
            state = FAIL
        else:
            state = PASS if cutoff <= expires_at else FAIL
            if state == FAIL:
                errors.append(f"historical_evidence_expired:{plane_name}")
        freshness_planes[plane_name] = {
            "state": state,
            "expires_at": expires_at or None,
            "max_age_seconds": raw_limit,
        }

    direct_sources = {
        "package": (package_created, "package_max_age_seconds"),
        "package_use": (use_created, "feedback_max_age_seconds"),
        "feedback": (feedback_created, "feedback_max_age_seconds"),
    }
    for plane_name, (created_at, policy_key) in direct_sources.items():
        raw_limit = freshness_policy.get(policy_key)
        if raw_limit in {None, ""} or created_at <= 0:
            unknown.append(f"historical_freshness_missing:{plane_name}")
            state = UNKNOWN
            expires_at = None
        else:
            expires_at = created_at + float(raw_limit)
            state = PASS if cutoff <= expires_at else FAIL
            if state == FAIL:
                errors.append(f"historical_evidence_expired:{plane_name}")
        freshness_planes[plane_name] = {
            "state": state,
            "expires_at": expires_at,
            "max_age_seconds": raw_limit,
        }

    if package is not None:
        package_id = str(package.get("package_id") or "")
        event_rows = store.db.execute(
            """SELECT * FROM competence_distribution_events
               WHERE repository_id=? AND repo=? AND package_id=? AND created_at<=?
               ORDER BY created_at ASC""",
            (_repo_identity(store, repo), repo, package_id, cutoff),
        ).fetchall()
        for row in event_rows:
            event = _json(row["event_json"])
            if event is None:
                errors.append("historical_package_event_json_invalid")
                continue
            event_material = {
                str(key): value
                for key, value in event.items()
                if key not in {"event_id", "event_hash", "created_at"}
            }
            expected_event_hash = _sha(event_material)
            if (
                str(event.get("event_id") or "") != expected_event_hash
                or str(event.get("event_hash") or "") != expected_event_hash
                or str(row["event_id"] or "") != expected_event_hash
                or str(row["event_hash"] or "") != expected_event_hash
                or str(event.get("package_id") or "") != package_id
                or str(row["package_id"] or "") != package_id
                or str(event.get("event_type") or "")
                != str(row["event_type"] or "")
                or str(event.get("target_id") or "")
                != str(row["target_id"] or "")
                or float(event.get("created_at") or 0.0)
                != float(row["created_at"] or 0.0)
            ):
                errors.append("historical_package_event_integrity_invalid")
            if str(row["event_type"] or "") in BLOCKING_EVENTS:
                errors.append(
                    f"historical_package_event:{row['event_type'] or ''!s}"
                )
        global_rows = store.db.execute(
            """SELECT e.*
               FROM competence_distribution_events e
               JOIN competence_distribution_packages p
                 ON p.repository_id=e.repository_id AND p.repo=e.repo
                AND p.package_id=e.package_id
               WHERE e.repository_id=? AND e.repo=? AND p.competence_id=?
                 AND e.created_at<=?
               ORDER BY e.created_at ASC""",
            (
                _repo_identity(store, repo),
                repo,
                str(package.get("competence_id") or ""),
                cutoff,
            ),
        ).fetchall()
        for row in global_rows:
            event = _json(row["event_json"]) or {}
            event_material = {
                str(key): value
                for key, value in event.items()
                if key not in {"event_id", "event_hash", "created_at"}
            }
            expected_event_hash = _sha(event_material)
            if (
                not event
                or str(event.get("event_id") or "") != expected_event_hash
                or str(event.get("event_hash") or "") != expected_event_hash
                or str(row["event_id"] or "") != expected_event_hash
                or str(row["event_hash"] or "") != expected_event_hash
                or str(event.get("event_type") or "")
                != str(row["event_type"] or "")
                or str(event.get("package_id") or "")
                != str(row["package_id"] or "")
                or float(event.get("created_at") or 0.0)
                != float(row["created_at"] or 0.0)
            ):
                errors.append("historical_global_event_integrity_invalid")
                continue
            if (
                str(event.get("scope") or "target") == "global"
                and str(row["event_type"] or "")
                in {"challenge", "quarantine", "revoke"}
            ):
                errors.append(
                    f"historical_global_competence_event:{row['event_type'] or ''!s}"
                )

        table = store.db.execute(
            """SELECT 1 FROM sqlite_master
               WHERE type='table' AND name='competence_revision_promotions'"""
        ).fetchone()
        if table is None:
            unknown.append("historical_promotion_ledger_missing")
        else:
            rows = store.db.execute(
                """SELECT *
                   FROM competence_revision_promotions
                   WHERE repository_id=? AND repo=? AND source_competence_id=?
                     AND created_at<=?""",
                (
                    _repo_identity(store, repo),
                    repo,
                    str(package.get("competence_id") or ""),
                    cutoff,
                ),
            ).fetchall()
            semantic = {"narrows", "specializes", "supersedes", "generalizes"}
            for row in rows:
                promotion = _json(row["promotion_json"])
                if promotion is None:
                    errors.append("historical_promotion_json_invalid")
                    continue
                promotion_material = {
                    str(key): value
                    for key, value in promotion.items()
                    if key
                    not in {
                        "promotion_receipt_hash",
                        "created_at",
                        "inserted",
                        "duplicate",
                        "ledger_hash",
                        "commit_state",
                    }
                }
                expected_promotion_hash = _sha(promotion_material)
                if (
                    str(promotion.get("promotion_receipt_hash") or "")
                    != expected_promotion_hash
                    or str(row["promotion_receipt_hash"] or "")
                    != expected_promotion_hash
                    or str(promotion.get("source_competence_id") or "")
                    != str(package.get("competence_id") or "")
                    or str(row["source_competence_id"] or "")
                    != str(package.get("competence_id") or "")
                    or str(promotion.get("revision_candidate_id") or "")
                    != str(row["revision_candidate_id"] or "")
                    or str(promotion.get("relationship") or "")
                    != str(row["relationship"] or "")
                    or float(promotion.get("created_at") or 0.0)
                    != float(row["created_at"] or 0.0)
                ):
                    errors.append("historical_promotion_integrity_invalid")
                    continue
                if ignore_revision_candidate_id and str(
                    row["revision_candidate_id"] or ""
                ) == str(ignore_revision_candidate_id):
                    continue
                if str(row["relationship"] or "") in semantic:
                    errors.append("historical_competence_superseded")

    use_empirical = bool(
        package_use_check.get("empirical_feedback_eligible") is True
        and package_use_check.get("sandbox_only") is False
        and package_use_check.get("non_promotable") is False
    )
    if not use_empirical:
        errors.append("historical_package_use_not_empirically_eligible")
    state = FAIL if errors else UNKNOWN if unknown else PASS
    return {
        "state": state,
        "errors": sorted(set(errors)),
        "unknown": sorted(set(unknown)),
        "as_of": cutoff,
        "chronology": chronology,
        "freshness_planes": freshness_planes,
        "currentness_basis": (
            "immutable_ledgers_at_declared_cutoff; present_state_not_used"
        ),
        "present_state_authorizing": False,
    }


def resolve_feedback_observation(
    store: Any,
    repo: str,
    feedback_id: str,
    *,
    competence_id: str | None = None,
    as_of: float | None = None,
    _ignore_revision_candidate_id: str | None = None,
) -> dict[str, Any]:
    """Resolve one feedback row into a canonical, non-authorizing observation."""

    body = _feedback_body(store, repo, feedback_id)
    if body is None:
        return {
            "feedback_id": str(feedback_id),
            "theta": UNKNOWN,
            "empirically_eligible": False,
            "errors": ["feedback_missing"],
            **AUTHORITY_FALSE,
        }
    cutoff = float(as_of if as_of is not None else time.time())
    repository_id = _repo_identity(store, repo)
    dynamic = verify_distribution_feedback(
        store,
        repo,
        str(feedback_id),
        resolve_current_package=False,
    )
    use_hash = str(body.get("package_use_receipt_hash") or "")
    use_check = (
        verify_package_use(
            store,
            repo,
            use_hash,
            expected_package_id=str(body.get("package_id") or ""),
            resolve_current_package=False,
        )
        if use_hash
        else {"valid": False, "state": UNKNOWN, "errors": ["package_use_missing"]}
    )
    package = get_distribution_package(store, repo, str(body.get("package_id") or ""))
    profile = (
        get_target_profile(store, repo, str(package.get("profile_id") or ""))
        if package is not None
        else None
    )
    candidate_id = str((package or {}).get("competence_id") or "")
    candidate = (
        get_competence_candidate(store, repo, candidate_id) if candidate_id else None
    )
    errors: list[str] = []
    if dynamic.get("valid") is not True:
        errors.extend(str(item) for item in dynamic.get("errors") or ())
    if str(body.get("feedback_id") or "") != str(feedback_id):
        errors.append("feedback_identity_mismatch")
    if str(body.get("repo") or "") != str(repo):
        errors.append("feedback_repository_name_mismatch")
    if str(body.get("repository_id") or "") != repository_id:
        errors.append("feedback_repository_identity_mismatch")
    if competence_id is not None and candidate_id != str(competence_id):
        errors.append("feedback_competence_mismatch")
    if use_check.get("valid") is not True:
        errors.extend(str(item) for item in use_check.get("errors") or ())
    if package is None:
        errors.append("package_missing")
    if profile is None:
        errors.append("profile_missing")
    if candidate is None:
        errors.append("competence_missing")
    elif verify_competence_candidate(store, repo, candidate_id).get("valid") is not True:
        errors.append("competence_verification_failed")
    if package is not None:
        if str(body.get("target_id") or "") != str(package.get("target_id") or ""):
            errors.append("feedback_target_package_mismatch")
        if candidate_id != str(package.get("competence_id") or ""):
            errors.append("feedback_package_competence_mismatch")

    receipt = (
        store.verify_symbiotic_receipt(repo, use_hash).get("receipt") or {}
        if use_hash
        else {}
    )
    if receipt and str(receipt.get("target_id") or "") != str(
        body.get("target_id") or ""
    ):
        errors.append("feedback_target_package_use_mismatch")
    if receipt and str(receipt.get("competence_id") or "") != candidate_id:
        errors.append("feedback_competence_package_use_mismatch")
    outcome = dict(use_check.get("canonical_outcome") or {})
    witness = dict(use_check.get("canonical_witness") or {})
    provenance = dict(use_check.get("adapter_provenance") or {})
    host_identity = dict(provenance.get("host_identity") or {})
    host_classification = dict(
        provenance.get("host_model_classification") or {}
    )
    classification_current = (
        str(host_classification.get("state") or "") == "host_registered"
    )
    principal_id = (
        str(host_classification.get("principal_id") or "")
        if classification_current
        else ""
    )
    evidence_class = str(use_check.get("evidence_class") or "unknown")
    freshness = (
        _feedback_freshness(
            body,
            profile or {},
            as_of=cutoff,
            package_use_created_at=float(receipt.get("created_at") or 0.0),
        )
        if profile is not None
        else {"state": UNKNOWN, "reason": "profile_missing"}
    )
    outcome_success = outcome.get("success")
    outcome_state = (
        PASS
        if outcome.get("status") in {"verified_success", "verified_failure"}
        and isinstance(outcome_success, bool)
        else UNKNOWN
    )
    witness_state = (
        PASS
        if witness.get("witness_state") == PASS
        and bool(witness.get("witness_result_hash"))
        and witness.get("independent") is True
        else UNKNOWN
    )
    historical_currentness = _historical_distribution_currentness(
        store,
        repo,
        feedback=body,
        package=package,
        profile=profile,
        package_use=receipt,
        package_use_check=use_check,
        as_of=cutoff,
        ignore_revision_candidate_id=_ignore_revision_candidate_id,
    )
    planes = {
        "empirical_class": (
            PASS
            if evidence_class in {EVIDENCE_LIVE, EVIDENCE_ATTESTED}
            else FAIL
            if evidence_class in {"synthetic", "simulated"}
            else UNKNOWN
        ),
        "provenance": (
            PASS
            if dynamic.get("valid") is True and use_check.get("valid") is True
            else FAIL
        ),
        "package_use_binding": PASS if use_check.get("valid") is True else FAIL,
        "feedback_currentness": str(
            historical_currentness.get("state") or UNKNOWN
        ),
        "outcome_binding": outcome_state,
        "witness_binding": witness_state,
        "target_identity": (
            PASS
            if profile is not None
            and body.get("target_id")
            and not any("target" in item for item in errors)
            else FAIL
            if any("target" in item for item in errors)
            else UNKNOWN
        ),
        "competence_identity": (
            PASS
            if candidate is not None
            and not any("competence" in item for item in errors)
            else FAIL
            if any("competence" in item for item in errors)
            else UNKNOWN
        ),
        "freshness": str(freshness.get("state") or UNKNOWN),
    }
    theta = _tri_state(list(planes.values()))
    roots = dict(use_check.get("binding_roots") or {})
    observation_identity = _sha(
        {
            "repository_id": repository_id,
            "competence_id": candidate_id,
            "competence_receipt_hash": (candidate or {}).get("receipt_hash"),
            "package_use_receipt_hash": use_hash,
            "outcome_receipt_hash": roots.get("model_outcome_receipt_hash"),
            "witness_result_hash": roots.get("witness_result_hash"),
            "trajectory_receipt_hash": roots.get("model_trajectory_receipt_hash"),
        }
    )
    environment = dict((profile or {}).get("environment") or {})
    environment_hash = _sha(environment)
    lineage_hash = str((candidate or {}).get("evidence_lineage_hash") or "")
    model_identity = {
        key: host_identity.get(key)
        for key in ("provider_family", "model_id", "model_version", "adapter_id", "adapter_version")
    }
    observed = {
        "feedback_id": str(feedback_id),
        "feedback_hash": body.get("feedback_hash"),
        "feedback_created_at": body.get("created_at"),
        "caller_scope_claim": body.get("kind"),
        "caller_scope_authorizing": False,
        "package_id": body.get("package_id"),
        "package_hash": (package or {}).get("package_hash"),
        "package_use_receipt_hash": use_hash,
        "package_use_created_at": receipt.get("created_at"),
        "profile_id": (profile or {}).get("profile_id"),
        "profile_hash": (profile or {}).get("profile_hash"),
        "target_id": body.get("target_id"),
        "target_class": _target_class(profile or {}),
        "environment_hash": environment_hash,
        "environment": environment,
        "competence_id": candidate_id,
        "competence_receipt_hash": (candidate or {}).get("receipt_hash"),
        "competence_lineage_hash": lineage_hash,
        "session_id": use_check.get("session_id"),
        "turn_id": use_check.get("turn_id"),
        "invocation_id": use_check.get("invocation_id"),
        "model_identity": model_identity,
        "model_identity_hash": _sha(model_identity),
        "model_family": (
            host_classification.get("model_family")
            if classification_current
            else ""
        ),
        "model_capability_class": (
            host_classification.get("capability_class")
            if classification_current
            else ""
        ),
        "host_model_classification": host_classification,
        "model_id": host_identity.get("model_id") or "",
        "provider_family": host_identity.get("provider_family") or "",
        # Principal identity is a dependence plane.  It comes only from the
        # hash-verified host registration classification; caller/model output
        # cannot supply it.  Legacy or unclassified registrations stay empty
        # and therefore unresolved under the mandatory policy axes.
        "principal_id": principal_id,
        "adapter_registration_id": provenance.get("registration_id"),
        "task_contract_hash": receipt.get("task_contract_hash")
        or outcome.get("task_contract_hash"),
        "witness_suite": receipt.get("task_contract_hash")
        or outcome.get("task_contract_hash")
        or "",
        "transfer_trial_root": str(
            (((package or {}).get("transfer_proof") or {}).get("latest_trial_receipt_hash"))
            or ""
        ),
        "binding_roots": roots,
        "observation_identity": observation_identity,
        "evidence_class": evidence_class,
        "evidence_type": "observational",
        "causal_effect_established": False,
        "outcome_success": outcome_success if isinstance(outcome_success, bool) else None,
        "outcome_status": outcome.get("status"),
        "theta_planes": planes,
        "theta": theta,
        "freshness": freshness,
        "feedback_currentness": {
            **historical_currentness,
            "distribution_feedback_structural_valid": bool(
                dynamic.get("valid") is True
            ),
        },
        "empirically_eligible": bool(theta == PASS and not errors),
        "errors": sorted(set(errors)),
        "canonical_outcome": {
            "receipt_hash": roots.get("model_outcome_receipt_hash"),
            "status": outcome.get("status"),
            "success": outcome_success if isinstance(outcome_success, bool) else None,
            "observed_result_hash": outcome.get("observed_result_hash"),
        },
        "canonical_witness": {
            "receipt_hash": roots.get("model_witness_receipt_hash"),
            "witness_result_hash": roots.get("witness_result_hash"),
            "independent": witness.get("independent") is True,
        },
        **AUTHORITY_FALSE,
    }
    return observed


def _cohort_material(cohort: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in cohort.items()
        if key
        not in {
            "cohort_id",
            "cohort_hash",
            "inserted",
            "duplicate",
            "ledger_hash",
        }
    }


def _cohort_counts(
    observations: Sequence[Mapping[str, Any]],
    *,
    requested_count: int,
    unique_feedback_count: int,
) -> dict[str, int]:
    return {
        "requested_feedback_count": int(requested_count),
        "unique_feedback_count": int(unique_feedback_count),
        "raw_evidence_count": len(observations),
        "empirically_eligible_count": sum(
            1
            for item in observations
            if item.get("empirically_eligible") is True
            and item.get("duplicate_observation") is not True
        ),
        "excluded_synthetic_count": sum(
            1
            for item in observations
            if item.get("evidence_class") in {"synthetic", "simulated"}
        ),
        "invalid_count": sum(1 for item in observations if item.get("theta") == FAIL),
        "unknown_count": sum(
            1 for item in observations if item.get("theta") == UNKNOWN
        ),
        "duplicate_count": int(requested_count)
        - int(unique_feedback_count)
        + sum(
            1
            for item in observations
            if item.get("duplicate_observation") is True
        ),
    }


def _apply_selection_policy(
    observation: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    result = dict(observation)
    allowed = {str(item) for item in policy.get("required_evidence_classes") or ()}
    evidence_class = str(result.get("evidence_class") or "unknown")
    if evidence_class not in allowed:
        planes = dict(result.get("theta_planes") or {})
        planes["empirical_class"] = (
            FAIL
            if evidence_class in {
                "synthetic",
                "simulated",
                EVIDENCE_LIVE,
                EVIDENCE_ATTESTED,
            }
            else UNKNOWN
        )
        result["theta_planes"] = planes
        result["theta"] = _tri_state(list(planes.values()))
        result["empirically_eligible"] = False
        result["errors"] = sorted(
            set(result.get("errors") or ())
            | {"evidence_class_excluded_by_frozen_selection_policy"}
        )
    return result


def freeze_evidence_cohort(
    store: Any,
    repo: str,
    *,
    competence_id: str,
    feedback_ids: Sequence[str] | None = None,
    selection_policy: Mapping[str, Any] | None = None,
    analysis_policy: Mapping[str, Any] | None = None,
    evidence_cutoff: float | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Freeze evidence membership and policy before any interpretation."""

    if persist:
        ensure_assimilation_tables(store)
    candidate = get_competence_candidate(store, repo, str(competence_id))
    check = verify_competence_candidate(store, repo, str(competence_id))
    if candidate is None or check.get("valid") is not True:
        raise AssimilationError("source competence is not canonically valid")
    explicit_cutoff = evidence_cutoff is not None
    cutoff = float(evidence_cutoff if explicit_cutoff else time.time())
    selection = _merge_policy(DEFAULT_SELECTION_POLICY, selection_policy)
    analysis = _merge_policy(DEFAULT_ANALYSIS_POLICY, analysis_policy)
    if (
        str(selection.get("deduplication_root") or "")
        != DEFAULT_SELECTION_POLICY["deduplication_root"]
        or selection.get("retain_negative_evidence") is not True
        or selection.get("retain_excluded_evidence") is not True
    ):
        raise AssimilationError(
            "selection policy cannot weaken canonical deduplication or evidence retention"
        )
    for policy_key in ("dependence_axes", "independence_axes"):
        axes = analysis.get(policy_key)
        if (
            not isinstance(axes, Sequence)
            or isinstance(axes, (str, bytes))
            or not axes
            or any(not str(axis).strip() for axis in axes)
        ):
            raise AssimilationError(f"{policy_key} must be a nonempty axis list")
        canonical_axes = [
            str(item) for item in DEFAULT_ANALYSIS_POLICY[policy_key]
        ]
        if [str(item) for item in axes] != canonical_axes:
            raise AssimilationError(
                f"{policy_key} is a constitutional v9.5 evidence boundary"
            )
    if dict(analysis.get("dependence_admission") or {}) != dict(
        DEFAULT_ANALYSIS_POLICY["dependence_admission"]
    ):
        raise AssimilationError(
            "dependence admission policy cannot be weakened by the caller"
        )
    if (
        str(analysis.get("causal_interpretation") or "")
        != DEFAULT_ANALYSIS_POLICY["causal_interpretation"]
        or analysis.get("broaden_applicability") is not False
    ):
        raise AssimilationError(
            "analysis policy cannot manufacture causality or applicability broadening"
        )
    required_classes = {
        str(item) for item in selection.get("required_evidence_classes") or ()
    }
    if required_classes != {
        EVIDENCE_LIVE,
        EVIDENCE_ATTESTED,
    }:
        raise AssimilationError(
            "production cohort evidence classes are a canonical boundary"
        )
    if feedback_ids is None:
        if explicit_cutoff:
            # v9.5 has no immutable precommitment created before an arbitrary
            # historical cutoff. Preserve the as-of cohort for inspection,
            # but do not let hindsight choose a promotable time window.
            selection["selection_mode"] = "structural_explicit_cutoff"
            selection_integrity = SELECTION_STRUCTURAL_CUTOFF
            selection_integrity_state = UNKNOWN
            selection_production_eligible = False
        else:
            selection["selection_mode"] = "all_canonical_before_cutoff"
            selection_integrity = SELECTION_CANONICAL_ALL
            selection_integrity_state = PASS
            selection_production_eligible = True
        requested = []
        for item in list_distribution_feedback(store, repo):
            feedback_id = str(item.get("feedback_id") or "")
            created_at = float(item.get("created_at") or 0.0)
            package = get_distribution_package(
                store, repo, str(item.get("package_id") or "")
            )
            if (
                feedback_id
                and created_at <= cutoff
                and package is not None
                and str(package.get("competence_id") or "")
                == str(competence_id)
            ):
                requested.append(feedback_id)
    else:
        requested = [str(item) for item in feedback_ids]
        selection["selection_mode"] = "explicit_feedback_ids"
        selection["explicit_feedback_ids"] = sorted(set(requested))
        # v9.5 has no canonical precommitment receipt for an arbitrary subset.
        # Freeze it for reproducible structural inspection, but never let a
        # post-hoc selection manufacture production revision evidence.
        selection_integrity = SELECTION_STRUCTURAL_SUBSET
        selection_integrity_state = UNKNOWN
        selection_production_eligible = False
    request_counts = Counter(requested)
    unique_ids = sorted(request_counts)
    observations: list[dict[str, Any]] = []
    first_by_identity: dict[str, str] = {}
    for feedback_id in unique_ids:
        observation = resolve_feedback_observation(
            store,
            repo,
            feedback_id,
            competence_id=str(competence_id),
            as_of=cutoff,
        )
        observation = _apply_selection_policy(observation, selection)
        identity = str(observation.get("observation_identity") or "")
        duplicate_of = first_by_identity.get(identity) if identity else None
        if identity and duplicate_of is None:
            first_by_identity[identity] = feedback_id
        observation = {
            **observation,
            "requested_repetitions": int(request_counts[feedback_id]),
            "duplicate_of_feedback_id": duplicate_of,
            "duplicate_observation": duplicate_of is not None,
        }
        observations.append(observation)
    counts = _cohort_counts(
        observations,
        requested_count=len(requested),
        unique_feedback_count=len(unique_ids),
    )
    repository_id = _repo_identity(store, repo)
    created_at = time.time()
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "repo": repo,
        "repository_id": repository_id,
        "competence_id": str(competence_id),
        "competence_receipt_hash": candidate.get("receipt_hash"),
        "source_competence_id": str(competence_id),
        "source_competence_receipt_hash": candidate.get("receipt_hash"),
        "evidence_cutoff": cutoff,
        "feedback_ids": unique_ids,
        "selection_policy": selection,
        "selection_policy_hash": _sha(selection),
        "selection_integrity": selection_integrity,
        "selection_integrity_state": selection_integrity_state,
        "selection_production_eligible": selection_production_eligible,
        # Cohort formation establishes selection integrity only. The analysis
        # receipt must still establish empirical and scope eligibility.
        "production_revision_eligible": False,
        "analysis_policy": analysis,
        "analysis_policy_hash": _sha(analysis),
        "observations": observations,
        "counts": counts,
        "evidence_roots": sorted(
            {
                str(root)
                for item in observations
                for root in (
                    item.get("package_use_receipt_hash"),
                    (item.get("canonical_outcome") or {}).get("receipt_hash"),
                    (item.get("canonical_witness") or {}).get("witness_result_hash"),
                )
                if root
            }
        ),
        "frozen": True,
        "membership_mutable": False,
        "thresholds_mutable": False,
        "counterevidence_retained": True,
        "created_at": created_at,
        **AUTHORITY_FALSE,
    }
    material["evidence_root"] = _sha(material["evidence_roots"])
    cohort_hash = _sha(material)
    body = {
        **material,
        "cohort_id": cohort_hash,
        "cohort_hash": cohort_hash,
    }
    if not persist:
        return {**body, "inserted": False, "persistence": "advisory_only"}
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT cohort_json FROM competence_assimilation_cohorts WHERE repository_id=? AND cohort_id=?",
            (repository_id, cohort_hash),
        ).fetchone()
        if existing is not None:
            prior = _json(existing["cohort_json"]) or body
            return {**prior, "inserted": False, "duplicate": True}
        conn.execute(
            """INSERT INTO competence_assimilation_cohorts(
                cohort_id, cohort_hash, repository_id, repo, competence_id,
                competence_receipt_hash, evidence_cutoff, selection_policy_hash,
                analysis_policy_hash, cohort_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cohort_hash,
                cohort_hash,
                repository_id,
                repo,
                str(competence_id),
                str(candidate.get("receipt_hash") or ""),
                cutoff,
                material["selection_policy_hash"],
                material["analysis_policy_hash"],
                _canonical(body),
                body["created_at"],
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def get_evidence_cohort(store: Any, repo: str, cohort_id: str) -> dict[str, Any] | None:
    row = store.db.execute(
        "SELECT cohort_hash, cohort_json FROM competence_assimilation_cohorts WHERE repository_id=? AND repo=? AND cohort_id=?",
        (_repo_identity(store, repo), repo, str(cohort_id)),
    ).fetchone()
    if row is None:
        return None
    body = _json(row["cohort_json"])
    if body is not None:
        body["ledger_hash"] = str(row["cohort_hash"])
    return body


def verify_evidence_cohort(store: Any, repo: str, cohort_id: str) -> dict[str, Any]:
    cohort = get_evidence_cohort(store, repo, cohort_id)
    if cohort is None:
        return {"valid": False, "state": UNKNOWN, "errors": ["cohort_missing"], **AUTHORITY_FALSE}
    errors: list[str] = []
    expected = _sha(_cohort_material(cohort))
    if expected != str(cohort.get("cohort_hash") or ""):
        errors.append("cohort_hash_invalid")
    if str(cohort.get("cohort_id") or "") != str(cohort_id):
        errors.append("cohort_identity_invalid")
    if str(cohort.get("ledger_hash") or "") != str(cohort.get("cohort_hash") or ""):
        errors.append("cohort_ledger_hash_invalid")
    candidate_check = verify_competence_candidate(
        store, repo, str(cohort.get("competence_id") or "")
    )
    if candidate_check.get("valid") is not True:
        errors.append("cohort_competence_invalid")
    if _sha(cohort.get("selection_policy") or {}) != str(cohort.get("selection_policy_hash") or ""):
        errors.append("selection_policy_hash_invalid")
    if _sha(cohort.get("analysis_policy") or {}) != str(cohort.get("analysis_policy_hash") or ""):
        errors.append("analysis_policy_hash_invalid")
    if str(cohort.get("repo") or "") != str(repo):
        errors.append("cohort_repository_name_invalid")
    if str(cohort.get("repository_id") or "") != _repo_identity(store, repo):
        errors.append("cohort_repository_identity_invalid")
    candidate = get_competence_candidate(
        store, repo, str(cohort.get("competence_id") or "")
    )
    if candidate is None or str(candidate.get("receipt_hash") or "") != str(
        cohort.get("competence_receipt_hash") or ""
    ):
        errors.append("cohort_competence_receipt_binding_invalid")
    seen: set[str] = set()
    first_by_identity: dict[str, str] = {}
    recomputed_observations: list[dict[str, Any]] = []
    for frozen in list(cohort.get("observations") or ()):
        if not isinstance(frozen, Mapping):
            errors.append("cohort_observation_invalid")
            continue
        feedback_id = str(frozen.get("feedback_id") or "")
        if feedback_id in seen:
            errors.append("cohort_feedback_membership_duplicate")
        seen.add(feedback_id)
        current = resolve_feedback_observation(
            store,
            repo,
            feedback_id,
            competence_id=str(cohort.get("competence_id") or ""),
            as_of=float(cohort.get("evidence_cutoff") or 0.0),
        )
        current = _apply_selection_policy(
            current, dict(cohort.get("selection_policy") or {})
        )
        identity = str(current.get("observation_identity") or "")
        duplicate_of = first_by_identity.get(identity) if identity else None
        if identity and duplicate_of is None:
            first_by_identity[identity] = feedback_id
        current = {
            **current,
            "requested_repetitions": int(frozen.get("requested_repetitions") or 0),
            "duplicate_of_feedback_id": duplicate_of,
            "duplicate_observation": duplicate_of is not None,
        }
        recomputed_observations.append(current)
        if dict(frozen) != current:
            errors.append("cohort_observation_reconstruction_mismatch")
    frozen_ids = [
        str(item.get("feedback_id") or "")
        for item in cohort.get("observations") or ()
        if isinstance(item, Mapping)
    ]
    if frozen_ids != sorted(frozen_ids):
        errors.append("cohort_feedback_membership_not_canonical")
    if sorted(str(item) for item in cohort.get("feedback_ids") or ()) != frozen_ids:
        errors.append("cohort_feedback_id_index_mismatch")
    selection = dict(cohort.get("selection_policy") or {})
    mode = str(selection.get("selection_mode") or "")
    if mode == "all_canonical_before_cutoff":
        if cohort.get("selection_integrity") != SELECTION_CANONICAL_ALL:
            errors.append("cohort_selection_integrity_invalid")
        if cohort.get("selection_integrity_state") != PASS:
            errors.append("cohort_selection_integrity_state_invalid")
        if cohort.get("selection_production_eligible") is not True:
            errors.append("cohort_selection_production_gate_invalid")
        expected_ids: list[str] = []
        cutoff = float(cohort.get("evidence_cutoff") or 0.0)
        for item in list_distribution_feedback(store, repo):
            package = get_distribution_package(
                store, repo, str(item.get("package_id") or "")
            )
            if (
                str(item.get("feedback_id") or "")
                and float(item.get("created_at") or 0.0) <= cutoff
                and package is not None
                and str(package.get("competence_id") or "")
                == str(cohort.get("competence_id") or "")
            ):
                expected_ids.append(str(item.get("feedback_id")))
        if sorted(set(expected_ids)) != frozen_ids:
            errors.append("cohort_all_evidence_membership_mismatch")
    elif mode == "explicit_feedback_ids":
        if cohort.get("selection_integrity") != SELECTION_STRUCTURAL_SUBSET:
            errors.append("cohort_selection_integrity_invalid")
        if cohort.get("selection_integrity_state") != UNKNOWN:
            errors.append("cohort_selection_integrity_state_invalid")
        if cohort.get("selection_production_eligible") is not False:
            errors.append("cohort_selection_production_gate_invalid")
        if sorted(str(item) for item in selection.get("explicit_feedback_ids") or ()) != frozen_ids:
            errors.append("cohort_explicit_membership_mismatch")
    elif mode == "structural_explicit_cutoff":
        if cohort.get("selection_integrity") != SELECTION_STRUCTURAL_CUTOFF:
            errors.append("cohort_selection_integrity_invalid")
        if cohort.get("selection_integrity_state") != UNKNOWN:
            errors.append("cohort_selection_integrity_state_invalid")
        if cohort.get("selection_production_eligible") is not False:
            errors.append("cohort_selection_production_gate_invalid")
        expected_ids = []
        cutoff = float(cohort.get("evidence_cutoff") or 0.0)
        for item in list_distribution_feedback(store, repo):
            package = get_distribution_package(
                store, repo, str(item.get("package_id") or "")
            )
            if (
                str(item.get("feedback_id") or "")
                and float(item.get("created_at") or 0.0) <= cutoff
                and package is not None
                and str(package.get("competence_id") or "")
                == str(cohort.get("competence_id") or "")
            ):
                expected_ids.append(str(item.get("feedback_id")))
        if sorted(set(expected_ids)) != frozen_ids:
            errors.append("cohort_all_evidence_membership_mismatch")
    else:
        errors.append("cohort_selection_mode_invalid")
    if cohort.get("production_revision_eligible") is not False:
        errors.append("cohort_cannot_self_authorize_production_revision")
    recomputed_roots = sorted(
        {
            str(root)
            for item in recomputed_observations
            for root in (
                item.get("package_use_receipt_hash"),
                (item.get("canonical_outcome") or {}).get("receipt_hash"),
                (item.get("canonical_witness") or {}).get("witness_result_hash"),
            )
            if root
        }
    )
    if recomputed_roots != list(cohort.get("evidence_roots") or ()):
        errors.append("cohort_evidence_roots_mismatch")
    if _sha(recomputed_roots) != str(cohort.get("evidence_root") or ""):
        errors.append("cohort_evidence_root_hash_mismatch")
    recomputed_counts = _cohort_counts(
        recomputed_observations,
        requested_count=sum(
            int(item.get("requested_repetitions") or 0)
            for item in recomputed_observations
        ),
        unique_feedback_count=len(recomputed_observations),
    )
    if recomputed_counts != dict(cohort.get("counts") or {}):
        errors.append("cohort_counts_mismatch")
    return {
        "valid": not errors,
        "state": PASS if not errors else FAIL,
        "errors": sorted(set(errors)),
        "cohort_id": cohort_id,
        "cohort": cohort,
        **AUTHORITY_FALSE,
    }


def _complete_axis(item: Mapping[str, Any], axis: str) -> str | None:
    value = item.get(axis)
    if value is None or value == "":
        return None
    if isinstance(value, (Mapping, list, tuple)) and not value:
        return None
    return _canonical(value) if isinstance(value, (Mapping, list, tuple)) else str(value)


def derive_dependence(
    observations: Sequence[Mapping[str, Any]], policy: Mapping[str, Any]
) -> dict[str, Any]:
    eligible = [
        dict(item)
        for item in observations
        if item.get("empirically_eligible") is True
        and item.get("duplicate_observation") is not True
    ]
    axes = [str(item) for item in policy.get("dependence_axes") or ()]
    independence_axes = [str(item) for item in policy.get("independence_axes") or ()]
    clusters: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []
    for item in eligible:
        values = {axis: _complete_axis(item, axis) for axis in axes}
        if any(value is None for value in values.values()):
            unresolved.append(str(item.get("observation_identity") or item.get("feedback_id") or ""))
            key = _sha({"unresolved": item.get("observation_identity")})
            complete = False
        else:
            key = _sha(values)
            complete = True
        cluster = clusters.setdefault(
            key,
            {
                "cluster_id": key,
                "axis_values": values,
                "complete": complete,
                "observation_ids": [],
                "support_count": 0,
                "contradiction_count": 0,
            },
        )
        cluster["observation_ids"].append(item.get("observation_identity"))
        if item.get("outcome_success") is True:
            cluster["support_count"] += 1
        elif item.get("outcome_success") is False:
            cluster["contradiction_count"] += 1
    relation_counts: Counter[str] = Counter()
    parent = list(range(len(eligible)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left_index: int, right_index: int) -> None:
        left_root = find(left_index)
        right_root = find(right_index)
        if left_root != right_root:
            parent[right_root] = left_root

    pair_relations: list[dict[str, Any]] = []
    unresolved_pair_observation_ids: set[str] = set()
    indexed = list(enumerate(eligible))
    for (left_index, left), (right_index, right) in combinations(indexed, 2):
        if not independence_axes:
            relation = "unresolved"
            shared_axes: list[str] = []
        else:
            left_values = [
                _complete_axis(left, axis) for axis in independence_axes
            ]
            right_values = [
                _complete_axis(right, axis) for axis in independence_axes
            ]
            if any(value is None for value in left_values + right_values):
                relation = "unresolved"
                shared_axes = []
            else:
                shared_axes = [
                    axis
                    for axis, left_value, right_value in zip(
                        independence_axes,
                        left_values,
                        right_values,
                        strict=True,
                    )
                    if left_value == right_value
                ]
                if len(shared_axes) == len(independence_axes):
                    relation = "strongly_dependent"
                elif shared_axes:
                    relation = "partially_dependent"
                else:
                    relation = "independent_under_declared_policy"
        relation_counts[relation] += 1
        pair_relations.append(
            {
                "left_observation_id": left.get("observation_identity"),
                "right_observation_id": right.get("observation_identity"),
                "relation": relation,
                "shared_axes": shared_axes,
            }
        )
        if relation == "unresolved":
            unresolved_pair_observation_ids.update(
                {
                    str(left.get("observation_identity") or ""),
                    str(right.get("observation_identity") or ""),
                }
            )
        if relation != "independent_under_declared_policy":
            # Non-independent and unresolved relations form one conservative
            # component. Repetition inside that component cannot increment
            # replication evidence.
            union(left_index, right_index)

    components: dict[int, dict[str, Any]] = {}
    unresolved_ids = set(unresolved)
    for index, item in indexed:
        root = find(index)
        observation_id = str(
            item.get("observation_identity") or item.get("feedback_id") or ""
        )
        component = components.setdefault(
            root,
            {
                "observation_ids": [],
                "complete": True,
                "support_count": 0,
                "contradiction_count": 0,
            },
        )
        component["observation_ids"].append(observation_id)
        if observation_id in unresolved_ids or observation_id in unresolved_pair_observation_ids:
            component["complete"] = False
        if item.get("outcome_success") is True:
            component["support_count"] += 1
        elif item.get("outcome_success") is False:
            component["contradiction_count"] += 1
    policy_components: list[dict[str, Any]] = []
    for component in components.values():
        observation_ids = sorted(component["observation_ids"])
        policy_components.append(
            {
                **component,
                "component_id": _sha(
                    {
                        "observation_ids": observation_ids,
                        "independence_axes": independence_axes,
                    }
                ),
                "observation_ids": observation_ids,
            }
        )
    policy_components.sort(key=lambda item: item["component_id"])
    complete_components = sum(
        1 for item in policy_components if item["complete"] is True
    )
    return {
        "raw_eligible_count": len(eligible),
        "complete_cluster_count": sum(1 for item in clusters.values() if item["complete"]),
        "policy_separated_component_count": complete_components,
        # Compatibility projection. This is deliberately not named or
        # described as independent support.
        "effective_evidence_count": complete_components,
        "independent_support_count": None,
        "effective_count_semantics": (
            "conservative_policy_separated_components; not a count of "
            "independent support and not a probability"
        ),
        "dependence_clusters": sorted(clusters.values(), key=lambda item: item["cluster_id"]),
        "policy_separated_components": policy_components,
        "unresolved_dependence": sorted(set(unresolved)),
        "unresolved_pair_count": int(relation_counts.get("unresolved", 0)),
        "pair_relation_counts": dict(sorted(relation_counts.items())),
        "pair_relations": pair_relations,
        "dependence_axes": axes,
        "independence_axes": independence_axes,
        "dependence_admission": dict(policy.get("dependence_admission") or {}),
    }


def derive_diversity(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    eligible = [
        item
        for item in observations
        if item.get("empirically_eligible") is True
        and item.get("duplicate_observation") is not True
    ]
    axes = {
        "targets": "target_id",
        "target_classes": "target_class",
        "environments": "environment_hash",
        "models": "model_identity_hash",
        "model_families": "model_family",
        "provider_families": "provider_family",
        "task_contracts": "task_contract_hash",
        "profiles": "profile_id",
        "packages": "package_id",
    }
    result: dict[str, Any] = {}
    for label, key in axes.items():
        values = sorted({str(item.get(key)) for item in eligible if item.get(key) not in {None, ""}})
        result[label] = {"count": len(values), "values": values}
    timestamps = sorted(
        float(item.get("feedback_created_at") or 0.0)
        for item in eligible
        if float(item.get("feedback_created_at") or 0.0) > 0
    )
    result["temporal_span_seconds"] = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0.0
    result["temporal_repetition_count"] = len(timestamps)
    return result


def _global_policy_pass(
    dependence: Mapping[str, Any], diversity: Mapping[str, Any], policy: Mapping[str, Any]
) -> tuple[bool, list[str]]:
    configured = policy.get("global_contradiction")
    configured = configured if isinstance(configured, Mapping) else {}
    minimum_clusters = configured.get("minimum_complete_clusters")
    reasons: list[str] = []
    component_count = int(
        dependence.get("policy_separated_component_count") or 0
    )
    if minimum_clusters in {None, ""}:
        reasons.append("global_minimum_complete_clusters_not_declared")
    elif component_count < int(minimum_clusters):
        reasons.append("insufficient_independent_clusters")
    if component_count < 2:
        reasons.append("global_policy_separated_replication_absent")
    required_admission = {
        "strongly_dependent": "collapse",
        "partially_dependent": "collapse",
        "unresolved": "collapse_and_block_global",
    }
    if dict(policy.get("dependence_admission") or {}) != required_admission:
        reasons.append("unsupported_dependence_admission_policy")
    requirements = configured.get("minimum_diversity")
    requirements = requirements if isinstance(requirements, Mapping) else {}
    if not requirements:
        reasons.append("global_minimum_diversity_not_declared")
    for axis, minimum in requirements.items():
        actual = int((diversity.get(str(axis)) or {}).get("count") or 0)
        if actual < int(minimum):
            reasons.append(f"insufficient_diversity:{axis}")
    if dependence.get("unresolved_dependence"):
        reasons.append("unresolved_dependence")
    if int(dependence.get("unresolved_pair_count") or 0) > 0:
        reasons.append("unresolved_pair_dependence")
    # These are constitutional floors, not configurable scores: one target,
    # one model family, or one provider family cannot manufacture a global
    # contradiction through repetition.
    for axis in ("targets", "model_families", "provider_families"):
        if int((diversity.get(axis) or {}).get("count") or 0) < 2:
            reasons.append(f"global_{axis}_diversity_absent")
    return not reasons, sorted(set(reasons))


def derive_scope(
    observations: Sequence[Mapping[str, Any]],
    dependence: Mapping[str, Any],
    diversity: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    eligible = [
        item
        for item in observations
        if item.get("empirically_eligible") is True
        and item.get("duplicate_observation") is not True
    ]
    support = [item for item in eligible if item.get("outcome_success") is True]
    contradiction = [item for item in eligible if item.get("outcome_success") is False]
    unresolved = [item for item in eligible if not isinstance(item.get("outcome_success"), bool)]
    scope = "unresolved"
    reason = "no_empirically_eligible_evidence"
    proposed = "unresolved"
    applicability_change: dict[str, Any] = {}
    global_state = UNKNOWN
    global_reasons: list[str] = []
    uncertainty_increased = False
    scope_blockers: list[str] = []
    discriminator: dict[str, Any] = {
        "state": UNKNOWN,
        "axis": None,
        "supported_values": [],
        "contradicted_values": [],
    }

    def axis_partition(key: str) -> tuple[set[str], set[str], bool]:
        support_values = [_complete_axis(item, key) for item in support]
        contradiction_values = [_complete_axis(item, key) for item in contradiction]
        complete = bool(support) and bool(contradiction) and all(
            value is not None for value in support_values + contradiction_values
        )
        return (
            {str(value) for value in support_values if value is not None},
            {str(value) for value in contradiction_values if value is not None},
            complete,
        )

    partitions = {
        axis: axis_partition(axis)
        for axis in ("target_id", "environment_hash", "target_class", "model_family")
    }
    mixed_components = sorted(
        str(item.get("component_id") or "")
        for item in dependence.get("policy_separated_components") or ()
        if isinstance(item, Mapping)
        and int(item.get("support_count") or 0) > 0
        and int(item.get("contradiction_count") or 0) > 0
    )

    def disjoint_discriminator(axis: str) -> bool:
        good, bad, complete = partitions[axis]
        return complete and bool(good) and bool(bad) and good.isdisjoint(bad)

    def set_discriminator(axis: str) -> None:
        nonlocal discriminator
        good, bad, _ = partitions[axis]
        discriminator = {
            "state": PASS,
            "axis": axis,
            "supported_values": sorted(good),
            "contradicted_values": sorted(bad),
        }

    if eligible and not contradiction:
        scope = "supporting_evidence"
        reason = "verified_support_without_scope_broadening"
        proposed = "preserve"
    elif contradiction:
        good_targets, bad_targets, targets_complete = partitions["target_id"]
        _, bad_envs, _ = partitions["environment_hash"]
        _, bad_classes, _ = partitions["target_class"]
        _, bad_models, _ = partitions["model_family"]
        if (
            len(bad_targets) == 1
            and all(_complete_axis(item, "target_id") is not None for item in contradiction)
            and (not support or (targets_complete and good_targets.isdisjoint(bad_targets)))
        ):
            # A target-local exception changes applicability for that target;
            # leaving it as a detached annotation would let future package
            # projection ignore the evidence.  Emit a semantic narrowing so
            # explicit promotion creates an enforceable successor constraint.
            scope, proposed = "local_exception", "narrow_applicability"
            reason = "contradiction_confined_to_one_target_requires_narrowing"
            applicability_change = {"exclude_target_ids": sorted(bad_targets)}
            if support:
                set_discriminator("target_id")
        elif (
            len(bad_envs) == 1
            and disjoint_discriminator("environment_hash")
        ):
            scope, proposed = "environment_specific_exception", "narrow_applicability"
            reason = "failure_confined_to_environment_with_support_elsewhere"
            applicability_change = {"exclude_environment_hashes": sorted(bad_envs)}
            set_discriminator("environment_hash")
        elif (
            len(bad_classes) == 1
            and disjoint_discriminator("target_class")
        ):
            scope, proposed = "target_class_exception", "narrow_applicability"
            reason = "failure_confined_to_target_class_with_support_elsewhere"
            applicability_change = {"exclude_target_classes": sorted(bad_classes)}
            set_discriminator("target_class")
        elif (
            len(bad_models) == 1
            and disjoint_discriminator("model_family")
        ):
            scope, proposed = "model_capability_exception", "narrow_applicability"
            reason = "failure_confined_to_model_family_with_support_elsewhere"
            applicability_change = {"exclude_model_families": sorted(bad_models)}
            set_discriminator("model_family")
        elif support:
            specialization_axis = next(
                (
                    axis
                    for axis in (
                        "environment_hash",
                        "target_class",
                        "model_family",
                        "target_id",
                    )
                    if disjoint_discriminator(axis)
                ),
                None,
            )
            if specialization_axis is None:
                scope, proposed = "unresolved", "unresolved"
                reason = (
                    "support_and_contradiction_share_dependence_component"
                    if mixed_components
                    else "support_and_contradiction_lack_disjoint_canonical_discriminator"
                )
                uncertainty_increased = True
                scope_blockers.append(
                    "mixed_outcomes_within_dependence_component"
                    if mixed_components
                    else "canonical_discriminator_missing_or_overlapping"
                )
            else:
                set_discriminator(specialization_axis)
                supported_values, contradicted_values, _ = partitions[
                    specialization_axis
                ]
                change_keys = {
                    "environment_hash": (
                        "supported_environment_hashes",
                        "contradicted_environment_hashes",
                    ),
                    "target_class": (
                        "supported_target_classes",
                        "contradicted_target_classes",
                    ),
                    "model_family": (
                        "supported_model_families",
                        "contradicted_model_families",
                    ),
                    "target_id": (
                        "supported_target_ids",
                        "contradicted_target_ids",
                    ),
                }
                supported_key, contradicted_key = change_keys[specialization_axis]
                scope, proposed = "competence_specialization_candidate", "specialize"
                reason = "support_and_contradiction_have_disjoint_canonical_regimes"
                applicability_change = {
                    supported_key: sorted(supported_values),
                    contradicted_key: sorted(contradicted_values),
                }
        else:
            global_ok, global_reasons = _global_policy_pass(dependence, diversity, policy)
            global_state = PASS if global_ok else UNKNOWN
            if global_ok:
                scope, proposed = "global_contradiction_candidate", "challenge"
                reason = "declared_global_independence_and_diversity_policy_satisfied"
            else:
                scope, proposed = "unresolved", "unresolved"
                reason = "insufficient_diversity_or_independence_for_global_claim"
    return {
        "derived_scope": scope,
        "scope_reason": reason,
        "proposed_revision_type": proposed,
        "proposed_applicability_change": applicability_change,
        "support_observation_ids": sorted(str(item.get("observation_identity")) for item in support),
        "contradiction_observation_ids": sorted(str(item.get("observation_identity")) for item in contradiction),
        "unresolved_observation_ids": sorted(str(item.get("observation_identity")) for item in unresolved),
        "global_contradiction_state": global_state,
        "global_contradiction_reasons": global_reasons,
        "discriminator": discriminator,
        "mixed_dependence_component_ids": mixed_components,
        "dependence_uncertainty_present": bool(mixed_components),
        "dependence_uncertainty_state": (
            "resolved_by_disjoint_discriminator"
            if mixed_components and discriminator.get("state") == PASS
            else "unresolved_mixed_outcomes"
            if mixed_components
            else "none"
        ),
        "scope_blockers": sorted(set(scope_blockers)),
        "uncertainty_increased": uncertainty_increased,
        "caller_scope_labels_ignored": True,
        "applicability_first": True,
        "causal_effect_established": False,
    }


def _analysis_material_from_cohort(cohort: Mapping[str, Any]) -> dict[str, Any]:
    observations = [dict(item) for item in cohort.get("observations") or () if isinstance(item, Mapping)]
    policy = dict(cohort.get("analysis_policy") or {})
    dependence = derive_dependence(observations, policy)
    diversity = derive_diversity(observations)
    scope = derive_scope(observations, dependence, diversity, policy)
    counts = dict(cohort.get("counts") or {})
    counts["effective_evidence_count"] = dependence["effective_evidence_count"]
    selection_integrity = str(cohort.get("selection_integrity") or UNKNOWN)
    selection_integrity_state = str(
        cohort.get("selection_integrity_state") or UNKNOWN
    )
    selection_production_eligible = bool(
        cohort.get("selection_production_eligible") is True
        and selection_integrity == SELECTION_CANONICAL_ALL
        and selection_integrity_state == PASS
    )
    if not selection_production_eligible:
        # Preserve the structural interpretation without exposing it as the
        # production-facing proposal. v9.5 has no canonical selection
        # precommitment object that could make an arbitrary subset admissible.
        structural_scope = {
            "derived_scope": scope["derived_scope"],
            "scope_reason": scope["scope_reason"],
            "proposed_revision_type": scope["proposed_revision_type"],
            "proposed_applicability_change": dict(
                scope["proposed_applicability_change"]
            ),
        }
        scope = {
            **scope,
            "structural_interpretation": structural_scope,
            "derived_scope": "unresolved",
            "scope_reason": "selection_not_canonically_precommitted_for_production",
            "proposed_revision_type": "unresolved",
            "proposed_applicability_change": {},
            "selection_integrity": selection_integrity,
            "selection_integrity_state": selection_integrity_state,
            "selection_production_eligible": False,
            "production_revision_eligible": False,
            "scope_blockers": sorted(
                set(scope.get("scope_blockers") or ())
                | {"post_hoc_or_unresolved_evidence_selection"}
            ),
            "uncertainty_increased": True,
        }
    production_revision_eligible = bool(
        selection_production_eligible
        and int(counts.get("empirically_eligible_count") or 0) > 0
        and scope.get("proposed_revision_type") != "unresolved"
        and scope.get("uncertainty_increased") is not True
        and not dependence.get("unresolved_dependence")
        and int(dependence.get("unresolved_pair_count") or 0) == 0
        and int(counts.get("unknown_count") or 0) == 0
    )
    scope["selection_integrity"] = selection_integrity
    scope["selection_integrity_state"] = selection_integrity_state
    scope["selection_production_eligible"] = selection_production_eligible
    scope["production_revision_eligible"] = production_revision_eligible
    outcome_structure = {
        "support_observation_ids": list(scope["support_observation_ids"]),
        "contradiction_observation_ids": list(
            scope["contradiction_observation_ids"]
        ),
        "unresolved_observation_ids": list(scope["unresolved_observation_ids"]),
        "averaged_into_scalar": False,
    }
    proposed_revision = {
        "revision_type": scope["proposed_revision_type"],
        "applicability_change": dict(scope["proposed_applicability_change"]),
        "scope": scope["derived_scope"],
        "selection_integrity": selection_integrity,
        "selection_integrity_state": selection_integrity_state,
        "production_revision_eligible": production_revision_eligible,
        "verified": False,
        "self_verification_authorized": False,
    }
    return {
        "schema_version": ANALYSIS_SCHEMA,
        "version": VERSION,
        "repo": cohort.get("repo"),
        "repository_id": cohort.get("repository_id"),
        "competence_id": cohort.get("competence_id"),
        "competence_receipt_hash": cohort.get("competence_receipt_hash"),
        "source_competence_id": cohort.get("competence_id"),
        "source_competence_receipt_hash": cohort.get("competence_receipt_hash"),
        "cohort_id": cohort.get("cohort_id"),
        "cohort_hash": cohort.get("cohort_hash"),
        "cohort_receipt_hash": cohort.get("cohort_hash"),
        "evidence_root": cohort.get("evidence_root"),
        "selection_policy": dict(cohort.get("selection_policy") or {}),
        "selection_policy_hash": cohort.get("selection_policy_hash"),
        "selection_integrity": selection_integrity,
        "selection_integrity_state": selection_integrity_state,
        "selection_production_eligible": selection_production_eligible,
        "production_revision_eligible": production_revision_eligible,
        "analysis_policy": policy,
        "analysis_policy_hash": cohort.get("analysis_policy_hash"),
        "counts": counts,
        "dependence": dependence,
        "diversity": diversity,
        "scope": scope,
        "scope_classification": scope,
        "outcome_structure": outcome_structure,
        "proposed_revision": proposed_revision,
        "causal_strength_class": "observational_exposure_bound",
        "causal_effect_established": False,
        "probability_estimate": None,
        "counterevidence_conserved": True,
        "evidence_roots": list(cohort.get("evidence_roots") or ()),
        **AUTHORITY_FALSE,
    }


def analyze_evidence_cohort(
    store: Any, repo: str, cohort_id: str, *, persist: bool = False
) -> dict[str, Any]:
    if persist:
        ensure_assimilation_tables(store)
    check = verify_evidence_cohort(store, repo, cohort_id)
    if check.get("valid") is not True:
        raise AssimilationError("frozen cohort failed canonical verification")
    material = _analysis_material_from_cohort(check["cohort"])
    analysis_hash = _sha(material)
    body = {
        **material,
        "analysis_id": analysis_hash,
        "analysis_hash": analysis_hash,
        "created_at": time.time(),
    }
    if not persist:
        return {**body, "inserted": False, "persistence": "advisory_only"}
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT analysis_json FROM competence_assimilation_analyses WHERE repository_id=? AND analysis_id=?",
            (str(material["repository_id"]), analysis_hash),
        ).fetchone()
        if existing is not None:
            prior = _json(existing["analysis_json"]) or body
            return {**prior, "inserted": False, "duplicate": True}
        conn.execute(
            """INSERT INTO competence_assimilation_analyses(
                analysis_id, analysis_hash, cohort_id, repository_id, repo,
                competence_id, analysis_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                analysis_hash,
                analysis_hash,
                cohort_id,
                str(material["repository_id"]),
                repo,
                str(material["competence_id"]),
                _canonical(body),
                body["created_at"],
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def get_assimilation_analysis(store: Any, repo: str, analysis_id: str) -> dict[str, Any] | None:
    row = store.db.execute(
        "SELECT analysis_hash, analysis_json FROM competence_assimilation_analyses WHERE repository_id=? AND repo=? AND analysis_id=?",
        (_repo_identity(store, repo), repo, str(analysis_id)),
    ).fetchone()
    if row is None:
        return None
    body = _json(row["analysis_json"])
    if body is not None:
        body["ledger_hash"] = str(row["analysis_hash"])
    return body


def verify_assimilation_analysis(store: Any, repo: str, analysis_id: str) -> dict[str, Any]:
    analysis = get_assimilation_analysis(store, repo, analysis_id)
    if analysis is None:
        return {"valid": False, "state": UNKNOWN, "errors": ["analysis_missing"], **AUTHORITY_FALSE}
    cohort_check = verify_evidence_cohort(store, repo, str(analysis.get("cohort_id") or ""))
    errors: list[str] = []
    if cohort_check.get("valid") is not True:
        errors.append("analysis_cohort_invalid")
        recomputed = None
    else:
        recomputed = _analysis_material_from_cohort(cohort_check["cohort"])
        expected = _sha(recomputed)
        if expected != str(analysis.get("analysis_hash") or ""):
            errors.append("analysis_hash_invalid")
        if str(analysis.get("analysis_id") or "") != str(analysis_id):
            errors.append("analysis_identity_invalid")
        if str(analysis.get("ledger_hash") or "") != str(analysis.get("analysis_hash") or ""):
            errors.append("analysis_ledger_hash_invalid")
        for key in ("counts", "dependence", "diversity", "scope", "evidence_roots"):
            if analysis.get(key) != recomputed.get(key):
                errors.append(f"analysis_{key}_mismatch")
    return {
        "valid": not errors,
        "state": PASS if not errors else FAIL,
        "errors": sorted(set(errors)),
        "analysis_id": analysis_id,
        "analysis": analysis,
        "recomputed": recomputed,
        **AUTHORITY_FALSE,
    }


__all__ = [
    "ANALYSIS_SCHEMA",
    "DEFAULT_ANALYSIS_POLICY",
    "DEFAULT_SELECTION_POLICY",
    "SCHEMA",
    "VERSION",
    "AssimilationError",
    "analyze_evidence_cohort",
    "derive_dependence",
    "derive_diversity",
    "derive_scope",
    "ensure_assimilation_tables",
    "freeze_evidence_cohort",
    "get_assimilation_analysis",
    "get_evidence_cohort",
    "resolve_feedback_observation",
    "verify_assimilation_analysis",
    "verify_evidence_cohort",
]
