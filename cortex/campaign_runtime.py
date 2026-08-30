"""Canonical worker execution observations for governed Cortex campaigns.

Control receipts express host intent. This module records what a worker has
actually claimed and reported. It never turns a request, heartbeat, or model
output into host authority or successful integration.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

from .autonomous_improvement import verify_autonomy_policy
from .campaign_control import campaign_state
from .coding_workspace import repository_head
from .storm import verify_storm_session
from .symbiosis import open_symbiotic_session

CLAIM_SCHEMA = "cortex-campaign-worker-claim/1.0"
HEARTBEAT_SCHEMA = "cortex-campaign-worker-heartbeat/1.0"
CANCELLATION_SCHEMA = "cortex-campaign-cancellation-ack/1.0"

WORKER_STAGES = frozenset(
    {
        "claimed",
        "context",
        "model",
        "candidate",
        "verification",
        "trial",
        "tournament",
        "integration_wait",
        "cancelling",
    }
)


class CampaignCancellationRequested(RuntimeError):
    """Raised only after the worker records observing canonical cancellation."""

    def __init__(self, campaign_id: str, heartbeat: Mapping[str, Any]) -> None:
        super().__init__(f"campaign cancellation requested: {campaign_id}")
        self.campaign_id = campaign_id
        self.heartbeat = dict(heartbeat)


class CampaignSourceDrift(RuntimeError):
    """Raised when the active source head differs from the claimed source."""


class CampaignRuntimeGuard:
    """Host-owned checkpoint callback for the real improvement loop."""

    def __init__(
        self,
        store: Any,
        repo: str,
        root: str | Path,
        claim_receipt_hash: str,
        *,
        lease_seconds: float = 30.0,
    ) -> None:
        self.store = store
        self.repo = repo
        self.root = Path(root).resolve()
        self.claim = _verified_receipt(
            store, repo, claim_receipt_hash, "campaign_worker_claim"
        )
        self.claim_receipt_hash = str(claim_receipt_hash)
        self.lease_seconds = float(lease_seconds)
        existing = _campaign_receipts(
            store,
            repo,
            "campaign_worker_heartbeat",
            str(self.claim["campaign_id"]),
        )
        self.sequence = max(
            (int(item.get("heartbeat_sequence") or 0) for item in existing),
            default=0,
        )
        self.heartbeats: list[dict[str, Any]] = []

    def __call__(self, stage: str, details: Mapping[str, Any]) -> None:
        del details  # Stage timing is evidence; arbitrary callback payload is not.
        if repository_head(self.root) != self.claim.get("source_head"):
            raise CampaignSourceDrift("campaign source HEAD changed after worker claim")
        control = campaign_state(
            self.store, self.repo, str(self.claim["campaign_id"])
        )
        cancelling = bool(control and control.get("status") == "cancel_requested")
        self.sequence += 1
        heartbeat = record_worker_heartbeat(
            self.store,
            self.repo,
            claim_receipt_hash=self.claim_receipt_hash,
            sequence=self.sequence,
            stage="cancelling" if cancelling else stage,
            cancellation_observed=cancelling,
            lease_seconds=self.lease_seconds,
        )
        self.heartbeats.append(heartbeat)
        if cancelling:
            raise CampaignCancellationRequested(
                str(self.claim["campaign_id"]), heartbeat
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


def _session(store: Any, repo: str, task: str) -> dict[str, Any]:
    return open_symbiotic_session(
        store,
        repo,
        task=task,
        provider="campaign-runtime",
        model_id="none",
        capability_profile={"campaign_runtime_observation": True},
        tool_scopes=(),
        persist=True,
    )


def _verified_receipt(
    store: Any, repo: str, receipt_hash: str, kind: str
) -> dict[str, Any]:
    receipt = store.symbiotic_receipt(str(receipt_hash), repo=repo)
    if not receipt or receipt.get("kind") != kind:
        raise PermissionError(f"canonical {kind} receipt required")
    if store.verify_symbiotic_receipt(repo, str(receipt_hash)).get("valid") is not True:
        raise PermissionError(f"canonical {kind} receipt invalid")
    return receipt


def _campaign_receipts(
    store: Any, repo: str, kind: str, campaign_id: str
) -> list[dict[str, Any]]:
    return [
        item
        for item in store.symbiotic_receipts_by_kind(repo, kind)
        if item.get("campaign_id") == str(campaign_id)
    ]


def claim_campaign_worker(
    store: Any,
    repo: str,
    root: str | Path,
    *,
    campaign_id: str,
    worker_id: str,
    policy_secret: str,
    lease_seconds: float = 30.0,
    now: float | None = None,
) -> dict[str, Any]:
    """Claim one start request after independently reverifying its evidence."""

    control = campaign_state(store, repo, campaign_id)
    if not control or control.get("status") != "start_requested":
        raise PermissionError("canonical start_requested state required")
    _verified_receipt(store, repo, str(control["receipt_hash"]), "campaign_lifecycle")
    policy_hash = str(control.get("policy_receipt_hash") or "")
    policy = verify_autonomy_policy(store, repo, policy_hash, secret=policy_secret)
    if policy.get("valid") is not True:
        raise PermissionError(
            "campaign policy invalid: " + ",".join(policy.get("errors") or ())
        )
    storm_hash = str(control.get("storm_summary_receipt_hash") or "")
    storm = verify_storm_session(store, repo, storm_hash)
    if storm.get("valid") is not True:
        raise PermissionError(
            "campaign Storm invalid: " + ",".join(storm.get("errors") or ())
        )
    worker_id = str(worker_id or "").strip()
    if not worker_id:
        raise ValueError("worker_id required")
    existing = _campaign_receipts(store, repo, "campaign_worker_claim", campaign_id)
    if existing:
        canonical = existing[0]
        if (
            canonical.get("worker_id") == worker_id
            and canonical.get("start_request_receipt_hash") == control.get("receipt_hash")
        ):
            return {**canonical, "inserted": False, "duplicate": True}
        raise PermissionError("campaign already claimed by another worker")
    observed_at = time.time() if now is None else float(now)
    lease = max(5.0, min(float(lease_seconds), 300.0))
    session = _session(store, repo, f"claim campaign worker {campaign_id}")
    return store.append_symbiotic_receipt(
        repo,
        {
            "schema_version": CLAIM_SCHEMA,
            "kind": "campaign_worker_claim",
            "status": "claimed",
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"campaign_claim_{_sha([campaign_id, worker_id])[:24]}",
            "body_epoch_id": session["body_epoch_id"],
            "campaign_id": str(campaign_id),
            "worker_id": worker_id,
            "start_request_receipt_hash": control["receipt_hash"],
            "policy_receipt_hash": policy_hash,
            "storm_summary_receipt_hash": storm_hash,
            "source_head": repository_head(root),
            "claimed_at": observed_at,
            "lease_seconds": lease,
            "lease_expires_at": observed_at + lease,
            "policy_verified": True,
            "storm_verified": True,
            "execution_success": False,
            "integration_authorized": False,
            **_closed_authority(),
        },
    )


def record_worker_heartbeat(
    store: Any,
    repo: str,
    *,
    claim_receipt_hash: str,
    sequence: int,
    stage: str,
    cancellation_observed: bool = False,
    lease_seconds: float = 30.0,
    now: float | None = None,
) -> dict[str, Any]:
    """Append one monotonic, hash-linked worker liveness observation."""

    claim = _verified_receipt(
        store, repo, claim_receipt_hash, "campaign_worker_claim"
    )
    stage = str(stage or "").strip()
    if stage not in WORKER_STAGES:
        raise ValueError("unsupported worker stage")
    sequence = int(sequence)
    prior_rows = _campaign_receipts(
        store, repo, "campaign_worker_heartbeat", str(claim["campaign_id"])
    )
    prior = max(
        prior_rows,
        key=lambda item: int(item.get("heartbeat_sequence") or 0),
        default=None,
    )
    expected = 1 if prior is None else int(prior["heartbeat_sequence"]) + 1
    if sequence != expected:
        raise ValueError(f"heartbeat sequence must be {expected}")
    control = campaign_state(store, repo, str(claim["campaign_id"]))
    cancellation_requested = bool(
        control and control.get("status") == "cancel_requested"
    )
    if cancellation_observed and not cancellation_requested:
        raise PermissionError("cancellation cannot be observed before it is requested")
    observed_at = time.time() if now is None else float(now)
    lease = max(5.0, min(float(lease_seconds), 300.0))
    session = _session(
        store, repo, f"campaign heartbeat {claim['campaign_id']} #{sequence}"
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            "schema_version": HEARTBEAT_SCHEMA,
            "kind": "campaign_worker_heartbeat",
            "status": "cancelling" if cancellation_observed else "alive",
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"campaign_heartbeat_{_sha([claim_receipt_hash, sequence])[:24]}",
            "body_epoch_id": session["body_epoch_id"],
            "campaign_id": claim["campaign_id"],
            "worker_id": claim["worker_id"],
            "claim_receipt_hash": claim_receipt_hash,
            "heartbeat_sequence": sequence,
            "previous_heartbeat_receipt_hash": str(
                (prior or {}).get("receipt_hash") or ""
            ),
            "stage": stage,
            "cancellation_requested": cancellation_requested,
            "cancellation_observed": bool(cancellation_observed),
            "observed_at": observed_at,
            "lease_seconds": lease,
            "lease_expires_at": observed_at + lease,
            "execution_success": False,
            "integration_authorized": False,
            **_closed_authority(),
        },
    )


def acknowledge_campaign_cancellation(
    store: Any,
    repo: str,
    *,
    claim_receipt_hash: str,
    heartbeat_receipt_hash: str,
    exit_state: str,
    now: float | None = None,
) -> dict[str, Any]:
    """Acknowledge cooperative stop without claiming independent success."""

    claim = _verified_receipt(
        store, repo, claim_receipt_hash, "campaign_worker_claim"
    )
    heartbeat = _verified_receipt(
        store, repo, heartbeat_receipt_hash, "campaign_worker_heartbeat"
    )
    if heartbeat.get("claim_receipt_hash") != claim_receipt_hash:
        raise PermissionError("cancellation heartbeat belongs to another worker")
    if heartbeat.get("cancellation_observed") is not True:
        raise PermissionError("worker has not observed cancellation")
    control = campaign_state(store, repo, str(claim["campaign_id"]))
    if not control or control.get("status") != "cancel_requested":
        raise PermissionError("canonical cancel_requested state required")
    existing = _campaign_receipts(
        store, repo, "campaign_cancellation_ack", str(claim["campaign_id"])
    )
    if existing:
        return {**existing[0], "inserted": False, "duplicate": True}
    exit_state = str(exit_state or "").strip()
    if exit_state not in {"cooperative_stop", "budget_stop", "worker_failed"}:
        raise ValueError("unsupported worker exit state")
    session = _session(store, repo, f"acknowledge campaign stop {claim['campaign_id']}")
    return store.append_symbiotic_receipt(
        repo,
        {
            "schema_version": CANCELLATION_SCHEMA,
            "kind": "campaign_cancellation_ack",
            "status": "cancellation_acknowledged",
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"campaign_cancel_ack_{str(claim['campaign_id'])}",
            "body_epoch_id": session["body_epoch_id"],
            "campaign_id": claim["campaign_id"],
            "worker_id": claim["worker_id"],
            "claim_receipt_hash": claim_receipt_hash,
            "heartbeat_receipt_hash": heartbeat_receipt_hash,
            "cancel_request_receipt_hash": control["receipt_hash"],
            "exit_state": exit_state,
            "acknowledged_at": time.time() if now is None else float(now),
            "independent_process_exit_verified": False,
            "execution_success": False,
            "integration_authorized": False,
            **_closed_authority(),
        },
    )


def observe_campaign_runtime(
    store: Any, repo: str, campaign_id: str, *, now: float | None = None
) -> dict[str, Any]:
    """Read current campaign runtime state without appending any receipt."""

    checked_at = time.time() if now is None else float(now)
    control = campaign_state(store, repo, campaign_id)
    claims = _campaign_receipts(store, repo, "campaign_worker_claim", campaign_id)
    heartbeats = _campaign_receipts(
        store, repo, "campaign_worker_heartbeat", campaign_id
    )
    acknowledgements = _campaign_receipts(
        store, repo, "campaign_cancellation_ack", campaign_id
    )
    claim = claims[0] if claims else None
    heartbeat = max(
        heartbeats,
        key=lambda item: int(item.get("heartbeat_sequence") or 0),
        default=None,
    )
    if acknowledgements:
        state = "cancellation_acknowledged"
    elif control and control.get("status") == "cancel_requested":
        state = "cancelling"
    elif heartbeat and checked_at > float(heartbeat.get("lease_expires_at") or 0):
        state = "stale"
    elif heartbeat:
        state = "running"
    elif claim and checked_at > float(claim.get("lease_expires_at") or 0):
        state = "stale"
    elif claim:
        state = "worker_claimed"
    elif control:
        state = str(control.get("status") or "unknown")
    else:
        state = "unknown"
    return {
        "campaign_id": str(campaign_id),
        "state": state,
        "control_state_receipt_hash": str((control or {}).get("receipt_hash") or ""),
        "worker_claim_receipt_hash": str((claim or {}).get("receipt_hash") or ""),
        "heartbeat_receipt_hash": str((heartbeat or {}).get("receipt_hash") or ""),
        "cancellation_ack_receipt_hash": str(
            (acknowledgements[0] if acknowledgements else {}).get("receipt_hash") or ""
        ),
        "observed_at": checked_at,
        "read_only": True,
        "campaign_execution_success": False,
        "integration_authorized": False,
        **_closed_authority(),
    }


__all__ = [
    "WORKER_STAGES",
    "CampaignCancellationRequested",
    "CampaignRuntimeGuard",
    "CampaignSourceDrift",
    "acknowledge_campaign_cancellation",
    "claim_campaign_worker",
    "observe_campaign_runtime",
    "record_worker_heartbeat",
]
