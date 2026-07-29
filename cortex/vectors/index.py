"""Persist and query HNSW in the single Cortex SQLite substrate."""

from __future__ import annotations

import json
import struct
import time
from hashlib import sha256
from typing import Any

from ..embeddings import VECTOR_MAGIC, deserialize_vector, get_embedder
from .hnsw import HNSWIndex

INDEX_ID = "hnsw_v1"


def insert_memory_vector(
    store: Any,
    repo: str,
    memory_id: int,
    vector: list[float],
    path: str = "",
) -> dict[str, Any]:
    """Incremental HNSW insert when an index already exists (v6)."""

    status = hnsw_status(store, repo)
    if not status.get("available"):
        return {"inserted": False, "reason": "index_missing"}
    key = f"mem:{memory_id}"
    existing = store.db.execute(
        """
        SELECT 1 FROM vector_index_nodes
        WHERE repo=? AND index_id=? AND node_key=?
        """,
        (repo, INDEX_ID, key),
    ).fetchone()
    if existing:
        return {"inserted": False, "reason": "already_present", "node_key": key}
    dim = int(status.get("dim") or len(vector))
    # Neighbor against a sample of existing keys
    rows = store.db.execute(
        """
        SELECT node_key, vector_blob FROM vector_index_nodes
        WHERE repo=? AND index_id=?
        ORDER BY node_key LIMIT 256
        """,
        (repo, INDEX_ID),
    ).fetchall()
    scored: list[tuple[float, str]] = []
    from .hnsw import cosine_similarity

    for row in rows:
        v = _vec_from_blob(row["vector_blob"])
        if not v:
            continue
        scored.append((cosine_similarity(vector, v), row["node_key"]))
    scored.sort(reverse=True)
    nbs = [k for _, k in scored[:8]]
    store.db.execute(
        """
        INSERT INTO vector_index_nodes(
          repo, index_id, node_key, vector_kind, layer, neighbors_json,
          vector_blob, path, memory_id
        ) VALUES(?, ?, ?, 'chunk', 0, ?, ?, ?, ?)
        """,
        (
            repo,
            INDEX_ID,
            key,
            json.dumps(sorted(nbs)),
            _vec_blob(list(vector[:dim]) + [0.0] * max(0, dim - len(vector))),
            path,
            memory_id,
        ),
    )
    # Bidirectional light link
    for peer in nbs[:4]:
        prow = store.db.execute(
            """
            SELECT neighbors_json FROM vector_index_nodes
            WHERE repo=? AND index_id=? AND node_key=?
            """,
            (repo, INDEX_ID, peer),
        ).fetchone()
        if not prow:
            continue
        peers = json.loads(prow["neighbors_json"] or "[]")
        if key not in peers:
            peers.append(key)
            peers = sorted(peers)[:16]
            store.db.execute(
                """
                UPDATE vector_index_nodes SET neighbors_json=?
                WHERE repo=? AND index_id=? AND node_key=?
                """,
                (json.dumps(peers), repo, INDEX_ID, peer),
            )
    store.db.commit()
    return {"inserted": True, "node_key": key, "neighbors": nbs}


def _vec_blob(vector: list[float]) -> bytes:
    return VECTOR_MAGIC + struct.pack(f"<{len(vector)}f", *[float(x) for x in vector])


def _vec_from_blob(blob: bytes) -> list[float]:
    if blob.startswith(VECTOR_MAGIC):
        raw = blob[len(VECTOR_MAGIC) :]
        n = len(raw) // 4
        return list(struct.unpack(f"<{n}f", raw))
    return deserialize_vector(blob) or []


def build_hnsw_index(
    store: Any,
    repo: str,
    *,
    M: int = 8,
    ef_construction: int = 32,
    limit: int = 50_000,
) -> dict[str, Any]:
    """Build deterministic HNSW from memory vectors. Local only."""

    rows = store.db.execute(
        """
        SELECT id, path, vector, kind FROM memories
        WHERE repo=? AND vector IS NOT NULL
        ORDER BY id
        LIMIT ?
        """,
        (repo, limit),
    ).fetchall()
    items: list[tuple[str, list[float], str, int]] = []
    dim = 0
    for row in rows:
        vec = deserialize_vector(row["vector"])
        if not vec:
            continue
        dim = dim or len(vec)
        key = f"mem:{row['id']}"
        items.append((key, vec, str(row["path"] or ""), int(row["id"])))
    if not items:
        return {
            "built": False,
            "reason": "no_vectors",
            "repo": repo,
            "claim_boundary": "HNSW build needs indexed vectors; grants no authority.",
        }

    seed_material = f"{repo}|{INDEX_ID}|{len(items)}|{items[0][0]}|{items[-1][0]}"
    seed = int.from_bytes(sha256(seed_material.encode()).digest()[:8], "big")
    index = HNSWIndex(dim=dim, M=M, ef_construction=ef_construction, seed=seed)
    index.build((k, v) for k, v, _, _ in items)
    fp = sha256(
        json.dumps(
            {"n": len(items), "dim": dim, "M": M, "seed": seed},
            sort_keys=True,
        ).encode()
    ).hexdigest()

    now = time.time()
    with store.transaction() as conn:
        conn.execute(
            "DELETE FROM vector_index_nodes WHERE repo=? AND index_id=?",
            (repo, INDEX_ID),
        )
        conn.execute(
            """
            INSERT INTO vector_indices(
              repo, index_id, algorithm, dim, metric, params_json,
              build_fingerprint, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(repo, index_id) DO UPDATE SET
              algorithm=excluded.algorithm, dim=excluded.dim, metric=excluded.metric,
              params_json=excluded.params_json, build_fingerprint=excluded.build_fingerprint,
              created_at=excluded.created_at
            """,
            (
                repo,
                INDEX_ID,
                "hnsw_v1",
                dim,
                "cosine",
                json.dumps({"M": M, "ef_construction": ef_construction, "seed": seed}),
                fp,
                now,
            ),
        )
        for key, vec, path, mid in items:
            nbs = index.neighbors.get(key) or []
            conn.execute(
                """
                INSERT INTO vector_index_nodes(
                  repo, index_id, node_key, vector_kind, layer, neighbors_json,
                  vector_blob, path, memory_id
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    repo,
                    INDEX_ID,
                    key,
                    "chunk",
                    0,
                    json.dumps(sorted(nbs)),
                    _vec_blob(vec),
                    path,
                    mid,
                ),
            )

    try:
        store.append_neural_event(
            repo,
            event_type="hnsw_built",
            entity_id=INDEX_ID,
            payload={"nodes": len(items), "dim": dim, "fingerprint": fp},
        )
    except Exception:
        pass

    return {
        "built": True,
        "repo": repo,
        "index_id": INDEX_ID,
        "nodes": len(items),
        "dim": dim,
        "algorithm": "hnsw_v1",
        "build_fingerprint": fp,
        "claim_boundary": "Vector index is evidence infrastructure; not mutation authority.",
    }


def hnsw_status(store: Any, repo: str) -> dict[str, Any]:
    row = store.db.execute(
        "SELECT * FROM vector_indices WHERE repo=? AND index_id=?",
        (repo, INDEX_ID),
    ).fetchone()
    count = store.db.execute(
        "SELECT COUNT(*) AS c FROM vector_index_nodes WHERE repo=? AND index_id=?",
        (repo, INDEX_ID),
    ).fetchone()["c"]
    if not row:
        return {
            "available": False,
            "repo": repo,
            "index_id": INDEX_ID,
            "nodes": 0,
            "fallback": "lsh_buckets+fts",
        }
    return {
        "available": True,
        "repo": repo,
        "index_id": row["index_id"],
        "algorithm": row["algorithm"],
        "dim": row["dim"],
        "metric": row["metric"],
        "params": json.loads(row["params_json"] or "{}"),
        "build_fingerprint": row["build_fingerprint"],
        "nodes": int(count),
        "created_at": row["created_at"],
        "claim_boundary": "HNSW status is local telemetry only.",
    }


def query_hnsw(
    store: Any,
    repo: str,
    text: str,
    *,
    k: int = 12,
) -> list[dict[str, Any]]:
    status = hnsw_status(store, repo)
    if not status.get("available"):
        return []
    q = get_embedder().encode_one(text)
    rows = store.db.execute(
        """
        SELECT node_key, neighbors_json, vector_blob, path, memory_id
        FROM vector_index_nodes
        WHERE repo=? AND index_id=?
        """,
        (repo, INDEX_ID),
    ).fetchall()
    if not rows:
        return []
    # Rebuild lightweight index in memory for search
    dim = status["dim"]
    index = HNSWIndex(dim=dim, seed=int((status.get("params") or {}).get("seed") or 0))
    for row in rows:
        vec = _vec_from_blob(row["vector_blob"])
        if not vec:
            continue
        key = row["node_key"]
        index.vectors[key] = vec
        index.neighbors[key] = json.loads(row["neighbors_json"] or "[]")
        if index.entry_point is None:
            index.entry_point = key
    hits = index.search(q, k=k)
    path_map = {row["node_key"]: row for row in rows}
    out: list[dict[str, Any]] = []
    for key, score in hits:
        row = path_map.get(key)
        if not row:
            continue
        out.append(
            {
                "node_key": key,
                "score": round(float(score), 6),
                "path": row["path"],
                "memory_id": row["memory_id"],
                "source": "hnsw_v1",
            }
        )
    return out
