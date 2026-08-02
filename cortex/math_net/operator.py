"""M2 — One graph operator A from neural synapses (+ structural reconciliation).

Build graph adjacency operator and dual reverse-edge operator for spectral work.
Assembles the weighted undirected adjacency from synapse mass for spectral operators.
Module that builds A_ij / operator A — not spectral_memory pulse, not heat kernels alone.
Undirected weighted adjacency from neural synapses (operator A) via build_operator_A.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "cortex-graph-operator/1.0"


def build_operator_A(
    store: Any,
    repo: str,
    *,
    max_nodes: int = 400,
) -> dict[str, Any]:
    """Build undirected weighted adjacency from neural synapses.

    Map: A_ij = sum of synapse weights between i and j (symmetric).
    Caps nodes by highest degree/weight mass for tractability.
    """
    nodes = list(store.neural_nodes(repo) or [])
    synapses = list(store.neural_synapses(repo) or [])
    # Prefer nodes that appear in synapses
    mass: dict[str, float] = {}
    undirected: dict[tuple[str, str], float] = {}
    for row in synapses:
        s = str(row["source_id"])
        t = str(row["target_id"])
        if s == t:
            continue
        w = abs(float(row["weight"] or 0.0))
        a, b = (s, t) if s < t else (t, s)
        undirected[(a, b)] = undirected.get((a, b), 0.0) + w
        mass[s] = mass.get(s, 0.0) + w
        mass[t] = mass.get(t, 0.0) + w

    # Select top nodes by mass
    ranked = sorted(mass.keys(), key=lambda k: mass[k], reverse=True)[: max(1, max_nodes)]
    index = {nid: i for i, nid in enumerate(ranked)}
    n = len(ranked)
    adj_rows: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    edge_list: list[dict[str, Any]] = []
    for (a, b), w in undirected.items():
        if a not in index or b not in index:
            continue
        i, j = index[a], index[b]
        adj_rows[i].append((j, w))
        adj_rows[j].append((i, w))
        edge_list.append({"i": i, "j": j, "source_id": a, "target_id": b, "weight": round(w, 6)})

    degrees = [sum(w for _, w in row) for row in adj_rows]
    # Laplacian L = D - A
    L_rows: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for i in range(n):
        acc: dict[int, float] = {i: degrees[i]}
        for j, w in adj_rows[i]:
            acc[j] = acc.get(j, 0.0) - w
        L_rows[i] = sorted(acc.items())

    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "n": n,
        "node_ids": ranked,
        "index": index,
        "adj_rows": adj_rows,
        "L_rows": L_rows,
        "degrees": degrees,
        "edges": edge_list,
        "edge_count": len(edge_list),
        "node_total_in_body": len(nodes),
        "synapse_total": len(synapses),
        "claim_boundary": (
            "A is neural-weight undirected projection; structural edges table "
            "reconciled separately in dual_graph_report."
        ),
    }


def dual_graph_report(store: Any, repo: str) -> dict[str, Any]:
    """Reconcile structural graph (edges) vs neural synapses."""
    neural_n = 0
    neural_e = 0
    try:
        neural_n = len(list(store.neural_nodes(repo) or []))
        neural_e = len(list(store.neural_synapses(repo) or []))
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    structural_e = 0
    structural_kinds: dict[str, int] = {}
    try:
        # Count the complete structural substrate.  store.edges() is a browsing
        # API whose default limit is 500; using it here silently truncated the
        # alignment denominator on larger repositories.
        if hasattr(store, "db"):
            cur = store.db.execute(
                "SELECT relation, COUNT(*) AS c FROM edges WHERE repo=? GROUP BY relation",
                (repo,),
            )
            for row in cur.fetchall():
                structural_kinds[str(row["relation"] or "?")] = int(row["c"])
                structural_e += int(row["c"])
        elif hasattr(store, "edges") and callable(store.edges):
            try:
                rows = list(store.edges(repo, limit=100_000) or [])
            except TypeError:
                rows = list(store.edges(repo) or [])
            structural_e = len(rows)
            for row in rows:
                relation = str(row.get("relation") or "?")
                structural_kinds[relation] = structural_kinds.get(relation, 0) + 1
    except Exception:
        # table may not exist or differ
        try:
            cur = store.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%edge%'"
            )
            tables = [r[0] for r in cur.fetchall()]
        except Exception:
            tables = []
        return {
            "ok": True,
            "neural_nodes": neural_n,
            "neural_synapses": neural_e,
            "structural_edges": structural_e,
            "structural_by_relation": structural_kinds,
            "edge_tables_seen": tables,
            "ratio_neural_to_structural": None,
            "note": "structural edge query partial; neural layer measured",
        }

    ratio = (neural_e / structural_e) if structural_e else None
    return {
        "ok": True,
        "neural_nodes": neural_n,
        "neural_synapses": neural_e,
        "structural_edges": structural_e,
        "structural_by_relation": structural_kinds,
        "ratio_neural_to_structural": round(ratio, 4) if ratio is not None else None,
        "count_basis": "complete_relation_aggregate",
        "theory": (
            "Neural layer is activation-over-compiled-edges, not a second ontology "
            "when A is built from neural weights mapped from structure."
        ),
        "claim_boundary": "Reconciliation is diagnostic; does not merge tables automatically.",
    }
