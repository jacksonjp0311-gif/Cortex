"""Policy-bound autonomous improvement for Cortex.

This module composes existing Storm, verification, counterfactual, and rollback
mechanics. It never creates authority from a model result or quality score.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .coding_workspace import (
    apply_approved_patch,
    default_verification_contract,
    repository_head,
    verify_patch_in_isolated_worktree,
    verify_patch_proposal,
)
from .epoch import observe_current_epoch
from .source_improvement import (
    create_source_improvement_contract,
    run_source_improvement_trial,
    verify_source_improvement_result,
)
from .symbiosis import open_symbiotic_session
from .storm import verify_storm_session


SCHEMA = "cortex-autonomous-improvement/1.0"
POLICY_SCHEMA = "cortex-autonomy-policy/1.0"
TOURNAMENT_SCHEMA = "cortex-improvement-tournament/1.0"
PROMOTION_SCHEMA = "cortex-policy-promotion/1.0"
EPISODE_SCHEMA = "cortex-improvement-episode/1.0"
GENERATION_SCHEMA = "cortex-generation-transition/1.0"
REVOCATION_SCHEMA = "cortex-autonomy-policy-revocation/1.0"

PERMANENTLY_PROTECTED_PREFIXES = (
    ".github/",
    ".cortex/",
    "cortex/will.py",
    "cortex/constitutional_",
    "cortex/capabilities.py",
    "cortex/promote_gate.py",
    "cortex/native_agent.py",
    "cortex/tool_fabric.py",
    "cortex/storm.py",
    "cortex/coding_workspace.py",
    "cortex/source_improvement.py",
    "cortex/autonomous_improvement.py",
    "tests/",
    "scripts/ci/",
    "pyproject.toml",
)


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


def _closed_authority() -> dict[str, bool]:
    return {
        "model_host_mutate_authorized": False,
        "model_execution_authorized": False,
        "memory_admission_authorized": False,
        "competence_promotion_authorized": False,
        "policy_effect": False,
    }


def _receipt_body(body: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(body)
    result["content_hash"] = _sha(result)
    return result


def _session(store: Any, repo: str, task: str) -> dict[str, Any]:
    return open_symbiotic_session(
        store,
        repo,
        task=task,
        provider="autonomy",
        model_id="provider-neutral",
        capability_profile={"autonomous_improvement": True},
        tool_scopes=(),
        persist=True,
    )


def synthesize_storm_claims(
    storm_result: Mapping[str, Any], claims: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Build an independence/conflict map without declaring any claim true."""

    verification = storm_result.get("verification")
    if not isinstance(verification, Mapping) or verification.get("valid") is not True:
        raise ValueError("canonical Storm verification is required")
    observations = {
        str(item.get("receipt_hash") or ""): item
        for item in storm_result.get("observations") or ()
        if isinstance(item, Mapping)
    }
    normalized: list[dict[str, Any]] = []
    for raw in claims:
        receipt_hash = str(raw.get("observation_receipt_hash") or "")
        observation = observations.get(receipt_hash)
        if not observation:
            raise ValueError("claim references an unrelated Storm observation")
        claim_key = str(raw.get("claim_key") or "").strip()
        stance = str(raw.get("stance") or "").strip()
        if not claim_key or stance not in {"affirm", "deny", "uncertain"}:
            raise ValueError("claim requires a key and typed stance")
        roots = sorted({str(item) for item in raw.get("evidence_roots") or () if str(item)})
        normalized.append(
            {
                "claim_key": claim_key,
                "stance": stance,
                "observation_receipt_hash": receipt_hash,
                "observation_hash": str(observation.get("observation_hash") or ""),
                "agent_id": str(observation.get("agent_id") or ""),
                "evidence_roots": roots,
            }
        )
    groups: list[dict[str, Any]] = []
    for key in sorted({item["claim_key"] for item in normalized}):
        members = [item for item in normalized if item["claim_key"] == key]
        stances = {item["stance"] for item in members if item["stance"] != "uncertain"}
        independent_roots = sorted({root for item in members for root in item["evidence_roots"]})
        state = "conflict" if {"affirm", "deny"}.issubset(stances) else "agreement" if len(stances) == 1 else "unresolved"
        groups.append(
            {
                "claim_key": key,
                "state": state,
                "member_count": len(members),
                "independent_evidence_root_count": len(independent_roots),
                "evidence_roots": independent_roots,
                "members": members,
                "truth_state": "unknown",
                "semantic_verification_required": True,
            }
        )
    body = {
        "schema_version": SCHEMA,
        "storm_session_id": str(storm_result.get("session_id") or ""),
        "storm_summary_receipt_hash": str(storm_result.get("summary_receipt_hash") or ""),
        "groups": groups,
        "claim_count": len(normalized),
        "agreement_is_truth": False,
        "advisory_only": True,
        **_closed_authority(),
    }
    body["synthesis_hash"] = _sha(body)
    return body


@dataclass(frozen=True)
class AutonomyPolicyEnvelope:
    principal_id: str
    policy_id: str
    allowed_path_prefixes: tuple[str, ...]
    forbidden_path_prefixes: tuple[str, ...] = PERMANENTLY_PROTECTED_PREFIXES
    allowed_trial_statuses: tuple[str, ...] = ("REPAIR_MEASURED",)
    canary_steps: tuple[Mapping[str, Any], ...] = ()
    max_files: int = 3
    max_changed_lines: int = 300
    allow_auto_promotion: bool = False
    allow_recursive_generation: bool = False
    issued_at: float = 0.0
    expires_at: float | None = None

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": POLICY_SCHEMA,
            "principal_id": str(self.principal_id).strip(),
            "policy_id": str(self.policy_id).strip(),
            "allowed_path_prefixes": sorted({str(item).replace("\\", "/") for item in self.allowed_path_prefixes if str(item)}),
            "forbidden_path_prefixes": sorted(
                set(PERMANENTLY_PROTECTED_PREFIXES)
                | {str(item).replace("\\", "/") for item in self.forbidden_path_prefixes if str(item)}
            ),
            "allowed_trial_statuses": sorted({str(item) for item in self.allowed_trial_statuses}),
            "canary_steps": json.loads(_canonical(list(self.canary_steps))),
            "max_files": max(1, min(int(self.max_files), 50)),
            "max_changed_lines": max(1, min(int(self.max_changed_lines), 10_000)),
            "allow_auto_promotion": bool(self.allow_auto_promotion),
            "allow_recursive_generation": bool(self.allow_recursive_generation),
            "issued_at": float(self.issued_at),
            "expires_at": float(self.expires_at) if self.expires_at is not None else None,
            "host_issued": True,
            "model_may_modify_policy": False,
            "policy_may_widen_itself": False,
            **_closed_authority(),
        }


def issue_autonomy_policy(
    store: Any, repo: str, envelope: AutonomyPolicyEnvelope, *, secret: str
) -> dict[str, Any]:
    body = envelope.material()
    if not body["principal_id"] or not body["policy_id"] or not secret:
        raise ValueError("registered principal, policy ID, and secret are required")
    principal = store.db.execute(
        "SELECT secret_hash FROM will_principals WHERE repo=? AND principal_id=?",
        (repo, body["principal_id"]),
    ).fetchone()
    supplied_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    if not principal or not hmac.compare_digest(supplied_hash, str(principal["secret_hash"])):
        raise PermissionError("principal secret does not match the canonical registration")
    if body["allow_auto_promotion"] and not body["canary_steps"]:
        raise ValueError("automatic promotion requires at least one host canary")
    epoch = observe_current_epoch(store, repo)
    if epoch.get("verified") is not True:
        raise RuntimeError("a current verified body epoch is required")
    body["bound_body_epoch_id"] = str(epoch.get("epoch_id") or "")
    body["policy_hash"] = _sha(body)
    body["signature"] = hmac.new(secret.encode("utf-8"), body["policy_hash"].encode("utf-8"), hashlib.sha256).hexdigest()
    session = _session(store, repo, f"issue autonomy policy {body['policy_id']}")
    return store.append_symbiotic_receipt(
        repo,
        _receipt_body(
            {
                **body,
                "kind": "autonomy_policy",
                "status": "active",
                "session_id": session["session_id"],
                "turn_id": 0,
                "event_id": f"autonomy_policy_{body['policy_hash'][:24]}",
                "body_epoch_id": session["body_epoch_id"],
            }
        ),
    )


def verify_autonomy_policy(
    store: Any, repo: str, receipt_hash: str, *, secret: str, now: float | None = None
) -> dict[str, Any]:
    receipt = store.symbiotic_receipt(receipt_hash, repo=repo)
    errors: list[str] = []
    if not receipt or receipt.get("kind") != "autonomy_policy":
        return {"valid": False, "errors": ["autonomy_policy_missing"]}
    principal = store.db.execute(
        "SELECT secret_hash FROM will_principals WHERE repo=? AND principal_id=?",
        (repo, str(receipt.get("principal_id") or "")),
    ).fetchone()
    supplied_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    if not principal or not hmac.compare_digest(supplied_hash, str(principal["secret_hash"])):
        errors.append("principal_secret_mismatch")
    excluded = {
        "policy_hash", "signature", "kind", "status", "session_id", "turn_id", "event_id",
        "body_epoch_id", "content_hash", "receipt_hash", "subject_receipt_hash",
        "previous_receipt_hash", "chain_sequence", "repository_id", "repo", "created_at",
        "ledger_schema_version", "inserted", "duplicate", "chain_valid",
    }
    material = {key: value for key, value in receipt.items() if key not in excluded}
    expected_hash = _sha(material)
    if str(receipt.get("policy_hash") or "") != expected_hash:
        errors.append("policy_hash_invalid")
    expected_signature = hmac.new(secret.encode("utf-8"), expected_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(receipt.get("signature") or ""), expected_signature):
        errors.append("policy_signature_invalid")
    checked_at = time.time() if now is None else float(now)
    if float(receipt.get("issued_at") or 0) > checked_at:
        errors.append("policy_not_yet_current")
    if receipt.get("expires_at") is not None and checked_at > float(receipt["expires_at"]):
        errors.append("policy_expired")
    epoch = observe_current_epoch(store, repo)
    if epoch.get("verified") is not True:
        errors.append("current_epoch_unverified")
    elif str(receipt.get("bound_body_epoch_id") or "") != str(epoch.get("epoch_id") or ""):
        errors.append("policy_epoch_stale")
    revocations = [
        item
        for item in store.symbiotic_receipts_by_kind(repo, "autonomy_policy_revocation")
        if item.get("policy_receipt_hash") == receipt_hash
    ]
    for revocation in revocations:
        revocation_material = {
            key: revocation.get(key)
            for key in (
                "schema_version",
                "policy_receipt_hash",
                "policy_hash",
                "principal_id",
                "reason",
                "revoked_at",
                "bound_body_epoch_id",
            )
        }
        revocation_hash = _sha(revocation_material)
        signature = hmac.new(
            secret.encode("utf-8"), revocation_hash.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        revocation_check = store.verify_symbiotic_receipt(
            repo, str(revocation.get("receipt_hash") or "")
        )
        if (
            revocation_check.get("valid") is not True
            or revocation.get("revocation_hash") != revocation_hash
            or not hmac.compare_digest(str(revocation.get("signature") or ""), signature)
            or revocation.get("principal_id") != receipt.get("principal_id")
        ):
            errors.append("policy_revocation_invalid")
        elif revocation.get("status") == "revoked":
            errors.append("policy_revoked")
    return {"valid": not errors, "errors": errors, "receipt": receipt}


def revoke_autonomy_policy(
    store: Any, repo: str, policy_receipt_hash: str, *, secret: str, reason: str
) -> dict[str, Any]:
    """Append an immutable principal-authenticated policy revocation."""

    check = verify_autonomy_policy(store, repo, policy_receipt_hash, secret=secret)
    if not check["valid"]:
        raise PermissionError("autonomy policy invalid: " + ",".join(check["errors"]))
    policy = check["receipt"]
    session = _session(store, repo, f"revoke autonomy policy {policy.get('policy_id')}")
    material = {
        "schema_version": REVOCATION_SCHEMA,
        "policy_receipt_hash": policy_receipt_hash,
        "policy_hash": str(policy.get("policy_hash") or ""),
        "principal_id": str(policy.get("principal_id") or ""),
        "reason": str(reason or "operator_revocation").strip(),
        "revoked_at": time.time(),
        "bound_body_epoch_id": str(policy.get("bound_body_epoch_id") or ""),
    }
    material["revocation_hash"] = _sha(material)
    material["signature"] = hmac.new(
        secret.encode("utf-8"), material["revocation_hash"].encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return store.append_symbiotic_receipt(
        repo,
        _receipt_body(
            {
                **material,
                "kind": "autonomy_policy_revocation",
                "status": "revoked",
                "session_id": session["session_id"],
                "turn_id": 0,
                "event_id": f"autonomy_revoke_{policy_receipt_hash[:24]}",
                "body_epoch_id": session["body_epoch_id"],
                **_closed_authority(),
            }
        ),
    )


def run_improvement_tournament(
    root: str | Path,
    candidates: Sequence[Mapping[str, Any]],
    *,
    allowed_statuses: Sequence[str] = ("REPAIR_MEASURED",),
) -> dict[str, Any]:
    """Rank canonically verified candidates without granting promotion."""

    workspace = Path(root).resolve()
    statuses = set(allowed_statuses)
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        proposal = candidate.get("proposal") if isinstance(candidate.get("proposal"), Mapping) else {}
        trial = candidate.get("trial") if isinstance(candidate.get("trial"), Mapping) else {}
        proposal_check = verify_patch_proposal(workspace, proposal)
        trial_check = verify_source_improvement_result(trial)
        targets = list(proposal.get("targets") or ())
        changed_lines = sum(
            1 for line in str(proposal.get("patch") or "").splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
        )
        eligible = (
            proposal_check.get("valid") is True
            and proposal_check.get("current") is True
            and trial_check.get("valid") is True
            and str(trial.get("status") or "") in statuses
        )
        candidate_duration = float(((trial.get("arms") or {}).get("candidate") or {}).get("duration_ms") or float("inf"))
        rows.append(
            {
                "proposal_hash": str(proposal.get("proposal_hash") or ""),
                "trial_hash": str(trial.get("result_hash") or ""),
                "status": str(trial.get("status") or ""),
                "paired_effect": int(trial.get("paired_effect") or 0),
                "candidate_duration_ms": candidate_duration,
                "target_count": len(targets),
                "changed_lines": changed_lines,
                "eligible": eligible,
                "errors": sorted(set((proposal_check.get("errors") or []) + (trial_check.get("errors") or []))),
            }
        )
    eligible_rows = [row for row in rows if row["eligible"]]
    eligible_rows.sort(
        key=lambda row: (-row["paired_effect"], row["target_count"], row["changed_lines"], row["candidate_duration_ms"], row["proposal_hash"])
    )
    selected = eligible_rows[0]["proposal_hash"] if eligible_rows else ""
    body = {
        "schema_version": TOURNAMENT_SCHEMA,
        "source_head": repository_head(workspace),
        "candidates": rows,
        "selected_proposal_hash": selected,
        "selection_state": "selected" if selected else "held",
        "promotion_authorized": False,
        "model_selected_policy": False,
        **_closed_authority(),
    }
    body["tournament_hash"] = _sha(body)
    return body


def collect_storm_patch_candidates(
    store: Any, repo: str, storm_result: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Resolve patch proposals from canonical child trajectories, never prose."""

    verification = storm_result.get("verification")
    if not isinstance(verification, Mapping) or verification.get("valid") is not True:
        raise ValueError("verified Storm result is required")
    candidates: list[dict[str, Any]] = []
    for observation in storm_result.get("observations") or ():
        if not isinstance(observation, Mapping) or observation.get("trajectory_valid") is not True:
            continue
        trajectory_hash = str(observation.get("trajectory_receipt_hash") or "")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo)
        if not trajectory or trajectory.get("kind") != "native_agent_trajectory":
            continue
        for result in trajectory.get("tool_results") or ():
            if not isinstance(result, Mapping) or result.get("tool_name") != "workspace.propose_patch":
                continue
            output = result.get("output") if isinstance(result.get("output"), Mapping) else {}
            if not output.get("proposal_hash"):
                continue
            candidates.append(
                {
                    "agent_id": str(observation.get("agent_id") or ""),
                    "storm_observation_receipt_hash": str(observation.get("receipt_hash") or ""),
                    "trajectory_receipt_hash": trajectory_hash,
                    "tool_result_hash": str(result.get("result_hash") or ""),
                    "proposal": dict(output),
                }
            )
    candidates.sort(key=lambda item: (item["agent_id"], item["proposal"]["proposal_hash"]))
    return candidates


def resolve_canonical_storm_result(
    store: Any, repo: str, summary_receipt_hash: str
) -> dict[str, Any]:
    """Reconstruct a Storm result exclusively from its immutable ledger."""

    verification = verify_storm_session(store, repo, summary_receipt_hash)
    if verification.get("valid") is not True:
        raise ValueError(
            "canonical Storm verification failed: "
            + ",".join(verification.get("errors") or ())
        )
    summary = store.symbiotic_receipt(summary_receipt_hash, repo=repo)
    if not summary:
        raise ValueError("canonical Storm summary is missing")
    observations = []
    for receipt_hash in summary.get("observation_receipt_hashes") or ():
        observation = store.symbiotic_receipt(str(receipt_hash), repo=repo)
        if not observation:
            raise ValueError("canonical Storm observation is missing")
        observations.append(observation)
    return {
        "schema_version": str(summary.get("schema_version") or ""),
        "session_id": str(summary.get("session_id") or ""),
        "status": str(summary.get("status") or ""),
        "plan_receipt_hash": str(summary.get("plan_receipt_hash") or ""),
        "summary_receipt_hash": summary_receipt_hash,
        "observations": observations,
        "verification": verification,
        "authority": _closed_authority(),
    }


def run_autonomous_improvement_campaign(
    store: Any,
    repo: str,
    root: str | Path,
    *,
    storm_result: Mapping[str, Any],
    policy_receipt_hash: str,
    secret: str,
    auto_promote: bool = False,
    checkpoint: Callable[[str, Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Verify, measure, compare, and optionally promote Storm patch candidates.

    A host-owned checkpoint callback may record liveness and raise cancellation
    between expensive stages. Callback output is ignored and grants no
    authority; only its bounded stop exception affects progression.
    """

    def observe(stage: str, **details: Any) -> None:
        if checkpoint is not None:
            checkpoint(stage, details)

    workspace = Path(root).resolve()
    observe("context", phase="policy_verification")
    policy_check = verify_autonomy_policy(store, repo, policy_receipt_hash, secret=secret)
    if not policy_check["valid"]:
        raise PermissionError("autonomy policy invalid: " + ",".join(policy_check["errors"]))
    policy = policy_check["receipt"]
    canonical_storm = resolve_canonical_storm_result(
        store, repo, str(storm_result.get("summary_receipt_hash") or "")
    )
    observe("context", phase="storm_resolution")
    candidates = collect_storm_patch_candidates(store, repo, canonical_storm)
    session = _session(store, repo, "autonomous Storm improvement campaign")
    evaluated: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, 1):
        proposal = candidate["proposal"]
        observe(
            "candidate",
            candidate_index=index,
            proposal_hash=str(proposal.get("proposal_hash") or ""),
        )
        scope_errors = _policy_scope_errors(policy, proposal)
        if scope_errors:
            evaluated.append({**candidate, "eligible": False, "errors": scope_errors})
            continue
        contract = default_verification_contract(workspace, list(proposal.get("targets") or ()))
        observe(
            "verification",
            candidate_index=index,
            proposal_hash=str(proposal.get("proposal_hash") or ""),
        )
        verification = verify_patch_in_isolated_worktree(workspace, proposal, contract)
        verification_receipt = store.append_symbiotic_receipt(
            repo,
            _receipt_body(
                {
                    **verification,
                    "kind": "coding_patch_verification",
                    "session_id": session["session_id"],
                    "turn_id": 100 + index,
                    "event_id": f"campaign_verify_{str(proposal.get('proposal_hash'))[:24]}",
                    "body_epoch_id": session["body_epoch_id"],
                    "source_trajectory_hash": candidate["trajectory_receipt_hash"],
                    "storm_observation_receipt_hash": candidate[
                        "storm_observation_receipt_hash"
                    ],
                    "advisory_only": True,
                    "update_authorized": False,
                }
            ),
        )
        if verification_receipt.get("status") != "verified":
            evaluated.append(
                {
                    **candidate,
                    "verification": verification_receipt,
                    "eligible": False,
                    "errors": ["isolated_verification_held"],
                }
            )
            continue
        improvement_contract = create_source_improvement_contract(
            workspace, proposal, verification_receipt
        )
        observe(
            "trial",
            candidate_index=index,
            proposal_hash=str(proposal.get("proposal_hash") or ""),
        )
        trial = run_source_improvement_trial(
            workspace, proposal, verification_receipt, improvement_contract
        )
        trial_receipt = store.append_symbiotic_receipt(
            repo,
            _receipt_body(
                {
                    **trial,
                    "kind": "coding_improvement_trial",
                    "session_id": session["session_id"],
                    "turn_id": 200 + index,
                    "event_id": f"campaign_trial_{str(proposal.get('proposal_hash'))[:24]}",
                    "body_epoch_id": session["body_epoch_id"],
                    "source_trajectory_hash": candidate["trajectory_receipt_hash"],
                    "storm_observation_receipt_hash": candidate[
                        "storm_observation_receipt_hash"
                    ],
                    "advisory_only": True,
                    "update_authorized": False,
                }
            ),
        )
        evaluated.append(
            {
                **candidate,
                "verification": verification_receipt,
                "trial": trial_receipt,
                "eligible": True,
                "errors": [],
            }
        )
    observe("tournament", eligible_candidate_count=sum(bool(item.get("eligible")) for item in evaluated))
    tournament = run_improvement_tournament(
        workspace,
        [item for item in evaluated if isinstance(item.get("trial"), Mapping)],
        allowed_statuses=policy.get("allowed_trial_statuses") or (),
    )
    tournament_receipt = store.append_symbiotic_receipt(
        repo,
        _receipt_body(
            {
                **tournament,
                "kind": "improvement_tournament",
                "session_id": session["session_id"],
                "turn_id": 300,
                "event_id": f"campaign_tournament_{tournament['tournament_hash'][:24]}",
                "body_epoch_id": session["body_epoch_id"],
                "storm_summary_receipt_hash": str(
                    canonical_storm.get("summary_receipt_hash") or ""
                ),
                "policy_receipt_hash": policy_receipt_hash,
                "advisory_only": True,
                "update_authorized": False,
            }
        ),
    )
    promotion = None
    selected = str(tournament.get("selected_proposal_hash") or "")
    if auto_promote and selected:
        observe("integration_wait", selected_proposal_hash=selected)
        winner = next(
            item
            for item in evaluated
            if (item.get("proposal") or {}).get("proposal_hash") == selected
        )
        promotion = promote_tournament_winner(
            store,
            repo,
            workspace,
            policy_receipt_hash=policy_receipt_hash,
            secret=secret,
            tournament=tournament_receipt,
            proposal=winner["proposal"],
            trial=winner["trial"],
        )
    return {
        "schema_version": SCHEMA,
        "campaign_session_id": session["session_id"],
        "storm_summary_receipt_hash": str(canonical_storm.get("summary_receipt_hash") or ""),
        "candidate_count": len(candidates),
        "evaluated": evaluated,
        "tournament": tournament_receipt,
        "promotion": promotion,
        "auto_promote_requested": bool(auto_promote),
        "authority": _closed_authority(),
    }


def _policy_scope_errors(policy: Mapping[str, Any], proposal: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    targets = [str(item).replace("\\", "/") for item in proposal.get("targets") or ()]
    allowed = tuple(str(item) for item in policy.get("allowed_path_prefixes") or ())
    forbidden = tuple(str(item) for item in policy.get("forbidden_path_prefixes") or ())
    if len(targets) > int(policy.get("max_files") or 0):
        errors.append("policy_file_budget_exceeded")
    for target in targets:
        if not any(target.startswith(prefix) for prefix in allowed):
            errors.append(f"policy_path_not_allowed:{target}")
        if any(target.startswith(prefix) for prefix in forbidden):
            errors.append(f"policy_path_forbidden:{target}")
    changed = sum(
        1 for line in str(proposal.get("patch") or "").splitlines() if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    )
    if changed > int(policy.get("max_changed_lines") or 0):
        errors.append("policy_line_budget_exceeded")
    return errors


def promote_tournament_winner(
    store: Any,
    repo: str,
    root: str | Path,
    *,
    policy_receipt_hash: str,
    secret: str,
    tournament: Mapping[str, Any],
    proposal: Mapping[str, Any],
    trial: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply one winner only inside the signed envelope and rollback on canary failure."""

    policy_check = verify_autonomy_policy(store, repo, policy_receipt_hash, secret=secret)
    if not policy_check["valid"]:
        raise PermissionError("autonomy policy invalid: " + ",".join(policy_check["errors"]))
    policy = policy_check["receipt"]
    tournament_hash = str(tournament.get("receipt_hash") or "")
    canonical_tournament = store.symbiotic_receipt(tournament_hash, repo=repo)
    if not canonical_tournament or canonical_tournament.get("kind") != "improvement_tournament":
        raise PermissionError("promotion held: canonical_tournament_missing")
    tournament_receipt_check = store.verify_symbiotic_receipt(repo, tournament_hash)
    if tournament_receipt_check.get("valid") is not True:
        raise PermissionError("promotion held: canonical_tournament_invalid")
    trial_receipt_hash = str(trial.get("receipt_hash") or "")
    canonical_trial = store.symbiotic_receipt(trial_receipt_hash, repo=repo)
    if not canonical_trial or canonical_trial.get("kind") != "coding_improvement_trial":
        raise PermissionError("promotion held: canonical_trial_missing")
    trial_receipt_check = store.verify_symbiotic_receipt(repo, trial_receipt_hash)
    if trial_receipt_check.get("valid") is not True:
        raise PermissionError("promotion held: canonical_trial_invalid")
    errors = _policy_scope_errors(policy, proposal)
    trial_check = verify_source_improvement_result(canonical_trial)
    if not trial_check["valid"]:
        errors.append("improvement_trial_invalid")
    if canonical_trial.get("status") not in set(policy.get("allowed_trial_statuses") or ()):
        errors.append("improvement_status_not_authorized")
    if canonical_tournament.get("policy_receipt_hash") != policy_receipt_hash:
        errors.append("tournament_policy_mismatch")
    if canonical_tournament.get("selected_proposal_hash") != proposal.get("proposal_hash"):
        errors.append("proposal_is_not_tournament_winner")
    selected_row = next(
        (
            row
            for row in canonical_tournament.get("candidates") or ()
            if isinstance(row, Mapping)
            and row.get("proposal_hash") == proposal.get("proposal_hash")
        ),
        None,
    )
    if not selected_row or selected_row.get("trial_hash") != canonical_trial.get("result_hash"):
        errors.append("tournament_trial_binding_invalid")
    if policy.get("allow_auto_promotion") is not True:
        errors.append("auto_promotion_not_delegated")
    if repository_head(root) != canonical_tournament.get("source_head"):
        errors.append("source_head_changed")
    if not policy.get("canary_steps"):
        errors.append("canary_contract_missing")
    if errors:
        raise PermissionError("promotion held: " + ",".join(sorted(set(errors))))

    canary_contract = default_verification_contract(
        root, list(proposal.get("targets") or ())
    )
    canary_contract["policy_id"] = str(policy.get("policy_id") or "")
    canary_contract["steps"] = json.loads(_canonical(policy.get("canary_steps") or ()))
    canary_contract["contract_hash"] = _sha(
        {key: value for key, value in canary_contract.items() if key != "contract_hash"}
    )
    canary = verify_patch_in_isolated_worktree(root, proposal, canary_contract)
    canary_results = list(canary.get("steps") or ())
    rolled_back = canary.get("status") != "verified"
    application = None if rolled_back else apply_approved_patch(root, proposal)
    status = "promoted_canary_pass" if not rolled_back else "rolled_back_canary_failed"
    session = _session(store, repo, f"policy promotion {proposal.get('proposal_hash')}")
    receipt = store.append_symbiotic_receipt(
        repo,
        _receipt_body(
            {
                "schema_version": PROMOTION_SCHEMA,
                "kind": "policy_bound_promotion",
                "status": status,
                "session_id": session["session_id"],
                "turn_id": 1,
                "event_id": f"policy_promotion_{str(proposal.get('proposal_hash'))[:24]}",
                "body_epoch_id": session["body_epoch_id"],
                "policy_receipt_hash": policy_receipt_hash,
                "tournament_receipt_hash": tournament_hash,
                "tournament_hash": canonical_tournament["tournament_hash"],
                "proposal_hash": proposal["proposal_hash"],
                "trial_receipt_hash": trial_receipt_hash,
                "trial_hash": canonical_trial["result_hash"],
                "application": application,
                "canary_results": canary_results,
                "canary_isolated_before_active_apply": True,
                "rolled_back": rolled_back,
                "host_policy_authorized": True,
                "autonomous_within_policy": True,
                **_closed_authority(),
            }
        ),
    )
    return receipt


def record_improvement_episode(
    store: Any,
    repo: str,
    promotion_receipt: Mapping[str, Any],
    *,
    lessons: Sequence[str] = (),
    counterevidence: Sequence[str] = (),
) -> dict[str, Any]:
    """Persist observational improvement history, not admitted semantic memory."""

    canonical = store.symbiotic_receipt(str(promotion_receipt.get("receipt_hash") or ""), repo=repo)
    if not canonical or canonical.get("kind") != "policy_bound_promotion":
        raise ValueError("canonical policy promotion is required")
    session = _session(store, repo, "record improvement episode")
    return store.append_symbiotic_receipt(
        repo,
        _receipt_body(
            {
                "schema_version": EPISODE_SCHEMA,
                "kind": "improvement_episode",
                "status": "observed",
                "session_id": session["session_id"],
                "turn_id": 1,
                "event_id": f"improvement_episode_{str(canonical.get('receipt_hash'))[:24]}",
                "body_epoch_id": session["body_epoch_id"],
                "promotion_receipt_hash": canonical["receipt_hash"],
                "proposal_hash": canonical["proposal_hash"],
                "outcome": canonical["status"],
                "lessons": sorted({str(item) for item in lessons if str(item)}),
                "counterevidence": sorted({str(item) for item in counterevidence if str(item)}),
                "historical_evidence_only": True,
                "active_guidance": False,
                **_closed_authority(),
            }
        ),
    )


def verify_generation_transition(
    *,
    parent_generation: str,
    candidate_generation: str,
    verifier_generation: str,
    policy: Mapping[str, Any],
    tournament: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    errors = _policy_scope_errors(policy, proposal)
    if not parent_generation or not candidate_generation or parent_generation == candidate_generation:
        errors.append("generation_identity_invalid")
    if verifier_generation != parent_generation:
        errors.append("candidate_generation_cannot_self_verify")
    if policy.get("allow_recursive_generation") is not True:
        errors.append("recursive_generation_not_delegated")
    if tournament.get("selected_proposal_hash") != proposal.get("proposal_hash"):
        errors.append("generation_candidate_not_tournament_winner")
    body = {
        "schema_version": GENERATION_SCHEMA,
        "parent_generation": parent_generation,
        "candidate_generation": candidate_generation,
        "verifier_generation": verifier_generation,
        "proposal_hash": str(proposal.get("proposal_hash") or ""),
        "eligible": not errors,
        "errors": sorted(set(errors)),
        "candidate_self_authorized": False,
        "promotion_authorized": False,
        **_closed_authority(),
    }
    body["transition_hash"] = _sha(body)
    return body


__all__ = [
    "AutonomyPolicyEnvelope",
    "PERMANENTLY_PROTECTED_PREFIXES",
    "issue_autonomy_policy",
    "collect_storm_patch_candidates",
    "promote_tournament_winner",
    "record_improvement_episode",
    "resolve_canonical_storm_result",
    "revoke_autonomy_policy",
    "run_improvement_tournament",
    "run_autonomous_improvement_campaign",
    "synthesize_storm_claims",
    "verify_autonomy_policy",
    "verify_generation_transition",
]
