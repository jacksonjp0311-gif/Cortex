"""v6.25.1 Selective causal unlearning — plan, full DB snapshot, apply, rollback."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .lineage import ensure_lineage_tables, invalidate_artifact, propagation_trace
from .quarantine import ensure_quarantine_tables, quarantine_artifacts
from .state_transition import logical_state_digest

SCHEMA = "cortex-unlearning/1.1"
GLYPH = "↺"

CLAIM = (
    "Selective causal unlearning removes or invalidates adaptive descendants of a wound. "
    "Never host source mutation. Not consciousness."
)

DDL = """
CREATE TABLE IF NOT EXISTS repair_snapshots(
    snapshot_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    backup_path TEXT,
    backup_hash TEXT,
    logical_state_hash TEXT,
    manifest_hash TEXT,
    verified INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS unlearning_plans(
    plan_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    wound_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    plan_json TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    applied INTEGER NOT NULL DEFAULT 0,
    repair_id TEXT
);
CREATE TABLE IF NOT EXISTS repair_receipts(
    repair_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    plan_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    ok INTEGER NOT NULL,
    receipt_json TEXT NOT NULL,
    receipt_hash TEXT NOT NULL
);
"""

REPAIR_HANDLERS: dict[str, str] = {
    "invented_synapse": "remove_synapse",
    "ranker_training_event": "exclude_ranker_event",
    "summary": "invalidate_summary",
    "episode": "quarantine_episode",
    "discovery_card": "invalidate_card",
    "fusion_event": "reset_fusion_descendant",
    "spectral_promotion": "invalidate_calibration",
    "federated_projection": "invalidate_projection",
}


def ensure_unlearning_tables(store: Any) -> None:
    ensure_lineage_tables(store)
    ensure_quarantine_tables(store)
    store.db.executescript(DDL)
    store.db.commit()


def plan_unlearning(
    store: Any,
    repo: str,
    *,
    wound_id: str,
    origin_ids: list[str],
    reason: str = "memory_wound",
) -> dict[str, Any]:
    ensure_unlearning_tables(store)
    trace = propagation_trace(store, repo, origin_ids)
    descendants = list(trace.get("descendants") or [])
    targets = sorted(set(str(o) for o in origin_ids) | set(descendants))

    ops: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = [
        {"op": "host_source_delete", "reason": "never_host_mutation"}
    ]
    for tid in targets:
        atype = "invented_synapse" if tid.startswith("syn_") else (
            "ranker_training_event" if tid.startswith("rte_") else "unknown"
        )
        if atype == "unknown":
            # try lineage
            try:
                row = store.db.execute(
                    "SELECT artifact_type FROM lineage_artifacts WHERE repo=? AND artifact_id=?",
                    (repo, tid),
                ).fetchone()
                if row:
                    atype = str(row["artifact_type"])
            except Exception:
                pass
        handler = REPAIR_HANDLERS.get(atype)
        if handler:
            ops.append({"artifact_id": tid, "artifact_type": atype, "handler": handler})
        else:
            refused.append(
                {
                    "artifact_id": tid,
                    "artifact_type": atype,
                    "reason": "no_repair_handler",
                }
            )

    plan = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "wound_id": wound_id,
        "repo": repo,
        "reason": reason,
        "origins": list(origin_ids),
        "direct_and_transitive_descendants": descendants,
        "n_descendants": len(descendants),
        "affected_artifacts": targets,
        "operations_proposed": ops,
        "operations_refused": refused,
        "estimated_collateral": {
            "handlers": len(ops),
            "refused": len(refused) - 1,
        },
        "claim_boundary": CLAIM,
    }
    now = time.time()
    plan_id = "up_" + hashlib.sha256(f"{repo}|{wound_id}|{now}".encode()).hexdigest()[:18]
    plan_hash = hashlib.sha256(
        json.dumps(plan, sort_keys=True, default=str).encode()
    ).hexdigest()
    plan["plan_id"] = plan_id
    plan["plan_hash"] = plan_hash
    store.db.execute(
        """
        INSERT INTO unlearning_plans(plan_id, repo, wound_id, created_at, plan_json, plan_hash)
        VALUES(?,?,?,?,?,?)
        """,
        (plan_id, repo, wound_id, now, json.dumps(plan, default=str), plan_hash),
    )
    store.db.commit()
    return plan


def create_db_snapshot(
    store: Any,
    repo: str,
    plan_id: str,
    *,
    home: Path | None = None,
) -> dict[str, Any]:
    """Full SQLite backup snapshot with integrity verification."""
    ensure_unlearning_tables(store)
    try:
        store.db.execute("PRAGMA wal_checkpoint(FULL)")
    except Exception:
        pass
    logical = logical_state_digest(store, repo)
    sid = "rs_" + hashlib.sha256(f"{repo}|{plan_id}|{time.time()}".encode()).hexdigest()[:18]
    base = Path(home) if home else Path.home() / ".cortex"
    snap_dir = base / "work" / "repair_snapshots" / repo
    # also under repo work if available
    try:
        from pathlib import Path as P

        # prefer Desktop Cortex work if store path under user
        snap_dir = P(store.path).resolve().parent / "repair_snapshots" / repo
    except Exception:
        pass
    snap_dir.mkdir(parents=True, exist_ok=True)
    backup_path = snap_dir / f"{sid}.sqlite"
    # sqlite backup API
    dst = sqlite3.connect(str(backup_path))
    try:
        store.db.backup(dst)
        dst.execute("PRAGMA integrity_check")
        ic = dst.execute("PRAGMA integrity_check").fetchone()
        verified = bool(ic and ic[0] == "ok")
    finally:
        dst.close()
    raw = backup_path.read_bytes()
    backup_hash = hashlib.sha256(raw).hexdigest()
    manifest_hash = ""
    try:
        row = store.repo(repo)
        if row:
            manifest_hash = str(row["manifest_hash"] or "")
    except Exception:
        pass
    meta = {
        "snapshot_id": sid,
        "repo": repo,
        "plan_id": plan_id,
        "database_path": str(store.path),
        "backup_path": str(backup_path),
        "backup_hash": backup_hash,
        "logical_state_hash": logical,
        "manifest_hash": manifest_hash,
        "schema_hash": hashlib.sha256(SCHEMA.encode()).hexdigest(),
        "created_at": time.time(),
        "verified": verified,
        "version": __version__,
    }
    store.db.execute(
        """
        INSERT INTO repair_snapshots(
          snapshot_id, repo, plan_id, created_at, payload_json, payload_hash,
          backup_path, backup_hash, logical_state_hash, manifest_hash, verified
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            sid,
            repo,
            plan_id,
            time.time(),
            json.dumps(meta),
            hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest(),
            str(backup_path),
            backup_hash,
            logical,
            manifest_hash,
            1 if verified else 0,
        ),
    )
    store.db.commit()
    return meta


def _remove_synapse(conn: Any, repo: str, sid: str) -> int:
    cur = conn.execute(
        "DELETE FROM neural_synapses WHERE repo=? AND synapse_id=?",
        (repo, sid.replace("edge:", "")),
    )
    return cur.rowcount


def apply_unlearning(
    store: Any,
    repo: str,
    plan_id: str,
    *,
    authorize: bool = False,
    governance_mode: str = "normal",
    capability: Any = None,
    home: Path | None = None,
) -> dict[str, Any]:
    ensure_unlearning_tables(store)
    if not authorize:
        return {
            "ok": False,
            "error": "authorize_required",
            "hint": "Pass authorize=True / --authorize",
            "claim_boundary": CLAIM,
        }
    if governance_mode == "read_only":
        return {"ok": False, "error": "governor_read_only", "claim_boundary": CLAIM}

    # capability gate
    try:
        from .capabilities import issue_for_controller, validate_capability

        cap = capability or issue_for_controller(repo, "repair", reason="unlearning_apply")
        d = validate_capability(cap, repo=repo, operation="repair_synapse_remove")
        if not d.allowed:
            return {"ok": False, "error": d.reason, "claim_boundary": CLAIM}
    except Exception as exc:
        return {"ok": False, "error": f"capability:{type(exc).__name__}:{exc}"}

    row = store.db.execute(
        "SELECT * FROM unlearning_plans WHERE plan_id=? AND repo=?",
        (plan_id, repo),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "plan_not_found"}
    plan = json.loads(row["plan_json"])
    snap = create_db_snapshot(store, repo, plan_id, home=home)
    if not snap.get("verified"):
        return {"ok": False, "error": "snapshot_integrity_failed", "snapshot": snap}

    pre_hash = snap["logical_state_hash"]
    deleted = 0
    excluded_events: list[str] = []
    handled: list[str] = []
    try:
        store.db.execute("BEGIN IMMEDIATE")
        for op in plan.get("operations_proposed") or []:
            tid = str(op.get("artifact_id") or "")
            handler = op.get("handler")
            if handler == "remove_synapse":
                deleted += _remove_synapse(store.db, repo, tid)
                handled.append(tid)
            elif handler == "exclude_ranker_event":
                store.db.execute(
                    "UPDATE ranker_training_events SET excluded=1, exclusion_reason=? WHERE repo=? AND event_id=?",
                    ("unlearning", repo, tid),
                )
                excluded_events.append(tid)
                handled.append(tid)
            else:
                # invalidate lineage only
                handled.append(tid)
            try:
                store.db.execute(
                    "UPDATE lineage_artifacts SET invalidated=1 WHERE repo=? AND artifact_id=?",
                    (repo, tid),
                )
            except Exception:
                pass
        # quarantine remaining
        targets = list(plan.get("affected_artifacts") or [])
        # inline quarantine without nested commit
        from .quarantine import ensure_quarantine_tables

        ensure_quarantine_tables(store)
        eid = "qe_" + hashlib.sha256(f"{repo}|{plan_id}|q".encode()).hexdigest()[:16]
        store.db.execute(
            """
            INSERT INTO quarantine_envelopes(
              envelope_id, repo, artifact_ids_json, reason, wound_id,
              created_at, expires_at, active, receipt_hash, metadata_json
            ) VALUES(?,?,?,?,?,?,NULL,1,?,?)
            """,
            (
                eid,
                repo,
                json.dumps(targets),
                f"unlearning_apply:{plan_id}",
                str(plan.get("wound_id") or ""),
                time.time(),
                hashlib.sha256(eid.encode()).hexdigest(),
                json.dumps({"version": __version__}),
            ),
        )
        if excluded_events:
            from .ranker.model import rebuild_ranker_from_events

            rebuild_ranker_from_events(
                store,
                repo,
                excluded_events,
                capability=cap,
                conn=store.db,
                commit=False,
            )
        store.db.execute(
            "UPDATE unlearning_plans SET applied=1 WHERE plan_id=?", (plan_id,)
        )
        repair_id = "rr_" + hashlib.sha256(f"{plan_id}|{time.time()}".encode()).hexdigest()[:18]
        receipt = {
            "repair_id": repair_id,
            "plan_id": plan_id,
            "snapshot_id": snap["snapshot_id"],
            "deleted_synapses": deleted,
            "quarantine": eid,
            "handled": handled,
            "excluded_events": excluded_events,
            "pre_logical_hash": pre_hash,
            "version": __version__,
            "ok": True,
        }
        rh = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
        store.db.execute(
            """
            INSERT INTO repair_receipts(repair_id, repo, plan_id, snapshot_id, created_at, ok, receipt_json, receipt_hash)
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                repair_id,
                repo,
                plan_id,
                snap["snapshot_id"],
                time.time(),
                1,
                json.dumps(receipt),
                rh,
            ),
        )
        store.db.execute(
            "UPDATE unlearning_plans SET repair_id=? WHERE plan_id=?",
            (repair_id, plan_id),
        )
        store.db.commit()
        receipt["receipt_hash"] = rh
        receipt["schema_version"] = SCHEMA
        receipt["claim_boundary"] = CLAIM
        receipt["post_logical_hash"] = logical_state_digest(store, repo)
        return receipt
    except Exception as exc:
        try:
            store.db.rollback()
        except Exception:
            pass
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "snapshot_id": snap.get("snapshot_id"),
            "claim_boundary": CLAIM,
        }


def rollback_repair(store: Any, repo: str, snapshot_id: str) -> dict[str, Any]:
    """Restore complete DB from verified backup; check logical hash."""
    ensure_unlearning_tables(store)
    row = store.db.execute(
        "SELECT * FROM repair_snapshots WHERE snapshot_id=? AND repo=?",
        (snapshot_id, repo),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "snapshot_not_found"}
    backup_path = str(row["backup_path"] or "")
    expected = str(row["logical_state_hash"] or "")
    if not backup_path or not Path(backup_path).is_file():
        return {"ok": False, "error": "backup_missing", "path": backup_path}
    # verify backup hash
    raw = Path(backup_path).read_bytes()
    bh = hashlib.sha256(raw).hexdigest()
    if row["backup_hash"] and bh != row["backup_hash"]:
        return {"ok": False, "error": "backup_hash_mismatch"}
    # restore: close isn't available; use backup into main db
    src = sqlite3.connect(backup_path)
    try:
        ic = src.execute("PRAGMA integrity_check").fetchone()
        if not ic or ic[0] != "ok":
            return {"ok": False, "error": "backup_integrity_failed"}
        store.db.execute("BEGIN IMMEDIATE")
        # wipe and restore via backup API reverse
        store.db.rollback()  # clear begin
        src.backup(store.db)
    finally:
        src.close()
    after = logical_state_digest(store, repo)
    ok = (not expected) or (after == expected)
    return {
        "ok": ok,
        "snapshot_id": snapshot_id,
        "logical_state_hash_before": expected,
        "logical_state_hash_after": after,
        "integrity_ok": True,
        "claim_boundary": CLAIM,
    }
