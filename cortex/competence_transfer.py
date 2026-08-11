"""v9.4 evidence-typed cross-model competence transfer trials.

This module is an experiment surface, not a promotion surface.  It freezes a
task contract and environment, runs fresh model instances through matched arms,
and records all outcomes (including failures) in an immutable ledger.  A trial
never changes competence state and never grants distribution, execution, or
host authority.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .adapter_provenance import (
    EVIDENCE_ATTESTED,
    EVIDENCE_LEGACY,
    EVIDENCE_LIVE,
    EVIDENCE_SIMULATED,
    EVIDENCE_SYNTHETIC,
    EVIDENCE_UNKNOWN,
    resolve_adapter_provenance,
)
from .competence import (
    CompetenceError,
    evaluate_competence_applicability_constraints,
    evaluate_revision_evidence_freshness,
    get_competence_candidate,
    verify_competence_candidate,
)
from .evaluation import TaskEvaluationContract
from .model_circulation import (
    ModelAdapter,
    ModelAdapterError,
    run_model_circulation,
    verify_model_circulation,
)
from .symbiosis import agent_instantiation_receipt, cortex_context_receipt

SCHEMA = "cortex-competence-transfer/1.2"
EVIDENCE_SCHEMA = "cortex-competence-transfer/1.1"
VERSION = "9.5.0"
GLYPH = "⟡◇⇄"
ARMS = ("A", "B", "C", "D", "E")
PORTABILITY_STATES = frozenset(
    {
        "model_specific",
        "capability_class_specific",
        "cross_model_verified",
        "cross_family_verified",
        "structural_cross_model_pass",
        "structural_cross_family_pass",
        "empirical_cross_model_verified",
        "empirical_cross_family_verified",
        "unresolved",
        "incompatible",
    }
)
CLAIM_BOUNDARY = (
    "Cross-model transfer trials estimate utility and failure surfaces under "
    "declared matched arms. Synthetic trials prove mechanism behavior, not "
    "empirical transfer. No trial proves universal competence, cognition, "
    "authority, or automatic distribution."
)

DEFAULT_POLICY: dict[str, Any] = {
    "min_success_gain": 0.0,
    "max_cost_ratio": 1.5,
    "min_repetitions": 1,
    "required_arms": list(ARMS),
    "target_portability": "unresolved",
    "utility_weights": {
        "task_success": 0.65,
        "abstention_quality": 0.05,
        "counterevidence_retention": 0.10,
        "correction_rate": 0.05,
        "cost_penalty": 0.10,
        "latency_penalty": 0.025,
        "prohibited_action_penalty": 0.025,
    },
}


class TransferTrialError(CompetenceError):
    """Raised when a controlled transfer trial cannot be safely constructed."""


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _clip01(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return max(0.0, min(1.0, number))


def _repo_identity(store: Any, repo: str) -> tuple[str, dict[str, Any]]:
    row = store.repo(repo)
    if row is None:
        raise TransferTrialError(f"Unknown repository: {repo}")
    repository_id = str(row["repository_id"] or "")
    if not repository_id:
        raise TransferTrialError("repository identity is missing")
    return repository_id, dict(row)


def _policy(policy: Mapping[str, Any] | None) -> dict[str, Any]:
    result = json.loads(_canonical(DEFAULT_POLICY))
    if policy is not None:
        if not isinstance(policy, Mapping):
            raise TransferTrialError("transfer policy must be a mapping")
        for key, value in policy.items():
            if key == "utility_weights":
                result["utility_weights"].update(dict(value or {}))
            else:
                result[str(key)] = value
    required = set(str(item) for item in result.get("required_arms") or ())
    if required != set(ARMS):
        raise TransferTrialError("policy must explicitly require arms A through E")
    target = str(result.get("target_portability") or "unresolved")
    if target not in PORTABILITY_STATES:
        raise TransferTrialError("unknown portability target in transfer policy")
    result["min_repetitions"] = max(1, int(result.get("min_repetitions") or 1))
    result["min_success_gain"] = float(result.get("min_success_gain") or 0.0)
    result["max_cost_ratio"] = max(0.0, float(result.get("max_cost_ratio") or 0.0))
    return result


def _adapter_identity(adapter: ModelAdapter) -> dict[str, str]:
    model_id = str(getattr(adapter, "model_id", "") or "")
    if not model_id:
        raise TransferTrialError("fresh adapter must declare model_id")
    return {
        "provider_family": str(getattr(adapter, "provider_family", "undeclared") or "undeclared"),
        "model_id": model_id,
        "model_version": str(getattr(adapter, "model_version", "undeclared") or "undeclared"),
        "adapter_id": str(getattr(adapter, "adapter_id", type(adapter).__name__) or type(adapter).__name__),
        "adapter_version": str(getattr(adapter, "adapter_version", "undeclared") or "undeclared"),
    }


def _public_raw_history(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep arm B public and bounded; hidden reasoning never enters the trial."""
    allowed = {
        "model_invocation": ("kind", "model_id", "model_version"),
        "model_proposal": ("kind", "proposal", "rationale_public", "evidence_citations"),
        "model_evaluation": ("kind", "evaluation", "task_contract_hash"),
        "model_outcome": ("kind", "observed_result", "evaluation_state", "success", "status"),
    }
    result: list[dict[str, Any]] = []
    for row in rows:
        kind = str(row.get("kind") or "")
        fields = allowed.get(kind)
        if fields:
            result.append({key: row.get(key) for key in fields})
    return result


def _candidate_projection(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Project K without model-origin or private provenance into arm D/E."""
    return {
        "competence_id": candidate.get("competence_id"),
        "semantic_identity_hash": candidate.get("semantic_identity_hash"),
        "candidate_type": candidate.get("candidate_type"),
        "capability": candidate.get("capability"),
        "intended_outcome": candidate.get("intended_outcome"),
        "prerequisites": candidate.get("prerequisites") or [],
        "applicability_conditions": candidate.get("applicability_conditions") or [],
        "applicability_constraints": candidate.get("applicability_constraints") or [],
        "applicability_exclusions": candidate.get("applicability_exclusions") or [],
        "environmental_assumptions": candidate.get("environmental_assumptions") or [],
        "required_tools": candidate.get("required_tools") or [],
        "failure_conditions": candidate.get("failure_conditions") or [],
        "counterevidence": candidate.get("counterevidence") or [],
        "uncertainty": candidate.get("uncertainty") or [],
        "revision_state": candidate.get("revision_state"),
        "portability_status": candidate.get("portability_status"),
        "canonical_evidence": {
            "receipt_hash": candidate.get("receipt_hash"),
            "evidence_lineage_hash": candidate.get("evidence_lineage_hash"),
        },
    }


def _freeze_applicability_context(
    store: Any,
    declared: Mapping[str, Any] | None,
    *,
    repo: str,
    repository_id: str,
    body_epoch_id: str,
    target_profile_id: str | None,
    model_family_bindings: Mapping[str, Any],
    frozen_at: float | None = None,
) -> dict[str, Any]:
    """Resolve and freeze canonical facts against which K will be tested."""
    if declared is None:
        declared = {}
    if not isinstance(declared, Mapping):
        raise TransferTrialError("applicability_context must be a mapping")
    allowed = {
        "target_id",
        "target_class",
        "environment",
        "environment_fingerprint",
        "model_family",
    }
    unsupported = sorted(str(key) for key in declared if key not in allowed)
    if unsupported:
        raise TransferTrialError(
            "applicability_context contains provider-specific or unsupported fields: "
            + ",".join(unsupported)
        )
    profile: Mapping[str, Any] | None = None
    profile_proof: dict[str, Any] = {
        "state": "unknown",
        "profile_id": None,
        "profile_hash": None,
        "reason": "canonical_target_profile_not_declared",
    }
    if target_profile_id:
        # Local import avoids the distribution -> transfer module import cycle.
        from .competence_distribution import _profile_material, get_target_profile

        profile = get_target_profile(store, repo, str(target_profile_id))
        if profile is None:
            raise TransferTrialError("canonical target profile is missing")
        expected_profile_hash = _sha(_profile_material(profile))
        if (
            str(profile.get("profile_id") or "") != expected_profile_hash
            or str(profile.get("profile_hash") or "") != expected_profile_hash
            or str(profile.get("ledger_profile_hash") or "")
            != expected_profile_hash
            or str(profile.get("repo") or "") != repo
            or str(profile.get("repository_id") or "") != repository_id
        ):
            raise TransferTrialError("canonical target profile failed verification")
        profile_proof = {
            "state": "pass",
            "profile_id": expected_profile_hash,
            "profile_hash": expected_profile_hash,
            "reason": "immutable_target_profile_resolved",
        }

    identity = profile.get("identity") if isinstance(profile, Mapping) else {}
    identity = identity if isinstance(identity, Mapping) else {}
    target_class = ""
    for key in ("target_class", "class", "type"):
        if identity.get(key):
            target_class = str(identity[key])
            break
    environment = (
        json.loads(_canonical(dict(profile.get("environment") or {})))
        if isinstance(profile, Mapping)
        else None
    )
    computed_fingerprint = _sha(environment) if environment is not None else ""
    canonical_values: dict[str, Any] = {
        "target_id": str(profile.get("target_id") or "")
        if isinstance(profile, Mapping)
        else "",
        "target_class": target_class,
        "environment": environment,
        "environment_fingerprint": computed_fingerprint,
    }
    for key in ("target_id", "target_class"):
        declared_value = str(declared.get(key) or "")
        if declared_value and declared_value != canonical_values[key]:
            raise TransferTrialError(
                f"caller applicability context does not match canonical {key}"
            )
    raw_environment = declared.get("environment")
    if raw_environment is not None:
        if not isinstance(raw_environment, Mapping):
            raise TransferTrialError(
                "applicability_context.environment must be a mapping"
            )
        if environment is None or dict(raw_environment) != environment:
            raise TransferTrialError(
                "caller applicability environment has no matching canonical profile"
            )
    declared_fingerprint = str(declared.get("environment_fingerprint") or "")
    if declared_fingerprint and declared_fingerprint != computed_fingerprint:
        raise TransferTrialError(
            "caller environment fingerprint has no matching canonical profile"
        )
    declared_model_family = str(declared.get("model_family") or "")
    canonical_families = sorted(
        {
            str(value.get("model_family") or "")
            for value in model_family_bindings.values()
            if isinstance(value, Mapping) and value.get("model_family")
        }
    )
    if declared_model_family and declared_model_family not in canonical_families:
        raise TransferTrialError(
            "caller model family has no matching host-registered adapter classification"
        )
    return {
        "schema_version": "cortex-transfer-applicability-context/1.0",
        "repo": str(repo),
        "repository_id": str(repository_id),
        "body_epoch_id": str(body_epoch_id),
        "frozen_at": float(frozen_at if frozen_at is not None else time.time()),
        "target_profile": profile_proof,
        "target_id": canonical_values["target_id"],
        "target_class": canonical_values["target_class"],
        "environment": environment,
        "environment_fingerprint": computed_fingerprint,
        "model_family_bindings": json.loads(
            _canonical(dict(model_family_bindings))
        ),
    }


def _adapter_family_binding(provenance: Mapping[str, Any]) -> dict[str, Any]:
    """Project only host-verified model-family provenance into a trial."""
    classification = provenance.get("host_model_classification")
    classification = classification if isinstance(classification, Mapping) else {}
    classified = str(classification.get("state") or "") == "host_registered"
    return {
        "state": "pass" if classified else "unknown",
        "model_family": str(classification.get("model_family") or "")
        if classified
        else "",
        "registration_id": provenance.get("registration_id"),
        "registration_hash": provenance.get("registration_hash"),
        "classification_digest": provenance.get(
            "host_model_classification_digest"
        ),
        "authority_basis": classification.get("authority_basis")
        if classified
        else "none",
    }


def _trial_applicability_proof(
    candidate: Mapping[str, Any], context: Mapping[str, Any]
) -> dict[str, Any]:
    """Recompute transfer applicability without granting active use."""
    reasons: list[str] = []
    if str(candidate.get("revision_state") or "") in {"revoked", "superseded", "contested"}:
        reasons.append("candidate_state_blocked")
    if str(candidate.get("portability_status") or "") in {"model_specific_blocked", "blocked"}:
        reasons.append("candidate_portability_blocked")
    current_epoch = str(context.get("body_epoch_id") or "")
    current_repo = str(context.get("repository_id") or context.get("repo") or "")
    conditions = candidate.get("applicability_conditions") or []
    if isinstance(conditions, Mapping):
        conditions = [conditions]
    for condition in conditions if isinstance(conditions, Sequence) and not isinstance(conditions, (str, bytes)) else []:
        if not isinstance(condition, Mapping):
            continue
        if condition.get("body_epoch_id") and str(condition["body_epoch_id"]) != current_epoch:
            reasons.append("epoch_incompatible")
        if condition.get("repository_id") and str(condition["repository_id"]) != current_repo:
            reasons.append("repository_incompatible")
    hard_failure = bool(reasons)
    freshness = evaluate_revision_evidence_freshness(
        candidate, as_of=float(context.get("frozen_at") or time.time())
    )
    freshness_state = str(freshness.get("state") or "unknown")
    if freshness.get("passed") is not True:
        reasons.append(str(freshness.get("reason") or "revision_evidence_unknown"))
    if freshness_state == "fail":
        hard_failure = True
    constraints = candidate.get("applicability_constraints")
    constraints = (
        list(constraints)
        if isinstance(constraints, Sequence)
        and not isinstance(constraints, (str, bytes))
        else []
    )
    model_constrained = any(
        isinstance(item, Mapping) and item.get("dimension") == "model_family"
        for item in constraints
    )
    checks: list[tuple[str, dict[str, Any]]] = []
    if model_constrained:
        bindings = context.get("model_family_bindings")
        bindings = bindings if isinstance(bindings, Mapping) else {}
        for arm in ("D", "E"):
            binding = bindings.get(arm)
            family = (
                str(binding.get("model_family") or "")
                if isinstance(binding, Mapping)
                else ""
            )
            checks.append(
                (
                    arm,
                    evaluate_competence_applicability_constraints(
                        candidate, {**context, "model_family": family}
                    ),
                )
            )
    else:
        checks.append(
            ("all", evaluate_competence_applicability_constraints(candidate, context))
        )
    constraint_results: list[dict[str, Any]] = []
    constraint_states: list[str] = []
    for arm, check in checks:
        constraint_states.append(str(check.get("state") or "unknown"))
        reasons.extend(str(item) for item in check.get("reasons") or ())
        for result in check.get("results") or ():
            constraint_results.append({"arm": arm, **dict(result)})
    constraint_state = (
        "fail"
        if "fail" in constraint_states
        else "unknown"
        if "unknown" in constraint_states
        else "pass"
    )
    state = (
        "fail"
        if hard_failure or constraint_state == "fail"
        else "unknown"
        if constraint_state == "unknown" or freshness_state == "unknown"
        else "pass"
    )
    return {
        "state": state,
        "applicable": not reasons,
        "reasons": sorted(set(reasons)),
        "constraint_state": constraint_state,
        "constraint_results": constraint_results,
        "revision_evidence_freshness": freshness,
        "context_hash": _sha(context),
        "read_only": True,
        "state_transition_persisted": False,
        "distribution_authorized": False,
        "execution_authorized": False,
        "host_mutate_authorized": False,
        "advisory_only": True,
    }


def _applicability_for_trial(
    candidate: Mapping[str, Any], context: Mapping[str, Any]
) -> tuple[bool, list[str]]:
    """Backward-compatible tuple projection of the typed trial proof."""
    proof = _trial_applicability_proof(candidate, context)
    return bool(proof["applicable"]), list(proof["reasons"])


def _new_trial_session(
    store: Any,
    repo: str,
    *,
    session_id: str,
    task: str,
    body_epoch_id: str,
    adapter: ModelAdapter,
    arm: str,
    context_package: Mapping[str, Any],
    trial_id: str,
    tool_scopes: Sequence[str],
    persist: bool,
) -> dict[str, Any]:
    repository_id, _ = _repo_identity(store, repo)
    identity = _adapter_identity(adapter)
    invocation_id = f"xfer_inv_{session_id}"
    context = cortex_context_receipt(
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        turn_id=0,
        invocation_id=invocation_id,
        case_id=f"case_{session_id}_0",
        evidence_items=[
            {
                "surface": "competence_transfer_trial",
                "arm": arm,
                "digest": _sha(context_package),
            }
        ],
        memory_episodes=[],
        predictions={
            "transfer_trial_id": trial_id,
            "transfer_arm": arm,
            "transfer_context": dict(context_package),
        },
        unresolved_contradictions=[],
        operating_regime={"transfer_trial": "frozen"},
        confidence={"context_frozen": 1.0},
        constitutional_restrictions=[
            "host_source_mutation_forbidden",
            "execution_requires_separate_authority",
            "trial_does_not_authorize_distribution",
        ],
    )
    instantiation = agent_instantiation_receipt(
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        provider=identity["provider_family"],
        model_id=identity["model_id"],
        capability_profile={"transfer_trial": True, "arm": arm},
        tool_scopes=tool_scopes,
        context_packet_digest=str(context.get("context_packet_digest") or ""),
        turn_id=0,
        invocation_id=invocation_id,
        case_id=f"case_{session_id}_0",
    )
    context["prior_receipt_hash"] = instantiation["receipt_hash"]
    if persist:
        store.append_symbiotic_receipt(repo, instantiation)
        store.append_symbiotic_receipt(repo, context)
    return {
        "schema_version": "cortex-transfer-trial-session/1.0",
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "invocation_id": invocation_id,
        "current_turn_id": 0,
        "task": task,
        "body_epoch_id": body_epoch_id,
        "epoch_verified": True,
        "receipts": {"cortex_context": context},
    }


def ensure_transfer_tables(store: Any) -> None:
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS competence_transfer_trials(
            trial_id TEXT PRIMARY KEY CHECK(length(trial_id) = 64),
            receipt_hash TEXT NOT NULL CHECK(length(receipt_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            competence_id TEXT NOT NULL,
            competence_receipt_hash TEXT NOT NULL,
            task_contract_hash TEXT NOT NULL,
            body_epoch_id TEXT NOT NULL,
            measurement_cohort_id TEXT,
            trial_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, trial_id),
            UNIQUE(repository_id, receipt_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_competence_transfer_repo
            ON competence_transfer_trials(repo, created_at DESC);
        CREATE TRIGGER IF NOT EXISTS competence_transfer_trials_no_delete
        BEFORE DELETE ON competence_transfer_trials
        BEGIN
            SELECT RAISE(ABORT, 'canonical competence transfer trials cannot be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_transfer_trials_no_update
        BEFORE UPDATE ON competence_transfer_trials
        BEGIN
            SELECT RAISE(ABORT, 'canonical competence transfer trials cannot be updated');
        END;
        """
    )
    store.db.commit()


def append_transfer_trial(store: Any, repo: str, trial: Mapping[str, Any]) -> dict[str, Any]:
    ensure_transfer_tables(store)
    repository_id, _ = _repo_identity(store, repo)
    body = dict(trial)
    if str(body.get("repo") or "") != repo or str(body.get("repository_id") or "") != repository_id:
        raise TransferTrialError("trial repository binding is invalid")
    trial_id = str(body.get("trial_id") or "")
    if len(trial_id) != 64:
        raise TransferTrialError("trial_id must be a SHA-256 identity")
    material = {
        key: value
        for key, value in body.items()
        if key not in {"receipt_hash", "created_at", "inserted", "duplicate"}
    }
    if _sha(material) != str(body.get("receipt_hash") or ""):
        raise TransferTrialError("trial receipt hash is invalid")
    if body.get("distribution_authorized") is not False or body.get("execution_authorized") is not False:
        raise TransferTrialError("transfer trials cannot carry authority")
    if str(body.get("schema_version") or "") == SCHEMA:
        conformance = _validate_transfer_body(store, repo, body)
        if conformance.get("valid") is not True:
            raise TransferTrialError(
                "trial claims are not independently reproducible: "
                + ",".join(str(item) for item in conformance.get("errors") or ())
            )
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT * FROM competence_transfer_trials WHERE repository_id=? AND trial_id=?",
            (repository_id, trial_id),
        ).fetchone()
        if existing is not None:
            if str(existing["receipt_hash"]) != str(body["receipt_hash"]):
                raise TransferTrialError("trial identity already has different content")
            existing_body = json.loads(str(existing["trial_json"]))
            return {**existing_body, "inserted": False, "duplicate": True}
        conn.execute(
            """INSERT INTO competence_transfer_trials(
                trial_id, receipt_hash, repository_id, repo, competence_id,
                competence_receipt_hash, task_contract_hash, body_epoch_id,
                measurement_cohort_id, trial_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trial_id,
                str(body["receipt_hash"]),
                repository_id,
                repo,
                str(body["competence_id"]),
                str(body["competence_receipt_hash"]),
                str(body["task_contract_hash"]),
                str(body["body_epoch_id"]),
                body.get("measurement_cohort_id"),
                _canonical(body),
                float(body.get("created_at") or time.time()),
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def get_transfer_trial(store: Any, repo: str, trial_id: str) -> dict[str, Any] | None:
    repository_id, _ = _repo_identity(store, repo)
    row = store.db.execute(
        "SELECT trial_json FROM competence_transfer_trials WHERE repository_id=? AND repo=? AND trial_id=?",
        (repository_id, repo, str(trial_id)),
    ).fetchone()
    if row is None:
        return None
    try:
        value = json.loads(str(row["trial_json"]))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return dict(value) if isinstance(value, Mapping) else None


def list_transfer_trials(store: Any, repo: str) -> list[dict[str, Any]]:
    repository_id, _ = _repo_identity(store, repo)
    rows = store.db.execute(
        "SELECT trial_json FROM competence_transfer_trials WHERE repository_id=? AND repo=? ORDER BY created_at ASC",
        (repository_id, repo),
    ).fetchall()
    result: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = json.loads(str(row["trial_json"]))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, Mapping):
            result.append(dict(value))
    return result


def _arm_metrics(
    result: Mapping[str, Any],
    *,
    context_package: Mapping[str, Any],
    token_budget: int,
    latency_budget_ms: int,
    feedback_available: bool,
) -> dict[str, Any]:
    evaluation = result.get("evaluation") if isinstance(result.get("evaluation"), Mapping) else {}
    invocation = result.get("invocation_result") if isinstance(result.get("invocation_result"), Mapping) else {}
    proposal = result.get("receipts", {}).get("model_proposal", {}) if isinstance(result.get("receipts"), Mapping) else {}
    usage = invocation.get("token_usage") if isinstance(invocation.get("token_usage"), Mapping) else {}
    tokens = sum(float(usage.get(key) or 0.0) for key in ("input", "output", "total"))
    requested = float(result.get("request", {}).get("requested_at") or 0.0)
    completed = float(invocation.get("completed_at") or requested)
    latency_ms = max(0.0, (completed - requested) * 1000.0)
    intents = proposal.get("tool_call_intents") if isinstance(proposal, Mapping) else []
    prohibited = 0
    for intent in intents or ():
        if isinstance(intent, Mapping) and any(
            token in _canonical(intent).lower()
            for token in ("host_mutat", "execute", "policy", "authority")
        ):
            prohibited += 1
    k = context_package.get("competence") if isinstance(context_package.get("competence"), Mapping) else None
    counterevidence = len(k.get("counterevidence") or ()) if k else 0
    feedback = context_package.get("usage_feedback") if isinstance(context_package.get("usage_feedback"), Sequence) else []
    success = evaluation.get("success") is True
    unknown = evaluation.get("success") is None
    return {
        "task_success": 1.0 if success else 0.0,
        "repeated_error_rate": None if not feedback_available else (0.0 if success else 1.0),
        "unsupported_claims": 0,
        "stale_competence_use": 0,
        "applicability_violations": 0,
        "abstention_quality": 1.0 if unknown else 0.0,
        "correction_rate": 1.0 if feedback and success else 0.0,
        "token_cost": tokens,
        "token_cost_ratio": min(1.0, tokens / max(1, token_budget)),
        "latency_ms": round(latency_ms, 3),
        "latency_ratio": min(1.0, latency_ms / max(1, latency_budget_ms)),
        "prohibited_action_attempts": prohibited,
        "counterevidence_retention": 1.0 if counterevidence else 0.0,
        "counterevidence_count": counterevidence,
        "feedback_available": bool(feedback_available),
        "evaluation_state": evaluation.get("state"),
    }


def _utility(metrics: Mapping[str, Any], weights: Mapping[str, Any]) -> float:
    value = (
        float(weights.get("task_success", 0.0)) * float(metrics.get("task_success") or 0.0)
        + float(weights.get("abstention_quality", 0.0)) * float(metrics.get("abstention_quality") or 0.0)
        + float(weights.get("counterevidence_retention", 0.0)) * float(metrics.get("counterevidence_retention") or 0.0)
        + float(weights.get("correction_rate", 0.0)) * float(metrics.get("correction_rate") or 0.0)
        - float(weights.get("cost_penalty", 0.0)) * float(metrics.get("token_cost_ratio") or 0.0)
        - float(weights.get("latency_penalty", 0.0)) * float(metrics.get("latency_ratio") or 0.0)
        - float(weights.get("prohibited_action_penalty", 0.0)) * min(1.0, float(metrics.get("prohibited_action_attempts") or 0.0))
    )
    return round(_clip01(value), 6)


def _classify(
    arm_scores: Mapping[str, Mapping[str, Any]],
    *,
    policy: Mapping[str, Any],
    fresh_identities: Sequence[Mapping[str, Any]],
    origin_identity: Mapping[str, Any],
    arm_evidence_classes: Sequence[str],
    origin_evidence_class: str,
    incompatible: bool,
    repetition_ready: bool,
    persisted: bool,
) -> tuple[str, list[str]]:
    if incompatible:
        return "incompatible", ["required_context_or_prerequisite_incompatible"]
    if set(arm_scores) != set(ARMS):
        return "unresolved", ["not_all_required_arms_completed"]
    if not repetition_ready:
        return "unresolved", ["minimum_repetitions_not_met"]
    gains = {
        "continuity": float(arm_scores["D"]["U"]) - float(arm_scores["A"]["U"]),
        "distillation": float(arm_scores["D"]["U"]) - float(arm_scores["B"]["U"]),
        "governance": float(arm_scores["D"]["U"]) - float(arm_scores["C"]["U"]),
        "credit": float(arm_scores["E"]["U"]) - float(arm_scores["D"]["U"]),
    }
    threshold = float(policy.get("min_success_gain") or 0.0)
    if any(gains[key] < threshold for key in ("continuity", "distillation", "governance")):
        return "unresolved", ["declared_gain_threshold_not_met"]
    d_cost = float(arm_scores["D"]["metrics"].get("token_cost") or 0.0)
    a_cost = float(arm_scores["A"]["metrics"].get("token_cost") or 0.0)
    if a_cost > 0 and d_cost / a_cost > float(policy.get("max_cost_ratio") or 0.0):
        return "unresolved", ["declared_cost_ratio_exceeded"]
    families = {str(item.get("provider_family") or "") for item in fresh_identities}
    origin_family = str(origin_identity.get("provider_family") or "")
    cross_family = len(families) > 1 and origin_family not in families
    empirical_classes = {EVIDENCE_LIVE, EVIDENCE_ATTESTED}
    structural_classes = {
        EVIDENCE_SYNTHETIC,
        EVIDENCE_SIMULATED,
        EVIDENCE_LIVE,
        EVIDENCE_ATTESTED,
    }
    if (
        persisted
        and origin_evidence_class in empirical_classes
        and arm_evidence_classes
        and all(item in empirical_classes for item in arm_evidence_classes)
    ):
        observed = (
            "empirical_cross_family_verified"
            if cross_family
            else "empirical_cross_model_verified"
        )
    elif (
        origin_evidence_class in structural_classes
        and arm_evidence_classes
        and all(item in structural_classes for item in arm_evidence_classes)
    ):
        observed = (
            "structural_cross_family_pass"
            if cross_family
            else "structural_cross_model_pass"
        )
    else:
        return "unresolved", ["adapter_evidence_class_unknown_or_legacy"]
    target = str(policy.get("target_portability") or "unresolved")
    if target not in {"unresolved", observed}:
        return "unresolved", ["declared_portability_target_not_met"]
    return observed, []


def _validate_transfer_body(
    store: Any, repo: str, trial: Mapping[str, Any]
) -> dict[str, Any]:
    """Reconstruct transfer claims from canonical arm circulations."""
    errors: list[str] = []
    arm_scores: dict[str, dict[str, Any]] = {}
    arm_classes: dict[str, str] = {}
    budgets = trial.get("budgets") if isinstance(trial.get("budgets"), Mapping) else {}
    policy = trial.get("policy") if isinstance(trial.get("policy"), Mapping) else {}
    weights = policy.get("utility_weights") if isinstance(policy.get("utility_weights"), Mapping) else {}
    stored_arms = trial.get("arm_results") if isinstance(trial.get("arm_results"), Mapping) else {}
    identity_keys = [
        "schema_version",
        "version",
        "repo",
        "repository_id",
        "competence_id",
        "competence_receipt_hash",
        "task",
        "task_contract",
        "task_contract_hash",
        "environment",
        "tools",
        "budgets",
        "model_configuration",
        "policy",
        "arms",
        "origin_model",
        "trial_nonce",
        "fresh_model_identities",
    ]
    if str(trial.get("schema_version") or "") == SCHEMA:
        identity_keys.extend(
            ("applicability_context", "applicability_verification")
        )
    if _sha({key: trial.get(key) for key in identity_keys}) != str(
        trial.get("trial_id") or ""
    ):
        errors.append("trial_identity_not_recomputed")
    candidate = get_competence_candidate(
        store, repo, str(trial.get("competence_id") or "")
    )
    if candidate is None:
        errors.append("competence_candidate_missing")
    else:
        candidate_check = verify_competence_candidate(
            store, repo, str(trial.get("competence_id") or "")
        )
        if candidate_check.get("valid") is not True:
            errors.append("competence_candidate_invalid")
        if str(candidate.get("receipt_hash") or "") != str(
            trial.get("competence_receipt_hash") or ""
        ):
            errors.append("competence_receipt_binding_invalid")
        canonical_origin = (
            candidate.get("evidence_lineage", {}).get("model_origin", {})
            if isinstance(candidate.get("evidence_lineage"), Mapping)
            else {}
        )
        if dict(canonical_origin or {}) != dict(trial.get("origin_model") or {}):
            errors.append("origin_model_binding_invalid")
        canonical_origin_class = str(
            (canonical_origin or {}).get("evidence_class") or EVIDENCE_LEGACY
        )
        if canonical_origin_class != str(
            trial.get("origin_evidence_class") or EVIDENCE_LEGACY
        ):
            errors.append("origin_evidence_class_binding_invalid")
        if str(trial.get("schema_version") or "") == SCHEMA:
            stored_context = trial.get("applicability_context")
            if not isinstance(stored_context, Mapping):
                errors.append("trial_applicability_context_missing")
            else:
                try:
                    reconstructed_context = _freeze_applicability_context(
                        store,
                        {},
                        repo=repo,
                        repository_id=str(trial.get("repository_id") or ""),
                        body_epoch_id=str(trial.get("body_epoch_id") or ""),
                        target_profile_id=str(
                            (
                                stored_context.get("target_profile")
                                if isinstance(
                                    stored_context.get("target_profile"), Mapping
                                )
                                else {}
                            ).get("profile_id")
                            or ""
                        ),
                        model_family_bindings=(
                            stored_context.get("model_family_bindings")
                            if isinstance(
                                stored_context.get("model_family_bindings"), Mapping
                            )
                            else {}
                        ),
                        frozen_at=float(stored_context.get("frozen_at") or 0.0),
                    )
                except (TransferTrialError, TypeError, ValueError):
                    errors.append("trial_applicability_context_invalid")
                else:
                    if dict(stored_context) != reconstructed_context:
                        errors.append("trial_applicability_context_not_canonical")
                    expected_proof = _trial_applicability_proof(
                        candidate, reconstructed_context
                    )
                    if dict(trial.get("applicability_verification") or {}) != expected_proof:
                        errors.append("trial_applicability_proof_invalid")
                    if expected_proof.get("applicable") is not True:
                        errors.append("trial_applicability_not_pass")
    for arm in ARMS:
        item = stored_arms.get(arm)
        if not isinstance(item, Mapping):
            errors.append(f"arm_{arm}_missing")
            continue
        session_id = str(item.get("session_id") or "")
        circulation = verify_model_circulation(store, repo, session_id, turn_id=1)
        if circulation.get("valid") is not True:
            errors.append(f"arm_{arm}_circulation_invalid")
            continue
        rows = store.symbiotic_session_receipts(repo, session_id)
        by_kind = {str(row.get("kind") or ""): row for row in rows}
        contexts = [row for row in rows if row.get("kind") == "cortex_context"]
        invocation = by_kind.get("model_invocation") or {}
        proposal = by_kind.get("model_proposal") or {}
        evaluation = by_kind.get("model_evaluation") or {}
        if not contexts:
            errors.append(f"arm_{arm}_context_missing")
            continue
        context_package = (
            (contexts[-1].get("predictions") or {}).get("transfer_context")
            if isinstance(contexts[-1].get("predictions"), Mapping)
            else None
        )
        if not isinstance(context_package, Mapping):
            errors.append(f"arm_{arm}_transfer_context_missing")
            continue
        if (
            str(trial.get("schema_version") or "") == SCHEMA
            and context_package.get("trial_applicability_context")
            != trial.get("applicability_context")
        ):
            errors.append(f"arm_{arm}_applicability_context_binding_invalid")
        reconstructed = {
            "evaluation": evaluation.get("evaluation") or {},
            "invocation_result": invocation.get("response") or {},
            "receipts": {"model_proposal": proposal},
            "request": invocation.get("request") or {},
        }
        metrics = _arm_metrics(
            reconstructed,
            context_package=context_package,
            token_budget=int(budgets.get("token_budget") or 4096),
            latency_budget_ms=int(budgets.get("latency_budget_ms") or 30000),
            feedback_available=bool(context_package.get("usage_feedback")) if arm == "E" else False,
        )
        score = _utility(metrics, weights)
        evidence_class = str(circulation.get("evidence_class") or EVIDENCE_UNKNOWN)
        expected_identity = dict(circulation.get("model_identity") or {})
        expected_provenance = dict(circulation.get("adapter_provenance") or {})
        if str(trial.get("schema_version") or "") == SCHEMA:
            stored_family_bindings = (
                (trial.get("applicability_context") or {}).get(
                    "model_family_bindings"
                )
                if isinstance(trial.get("applicability_context"), Mapping)
                else {}
            )
            stored_family_binding = (
                stored_family_bindings.get(arm)
                if isinstance(stored_family_bindings, Mapping)
                else None
            )
            if stored_family_binding != _adapter_family_binding(expected_provenance):
                errors.append(f"arm_{arm}_model_family_binding_invalid")
        expected_bindings = dict(circulation.get("receipt_bindings") or {})
        comparisons = {
            "model_identity": expected_identity,
            "adapter_provenance": expected_provenance,
            "evidence_class": evidence_class,
            "context_hash": _sha(context_package),
            "context_projection_hash": circulation.get("context_projection_hash"),
            "task_contract_hash": circulation.get("task_contract_hash"),
            "circulation_receipts": expected_bindings,
            "metrics": metrics,
            "U": score,
            "evaluation_state": evaluation.get("evaluation", {}).get("state"),
            "witness_result_hash": circulation.get("witness"),
        }
        for key, expected in comparisons.items():
            if item.get(key) != expected:
                errors.append(f"arm_{arm}_{key}_binding_invalid")
        arm_scores[arm] = {"U": score, "metrics": metrics}
        arm_classes[arm] = evidence_class
    expected_fresh_identities = [
        dict(stored_arms[arm].get("model_identity") or {})
        for arm in ARMS
        if isinstance(stored_arms.get(arm), Mapping)
    ]
    if list(trial.get("fresh_model_identities") or ()) != expected_fresh_identities:
        errors.append("fresh_model_identities_not_reconstructed")
    gains = {
        "G_continuity": round(float(arm_scores.get("D", {}).get("U") or 0.0) - float(arm_scores.get("A", {}).get("U") or 0.0), 6),
        "G_distillation": round(float(arm_scores.get("D", {}).get("U") or 0.0) - float(arm_scores.get("B", {}).get("U") or 0.0), 6),
        "G_governance": round(float(arm_scores.get("D", {}).get("U") or 0.0) - float(arm_scores.get("C", {}).get("U") or 0.0), 6),
        "G_credit": round(float(arm_scores.get("E", {}).get("U") or 0.0) - float(arm_scores.get("D", {}).get("U") or 0.0), 6),
    }
    if dict(trial.get("gains") or {}) != gains:
        errors.append("transfer_gains_not_recomputed")
    origin = trial.get("origin_model") if isinstance(trial.get("origin_model"), Mapping) else {}
    status, reasons = _classify(
        arm_scores,
        policy=policy,
        fresh_identities=list(trial.get("fresh_model_identities") or ()),
        origin_identity=origin,
        arm_evidence_classes=[arm_classes.get(arm, EVIDENCE_UNKNOWN) for arm in ARMS],
        origin_evidence_class=str(trial.get("origin_evidence_class") or EVIDENCE_LEGACY),
        incompatible=bool(
            trial.get("arm_errors")
            or trial.get("feedback_errors")
            or trial.get("applicability_reasons")
        ),
        repetition_ready=(int(trial.get("feedback_reference_count") or 0) + 1)
        >= int(policy.get("min_repetitions") or 1),
        persisted=True,
    )
    if str(trial.get("portability_status") or "") != status:
        errors.append("portability_status_not_recomputed")
    if list(trial.get("classification_reasons") or ()) != reasons:
        errors.append("classification_reasons_not_recomputed")
    if dict(trial.get("arm_evidence_classes") or {}) != arm_classes:
        errors.append("arm_evidence_classes_not_recomputed")
    expected_aggregate = (
        EVIDENCE_LIVE
        if status.startswith("empirical_")
        else EVIDENCE_SYNTHETIC
        if arm_classes and all(item == EVIDENCE_SYNTHETIC for item in arm_classes.values())
        else EVIDENCE_SIMULATED
        if arm_classes and all(item in {EVIDENCE_SYNTHETIC, EVIDENCE_SIMULATED} for item in arm_classes.values())
        else EVIDENCE_UNKNOWN
    )
    if str(trial.get("evidence_class") or EVIDENCE_LEGACY) != expected_aggregate:
        errors.append("trial_evidence_class_not_recomputed")
    if status in {"incompatible", "unresolved"} and trial.get("arm_errors"):
        # Unsuccessful and incomplete experiments are canonical evidence too.
        # Their missing arms cannot authorize transfer because the derived
        # status is non-promotable, but the failed trial must remain durable.
        errors = [
            error
            for error in errors
            if not (error.startswith("arm_") and error.endswith("_missing"))
        ]
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "portability_status": status,
        "classification_reasons": reasons,
        "evidence_class": expected_aggregate,
        "arm_evidence_classes": arm_classes,
        "gains": gains,
    }


def run_cross_model_transfer_trial(
    store: Any,
    repo: str,
    *,
    competence_id: str,
    task_contract: TaskEvaluationContract,
    adapter_factory: Callable[[str], ModelAdapter],
    task: str,
    tool_scopes: Sequence[str] | None = None,
    tool_budget: Mapping[str, Any] | None = None,
    model_configuration: Mapping[str, Any] | None = None,
    policy: Mapping[str, Any] | None = None,
    target_profile_id: str | None = None,
    applicability_context: Mapping[str, Any] | None = None,
    prior_feedback: Sequence[Mapping[str, Any]] | None = None,
    measurement_cohort_id: str | None = None,
    trial_nonce: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run fresh-model arms A-E against one frozen competence candidate."""
    if not isinstance(task_contract, TaskEvaluationContract):
        raise TransferTrialError("task_contract must be frozen TaskEvaluationContract")
    if not callable(adapter_factory):
        raise TransferTrialError("adapter_factory is required for fresh model isolation")
    candidate = get_competence_candidate(store, repo, competence_id)
    if candidate is None:
        raise TransferTrialError("competence candidate is missing")
    candidate_check = verify_competence_candidate(store, repo, competence_id)
    if candidate_check.get("valid") is not True:
        raise TransferTrialError("competence candidate failed canonical verification")
    repository_id, repository = _repo_identity(store, repo)
    from .epoch import observe_current_epoch

    epoch = observe_current_epoch(store, repo)
    current_epoch_id = str(epoch.get("epoch_id") or epoch.get("live_epoch_id") or "")
    origin = candidate.get("evidence_lineage", {}).get("model_origin", {})
    origin_evidence_class = str(origin.get("evidence_class") or EVIDENCE_LEGACY)
    origin_epoch = str(
        (candidate.get("evidence_lineage", {}).get("originating_trajectories") or [{}])[0].get("body_epoch_id")
        or ""
    )
    # The trial freezes the epoch that produced K.  New canonical receipts may
    # advance the live epoch while the trial is being prepared; that drift is
    # recorded in the environment instead of silently relabeling K.
    body_epoch_id = origin_epoch
    if not body_epoch_id:
        raise TransferTrialError("competence has no origin epoch to freeze")
    frozen_policy = _policy(policy)
    tools = tuple(sorted({str(item) for item in tool_scopes or ()}))
    budgets = {"token_budget": 4096, "latency_budget_ms": 30000}
    budgets.update(dict(tool_budget or {}))
    configuration = dict(model_configuration or {})
    arm_results: dict[str, Any] = {}
    arm_scores: dict[str, Any] = {}
    fresh_identities: list[dict[str, str]] = []
    adapters: dict[str, ModelAdapter] = {}
    arm_errors: list[str] = []
    arm_evidence_classes: dict[str, str] = {}
    model_family_bindings: dict[str, dict[str, Any]] = {}
    seen_adapter_objects: set[int] = set()
    for arm in ARMS:
        try:
            adapter = adapter_factory(arm)
            if id(adapter) in seen_adapter_objects:
                raise TransferTrialError(
                    "adapter_factory reused one model instance across arms"
                )
            seen_adapter_objects.add(id(adapter))
            identity = _adapter_identity(adapter)
            if identity["model_id"] == str(origin.get("model_id") or ""):
                raise TransferTrialError(
                    "fresh model identity matches originating model"
                )
            adapters[arm] = adapter
            fresh_identities.append(identity)
            model_family_bindings[arm] = _adapter_family_binding(
                resolve_adapter_provenance(store, repo, adapter)
            )
        except (ModelAdapterError, TransferTrialError, TypeError, ValueError) as exc:
            arm_errors.append(f"{arm}:{type(exc).__name__}:{exc}")
    environment = {
        "repo": repo,
        "repository_id": repository_id,
        "manifest_hash": repository.get("manifest_hash"),
        "body_epoch_id": body_epoch_id,
        "current_epoch_id": current_epoch_id,
        "epoch_drifted_since_origin": current_epoch_id != body_epoch_id,
        "measurement_cohort_id": measurement_cohort_id,
    }
    frozen_applicability_context = _freeze_applicability_context(
        store,
        applicability_context,
        repo=repo,
        repository_id=repository_id,
        body_epoch_id=body_epoch_id,
        target_profile_id=target_profile_id,
        model_family_bindings=model_family_bindings,
    )
    applicability_verification = _trial_applicability_proof(
        candidate, frozen_applicability_context
    )
    if applicability_verification.get("applicable") is not True:
        raise TransferTrialError(
            "competence is not applicable to frozen trial context: "
            + ",".join(
                str(item)
                for item in applicability_verification.get("reasons") or ()
            )
        )
    trial_material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "repo": repo,
        "repository_id": repository_id,
        "competence_id": competence_id,
        "competence_receipt_hash": candidate.get("receipt_hash"),
        "task": str(task),
        "task_contract": task_contract.to_dict(),
        "task_contract_hash": task_contract.contract_hash,
        "environment": environment,
        "applicability_context": frozen_applicability_context,
        "applicability_verification": applicability_verification,
        "tools": list(tools),
        "budgets": budgets,
        "model_configuration": configuration,
        "policy": frozen_policy,
        "arms": list(ARMS),
        "origin_model": dict(origin),
        "trial_nonce": str(trial_nonce or ""),
        "fresh_model_identities": fresh_identities,
    }
    ordinary = {
        "arm": "A",
        "task": str(task),
        "repository": {"repo": repo, "repository_id": repository_id, "manifest_hash": repository.get("manifest_hash")},
        "competence_included": False,
        "trial_applicability_context": frozen_applicability_context,
    }
    origin_rows = store.symbiotic_session_receipts(
        repo,
        str((candidate.get("evidence_lineage", {}).get("originating_trajectories") or [{}])[0].get("session_id") or ""),
    )
    raw_history = {"arm": "B", "task": str(task), "raw_origin_public_history": _public_raw_history(origin_rows), "competence_included": False, "trial_applicability_context": frozen_applicability_context}
    unfiltered = {
        "arm": "C",
        "task": str(task),
        "unfiltered_admitted_memory": [
            {
                "memory_id": item.get("memory_id"),
                "candidate_type": item.get("candidate_type"),
                "summary": item.get("summary"),
                "current_state": item.get("current_state"),
            }
            for item in store.list_admitted_memories(repo)
        ],
        "competence_included": False,
        "trial_applicability_context": frozen_applicability_context,
    }
    applicability_reasons = list(applicability_verification["reasons"])
    competence = _candidate_projection(candidate)
    distilled = {"arm": "D", "task": str(task), "competence": competence, "competence_included": True, "trial_applicability_context": frozen_applicability_context}
    feedback_items: list[dict[str, Any]] = []
    feedback_errors: list[str] = []
    for reference in prior_feedback or ():
        if not isinstance(reference, Mapping):
            feedback_errors.append("feedback_reference_not_mapping")
            continue
        reference_id = str(reference.get("trial_id") or "")
        prior = get_transfer_trial(store, repo, reference_id) if reference_id else None
        if prior is None:
            feedback_errors.append("feedback_trial_missing")
            continue
        prior_check = verify_transfer_trial(store, repo, reference_id)
        if prior_check.get("valid") is not True:
            feedback_errors.append("feedback_trial_unverified")
            continue
        feedback_items.append(
            {
                "trial_id": reference_id,
                "portability_status": prior.get("portability_status"),
                "gains": prior.get("gains"),
                "arm_D": (prior.get("arm_results", {}).get("D") or {}).get("metrics"),
            }
        )
    enriched = {"arm": "E", "task": str(task), "competence": competence, "usage_feedback": feedback_items, "competence_included": True, "trial_applicability_context": frozen_applicability_context}
    packages = {"A": ordinary, "B": raw_history, "C": unfiltered, "D": distilled, "E": enriched}
    trial_id = _sha(trial_material)
    for arm in ARMS:
        try:
            adapter = adapters[arm]
            identity = _adapter_identity(adapter)
            session_id = "xfer_" + _sha({"trial": trial_id, "arm": arm, "model": identity, "t": time.time_ns()})[:20]
            session = _new_trial_session(
                store,
                repo,
                session_id=session_id,
                task=str(task),
                body_epoch_id=body_epoch_id,
                adapter=adapter,
                arm=arm,
                context_package=packages[arm],
                trial_id=trial_id,
                tool_scopes=tools,
                persist=persist,
            )
            result = run_model_circulation(
                store,
                repo,
                session,
                adapter=adapter,
                task_contract=task_contract,
                observed_result=None,
                tool_scopes=tools,
                configuration={**configuration, "transfer_trial_id": trial_id, "transfer_arm": arm},
                persist=persist,
            )
            verified: Mapping[str, Any] = {
                "valid": False,
                "evidence_class": result.get("evidence_class"),
                "receipt_bindings": {},
            }
            if persist:
                verified = verify_model_circulation(store, repo, session_id, turn_id=1)
                if not verified.get("valid"):
                    raise TransferTrialError("canonical arm circulation failed verification")
            metrics = _arm_metrics(
                result,
                context_package=packages[arm],
                token_budget=int(budgets.get("token_budget") or 4096),
                latency_budget_ms=int(budgets.get("latency_budget_ms") or 30000),
                feedback_available=bool(feedback_items) if arm == "E" else False,
            )
            score = _utility(metrics, frozen_policy["utility_weights"])
            arm_evidence_class = str(
                verified.get("evidence_class")
                or result.get("evidence_class")
                or EVIDENCE_UNKNOWN
            )
            arm_evidence_classes[arm] = arm_evidence_class
            arm_results[arm] = {
                "arm": arm,
                "session_id": session_id,
                "model_identity": identity,
                "adapter_provenance": dict(result.get("adapter_provenance") or {}),
                "evidence_class": arm_evidence_class,
                "context_hash": _sha(packages[arm]),
                "context_projection_hash": result.get("request", {}).get("context_projection_hash"),
                "task_contract_hash": task_contract.contract_hash,
                "circulation_receipts": dict(verified.get("receipt_bindings") or {}),
                "metrics": metrics,
                "U": score,
                "evaluation_state": (result.get("evaluation") or {}).get("state"),
                "witness_result_hash": (result.get("witness_result") or {}).get("witness_result_hash"),
                "persistence_status": result.get("persistence_status"),
            }
            arm_scores[arm] = arm_results[arm]
        except (KeyError, ModelAdapterError, TransferTrialError, TypeError, ValueError) as exc:
            arm_errors.append(f"{arm}:{type(exc).__name__}:{exc}")

    gains = {
        "G_continuity": round(float(arm_scores.get("D", {}).get("U") or 0.0) - float(arm_scores.get("A", {}).get("U") or 0.0), 6),
        "G_distillation": round(float(arm_scores.get("D", {}).get("U") or 0.0) - float(arm_scores.get("B", {}).get("U") or 0.0), 6),
        "G_governance": round(float(arm_scores.get("D", {}).get("U") or 0.0) - float(arm_scores.get("C", {}).get("U") or 0.0), 6),
        "G_credit": round(float(arm_scores.get("E", {}).get("U") or 0.0) - float(arm_scores.get("D", {}).get("U") or 0.0), 6),
    }
    status, classification_reasons = _classify(
        arm_scores,
        policy=frozen_policy,
        fresh_identities=fresh_identities,
        origin_identity=origin,
        arm_evidence_classes=[arm_evidence_classes.get(arm, EVIDENCE_UNKNOWN) for arm in ARMS],
        origin_evidence_class=origin_evidence_class,
        incompatible=bool(arm_errors or feedback_errors or applicability_reasons),
        repetition_ready=(len(feedback_items) + 1) >= int(frozen_policy.get("min_repetitions") or 1),
        persisted=persist,
    )
    aggregate_evidence_class = (
        EVIDENCE_LIVE
        if status.startswith("empirical_")
        else EVIDENCE_SYNTHETIC
        if arm_evidence_classes and all(item == EVIDENCE_SYNTHETIC for item in arm_evidence_classes.values())
        else EVIDENCE_SIMULATED
        if arm_evidence_classes and all(item in {EVIDENCE_SYNTHETIC, EVIDENCE_SIMULATED} for item in arm_evidence_classes.values())
        else EVIDENCE_UNKNOWN
    )
    trial = {
        **trial_material,
        "trial_id": trial_id,
        "body_epoch_id": body_epoch_id,
        "measurement_cohort_id": measurement_cohort_id,
        "created_at": time.time(),
        "arm_results": arm_results,
        "arm_errors": arm_errors,
        "feedback_errors": feedback_errors,
        "feedback_reference_count": len(feedback_items),
        "applicability_reasons": list(applicability_reasons),
        "gains": gains,
        "portability_status": status,
        "evidence_class": aggregate_evidence_class,
        "origin_evidence_class": origin_evidence_class,
        "arm_evidence_classes": dict(arm_evidence_classes),
        "empirical_transfer_established": status.startswith("empirical_"),
        "structural_transfer_established": status.startswith("structural_"),
        "classification_reasons": classification_reasons,
        "evidence": {
            "candidate_verification": candidate_check,
            "fresh_model_instances": fresh_identities,
            "matched_controls": list(ARMS),
            "origin_model_detached": True,
        },
        "distribution_authorized": False,
        "execution_authorized": False,
        "host_mutate_authorized": False,
        "memory_admission_authorized": False,
        "learning_authorized": False,
        "promotion_eligible": False,
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    trial["receipt_hash"] = _sha(
        {key: value for key, value in trial.items() if key not in {"receipt_hash", "created_at"}}
    )
    if persist:
        persisted = append_transfer_trial(store, repo, trial)
        persisted["portability_status"] = status
        return persisted
    return {**trial, "persisted": False}


def verify_transfer_trial(store: Any, repo: str, trial_id: str) -> dict[str, Any]:
    trial = get_transfer_trial(store, repo, trial_id)
    if trial is None:
        return {"valid": False, "errors": ["trial_missing"], "advisory_only": True}
    material = {
        key: value
        for key, value in trial.items()
        if key not in {"receipt_hash", "created_at", "inserted", "duplicate"}
    }
    errors: list[str] = []
    schema_version = str(trial.get("schema_version") or "")
    evidence_typed = schema_version in {SCHEMA, EVIDENCE_SCHEMA}
    if _sha(material) != str(trial.get("receipt_hash") or ""):
        errors.append("trial_receipt_hash_invalid")
    if trial.get("distribution_authorized") is not False or trial.get("execution_authorized") is not False:
        errors.append("trial_authority_flags_invalid")
    for arm in ARMS:
        if evidence_typed:
            continue
        item = trial.get("arm_results", {}).get(arm)
        if not isinstance(item, Mapping):
            errors.append(f"arm_{arm}_missing")
            continue
        session_id = str(item.get("session_id") or "")
        if not session_id:
            errors.append(f"arm_{arm}_session_missing")
            continue
        circulation = verify_model_circulation(store, repo, session_id, turn_id=1)
        if circulation.get("valid") is not True:
            errors.append(f"arm_{arm}_circulation_invalid")
    try:
        contract = TaskEvaluationContract.from_mapping(trial.get("task_contract") or {})
        if contract.contract_hash != str(trial.get("task_contract_hash") or ""):
            errors.append("task_contract_hash_invalid")
    except (TypeError, ValueError):
        errors.append("task_contract_invalid")
    try:
        candidate_check = verify_competence_candidate(
            store, repo, str(trial.get("competence_id") or "")
        )
        if candidate_check.get("valid") is not True:
            errors.append("competence_lineage_invalid")
    except Exception:
        errors.append("competence_lineage_unavailable")
    arm_scores = trial.get("arm_results") if isinstance(trial.get("arm_results"), Mapping) else {}
    expected_gains = {
        "G_continuity": ("D", "A"),
        "G_distillation": ("D", "B"),
        "G_governance": ("D", "C"),
        "G_credit": ("E", "D"),
    }
    for name, (left, right) in expected_gains.items():
        if left in arm_scores and right in arm_scores:
            observed = round(
                float(arm_scores[left].get("U") or 0.0)
                - float(arm_scores[right].get("U") or 0.0),
                6,
            )
            if observed != float((trial.get("gains") or {}).get(name)):
                errors.append(f"{name}_mismatch")
    conformance = (
        _validate_transfer_body(store, repo, trial)
        if evidence_typed
        else {
            "valid": True,
            "errors": [],
            "portability_status": "unresolved",
            "classification_reasons": ["legacy_trial_has_no_evidence_class"],
            "evidence_class": EVIDENCE_LEGACY,
            "arm_evidence_classes": {},
            "gains": dict(trial.get("gains") or {}),
        }
    )
    errors.extend(str(item) for item in conformance.get("errors") or ())
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "trial_id": trial_id,
        "receipt_hash": trial.get("receipt_hash"),
        "portability_status": conformance.get("portability_status"),
        "stored_portability_status": trial.get("portability_status"),
        "evidence_class": conformance.get("evidence_class"),
        "empirical_transfer_established": bool(
            evidence_typed
            and not errors
            and str(conformance.get("portability_status") or "").startswith(
                "empirical_"
            )
        ),
        "structural_transfer_established": bool(
            evidence_typed
            and not errors
            and str(conformance.get("portability_status") or "").startswith(
                "structural_"
            )
        ),
        "classification_reasons": list(
            conformance.get("classification_reasons") or ()
        ),
        "arm_evidence_classes": dict(
            conformance.get("arm_evidence_classes") or {}
        ),
        "legacy_partial": not evidence_typed,
        "distribution_authorized": False,
        "execution_authorized": False,
        "advisory_only": True,
    }


__all__ = [
    "ARMS",
    "CLAIM_BOUNDARY",
    "DEFAULT_POLICY",
    "PORTABILITY_STATES",
    "SCHEMA",
    "VERSION",
    "TransferTrialError",
    "append_transfer_trial",
    "ensure_transfer_tables",
    "get_transfer_trial",
    "list_transfer_trials",
    "run_cross_model_transfer_trial",
    "verify_transfer_trial",
]
