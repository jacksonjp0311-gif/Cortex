from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from ..aria_meta.substrate import (
    ARIA_SUBSTRATE_DEFERRED_STATUS,
    INTERNAL_ARIA_REGION,
    REPOSITORY_REGION,
    aria_purposes_for_path,
    is_internal_aria_path,
)
from .models import NeuralNode, NeuralSynapse


RELATION_PRIORS: dict[str, float] = {
    "resolves_to": 1.00,
    "tested_by": 0.95,
    "co_changed": 0.90,
    "described_by": 0.78,
    "imports": 0.72,
    "references": 0.66,
    "documents": 0.62,
    "calls": 0.56,
    "contains": 0.88,
    "child_of": 0.84,
    "dataflow_def": 0.70,
    "dataflow_use": 0.68,
    "covers": 0.80,
    "covered_by": 0.80,
    "next_bb": 0.60,
}

REVERSE_RELATIONS = {"tested_by", "co_changed", "described_by"}


def _node_threshold(kind: str, authoritative: bool) -> float:
    if authoritative:
        return 0.46
    return {
        "source": 0.52,
        "test": 0.54,
        "documentation": 0.58,
        "configuration": 0.56,
        "runtime_evidence": 0.60,
        "discovery_card": 0.57,
        "telemetry": 0.61,
    }.get(kind, 0.58)


def _node_tags(path: str, kind: str, language: str, authoritative: bool) -> tuple[str, ...]:
    parts = [part.lower() for part in Path(path).parts]
    tags = {kind, language, *parts[:-1]}
    suffix = Path(path).suffix.lower().lstrip(".")
    if suffix:
        tags.add(suffix)
    if authoritative:
        tags.add("authoritative")
    return tuple(sorted(tag for tag in tags if tag))


def _synapse_id(source: str, target: str, relation: str) -> str:
    material = f"{source}|{target}|{relation}"
    return "syn_" + sha256(material.encode("utf-8")).hexdigest()[:24]


def _normalized_endpoint(value: str) -> str:
    return value.split("::", 1)[0].replace("\\", "/")


def _symbol_node_id(path: str, qualified_name: str) -> str:
    material = f"{path}::{qualified_name}"
    return "symbol:" + sha256(material.encode("utf-8")).hexdigest()[:28]


def _bb_node_id(path: str, qualified_name: str, bb_index: int, body_hash: str) -> str:
    material = f"{path}::{qualified_name}::bb{bb_index}::{body_hash}"
    return "bb:" + sha256(material.encode("utf-8")).hexdigest()[:28]


def compile_interlink(
    store: Any,
    repo: str,
    *,
    resolutions: tuple[str, ...] = ("file", "symbol"),
) -> dict[str, Any]:
    """Compile Cortex's existing repository graph into a sparse neural interlink.

    Multi-resolution (v5): file nodes remain primary; symbol (and optional
    basic_block) children attach via contains/child_of. Topology is compiled
    from evidence only — no synthetic authority edges.
    """

    want_symbol = "symbol" in resolutions
    want_bb = "basic_block" in resolutions or "bb" in resolutions
    file_rows = [
        row
        for row in store.files(repo)
        if row["status"] in {"indexed", ARIA_SUBSTRATE_DEFERRED_STATUS}
    ]
    live_paths = {row["path"] for row in file_rows}
    live_ids = set(live_paths)
    nodes: list[NeuralNode] = []
    for row in file_rows:
        metadata = json.loads(row["metadata"] or "{}")
        internal_aria = is_internal_aria_path(row["path"])
        deferred = row["status"] == ARIA_SUBSTRATE_DEFERRED_STATUS
        neural_region = INTERNAL_ARIA_REGION if internal_aria else REPOSITORY_REGION
        # Deferred substrate nodes are known topology but not retrieval-seeded until
        # materialization. Slightly higher threshold reduces accidental firing.
        threshold = _node_threshold(row["kind"], bool(row["authoritative"]))
        if deferred:
            threshold = min(0.95, threshold + 0.12)
        node = NeuralNode(
            node_id=row["path"],
            path=row["path"],
            kind=row["kind"],
            threshold=threshold,
            tags=tuple(sorted({
                *_node_tags(
                row["path"],
                row["kind"],
                row["language"],
                bool(row["authoritative"]),
                ),
                neural_region,
                *(("native_semantic_language",) if internal_aria else ()),
                *(("substrate_deferred",) if deferred else ()),
                "resolution:file",
            })),
            metadata={
                "language": row["language"],
                "authoritative": bool(row["authoritative"]),
                "content_hash": row["content_hash"],
                "neural_region": neural_region,
                "dormant_by_default": internal_aria,
                "indexing_tier": "deferred" if deferred else metadata.get(
                    "indexing_tier", "repository"
                ),
                "searchable": not deferred,
                "aria_purposes": (
                    list(aria_purposes_for_path(row["path"]))
                    if internal_aria
                    else []
                ),
                "resolution": "file",
                **metadata,
            },
            resolution="file",
            fingerprint=str(row["content_hash"] or "")[:32] or None,
        )
        nodes.append(node)

    # Symbol (+ optional basic-block) children from extracted symbols table.
    symbol_count = 0
    bb_count = 0
    if want_symbol:
        try:
            symbol_rows = store.symbols(repo)
        except Exception:
            symbol_rows = []
        for sym in symbol_rows:
            path = str(sym["path"] or "").replace("\\", "/")
            if path not in live_paths:
                continue
            qname = str(sym["qualified_name"] or sym["name"] or "")
            if not qname:
                continue
            sid = _symbol_node_id(path, qname)
            live_ids.add(sid)
            start = int(sym["start_line"] or 0)
            end = int(sym["end_line"] or start)
            fp = sha256(
                f"{path}|{qname}|{start}|{end}|{sym['symbol_kind']}".encode()
            ).hexdigest()[:16]
            nodes.append(
                NeuralNode(
                    node_id=sid,
                    path=path,
                    kind="symbol",
                    threshold=0.55,
                    tags=("symbol", "resolution:symbol", str(sym["symbol_kind"] or "")),
                    metadata={
                        "resolution": "symbol",
                        "qualified_name": qname,
                        "symbol_kind": sym["symbol_kind"],
                        "signature": sym["signature"] if "signature" in sym.keys() else "",
                        "parent_node_id": path,
                        "searchable": True,
                    },
                    resolution="symbol",
                    parent_node_id=path,
                    span_start=start,
                    span_end=end,
                    fingerprint=fp,
                )
            )
            symbol_count += 1
            # Lightweight basic-block proxy: one BB per function symbol span.
            if want_bb and str(sym["symbol_kind"] or "") in {
                "function",
                "method",
                "async_function",
                "def",
            }:
                body_hash = fp
                bid = _bb_node_id(path, qname, 0, body_hash)
                live_ids.add(bid)
                nodes.append(
                    NeuralNode(
                        node_id=bid,
                        path=path,
                        kind="basic_block",
                        threshold=0.62,
                        tags=("basic_block", "resolution:basic_block"),
                        metadata={
                            "resolution": "basic_block",
                            "qualified_name": qname,
                            "bb_index": 0,
                            "parent_node_id": sid,
                            "searchable": False,
                        },
                        resolution="basic_block",
                        parent_node_id=sid,
                        span_start=start,
                        span_end=end,
                        fingerprint=body_hash,
                    )
                )
                bb_count += 1

    compiled: dict[tuple[str, str, str], NeuralSynapse] = {}
    for edge in store.edges(repo, limit=200_000):
        relation = edge["relation"]
        if relation not in RELATION_PRIORS:
            continue
        source = _normalized_endpoint(edge["source"])
        target = _normalized_endpoint(edge["target"])
        if source not in live_paths or target not in live_paths or source == target:
            continue
        base = max(0.05, min(0.95, float(edge["confidence"]) * RELATION_PRIORS[relation]))
        key = (source, target, relation)
        existing = compiled.get(key)
        if existing is None or base > existing.base_weight:
            compiled[key] = NeuralSynapse(
                synapse_id=_synapse_id(source, target, relation),
                source_id=source,
                target_id=target,
                relation=relation,
                base_weight=round(base, 6),
                weight=round(base, 6),
                evidence=edge["evidence"],
                metadata=json.loads(edge["metadata"] or "{}"),
            )
        if relation in REVERSE_RELATIONS:
            reverse_relation = f"reverse:{relation}"
            reverse_base = max(0.05, min(0.85, base * 0.82))
            reverse_key = (target, source, reverse_relation)
            if reverse_key not in compiled:
                compiled[reverse_key] = NeuralSynapse(
                    synapse_id=_synapse_id(target, source, reverse_relation),
                    source_id=target,
                    target_id=source,
                    relation=reverse_relation,
                    base_weight=round(reverse_base, 6),
                    weight=round(reverse_base, 6),
                    evidence=f"reverse of {relation}: {edge['evidence']}",
                    metadata={"derived_reverse": True},
                )

    # Hierarchical contains / child_of from multi-res nodes.
    for node in nodes:
        parent = node.parent_node_id
        if not parent or parent not in live_ids:
            continue
        child = node.node_id
        if child == parent:
            continue
        max_w = 0.90 if node.resolution == "symbol" else 0.75
        for relation, base in (("contains", 0.85), ("child_of", 0.80)):
            if relation == "contains":
                src, tgt = parent, child
            else:
                src, tgt = child, parent
            key = (src, tgt, relation)
            if key not in compiled:
                compiled[key] = NeuralSynapse(
                    synapse_id=_synapse_id(src, tgt, relation),
                    source_id=src,
                    target_id=tgt,
                    relation=relation,
                    base_weight=round(base, 6),
                    weight=round(base, 6),
                    minimum_weight=0.05,
                    maximum_weight=max_w,
                    evidence=f"multi_res:{node.resolution}",
                    metadata={"resolution": node.resolution, "hierarchical": True},
                )

    store.sync_neural_graph(repo, nodes, list(compiled.values()))
    state = neural_graph_state(store, repo)
    state["resolutions"] = {
        "file": sum(1 for n in nodes if n.resolution == "file"),
        "symbol": symbol_count,
        "basic_block": bb_count,
    }
    store.append_neural_event(
        repo,
        event_type="interlink_compiled",
        entity_id=repo,
        payload={
            "nodes": state["nodes"],
            "synapses": state["synapses"],
            "graph_hash": state["graph_hash"],
            "resolutions": state["resolutions"],
        },
    )
    return state


def neural_graph_state(store: Any, repo: str) -> dict[str, Any]:
    nodes = store.neural_nodes(repo)
    synapses = store.neural_synapses(repo)
    material = {
        "nodes": [
            {
                "node_id": row["node_id"],
                "path": row["path"],
                "threshold": row["threshold"],
                "kind": row["kind"],
                "neural_region": json.loads(row["metadata"] or "{}").get(
                    "neural_region", REPOSITORY_REGION
                ),
            }
            for row in nodes
        ],
        "synapses": [
            {
                "synapse_id": row["synapse_id"],
                "source_id": row["source_id"],
                "target_id": row["target_id"],
                "relation": row["relation"],
                "base_weight": row["base_weight"],
                "weight": row["weight"],
                "update_count": row["update_count"],
            }
            for row in synapses
        ],
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    graph_hash = sha256(canonical.encode("utf-8")).hexdigest()
    graph_eligible = sum(
        row["status"] in {"indexed", ARIA_SUBSTRATE_DEFERRED_STATUS}
        for row in store.files(repo)
    )
    # Coverage is file-resolution nodes / eligible files (multi-res children excluded).
    file_nodes = 0
    for row in nodes:
        res = None
        try:
            res = row["resolution"]
        except (KeyError, IndexError):
            res = None
        if not res:
            meta = json.loads(row["metadata"] or "{}")
            res = meta.get("resolution") or "file"
        if res == "file":
            file_nodes += 1
    coverage = file_nodes / graph_eligible if graph_eligible else 1.0
    regions: dict[str, int] = {}
    deferred_nodes = 0
    resolution_counts: dict[str, int] = {}
    for row in nodes:
        metadata = json.loads(row["metadata"] or "{}")
        region = metadata.get("neural_region", REPOSITORY_REGION)
        regions[region] = regions.get(region, 0) + 1
        try:
            res = row["resolution"] or metadata.get("resolution") or "file"
        except (KeyError, IndexError):
            res = metadata.get("resolution") or "file"
        resolution_counts[str(res)] = resolution_counts.get(str(res), 0) + 1
        if metadata.get("indexing_tier") == "deferred" or metadata.get("searchable") is False:
            deferred_nodes += 1
    return {
        "repo": repo,
        "nodes": len(nodes),
        "file_nodes": file_nodes,
        "synapses": len(synapses),
        "node_coverage": round(coverage, 6),
        "regions": dict(sorted(regions.items())),
        "resolutions": dict(sorted(resolution_counts.items())),
        "deferred_substrate_nodes": deferred_nodes,
        "graph_hash": graph_hash,
        "ledger_valid": store.verify_neural_ledger(repo),
    }
