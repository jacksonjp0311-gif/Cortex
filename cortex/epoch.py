"""v7.0 Body Epoch — deterministic identity of evidence+constitution+adaptive roots.

Routine retrieval does not create epochs. Epoch transitions are explicit and receipted.
Timestamps are metadata only — not identity material.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from . import __version__
from .state_transition import logical_state_digest

SCHEMA = "cortex-body-epoch/1.0"
GLYPH = "⏱"

CLAIM = (
    "Body epochs identify compatible runtime continuity: evidence, constitution, "
    "schema, and adaptive roots. Not consciousness. Not host mutation authority."
)

DDL = """
CREATE TABLE IF NOT EXISTS body_epochs(
    epoch_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    repository_id TEXT,
    manifest_hash TEXT,
    certificate_hash TEXT,
    schema_hash TEXT,
    cortex_version TEXT,
    cortex_commit TEXT,
    constitutional_config_hash TEXT,
    evidence_root_hash TEXT,
    adaptive_root_hash TEXT,
    lineage_root_hash TEXT,
    created_at REAL NOT NULL,
    parent_epoch_id TEXT,
    transition_reason TEXT,
    receipt_hash TEXT NOT NULL,
    sealed INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_body_epochs_repo ON body_epochs(repo, created_at);
"""

# Ops that may survive epoch transition (read/audit only)
EPOCH_STABLE_OPS = frozenset(
    {
        "audit_append",
        "controller_resolved",
        "evidence_kernel_queried",
        "certificate_observed",
        "manifest_observed",
        "activation_completed",
        "activation_failed",
        "read_only_query",
    }
)


@dataclass(frozen=True)
class EpochComponent:
    name: str
    hash: str


@dataclass(frozen=True)
class BodyEpoch:
    epoch_id: str
    repo: str
    repository_id: str
    manifest_hash: str
    certificate_hash: str
    schema_hash: str
    cortex_version: str
    cortex_commit: str
    constitutional_config_hash: str
    evidence_root_hash: str
    adaptive_root_hash: str
    lineage_root_hash: str
    created_at: float
    parent_epoch_id: str | None
    transition_reason: str
    receipt_hash: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA
        d["glyph"] = GLYPH
        d["claim_boundary"] = CLAIM
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "BodyEpoch":
        return BodyEpoch(
            epoch_id=str(d["epoch_id"]),
            repo=str(d["repo"]),
            repository_id=str(d.get("repository_id") or ""),
            manifest_hash=str(d.get("manifest_hash") or ""),
            certificate_hash=str(d.get("certificate_hash") or ""),
            schema_hash=str(d.get("schema_hash") or ""),
            cortex_version=str(d.get("cortex_version") or ""),
            cortex_commit=str(d.get("cortex_commit") or ""),
            constitutional_config_hash=str(d.get("constitutional_config_hash") or ""),
            evidence_root_hash=str(d.get("evidence_root_hash") or ""),
            adaptive_root_hash=str(d.get("adaptive_root_hash") or ""),
            lineage_root_hash=str(d.get("lineage_root_hash") or ""),
            created_at=float(d.get("created_at") or 0),
            parent_epoch_id=d.get("parent_epoch_id"),
            transition_reason=str(d.get("transition_reason") or ""),
            receipt_hash=str(d.get("receipt_hash") or ""),
        )


@dataclass
class EpochCompatibility:
    compatible: bool
    reason: str
    left_epoch_id: str
    right_epoch_id: str
    mismatches: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EpochReceipt:
    """Deterministic continuation receipt for an epoch seal or verify."""

    receipt_hash: str
    epoch_id: str
    repo: str
    transition_reason: str
    parent_epoch_id: str | None
    sealed: bool
    components: tuple[EpochComponent, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA
        d["claim_boundary"] = CLAIM
        return d


@dataclass
class EpochTransition:
    """Open or sealed epoch transition record (not identity material)."""

    repo: str
    reason: str
    parent_epoch_id: str | None
    proposed_epoch_id: str
    sealed_epoch_id: str | None = None
    changed: bool = False
    sealed: bool = False
    opened_at: float = 0.0
    sealed_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA
        d["claim_boundary"] = CLAIM
        return d


def ensure_epoch_tables(store: Any) -> None:
    store.db.executescript(DDL)
    store.db.commit()


def _sha(material: str) -> str:
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _evidence_root(store: Any, repo: str) -> str:
    try:
        rows = store.db.execute(
            """
            SELECT path, content_hash FROM memories
            WHERE repo=? AND kind NOT LIKE '%discovery%' AND kind NOT LIKE '%card%'
            ORDER BY path, chunk_index, content_hash
            LIMIT 5000
            """,
            (repo,),
        ).fetchall()
        mat = json.dumps([dict(r) for r in rows], sort_keys=True, default=str)
        return _sha(mat)
    except Exception:
        return _sha(f"evidence_missing|{repo}")


def _lineage_root(store: Any, repo: str) -> str:
    try:
        rows = store.db.execute(
            """
            SELECT artifact_id, artifact_type, invalidated, receipt_hash
            FROM lineage_artifacts WHERE repo=? ORDER BY artifact_id
            """,
            (repo,),
        ).fetchall()
        return _sha(json.dumps([dict(r) for r in rows], sort_keys=True, default=str))
    except Exception:
        return _sha(f"lineage_missing|{repo}")


def _certificate_hash(store: Any, repo: str) -> str:
    try:
        row = store.latest_bootstrap(repo)
        if not row:
            return _sha("no_certificate")
        cert = row["certificate"] or "{}"
        return _sha(str(cert))
    except Exception:
        return _sha("certificate_error")


def _constitutional_config_hash() -> str:
    # Stable digest of constitutional policy surface
    from .capabilities import OPERATION_REGISTRY, REPAIR_ALLOWLIST

    mat = {
        "ops": sorted(OPERATION_REGISTRY.keys()),
        "repair": sorted(REPAIR_ALLOWLIST),
        "version": __version__,
        "schema": SCHEMA,
    }
    return _sha(json.dumps(mat, sort_keys=True))


def _schema_hash(store: Any) -> str:
    try:
        tables = store.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        names = [str(r["name"]) for r in tables]
        return _sha(json.dumps(names))
    except Exception:
        return _sha("schema_unknown")


def compute_body_epoch(
    store: Any,
    repo: str,
    *,
    cortex_commit: str = "",
    parent_epoch_id: str | None = None,
    transition_reason: str = "observe",
    created_at: float | None = None,
) -> BodyEpoch:
    """Compute deterministic BodyEpoch (timestamps excluded from epoch_id material)."""
    ensure_epoch_tables(store)
    row = store.repo(repo)
    repository_id = str(row["repository_id"] or "") if row else ""
    manifest_hash = str(row["manifest_hash"] or "") if row else ""
    certificate_hash = _certificate_hash(store, repo)
    schema_hash = _schema_hash(store)
    constitutional_config_hash = _constitutional_config_hash()
    evidence_root_hash = _evidence_root(store, repo)
    adaptive_root_hash = logical_state_digest(store, repo)
    lineage_root_hash = _lineage_root(store, repo)
    cortex_version = __version__
    commit = cortex_commit or __version__

    # Identity material — NO timestamps
    identity = {
        "repo": repo,
        "repository_id": repository_id,
        "manifest_hash": manifest_hash,
        "certificate_hash": certificate_hash,
        "schema_hash": schema_hash,
        "cortex_version": cortex_version,
        "cortex_commit": commit,
        "constitutional_config_hash": constitutional_config_hash,
        "evidence_root_hash": evidence_root_hash,
        "adaptive_root_hash": adaptive_root_hash,
        "lineage_root_hash": lineage_root_hash,
    }
    epoch_id = _sha(json.dumps(identity, sort_keys=True))
    receipt = _sha(json.dumps({**identity, "parent": parent_epoch_id, "reason": transition_reason}, sort_keys=True))
    return BodyEpoch(
        epoch_id=epoch_id,
        repo=repo,
        repository_id=repository_id,
        manifest_hash=manifest_hash,
        certificate_hash=certificate_hash,
        schema_hash=schema_hash,
        cortex_version=cortex_version,
        cortex_commit=commit,
        constitutional_config_hash=constitutional_config_hash,
        evidence_root_hash=evidence_root_hash,
        adaptive_root_hash=adaptive_root_hash,
        lineage_root_hash=lineage_root_hash,
        created_at=float(created_at if created_at is not None else time.time()),
        parent_epoch_id=parent_epoch_id,
        transition_reason=transition_reason,
        receipt_hash=receipt,
    )


def current_body_epoch(store: Any, repo: str) -> BodyEpoch | None:
    ensure_epoch_tables(store)
    row = store.db.execute(
        "SELECT * FROM body_epochs WHERE repo=? ORDER BY created_at DESC LIMIT 1",
        (repo,),
    ).fetchone()
    if not row:
        return None
    return BodyEpoch(
        epoch_id=str(row["epoch_id"]),
        repo=str(row["repo"]),
        repository_id=str(row["repository_id"] or ""),
        manifest_hash=str(row["manifest_hash"] or ""),
        certificate_hash=str(row["certificate_hash"] or ""),
        schema_hash=str(row["schema_hash"] or ""),
        cortex_version=str(row["cortex_version"] or ""),
        cortex_commit=str(row["cortex_commit"] or ""),
        constitutional_config_hash=str(row["constitutional_config_hash"] or ""),
        evidence_root_hash=str(row["evidence_root_hash"] or ""),
        adaptive_root_hash=str(row["adaptive_root_hash"] or ""),
        lineage_root_hash=str(row["lineage_root_hash"] or ""),
        created_at=float(row["created_at"] or 0),
        parent_epoch_id=row["parent_epoch_id"],
        transition_reason=str(row["transition_reason"] or ""),
        receipt_hash=str(row["receipt_hash"] or ""),
    )


def verify_body_epoch(store: Any, repo: str, epoch: BodyEpoch | dict[str, Any]) -> dict[str, Any]:
    ep = epoch if isinstance(epoch, BodyEpoch) else BodyEpoch.from_dict(epoch)
    live = compute_body_epoch(store, repo, cortex_commit=ep.cortex_commit)
    ok = live.epoch_id == ep.epoch_id
    mismatches = []
    if not ok:
        for field in (
            "manifest_hash",
            "certificate_hash",
            "schema_hash",
            "constitutional_config_hash",
            "evidence_root_hash",
            "adaptive_root_hash",
            "lineage_root_hash",
            "cortex_version",
        ):
            if getattr(live, field) != getattr(ep, field):
                mismatches.append(field)
    return {
        "ok": ok,
        "claimed_epoch_id": ep.epoch_id,
        "live_epoch_id": live.epoch_id,
        "mismatches": mismatches,
        "claim_boundary": CLAIM,
    }


def compare_epochs(left: BodyEpoch, right: BodyEpoch) -> EpochCompatibility:
    mismatches = []
    for field in (
        "repo",
        "repository_id",
        "manifest_hash",
        "evidence_root_hash",
        "adaptive_root_hash",
        "constitutional_config_hash",
        "schema_hash",
        "cortex_version",
    ):
        if getattr(left, field) != getattr(right, field):
            mismatches.append(field)
    if left.epoch_id == right.epoch_id:
        return EpochCompatibility(True, "identical", left.epoch_id, right.epoch_id, [])
    if not mismatches:
        return EpochCompatibility(True, "equivalent_roots", left.epoch_id, right.epoch_id, [])
    # evidence-compatible if only adaptive differs
    hard = [m for m in mismatches if m not in {"adaptive_root_hash", "lineage_root_hash"}]
    if not hard:
        return EpochCompatibility(
            False, "adaptive_divergence", left.epoch_id, right.epoch_id, mismatches
        )
    return EpochCompatibility(
        False, "incompatible", left.epoch_id, right.epoch_id, mismatches
    )


def seal_epoch_transition(
    store: Any,
    repo: str,
    *,
    reason: str,
    parent: BodyEpoch | None = None,
    cortex_commit: str = "",
) -> BodyEpoch:
    """Persist a new epoch when roots change; no-op return of current if unchanged."""
    ensure_epoch_tables(store)
    parent = parent or current_body_epoch(store, repo)
    parent_id = parent.epoch_id if parent else None
    epoch = compute_body_epoch(
        store,
        repo,
        cortex_commit=cortex_commit,
        parent_epoch_id=parent_id,
        transition_reason=reason,
    )
    if parent and parent.epoch_id == epoch.epoch_id:
        return parent  # no material change
    store.db.execute(
        """
        INSERT OR REPLACE INTO body_epochs(
          epoch_id, repo, repository_id, manifest_hash, certificate_hash, schema_hash,
          cortex_version, cortex_commit, constitutional_config_hash,
          evidence_root_hash, adaptive_root_hash, lineage_root_hash,
          created_at, parent_epoch_id, transition_reason, receipt_hash, sealed, metadata_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?)
        """,
        (
            epoch.epoch_id,
            epoch.repo,
            epoch.repository_id,
            epoch.manifest_hash,
            epoch.certificate_hash,
            epoch.schema_hash,
            epoch.cortex_version,
            epoch.cortex_commit,
            epoch.constitutional_config_hash,
            epoch.evidence_root_hash,
            epoch.adaptive_root_hash,
            epoch.lineage_root_hash,
            epoch.created_at,
            epoch.parent_epoch_id,
            epoch.transition_reason,
            epoch.receipt_hash,
            json.dumps({"reason": reason}),
        ),
    )
    store.db.commit()
    try:
        store.set_setting(
            f"body_epoch_current:{repo}",
            epoch.to_dict(),
        )
    except Exception:
        pass
    return epoch


def observe_current_epoch(store: Any, repo: str) -> dict[str, Any]:
    """Read-only epoch observation. Never creates or seals.

    Returns presence, live vs sealed comparison, and verification flags.
    Safe for mesh, continuity reports, dashboards, and diagnostics.
    """
    ensure_epoch_tables(store)
    cur = current_body_epoch(store, repo)
    live = compute_body_epoch(store, repo, transition_reason="observe")
    if cur is None:
        return {
            "present": False,
            "verified": False,
            "stale": True,
            "epoch_id": None,
            "live_epoch_id": live.epoch_id,
            "receipt_hash": None,
            "live": live.to_dict(),
            "sealed": None,
            "mismatches": ["epoch_absent"],
            "claim_boundary": CLAIM,
        }
    mismatches: list[str] = []
    if cur.epoch_id != live.epoch_id:
        for field in (
            "manifest_hash",
            "certificate_hash",
            "schema_hash",
            "constitutional_config_hash",
            "evidence_root_hash",
            "adaptive_root_hash",
            "lineage_root_hash",
            "cortex_version",
        ):
            if getattr(live, field) != getattr(cur, field):
                mismatches.append(field)
    verified = cur.epoch_id == live.epoch_id
    return {
        "present": True,
        "verified": verified,
        "stale": not verified,
        "epoch_id": cur.epoch_id,
        "live_epoch_id": live.epoch_id,
        "receipt_hash": cur.receipt_hash,
        "runtime_compatible": verified,
        "mismatches": mismatches,
        "sealed": cur.to_dict(),
        "live_roots": {
            "evidence_root_hash": live.evidence_root_hash,
            "adaptive_root_hash": live.adaptive_root_hash,
            "constitutional_config_hash": live.constitutional_config_hash,
        },
        "claim_boundary": CLAIM,
    }


def require_current_epoch(store: Any, repo: str) -> BodyEpoch:
    """Read-only: return sealed epoch if present and not stale; else raise.

    Never creates or seals. Use at gates that must not mutate.
    """
    obs = observe_current_epoch(store, repo)
    if not obs.get("present"):
        raise LookupError(f"body_epoch_absent:{repo}")
    if not obs.get("verified"):
        raise ValueError(
            f"body_epoch_stale:{repo}:mismatches={obs.get('mismatches')}"
        )
    cur = current_body_epoch(store, repo)
    if cur is None:
        raise LookupError(f"body_epoch_absent:{repo}")
    return cur


def ensure_current_epoch(store: Any, repo: str, *, reason: str = "ensure") -> BodyEpoch:
    """May mutate: create/seal if missing or roots drifted.

    Only for explicit mutation paths (activation, seal, self-org, phase init).
    Diagnostics, mesh, continuity reports must use observe_current_epoch.
    """
    live = compute_body_epoch(store, repo, transition_reason=reason)
    cur = current_body_epoch(store, repo)
    if cur is None or cur.epoch_id != live.epoch_id:
        return seal_epoch_transition(
            store, repo, reason=reason if cur is None else f"drift:{reason}", parent=cur
        )
    return cur


def open_epoch_transition(store: Any, repo: str, reason: str) -> dict[str, Any]:
    """Begin transition report (does not seal until seal_epoch_transition)."""
    parent = current_body_epoch(store, repo)
    proposed = compute_body_epoch(
        store, repo, parent_epoch_id=parent.epoch_id if parent else None, transition_reason=reason
    )
    transition = EpochTransition(
        repo=repo,
        reason=reason,
        parent_epoch_id=parent.epoch_id if parent else None,
        proposed_epoch_id=proposed.epoch_id,
        changed=(parent is None) or (parent.epoch_id != proposed.epoch_id),
        sealed=False,
        opened_at=time.time(),
    )
    return {
        **transition.to_dict(),
        "proposed": proposed.to_dict(),
    }


def epoch_receipt(epoch: BodyEpoch, *, sealed: bool = True) -> EpochReceipt:
    """Build independent continuity receipt from a BodyEpoch (no hidden witness material)."""
    components = (
        EpochComponent("manifest", epoch.manifest_hash),
        EpochComponent("evidence", epoch.evidence_root_hash),
        EpochComponent("adaptive", epoch.adaptive_root_hash),
        EpochComponent("lineage", epoch.lineage_root_hash),
        EpochComponent("constitution", epoch.constitutional_config_hash),
        EpochComponent("schema", epoch.schema_hash),
        EpochComponent("certificate", epoch.certificate_hash),
    )
    return EpochReceipt(
        receipt_hash=epoch.receipt_hash,
        epoch_id=epoch.epoch_id,
        repo=epoch.repo,
        transition_reason=epoch.transition_reason,
        parent_epoch_id=epoch.parent_epoch_id,
        sealed=sealed,
        components=components,
    )
