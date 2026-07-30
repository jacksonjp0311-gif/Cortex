"""v6.25 Evidence Kernel — separate trusted retrieval path (Memory Simplex safe controller).

Does NOT import or call:
  retrieval.query, ranker, spectral, concept_routes, HNSW, fusion, structure_invent,
  embeddings similarity, neural synapses, discovery cards, prefetch.

Only host-derived indexed source/test/doc memories + structural edges + certificate.
Deterministic for the same evidence snapshot, query, and configuration.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from typing import Any

from . import __version__

SCHEMA = "cortex-evidence-kernel/1.0"
KERNEL_ID = "evidence_kernel_v1"
GLYPH = "◈E"

# Allowed memory kinds for trusted path
_ALLOWED_KINDS = frozenset(
    {
        "source",
        "code",
        "test",
        "documentation",
        "doc",
        "markdown",
        "file",
        "",
    }
)
_FORBIDDEN_KIND_SUBSTR = (
    "discovery",
    "card",
    "telemetry",
    "runtime",
    "episode",
    "summary",
    "distill",
    "prefetch",
    "fusion",
    "learned",
    "invented",
)

CLAIM = (
    "Evidence Kernel provides provenance-backed host evidence retrieval only. "
    "No adaptive machinery. Not consciousness. Not host mutation authority."
)


def _content_hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _tokens(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-zA-Z0-9_./\\-]+", (q or "").casefold()) if len(t) > 1]


def _kind_allowed(kind: str) -> bool:
    k = (kind or "").casefold()
    if k in _ALLOWED_KINDS:
        return True
    for bad in _FORBIDDEN_KIND_SUBSTR:
        if bad in k:
            return False
    # unknown kinds: allow only if looks like source path later
    return k in {"", "text", "chunk"}


def _path_forbidden(path: str) -> bool:
    p = (path or "").replace("\\", "/")
    if ".cortex/cards/" in p or p.startswith(".cortex/cards"):
        return True
    if "discovery" in p.casefold() and p.endswith(".md"):
        return True
    return False


def evidence_kernel_query(
    store: Any,
    repo: str,
    task: str,
    *,
    limit: int = 16,
    certificate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Trusted lexical retrieval over host evidence memories only."""
    t0 = time.time()
    cert = certificate or {}
    try:
        cert_row = store.latest_bootstrap(repo) if hasattr(store, "latest_bootstrap") else None
        if cert_row and not cert:
            try:
                cert = json.loads(cert_row["certificate"] or "{}")
            except Exception:
                cert = {}
    except Exception:
        cert = cert or {}

    repo_row = store.repo(repo) if hasattr(store, "repo") else None
    manifest_hash = ""
    if repo_row:
        try:
            manifest_hash = str(repo_row["manifest_hash"] or "")
        except Exception:
            manifest_hash = ""

    cert_status = str(cert.get("status") or "unknown")
    cert_id = str(cert.get("certificate_id") or cert.get("id") or cert_status)

    # Pure FTS / lexical via store — no semantic vectors, no ranker
    rows: list[Any] = []
    try:
        rows = list(store.lexical(repo, task, max(limit * 4, 40)) or [])
    except Exception as exc:
        return {
            "schema_version": SCHEMA,
            "glyph": GLYPH,
            "kernel_id": KERNEL_ID,
            "kernel_version": __version__,
            "ok": False,
            "error": f"lexical:{type(exc).__name__}:{exc}",
            "hits": [],
            "claim_boundary": CLAIM,
        }

    q_tokens = set(_tokens(task))
    scored: list[dict[str, Any]] = []
    for row in rows:
        try:
            kind = str(row["kind"] or "")
            path = str(row["path"] or "").replace("\\", "/")
            text = str(row["text"] or "")
            mid = int(row["id"] if "id" in row.keys() else row["memory_id"])
        except Exception:
            continue
        if not _kind_allowed(kind):
            continue
        if _path_forbidden(path):
            continue
        # score: exact path token + lexical overlap only
        path_l = path.casefold()
        text_l = text.casefold()
        score = 0.0
        for t in q_tokens:
            if t in path_l:
                score += 2.0
            if t in text_l:
                score += 0.35
        if score <= 0:
            continue
        # Prefer implementation-ish paths
        if path.endswith((".py", ".rs", ".ts", ".js", ".go", ".java")):
            score *= 1.15
        if "/test" in path_l or path_l.startswith("tests/"):
            score *= 1.05
        ch = str(row["content_hash"] or "") or _content_hash_text(text)
        scored.append(
            {
                "memory_id": mid,
                "path": path,
                "start_line": int(row["start_line"] or 0),
                "end_line": int(row["end_line"] or 0),
                "kind": kind,
                "score": round(score, 6),
                "content_hash": ch,
                "manifest_hash": manifest_hash,
                "certificate_id": cert_id,
                "certificate_status": cert_status,
                "selection_rule": "lexical_token_overlap_host_evidence",
                "controller_id": KERNEL_ID,
                "kernel_version": __version__,
                "text": text[:1200],
            }
        )
    scored.sort(key=lambda h: (-h["score"], h["path"], h["start_line"]))
    hits = scored[: max(1, int(limit))]

    # Optional structural neighborhood from edges table only (compiler-derived)
    structural: list[dict[str, Any]] = []
    try:
        paths = [h["path"] for h in hits[:8]]
        for p in paths:
            for erow in store.db.execute(
                """
                SELECT source, target, relation, confidence FROM edges
                WHERE repo=? AND (source=? OR target=?) LIMIT 6
                """,
                (repo, p, p),
            ).fetchall():
                structural.append(
                    {
                        "source": erow["source"],
                        "target": erow["target"],
                        "relation": erow["relation"],
                        "confidence": float(erow["confidence"] or 0),
                        "plane": "G_evidence",
                    }
                )
    except Exception:
        structural = []

    receipt = evidence_kernel_receipt(repo, task, hits, cert_status, manifest_hash)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "kernel_id": KERNEL_ID,
        "kernel_version": __version__,
        "ok": True,
        "repo": repo,
        "task": task,
        "hits": hits,
        "structural_neighborhood": structural[:24],
        "receipt": receipt,
        "elapsed_s": round(time.time() - t0, 4),
        "claim_boundary": CLAIM,
    }


def evidence_kernel_context(
    store: Any,
    repo: str,
    task: str,
    *,
    budget: int = 800,
    certificate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Flat-budget context packet from Evidence Kernel only."""
    q = evidence_kernel_query(store, repo, task, limit=20, certificate=certificate)
    hits = list(q.get("hits") or [])
    used = 0
    evidence: list[dict[str, Any]] = []
    for h in hits:
        # rough token estimate
        cost = max(20, len(str(h.get("text") or "")) // 4)
        if used + cost > int(budget):
            break
        evidence.append(
            {
                "memory_id": h.get("memory_id"),
                "path": h.get("path"),
                "line_range": [h.get("start_line"), h.get("end_line")],
                "kind": h.get("kind"),
                "score": h.get("score"),
                "content_hash": h.get("content_hash"),
                "text": h.get("text"),
                "metadata": {
                    "controller_id": KERNEL_ID,
                    "selection_rule": h.get("selection_rule"),
                    "certificate_status": h.get("certificate_status"),
                    "manifest_hash": h.get("manifest_hash"),
                },
            }
        )
        used += cost
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "controller": "evidence_baseline",
        "kernel_id": KERNEL_ID,
        "context_budget": int(budget),
        "estimated_tokens": used,
        "budget_partition": {
            "scheme": "flat",
            "pools": {"all": int(budget)},
            "used_by_level": {"all": used},
        },
        "evidence": evidence,
        "structural_neighborhood": q.get("structural_neighborhood") or [],
        "receipt": q.get("receipt"),
        "query": q,
        "claim_boundary": CLAIM,
    }


def evidence_kernel_receipt(
    repo: str,
    task: str,
    hits: list[dict[str, Any]],
    cert_status: str,
    manifest_hash: str,
) -> dict[str, Any]:
    material = json.dumps(
        {
            "repo": repo,
            "task": task,
            "paths": [h.get("path") for h in hits],
            "hashes": [h.get("content_hash") for h in hits],
            "cert": cert_status,
            "manifest": manifest_hash,
            "kernel": KERNEL_ID,
            "version": __version__,
        },
        sort_keys=True,
    )
    return {
        "schema_version": "cortex-evidence-kernel-receipt/1.0",
        "receipt_hash": hashlib.sha256(material.encode("utf-8")).hexdigest(),
        "kernel_id": KERNEL_ID,
        "kernel_version": __version__,
        "controller_id": KERNEL_ID,
        "n_hits": len(hits),
        "certificate_status": cert_status,
        "manifest_hash": manifest_hash,
        "claim_boundary": CLAIM,
    }
