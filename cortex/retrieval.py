from __future__ import annotations

import hashlib
import json
import math
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


def reciprocal_rank_fusion(
    rankings: list[list[int]], weights: list[float] | None = None, k: int = 60
) -> dict[int, float]:
    weights = weights or [1.0] * len(rankings)
    scores: dict[int, float] = defaultdict(float)
    for ranking, weight in zip(rankings, weights):
        for rank, item in enumerate(ranking, 1):
            scores[item] += weight / (k + rank)
    return dict(scores)


def _materialize_aria_if_needed(store: Any, repo: str, text: str) -> None:
    """On ARIA wake, materialize deferred substrate before hybrid retrieval."""

    aria_profile = load_aria_cue_profile(store, repo)
    if classify_aria_task(text, aria_profile["cues"])["mode"] != "active":
        return
    repository = store.repo(repo)
    if not repository:
        return
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
    except FileNotFoundError:
        return


def query(store: Any, repo: str, text: str, limit: int = 8, semantic_scan_limit: int = 5000) -> list[Hit]:
    _materialize_aria_if_needed(store, repo, text)
    aria_profile = load_aria_cue_profile(store, repo)
    aria_classification = classify_aria_task(text, aria_profile["cues"])
    aria_active = aria_classification["mode"] == "active"
    aria_purposes = aria_routing_purposes(aria_classification)
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
    semantic: list[tuple[float, int]] = []
    seed = int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big")
    for row in store.vector_candidates(
        repo,
        lexical_ids,
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

    fused = reciprocal_rank_fusion([lexical_ids, semantic_ids], [1.0, 1.25])
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
        normalized_chunk = " ".join(row["text"].casefold().split())
        if normalized_query and normalized_query in normalized_chunk:
            quality *= 1.35
        if row["kind"] in {"discovery_card", "telemetry", "runtime_evidence"}:
            quality *= 1.04
        telemetry = store.file_telemetry(repo, row["path"])
        if telemetry:
            frequency = telemetry[0]["commit_count"]
            quality *= 1.0 + min(0.12, math.log1p(frequency) / 30.0)
        score = base_score * quality
        metadata["semantic_similarity"] = round(semantic_lookup.get(memory_id, 0.0), 6)
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
    return output[:limit]


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
