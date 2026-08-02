"""Ratio lattice operators — self-similar partition, triadic closure, rational slopes.

v6.21 law compression. Measurement-structure operators only.
Not sacred geometry, not consciousness, not host authority.
"""

from __future__ import annotations

import math
from typing import Any

SCHEMA = "cortex-ratio-lattice/1.0"

# Rational slope / share tables (seked-style discipline — audit, not π-worship).
RATIONAL_RATIOS: dict[str, tuple[int, int]] = {
    "fib_5_8": (5, 8),
    "fib_8_13": (8, 13),
    "double_square": (1, 2),
    "quarter": (1, 4),
    "seked_14_11": (14, 11),  # face-slope band analogy only
    "half": (1, 1),
}

# Self-similar fixed point φ = (1+√5)/2 — used only when scheme="phi".
_PHI = (1.0 + math.sqrt(5.0)) / 2.0

CLAIM = (
    "Ratio lattice operators are self-similar partition, graph triadic closure, "
    "and rational config ratios — not sacred geometry, consciousness, or host authority."
)


def rational_ratio(name: str) -> tuple[int, int]:
    """Return a named small-integer ratio; raises KeyError if unknown."""
    return RATIONAL_RATIOS[name]


def partition_budgets(
    total: int,
    levels: tuple[str, ...] = ("symbol", "file", "module"),
    *,
    scheme: str = "fib",
) -> dict[str, Any]:
    """Split total budget across resolution levels under a ratio scheme.

    Schemes:
      fib           — Fibonacci weights (default; rational audit)
      phi           — self-similar residual ladder; coarsest holds envelope
      double_square — 1:2 fine:coarse prior
      flat          — entire budget on first level (pre-6.21 ablation)
    """
    B = max(0, int(total))
    names = tuple(levels) if levels else ("all",)
    n = len(names)
    scheme_n = (scheme or "fib").casefold().strip()
    if scheme_n not in {"fib", "phi", "double_square", "flat"}:
        scheme_n = "fib"
    pools: dict[str, int] = {}

    if B == 0 or n == 0:
        return {
            "schema_version": SCHEMA,
            "scheme": scheme_n,
            "total": B,
            "pools": {k: 0 for k in names},
            "levels": list(names),
            "sum_check": 0,
            "claim_boundary": CLAIM,
        }

    if scheme_n == "flat":
        pools = {names[0]: B}
        for k in names[1:]:
            pools[k] = 0
    elif scheme_n == "double_square":
        if n == 1:
            pools = {names[0]: B}
        else:
            fine = B // 3  # 1 part of 1:2 → fine gets 1/3
            coarse = B - fine
            pools = {names[0]: fine, names[1]: coarse}
            if n > 2:
                mod = coarse // 3
                pools[names[1]] = coarse - mod
                pools[names[2]] = mod
                for k in names[3:]:
                    pools[k] = 0
    elif scheme_n == "phi":
        # Larger share on coarser levels (envelope holds mass)
        raw: list[float] = []
        rem = float(B)
        for _ in range(n - 1):
            share = rem / _PHI
            raw.append(share)
            rem -= share
        raw.append(rem)
        raw = list(reversed(raw))  # fine first (smaller leaf)
        ints = [int(x) for x in raw]
        ints[-1] += B - sum(ints)
        pools = {names[i]: max(0, ints[i]) for i in range(n)}
    else:
        # fib: fine small, coarse large (envelope)
        fib = [1, 2]
        while len(fib) < n:
            fib.append(fib[-1] + fib[-2])
        # Levels are ordered fine -> coarse.  Keep the Fibonacci mass in that
        # same direction so the containing envelope receives the largest pool.
        # The previous reverse() produced 3:2:1 for symbol:file:module while the
        # documented law (and the other schemes) requires 1:2:3.
        weights = fib[:n]
        wsum = sum(weights) or 1
        ints = [int(B * w / wsum) for w in weights]
        ints[-1] += B - sum(ints)
        pools = {names[i]: max(0, ints[i]) for i in range(n)}

    return {
        "schema_version": SCHEMA,
        "scheme": scheme_n,
        "total": B,
        "pools": pools,
        "levels": list(names),
        "sum_check": sum(pools.values()),
        "claim_boundary": (
            "Budget heuristic from self-similar / rational partition — "
            "not golden-ratio activation or sacred geometry."
        ),
    }


def build_undirected_adj(
    store: Any,
    repo: str,
    *,
    max_nodes: int = 400,
) -> dict[str, set[str]]:
    """Undirected adjacency from neural synapses (relation-agnostic)."""
    adj: dict[str, set[str]] = {}
    try:
        rows = list(store.neural_synapses(repo) or [])
    except Exception:
        return adj
    for row in rows:
        s = str(row["source_id"] or "")
        t = str(row["target_id"] or "")
        if not s or not t or s == t:
            continue
        adj.setdefault(s, set()).add(t)
        adj.setdefault(t, set()).add(s)

    if max_nodes > 0 and len(adj) > max_nodes:
        top = sorted(adj.keys(), key=lambda n: len(adj[n]), reverse=True)[:max_nodes]
        keep = set(top)
        adj = {n: {m for m in adj[n] if m in keep} for n in keep}
    return adj


def local_closure(adj: dict[str, set[str]], node_id: str) -> float:
    """Local clustering coefficient c_u ∈ [0,1]."""
    nbrs = adj.get(node_id) or set()
    k = len(nbrs)
    if k < 2:
        return 0.0
    edges = 0
    nbr_list = list(nbrs)
    for i in range(len(nbr_list)):
        ni = adj.get(nbr_list[i]) or set()
        for j in range(i + 1, len(nbr_list)):
            if nbr_list[j] in ni:
                edges += 1
    denom = k * (k - 1) / 2.0
    if denom <= 0:
        return 0.0
    return float(edges) / float(denom)


def _count_triangles_and_triples(
    adj: dict[str, set[str]],
) -> tuple[int, int]:
    """Return (triangle_count, connected_triple_count / wedges)."""
    tri_corners = 0
    wedges = 0
    for u, nbr_set in adj.items():
        nbrs = sorted(nbr_set)
        k = len(nbrs)
        if k < 2:
            continue
        wedges += k * (k - 1) // 2
        for i in range(k):
            ni = adj.get(nbrs[i]) or set()
            for j in range(i + 1, k):
                if nbrs[j] in ni:
                    tri_corners += 1
    return tri_corners // 3, wedges


def edge_triangle_count(adj: dict[str, set[str]], u: str, v: str) -> int:
    """Number of common neighbors (triangles through edge uv)."""
    return len((adj.get(u) or set()) & (adj.get(v) or set()))


def open_bridge_edges(
    adj: dict[str, set[str]],
    synapses: list[Any] | None = None,
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Edges that participate in zero triangles (bridge-like / open paths)."""
    seen: set[tuple[str, str]] = set()
    bridges: list[dict[str, Any]] = []

    def _consider(a: str, b: str, extra: dict[str, Any] | None = None) -> None:
        if a > b:
            a, b = b, a
        key = (a, b)
        if key in seen:
            return
        seen.add(key)
        if b not in (adj.get(a) or set()):
            return
        if edge_triangle_count(adj, a, b) == 0:
            item: dict[str, Any] = {
                "source_id": a,
                "target_id": b,
                "triangles": 0,
                "bridge_like": True,
            }
            if extra:
                item.update(extra)
            bridges.append(item)

    if synapses:
        for row in synapses:
            s = str(row["source_id"] or "")
            t = str(row["target_id"] or "")
            if not s or not t:
                continue
            _consider(
                s,
                t,
                {
                    "synapse_id": str(row["synapse_id"] or ""),
                    "weight": float(row["weight"] or 0),
                    "relation": str(row["relation"] or ""),
                },
            )
    else:
        for u, nbrs in adj.items():
            for v in nbrs:
                if u < v:
                    _consider(u, v)

    bridges.sort(key=lambda x: (x.get("weight") is None, float(x.get("weight") or 0.0)))
    return bridges[: max(0, int(limit))]


def triadic_metrics(
    store: Any,
    repo: str,
    *,
    max_nodes: int = 400,
) -> dict[str, Any]:
    """Global triadic closure T and local clustering summary on neural graph."""
    adj = build_undirected_adj(store, repo, max_nodes=max_nodes)
    n = len(adj)
    if n == 0:
        return {
            "schema_version": SCHEMA,
            "ok": True,
            "n_nodes": 0,
            "n_edges": 0,
            "triangles": 0,
            "connected_triples": 0,
            "global_closure_T": 0.0,
            "mean_local_closure": 0.0,
            "open_bridges_sample": [],
            "claim_boundary": CLAIM,
        }

    n_edges = sum(len(v) for v in adj.values()) // 2
    triangles, wedges = _count_triangles_and_triples(adj)
    # T = 3Δ / #connected triples (wedges)
    T = (3.0 * float(triangles)) / float(wedges) if wedges > 0 else 0.0
    T = max(0.0, min(1.0, T))

    local_vals = [local_closure(adj, u) for u in adj]
    mean_c = sum(local_vals) / len(local_vals) if local_vals else 0.0

    synapses = None
    try:
        synapses = list(store.neural_synapses(repo) or [])
    except Exception:
        synapses = None
    bridges = open_bridge_edges(adj, synapses, limit=12)

    return {
        "schema_version": SCHEMA,
        "ok": True,
        "n_nodes": n,
        "n_edges": n_edges,
        "triangles": triangles,
        "connected_triples": wedges,
        "global_closure_T": round(T, 6),
        "mean_local_closure": round(mean_c, 6),
        "open_bridges_sample": bridges,
        "claim_boundary": (
            "Triadic closure is graph clustering / common-neighbor telemetry on "
            "neural synapses — not cosmology, consciousness, or host authority."
        ),
    }


def local_closure_map(
    store: Any,
    repo: str,
    *,
    max_nodes: int = 400,
) -> dict[str, float]:
    """node_id → local clustering for enrich stamp."""
    adj = build_undirected_adj(store, repo, max_nodes=max_nodes)
    return {nid: round(local_closure(adj, nid), 6) for nid in adj}


def hit_resolution(path: str, meta: dict[str, Any] | None = None) -> str:
    """Coarse resolution tag for budget partition: symbol | file | module."""
    meta = meta or {}
    res = str(meta.get("resolution") or "").casefold()
    if res in {"symbol", "file", "module"}:
        return res
    p = (path or "").replace("\\", "/")
    if "::" in p:
        return "symbol"
    leaf = p.rsplit("/", 1)[-1] if p else ""
    if leaf and "." not in leaf and p.count("/") >= 1:
        return "module"
    return "file"
