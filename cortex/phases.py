"""v7.0 Runtime phase machine — legal phase transitions bound to body epochs."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, FrozenSet

from .epoch import ensure_current_epoch

SCHEMA = "cortex-runtime-phases/1.0"
GLYPH = "⟳"

CLAIM = (
    "Runtime phases constrain which plane operations may run under a body epoch. "
    "Illegal transitions are denied. Not consciousness."
)

# Legal phases
QUIESCENT = "QUIESCENT"
OBSERVE = "OBSERVE"
INDEX = "INDEX"
EVIDENCE_FREEZE = "EVIDENCE_FREEZE"
ADAPT = "ADAPT"
CONSOLIDATE = "CONSOLIDATE"
WITNESS = "WITNESS"
PROMOTE = "PROMOTE"
FEDERATE = "FEDERATE"
QUARANTINE = "QUARANTINE"
REPAIR = "REPAIR"
VERIFY_REPAIR = "VERIFY_REPAIR"
ROLLBACK = "ROLLBACK"

ALL_PHASES: FrozenSet[str] = frozenset(
    {
        QUIESCENT,
        OBSERVE,
        INDEX,
        EVIDENCE_FREEZE,
        ADAPT,
        CONSOLIDATE,
        WITNESS,
        PROMOTE,
        FEDERATE,
        QUARANTINE,
        REPAIR,
        VERIFY_REPAIR,
        ROLLBACK,
    }
)

# Directed legal transitions
LEGAL_TRANSITIONS: dict[str, FrozenSet[str]] = {
    QUIESCENT: frozenset({OBSERVE, INDEX, QUARANTINE, REPAIR, WITNESS}),
    OBSERVE: frozenset({QUIESCENT, INDEX, EVIDENCE_FREEZE, ADAPT, QUARANTINE, WITNESS}),
    INDEX: frozenset({OBSERVE, EVIDENCE_FREEZE, QUIESCENT}),
    EVIDENCE_FREEZE: frozenset({OBSERVE, ADAPT, WITNESS, QUIESCENT}),
    ADAPT: frozenset({CONSOLIDATE, OBSERVE, QUARANTINE, REPAIR, QUIESCENT}),
    CONSOLIDATE: frozenset({WITNESS, PROMOTE, OBSERVE, QUIESCENT}),
    WITNESS: frozenset({PROMOTE, OBSERVE, QUIESCENT, FEDERATE}),
    PROMOTE: frozenset({FEDERATE, QUIESCENT, OBSERVE}),
    FEDERATE: frozenset({QUIESCENT, OBSERVE}),
    QUARANTINE: frozenset({REPAIR, OBSERVE, QUIESCENT}),
    REPAIR: frozenset({VERIFY_REPAIR, ROLLBACK, QUIESCENT}),
    VERIFY_REPAIR: frozenset({QUIESCENT, OBSERVE, ROLLBACK, PROMOTE}),
    ROLLBACK: frozenset({QUIESCENT, OBSERVE, REPAIR}),
}

# Operations allowed in each phase (capability still required)
PHASE_OPERATIONS: dict[str, FrozenSet[str]] = {
    QUIESCENT: frozenset({"audit_append", "read_only_query", "controller_resolved"}),
    OBSERVE: frozenset(
        {
            "audit_append",
            "read_only_query",
            "evidence_kernel_queried",
            "certificate_observed",
            "manifest_observed",
            "activation_completed",
        }
    ),
    INDEX: frozenset({"explicit_index", "manual_refresh", "explicit_verify", "audit_append"}),
    EVIDENCE_FREEZE: frozenset({"evidence_kernel_queried", "audit_append", "read_only_query"}),
    ADAPT: frozenset(
        {
            "ranker_train",
            "structure_invent",
            "fusion_open",
            "fusion_tick",
            "spectral_promote",
            "foreign_emerge",
            "connect_pass_write",
            "self_org",
            "session_begin",
            "audit_append",
        }
    ),
    CONSOLIDATE: frozenset({"auto_distill", "learned_summary", "session_end", "audit_append"}),
    WITNESS: frozenset({"audit_append", "read_only_query", "evidence_kernel_queried"}),
    PROMOTE: frozenset({"shadow_calibration", "audit_append", "ranker_rebuild"}),
    FEDERATE: frozenset({"audit_append", "read_only_query"}),
    QUARANTINE: frozenset({"repair_quarantine", "repair_invalidate", "audit_append"}),
    REPAIR: frozenset(
        {
            "repair_snapshot_create",
            "repair_synapse_remove",
            "repair_ranker_rebuild",
            "repair_calibration_invalidate",
            "repair_fusion_reset",
            "repair_reconstruct",
            "audit_append",
        }
    ),
    VERIFY_REPAIR: frozenset({"repair_verify", "audit_append", "read_only_query"}),
    ROLLBACK: frozenset({"repair_rollback", "audit_append"}),
}

DDL = """
CREATE TABLE IF NOT EXISTS runtime_phase_state(
    repo TEXT PRIMARY KEY,
    epoch_id TEXT NOT NULL,
    phase TEXT NOT NULL,
    entered_at REAL NOT NULL,
    previous_phase TEXT,
    receipt_hash TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
"""


@dataclass
class RuntimePhaseState:
    repo: str
    epoch_id: str
    phase: str
    entered_at: float
    previous_phase: str | None = None
    receipt_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA
        d["glyph"] = GLYPH
        d["claim_boundary"] = CLAIM
        return d


def ensure_phase_tables(store: Any) -> None:
    store.db.executescript(DDL)
    store.db.commit()


def current_phase(store: Any, repo: str) -> RuntimePhaseState:
    ensure_phase_tables(store)
    row = store.db.execute(
        "SELECT * FROM runtime_phase_state WHERE repo=?", (repo,)
    ).fetchone()
    if not row:
        ep = ensure_current_epoch(store, repo, reason="phase_init")
        st = RuntimePhaseState(
            repo=repo,
            epoch_id=ep.epoch_id,
            phase=QUIESCENT,
            entered_at=time.time(),
            previous_phase=None,
        )
        _persist(store, st)
        return st
    import json

    meta = {}
    try:
        meta = json.loads(row["metadata_json"] or "{}")
    except Exception:
        meta = {}
    return RuntimePhaseState(
        repo=str(row["repo"]),
        epoch_id=str(row["epoch_id"]),
        phase=str(row["phase"]),
        entered_at=float(row["entered_at"] or 0),
        previous_phase=row["previous_phase"],
        receipt_hash=row["receipt_hash"],
        metadata=meta,
    )


def _persist(store: Any, st: RuntimePhaseState) -> None:
    import hashlib
    import json

    rh = hashlib.sha256(
        json.dumps(
            {"repo": st.repo, "epoch": st.epoch_id, "phase": st.phase, "at": st.entered_at},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    st.receipt_hash = rh
    store.db.execute(
        """
        INSERT OR REPLACE INTO runtime_phase_state(
          repo, epoch_id, phase, entered_at, previous_phase, receipt_hash, metadata_json
        ) VALUES(?,?,?,?,?,?,?)
        """,
        (
            st.repo,
            st.epoch_id,
            st.phase,
            st.entered_at,
            st.previous_phase,
            rh,
            json.dumps(st.metadata),
        ),
    )
    store.db.commit()


def can_transition(from_phase: str, to_phase: str) -> bool:
    if to_phase not in ALL_PHASES:
        return False
    allowed = LEGAL_TRANSITIONS.get(from_phase, frozenset())
    return to_phase in allowed


def transition_phase(
    store: Any,
    repo: str,
    to_phase: str,
    *,
    reason: str = "",
    force_epoch_refresh: bool = False,
) -> dict[str, Any]:
    """Attempt legal phase transition under current body epoch."""
    to_phase = (to_phase or "").upper().strip()
    if to_phase not in ALL_PHASES:
        return {"ok": False, "error": "unknown_phase", "phase": to_phase}
    cur = current_phase(store, repo)
    if force_epoch_refresh:
        ep = ensure_current_epoch(store, repo, reason=f"phase:{to_phase}")
    else:
        ep = ensure_current_epoch(store, repo, reason="phase_touch")
    if cur.epoch_id != ep.epoch_id:
        # epoch drifted — rebind quiescent then continue if legal from QUIESCENT
        cur = RuntimePhaseState(
            repo=repo,
            epoch_id=ep.epoch_id,
            phase=QUIESCENT,
            entered_at=time.time(),
            previous_phase=cur.phase,
            metadata={"epoch_rebind": True, "reason": reason},
        )
        _persist(store, cur)
    if cur.phase == to_phase:
        return {"ok": True, "phase": cur.to_dict(), "unchanged": True}
    if not can_transition(cur.phase, to_phase):
        return {
            "ok": False,
            "error": "illegal_phase_transition",
            "from": cur.phase,
            "to": to_phase,
            "allowed": sorted(LEGAL_TRANSITIONS.get(cur.phase, frozenset())),
            "claim_boundary": CLAIM,
        }
    nxt = RuntimePhaseState(
        repo=repo,
        epoch_id=ep.epoch_id,
        phase=to_phase,
        entered_at=time.time(),
        previous_phase=cur.phase,
        metadata={"reason": reason},
    )
    _persist(store, nxt)
    return {"ok": True, "phase": nxt.to_dict(), "claim_boundary": CLAIM}


def phase_allows_operation(phase: str, operation: str) -> bool:
    ops = PHASE_OPERATIONS.get(phase, frozenset())
    # audit always soft-allowed in any phase for constitutional continuity
    if operation in {"audit_append", "controller_resolved", "activation_completed", "activation_failed"}:
        return True
    return operation in ops


def assert_phase_operation(store: Any, repo: str, operation: str) -> None:
    st = current_phase(store, repo)
    if not phase_allows_operation(st.phase, operation):
        raise PermissionError(
            f"phase {st.phase} forbids operation {operation} (epoch={st.epoch_id})"
        )


def phase_report(store: Any, repo: str) -> dict[str, Any]:
    st = current_phase(store, repo)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "state": st.to_dict(),
        "legal_next": sorted(LEGAL_TRANSITIONS.get(st.phase, frozenset())),
        "allowed_operations": sorted(PHASE_OPERATIONS.get(st.phase, frozenset())),
        "claim_boundary": CLAIM,
    }
