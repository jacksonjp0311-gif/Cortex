"""v6.25 Causal lineage graph for adaptive memory artifacts."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from . import __version__

SCHEMA = "cortex-lineage/1.0"
GLYPH = "◎→"

CLAIM = (
    "Lineage is provenance of adaptive artifacts for quarantine and unlearning. "
    "Not host authority. Not consciousness."
)

DDL = """
CREATE TABLE IF NOT EXISTS lineage_artifacts(
    artifact_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    lineage_plane TEXT NOT NULL DEFAULT 'G_learned',
    parent_ids_json TEXT NOT NULL DEFAULT '[]',
    origin_memory_ids_json TEXT NOT NULL DEFAULT '[]',
    origin_content_hashes_json TEXT NOT NULL DEFAULT '[]',
    operation_id TEXT,
    operator_id TEXT,
    governance_mode TEXT,
    controller TEXT,
    created_at REAL NOT NULL,
    code_version TEXT,
    configuration_hash TEXT,
    receipt_hash TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    invalidated INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(repo, artifact_id)
);
CREATE INDEX IF NOT EXISTS idx_lineage_repo_type ON lineage_artifacts(repo, artifact_type);
CREATE INDEX IF NOT EXISTS idx_lineage_repo_invalid ON lineage_artifacts(repo, invalidated);

CREATE TABLE IF NOT EXISTS lineage_edges(
    repo TEXT NOT NULL,
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    relation TEXT NOT NULL DEFAULT 'derived_from',
    created_at REAL NOT NULL,
    PRIMARY KEY(repo, parent_id, child_id, relation)
);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_child ON lineage_edges(repo, child_id);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_parent ON lineage_edges(repo, parent_id);
"""


def ensure_lineage_tables(store: Any) -> None:
    store.db.executescript(DDL)
    store.db.commit()


def _j(x: Any) -> str:
    return json.dumps(x if x is not None else [], sort_keys=True)


def record_artifact(
    store: Any,
    repo: str,
    *,
    artifact_id: str,
    artifact_type: str,
    lineage_plane: str = "G_learned",
    parent_ids: list[str] | None = None,
    origin_memory_ids: list[Any] | None = None,
    origin_content_hashes: list[str] | None = None,
    operation_id: str | None = None,
    operator_id: str = "system",
    governance_mode: str = "normal",
    controller: str = "advanced",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_lineage_tables(store)
    now = time.time()
    parents = [str(p) for p in (parent_ids or [])]
    origins = [str(o) for o in (origin_memory_ids or [])]
    hashes = [str(h) for h in (origin_content_hashes or [])]
    meta = metadata or {}
    material = f"{repo}|{artifact_id}|{artifact_type}|{parents}|{origins}|{now}"
    receipt = hashlib.sha256(material.encode()).hexdigest()
    store.db.execute(
        """
        INSERT INTO lineage_artifacts(
          artifact_id, repo, artifact_type, lineage_plane,
          parent_ids_json, origin_memory_ids_json, origin_content_hashes_json,
          operation_id, operator_id, governance_mode, controller,
          created_at, code_version, configuration_hash, receipt_hash, metadata_json
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(repo, artifact_id) DO UPDATE SET
          parent_ids_json=excluded.parent_ids_json,
          origin_memory_ids_json=excluded.origin_memory_ids_json,
          metadata_json=excluded.metadata_json,
          receipt_hash=excluded.receipt_hash
        """,
        (
            artifact_id,
            repo,
            artifact_type,
            lineage_plane,
            _j(parents),
            _j(origins),
            _j(hashes),
            operation_id,
            operator_id,
            governance_mode,
            controller,
            now,
            __version__,
            meta.get("configuration_hash"),
            receipt,
            _j(meta),
        ),
    )
    for p in parents:
        store.db.execute(
            """
            INSERT OR IGNORE INTO lineage_edges(repo, parent_id, child_id, relation, created_at)
            VALUES(?,?,?,?,?)
            """,
            (repo, p, artifact_id, "derived_from", now),
        )
    for o in origins:
        oid = f"mem:{o}"
        store.db.execute(
            """
            INSERT OR IGNORE INTO lineage_edges(repo, parent_id, child_id, relation, created_at)
            VALUES(?,?,?,?,?)
            """,
            (repo, oid, artifact_id, "origin_memory", now),
        )
    store.db.commit()
    return {
        "artifact_id": artifact_id,
        "repo": repo,
        "artifact_type": artifact_type,
        "receipt_hash": receipt,
        "parents": parents,
        "origins": origins,
    }


def ancestors_of(store: Any, repo: str, artifact_id: str, *, limit: int = 200) -> list[str]:
    ensure_lineage_tables(store)
    seen: set[str] = set()
    stack = [artifact_id]
    out: list[str] = []
    while stack and len(out) < limit:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        rows = store.db.execute(
            "SELECT parent_id FROM lineage_edges WHERE repo=? AND child_id=?",
            (repo, cur),
        ).fetchall()
        for r in rows:
            p = str(r["parent_id"])
            if p not in seen:
                out.append(p)
                stack.append(p)
    return out


def descendants_of(store: Any, repo: str, artifact_id: str, *, limit: int = 500) -> list[str]:
    ensure_lineage_tables(store)
    seen: set[str] = set()
    stack = [artifact_id]
    out: list[str] = []
    while stack and len(out) < limit:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        rows = store.db.execute(
            "SELECT child_id FROM lineage_edges WHERE repo=? AND parent_id=?",
            (repo, cur),
        ).fetchall()
        for r in rows:
            c = str(r["child_id"])
            if c not in seen:
                out.append(c)
                stack.append(c)
    return out


def propagation_trace(
    store: Any,
    repo: str,
    origin_ids: list[str],
    *,
    limit: int = 1000,
) -> dict[str, Any]:
    ensure_lineage_tables(store)
    all_desc: list[str] = []
    for oid in origin_ids:
        key = oid if str(oid).startswith("mem:") or ":" in str(oid) else f"mem:{oid}"
        all_desc.extend(descendants_of(store, repo, key, limit=limit))
        all_desc.extend(descendants_of(store, repo, str(oid), limit=limit))
    # unique preserve order
    seen: set[str] = set()
    uniq = []
    for d in all_desc:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "origins": list(origin_ids),
        "descendants": uniq[:limit],
        "n_descendants": len(uniq),
        "claim_boundary": CLAIM,
    }


def invalidate_artifact(store: Any, repo: str, artifact_id: str) -> bool:
    ensure_lineage_tables(store)
    cur = store.db.execute(
        "UPDATE lineage_artifacts SET invalidated=1 WHERE repo=? AND artifact_id=?",
        (repo, artifact_id),
    )
    store.db.commit()
    return cur.rowcount > 0


def lineage_integrity_check(store: Any, repo: str) -> dict[str, Any]:
    ensure_lineage_tables(store)
    arts = store.db.execute(
        "SELECT artifact_id, parent_ids_json, lineage_plane, invalidated FROM lineage_artifacts WHERE repo=?",
        (repo,),
    ).fetchall()
    issues: list[dict[str, Any]] = []
    ids = {str(a["artifact_id"]) for a in arts}
    for a in arts:
        aid = str(a["artifact_id"])
        try:
            parents = json.loads(a["parent_ids_json"] or "[]")
        except Exception:
            parents = []
            issues.append({"kind": "bad_parent_json", "artifact_id": aid})
        for p in parents:
            # parents may be mem: ids or artifacts
            if str(p) in ids or str(p).startswith("mem:"):
                continue
            # dangling parent reference
            issues.append({"kind": "missing_parent", "artifact_id": aid, "parent": p})
        if a["lineage_plane"] == "G_evidence" and "invent" in aid.casefold():
            issues.append({"kind": "learned_marked_evidence", "artifact_id": aid})
    # simple cycle detection on edges
    for a in list(ids)[:200]:
        if a in set(descendants_of(store, repo, a, limit=50)) and a in set(
            ancestors_of(store, repo, a, limit=50)
        ):
            # only if self in both - true cycle
            des = set(descendants_of(store, repo, a, limit=100))
            if a in des:
                issues.append({"kind": "cycle", "artifact_id": a})
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "n_artifacts": len(arts),
        "issues": issues[:50],
        "ok": len(issues) == 0,
        "claim_boundary": CLAIM,
    }
