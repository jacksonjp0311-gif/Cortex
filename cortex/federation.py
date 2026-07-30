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
    skip_geometry: bool = False,
    authority_ok: bool = True,
) -> dict[str, Any]:
    available = {row["name"] for row in store.repos()}
    selected = sorted(set(repositories or available))
    missing = sorted(set(selected) - available)
    if missing:
        raise ValueError(f"Unknown repositories: {', '.join(missing)}")

    # v7.1 constitutional geometry — federation admission per host
    # Denies individual hosts; still searches admitted set (partial admission).
    geometry_by_repo: dict[str, Any] = {}
    denied: list[str] = []
    if not skip_geometry:
        try:
            from .constitutional_path import assess_operation_at_boundary
            from .epoch import ensure_current_epoch

            for repo in selected:
                # Federation is a mutation-boundary admission: seal epoch if needed
                # so e/t can be evaluated; does not grant authority across repos.
                try:
                    ensure_current_epoch(store, repo, reason="federate_admission")
                except Exception:
                    pass
                g = assess_operation_at_boundary(
                    store,
                    repo,
                    "federate",
                    authority_ok=authority_ok,
                    require_witness=False,
                )
                geometry_by_repo[repo] = {
                    "allowed": g.get("allowed"),
                    "coordinate": g.get("coordinate"),
                    "missing_axes": g.get("missing_axes"),
                    "reasons": g.get("reasons"),
                    "required_legal_path": g.get("required_legal_path"),
                }
                if not g.get("allowed"):
                    denied.append(repo)
        except Exception as exc:
            geometry_by_repo["_error"] = f"{type(exc).__name__}:{exc}"

    admitted = [r for r in selected if r not in denied]
    if not admitted and selected and not skip_geometry:
        return {
            "protocol": "cortex-federation/1.1",
            "query": text,
            "repositories_searched": [],
            "repositories_represented": [],
            "boundary_preserved": True,
            "admission_denied": denied,
            "geometry": geometry_by_repo,
            "hits": [],
            "error": "constitutional_geometry_denied",
            "claim_boundary": (
                "Federation admission requires evidence+authority+epoch per host. "
                "Cross-repository similarity never merges repository identity."
            ),
        }
    ranked: list[dict[str, Any]] = []
    for repo in admitted:
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
    result = {
        "protocol": "cortex-federation/1.1",
        "query": text,
        "repositories_searched": admitted,
        "repositories_represented": represented,
        "boundary_preserved": all(item.get("boundary", {}).get("repository") for item in output),
        "ambiguous_repository_boundary": ambiguous,
        "recommended_action": "source-check" if ambiguous else "use ranked evidence",
        "hits": output,
        "claim_boundary": "Cross-repository similarity never merges repository identity or authority scope.",
    }
    if geometry_by_repo:
        result["geometry"] = geometry_by_repo
        result["admission_denied"] = denied
    return result
