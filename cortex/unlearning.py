"""v6.25 Selective causal unlearning — plan then apply with snapshot."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from . import __version__
from .lineage import ensure_lineage_tables, invalidate_artifact, propagation_trace
from .quarantine import ensure_quarantine_tables, quarantine_artifacts

SCHEMA = "cortex-unlearning/1.0"
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
    payload_hash TEXT NOT NULL
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
    # Also include origin artifact ids themselves
    targets = sorted(set(str(o) for o in origin_ids) | set(descendants))

    # Classify proposed ops
    synapse_ids = [t for t in targets if t.startswith("syn_") or t.startswith("edge:")]
    other = [t for t in targets if t not in synapse_ids]

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
        "operations_proposed": [
            {"op": "quarantine_all_targets", "n": len(targets)},
            {"op": "invalidate_lineage", "n": len(targets)},
            {"op": "delete_invented_synapses", "ids": synapse_ids[:50]},
            {"op": "exclude_ranker_outcomes_contaminated", "note": "rebuild path"},
        ],
        "operations_refused": [
            {"op": "host_source_delete", "reason": "never_host_mutation"},
        ],
        "estimated_collateral": {
            "retrieval_impact": "low_if_only_learned_edges",
            "synapse_deletes": len(synapse_ids),
            "artifacts_quarantined": len(targets),
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


def _snapshot(store: Any, repo: str, plan_id: str) -> dict[str, Any]:
    # Capture invent synapses + settings keys related to ranker train count
    syns = []
    try:
        for row in store.neural_synapses(repo) or []:
            meta = {}
            try:
                meta = json.loads(row["metadata"] or "{}")
            except Exception:
                pass
            if meta.get("invented") or meta.get("source") in {
                "structure_invent",
                "pyramid_apex_close",
                "ratio_lattice_triad_close",
            }:
                syns.append(
                    {
                        "synapse_id": row["synapse_id"],
                        "source_id": row["source_id"],
                        "target_id": row["target_id"],
                        "relation": row["relation"],
                        "weight": float(row["weight"] or 0),
                        "metadata": meta,
                    }
                )
    except Exception:
        syns = []
    payload = {"synapses_invented": syns, "at": time.time(), "plan_id": plan_id}
    raw = json.dumps(payload, sort_keys=True, default=str)
    sid = "rs_" + hashlib.sha256(f"{repo}|{plan_id}|{raw}".encode()).hexdigest()[:18]
    ph = hashlib.sha256(raw.encode()).hexdigest()
    store.db.execute(
        """
        INSERT INTO repair_snapshots(snapshot_id, repo, plan_id, created_at, payload_json, payload_hash)
        VALUES(?,?,?,?,?,?)
        """,
        (sid, repo, plan_id, time.time(), raw, ph),
    )
    store.db.commit()
    return {"snapshot_id": sid, "payload_hash": ph, "n_synapses": len(syns)}


def apply_unlearning(
    store: Any,
    repo: str,
    plan_id: str,
    *,
    authorize: bool = False,
    governance_mode: str = "normal",
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

    row = store.db.execute(
        "SELECT * FROM unlearning_plans WHERE plan_id=? AND repo=?",
        (plan_id, repo),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "plan_not_found"}
    plan = json.loads(row["plan_json"])
    snap = _snapshot(store, repo, plan_id)
    targets = list(plan.get("affected_artifacts") or [])
    deleted = 0
    # Delete invented synapses present in targets
    with store.transaction() as conn:
        for tid in targets:
            sid = tid[5:] if tid.startswith("edge:") else tid
            if sid.startswith("syn_") or True:
                cur = conn.execute(
                    "DELETE FROM neural_synapses WHERE repo=? AND synapse_id=?",
                    (repo, sid),
                )
                deleted += cur.rowcount
            try:
                invalidate_artifact(store, repo, tid)
            except Exception:
                pass
    q = quarantine_artifacts(
        store,
        repo,
        targets,
        reason=f"unlearning_apply:{plan_id}",
        wound_id=str(plan.get("wound_id") or ""),
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
        "quarantine": q.get("envelope_id"),
        "targets_n": len(targets),
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
    return receipt


def rollback_repair(store: Any, repo: str, snapshot_id: str) -> dict[str, Any]:
    ensure_unlearning_tables(store)
    row = store.db.execute(
        "SELECT * FROM repair_snapshots WHERE snapshot_id=? AND repo=?",
        (snapshot_id, repo),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "snapshot_not_found"}
    payload = json.loads(row["payload_json"])
    restored = 0
    now = time.time()
    with store.transaction() as conn:
        for s in payload.get("synapses_invented") or []:
            meta = s.get("metadata") or {}
            conn.execute(
                """
                INSERT INTO neural_synapses(
                  repo, synapse_id, source_id, target_id, relation, base_weight, weight,
                  minimum_weight, maximum_weight, plasticity_rule, update_count,
                  evidence, metadata, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,0,?,?,?)
                ON CONFLICT(repo, synapse_id) DO UPDATE SET
                  weight=excluded.weight, metadata=excluded.metadata, updated_at=excluded.updated_at
                """,
                (
                    repo,
                    s["synapse_id"],
                    s["source_id"],
                    s["target_id"],
                    s.get("relation") or "coactivated",
                    float(s.get("weight") or 0.1),
                    float(s.get("weight") or 0.1),
                    0.01,
                    0.95,
                    "bounded_hebbian",
                    json.dumps(["rollback_restore"]),
                    json.dumps(meta),
                    now,
                ),
            )
            restored += 1
    return {
        "ok": True,
        "snapshot_id": snapshot_id,
        "restored_synapses": restored,
        "claim_boundary": CLAIM,
    }
