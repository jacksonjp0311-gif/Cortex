"""Event-sourced epistemic state and bounded context compilation.

This module does not decide real-world truth and does not authorize action.
It deterministically folds immutable, bitemporal evidence events into a
four-valued support state, then emits the smallest evidence-bearing context
that preserves that state under the declared Boolean support semantics.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA = "cortex-epistemic-event/1.0"
PROJECTION_SCHEMA = "cortex-epistemic-projection/1.0"
CONTEXT_SCHEMA = "cortex-action-sufficient-context/1.0"
DEBT_SCHEMA = "cortex-continuation-debt/1.0"
ZERO_HASH = "0" * 64
POLARITIES = frozenset({"support", "oppose", "retract"})
TRUTH_STATES = frozenset({"TRUE", "FALSE", "NEITHER", "BOTH"})
CLAIM_BOUNDARY = (
    "Epistemic events record evidence support, not reality itself. Projection "
    "does not grant execution, mutation, memory admission, or policy authority."
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False, default=str,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _repository_id(store: Any, repo: str) -> str:
    row = store.repo(str(repo))
    if row is None:
        raise ValueError(f"repository is not attached: {repo}")
    return str(row["repository_id"])


def ensure_epistemic_tables(store: Any) -> None:
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS epistemic_events(
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            event_hash TEXT PRIMARY KEY CHECK(length(event_hash) = 64),
            previous_event_hash TEXT NOT NULL CHECK(length(previous_event_hash) = 64),
            claim_id TEXT NOT NULL,
            polarity TEXT NOT NULL,
            valid_from REAL NOT NULL,
            valid_to REAL,
            system_time REAL NOT NULL,
            receipt_json TEXT NOT NULL,
            UNIQUE(repository_id, sequence)
        );
        CREATE INDEX IF NOT EXISTS idx_epistemic_claim
        ON epistemic_events(repository_id, claim_id, system_time);
        CREATE TRIGGER IF NOT EXISTS epistemic_events_no_update
        BEFORE UPDATE ON epistemic_events BEGIN
            SELECT RAISE(ABORT, 'epistemic events are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS epistemic_events_no_delete
        BEFORE DELETE ON epistemic_events BEGIN
            SELECT RAISE(ABORT, 'epistemic events are immutable');
        END;
        """
    )


def append_epistemic_event(
    store: Any,
    repo: str,
    *,
    claim_id: str,
    claim_text: str,
    polarity: str,
    evidence_receipt_hash: str,
    source_lineage_hash: str,
    valid_from: float,
    valid_to: float | None = None,
    observed_at: float | None = None,
    retracts_event_hash: str = "",
) -> dict[str, Any]:
    """Append one immutable evidence event to the repository chain."""
    polarity = str(polarity)
    if polarity not in POLARITIES:
        raise ValueError(f"invalid epistemic polarity: {polarity}")
    if not str(claim_id).strip() or not str(claim_text).strip():
        raise ValueError("claim_id and claim_text are required")
    for label, value in (
        ("evidence_receipt_hash", evidence_receipt_hash),
        ("source_lineage_hash", source_lineage_hash),
    ):
        if len(str(value)) != 64:
            raise ValueError(f"{label} must be a canonical hash")
    if polarity == "retract" and len(str(retracts_event_hash)) != 64:
        raise ValueError("retraction must bind the exact target event hash")
    if valid_to is not None and float(valid_to) < float(valid_from):
        raise ValueError("valid_to cannot precede valid_from")

    ensure_epistemic_tables(store)
    repository_id = _repository_id(store, repo)
    system_time = time.time()
    with store.transaction() as conn:
        tip = conn.execute(
            """SELECT sequence, event_hash FROM epistemic_events
               WHERE repository_id=? ORDER BY sequence DESC LIMIT 1""",
            (repository_id,),
        ).fetchone()
        sequence = int(tip["sequence"] if tip else 0) + 1
        previous = str(tip["event_hash"] if tip else ZERO_HASH)
        body = {
            "schema_version": SCHEMA,
            "version": __version__,
            "kind": "epistemic_evidence_event",
            "repo": str(repo),
            "repository_id": repository_id,
            "sequence": sequence,
            "previous_event_hash": previous,
            "claim_id": str(claim_id),
            "claim_text": str(claim_text),
            "polarity": polarity,
            "evidence_receipt_hash": str(evidence_receipt_hash),
            "source_lineage_hash": str(source_lineage_hash),
            "valid_time": {"from": float(valid_from), "to": valid_to},
            "observed_at": float(observed_at or system_time),
            "system_time": system_time,
            "retracts_event_hash": str(retracts_event_hash or ""),
            "advisory_only": True,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
            "claim_boundary": CLAIM_BOUNDARY,
        }
        event_hash = _sha(body)
        receipt = {**body, "event_hash": event_hash}
        conn.execute(
            """INSERT INTO epistemic_events(
                 repository_id, repo, sequence, event_hash, previous_event_hash,
                 claim_id, polarity, valid_from, valid_to, system_time, receipt_json
               ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                repository_id, str(repo), sequence, event_hash, previous,
                str(claim_id), polarity, float(valid_from), valid_to,
                system_time, _canonical(receipt),
            ),
        )
    return receipt


def list_epistemic_events(store: Any, repo: str) -> list[dict[str, Any]]:
    ensure_epistemic_tables(store)
    repository_id = _repository_id(store, repo)
    rows = store.db.execute(
        """SELECT receipt_json FROM epistemic_events
           WHERE repository_id=? ORDER BY sequence ASC""",
        (repository_id,),
    ).fetchall()
    return [json.loads(str(row["receipt_json"])) for row in rows]


def verify_epistemic_history(store: Any, repo: str) -> dict[str, Any]:
    events = list_epistemic_events(store, repo)
    errors: list[str] = []
    previous = ZERO_HASH
    for expected_sequence, event in enumerate(events, 1):
        if int(event.get("sequence") or 0) != expected_sequence:
            errors.append(f"sequence_{expected_sequence}_invalid")
        if str(event.get("previous_event_hash") or "") != previous:
            errors.append(f"sequence_{expected_sequence}_previous_hash_invalid")
        material = {key: value for key, value in event.items() if key != "event_hash"}
        if _sha(material) != str(event.get("event_hash") or ""):
            errors.append(f"sequence_{expected_sequence}_event_hash_invalid")
        previous = str(event.get("event_hash") or "")
    return {
        "valid": not errors,
        "errors": errors,
        "event_count": len(events),
        "tip_hash": previous,
        "history_primary": True,
        "state_derived": True,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
    }


def _active_events(
    events: Sequence[Mapping[str, Any]], *, valid_at: float, known_at: float
) -> list[dict[str, Any]]:
    visible = [
        dict(event) for event in events
        if float(event.get("system_time") or 0.0) <= known_at
    ]
    retracted = {
        str(event.get("retracts_event_hash") or "")
        for event in visible if event.get("polarity") == "retract"
    }
    active: list[dict[str, Any]] = []
    for event in visible:
        if event.get("polarity") == "retract" or event.get("event_hash") in retracted:
            continue
        interval = event.get("valid_time") if isinstance(event.get("valid_time"), Mapping) else {}
        start = float(interval.get("from") or 0.0)
        end = interval.get("to")
        if start <= valid_at and (end is None or valid_at <= float(end)):
            active.append(event)
    return active


def project_epistemic_state(
    events: Sequence[Mapping[str, Any]],
    *,
    valid_at: float | None = None,
    known_at: float | None = None,
) -> dict[str, Any]:
    """Fold history into Belnap-Dunn style support states."""
    valid_at = float(valid_at or time.time())
    known_at = float(known_at or time.time())
    active = _active_events(events, valid_at=valid_at, known_at=known_at)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for event in active:
        grouped.setdefault(str(event.get("claim_id") or ""), []).append(event)
    claims: list[dict[str, Any]] = []
    for claim_id in sorted(grouped):
        rows = grouped[claim_id]
        supports = [row for row in rows if row.get("polarity") == "support"]
        opposes = [row for row in rows if row.get("polarity") == "oppose"]
        state = (
            "BOTH" if supports and opposes else
            "TRUE" if supports else
            "FALSE" if opposes else "NEITHER"
        )
        claims.append({
            "claim_id": claim_id,
            "claim_text": str(rows[0].get("claim_text") or ""),
            "truth_state": state,
            "support_bits": [int(bool(supports)), int(bool(opposes))],
            "support_event_hashes": [row["event_hash"] for row in supports],
            "opposition_event_hashes": [row["event_hash"] for row in opposes],
            "source_lineage_count": len({str(row.get("source_lineage_hash")) for row in rows}),
            "source_independence": "UNTESTED",
        })
    material = {
        "schema_version": PROJECTION_SCHEMA,
        "valid_at": valid_at,
        "known_at": known_at,
        "claims": claims,
        "event_count_considered": len(active),
        "history_primary": True,
        "state_derived": True,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return {**material, "projection_hash": _sha(material)}


def compile_action_sufficient_context(
    events: Sequence[Mapping[str, Any]],
    *,
    required_claim_ids: Sequence[str],
    valid_at: float | None = None,
    known_at: float | None = None,
    character_budget: int = 4000,
) -> dict[str, Any]:
    """Compile a minimal state-preserving epistemic context.

    Under the kernel's two-bit presence semantics one support event and one
    opposition event are sufficient to preserve each requested truth state.
    All relevant conflicts remain visible. Authority is intentionally left to
    a separate canonical gate.
    """
    valid_at = float(valid_at or time.time())
    known_at = float(known_at or time.time())
    active = _active_events(events, valid_at=valid_at, known_at=known_at)
    selected: list[dict[str, Any]] = []
    missing: list[str] = []
    used = 0
    for claim_id in dict.fromkeys(str(item) for item in required_claim_ids):
        rows = [row for row in active if str(row.get("claim_id") or "") == claim_id]
        support = next((row for row in rows if row.get("polarity") == "support"), None)
        oppose = next((row for row in rows if row.get("polarity") == "oppose"), None)
        representatives = [row for row in (support, oppose) if row is not None]
        if not representatives:
            missing.append(claim_id)
            continue
        for row in representatives:
            item = {
                "claim_id": claim_id,
                "claim_text": str(row.get("claim_text") or ""),
                "polarity": row.get("polarity"),
                "event_hash": row.get("event_hash"),
                "evidence_receipt_hash": row.get("evidence_receipt_hash"),
                "source_lineage_hash": row.get("source_lineage_hash"),
            }
            cost = len(_canonical(item))
            if used + cost > max(0, int(character_budget)):
                missing.append(claim_id)
                break
            selected.append(item)
            used += cost
    projection = project_epistemic_state(events, valid_at=valid_at, known_at=known_at)
    requested = [
        claim for claim in projection["claims"]
        if claim["claim_id"] in set(str(item) for item in required_claim_ids)
    ]
    material = {
        "schema_version": CONTEXT_SCHEMA,
        "projection_hash": projection["projection_hash"],
        "required_claim_ids": list(dict.fromkeys(str(item) for item in required_claim_ids)),
        "claims": requested,
        "evidence": selected,
        "character_budget": int(character_budget),
        "characters_used": used,
        "missing_claim_ids": sorted(set(missing)),
        "state_preservation": "PASS" if not missing else "UNKNOWN",
        "minimality_scope": "exact_for_two_bit_presence_semantics",
        "authority_state": "SEPARATE_CANONICAL_GATE_REQUIRED",
        "action_authorized": False,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return {**material, "context_hash": _sha(material)}


def update_continuation_debt(
    previous_debt: float,
    *,
    uncertainty: float,
    conflict: float,
    drift: float,
    staleness: float,
    verification: float,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Apply an explicit host policy; no expiration/control law is invented."""
    required = {"rho", "alpha", "beta", "gamma", "eta", "delta", "reanchor", "quarantine"}
    missing = sorted(required - set(policy))
    if missing:
        return {
            "schema_version": DEBT_SCHEMA,
            "state": "UNKNOWN",
            "errors": [f"policy_{item}_missing" for item in missing],
            "advisory_only": True,
            "action_authorized": False,
        }
    debt = (
        float(policy["rho"]) * float(previous_debt)
        + float(policy["alpha"]) * float(uncertainty)
        + float(policy["beta"]) * float(conflict)
        + float(policy["gamma"]) * float(drift)
        + float(policy["eta"]) * float(staleness)
        - float(policy["delta"]) * float(verification)
    )
    debt = max(0.0, debt)
    regime = (
        "QUARANTINE" if debt >= float(policy["quarantine"]) else
        "REANCHOR" if debt >= float(policy["reanchor"]) else "CONTINUE"
    )
    return {
        "schema_version": DEBT_SCHEMA,
        "state": "PASS",
        "previous_debt": float(previous_debt),
        "continuation_debt": debt,
        "regime": regime,
        "policy_hash": _sha(dict(policy)),
        "advisory_only": True,
        "action_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
    }


__all__ = [
    "CLAIM_BOUNDARY", "CONTEXT_SCHEMA", "DEBT_SCHEMA", "POLARITIES",
    "PROJECTION_SCHEMA", "SCHEMA", "TRUTH_STATES",
    "append_epistemic_event", "compile_action_sufficient_context",
    "ensure_epistemic_tables", "list_epistemic_events",
    "project_epistemic_state", "update_continuation_debt",
    "verify_epistemic_history",
]
