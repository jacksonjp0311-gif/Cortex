"""v6.25 Quarantine envelopes — block adaptive influence without host deletion."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from . import __version__
from .lineage import ensure_lineage_tables, invalidate_artifact

SCHEMA = "cortex-quarantine/1.0"
GLYPH = "⊘"

CLAIM = (
    "Quarantine blocks adaptive retrieval and training influence. "
    "Not host source deletion. Not consciousness."
)

DDL = """
CREATE TABLE IF NOT EXISTS quarantine_envelopes(
    envelope_id TEXT PRIMARY KEY,
    repo TEXT NOT NULL,
    artifact_ids_json TEXT NOT NULL,
    reason TEXT NOT NULL,
    wound_id TEXT,
    created_at REAL NOT NULL,
    expires_at REAL,
    active INTEGER NOT NULL DEFAULT 1,
    receipt_hash TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_quarantine_repo_active ON quarantine_envelopes(repo, active);
"""


def ensure_quarantine_tables(store: Any) -> None:
    ensure_lineage_tables(store)
    store.db.executescript(DDL)
    store.db.commit()


def _hash_chain(prev: str, material: str) -> str:
    return hashlib.sha256(f"{prev}|{material}".encode()).hexdigest()


def active_quarantined_ids(store: Any, repo: str) -> set[str]:
    ensure_quarantine_tables(store)
    now = time.time()
    rows = store.db.execute(
        "SELECT artifact_ids_json, expires_at FROM quarantine_envelopes WHERE repo=? AND active=1",
        (repo,),
    ).fetchall()
    out: set[str] = set()
    for r in rows:
        exp = r["expires_at"]
        if exp is not None and float(exp) < now:
            continue
        try:
            ids = json.loads(r["artifact_ids_json"] or "[]")
        except Exception:
            ids = []
        for i in ids:
            out.add(str(i))
    return out


def is_quarantined(store: Any, repo: str, artifact_id: str) -> bool:
    return str(artifact_id) in active_quarantined_ids(store, repo)


def quarantine_artifacts(
    store: Any,
    repo: str,
    artifact_ids: list[str],
    *,
    reason: str,
    wound_id: str | None = None,
    expires_at: float | None = None,
    invalidate_lineage: bool = True,
) -> dict[str, Any]:
    ensure_quarantine_tables(store)
    ids = sorted({str(a) for a in artifact_ids if a})
    now = time.time()
    eid = "qe_" + hashlib.sha256(f"{repo}|{ids}|{now}".encode()).hexdigest()[:18]
    prev = ""
    try:
        row = store.db.execute(
            "SELECT receipt_hash FROM quarantine_envelopes WHERE repo=? ORDER BY created_at DESC LIMIT 1",
            (repo,),
        ).fetchone()
        if row:
            prev = str(row["receipt_hash"] or "")
    except Exception:
        prev = ""
    material = json.dumps(
        {"id": eid, "repo": repo, "ids": ids, "reason": reason, "at": now},
        sort_keys=True,
    )
    receipt = _hash_chain(prev, material)
    store.db.execute(
        """
        INSERT INTO quarantine_envelopes(
          envelope_id, repo, artifact_ids_json, reason, wound_id,
          created_at, expires_at, active, receipt_hash, metadata_json
        ) VALUES(?,?,?,?,?,?,?,1,?,?)
        """,
        (
            eid,
            repo,
            json.dumps(ids),
            reason,
            wound_id,
            now,
            expires_at,
            receipt,
            json.dumps({"version": __version__}),
        ),
    )
    if invalidate_lineage:
        for aid in ids:
            try:
                invalidate_artifact(store, repo, aid)
            except Exception:
                pass
    store.db.commit()
    # settings index for fast retrieval filters
    try:
        store.set_setting(
            f"quarantine_active:{repo}",
            {"ids": list(active_quarantined_ids(store, repo)), "updated_at": now},
        )
    except Exception:
        pass
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "envelope_id": eid,
        "repo": repo,
        "artifact_ids": ids,
        "reason": reason,
        "wound_id": wound_id,
        "receipt_hash": receipt,
        "active": True,
        "claim_boundary": CLAIM,
    }


def release_quarantine(store: Any, repo: str, envelope_id: str) -> dict[str, Any]:
    ensure_quarantine_tables(store)
    cur = store.db.execute(
        "UPDATE quarantine_envelopes SET active=0 WHERE repo=? AND envelope_id=?",
        (repo, envelope_id),
    )
    store.db.commit()
    return {
        "released": cur.rowcount > 0,
        "envelope_id": envelope_id,
        "claim_boundary": CLAIM,
    }
