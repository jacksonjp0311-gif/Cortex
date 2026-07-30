from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from .aria_meta.substrate import (
    INTERNAL_ARIA_PREFIX,
    aria_path_supports,
    aria_routing_purposes,
    classify_aria_task,
    is_internal_aria_path,
    load_aria_cue_profile,
)
from .embeddings import cosine, get_embedder, deserialize_vector
from .models import Hit

# Stop-ish tokens: too common to count as path/query stem overlap.
_PATH_MATCH_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "is",
        "py",
        "md",
        "json",
        "txt",
        "html",
        "js",
        "ts",
        "src",
        "lib",
        "test",
        "tests",
        "docs",
        "doc",
        "file",
        "path",
        "cortex",
        "examples",
        "memory",
        "packets",
    }
)

# When these appear in the query, prefer implementation paths over teach-mass packets.
_IMPL_QUERY_MARKERS = frozenset(
    {
        "fuse",
        "coprocess",
        "fuseproxy",
        "fuse_proxy",
        "mindhash",
        "mind_hash",
        "regenerate",
        "tick",
        "proxy",
        "laplacian",
        "lambda2",
        "spectral",
        "ranker",
        "ppr",
        "heat",
        "geometry",
    }
)


def reciprocal_rank_fusion(
    rankings: list[list[int]], weights: list[float] | None = None, k: int = 60
) -> dict[int, float]:
    weights = weights or [1.0] * len(rankings)
    scores: dict[int, float] = defaultdict(float)
    for ranking, weight in zip(rankings, weights):
        for rank, item in enumerate(ranking, 1):
            scores[item] += weight / (k + rank)
    return dict(scores)


def _token_stems(text: str) -> set[str]:
    """Tokenize path/query stems; keep both split and collapsed forms.

    ``co-process`` → {process, coprocess}; ``fuse_proxy`` → {fuse, proxy, fuseproxy}.
    """
    folded = text.casefold()
    split_parts = re.findall(
        r"[a-z0-9]+", folded.replace("-", " ").replace("_", " ")
    )
    collapsed = re.findall(
        r"[a-z0-9]{3,}", folded.replace("-", "").replace("_", "")
    )
    stems = {t for t in split_parts if len(t) >= 3 and t not in _PATH_MATCH_STOP}
    stems |= {t for t in collapsed if t not in _PATH_MATCH_STOP}
    return stems


def path_token_overlap(query: str, path: str) -> float:
    """0..1 overlap score of query stems with path/filename stems."""
    q = _token_stems(query)
    if not q:
        return 0.0
    path_n = path.replace("\\", "/")
    base = path_n.rsplit("/", 1)[-1]
    p_base = _token_stems(base)
    p_full = _token_stems(path_n.replace("/", " ").replace(".", " "))
    base_hits = len(q & p_base)
    full_hits = len(q & p_full)
    if base_hits == 0 and full_hits == 0:
        return 0.0
    # Basename hits dominate (module name in query beats ambient path noise).
    score = 0.55 * min(3, base_hits) + 0.20 * min(3, max(0, full_hits - base_hits))
    return min(1.0, score)


def path_token_quality_boost(query: str, path: str) -> float:
    """Quality multiplier (>=1) when path/filename stems appear in the query."""
    ov = path_token_overlap(query, path)
    if ov <= 0.0:
        return 1.0
    # Strong enough to outrank teach-mass ambient hits when the module is named.
    return 1.0 + 1.15 * ov


def query_has_impl_markers(text: str) -> bool:
    stems = _token_stems(text)
    # also check raw fold for multiword markers already collapsed
    folded = text.casefold().replace("-", "").replace("_", "")
    if any(m.replace("_", "") in folded for m in _IMPL_QUERY_MARKERS):
        return True
    return bool(stems & {m.replace("_", "") for m in _IMPL_QUERY_MARKERS})


def materialize_aria_for_task(store: Any, repo: str, text: str) -> dict[str, Any]:
    """Explicitly materialize deferred ARIA bulk when a task wakes the region.

    Must not be called from certificate retrieval probes: README headings that
    mention ARIA would otherwise eagerly index the entire language substrate
    during bootstrap verification and erase deferred-tier economics.
    """

    repository = store.repo(repo)
    if not repository:
        return {"mode": "unknown", "materialized": False, "reason": "repo_missing"}
    try:
        from .config import load_repo_config
        from .graph import resolve_graph
        from .indexer import ensure_aria_substrate_materialized
        from .neuron import compile_interlink

        config = load_repo_config(Path(repository["path"]))
        result = ensure_aria_substrate_materialized(store, repo, config, text)
        if result.get("materialized"):
            resolve_graph(store, repo)
            if config.neural_interlink_enabled:
                compile_interlink(store, repo)
        return result
    except FileNotFoundError:
        return {"mode": "unknown", "materialized": False, "reason": "config_missing"}


def query(
    store: Any,
    repo: str,
    text: str,
    limit: int = 8,
    semantic_scan_limit: int = 5000,
    *,
    materialize_substrate: bool = False,
    prove_implementation: bool = False,
    ranker_primary: bool = True,
    enrich_spectral: bool = True,
) -> list[Hit]:
    """Hybrid retrieval. Substrate materialization is opt-in (activation/CLI).

    prove_implementation: prefer substrate + cortex source/tests over discovery-card
    monopoly and vendor-guide domination (evidence selection, not authority).
    Activation enables this when ARIA is awake; bare verify probes do not, so
    host heading evidence (e.g. README) is not reordered away by prove mode.

    ranker_primary=False returns hybrid order only (measure-gate ablations).
    """

    if materialize_substrate:
        materialize_aria_for_task(store, repo, text)
    aria_profile = load_aria_cue_profile(store, repo)
    aria_classification = classify_aria_task(text, aria_profile["cues"])
    aria_active = aria_classification["mode"] == "active"
    aria_purposes = aria_routing_purposes(aria_classification)
    # Full prove reordering is opt-in (activation/CLI). ARIA-active alone still
    # boosts purpose-aligned substrate and runs the evidence floor, but does not
    # bury exact host matches used by bootstrap/verify heading probes.
    prove = bool(prove_implementation)
    excluded_prefixes = () if aria_active else (INTERNAL_ARIA_PREFIX,)
    lexical_rows = store.lexical(
        repo, text, 60, excluded_prefixes=excluded_prefixes
    )
    if aria_active:
        lexical_rows = [
            row
            for row in lexical_rows
            if not is_internal_aria_path(row["path"])
            or aria_path_supports(row["path"], aria_purposes)
        ]
    lexical_ids = [row["id"] for row in lexical_rows]

    query_vector = get_embedder().encode_one(text)
    store.ensure_vector_buckets(repo)
    # Optional HNSW lane (v5) — blends with LSH candidates when available.
    hnsw_ids: list[int] = []
    try:
        from .vectors import hnsw_status, query_hnsw

        if hnsw_status(store, repo).get("available"):
            for item in query_hnsw(store, repo, text, k=min(24, limit * 3)):
                mid = item.get("memory_id")
                if mid is not None:
                    hnsw_ids.append(int(mid))
    except Exception:
        hnsw_ids = []
    semantic: list[tuple[float, int]] = []
    seed = int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")
    for row in store.vector_candidates(
        repo,
        list(dict.fromkeys([*lexical_ids, *hnsw_ids])),
        limit=semantic_scan_limit,
        seed=seed,
        query_vector=query_vector,
        excluded_prefixes=excluded_prefixes,
    ):
        if (
            aria_active
            and is_internal_aria_path(row["path"])
            and not aria_path_supports(row["path"], aria_purposes)
        ):
            continue
        try:
            vector = deserialize_vector(row["vector"])
            similarity = cosine(query_vector, vector)
        except (TypeError, ValueError):
            continue
        semantic.append((similarity, row["id"]))
    semantic.sort(key=lambda item: item[0], reverse=True)
    semantic_ids = [memory_id for _, memory_id in semantic[:60]]

    fused = reciprocal_rank_fusion(
        [lexical_ids, semantic_ids, hnsw_ids] if hnsw_ids else [lexical_ids, semantic_ids],
        [1.0, 1.25, 1.15] if hnsw_ids else [1.0, 1.25],
    )
    semantic_lookup = {memory_id: similarity for similarity, memory_id in semantic[:100]}
    output: list[Hit] = []
    normalized_query = " ".join(text.casefold().split())
    for memory_id, base_score in sorted(fused.items(), key=lambda item: item[1], reverse=True):
        row = store.memory(memory_id)
        if not row:
            continue
        if is_internal_aria_path(row["path"]) and not aria_active:
            continue
        metadata = json.loads(row["metadata"] or "{}")
        quality = 1.0
        if metadata.get("authoritative"):
            quality *= 1.25
            if prove:
                quality *= 1.08
            # Exact authoritative match stays competitive even when ARIA substrate
            # is awake (verify probes + host claims).
            if (
                normalized_query
                and normalized_query in " ".join(row["text"].casefold().split())
            ):
                quality *= 1.20
        # Teaching mass: interconnect doctrine and memory packets rank up for
        # organism / protocol / teach tasks without becoming authority.
        path_norm = row["path"].replace("\\", "/")
        # Path/filename stem overlap — promote modules named in the query
        # (e.g. "fuse" / "coprocess" → cortex/fuse_proxy.py, cortex/coprocess.py).
        path_ov = path_token_overlap(text, path_norm)
        if path_ov > 0.0:
            quality *= path_token_quality_boost(text, path_norm)
            metadata["path_token_overlap"] = round(path_ov, 4)
        is_teach_mass = any(
            marker in path_norm
            for marker in (
                "docs/intelligence/",
                "docs/ORGANISM.md",
                "docs/TRANSCEND.md",
                "docs/COVENANT.md",
                "examples/memory-packets/",
                ".cortex/cards/",
            )
        )
        if is_teach_mass:
            teach_terms = (
                "organism",
                "interconnect",
                "protocol",
                "ritual",
                "teach",
                "covenant",
                "governor",
                "control error",
                "memory packet",
                "co-process",
                "aria",
            )
            if any(term in text.casefold() for term in teach_terms):
                # When the query is implementation-shaped (fuse/tick/spectral…),
                # do not let doctrine packets bury the modules they describe.
                if query_has_impl_markers(text) and not prove:
                    quality *= 0.92
                else:
                    quality *= 1.28 if not prove else 1.12
        if row["kind"] == "discovery_card":
            # Cards are retain-class memory; when proving ARIA/implementation,
            # do not let cards monopolize the packet over substrate source.
            quality *= 0.88 if prove else 1.12
        # Implementation + test proof lanes (still not mutation authority).
        if prove:
            is_test_path = (
                "/tests/" in path_norm
                or path_norm.startswith("tests/")
                or "/test_" in path_norm
                or path_norm.endswith(("_test.py", ".test.js", ".spec.ts", ".spec.js"))
                or row["kind"] == "test"
            )
            is_cortex_impl = (
                path_norm.startswith("cortex/")
                and path_norm.endswith((".py", ".pyi"))
                and not path_norm.startswith("cortex/aria_meta/vendor/")
            )
            if is_test_path:
                quality *= 1.32
                metadata["selection_source"] = (
                    metadata.get("selection_source") or "implementation_test_proof"
                )
            elif is_cortex_impl:
                quality *= 1.26
                metadata["selection_source"] = (
                    metadata.get("selection_source") or "implementation_proof"
                )
            # Prefer host source over vendor guides when proving.
            if path_norm.startswith("cortex/aria_meta/vendor/"):
                if "/docs/" in path_norm or "/plans/" in path_norm:
                    quality *= 0.78
                elif path_norm.endswith(".md") and not path_norm.endswith(
                    ("AGENTS.md",)
                ):
                    quality *= 0.86
        if aria_active and is_internal_aria_path(row["path"]):
            # Prefer purpose-aligned substrate evidence once the region is awake.
            # Anchors and purpose hits must outrank ambient host noise after wake.
            if aria_path_supports(row["path"], aria_purposes):
                quality *= 1.65 if prove else 1.55
            else:
                quality *= 1.22 if prove else 1.18
            if path_norm.endswith(
                (
                    "ARIA-RUNTIME.json",
                    "ARIA-CONNECT.json",
                    "semantic-cues.json",
                )
            ):
                quality *= 1.18
            elif path_norm.endswith(("README.md", "AGENTS.md")):
                # Anchors remain useful, but under prove they yield to tests/impl.
                quality *= 1.05 if prove else 1.15
            if "/docs/" in path_norm or "/plans/" in path_norm:
                # Vendor guides inform; they must not outrank tests/impl when proving.
                quality *= 0.82 if prove else 1.0
            metadata["selection_source"] = metadata.get("selection_source") or "aria_substrate"
        normalized_chunk = " ".join(row["text"].casefold().split())
        if normalized_query and normalized_query in normalized_chunk:
            quality *= 1.35
        if row["kind"] in {"discovery_card", "telemetry", "runtime_evidence"}:
            quality *= 0.98 if prove else 1.04
        telemetry = store.file_telemetry(repo, row["path"])
        if telemetry:
            frequency = telemetry[0]["commit_count"]
            quality *= 1.0 + min(0.12, math.log1p(frequency) / 30.0)
        score = base_score * quality
        metadata["semantic_similarity"] = round(semantic_lookup.get(memory_id, 0.0), 6)
        if prove:
            metadata["prove_implementation"] = True
        output.append(Hit(
            memory_id=memory_id,
            repo=row["repo"],
            path=row["path"],
            start_line=row["start_line"],
            end_line=row["end_line"],
            text=row["text"],
            kind=row["kind"],
            score=round(score, 8),
            content_hash=row["content_hash"],
            metadata=metadata,
        ))
    output.sort(key=lambda hit: (-hit.score, hit.path, hit.start_line))
    # Promote implementation paths cited as evidence in top teach/doctrine hits.
    output = _expand_evidence_paths(store, repo, output, limit=max(limit * 2, 24))
    # Hard paraphrases: concept routes map phrase clusters → modules (measure gate).
    output = _inject_concept_routes(store, repo, text, output, limit=max(limit * 2, 28))
    # Ranker-primary + spectral diffusion features (v6.13) — never authority.
    # Measure-gate sets ranker_primary=False to obtain raw hybrid for ablations.
    if ranker_primary:
        try:
            from .ranker.model import rerank_hits

            # Confidence proxy from top fused score mass
            top_scores = [float(h.score) for h in output[:8]] or [0.0]
            conf_proxy = max(0.0, min(1.0, sum(top_scores) / max(1, len(top_scores))))
            output = rerank_hits(
                store,
                repo,
                output,
                retrieval_confidence=conf_proxy,
                primary=True,
                enrich_spectral=bool(enrich_spectral),
            )
            # Keep rerank_hits order (includes soft pin for hybrid-prior winners).
            # Do not re-sort solely by ranker_score — that undoes prior pins.
        except Exception:
            pass
    floor = _aria_evidence_floor(
        store, repo, text, output, limit=limit, prove=prove
    )
    # Binary-intel pack domain boost (zero-in) — operational only.
    try:
        from .config import cortex_home
        from .packs.memory import boost_hits_for_domains, domain_route

        route = domain_route(cortex_home(), text)
        if route.get("packs"):
            floor = boost_hits_for_domains(floor, route)
            for hit in floor:
                try:
                    meta = hit.metadata if hasattr(hit, "metadata") else None
                    if isinstance(meta, dict):
                        meta["domain_route_top"] = route.get("top_domain")
                except Exception:
                    pass
    except Exception:
        pass
    return floor


_EVIDENCE_PATH_RE = re.compile(
    r"(?:^|[\s\"'`(\[,])((?:cortex|thalamus|docs|tests)/[A-Za-z0-9_./-]+\.(?:py|md|json))"
)


def _memory_hit_for_path(
    store: Any,
    repo: str,
    path: str,
    *,
    score: float,
    source: str,
    extra_meta: dict[str, Any] | None = None,
) -> Hit | None:
    """Build a Hit from the first memory chunk for path, if indexed."""
    path_n = path.replace("\\", "/")
    rows = []
    try:
        rows = store.memories_for_path(repo, path_n)
    except Exception:
        rows = []
    if not rows:
        try:
            rows = store.memories_for_path(repo, path_n.replace("/", "\\"))
        except Exception:
            rows = []
    if not rows:
        return None
    row = rows[0]
    try:
        meta = json.loads(row["metadata"] or "{}")
    except (TypeError, json.JSONDecodeError):
        meta = {}
    meta["selection_source"] = source
    if extra_meta:
        meta.update(extra_meta)
    return Hit(
        memory_id=int(row["id"]),
        repo=row["repo"],
        path=row["path"],
        start_line=row["start_line"],
        end_line=row["end_line"],
        text=row["text"],
        kind=row["kind"],
        score=round(float(score), 8),
        content_hash=row["content_hash"],
        metadata=meta,
    )


def _inject_concept_routes(
    store: Any,
    repo: str,
    text: str,
    hits: list[Hit],
    *,
    limit: int = 28,
) -> list[Hit]:
    """Inject/boost modules matched by frozen concept-route paraphrases."""
    try:
        from .concept_routes import match_concept_routes
    except Exception:
        return hits
    routes = match_concept_routes(text)
    if not routes:
        return hits
    top_score = float(hits[0].score) if hits else 0.05
    base_boost = max(0.08, top_score * 1.05)
    seen_paths = {str(h.path or "").replace("\\", "/") for h in hits}
    seen_ids = {int(h.memory_id) for h in hits if h.memory_id is not None}
    extras: list[Hit] = []
    boosted: list[Hit] = []
    # Boost existing hits that already match route paths
    route_paths = {
        str(p).replace("\\", "/")
        for r in routes
        for p in (r.get("paths") or [])
    }
    for h in hits:
        pn = str(h.path or "").replace("\\", "/")
        if pn in route_paths:
            try:
                md = dict(h.metadata or {})
                md["concept_route"] = True
                h.metadata = md
                h.score = round(max(float(h.score or 0.0), base_boost), 8)
            except Exception:
                pass
        boosted.append(h)
    for route in routes:
        for path in route.get("paths") or []:
            pn = str(path).replace("\\", "/")
            if pn in seen_paths:
                continue
            hit = _memory_hit_for_path(
                store,
                repo,
                pn,
                score=base_boost
                * (1.0 + 0.12 * min(5, int(route.get("score") or 1))),
                source="concept_route",
                extra_meta={
                    "concept_route_id": route.get("id"),
                    "matched_phrases": route.get("matched_phrases"),
                },
            )
            if hit is None:
                continue
            if int(hit.memory_id) in seen_ids:
                continue
            seen_ids.add(int(hit.memory_id))
            seen_paths.add(pn)
            extras.append(hit)
            if len(boosted) + len(extras) >= limit:
                break
        if len(boosted) + len(extras) >= limit:
            break
    if not extras and not any(
        (h.metadata or {}).get("concept_route") for h in boosted
    ):
        return hits
    merged = boosted + extras
    # Surgical neighbor damp: when operator_a or host_mesh route fires hard,
    # prefer the target module over close spectral/docs distractors (v6.18.1).
    route_ids = {str(r.get("id") or "") for r in routes}
    if "operator_a" in route_ids:
        for h in merged:
            pn = str(h.path or "").replace("\\", "/")
            try:
                if pn.endswith("math_net/operator.py") or "/operator.py" in pn:
                    h.score = round(float(h.score or 0.0) * 1.22, 8)
                elif "spectral" in pn and "operator" not in pn:
                    h.score = round(float(h.score or 0.0) * 0.82, 8)
            except Exception:
                pass
    if "host_mesh" in route_ids:
        for h in merged:
            pn = str(h.path or "").replace("\\", "/")
            try:
                if pn.endswith("host_mesh.py") or "/host_mesh.py" in pn:
                    h.score = round(float(h.score or 0.0) * 1.25, 8)
            except Exception:
                pass
    merged.sort(key=lambda h: (-float(h.score or 0.0), h.path, h.start_line))
    return merged


def _expand_evidence_paths(
    store: Any,
    repo: str,
    hits: list[Hit],
    *,
    limit: int = 24,
) -> list[Hit]:
    """If top hits cite implementation paths (teach packets/cards), inject those files.

    Turns doctrine evidence strings into retrievable source paths so measure-gate
    and agents land on modules, not only the packet/card that names them.
    """
    if not hits:
        return hits
    seen_paths = {str(h.path or "").replace("\\", "/") for h in hits}
    seen_ids = {int(h.memory_id) for h in hits if h.memory_id is not None}
    extras: list[Hit] = []
    for hit in hits[:14]:
        blob = f"{hit.path or ''}\n{hit.text or ''}"
        cited = _EVIDENCE_PATH_RE.findall(blob)
        for raw in cited:
            path = raw.replace("\\", "/").lstrip("./")
            if path in seen_paths:
                continue
            parent_score = float(hit.score or 0.0)
            extra = _memory_hit_for_path(
                store,
                repo,
                path,
                score=parent_score * 0.97,
                source="evidence_expansion",
                extra_meta={"expanded_from": str(hit.path or "")},
            )
            if extra is None:
                continue
            mid = int(extra.memory_id)
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            seen_paths.add(path)
            extras.append(extra)
            if len(hits) + len(extras) >= limit:
                break
        if len(hits) + len(extras) >= limit:
            break
    if not extras:
        return hits
    merged = list(hits) + extras
    merged.sort(key=lambda h: (-float(h.score or 0.0), h.path, h.start_line))
    return merged


def _aria_evidence_floor(
    store: Any,
    repo: str,
    text: str,
    hits: list[Hit],
    *,
    limit: int,
    prove: bool = False,
) -> list[Hit]:
    """When ARIA is awake, ensure a minimum of substrate evidence in the ranking."""

    aria_profile = load_aria_cue_profile(store, repo)
    classification = classify_aria_task(text, aria_profile["cues"])
    if classification["mode"] != "active":
        return hits
    purposes = aria_routing_purposes(classification)
    existing_ids = {hit.memory_id for hit in hits}
    aria_hits = [hit for hit in hits if is_internal_aria_path(hit.path)]
    # When proving implementation, require stronger substrate floor (not cards alone).
    min_aria = 3 if prove else 2
    if len(aria_hits) >= min_aria and not prove:
        return hits[:limit]
    if prove and len(aria_hits) >= min_aria:
        # Rebalance under prove: tests/impl → anchors → other → vendor docs → cards
        def _proof_rank(h: Hit) -> int:
            p = h.path.replace("\\", "/")
            if (
                "/tests/" in p
                or p.startswith("tests/")
                or "/test_" in p
                or p.endswith(("_test.py", ".test.js", ".spec.ts", ".spec.js"))
                or h.kind == "test"
            ):
                return 0
            if (
                p.startswith("cortex/")
                and p.endswith((".py", ".pyi"))
                and "aria_meta/vendor" not in p
            ):
                return 1
            if is_internal_aria_path(h.path) and p.endswith(
                ("ARIA-RUNTIME.json", "ARIA-CONNECT.json", "semantic-cues.json")
            ):
                return 2
            if is_internal_aria_path(h.path) and (
                "/docs/" in p or "/plans/" in p or p.endswith(".md")
            ):
                return 5
            if h.kind == "discovery_card":
                return 6
            if is_internal_aria_path(h.path):
                return 3
            return 4

        ordered = sorted(
            hits,
            key=lambda h: (_proof_rank(h), -float(h.score), h.path, h.start_line),
        )
        return ordered[:limit]

    extras: list[Hit] = []
    # Direct lexical scan with ARIA included (no excluded prefix).
    lexical_rows = store.lexical(repo, text, 40, excluded_prefixes=())
    for row in lexical_rows:
        if row["id"] in existing_ids:
            continue
        if not is_internal_aria_path(row["path"]):
            continue
        if not aria_path_supports(row["path"], purposes):
            # Still admit anchors as floor evidence.
            normalized = row["path"].replace("\\", "/")
            if not normalized.endswith(
                (
                    "ARIA-RUNTIME.json",
                    "ARIA-CONNECT.json",
                    "README.md",
                    "semantic-cues.json",
                    "AGENTS.md",
                )
            ) and "docs/" not in normalized and "plans/" not in normalized:
                continue
        full = store.memory(row["id"])
        if not full:
            continue
        metadata = json.loads(full["metadata"] or "{}")
        metadata["selection_source"] = "aria_evidence_floor"
        extras.append(
            Hit(
                memory_id=full["id"],
                repo=full["repo"],
                path=full["path"],
                start_line=full["start_line"],
                end_line=full["end_line"],
                text=full["text"],
                kind=full["kind"],
                score=round(0.85 + 0.01 * len(extras), 8),
                content_hash=full["content_hash"],
                metadata=metadata,
            )
        )
        existing_ids.add(full["id"])
        if len(aria_hits) + len(extras) >= 3:
            break
    # Prefer substrate anchors + purpose docs when proving ARIA.
    extras.sort(
        key=lambda h: (
            0
            if h.path.replace("\\", "/").endswith(
                ("ARIA-RUNTIME.json", "ARIA-CONNECT.json", "semantic-cues.json")
            )
            else 1
            if "/docs/" in h.path.replace("\\", "/")
            else 2
        )
    )
    if len(aria_hits) + len(extras) < 2:
        for file_row in store.files(repo):
            path = file_row["path"]
            if file_row["status"] != "indexed" or not is_internal_aria_path(path):
                continue
            if not (
                aria_path_supports(path, purposes)
                or path.replace("\\", "/").endswith(
                    (
                        "ARIA-RUNTIME.json",
                        "ARIA-CONNECT.json",
                        "README.md",
                        "semantic-cues.json",
                    )
                )
            ):
                continue
            for full in store.memories_for_path(repo, path)[:1]:
                if full["id"] in existing_ids:
                    continue
                metadata = json.loads(full["metadata"] or "{}")
                metadata["selection_source"] = "aria_evidence_floor_path"
                extras.append(
                    Hit(
                        memory_id=full["id"],
                        repo=full["repo"],
                        path=full["path"],
                        start_line=full["start_line"],
                        end_line=full["end_line"],
                        text=full["text"],
                        kind=full["kind"],
                        score=round(0.8 + 0.01 * len(extras), 8),
                        content_hash=full["content_hash"],
                        metadata=metadata,
                    )
                )
                existing_ids.add(full["id"])
                if len(aria_hits) + len(extras) >= 3:
                    break
            if len(aria_hits) + len(extras) >= 3:
                break
    merged = list(hits) + extras
    merged.sort(key=lambda hit: (-hit.score, hit.path, hit.start_line))
    return merged[:limit]


def support_hits(
    store: Any,
    repo: str,
    text: str,
    paths: list[str] | tuple[str, ...],
    limit: int = 12,
) -> list[Hit]:
    """Select the most task-relevant chunk from each neural support path."""

    query_vector = get_embedder().encode_one(text)
    candidates: list[Hit] = []
    for path in paths:
        best: Hit | None = None
        for row in store.memories_for_path(repo, path):
            try:
                vector = deserialize_vector(row["vector"]) if row["vector"] else []
                similarity = cosine(query_vector, vector)
            except (TypeError, ValueError):
                similarity = 0.0
            metadata = json.loads(row["metadata"] or "{}")
            metadata["semantic_similarity"] = round(similarity, 6)
            metadata["selection_source"] = "neural_interlink"
            quality = 1.10 if metadata.get("authoritative") else 1.0
            score = (0.5 + max(0.0, similarity)) * quality
            hit = Hit(
                memory_id=row["id"],
                repo=row["repo"],
                path=row["path"],
                start_line=row["start_line"],
                end_line=row["end_line"],
                text=row["text"],
                kind=row["kind"],
                score=round(score, 8),
                content_hash=row["content_hash"],
                metadata=metadata,
            )
            if best is None or hit.score > best.score or (
                hit.score == best.score and hit.start_line < best.start_line
            ):
                best = hit
        if best is not None:
            candidates.append(best)
    candidates.sort(key=lambda hit: (-hit.score, hit.path, hit.start_line))
    return candidates[:limit]
