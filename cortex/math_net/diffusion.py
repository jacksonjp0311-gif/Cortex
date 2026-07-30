"""M3 — Propagation v2: Personalized PageRank / heat features on A."""

from __future__ import annotations

from typing import Any

from .linalg import heat_apply, personalized_pagerank
from .operator import build_operator_A

SCHEMA = "cortex-diffusion/1.0"


def diffusion_features(
    store: Any,
    repo: str,
    seed_node_ids: list[str] | None = None,
    *,
    max_nodes: int = 300,
    t_heat: float = 0.5,
) -> dict[str, Any]:
    """Compute PPR and heat scores for seed set; map back to node_ids."""
    op = build_operator_A(store, repo, max_nodes=max_nodes)
    n = int(op["n"])
    if n == 0:
        return {
            "schema_version": SCHEMA,
            "ok": False,
            "reason": "empty_operator",
            "by_node": {},
        }
    index: dict[str, int] = op["index"]
    node_ids: list[str] = op["node_ids"]
    seeds = [index[s] for s in (seed_node_ids or []) if s in index]
    if not seeds:
        # top-degree seeds
        degrees = op["degrees"]
        order = sorted(range(n), key=lambda i: degrees[i], reverse=True)[: min(5, n)]
        seeds = order

    ppr = personalized_pagerank(n, op["adj_rows"], seeds, alpha=0.85, iters=25)
    s = [0.0] * n
    for i in seeds:
        s[i] = 1.0 / len(seeds)
    heat = heat_apply(n, op["L_rows"], s, t_heat, steps=10)

    by_node: dict[str, dict[str, float]] = {}
    for i, nid in enumerate(node_ids):
        by_node[nid] = {
            "ppr": round(ppr[i], 8),
            "heat": round(heat[i], 8),
            "degree": round(float(op["degrees"][i]), 6),
        }

    # centrality proxy: degree normalized
    max_d = max(op["degrees"]) or 1.0
    for nid, feats in by_node.items():
        feats["degree_centrality"] = round(feats["degree"] / max_d, 6)

    return {
        "schema_version": SCHEMA,
        "ok": True,
        "repo": repo,
        "n": n,
        "seed_indices": seeds,
        "seed_node_ids": [node_ids[i] for i in seeds],
        "t_heat": t_heat,
        "by_node": by_node,
        "top_ppr": sorted(
            ({"node_id": k, **v} for k, v in by_node.items()),
            key=lambda r: r["ppr"],
            reverse=True,
        )[:12],
        "claim_boundary": (
            "Diffusion features for ranker/activation; shallow fire remains budgeted."
        ),
    }
