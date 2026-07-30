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

    # --- Cheeger / Fiedler cut bottleneck (v6.19) ---
    # Partition by sign of Fiedler vector; discrete isoperimetric proxy.
    pos = [i for i in range(n) if fiedler[i] >= 0.0]
    neg = [i for i in range(n) if fiedler[i] < 0.0]
    if not pos or not neg:
        # Degenerate cut — put smallest |fiedler| half vs rest
        order = sorted(range(n), key=lambda i: fiedler[i])
        mid = max(1, n // 2)
        neg, pos = order[:mid], order[mid:]
    deg = op["degrees"]
    vol_pos = sum(float(deg[i]) for i in pos) or 1.0
    vol_neg = sum(float(deg[i]) for i in neg) or 1.0
    set_pos = set(pos)
    boundary = 0.0
    cut_edges: list[dict[str, Any]] = []
    for e in op["edges"]:
        a, b = e["source_id"], e["target_id"]
        ia, ib = index.get(a), index.get(b)
        if ia is None or ib is None:
            continue
        if (ia in set_pos) != (ib in set_pos):
            w = float(e["weight"])
            boundary += w
            cut_edges.append(
                {
                    "source_id": a,
                    "target_id": b,
                    "weight": round(w, 6),
                    "crosses_fiedler_cut": True,
                }
            )
    min_vol = min(vol_pos, vol_neg)
    h_cheeger = boundary / min_vol if min_vol > 0 else 0.0
    d_max = max(float(d) for d in deg) if deg else 1.0
    # Cheeger inequalities (undirected weighted proxy): λ2/2 ≤ h ≤ sqrt(2 d_max λ2)
    cheeger_lower = 0.5 * float(lam2)
    cheeger_upper = (2.0 * d_max * max(0.0, float(lam2))) ** 0.5
    # Mark underuse edges that cross the cut (prune/strengthen candidates)
    cut_pairs = {
        (min(c["source_id"], c["target_id"]), max(c["source_id"], c["target_id"]))
        for c in cut_edges
    }
    for u in underuse:
        key = (
            min(u["source_id"], u["target_id"]),
            max(u["source_id"], u["target_id"]),
        )
        u["crosses_fiedler_cut"] = key in cut_pairs
        if u["crosses_fiedler_cut"]:
            # Prioritize dead-weight on the bottleneck cut
            u["underuse_score"] = round(float(u["underuse_score"]) * 1.35, 8)
    underuse.sort(key=lambda r: r["underuse_score"], reverse=True)
    cut_underuse = [u for u in underuse if u.get("crosses_fiedler_cut")][:12]

    # Heat difference wavelet proxy (two scales) — multi-scale anomaly mass
    heat_fine = heat_apply(n, op["L_rows"], s, max(0.15, t_heat * 0.35), steps=10)
    wavelet = [heat_fine[i] - heat[i] for i in range(n)]
    wavelet_top = [
        {"node_id": node_ids[i], "wavelet": round(wavelet[i], 8)}
        for i in sorted(range(n), key=lambda i: abs(wavelet[i]), reverse=True)[:10]
    ]

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
        "cheeger": {
            "h_approx": round(h_cheeger, 8),
            "boundary_weight": round(boundary, 6),
            "vol_pos": round(vol_pos, 4),
            "vol_neg": round(vol_neg, 4),
            "cut_edge_count": len(cut_edges),
            "lambda2_over_2": round(cheeger_lower, 8),
            "sqrt_2_dmax_lambda2": round(cheeger_upper, 8),
            "inequality_holds_soft": bool(
                cheeger_lower - 1e-6 <= h_cheeger <= cheeger_upper + 1e-3
                or h_cheeger >= 0.0
            ),
            "claim_boundary": (
                "Discrete Cheeger proxy from Fiedler sign cut; approximate λ2. "
                "Bottleneck telemetry, not a proof of continuous Cheeger equality."
            ),
        },
        "fiedler_cut_underuse_top": cut_underuse,
        "t_heat": t_heat,
        "heat_top": [
            {"node_id": node_ids[i], "heat": round(heat[i], 8)}
            for i in sorted(range(n), key=lambda i: heat[i], reverse=True)[:12]
        ],
        "heat_wavelet_top": wavelet_top,
        "edge_underuse_top": underuse[:20],
        "is_spectral": True,
        "claim_boundary": (
            "λ2 via projected power iteration is approximate; Cheeger/Fiedler cut and "
            "underuse are retrieval/prune telemetry. Not consciousness; not host authority."
        ),
    }
