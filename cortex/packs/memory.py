"""Index pack cards into Cortex SQLite memory + domain zero-in/expand."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..embeddings import get_embedder
from .format import (
    GLYPH,
    expand_threshold,
    score_task_against_domains,
)
from .store import list_packs, load_pack, packs_root


def pack_memory_prefix(pack_id: str) -> str:
    return f"cortex-packs/{pack_id}/"


def index_packs_into_repo(
    store: Any,
    home: Path,
    repo: str,
    *,
    pack_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Upsert installed pack cards as searchable memories for a repository."""

    listed = list_packs(home)
    targets = pack_ids or [
        p["id"] for p in listed.get("packs") or [] if p.get("id") and not p.get("error")
    ]
    embedder = get_embedder()
    indexed = 0
    for pack_id in targets:
        try:
            pack = load_pack(home, pack_id)
        except Exception:
            continue
        man = pack["manifest"]
        for card in pack["cards"]:
            rel = card["path"]
            mem_path = pack_memory_prefix(pack_id) + rel
            text = card["text"]
            content_hash = card["sha256"]
            # remove old chunks for path
            try:
                store.remove_path(repo, mem_path)
            except Exception:
                pass
            # chunk large cards
            lines = text.splitlines()
            chunk_size = 80
            for i in range(0, max(1, len(lines)), chunk_size):
                chunk_lines = lines[i : i + chunk_size]
                chunk_text = "\n".join(chunk_lines)
                if not chunk_text.strip():
                    continue
                start = i + 1
                end = i + len(chunk_lines)
                store.upsert_memory(
                    repo=repo,
                    path=mem_path,
                    chunk_index=i // chunk_size,
                    start_line=start,
                    end_line=end,
                    kind="intelligence_pack",
                    text=chunk_text,
                    content_hash=hashlib_sha(chunk_text + content_hash),
                    vector=embedder.encode_one(chunk_text),
                    embedding_model=embedder.name,
                    metadata={
                        "pack_id": pack_id,
                        "pack_version": man.get("version"),
                        "domains": man.get("domains"),
                        "selection_source": "binary_intel_pack",
                        "authoritative": False,
                        "card": rel,
                        "glyph": GLYPH,
                    },
                )
                indexed += 1
        # register pack in settings
        store.set_setting(
            f"pack_indexed:{repo}:{pack_id}",
            {
                "at": time.time(),
                "domains": man.get("domains"),
                "version": man.get("version"),
            },
        )
    try:
        store.commit()
    except Exception:
        pass
    store.set_setting(
        f"packs_indexed_at:{repo}",
        {"at": time.time(), "pack_ids": targets, "chunks": indexed},
    )
    return {
        "schema_version": "cortex-pack-index/1.0",
        "glyph": GLYPH,
        "repo": repo,
        "pack_ids": targets,
        "chunks_indexed": indexed,
        "claim_boundary": (
            "Pack index is searchable memory; cards are not host source authority."
        ),
    }


def hashlib_sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def domain_route(
    home: Path,
    task: str,
    *,
    pack_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Aggregate domain scores across installed packs (zero-in)."""

    listed = list_packs(home)
    packs = [
        p for p in (listed.get("packs") or []) if p.get("id") and not p.get("error")
    ]
    if pack_ids:
        packs = [p for p in packs if p["id"] in pack_ids]
    per_pack: list[dict[str, Any]] = []
    domain_best: dict[str, float] = {}
    for p in packs:
        try:
            loaded = load_pack(home, p["id"])
        except Exception as exc:
            per_pack.append({"pack_id": p["id"], "error": str(exc)})
            continue
        man = loaded["manifest"]
        scores = score_task_against_domains(
            task, list(man.get("domains") or []), binary=loaded.get("binary")
        )
        top = scores[0] if scores else {"domain": "general", "score": 0.0}
        for s in scores:
            d = s["domain"]
            domain_best[d] = max(domain_best.get(d, 0.0), float(s["score"]))
        per_pack.append(
            {
                "pack_id": p["id"],
                "version": man.get("version"),
                "top_domain": top.get("domain"),
                "top_score": top.get("score"),
                "expand": expand_threshold(float(top.get("score") or 0.0)),
                "scores": scores[:6],
            }
        )
    ranked_domains = sorted(
        ({"domain": d, "score": s} for d, s in domain_best.items()),
        key=lambda item: (-item["score"], item["domain"]),
    )
    top_score = float(ranked_domains[0]["score"]) if ranked_domains else 0.0
    return {
        "schema_version": "cortex-domain-route/1.0",
        "glyph": GLYPH,
        "task": task,
        "packs": per_pack,
        "domains": ranked_domains[:12],
        "top_domain": ranked_domains[0]["domain"] if ranked_domains else None,
        "top_score": top_score,
        "expand": expand_threshold(top_score),
        "packs_root": str(packs_root(home)),
        "claim_boundary": (
            "Domain route is zero-in geometry; expand loads pack cards, not host rights."
        ),
    }


def pack_surface_for_packet(
    home: Path,
    store: Any,
    repo: str,
    task: str,
) -> dict[str, Any]:
    """Lean pack surface for activate packets — extension of Cortex memory."""

    route = domain_route(home, task)
    # Auto-index if packs installed but never indexed for this repo
    marker = store.get_setting(f"packs_indexed_at:{repo}", None)
    listed = list_packs(home)
    if (listed.get("count") or 0) > 0 and not marker:
        try:
            index_packs_into_repo(store, home, repo)
        except Exception as exc:
            route["index_error"] = f"{type(exc).__name__}: {exc}"
    expand = bool(route.get("expand"))
    expanded_cards: list[dict[str, Any]] = []
    if expand:
        # pull top domain cards into surface (text capped)
        for p in route.get("packs") or []:
            if not p.get("expand"):
                continue
            try:
                loaded = load_pack(home, p["pack_id"])
            except Exception:
                continue
            for card in (loaded.get("cards") or [])[:2]:
                expanded_cards.append(
                    {
                        "pack_id": p["pack_id"],
                        "path": pack_memory_prefix(p["pack_id"]) + card["path"],
                        "domain": p.get("top_domain"),
                        "text": (card.get("text") or "")[:1200],
                        "selection_source": "binary_intel_expand",
                    }
                )
            if len(expanded_cards) >= 4:
                break
    return {
        **route,
        "indexed": bool(store.get_setting(f"packs_indexed_at:{repo}", None)),
        "expanded_cards": expanded_cards,
        "memory_prefix": "cortex-packs/",
        "doctrine": (
            "▣ packs are Cortex memory branches: zero-in by domain binary field, "
            "expand cards when mass coheres, never mutation authority."
        ),
    }


def boost_hits_for_domains(
    hits: list[Any],
    domain_route_result: dict[str, Any],
) -> list[Any]:
    """Operational reordering: boost intelligence_pack hits in active domains."""

    if not hits or not domain_route_result.get("expand"):
        # still mild boost if any domain score > 0.5
        pass
    top = float(domain_route_result.get("top_score") or 0.0)
    active = {
        d["domain"]
        for d in (domain_route_result.get("domains") or [])
        if float(d.get("score") or 0.0) >= 0.5
    }
    if not active and top < 0.5:
        return hits
    scored: list[tuple[float, Any]] = []
    for hit in hits:
        if isinstance(hit, dict):
            path = str(hit.get("path") or "").replace("\\", "/")
            kind = str(hit.get("kind") or "")
            score = float(hit.get("score") or 0.0)
            meta = hit.get("metadata") or {}
        else:
            path = str(getattr(hit, "path", "") or "").replace("\\", "/")
            kind = str(getattr(hit, "kind", "") or "")
            score = float(getattr(hit, "score", 0.0) or 0.0)
            meta = getattr(hit, "metadata", None) or {}
        mult = 1.0
        if path.startswith("cortex-packs/") or kind == "intelligence_pack":
            mult *= 1.18 if domain_route_result.get("expand") else 1.08
            domains = meta.get("domains") or []
            if isinstance(domains, list) and active.intersection(
                {str(x).casefold() for x in domains}
            ):
                mult *= 1.22
            if meta.get("selection_source") == "binary_intel_pack":
                mult *= 1.05
        scored.append((score * mult, hit))
    scored.sort(
        key=lambda item: (
            -item[0],
            str(
                item[1].get("path")
                if isinstance(item[1], dict)
                else getattr(item[1], "path", "")
            ),
        )
    )
    # write back adjusted scores on Hit objects when possible
    out: list[Any] = []
    for new_score, hit in scored:
        if isinstance(hit, dict):
            hit = {**hit, "score": round(new_score, 8)}
            meta = dict(hit.get("metadata") or {})
            meta["pack_domain_boost"] = True
            hit["metadata"] = meta
        else:
            try:
                hit.score = round(new_score, 8)
                meta = dict(hit.metadata or {})
                meta["pack_domain_boost"] = True
                hit.metadata = meta
            except Exception:
                pass
        out.append(hit)
    return out
