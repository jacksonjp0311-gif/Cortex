"""Boundary-preserving retrieval across attached repositories."""

from __future__ import annotations

from typing import Any, Iterable

from .retrieval import query


def federated_query(
    store: Any,
    text: str,
    *,
    repositories: Iterable[str] | None = None,
    limit: int = 12,
    per_repo: int = 8,
    semantic_scan_limit: int = 5000,
) -> dict[str, Any]:
    available = {row["name"] for row in store.repos()}
    selected = sorted(set(repositories or available))
    missing = sorted(set(selected) - available)
    if missing:
        raise ValueError(f"Unknown repositories: {', '.join(missing)}")

    ranked: list[dict[str, Any]] = []
    for repo in selected:
        hits = query(
            store,
            repo,
            text,
            limit=max(1, per_repo),
            semantic_scan_limit=semantic_scan_limit,
        )
        maximum = max((hit.score for hit in hits), default=1.0) or 1.0
        for rank, hit in enumerate(hits, 1):
            normalized = hit.score / maximum
            semantic = max(0.0, float(hit.metadata.get("semantic_similarity", 0.0)))
            score = 0.45 * normalized + 0.25 / rank + 0.30 * min(1.0, semantic)
            item = hit.to_dict()
            item["boundary"] = {
                "repository": repo,
                "repository_id": store.repo(repo)["repository_id"],
                "cross_repository": len(selected) > 1,
            }
            item["federated_score"] = round(score, 8)
            item["local_rank"] = rank
            ranked.append(item)
    ranked.sort(
        key=lambda item: (
            -item["federated_score"],
            item["boundary"]["repository"],
            item["path"],
            item["start_line"],
        )
    )
    output = ranked[: max(1, limit)]
    represented = sorted({item["boundary"]["repository"] for item in output})
    top_scores = [item["federated_score"] for item in output[:2]]
    ambiguous = (
        len(output) >= 2
        and output[0]["boundary"]["repository"] != output[1]["boundary"]["repository"]
        and abs(top_scores[0] - top_scores[1]) < 0.03
    )
    return {
        "protocol": "cortex-federation/1.0",
        "query": text,
        "repositories_searched": selected,
        "repositories_represented": represented,
        "boundary_preserved": all(item.get("boundary", {}).get("repository") for item in output),
        "ambiguous_repository_boundary": ambiguous,
        "recommended_action": "source-check" if ambiguous else "use ranked evidence",
        "hits": output,
        "claim_boundary": "Cross-repository similarity never merges repository identity or authority scope.",
    }
