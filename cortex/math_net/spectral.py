"""M4 — True spectral slice: L, λ₂ estimate, heat e^{-tL}s, edge underuse."""

from __future__ import annotations

from typing import Any

from .linalg import fiedler_inverse_iteration, heat_apply
from .operator import build_operator_A

SCHEMA = "cortex-spectral/1.0"


def spectral_slice(
    store: Any,
    repo: str,
    seed_node_ids: list[str] | None = None,
    *,
    max_nodes: int = 250,
    t_heat: float = 0.75,
) -> dict[str, Any]:
    op = build_operator_A(store, repo, max_nodes=max_nodes)
    n = int(op["n"])
    if n <= 1:
        return {
            "schema_version": SCHEMA,
            "ok": False,
            "reason": "graph_too_small",
            "n": n,
            "lambda2": 0.0,
        }

    lam2, fiedler = fiedler_inverse_iteration(
        n, op["L_rows"], op["degrees"], iters=40
    )
    index: dict[str, int] = op["index"]
    node_ids: list[str] = op["node_ids"]
    seeds = [index[s] for s in (seed_node_ids or []) if s in index]
    if not seeds:
        seeds = [max(range(n), key=lambda i: op["degrees"][i])]

    s = [0.0] * n
    for i in seeds:
        s[i] = 1.0 / len(seeds)
    heat = heat_apply(n, op["L_rows"], s, t_heat, steps=14)

    # Edge underuse: low weight * low heat on endpoints * zero update_count if available
    underuse: list[dict[str, Any]] = []
    syn_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        for row in store.neural_synapses(repo) or []:
            a, b = str(row["source_id"]), str(row["target_id"])
            key = (a, b) if a < b else (b, a)
            syn_by_pair[key] = {
                "weight": float(row["weight"] or 0),
                "update_count": int(row["update_count"] or 0),
                "synapse_id": row["synapse_id"],
            }
    except Exception:
        pass

    for e in op["edges"]:
        a, b = e["source_id"], e["target_id"]
        ia, ib = index.get(a), index.get(b)
        if ia is None or ib is None:
            continue
        h = 0.5 * (heat[ia] + heat[ib])
        meta = syn_by_pair.get((a, b) if a < b else (b, a), {})
        w = float(e["weight"])
        updates = int(meta.get("update_count") or 0)
        # high underuse score => candidate for decay attention
        score = (1.0 / (1.0 + 10.0 * h)) * (1.0 / (1.0 + 5.0 * w)) * (1.0 if updates == 0 else 0.4)
        underuse.append(
            {
                "source_id": a,
                "target_id": b,
                "weight": round(w, 6),
                "heat_endpoints": round(h, 8),
                "update_count": updates,
                "underuse_score": round(score, 8),
                "synapse_id": meta.get("synapse_id"),
            }
        )
    underuse.sort(key=lambda r: r["underuse_score"], reverse=True)

    return {
        "schema_version": SCHEMA,
        "ok": True,
        "repo": repo,
        "n": n,
        "edge_count": op["edge_count"],
        "lambda2": round(lam2, 8),
        "algebraic_connectivity": round(lam2, 8),
        "fiedler_sample": [
            {"node_id": node_ids[i], "value": round(fiedler[i], 6)}
            for i in sorted(range(n), key=lambda i: abs(fiedler[i]), reverse=True)[:8]
        ],
        "t_heat": t_heat,
        "heat_top": [
            {"node_id": node_ids[i], "heat": round(heat[i], 8)}
            for i in sorted(range(n), key=lambda i: heat[i], reverse=True)[:12]
        ],
        "edge_underuse_top": underuse[:20],
        "is_spectral": True,
        "claim_boundary": (
            "λ2 via projected power iteration is approximate; dense eigendecomposition "
            "not required for telemetry. This is true spectral content (L-based)."
        ),
    }
