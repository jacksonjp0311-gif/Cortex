"""v9.4 evidence-typed governed competence distribution.

This module is deliberately a consumer-side fabric, not a second competence
ledger.  Cortex owns immutable competence and transfer evidence; a target
receives an immutable, target-bound package whose current usability is derived
from canonical package events.  Feedback is append-only and advisory until an
independent evidence path verifies it.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from .adapter_provenance import (
    EVIDENCE_ATTESTED,
    EVIDENCE_LIVE,
    EVIDENCE_SIMULATED,
    EVIDENCE_SYNTHETIC,
    EVIDENCE_UNKNOWN,
    evidence_satisfies,
)
from .competence import get_competence_candidate, verify_competence_candidate
from .competence_transfer import (
    get_transfer_trial,
    list_transfer_trials,
    verify_transfer_trial,
)

SCHEMA = "cortex-competence-distribution/1.1"
VERSION = "9.4.0"
GLYPH = "⟿"
EVENT_TYPES = frozenset({"challenge", "quarantine", "revoke", "supersede", "rollback"})
BLOCKING_EVENTS = frozenset({"challenge", "quarantine", "revoke", "supersede", "rollback"})
FEEDBACK_KINDS = frozenset(
    {
        "use",
        "success",
        "local_exception",
        "target_class_exception",
        "global_contradiction",
        "applicability_failure",
        "counterevidence",
    }
)
EMPIRICAL_TRANSFER_READY = frozenset(
    {"empirical_cross_model_verified", "empirical_cross_family_verified"}
)
STRUCTURAL_TRANSFER_READY = frozenset(
    {"structural_cross_model_pass", "structural_cross_family_pass"}
)
CLAIM_BOUNDARY = (
    "A distribution package is a target-bound, revocable projection of a "
    "transfer-verified competence. Package-use evidence proves exact exposure, "
    "not causal benefit, authority, execution permission, universal validity, "
    "or automatic learning."
)


class DistributionError(ValueError):
    """Raised when a governed distribution boundary cannot be established."""


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _repo_identity(store: Any, repo: str) -> tuple[str, Mapping[str, Any]]:
    row = store.db.execute("SELECT * FROM repositories WHERE name=?", (str(repo),)).fetchone()
    if row is None:
        raise DistributionError(f"Unknown repository: {repo}")
    return str(row["repository_id"] or ""), dict(row)


def _json(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    try:
        decoded = json.loads(str(value or ""))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return dict(decoded) if isinstance(decoded, Mapping) else None


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        return [value.decode() if isinstance(value, bytes) else value]
    if isinstance(value, Sequence):
        return list(value)
    return [value]


def _truth_state(value: bool | None) -> str:
    return "pass" if value is True else "fail" if value is False else "unknown"


def ensure_distribution_tables(store: Any) -> None:
    """Install immutable target, package, event, and feedback ledgers."""
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS competence_target_profiles(
            profile_id TEXT PRIMARY KEY CHECK(length(profile_id) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_id TEXT NOT NULL,
            profile_version TEXT NOT NULL,
            profile_hash TEXT NOT NULL CHECK(length(profile_hash) = 64),
            profile_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, target_id, profile_version),
            UNIQUE(repository_id, profile_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_competence_target_profiles_repo
            ON competence_target_profiles(repo, target_id, created_at DESC);
        CREATE TRIGGER IF NOT EXISTS competence_target_profiles_no_delete
        BEFORE DELETE ON competence_target_profiles BEGIN
            SELECT RAISE(ABORT, 'target profiles cannot be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_target_profiles_no_update
        BEFORE UPDATE ON competence_target_profiles BEGIN
            SELECT RAISE(ABORT, 'target profiles cannot be updated');
        END;

        CREATE TABLE IF NOT EXISTS competence_distribution_packages(
            package_id TEXT PRIMARY KEY CHECK(length(package_id) = 64),
            package_hash TEXT NOT NULL CHECK(length(package_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            competence_id TEXT NOT NULL,
            competence_receipt_hash TEXT NOT NULL CHECK(length(competence_receipt_hash) = 64),
            package_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, package_id),
            UNIQUE(repository_id, package_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_competence_distribution_packages_target
            ON competence_distribution_packages(repo, target_id, created_at DESC);
        CREATE TRIGGER IF NOT EXISTS competence_distribution_packages_no_delete
        BEFORE DELETE ON competence_distribution_packages BEGIN
            SELECT RAISE(ABORT, 'distribution packages cannot be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_distribution_packages_no_update
        BEFORE UPDATE ON competence_distribution_packages BEGIN
            SELECT RAISE(ABORT, 'distribution packages cannot be updated');
        END;

        CREATE TABLE IF NOT EXISTS competence_distribution_events(
            event_id TEXT PRIMARY KEY CHECK(length(event_id) = 64),
            package_id TEXT NOT NULL,
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_hash TEXT NOT NULL CHECK(length(event_hash) = 64),
            event_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, event_id),
            UNIQUE(repository_id, event_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_competence_distribution_events_package
            ON competence_distribution_events(repo, package_id, created_at ASC);
        CREATE TRIGGER IF NOT EXISTS competence_distribution_events_no_delete
        BEFORE DELETE ON competence_distribution_events BEGIN
            SELECT RAISE(ABORT, 'distribution events cannot be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_distribution_events_no_update
        BEFORE UPDATE ON competence_distribution_events BEGIN
            SELECT RAISE(ABORT, 'distribution events cannot be updated');
        END;

        CREATE TABLE IF NOT EXISTS competence_usage_feedback(
            feedback_id TEXT PRIMARY KEY CHECK(length(feedback_id) = 64),
            package_id TEXT NOT NULL,
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            target_id TEXT NOT NULL,
            feedback_hash TEXT NOT NULL CHECK(length(feedback_hash) = 64),
            feedback_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, feedback_id),
            UNIQUE(repository_id, feedback_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_competence_usage_feedback_package
            ON competence_usage_feedback(repo, package_id, created_at ASC);
        CREATE TRIGGER IF NOT EXISTS competence_usage_feedback_no_delete
        BEFORE DELETE ON competence_usage_feedback BEGIN
            SELECT RAISE(ABORT, 'usage feedback cannot be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_usage_feedback_no_update
        BEFORE UPDATE ON competence_usage_feedback BEGIN
            SELECT RAISE(ABORT, 'usage feedback cannot be updated');
        END;
        """
    )
    store.db.commit()


def _profile_material(profile: Mapping[str, Any]) -> dict[str, Any]:
    material = {
        "schema_version": str(profile.get("schema_version") or SCHEMA),
        "target_id": str(profile.get("target_id") or ""),
        "profile_version": str(profile.get("profile_version") or "1"),
        "identity": dict(profile.get("identity") or {}),
        "environment": dict(profile.get("environment") or {}),
        "role": str(profile.get("role") or ""),
        "task_family": str(profile.get("task_family") or ""),
        "model_capability": dict(profile.get("model_capability") or {}),
        "available_tools": sorted(str(item) for item in _list(profile.get("available_tools"))),
        "authority_scope": dict(profile.get("authority_scope") or {}),
        "authority_scope_declared": "authority_scope" in profile and isinstance(profile.get("authority_scope"), Mapping),
        "model_capability_declared": "model_capability" in profile and isinstance(profile.get("model_capability"), Mapping),
        "body_epoch_id": str(profile.get("body_epoch_id") or ""),
        "privacy_boundaries": dict(profile.get("privacy_boundaries") or {}),
        "required_competence_types": sorted(str(item) for item in _list(profile.get("required_competence_types"))),
        "prohibited_competence_types": sorted(str(item) for item in _list(profile.get("prohibited_competence_types"))),
        "freshness_ttl_seconds": float(profile.get("freshness_ttl_seconds") or 86400.0),
    }
    # v9.4 policy fields are included only when present.  This preserves the
    # schema-specific identity of immutable v9.3 profiles during inspection.
    for key in (
        "distribution_mode",
        "minimum_evidence_class",
        "currentness_policy",
        "freshness_policy",
    ):
        if key in profile:
            value = profile.get(key)
            material[key] = dict(value) if isinstance(value, Mapping) else value
    return material


def register_target_profile(store: Any, repo: str, profile: Mapping[str, Any]) -> dict[str, Any]:
    """Append one immutable compatibility profile for a consuming system."""
    if not isinstance(profile, Mapping):
        raise DistributionError("target profile must be a mapping")
    ensure_distribution_tables(store)
    repository_id, _ = _repo_identity(store, repo)
    normalized = dict(profile)
    mode = str(normalized.get("distribution_mode") or "production")
    if mode not in {"production", "sandbox"}:
        raise DistributionError("distribution_mode must be production or sandbox")
    requested_minimum = str(normalized.get("minimum_evidence_class") or "")
    if mode == "production":
        # A target may demand stronger evidence, but cannot lower the default
        # production boundary below a live external inference observation.
        if requested_minimum and not evidence_satisfies(
            requested_minimum, EVIDENCE_LIVE
        ):
            raise DistributionError(
                "production target cannot lower empirical evidence requirement"
            )
        normalized["minimum_evidence_class"] = (
            requested_minimum or EVIDENCE_LIVE
        )
    else:
        if requested_minimum and not evidence_satisfies(
            requested_minimum, EVIDENCE_SYNTHETIC
        ):
            raise DistributionError(
                "sandbox target cannot lower evidence requirement below synthetic"
            )
        normalized["minimum_evidence_class"] = (
            requested_minimum or EVIDENCE_SYNTHETIC
        )
    normalized["distribution_mode"] = mode
    normalized.setdefault("currentness_policy", "latest_registered")
    normalized.setdefault(
        "freshness_policy",
        {
            "competence_max_age_seconds": float(
                normalized.get("freshness_ttl_seconds") or 86400.0
            ),
            "transfer_max_age_seconds": float(
                normalized.get("freshness_ttl_seconds") or 86400.0
            ),
            "profile_max_age_seconds": float(
                normalized.get("freshness_ttl_seconds") or 86400.0
            ),
            "package_max_age_seconds": float(
                normalized.get("freshness_ttl_seconds") or 86400.0
            ),
            "feedback_max_age_seconds": float(
                normalized.get("freshness_ttl_seconds") or 86400.0
            ),
        },
    )
    material = _profile_material(normalized)
    if not material["target_id"]:
        raise DistributionError("target_id is required")
    body = {
        **material,
        "repo": str(repo),
        "repository_id": repository_id,
        "profile_id": _sha(material),
        "profile_hash": _sha(material),
        # Ledger time, not a caller timestamp, orders target currentness.
        "created_at": time.time(),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "advisory_only": True,
    }
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT profile_json FROM competence_target_profiles WHERE repository_id=? AND profile_id=?",
            (repository_id, body["profile_id"]),
        ).fetchone()
        if existing is not None:
            prior = _json(existing["profile_json"])
            return {**(prior or body), "inserted": False, "duplicate": True}
        conn.execute(
            """INSERT INTO competence_target_profiles(
                profile_id, repository_id, repo, target_id, profile_version,
                profile_hash, profile_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                body["profile_id"], repository_id, repo, body["target_id"],
                body["profile_version"], body["profile_hash"], _canonical(body), body["created_at"],
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def get_target_profile(store: Any, repo: str, profile_id: str) -> dict[str, Any] | None:
    repository_id, _ = _repo_identity(store, repo)
    row = store.db.execute(
        "SELECT profile_json, profile_hash FROM competence_target_profiles WHERE repository_id=? AND repo=? AND profile_id=?",
        (repository_id, repo, str(profile_id)),
    ).fetchone()
    if row is None:
        return None
    parsed = _json(row["profile_json"])
    if parsed is not None:
        parsed["ledger_profile_hash"] = str(row["profile_hash"] or "")
    return parsed


def list_target_profiles(store: Any, repo: str, target_id: str | None = None) -> list[dict[str, Any]]:
    repository_id, _ = _repo_identity(store, repo)
    if target_id:
        rows = store.db.execute(
            "SELECT profile_json FROM competence_target_profiles WHERE repository_id=? AND repo=? AND target_id=? ORDER BY created_at ASC",
            (repository_id, repo, str(target_id)),
        ).fetchall()
    else:
        rows = store.db.execute(
            "SELECT profile_json FROM competence_target_profiles WHERE repository_id=? AND repo=? ORDER BY created_at ASC",
            (repository_id, repo),
        ).fetchall()
    return [parsed for row in rows if (parsed := _json(row["profile_json"])) is not None]


def _origin_epoch(candidate: Mapping[str, Any]) -> str:
    lineage = candidate.get("evidence_lineage") if isinstance(candidate.get("evidence_lineage"), Mapping) else {}
    trajectories = lineage.get("originating_trajectories") if isinstance(lineage, Mapping) else []
    first = trajectories[0] if isinstance(trajectories, Sequence) and trajectories and isinstance(trajectories[0], Mapping) else {}
    return str(first.get("body_epoch_id") or "")


def _current_event_rows(store: Any, repo: str, package_id: str) -> list[dict[str, Any]]:
    repository_id, _ = _repo_identity(store, repo)
    rows = store.db.execute(
        "SELECT event_json FROM competence_distribution_events WHERE repository_id=? AND repo=? AND package_id=? ORDER BY created_at ASC",
        (repository_id, repo, str(package_id)),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        parsed = _json(row["event_json"])
        if parsed is None:
            continue
        material = {key: value for key, value in parsed.items() if key not in {"event_id", "event_hash", "created_at"}}
        if str(parsed.get("event_id") or "") != _sha(material) or str(parsed.get("event_hash") or "") != _sha(material):
            parsed["__integrity_error"] = "event_hash_invalid"
        result.append(parsed)
    return result


def _global_competence_events(store: Any, repo: str, competence_id: str) -> list[dict[str, Any]]:
    """Resolve explicitly global safety events without treating local feedback as contagion."""
    repository_id, _ = _repo_identity(store, repo)
    rows = store.db.execute(
        """SELECT e.event_json
           FROM competence_distribution_events e
           JOIN competence_distribution_packages p
             ON p.repository_id=e.repository_id AND p.repo=e.repo AND p.package_id=e.package_id
          WHERE e.repository_id=? AND e.repo=? AND p.competence_id=?
          ORDER BY e.created_at ASC""",
        (repository_id, repo, str(competence_id)),
    ).fetchall()
    events: list[dict[str, Any]] = []
    for row in rows:
        parsed = _json(row["event_json"])
        if parsed is None:
            continue
        material = {key: value for key, value in parsed.items() if key not in {"event_id", "event_hash", "created_at"}}
        if str(parsed.get("event_id") or "") != _sha(material) or str(parsed.get("event_hash") or "") != _sha(material):
            parsed["__integrity_error"] = "event_hash_invalid"
        events.append(parsed)
    return [
        event
        for event in events
        if str(event.get("scope") or "target") == "global"
        and str(event.get("event_type") or "") in {"challenge", "quarantine", "revoke"}
    ]


def _event_state(events: Sequence[Mapping[str, Any]]) -> tuple[str, list[str]]:
    blocking: list[str] = []
    for event in events:
        if event.get("__integrity_error"):
            blocking.append("event_integrity_invalid")
        kind = str(event.get("event_type") or "")
        if kind in BLOCKING_EVENTS:
            blocking.append(kind)
    if "revoke" in blocking:
        return "revoked", sorted(set(blocking))
    if "supersede" in blocking:
        return "superseded", sorted(set(blocking))
    if "rollback" in blocking:
        return "rolled_back", sorted(set(blocking))
    if "quarantine" in blocking:
        return "quarantined", sorted(set(blocking))
    if "challenge" in blocking:
        return "challenged", sorted(set(blocking))
    return "active", sorted(set(blocking))


def _transfer_gate(
    store: Any,
    repo: str,
    competence_id: str,
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    trials = list_transfer_trials(store, repo)
    matching: list[dict[str, Any]] = []
    errors: list[str] = []
    mode = str(profile.get("distribution_mode") or "")
    minimum = str(profile.get("minimum_evidence_class") or "")
    if mode not in {"production", "sandbox"} or not minimum:
        return {
            "state": "unknown",
            "transfer_status": "unresolved",
            "trial_ids": [],
            "trial_proofs": [],
            "errors": ["target_evidence_policy_missing_or_legacy"],
            "minimum_evidence_class": minimum or EVIDENCE_UNKNOWN,
            "distribution_mode": mode or "legacy",
        }
    for trial in trials:
        if str(trial.get("competence_id") or "") != competence_id:
            continue
        check = verify_transfer_trial(store, repo, str(trial.get("trial_id") or ""))
        status = str(check.get("portability_status") or "unresolved")
        evidence_class = str(check.get("evidence_class") or EVIDENCE_UNKNOWN)
        status_ready = (
            status in EMPIRICAL_TRANSFER_READY
            if mode == "production"
            else status in EMPIRICAL_TRANSFER_READY | STRUCTURAL_TRANSFER_READY
        )
        evidence_ready = evidence_satisfies(evidence_class, minimum)
        if check.get("valid") is True and status_ready and evidence_ready:
            matching.append(
                {
                    "trial": trial,
                    "check": check,
                    "trial_id": str(trial.get("trial_id") or ""),
                    "receipt_hash": str(check.get("receipt_hash") or ""),
                    "portability_status": status,
                    "evidence_class": evidence_class,
                    "created_at": float(trial.get("created_at") or 0.0),
                    "task_contract_hash": str(
                        trial.get("task_contract_hash") or ""
                    ),
                    "environment": dict(trial.get("environment") or {}),
                    "model_identities": list(
                        trial.get("fresh_model_identities") or ()
                    ),
                }
            )
        elif check.get("valid") is not True:
            errors.extend(str(item) for item in check.get("errors") or ())
        elif not status_ready:
            errors.append("transfer_status_below_target_policy")
        elif not evidence_ready:
            errors.append("transfer_evidence_below_target_policy")
    if not matching:
        return {
            "state": "unknown" if not trials else "fail",
            "transfer_status": "unresolved",
            "trial_ids": [],
            "trial_proofs": [],
            "errors": sorted(set(errors or ["transfer_verified_trial_missing"])),
            "minimum_evidence_class": minimum,
            "distribution_mode": mode,
        }
    latest = sorted(matching, key=lambda item: item["created_at"])[-1]
    proofs = [
        {
            key: item[key]
            for key in (
                "trial_id",
                "receipt_hash",
                "portability_status",
                "evidence_class",
                "created_at",
                "task_contract_hash",
                "environment",
                "model_identities",
            )
        }
        for item in matching
    ]
    return {
        "state": "pass",
        "transfer_status": latest["portability_status"],
        "evidence_class": latest["evidence_class"],
        "trial_ids": [item["trial_id"] for item in matching],
        "trial_proofs": proofs,
        "latest_trial_id": latest["trial_id"],
        "latest_trial_receipt_hash": latest["receipt_hash"],
        "latest_trial_created_at": latest["created_at"],
        "minimum_evidence_class": minimum,
        "distribution_mode": mode,
        "errors": [],
    }


def _verify_bound_transfer_proof(
    store: Any,
    repo: str,
    package: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    proof = (
        dict(package.get("transfer_proof") or {})
        if isinstance(package.get("transfer_proof"), Mapping)
        else {}
    )
    trial_id = str(proof.get("latest_trial_id") or "")
    trial = get_transfer_trial(store, repo, trial_id) if trial_id else None
    if trial is None:
        return {"valid": False, "state": "unknown", "errors": ["bound_transfer_trial_missing"]}
    check = verify_transfer_trial(store, repo, trial_id)
    errors = list(check.get("errors") or ())
    status = str(check.get("portability_status") or "unresolved")
    evidence_class = str(check.get("evidence_class") or EVIDENCE_UNKNOWN)
    mode = str(profile.get("distribution_mode") or "")
    minimum = str(profile.get("minimum_evidence_class") or "")
    ready = (
        status in EMPIRICAL_TRANSFER_READY
        if mode == "production"
        else status in EMPIRICAL_TRANSFER_READY | STRUCTURAL_TRANSFER_READY
    )
    if check.get("valid") is not True:
        errors.append("bound_transfer_trial_invalid")
    if str(check.get("receipt_hash") or "") != str(
        proof.get("latest_trial_receipt_hash") or ""
    ):
        errors.append("bound_transfer_receipt_hash_mismatch")
    if status != str(proof.get("status") or ""):
        errors.append("bound_transfer_status_mismatch")
    if evidence_class != str(proof.get("evidence_class") or ""):
        errors.append("bound_transfer_evidence_class_mismatch")
    if not ready:
        errors.append("bound_transfer_status_below_policy")
    if not evidence_satisfies(evidence_class, minimum):
        errors.append("bound_transfer_evidence_below_policy")
    if str(trial.get("competence_id") or "") != str(
        package.get("competence_id") or ""
    ):
        errors.append("bound_transfer_competence_mismatch")
    canonical_proof = {
        "trial_id": trial_id,
        "receipt_hash": check.get("receipt_hash"),
        "portability_status": status,
        "evidence_class": evidence_class,
        "created_at": float(trial.get("created_at") or 0.0),
        "task_contract_hash": trial.get("task_contract_hash"),
        "environment": dict(trial.get("environment") or {}),
        "model_identities": list(trial.get("fresh_model_identities") or ()),
    }
    proof_rows = [
        dict(item)
        for item in proof.get("trial_proofs") or ()
        if isinstance(item, Mapping)
    ]
    if canonical_proof not in proof_rows:
        errors.append("bound_transfer_result_body_mismatch")
    provenance_rows = (
        (package.get("provenance_roots") or {}).get("transfer_trial_proofs")
        if isinstance(package.get("provenance_roots"), Mapping)
        else None
    )
    if list(provenance_rows or ()) != list(proof.get("trial_proofs") or ()):
        errors.append("package_transfer_provenance_roots_mismatch")
    return {
        "valid": not errors,
        "state": "pass" if not errors else "fail",
        "errors": sorted(set(str(item) for item in errors)),
        "trial_id": trial_id,
        "receipt_hash": check.get("receipt_hash"),
        "status": status,
        "evidence_class": evidence_class,
        "task_contract_hash": canonical_proof["task_contract_hash"],
        "environment": canonical_proof["environment"],
        "model_identities": canonical_proof["model_identities"],
        "created_at": canonical_proof["created_at"],
    }


def _compatibility(candidate: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    target_errors: list[str] = []
    target_unknown: list[str] = []
    environment_errors: list[str] = []
    environment_unknown: list[str] = []
    epoch_errors: list[str] = []
    epoch_unknown: list[str] = []
    candidate_type = str(candidate.get("candidate_type") or "")
    prohibited = {str(item) for item in _list(profile.get("prohibited_competence_types"))}
    required = {str(item) for item in _list(profile.get("required_competence_types"))}
    tools = {str(item) for item in _list(profile.get("available_tools"))}
    needed_tools = {str(item) for item in _list(candidate.get("required_tools"))}
    if candidate_type in prohibited:
        target_errors.append("competence_type_prohibited")
    if required and candidate_type not in required:
        target_errors.append("competence_type_not_required")
    if needed_tools - tools:
        target_errors.append(
            "required_tools_unavailable:" + ",".join(sorted(needed_tools - tools))
        )
    role = str(profile.get("role") or "")
    task_family = str(profile.get("task_family") or "")
    for condition in _list(candidate.get("applicability_conditions")):
        if not isinstance(condition, Mapping):
            continue
        if condition.get("role") and str(condition["role"]) != role:
            target_errors.append("role_incompatible")
        if condition.get("task_family") and str(condition["task_family"]) != task_family:
            target_errors.append("task_family_incompatible")
        if condition.get("body_epoch_id") and str(condition["body_epoch_id"]) != str(profile.get("body_epoch_id") or ""):
            epoch_errors.append("epoch_incompatible")
        if condition.get("repository_id") and str(condition["repository_id"]) != str(candidate.get("repository_id") or ""):
            target_errors.append("repository_incompatible")
    environment = profile.get("environment") if isinstance(profile.get("environment"), Mapping) else {}
    for assumption in _list(candidate.get("environmental_assumptions")):
        if isinstance(assumption, Mapping):
            for key, expected in assumption.items():
                if key not in environment:
                    environment_unknown.append(f"environment_missing:{key}")
                elif environment[key] != expected:
                    environment_errors.append(f"environment_mismatch:{key}")
    if not profile.get("body_epoch_id"):
        epoch_unknown.append("target_epoch_missing")
    if not profile.get("model_capability"):
        target_unknown.append("model_capability_missing")

    def plane(errors: list[str], unknown: list[str]) -> dict[str, Any]:
        state = "fail" if errors else "unknown" if unknown else "pass"
        return {
            "state": state,
            "errors": sorted(set(errors)),
            "unknown": sorted(set(unknown)),
        }

    planes = {
        "target": plane(target_errors, target_unknown),
        "environment": plane(environment_errors, environment_unknown),
        "epoch": plane(epoch_errors, epoch_unknown),
    }
    states = [item["state"] for item in planes.values()]
    state = "fail" if "fail" in states else "unknown" if "unknown" in states else "pass"
    errors = [item for proof in planes.values() for item in proof["errors"]]
    unknown = [item for proof in planes.values() for item in proof["unknown"]]
    return {
        "state": state,
        "selected": state == "pass",
        "errors": sorted(set(errors)),
        "unknown": sorted(set(unknown)),
        "candidate_type": candidate_type,
        "required_tools": sorted(needed_tools),
        "available_tools": sorted(tools),
        "planes": planes,
    }


def _freshness(
    profile: Mapping[str, Any],
    candidate: Mapping[str, Any],
    *,
    transfer: Mapping[str, Any] | None = None,
    package: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = (
        dict(profile.get("freshness_policy") or {})
        if isinstance(profile.get("freshness_policy"), Mapping)
        else {}
    )
    if not policy:
        return {
            "state": "unknown",
            "planes": {},
            "errors": ["freshness_policy_missing_or_legacy"],
        }
    now = time.time()
    sources = {
        "competence": (
            float(candidate.get("created_at") or 0.0),
            policy.get("competence_max_age_seconds"),
        ),
        "transfer_evidence": (
            float(
                (transfer or {}).get("latest_trial_created_at")
                or (transfer or {}).get("created_at")
                or 0.0
            ),
            policy.get("transfer_max_age_seconds"),
        ),
        "target_profile": (
            float(profile.get("created_at") or 0.0),
            policy.get("profile_max_age_seconds"),
        ),
    }
    if package is not None:
        sources["package"] = (
            float(package.get("created_at") or 0.0),
            policy.get("package_max_age_seconds"),
        )
    planes: dict[str, Any] = {}
    for name, (created, raw_limit) in sources.items():
        if not created or raw_limit in {None, ""}:
            planes[name] = {
                "state": "unknown",
                "age_seconds": None,
                "max_age_seconds": raw_limit,
            }
            continue
        limit = float(raw_limit)
        age = max(0.0, now - created)
        planes[name] = {
            "state": "pass" if age <= limit else "fail",
            "age_seconds": age,
            "max_age_seconds": limit,
            "expires_at": created + limit,
        }
    states = [item["state"] for item in planes.values()]
    state = "fail" if "fail" in states else "unknown" if "unknown" in states else "pass"
    return {"state": state, "planes": planes, "errors": []}


def _profile_currentness(
    store: Any, repo: str, profile: Mapping[str, Any]
) -> dict[str, Any]:
    policy = str(profile.get("currentness_policy") or "")
    if policy != "latest_registered":
        return {
            "state": "unknown",
            "reason": "target_currentness_policy_missing_or_legacy",
        }
    profiles = list_target_profiles(store, repo, str(profile.get("target_id") or ""))
    if not profiles:
        return {"state": "unknown", "reason": "target_profile_not_resolvable"}
    latest = sorted(
        profiles, key=lambda item: float(item.get("created_at") or 0.0)
    )[-1]
    if str(latest.get("profile_id") or "") != str(profile.get("profile_id") or ""):
        return {
            "state": "fail",
            "reason": "newer_target_profile_registered",
            "latest_profile_id": latest.get("profile_id"),
        }
    return {
        "state": "pass",
        "reason": "latest_registered_profile_matches",
        "latest_profile_id": latest.get("profile_id"),
    }


def _package_material(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in package.items()
        if key not in {"package_id", "package_hash", "ledger_package_hash", "created_at", "inserted", "duplicate"}
    }


def _package_receipt(package: Mapping[str, Any]) -> str:
    return _sha(_package_material(package))


def project_competence(
    store: Any,
    repo: str,
    *,
    competence_id: str,
    profile_id: str,
    previous_package_id: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Create a target-bound package only when every required distribution gate passes."""
    ensure_distribution_tables(store)
    profile = get_target_profile(store, repo, profile_id)
    candidate = get_competence_candidate(store, repo, competence_id)
    if profile is None or candidate is None:
        return {
            "status": "blocked",
            "errors": ["profile_missing" if profile is None else "candidate_missing"],
            "package_persisted": False,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "advisory_only": True,
        }
    candidate_check = verify_competence_candidate(store, repo, competence_id)
    transfer = _transfer_gate(store, repo, competence_id, profile)
    applicability = _compatibility(candidate, profile)
    freshness = _freshness(profile, candidate, transfer=transfer)
    profile_currentness = _profile_currentness(store, repo, profile)
    events = _current_event_rows(store, repo, previous_package_id) if previous_package_id else []
    previous_state, previous_blocks = _event_state(events)
    global_events = _global_competence_events(store, repo, competence_id)
    gates = {
        "provenance": "pass" if candidate_check.get("valid") is True else "fail",
        "transfer": transfer["state"],
        "competence_active": "fail" if str(candidate.get("revision_state") or candidate.get("ledger_state") or "") in {"revoked", "superseded", "contested"} else "pass",
        "target_compatible": applicability["planes"]["target"]["state"],
        "environment_compatible": applicability["planes"]["environment"]["state"],
        "epoch_compatible": applicability["planes"]["epoch"]["state"],
        "authority_scope_compatible": "pass" if profile.get("authority_scope_declared") is True else "unknown",
        "profile_current": profile_currentness["state"],
        "not_revoked": "fail" if previous_state in {"revoked", "superseded", "quarantined", "challenged", "rolled_back"} or global_events else "pass",
        "freshness": freshness["state"],
    }
    gate_states = list(gates.values())
    overall = "fail" if "fail" in gate_states else "unknown" if "unknown" in gate_states else "pass"
    errors = sorted(
        set(
            transfer.get("errors", [])
            + applicability.get("errors", [])
            + applicability.get("unknown", [])
            + ([str(profile_currentness.get("reason"))] if profile_currentness["state"] != "pass" else [])
            + previous_blocks
            + (["global_competence_event"] if global_events else [])
        )
    )
    if overall != "pass":
        return {
            "status": "blocked",
            "gates": gates,
            "overall": overall,
            "errors": errors or ["distribution_gate_not_pass"],
            "candidate_verification": candidate_check,
            "transfer_verification": transfer,
            "applicability": applicability,
            "freshness": freshness,
            "profile_currentness": profile_currentness,
            "package_persisted": False,
            "policy_effect": False,
            "distribution_authorized": False,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "advisory_only": True,
        }
    repository_id, _ = _repo_identity(store, repo)
    sandbox_only = str(profile.get("distribution_mode") or "") == "sandbox"
    synthetic_evidence = str(transfer.get("evidence_class") or "") in {
        EVIDENCE_SYNTHETIC,
        EVIDENCE_SIMULATED,
    }
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "repo": repo,
        "repository_id": repository_id,
        "target_id": str(profile["target_id"]),
        "profile_id": profile_id,
        "profile_hash": str(profile["profile_hash"]),
        "competence_id": competence_id,
        "competence_receipt_hash": str(candidate.get("receipt_hash") or ""),
        "competence_version": str(candidate.get("version") or "9.1.0"),
        "provenance_roots": {
            "competence_receipt_hash": candidate.get("receipt_hash"),
            "transfer_trial_ids": transfer.get("trial_ids", []),
            "transfer_trial_proofs": transfer.get("trial_proofs", []),
        },
        "transfer_proof": {
            "status": transfer.get("transfer_status"),
            "evidence_class": transfer.get("evidence_class"),
            "minimum_evidence_class": transfer.get("minimum_evidence_class"),
            "distribution_mode": transfer.get("distribution_mode"),
            "latest_trial_id": transfer.get("latest_trial_id"),
            "latest_trial_receipt_hash": transfer.get(
                "latest_trial_receipt_hash"
            ),
            "trial_proofs": transfer.get("trial_proofs", []),
        },
        "applicability_proof": applicability,
        "compatibility_proof": applicability,
        "exclusions": list(candidate.get("failure_conditions") or []),
        "counterevidence": list(candidate.get("counterevidence") or []),
        "freshness": freshness,
        "profile_currentness": profile_currentness,
        "global_events": global_events,
        "revocation_state": "active",
        "previous_package_id": previous_package_id,
        "gates": gates,
        "status": "active",
        "sandbox_only": sandbox_only,
        "synthetic_evidence": synthetic_evidence,
        "non_promotable": sandbox_only or synthetic_evidence,
        "empirical_feedback_eligible": bool(
            not sandbox_only
            and not synthetic_evidence
            and str(transfer.get("evidence_class") or "")
            in {EVIDENCE_LIVE, EVIDENCE_ATTESTED}
        ),
        "distribution_receipt": {"kind": "governed_projection", "source": "cortex.distribution_gate"},
        "distribution_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    body = {
        **material,
        "package_id": _sha(material),
        "package_hash": _sha(material),
        "created_at": time.time(),
    }
    if not persist:
        return {**body, "package_persisted": False}
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT package_json FROM competence_distribution_packages WHERE repository_id=? AND package_id=?",
            (repository_id, body["package_id"]),
        ).fetchone()
        if existing is not None:
            return {**(_json(existing["package_json"]) or body), "package_persisted": True, "duplicate": True}
        conn.execute(
            """INSERT INTO competence_distribution_packages(
                package_id, package_hash, repository_id, repo, target_id,
                profile_id, competence_id, competence_receipt_hash,
                package_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                body["package_id"], body["package_hash"], repository_id, repo,
                body["target_id"], profile_id, competence_id,
                body["competence_receipt_hash"], _canonical(body), body["created_at"],
            ),
        )
    return {**body, "package_persisted": True, "inserted": True, "duplicate": False}


def get_distribution_package(store: Any, repo: str, package_id: str) -> dict[str, Any] | None:
    repository_id, _ = _repo_identity(store, repo)
    row = store.db.execute(
        "SELECT package_json, package_hash FROM competence_distribution_packages WHERE repository_id=? AND repo=? AND package_id=?",
        (repository_id, repo, str(package_id)),
    ).fetchone()
    if row is None:
        return None
    parsed = _json(row["package_json"])
    if parsed is not None:
        parsed["ledger_package_hash"] = str(row["package_hash"] or "")
    return parsed


def list_distribution_packages(store: Any, repo: str, target_id: str | None = None) -> list[dict[str, Any]]:
    repository_id, _ = _repo_identity(store, repo)
    if target_id:
        rows = store.db.execute(
            "SELECT package_json FROM competence_distribution_packages WHERE repository_id=? AND repo=? AND target_id=? ORDER BY created_at ASC",
            (repository_id, repo, str(target_id)),
        ).fetchall()
    else:
        rows = store.db.execute(
            "SELECT package_json FROM competence_distribution_packages WHERE repository_id=? AND repo=? ORDER BY created_at ASC",
            (repository_id, repo),
        ).fetchall()
    return [parsed for row in rows if (parsed := _json(row["package_json"])) is not None]


def verify_distribution_package(store: Any, repo: str, package_id: str) -> dict[str, Any]:
    package = get_distribution_package(store, repo, package_id)
    if package is None:
        return {"valid": False, "state": "unknown", "errors": ["package_missing"], "advisory_only": True}
    errors: list[str] = []
    repository_id, _ = _repo_identity(store, repo)
    if str(package.get("repo") or "") != repo or str(package.get("repository_id") or "") != repository_id:
        errors.append("package_repository_binding_invalid")
    if str(package.get("package_id") or "") != package_id:
        errors.append("package_identity_invalid")
    if _package_receipt(package) != str(package.get("package_hash") or ""):
        errors.append("package_hash_invalid")
    if str(package.get("ledger_package_hash") or "") != str(package.get("package_hash") or ""):
        errors.append("ledger_package_hash_invalid")
    profile = get_target_profile(store, repo, str(package.get("profile_id") or ""))
    candidate = get_competence_candidate(store, repo, str(package.get("competence_id") or ""))
    if profile is None:
        errors.append("profile_missing")
    if candidate is None:
        errors.append("candidate_missing")
    if profile is not None:
        profile_material = _profile_material(profile)
        if _sha(profile_material) != str(profile.get("profile_hash") or ""):
            errors.append("profile_hash_invalid")
        if str(profile.get("profile_id") or "") != _sha(profile_material):
            errors.append("profile_identity_invalid")
        if str(profile.get("ledger_profile_hash") or "") != str(profile.get("profile_hash") or ""):
            errors.append("ledger_profile_hash_invalid")
        if str(package.get("profile_hash") or "") != str(profile.get("profile_hash") or ""):
            errors.append("package_profile_binding_invalid")
        if str(package.get("target_id") or "") != str(profile.get("target_id") or ""):
            errors.append("package_target_binding_invalid")
    candidate_check = verify_competence_candidate(store, repo, str(package.get("competence_id") or "")) if candidate else {"valid": False}
    if candidate_check.get("valid") is not True:
        errors.append("candidate_verification_invalid")
    elif str(package.get("competence_receipt_hash") or "") != str((candidate or {}).get("receipt_hash") or ""):
        errors.append("package_competence_binding_invalid")
    transfer = (
        _verify_bound_transfer_proof(store, repo, package, profile)
        if candidate and profile
        else {"state": "unknown", "valid": False, "errors": ["transfer_binding_unavailable"]}
    )
    if transfer.get("valid") is not True:
        errors.append("transfer_verification_invalid")
        errors.extend(str(item) for item in transfer.get("errors") or ())
    if profile is not None:
        current_compatibility = _compatibility(candidate or {}, profile)
        if current_compatibility != package.get("compatibility_proof"):
            errors.append("compatibility_proof_mismatch")
        currentness = _profile_currentness(store, repo, profile)
        if currentness.get("state") != "pass":
            errors.append("target_profile_not_current")
    else:
        currentness = {"state": "unknown", "reason": "profile_missing"}
    events = _current_event_rows(store, repo, package_id)
    state, blocking = _event_state(events)
    errors.extend(f"package_{item}" for item in blocking)
    global_events = _global_competence_events(store, repo, str(package.get("competence_id") or ""))
    if global_events:
        errors.append("competence_global_event")
    freshness = _freshness(
        profile or {}, candidate or {}, transfer=transfer, package=package
    )
    if freshness.get("state") != "pass":
        errors.append("package_stale")
    return {
        "valid": not errors,
        "state": state if errors and state != "active" else "active" if not errors else "stale",
        "errors": sorted(set(errors)),
        "package_id": package_id,
        "target_id": package.get("target_id"),
        "competence_id": package.get("competence_id"),
        "candidate_verification": candidate_check,
        "transfer_verification": transfer,
        "event_state": state,
        "global_events": global_events,
        "freshness": freshness,
        "profile_currentness": currentness,
        "distribution_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "advisory_only": True,
    }


def build_competence_package_projection(
    store: Any,
    repo: str,
    package_id: str,
    *,
    require_current: bool = True,
) -> dict[str, Any]:
    """Resolve the exact bounded package semantics exposed to an adapter.

    ``require_current=False`` exists only for historical verification.  It
    confirms the immutable package/profile/competence bodies without turning a
    later revocation into a claim that the earlier exposure never occurred.
    """

    package = get_distribution_package(store, repo, package_id)
    if package is None:
        raise DistributionError("package_missing")
    errors: list[str] = []
    if str(package.get("package_id") or "") != str(package_id):
        errors.append("package_identity_invalid")
    if _package_receipt(package) != str(package.get("package_hash") or ""):
        errors.append("package_hash_invalid")
    if str(package.get("ledger_package_hash") or "") != str(
        package.get("package_hash") or ""
    ):
        errors.append("package_ledger_hash_invalid")
    profile = get_target_profile(store, repo, str(package.get("profile_id") or ""))
    candidate = get_competence_candidate(
        store, repo, str(package.get("competence_id") or "")
    )
    if profile is None:
        errors.append("profile_missing")
    else:
        if _sha(_profile_material(profile)) != str(
            profile.get("profile_hash") or ""
        ):
            errors.append("profile_content_hash_invalid")
        if str(profile.get("ledger_profile_hash") or "") != str(
            profile.get("profile_hash") or ""
        ):
            errors.append("profile_ledger_hash_invalid")
        if str(profile.get("profile_hash") or "") != str(
            package.get("profile_hash") or ""
        ):
            errors.append("package_profile_hash_mismatch")
    if candidate is None:
        errors.append("competence_missing")
    else:
        candidate_check = verify_competence_candidate(
            store, repo, str(package.get("competence_id") or "")
        )
        if candidate_check.get("valid") is not True:
            errors.append("competence_verification_invalid")
        if str(candidate.get("receipt_hash") or "") != str(
            package.get("competence_receipt_hash") or ""
        ):
            errors.append("package_competence_hash_mismatch")
    if require_current:
        current = verify_distribution_package(store, repo, package_id)
        if current.get("valid") is not True:
            errors.extend(str(item) for item in current.get("errors") or ())
    if errors:
        raise DistributionError("package projection blocked: " + ",".join(sorted(set(errors))))
    assert profile is not None and candidate is not None
    environment = dict(profile.get("environment") or {})
    target_environment_material = {
        "target_id": profile.get("target_id"),
        "profile_id": profile.get("profile_id"),
        "profile_hash": profile.get("profile_hash"),
        "environment": environment,
        "body_epoch_id": profile.get("body_epoch_id"),
    }
    material = {
        "schema_version": "cortex-competence-package-projection/1.0",
        "package_id": package_id,
        "package_hash": package.get("package_hash"),
        "competence_id": package.get("competence_id"),
        "competence_receipt_hash": package.get("competence_receipt_hash"),
        "profile_id": package.get("profile_id"),
        "profile_hash": package.get("profile_hash"),
        "target_id": package.get("target_id"),
        "target_environment": environment,
        "target_environment_hash": _sha(target_environment_material),
        "target_body_epoch_id": profile.get("body_epoch_id"),
        "task_family": profile.get("task_family"),
        "role": profile.get("role"),
        "available_tools": list(profile.get("available_tools") or ()),
        "authority_scope": dict(profile.get("authority_scope") or {}),
        "competence": {
            "candidate_type": candidate.get("candidate_type"),
            "capability": dict(candidate.get("capability") or {}),
            "intended_outcome": dict(candidate.get("intended_outcome") or {}),
            "prerequisites": list(candidate.get("prerequisites") or ()),
            "applicability_conditions": list(
                candidate.get("applicability_conditions") or ()
            ),
            "environmental_assumptions": list(
                candidate.get("environmental_assumptions") or ()
            ),
            "required_tools": list(candidate.get("required_tools") or ()),
            "failure_conditions": list(
                candidate.get("failure_conditions") or ()
            ),
            "counterevidence": list(candidate.get("counterevidence") or ()),
            "unresolved_uncertainty": list(
                candidate.get("unresolved_uncertainty") or ()
            ),
            "revision_state": candidate.get("revision_state"),
        },
        "exclusions": list(package.get("exclusions") or ()),
        "transfer_proof": dict(package.get("transfer_proof") or {}),
        "sandbox_only": bool(package.get("sandbox_only")),
        "synthetic_evidence": bool(package.get("synthetic_evidence")),
        "non_promotable": bool(package.get("non_promotable")),
        "empirical_feedback_eligible": bool(
            package.get("empirical_feedback_eligible")
        ),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    return {**material, "package_projection_hash": _sha(material)}


def append_distribution_event(
    store: Any,
    repo: str,
    *,
    package_id: str,
    event_type: str,
    reason: str,
    replacement_package_id: str | None = None,
    scope: str = "target",
) -> dict[str, Any]:
    """Append a challenge/quarantine/revocation/supersession event."""
    if event_type not in EVENT_TYPES:
        raise DistributionError(f"unknown distribution event: {event_type}")
    if scope not in {"target", "global"}:
        raise DistributionError("event scope must be target or global")
    package = get_distribution_package(store, repo, package_id)
    if package is None:
        raise DistributionError("package_missing")
    repository_id, _ = _repo_identity(store, repo)
    target_id = str(package.get("target_id") or "")
    material = {
        "schema_version": SCHEMA,
        "event_type": event_type,
        "package_id": package_id,
        "repo": repo,
        "repository_id": repository_id,
        "target_id": target_id,
        "reason": str(reason or ""),
        "replacement_package_id": replacement_package_id,
        "scope": scope,
    }
    if not material["reason"]:
        raise DistributionError("event reason is required")
    body = {**material, "event_id": _sha(material), "event_hash": _sha(material), "created_at": time.time()}
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT event_json FROM competence_distribution_events WHERE repository_id=? AND event_id=?",
            (repository_id, body["event_id"]),
        ).fetchone()
        if existing is not None:
            return {**(_json(existing["event_json"]) or body), "duplicate": True}
        conn.execute(
            """INSERT INTO competence_distribution_events(
                event_id, package_id, repository_id, repo, target_id,
                event_type, event_hash, event_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                body["event_id"], package_id, repository_id, repo, target_id,
                event_type, body["event_hash"], _canonical(body), body["created_at"],
            ),
        )
    return {**body, "duplicate": False}


def revoke_distribution(store: Any, repo: str, package_id: str, *, reason: str) -> dict[str, Any]:
    return append_distribution_event(store, repo, package_id=package_id, event_type="revoke", reason=reason, scope="global")


def quarantine_distribution(store: Any, repo: str, package_id: str, *, reason: str) -> dict[str, Any]:
    return append_distribution_event(store, repo, package_id=package_id, event_type="quarantine", reason=reason, scope="global")


def supersede_distribution(store: Any, repo: str, package_id: str, *, replacement_package_id: str, reason: str) -> dict[str, Any]:
    current = get_distribution_package(store, repo, package_id)
    replacement = get_distribution_package(store, repo, replacement_package_id)
    if current is None or replacement is None:
        raise DistributionError("package_missing")
    if (
        str(current.get("target_id") or "") != str(replacement.get("target_id") or "")
        or str(current.get("competence_id") or "") != str(replacement.get("competence_id") or "")
    ):
        raise DistributionError("replacement_package_binding_invalid")
    if verify_distribution_package(store, repo, replacement_package_id).get("valid") is not True:
        raise DistributionError("replacement package is not valid")
    return append_distribution_event(store, repo, package_id=package_id, event_type="supersede", reason=reason, replacement_package_id=replacement_package_id)


def rollback_distribution(store: Any, repo: str, package_id: str, *, reason: str) -> dict[str, Any]:
    package = get_distribution_package(store, repo, package_id)
    if package is None:
        raise DistributionError("package_missing")
    previous = str(package.get("previous_package_id") or "")
    if not previous or verify_distribution_package(store, repo, previous).get("valid") is not True:
        raise DistributionError("no_previous_valid_package")
    return append_distribution_event(store, repo, package_id=package_id, event_type="rollback", reason=reason, replacement_package_id=previous)


def verify_package_use(
    store: Any,
    repo: str,
    package_use_receipt_hash: str,
    *,
    expected_package_id: str | None = None,
) -> dict[str, Any]:
    """Verify exact package exposure and its same-turn canonical circulation."""

    receipt_check = store.verify_symbiotic_receipt(repo, package_use_receipt_hash)
    errors: list[str] = []
    if receipt_check.get("valid") is not True:
        return {
            "valid": False,
            "state": "unknown"
            if receipt_check.get("verification_status") == "not_found"
            else "binding_failed",
            "errors": ["package_use_receipt_missing_or_invalid"],
            "package_use_receipt_hash": package_use_receipt_hash,
        }
    use = receipt_check.get("receipt") or {}
    if str(use.get("kind") or "") != "competence_package_use":
        errors.append("receipt_is_not_package_use")
    package_id = str(use.get("package_id") or "")
    if expected_package_id is not None and package_id != str(expected_package_id):
        errors.append("package_use_package_mismatch")
    package = get_distribution_package(store, repo, package_id)
    if package is None:
        errors.append("package_use_package_missing")
    else:
        comparisons = {
            "package_hash": package.get("package_hash"),
            "competence_id": package.get("competence_id"),
            "competence_receipt_hash": package.get("competence_receipt_hash"),
            "profile_id": package.get("profile_id"),
            "profile_hash": package.get("profile_hash"),
            "target_id": package.get("target_id"),
        }
        for key, expected in comparisons.items():
            if use.get(key) != expected:
                errors.append(f"package_use_{key}_mismatch")
    session_id = str(use.get("session_id") or "")
    turn_id = int(use.get("turn_id") or 0)
    from .model_circulation import verify_model_circulation

    circulation = verify_model_circulation(
        store, repo, session_id, turn_id=turn_id
    )
    if circulation.get("valid") is not True:
        errors.extend(
            f"package_use_circulation_{item}"
            for item in circulation.get("errors") or ()
        )
    if str(circulation.get("package_use_receipt_hash") or "") != str(
        package_use_receipt_hash
    ):
        errors.append("package_use_not_bound_to_circulation")
    if str(circulation.get("invocation_id") or "") != str(
        use.get("invocation_id") or ""
    ):
        errors.append("package_use_invocation_mismatch")
    if str(circulation.get("evidence_class") or EVIDENCE_UNKNOWN) != str(
        use.get("evidence_class") or EVIDENCE_UNKNOWN
    ):
        errors.append("package_use_evidence_class_mismatch")
    rows = [
        row
        for row in store.symbiotic_session_receipts(repo, session_id)
        if int(row.get("turn_id") or -1) == turn_id
    ]
    by_kind = {str(row.get("kind") or ""): row for row in rows}
    outcome = by_kind.get("model_outcome") or {}
    witness = by_kind.get("model_witness") or {}
    trajectory = by_kind.get("model_trajectory") or {}
    bindings = dict(circulation.get("receipt_bindings") or {})
    expected_content = {
        "model_outcome_content_hash": outcome.get("content_hash"),
        "model_witness_content_hash": witness.get("content_hash"),
        "witness_result_hash": witness.get("witness_result_hash"),
    }
    for key, expected in expected_content.items():
        if use.get(key) != expected:
            errors.append(f"package_use_{key}_mismatch")
    if trajectory.get("package_use_content_hash") != use.get("content_hash"):
        errors.append("trajectory_package_use_content_mismatch")
    current_package = (
        verify_distribution_package(store, repo, package_id)
        if package is not None
        else {"valid": False, "state": "unknown", "errors": ["package_missing"]}
    )
    evidence_class = str(use.get("evidence_class") or EVIDENCE_UNKNOWN)
    return {
        "valid": not errors,
        "state": "pass" if not errors else "binding_failed",
        "errors": sorted(set(errors)),
        "package_use_receipt_hash": package_use_receipt_hash,
        "package_id": package_id,
        "package": package,
        "target_id": use.get("target_id"),
        "profile_id": use.get("profile_id"),
        "competence_id": use.get("competence_id"),
        "session_id": session_id,
        "turn_id": turn_id,
        "invocation_id": use.get("invocation_id"),
        "evidence_class": evidence_class,
        "adapter_provenance": dict(use.get("adapter_provenance") or {}),
        "sandbox_only": bool(use.get("sandbox_only")),
        "synthetic_evidence": bool(use.get("synthetic_evidence")),
        "non_promotable": bool(use.get("non_promotable")),
        "empirical_feedback_eligible": bool(
            use.get("empirical_feedback_eligible")
        ),
        "current_package_valid": current_package.get("valid") is True,
        "current_package_verification": current_package,
        "canonical_outcome": dict(outcome),
        "canonical_witness": dict(witness),
        "canonical_trajectory": dict(trajectory),
        "binding_roots": {
            "package_use_receipt_hash": package_use_receipt_hash,
            "model_invocation_receipt_hash": (
                bindings.get("model_invocation") or {}
            ).get("receipt_hash"),
            "model_outcome_receipt_hash": (
                bindings.get("model_outcome") or {}
            ).get("receipt_hash"),
            "model_witness_receipt_hash": (
                bindings.get("model_witness") or {}
            ).get("receipt_hash"),
            "witness_result_hash": witness.get("witness_result_hash"),
            "model_trajectory_receipt_hash": (
                bindings.get("model_trajectory") or {}
            ).get("receipt_hash"),
        },
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }


def _feedback_verification(
    use_check: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if use_check is None:
        return {
            "state": "unverified",
            "errors": ["canonical_package_use_missing"],
            "aggregation_eligible": False,
        }
    if use_check.get("valid") is not True:
        return {
            "state": str(use_check.get("state") or "binding_failed"),
            "errors": list(use_check.get("errors") or ()),
            "aggregation_eligible": False,
        }
    if use_check.get("current_package_valid") is not True:
        return {
            "state": "unknown",
            "errors": ["package_or_target_currentness_unresolved"],
            "aggregation_eligible": False,
        }
    evidence_class = str(use_check.get("evidence_class") or EVIDENCE_UNKNOWN)
    if evidence_class in {EVIDENCE_SYNTHETIC, EVIDENCE_SIMULATED}:
        return {
            "state": "synthetic_verified",
            "errors": [],
            "evidence_class": evidence_class,
            "aggregation_eligible": False,
        }
    if (
        evidence_class in {EVIDENCE_LIVE, EVIDENCE_ATTESTED}
        and use_check.get("empirical_feedback_eligible") is True
        and use_check.get("sandbox_only") is False
        and use_check.get("non_promotable") is False
    ):
        return {
            "state": "empirically_verified",
            "errors": [],
            "evidence_class": evidence_class,
            "aggregation_eligible": True,
        }
    return {
        "state": "unknown",
        "errors": ["package_use_evidence_not_empirically_resolved"],
        "evidence_class": evidence_class,
        "aggregation_eligible": False,
    }


def _feedback_material(feedback: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in feedback.items()
        if key
        not in {
            "feedback_id",
            "feedback_hash",
            "created_at",
            "inserted",
            "duplicate",
        }
    }


def submit_distribution_feedback(
    store: Any,
    repo: str,
    *,
    package_id: str,
    kind: str,
    context: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
    evidence: Mapping[str, Any] | None = None,
    package_use_receipt_hash: str | None = None,
    circulation_session_id: str | None = None,
    turn_id: int = 1,
) -> dict[str, Any]:
    """Record target feedback bound to one exact canonical package exposure.

    ``circulation_session_id`` remains a non-authorizing legacy reference.  It
    can never substitute for ``package_use_receipt_hash``.
    """
    if kind not in FEEDBACK_KINDS:
        raise DistributionError(f"unknown feedback kind: {kind}")
    package = get_distribution_package(store, repo, package_id)
    if package is None:
        raise DistributionError("package_missing")
    repository_id, _ = _repo_identity(store, repo)
    use_check: dict[str, Any] | None = None
    if package_use_receipt_hash:
        try:
            use_check = verify_package_use(
                store,
                repo,
                str(package_use_receipt_hash),
                expected_package_id=package_id,
            )
        except Exception as exc:
            use_check = {
                "valid": False,
                "state": "binding_failed",
                "errors": [f"package_use_verification_error:{type(exc).__name__}"],
            }
    verification = _feedback_verification(use_check)
    canonical_outcome = dict((use_check or {}).get("canonical_outcome") or {})
    reported_outcome = dict(outcome or {})
    if reported_outcome and use_check is not None and use_check.get("valid") is True:
        canonical_claim = {
            "observed_result": canonical_outcome.get("observed_result"),
            "status": canonical_outcome.get("status"),
            "success": canonical_outcome.get("success"),
            "evaluation_state": canonical_outcome.get("evaluation_state"),
        }
        for key, value in reported_outcome.items():
            if key in canonical_claim and canonical_claim[key] != value:
                verification = {
                    "state": "binding_failed",
                    "errors": [f"reported_outcome_{key}_mismatch"],
                    "aggregation_eligible": False,
                }
                break
    binding_roots = dict((use_check or {}).get("binding_roots") or {})
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "repo": repo,
        "repository_id": repository_id,
        "target_id": package.get("target_id"),
        "package_id": package_id,
        "kind": kind,
        "reported_claim": {
            "context": dict(context or {}),
            "result": dict(result or {}),
            "outcome": reported_outcome,
            "evidence": dict(evidence or {}),
        },
        "package_use_receipt_hash": str(package_use_receipt_hash or ""),
        "legacy_circulation_reference": {
            "session_id": str(circulation_session_id or ""),
            "turn_id": int(turn_id),
            "authorizing": False,
        },
        "binding_roots": binding_roots,
        "verification": {
            **verification,
            "global_fact": False,
            "causal_effect_established": False,
        },
        "evidence_scope": kind,
        "global_fact": False,
        "empirical_aggregation_eligible": bool(
            verification.get("aggregation_eligible")
        ),
        "canonical_update": False,
        "distribution_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "advisory_only": True,
    }
    body = {
        **material,
        "feedback_id": _sha(material),
        "feedback_hash": _sha(material),
        "created_at": time.time(),
    }
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT feedback_json FROM competence_usage_feedback WHERE repository_id=? AND feedback_id=?",
            (repository_id, body["feedback_id"]),
        ).fetchone()
        if existing is not None:
            return {**(_json(existing["feedback_json"]) or body), "duplicate": True}
        conn.execute(
            """INSERT INTO competence_usage_feedback(
                feedback_id, package_id, repository_id, repo, target_id,
                feedback_hash, feedback_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                body["feedback_id"], package_id, repository_id, repo, body["target_id"],
                body["feedback_hash"], _canonical(body), body["created_at"],
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def list_distribution_feedback(store: Any, repo: str, package_id: str | None = None) -> list[dict[str, Any]]:
    repository_id, _ = _repo_identity(store, repo)
    if package_id:
        rows = store.db.execute(
            "SELECT feedback_json FROM competence_usage_feedback WHERE repository_id=? AND repo=? AND package_id=? ORDER BY created_at ASC",
            (repository_id, repo, package_id),
        ).fetchall()
    else:
        rows = store.db.execute(
            "SELECT feedback_json FROM competence_usage_feedback WHERE repository_id=? AND repo=? ORDER BY created_at ASC",
            (repository_id, repo),
        ).fetchall()
    return [parsed for row in rows if (parsed := _json(row["feedback_json"])) is not None]


def verify_distribution_feedback(
    store: Any, repo: str, feedback_id: str
) -> dict[str, Any]:
    repository_id, _ = _repo_identity(store, repo)
    row = store.db.execute(
        """SELECT * FROM competence_usage_feedback
           WHERE repository_id=? AND repo=? AND feedback_id=?""",
        (repository_id, repo, str(feedback_id)),
    ).fetchone()
    if row is None:
        return {
            "valid": False,
            "state": "unknown",
            "errors": ["feedback_missing"],
            "advisory_only": True,
        }
    feedback = _json(row["feedback_json"])
    if feedback is None:
        return {
            "valid": False,
            "state": "binding_failed",
            "errors": ["feedback_json_invalid"],
            "advisory_only": True,
        }
    errors: list[str] = []
    material = _feedback_material(feedback)
    expected_hash = _sha(material)
    if str(feedback.get("feedback_id") or "") != str(feedback_id):
        errors.append("feedback_identity_invalid")
    if expected_hash != str(feedback.get("feedback_hash") or ""):
        errors.append("feedback_hash_invalid")
    if str(row["feedback_hash"] or "") != str(feedback.get("feedback_hash") or ""):
        errors.append("feedback_ledger_hash_invalid")
    if str(row["package_id"] or "") != str(feedback.get("package_id") or ""):
        errors.append("feedback_package_index_mismatch")
    if str(row["target_id"] or "") != str(feedback.get("target_id") or ""):
        errors.append("feedback_target_index_mismatch")
    if float(row["created_at"] or 0.0) != float(feedback.get("created_at") or 0.0):
        errors.append("feedback_created_at_index_mismatch")
    use_hash = str(feedback.get("package_use_receipt_hash") or "")
    legacy_partial = not use_hash
    if use_hash:
        use_check = verify_package_use(
            store,
            repo,
            use_hash,
            expected_package_id=str(feedback.get("package_id") or ""),
        )
        if use_check.get("valid") is not True:
            errors.extend(str(item) for item in use_check.get("errors") or ())
        expected_roots = dict(use_check.get("binding_roots") or {})
        if expected_roots != dict(feedback.get("binding_roots") or {}):
            errors.append("feedback_binding_roots_mismatch")
        current_verification = _feedback_verification(use_check)
    else:
        use_check = None
        current_verification = {
            "state": "unverified",
            "errors": ["legacy_feedback_has_no_package_use_receipt"],
            "aggregation_eligible": False,
        }
    package = get_distribution_package(
        store, repo, str(feedback.get("package_id") or "")
    )
    profile = (
        get_target_profile(store, repo, str(package.get("profile_id") or ""))
        if package is not None
        else None
    )
    freshness_policy = (
        dict(profile.get("freshness_policy") or {})
        if profile is not None
        and isinstance(profile.get("freshness_policy"), Mapping)
        else {}
    )
    feedback_limit = freshness_policy.get("feedback_max_age_seconds")
    feedback_created = float(feedback.get("created_at") or 0.0)
    if feedback_limit in {None, ""} or not feedback_created:
        feedback_freshness = {
            "state": "unknown",
            "reason": "feedback_freshness_policy_missing_or_legacy",
        }
    else:
        feedback_age = max(0.0, time.time() - feedback_created)
        feedback_freshness = {
            "state": (
                "pass" if feedback_age <= float(feedback_limit) else "fail"
            ),
            "age_seconds": feedback_age,
            "max_age_seconds": float(feedback_limit),
        }
    if feedback_freshness["state"] != "pass":
        current_verification = {
            **current_verification,
            "state": "unknown",
            "errors": sorted(
                set(
                    list(current_verification.get("errors") or ())
                    + ["feedback_freshness_not_current"]
                )
            ),
            "aggregation_eligible": False,
        }
    return {
        "valid": not errors,
        "state": (
            "binding_failed" if errors else str(current_verification["state"])
        ),
        "errors": sorted(set(errors)),
        "feedback_id": feedback_id,
        "package_id": feedback.get("package_id"),
        "target_id": feedback.get("target_id"),
        "stored_verification_state": (
            feedback.get("verification") or {}
        ).get("state"),
        "current_verification": current_verification,
        "feedback_freshness": feedback_freshness,
        "legacy_partial": legacy_partial,
        "empirical_aggregation_eligible": bool(
            not errors and current_verification.get("aggregation_eligible")
        ),
        "global_fact": False,
        "canonical_update": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "advisory_only": True,
    }


__all__ = [
    "BLOCKING_EVENTS",
    "CLAIM_BOUNDARY",
    "DistributionError",
    "EVENT_TYPES",
    "FEEDBACK_KINDS",
    "GLYPH",
    "SCHEMA",
    "VERSION",
    "append_distribution_event",
    "build_competence_package_projection",
    "ensure_distribution_tables",
    "get_distribution_package",
    "get_target_profile",
    "list_distribution_feedback",
    "list_distribution_packages",
    "list_target_profiles",
    "project_competence",
    "quarantine_distribution",
    "register_target_profile",
    "revoke_distribution",
    "rollback_distribution",
    "submit_distribution_feedback",
    "supersede_distribution",
    "verify_distribution_package",
    "verify_distribution_feedback",
    "verify_package_use",
]
