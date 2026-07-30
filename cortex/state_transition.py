"""v6.25.1 State transitions — atomic adaptive mutations with capability + receipt."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Callable

from .capabilities import (
    CLAIM as CAP_CLAIM,
    ExecutionCapability,
    OPERATION_REGISTRY,
    require_capability,
    validate_capability,
)

SCHEMA = "cortex-state-transition/1.0"

CLAIM = (
    "State transitions enforce capability-scoped atomic adaptive writes with "
    "receipts and optional rollback snapshots. Not consciousness. Not host mutation."
)

DDL = """
CREATE TABLE IF NOT EXISTS state_transitions(
    transition_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    controller TEXT NOT NULL,
    capability_id TEXT,
    operation TEXT NOT NULL,
    write_class TEXT NOT NULL,
    pre_state_hash TEXT,
    post_state_hash TEXT,
    provenance_ids_json TEXT NOT NULL DEFAULT '[]',
    transaction_id TEXT,
    started_at REAL NOT NULL,
    completed_at REAL,
    receipt_hash TEXT,
    verification_status TEXT NOT NULL DEFAULT 'pending',
    rollback_snapshot_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_st_repo ON state_transitions(repo, started_at);

CREATE TABLE IF NOT EXISTS controller_audit_events(
    event_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    event_type TEXT NOT NULL,
    controller TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at REAL NOT NULL,
    receipt_hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cae_repo ON controller_audit_events(repo, created_at);
"""


def ensure_transition_tables(store: Any) -> None:
    store.db.executescript(DDL)
    store.db.commit()


def logical_state_digest(store: Any, repo: str) -> str:
    """Canonical digest of adaptive tables for a repo."""
    parts: list[str] = []
    queries = [
        ("ranker_models", "SELECT model_id, weights_json, bias, train_count FROM ranker_models WHERE repo=? ORDER BY model_id"),
        ("neural_synapses", "SELECT synapse_id, weight, relation FROM neural_synapses WHERE repo=? ORDER BY synapse_id"),
        ("lineage_artifacts", "SELECT artifact_id, invalidated FROM lineage_artifacts WHERE repo=? ORDER BY artifact_id"),
        ("quarantine_envelopes", "SELECT envelope_id, active FROM quarantine_envelopes WHERE repo=? ORDER BY envelope_id"),
        ("memory_wounds", "SELECT wound_id, resolved FROM memory_wounds WHERE repo=? ORDER BY wound_id"),
        ("ranker_training_events", "SELECT event_id, excluded FROM ranker_training_events WHERE repo=? ORDER BY event_id"),
    ]
    for name, sql in queries:
        try:
            rows = store.db.execute(sql, (repo,)).fetchall()
            parts.append(name + ":" + json.dumps([dict(r) for r in rows], sort_keys=True, default=str))
        except Exception:
            parts.append(name + ":missing")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


@dataclass
class StateTransition:
    transition_id: str
    repo: str
    controller: str
    capability_id: str
    operation: str
    write_class: str
    pre_state_hash: str
    provenance_ids: list[str]
    transaction_id: str
    started_at: float
    completed_at: float | None = None
    post_state_hash: str | None = None
    receipt_hash: str | None = None
    verification_status: str = "pending"
    rollback_snapshot_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["claim_boundary"] = CLAIM
        return d


def append_controller_audit(
    store: Any,
    repo: str,
    event_type: str,
    *,
    controller: str | None = None,
    payload: dict[str, Any] | None = None,
    conn: Any = None,
    commit: bool = True,
) -> dict[str, Any]:
    """Append-only baseline-safe audit — does not strengthen coactivation."""
    ensure_transition_tables(store)
    now = time.time()
    eid = "cae_" + hashlib.sha256(f"{repo}|{event_type}|{now}|{uuid.uuid4().hex}".encode()).hexdigest()[:18]
    body = payload or {}
    rh = hashlib.sha256(
        json.dumps({"id": eid, "type": event_type, "body": body}, sort_keys=True, default=str).encode()
    ).hexdigest()
    db = conn or store.db
    db.execute(
        """
        INSERT INTO controller_audit_events(event_id, repo, event_type, controller, payload_json, created_at, receipt_hash)
        VALUES(?,?,?,?,?,?,?)
        """,
        (eid, repo, event_type, controller, json.dumps(body, default=str), now, rh),
    )
    if commit and conn is None:
        store.db.commit()
    return {"event_id": eid, "event_type": event_type, "receipt_hash": rh}


def run_transition(
    store: Any,
    *,
    repo: str,
    capability: ExecutionCapability | None,
    operation: str,
    mutate: Callable[[Any], Any],
    provenance_ids: list[str] | None = None,
    require_snapshot: bool = False,
    snapshot_id: str | None = None,
) -> dict[str, Any]:
    """
    Execute a capability-gated mutation in one transaction.
    mutate(conn) performs writes using the provided connection; must not commit.
    """
    ensure_transition_tables(store)
    decision = validate_capability(capability, repo=repo, operation=operation)
    if not decision.allowed:
        return {
            "ok": False,
            "error": decision.reason,
            "decision": decision.to_dict(),
            "claim_boundary": CLAIM,
        }
    assert capability is not None
    write_class = OPERATION_REGISTRY[operation]
    tid = "st_" + uuid.uuid4().hex[:16]
    tx = "tx_" + uuid.uuid4().hex[:12]
    pre = logical_state_digest(store, repo)
    started = time.time()
    st = StateTransition(
        transition_id=tid,
        repo=repo,
        controller=capability.controller,
        capability_id=capability.capability_id,
        operation=operation,
        write_class=write_class,
        pre_state_hash=pre,
        provenance_ids=list(provenance_ids or []),
        transaction_id=tx,
        started_at=started,
        rollback_snapshot_id=snapshot_id,
    )
    result: Any = None
    try:
        store.db.execute("BEGIN IMMEDIATE")
        result = mutate(store.db)
        post = logical_state_digest(store, repo)
        completed = time.time()
        receipt_body = {
            "transition_id": tid,
            "pre": pre,
            "post": post,
            "operation": operation,
            "capability_id": capability.capability_id,
        }
        rh = hashlib.sha256(json.dumps(receipt_body, sort_keys=True).encode()).hexdigest()
        store.db.execute(
            """
            INSERT INTO state_transitions(
              transition_id, repo, controller, capability_id, operation, write_class,
              pre_state_hash, post_state_hash, provenance_ids_json, transaction_id,
              started_at, completed_at, receipt_hash, verification_status, rollback_snapshot_id
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                tid,
                repo,
                capability.controller,
                capability.capability_id,
                operation,
                write_class,
                pre,
                post,
                json.dumps(st.provenance_ids),
                tx,
                started,
                completed,
                rh,
                "committed",
                snapshot_id,
            ),
        )
        store.db.commit()
        st.completed_at = completed
        st.post_state_hash = post
        st.receipt_hash = rh
        st.verification_status = "committed"
        return {
            "ok": True,
            "transition": st.to_dict(),
            "result": result,
            "claim_boundary": CLAIM,
        }
    except Exception as exc:
        try:
            store.db.rollback()
        except Exception:
            pass
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "transition_id": tid,
            "pre_state_hash": pre,
            "claim_boundary": CLAIM,
        }
