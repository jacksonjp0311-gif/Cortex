"""Interconnect mesh — fold v5/v6 organs into one read-only health surface.

Glyphic medium alignment: status only. Never mutation authority.
"""

from __future__ import annotations

import time
from typing import Any

from .agents.tokens import ALLOWED_SCOPES, FORBIDDEN_SCOPES
from .causal.ledger import causal_report
from .connect_pass import load_metric_graph
from .control_error import build_control_error
from .progress_glyphs import progress_glyph_registry
from .ranker.model import ranker_status
from .vectors.index import hnsw_status

SCHEMA = "cortex-interconnect/1.0"
GLYPH = "⧉"


def mesh_status(
    store: Any,
    repo: str,
    *,
    governor: Any | None = None,
    home: Any | None = None,
) -> dict[str, Any]:
    """Single-pane mesh health. Telemetry only; never authorization."""

    graph = load_metric_graph(store, repo)
    ranker = ranker_status(store, repo)
    hnsw = hnsw_status(store, repo)
    causal = causal_report(store, repo, limit=10)
    frozen = bool((store.get_setting(f"ranker_frozen:{repo}", {}) or {}).get("frozen"))
    multi_agent = bool(
        (store.get_setting(f"multi_agent:{repo}", {}) or {}).get("enabled")
    )
    last_prune = store.get_setting(f"prune:{repo}", {}) or {}

    control: dict[str, Any] = {}
    if governor is not None and home is not None:
        try:
            from .config import load_repo_config
            from .indexer import current_manifest_hash
            from .verify import verify_repository
            from pathlib import Path

            repository = store.repo(repo)
            if repository:
                root = Path(repository["path"])
                config = load_repo_config(root)
                current = current_manifest_hash(root, config) == (
                    repository["manifest_hash"] or ""
                )
                cert = verify_repository(
                    home, store, repo, config, write_certificate=False
                )
                gov = governor.evaluate(
                    repo, manifest_current=current, certificate=cert
                )
                control = build_control_error(
                    certificate=cert,
                    governance=gov,
                    manifest_current=current,
                    retrieval_confidence=0.0,
                    aria_materialization={},
                )
        except Exception as exc:
            control = {"error": f"{type(exc).__name__}: {exc}"}

    block = bool(control.get("block"))
    # Bottleneck signals: high scan, low sparse fire, blocked immune
    averages = graph.get("averages") or {}
    bottlenecks: list[str] = []
    if block:
        bottlenecks.append("immune_block")
    if float(averages.get("block_rate") or 0) > 0.3:
        bottlenecks.append("high_historical_block_rate")
    if frozen:
        bottlenecks.append("ranker_frozen")
    if not hnsw.get("available"):
        bottlenecks.append("hnsw_absent")
    if int(graph.get("pass_count") or 0) == 0:
        bottlenecks.append("no_connect_passes_yet")

    nodes = store.db.execute(
        "SELECT COUNT(*) AS c FROM neural_nodes WHERE repo=?", (repo,)
    ).fetchone()["c"]
    synapses = store.db.execute(
        "SELECT COUNT(*) AS c FROM neural_synapses WHERE repo=?", (repo,)
    ).fetchone()["c"]
    file_nodes = store.db.execute(
        """
        SELECT COUNT(*) AS c FROM neural_nodes
        WHERE repo=? AND (resolution='file' OR resolution IS NULL OR resolution='')
        """,
        (repo,),
    ).fetchone()["c"]

    mesh_green = (
        not block
        and "host.mutate" not in ALLOWED_SCOPES
        and "host.mutate" in FORBIDDEN_SCOPES
        and not frozen
    )

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "spoken": "interconnect mesh",
        "repo": repo,
        "ts": round(time.time(), 3),
        "mesh_green": mesh_green,
        "bottlenecks": bottlenecks,
        "immune": {
            "block": block,
            "code": (control.get("immune_action") or {}).get("code"),
            "severity": control.get("severity"),
        },
        "connect": {
            "pass_count": graph.get("pass_count"),
            "averages": averages,
            "totals": {
                "distill_count": (graph.get("totals") or {}).get("distill_count"),
                "aria_materialize_count": (graph.get("totals") or {}).get(
                    "aria_materialize_count"
                ),
                "block_count": (graph.get("totals") or {}).get("block_count"),
            },
            "top_coactivations": dict(
                list((graph.get("path_coactivation") or {}).items())[:5]
            ),
        },
        "ranker": {
            "train_count": ranker.get("train_count"),
            "model_id": ranker.get("model_id"),
            "frozen": frozen,
        },
        "hnsw": {
            "available": hnsw.get("available"),
            "nodes": hnsw.get("nodes"),
            "algorithm": hnsw.get("algorithm"),
        },
        "graph": {
            "nodes": int(nodes),
            "file_nodes": int(file_nodes),
            "synapses": int(synapses),
            "last_prune": last_prune,
        },
        "causal": causal.get("counts"),
        "agents": {
            "multi_agent_mode": multi_agent,
            "host_mutate_forbidden": "host.mutate" in FORBIDDEN_SCOPES,
        },
        "aria": {
            "medium": "glyphic_progress_labels",
            "automatic_execution": False,
            "glyphs": {
                k: v.get("symbol")
                for k, v in (progress_glyph_registry().get("glyphs") or {}).items()
            },
        },
        "gates": {
            "immune_blocks_train": True,
            "immune_blocks_seal": True,
            "contract_constrains_only": True,
            "relevance_never_mutation": True,
        },
        "progress_glyphs": progress_glyph_registry(),
        "claim_boundary": (
            "Interconnect mesh is local operational health; not consciousness "
            "and not host mutation authority."
        ),
    }
