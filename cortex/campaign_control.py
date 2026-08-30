"""Authenticated, replay-resistant host control for autonomous campaigns.

This module issues short-lived loopback control sessions. Raw bearer and CSRF
secrets are returned once to the operator and are never persisted in Cortex.
It does not itself execute a campaign or grant model authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from .epoch import observe_current_epoch
from .symbiosis import open_symbiotic_session

SCHEMA = "cortex-campaign-control/1.0"
SESSION_SCHEMA = "cortex-campaign-control-session/1.0"
ACTION_SCHEMA = "cortex-campaign-control-action/1.0"
REVOCATION_SCHEMA = "cortex-campaign-control-revocation/1.0"
LIFECYCLE_SCHEMA = "cortex-campaign-lifecycle/1.0"
LIFECYCLE_VERIFICATION_SCHEMA = "cortex-campaign-lifecycle-verification/1.0"

ALLOWED_CONTROL_ACTIONS = frozenset(
    {
        "campaign.prepare",
        "campaign.start",
        "campaign.cancel",
        "campaign.promote",
        "campaign.integrate",
        "campaign.rollback",
        "control.revoke",
    }
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _secret_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _closed_authority() -> dict[str, bool]:
    return {
        "model_host_mutate_authorized": False,
        "model_execution_authorized": False,
        "memory_admission_authorized": False,
        "competence_promotion_authorized": False,
        "policy_effect": False,
    }


def _loopback_origin(origin: str) -> bool:
    try:
        parsed = urlparse(origin)
    except ValueError:
        return False
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _session(store: Any, repo: str, task: str) -> dict[str, Any]:
    return open_symbiotic_session(
        store,
        repo,
        task=task,
        provider="host-control",
        model_id="none",
        capability_profile={"campaign_control": True},
        tool_scopes=(),
        persist=True,
    )


def campaign_action_request(
    campaign_id: str,
    action: str,
    *,
    prior_state_receipt_hash: str = "",
    policy_receipt_hash: str = "",
    storm_summary_receipt_hash: str = "",
) -> dict[str, str]:
    """Build the exact public material covered by one action authorization."""

    return {
        "campaign_id": str(campaign_id),
        "action": str(action),
        "prior_state_receipt_hash": str(prior_state_receipt_hash),
        "policy_receipt_hash": str(policy_receipt_hash),
        "storm_summary_receipt_hash": str(storm_summary_receipt_hash),
    }


def verify_control_action(
    store: Any,
    repo: str,
    action_authorization: Mapping[str, Any],
    *,
    expected_action: str,
    expected_request: Mapping[str, Any],
    consumed_kinds: Sequence[str] = ("campaign_lifecycle",),
    now: float | None = None,
) -> dict[str, Any]:
    """Verify an action at spend time, including its live parent capability."""

    receipt_hash = str(action_authorization.get("receipt_hash") or "")
    canonical = store.symbiotic_receipt(receipt_hash, repo=repo)
    errors: list[str] = []
    if not canonical or canonical.get("kind") != "campaign_control_action":
        errors.append("canonical_action_missing")
    else:
        if store.verify_symbiotic_receipt(repo, receipt_hash).get("valid") is not True:
            errors.append("canonical_action_invalid")
        if canonical.get("action") != expected_action:
            errors.append("canonical_action_mismatch")
        if canonical.get("request_hash") != _sha(dict(expected_request)):
            errors.append("canonical_action_request_mismatch")
        parent_hash = str(canonical.get("control_session_receipt_hash") or "")
        parent = store.symbiotic_receipt(parent_hash, repo=repo)
        checked_at = time.time() if now is None else float(now)
        if not parent or parent.get("kind") != "campaign_control_session":
            errors.append("parent_control_session_missing")
        else:
            if store.verify_symbiotic_receipt(repo, parent_hash).get("valid") is not True:
                errors.append("parent_control_session_invalid")
            if canonical.get("principal_id") != parent.get("principal_id"):
                errors.append("parent_control_principal_mismatch")
            if checked_at < float(canonical.get("authorized_at") or 0):
                errors.append("canonical_action_not_yet_current")
            spend_expires_at = float(
                canonical.get("spend_expires_at")
                or parent.get("expires_at")
                or 0
            )
            if checked_at > spend_expires_at:
                errors.append("canonical_action_expired")
            epoch = observe_current_epoch(store, repo)
            if epoch.get("verified") is not True:
                errors.append("current_epoch_unverified")
            elif parent.get("bound_body_epoch_id") != epoch.get("epoch_id"):
                errors.append("parent_control_session_epoch_stale")
            revocations = store.symbiotic_receipts_by_kind(
                repo, "campaign_control_revocation"
            )
            if any(
                item.get("control_session_receipt_hash") == parent_hash
                for item in revocations
            ):
                errors.append("parent_control_session_revoked")
        for kind in consumed_kinds:
            used = store.symbiotic_receipts_by_kind(repo, str(kind))
            if any(
                item.get("action_authorization_receipt_hash") == receipt_hash
                for item in used
            ):
                errors.append("canonical_action_already_consumed")
                break
    if errors:
        raise PermissionError("campaign transition held: " + ",".join(errors))
    return canonical


def verify_campaign_lifecycle(
    store: Any,
    repo: str,
    campaign_id: str,
    *,
    require_current_epoch: bool = True,
) -> dict[str, Any]:
    """Reconstruct and semantically verify one immutable campaign chain."""

    campaign_id = str(campaign_id)
    rows = [
        item
        for item in store.symbiotic_receipts_by_kind(repo, "campaign_lifecycle")
        if item.get("campaign_id") == campaign_id
    ]
    errors: list[str] = []
    if not rows:
        return {
            "schema_version": LIFECYCLE_VERIFICATION_SCHEMA,
            "campaign_id": campaign_id,
            "valid": False,
            "state": None,
            "receipt_count": 0,
            "errors": ["campaign_lifecycle_missing"],
        }
    ordered = sorted(
        rows,
        key=lambda item: (int(item.get("state_sequence") or 0), item["receipt_hash"]),
    )
    expected_transitions = {
        (None, "prepared_request"): "campaign.prepare",
        ("prepared_request", "start_requested"): "campaign.start",
        ("prepared_request", "cancel_requested"): "campaign.cancel",
        ("start_requested", "cancel_requested"): "campaign.cancel",
    }
    root_policy = str(ordered[0].get("policy_receipt_hash") or "")
    root_storm = str(ordered[0].get("storm_summary_receipt_hash") or "")
    seen_sequences: set[int] = set()
    prior: dict[str, Any] | None = None
    for index, row in enumerate(ordered):
        sequence = int(row.get("state_sequence") or 0)
        if sequence in seen_sequences:
            errors.append(f"conflicting_state_sequence:{sequence}")
        seen_sequences.add(sequence)
        if sequence != index:
            errors.append(f"state_sequence_gap:{sequence}")
        if store.verify_symbiotic_receipt(repo, str(row["receipt_hash"])).get("valid") is not True:
            errors.append(f"lifecycle_receipt_invalid:{sequence}")
        expected_previous = str((prior or {}).get("receipt_hash") or "")
        if str(row.get("previous_state_receipt_hash") or "") != expected_previous:
            errors.append(f"previous_state_mismatch:{sequence}")
        if row.get("campaign_id") != campaign_id:
            errors.append(f"campaign_identity_mismatch:{sequence}")
        if str(row.get("policy_receipt_hash") or "") != root_policy:
            errors.append(f"policy_root_drift:{sequence}")
        if str(row.get("storm_summary_receipt_hash") or "") != root_storm:
            errors.append(f"storm_root_drift:{sequence}")
        prior_status = str(prior.get("status") or "") if prior else None
        status = str(row.get("status") or "")
        expected_action = expected_transitions.get((prior_status, status))
        if expected_action is None:
            errors.append(f"illegal_transition:{prior_status or 'genesis'}->{status}")
        action_hash = str(row.get("action_authorization_receipt_hash") or "")
        action = store.symbiotic_receipt(action_hash, repo=repo)
        if not action or action.get("kind") != "campaign_control_action":
            errors.append(f"lifecycle_action_missing:{sequence}")
        else:
            if store.verify_symbiotic_receipt(repo, action_hash).get("valid") is not True:
                errors.append(f"lifecycle_action_invalid:{sequence}")
            if expected_action and action.get("action") != expected_action:
                errors.append(f"lifecycle_action_mismatch:{sequence}")
            request = campaign_action_request(
                campaign_id,
                expected_action or "",
                prior_state_receipt_hash=expected_previous,
                policy_receipt_hash=root_policy,
                storm_summary_receipt_hash=root_storm,
            )
            if action.get("request_hash") != _sha(request):
                errors.append(f"lifecycle_request_mismatch:{sequence}")
            parent = store.symbiotic_receipt(
                str(action.get("control_session_receipt_hash") or ""), repo=repo
            )
            if not parent or parent.get("kind") != "campaign_control_session":
                errors.append(f"lifecycle_parent_session_missing:{sequence}")
            else:
                consumed_at = float(row.get("created_at") or 0)
                if consumed_at < float(action.get("authorized_at") or 0):
                    errors.append(f"lifecycle_chronology_invalid:{sequence}")
                if consumed_at > float(
                    action.get("spend_expires_at")
                    or parent.get("expires_at")
                    or 0
                ):
                    errors.append(f"lifecycle_action_expired_at_spend:{sequence}")
                revocations = store.symbiotic_receipts_by_kind(
                    repo, "campaign_control_revocation"
                )
                if any(
                    item.get("control_session_receipt_hash")
                    == parent.get("receipt_hash")
                    and float(item.get("revoked_at") or 0) <= consumed_at
                    for item in revocations
                ):
                    errors.append(f"lifecycle_session_revoked_at_spend:{sequence}")
        prior = row

    for label, kind, receipt_hash in (
        ("policy", "autonomy_policy", root_policy),
        ("storm", "storm_summary", root_storm),
    ):
        canonical = store.symbiotic_receipt(receipt_hash, repo=repo)
        if (
            not canonical
            or canonical.get("kind") != kind
            or store.verify_symbiotic_receipt(repo, receipt_hash).get("valid") is not True
        ):
            errors.append(f"canonical_{label}_root_invalid")
    if require_current_epoch:
        epoch = observe_current_epoch(store, repo)
        if epoch.get("verified") is not True:
            errors.append("current_epoch_unverified")
        elif any(row.get("body_epoch_id") != epoch.get("epoch_id") for row in ordered):
            errors.append("campaign_lifecycle_epoch_stale")
    return {
        "schema_version": LIFECYCLE_VERIFICATION_SCHEMA,
        "campaign_id": campaign_id,
        "valid": not errors,
        "state": ordered[-1] if not errors else None,
        "latest_observed_state": ordered[-1],
        "receipt_count": len(ordered),
        "policy_receipt_hash": root_policy,
        "storm_summary_receipt_hash": root_storm,
        "errors": sorted(set(errors)),
        **_closed_authority(),
    }


def campaign_state(store: Any, repo: str, campaign_id: str) -> dict[str, Any] | None:
    """Return the latest state only after full lifecycle reconstruction."""

    verification = verify_campaign_lifecycle(store, repo, campaign_id)
    if verification.get("errors") == ["campaign_lifecycle_missing"]:
        return None
    if verification.get("valid") is not True:
        raise PermissionError(
            "campaign lifecycle held: "
            + ",".join(verification.get("errors") or ())
        )
    return verification["state"]


def _append_campaign_state(
    store: Any,
    repo: str,
    *,
    campaign_id: str,
    state: str,
    prior: Mapping[str, Any] | None,
    action: Mapping[str, Any],
    policy_receipt_hash: str,
    storm_summary_receipt_hash: str,
) -> dict[str, Any]:
    sequence = 0 if prior is None else int(prior.get("state_sequence") or 0) + 1
    session = _session(store, repo, f"campaign {campaign_id} -> {state}")
    return store.append_symbiotic_receipt(
        repo,
        {
            "schema_version": LIFECYCLE_SCHEMA,
            "kind": "campaign_lifecycle",
            "status": state,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"campaign_{_sha([campaign_id, sequence, state])[:24]}",
            "body_epoch_id": session["body_epoch_id"],
            "campaign_id": campaign_id,
            "state_sequence": sequence,
            "previous_state_receipt_hash": str(
                (prior or {}).get("receipt_hash") or ""
            ),
            "action_authorization_receipt_hash": action["receipt_hash"],
            "principal_id": action["principal_id"],
            "policy_receipt_hash": policy_receipt_hash,
            "storm_summary_receipt_hash": storm_summary_receipt_hash,
            "cooperative_stop_required": state == "cancel_requested",
            "campaign_execution_observed": False,
            "evidence_semantics_verified": False,
            "host_control_authorized": True,
            **_closed_authority(),
        },
    )


def prepare_campaign(
    store: Any,
    repo: str,
    *,
    campaign_id: str,
    policy_receipt_hash: str,
    storm_summary_receipt_hash: str,
    action_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist host intent bound to canonical policy and Storm receipt roots.

    This verifies receipt identity, not the policy signature or full Storm
    semantics. The campaign runner must independently reverify both before any
    execution. Accordingly this state is a prepared request, not a running job.
    """

    campaign_id = str(campaign_id or "").strip()
    if not campaign_id:
        raise ValueError("campaign_id required")
    if campaign_state(store, repo, campaign_id):
        raise ValueError("campaign already exists")
    for label, expected_kind, receipt_hash in (
        ("policy", "autonomy_policy", policy_receipt_hash),
        ("storm", "storm_summary", storm_summary_receipt_hash),
    ):
        canonical = store.symbiotic_receipt(str(receipt_hash), repo=repo)
        verification = store.verify_symbiotic_receipt(repo, str(receipt_hash))
        if (
            not canonical
            or canonical.get("kind") != expected_kind
            or verification.get("valid") is not True
        ):
            raise PermissionError(f"canonical {label} receipt required")
    request = campaign_action_request(
        campaign_id,
        "campaign.prepare",
        policy_receipt_hash=policy_receipt_hash,
        storm_summary_receipt_hash=storm_summary_receipt_hash,
    )
    action = verify_control_action(
        store,
        repo,
        action_authorization,
        expected_action="campaign.prepare",
        expected_request=request,
    )
    return _append_campaign_state(
        store,
        repo,
        campaign_id=campaign_id,
        state="prepared_request",
        prior=None,
        action=action,
        policy_receipt_hash=policy_receipt_hash,
        storm_summary_receipt_hash=storm_summary_receipt_hash,
    )


def transition_campaign_control(
    store: Any,
    repo: str,
    *,
    campaign_id: str,
    action: str,
    action_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply a host lifecycle command without running model or mutation work."""

    transitions = {
        ("prepared_request", "campaign.start"): "start_requested",
        ("prepared_request", "campaign.cancel"): "cancel_requested",
        ("start_requested", "campaign.cancel"): "cancel_requested",
    }
    prior = campaign_state(store, repo, campaign_id)
    if not prior:
        raise ValueError("campaign is not prepared")
    next_state = transitions.get((str(prior.get("status") or ""), action))
    if not next_state:
        raise PermissionError("campaign transition is not allowed")
    request = campaign_action_request(
        campaign_id,
        action,
        prior_state_receipt_hash=str(prior["receipt_hash"]),
        policy_receipt_hash=str(prior.get("policy_receipt_hash") or ""),
        storm_summary_receipt_hash=str(
            prior.get("storm_summary_receipt_hash") or ""
        ),
    )
    canonical_action = verify_control_action(
        store,
        repo,
        action_authorization,
        expected_action=action,
        expected_request=request,
    )
    return _append_campaign_state(
        store,
        repo,
        campaign_id=campaign_id,
        state=next_state,
        prior=prior,
        action=canonical_action,
        policy_receipt_hash=str(prior.get("policy_receipt_hash") or ""),
        storm_summary_receipt_hash=str(
            prior.get("storm_summary_receipt_hash") or ""
        ),
    )


def issue_control_session(
    store: Any,
    repo: str,
    *,
    principal_id: str,
    principal_secret: str,
    allowed_actions: Sequence[str],
    origin: str,
    ttl_seconds: float = 600.0,
) -> dict[str, Any]:
    """Issue one host-authenticated control session and return secrets once."""

    if not _loopback_origin(origin):
        raise PermissionError("control origin must be loopback HTTP")
    actions = sorted({str(item) for item in allowed_actions})
    if not actions or not set(actions).issubset(ALLOWED_CONTROL_ACTIONS):
        raise ValueError("control action set is empty or unsupported")
    principal = store.db.execute(
        "SELECT secret_hash FROM will_principals WHERE repo=? AND principal_id=?",
        (repo, principal_id),
    ).fetchone()
    if not principal or not hmac.compare_digest(
        _secret_hash(principal_secret), str(principal["secret_hash"])
    ):
        raise PermissionError("principal secret mismatch")
    epoch = observe_current_epoch(store, repo)
    if epoch.get("verified") is not True:
        raise RuntimeError("current verified body epoch required")
    issued_at = time.time()
    expires_at = issued_at + max(30.0, min(float(ttl_seconds), 3600.0))
    control_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(24)
    material = {
        "schema_version": SESSION_SCHEMA,
        "principal_id": principal_id,
        "allowed_actions": actions,
        "origin": origin,
        "control_token_hash": _secret_hash(control_token),
        "csrf_token_hash": _secret_hash(csrf_token),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "bound_body_epoch_id": str(epoch.get("epoch_id") or ""),
        "model_may_use_control_session": False,
        **_closed_authority(),
    }
    material["control_session_hash"] = _sha(material)
    material["principal_signature"] = hmac.new(
        principal_secret.encode("utf-8"),
        material["control_session_hash"].encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    session = _session(store, repo, "issue campaign control session")
    receipt = store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "kind": "campaign_control_session",
            "status": "active",
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"campaign_control_{material['control_session_hash'][:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )
    return {**receipt, "control_token": control_token, "csrf_token": csrf_token}


def authorize_control_action(
    store: Any,
    repo: str,
    *,
    control_session_receipt_hash: str,
    control_token: str,
    csrf_token: str,
    origin: str,
    action: str,
    action_nonce: str,
    request: Mapping[str, Any],
    now: float | None = None,
) -> dict[str, Any]:
    """Consume one unique nonce and append an immutable action authorization."""

    receipt = store.symbiotic_receipt(control_session_receipt_hash, repo=repo)
    errors: list[str] = []
    if not receipt or receipt.get("kind") != "campaign_control_session":
        raise PermissionError("control session missing")
    if store.verify_symbiotic_receipt(repo, control_session_receipt_hash).get("valid") is not True:
        errors.append("control_session_invalid")
    if not _loopback_origin(origin) or origin != receipt.get("origin"):
        errors.append("control_origin_mismatch")
    if not hmac.compare_digest(_secret_hash(control_token), str(receipt.get("control_token_hash") or "")):
        errors.append("control_token_mismatch")
    if not hmac.compare_digest(_secret_hash(csrf_token), str(receipt.get("csrf_token_hash") or "")):
        errors.append("csrf_token_mismatch")
    if action not in set(receipt.get("allowed_actions") or ()):
        errors.append("control_action_not_allowed")
    checked_at = time.time() if now is None else float(now)
    if checked_at < float(receipt.get("issued_at") or 0):
        errors.append("control_session_not_yet_current")
    if checked_at > float(receipt.get("expires_at") or 0):
        errors.append("control_session_expired")
    epoch = observe_current_epoch(store, repo)
    if epoch.get("verified") is not True:
        errors.append("current_epoch_unverified")
    elif receipt.get("bound_body_epoch_id") != epoch.get("epoch_id"):
        errors.append("control_session_epoch_stale")
    revocations = store.symbiotic_receipts_by_kind(repo, "campaign_control_revocation")
    if any(item.get("control_session_receipt_hash") == control_session_receipt_hash for item in revocations):
        errors.append("control_session_revoked")
    nonce = str(action_nonce or "").strip()
    if not nonce:
        errors.append("action_nonce_missing")
    actions = store.symbiotic_receipts_by_kind(repo, "campaign_control_action")
    if any(
        item.get("control_session_receipt_hash") == control_session_receipt_hash
        and item.get("action_nonce") == nonce
        for item in actions
    ):
        errors.append("action_nonce_replayed")
    if errors:
        raise PermissionError("control action held: " + ",".join(sorted(set(errors))))
    request_hash = _sha(dict(request))
    session = _session(store, repo, f"authorize {action}")
    try:
        return store.append_symbiotic_receipt(
            repo,
            {
            "schema_version": ACTION_SCHEMA,
            "kind": "campaign_control_action",
            "status": "authorized_once",
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"control_action_{_sha([control_session_receipt_hash, nonce])[:24]}",
            "body_epoch_id": session["body_epoch_id"],
            "control_session_receipt_hash": control_session_receipt_hash,
            "principal_id": receipt["principal_id"],
            "action": action,
            "action_nonce": nonce,
            "request_hash": request_hash,
            "authorized_at": checked_at,
            "spend_expires_at": float(receipt.get("expires_at") or 0),
            "exactly_once": True,
            "host_control_authorized": True,
            **_closed_authority(),
            },
        )
    except sqlite3.IntegrityError as exc:
        if "idx_campaign_control_nonce_once" in str(exc) or "UNIQUE constraint" in str(exc):
            raise PermissionError("control action held: action_nonce_replayed") from exc
        raise


def revoke_control_session(
    store: Any,
    repo: str,
    *,
    action_authorization: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    """Revoke a control session through a canonical one-shot revoke action."""

    canonical = store.symbiotic_receipt(
        str(action_authorization.get("receipt_hash") or ""), repo=repo
    )
    if (
        not canonical
        or canonical.get("kind") != "campaign_control_action"
        or canonical.get("action") != "control.revoke"
    ):
        raise PermissionError("canonical control.revoke authorization required")
    verification = store.verify_symbiotic_receipt(repo, str(canonical["receipt_hash"]))
    if verification.get("valid") is not True:
        raise PermissionError("canonical control.revoke authorization is invalid")
    existing = next(
        (
            item
            for item in store.symbiotic_receipts_by_kind(
                repo, "campaign_control_revocation"
            )
            if item.get("action_authorization_receipt_hash")
            == canonical.get("receipt_hash")
        ),
        None,
    )
    if existing:
        return {**existing, "inserted": False, "duplicate": True}
    session = _session(store, repo, "revoke campaign control session")
    return store.append_symbiotic_receipt(
        repo,
        {
            "schema_version": REVOCATION_SCHEMA,
            "kind": "campaign_control_revocation",
            "status": "revoked",
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"control_revoke_{str(canonical['control_session_receipt_hash'])[:24]}",
            "body_epoch_id": session["body_epoch_id"],
            "control_session_receipt_hash": canonical["control_session_receipt_hash"],
            "action_authorization_receipt_hash": canonical["receipt_hash"],
            "reason": str(reason or "operator_revocation"),
            "revoked_at": time.time(),
            **_closed_authority(),
        },
    )


__all__ = [
    "ALLOWED_CONTROL_ACTIONS",
    "authorize_control_action",
    "campaign_action_request",
    "campaign_state",
    "issue_control_session",
    "prepare_campaign",
    "revoke_control_session",
    "transition_campaign_control",
    "verify_control_action",
    "verify_campaign_lifecycle",
]
