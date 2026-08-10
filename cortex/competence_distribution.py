"""v9.3 governed competence distribution.

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

from .competence import get_competence_candidate, verify_competence_candidate
from .competence_transfer import (
    list_transfer_trials,
    verify_transfer_trial,
)

SCHEMA = "cortex-competence-distribution/1.0"
VERSION = "9.3.0"
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
TRANSFER_READY = frozenset({"cross_model_verified", "cross_family_verified"})
CLAIM_BOUNDARY = (
    "A distribution package is a target-bound, revocable projection of a "
    "transfer-verified competence. It is not authority, execution permission, "
    "proof of universal validity, or automatic learning."
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
    return {
        "schema_version": SCHEMA,
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


def register_target_profile(store: Any, repo: str, profile: Mapping[str, Any]) -> dict[str, Any]:
    """Append one immutable compatibility profile for a consuming system."""
    if not isinstance(profile, Mapping):
        raise DistributionError("target profile must be a mapping")
    ensure_distribution_tables(store)
    repository_id, _ = _repo_identity(store, repo)
    material = _profile_material(profile)
    if not material["target_id"]:
        raise DistributionError("target_id is required")
    body = {
        **material,
        "repo": str(repo),
        "repository_id": repository_id,
        "profile_id": _sha(material),
        "profile_hash": _sha(material),
        "created_at": float(profile.get("created_at") or time.time()),
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


def _transfer_gate(store: Any, repo: str, competence_id: str) -> dict[str, Any]:
    trials = list_transfer_trials(store, repo)
    matching: list[dict[str, Any]] = []
    errors: list[str] = []
    for trial in trials:
        if str(trial.get("competence_id") or "") != competence_id:
            continue
        check = verify_transfer_trial(store, repo, str(trial.get("trial_id") or ""))
        if check.get("valid") is True and str(trial.get("portability_status") or "") in TRANSFER_READY:
            matching.append(trial)
        elif check.get("valid") is not True:
            errors.extend(str(item) for item in check.get("errors") or ())
    if not matching:
        return {
            "state": "unknown" if not trials else "fail",
            "transfer_status": "unresolved",
            "trial_ids": [],
            "errors": sorted(set(errors or ["transfer_verified_trial_missing"])),
        }
    latest = sorted(matching, key=lambda item: float(item.get("created_at") or 0.0))[-1]
    return {
        "state": "pass",
        "transfer_status": str(latest.get("portability_status") or ""),
        "trial_ids": [str(item.get("trial_id") or "") for item in matching],
        "latest_trial_id": str(latest.get("trial_id") or ""),
        "errors": [],
    }


def _compatibility(candidate: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    unknown: list[str] = []
    candidate_type = str(candidate.get("candidate_type") or "")
    prohibited = {str(item) for item in _list(profile.get("prohibited_competence_types"))}
    required = {str(item) for item in _list(profile.get("required_competence_types"))}
    tools = {str(item) for item in _list(profile.get("available_tools"))}
    needed_tools = {str(item) for item in _list(candidate.get("required_tools"))}
    if candidate_type in prohibited:
        errors.append("competence_type_prohibited")
    if required and candidate_type not in required:
        errors.append("competence_type_not_required")
    if needed_tools - tools:
        errors.append("required_tools_unavailable:" + ",".join(sorted(needed_tools - tools)))
    role = str(profile.get("role") or "")
    task_family = str(profile.get("task_family") or "")
    for condition in _list(candidate.get("applicability_conditions")):
        if not isinstance(condition, Mapping):
            continue
        if condition.get("role") and str(condition["role"]) != role:
            errors.append("role_incompatible")
        if condition.get("task_family") and str(condition["task_family"]) != task_family:
            errors.append("task_family_incompatible")
        if condition.get("body_epoch_id") and str(condition["body_epoch_id"]) != str(profile.get("body_epoch_id") or ""):
            errors.append("epoch_incompatible")
        if condition.get("repository_id") and str(condition["repository_id"]) != str(candidate.get("repository_id") or ""):
            errors.append("repository_incompatible")
    environment = profile.get("environment") if isinstance(profile.get("environment"), Mapping) else {}
    for assumption in _list(candidate.get("environmental_assumptions")):
        if isinstance(assumption, Mapping):
            for key, expected in assumption.items():
                if key not in environment:
                    unknown.append(f"environment_missing:{key}")
                elif environment[key] != expected:
                    errors.append(f"environment_mismatch:{key}")
    if not profile.get("body_epoch_id"):
        unknown.append("target_epoch_missing")
    if not profile.get("model_capability"):
        unknown.append("model_capability_missing")
    if errors:
        state = "fail"
    elif unknown:
        state = "unknown"
    else:
        state = "pass"
    return {
        "state": state,
        "selected": state == "pass",
        "errors": sorted(set(errors)),
        "unknown": sorted(set(unknown)),
        "candidate_type": candidate_type,
        "required_tools": sorted(needed_tools),
        "available_tools": sorted(tools),
    }


def _freshness(profile: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    created = float(candidate.get("created_at") or 0.0)
    ttl = float(profile.get("freshness_ttl_seconds") or 86400.0)
    age = max(0.0, time.time() - created) if created else float("inf")
    valid = age <= ttl
    return {"state": _truth_state(valid), "age_seconds": age, "ttl_seconds": ttl, "expires_at": created + ttl if created else None}


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
    transfer = _transfer_gate(store, repo, competence_id)
    applicability = _compatibility(candidate, profile)
    freshness = _freshness(profile, candidate)
    events = _current_event_rows(store, repo, previous_package_id) if previous_package_id else []
    previous_state, previous_blocks = _event_state(events)
    global_events = _global_competence_events(store, repo, competence_id)
    gates = {
        "provenance": "pass" if candidate_check.get("valid") is True else "fail",
        "transfer": transfer["state"],
        "competence_active": "fail" if str(candidate.get("revision_state") or candidate.get("ledger_state") or "") in {"revoked", "superseded", "contested"} else "pass",
        "target_compatible": applicability["state"],
        "environment_compatible": applicability["state"],
        "authority_scope_compatible": "pass" if profile.get("authority_scope_declared") is True else "unknown",
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
            "package_persisted": False,
            "policy_effect": False,
            "distribution_authorized": False,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "advisory_only": True,
        }
    repository_id, _ = _repo_identity(store, repo)
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
        },
        "applicability_proof": applicability,
        "compatibility_proof": applicability,
        "exclusions": list(candidate.get("failure_conditions") or []),
        "counterevidence": list(candidate.get("counterevidence") or []),
        "freshness": freshness,
        "global_events": global_events,
        "revocation_state": "active",
        "previous_package_id": previous_package_id,
        "gates": gates,
        "status": "active",
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
    transfer = _transfer_gate(store, repo, str(package.get("competence_id") or "")) if candidate else {"state": "unknown"}
    if transfer.get("state") != "pass":
        errors.append("transfer_verification_invalid")
    if profile is not None:
        current_compatibility = _compatibility(candidate or {}, profile)
        if current_compatibility != package.get("compatibility_proof"):
            errors.append("compatibility_proof_mismatch")
    events = _current_event_rows(store, repo, package_id)
    state, blocking = _event_state(events)
    errors.extend(f"package_{item}" for item in blocking)
    global_events = _global_competence_events(store, repo, str(package.get("competence_id") or ""))
    if global_events:
        errors.append("competence_global_event")
    freshness = _freshness(profile or {}, candidate or {})
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
        "distribution_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "advisory_only": True,
    }


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
    circulation_session_id: str | None = None,
    turn_id: int = 1,
) -> dict[str, Any]:
    """Record target feedback; only canonical circulation can mark it verified."""
    if kind not in FEEDBACK_KINDS:
        raise DistributionError(f"unknown feedback kind: {kind}")
    package = get_distribution_package(store, repo, package_id)
    if package is None:
        raise DistributionError("package_missing")
    repository_id, _ = _repo_identity(store, repo)
    verification: dict[str, Any] = {"state": "unverified", "errors": ["independent_feedback_evidence_missing"]}
    if circulation_session_id:
        try:
            from .model_circulation import verify_model_circulation

            verification = verify_model_circulation(store, repo, str(circulation_session_id), turn_id=int(turn_id))
            verification = {
                "state": "pass" if verification.get("valid") is True else "fail",
                "errors": list(verification.get("errors") or []),
                "witness_result_hash": verification.get("witness_result_hash"),
            }
        except Exception as exc:
            verification = {"state": "fail", "errors": [f"feedback_verification_error:{type(exc).__name__}"]}
    material = {
        "schema_version": SCHEMA,
        "repo": repo,
        "repository_id": repository_id,
        "target_id": package.get("target_id"),
        "package_id": package_id,
        "kind": kind,
        "context": dict(context or {}),
        "result": dict(result or {}),
        "outcome": dict(outcome or {}),
        "evidence": dict(evidence or {}),
        "verification": verification,
        "canonical_update": False,
        "distribution_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "advisory_only": True,
    }
    body = {**material, "feedback_id": _sha(material), "feedback_hash": _sha(material), "created_at": time.time()}
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
]
