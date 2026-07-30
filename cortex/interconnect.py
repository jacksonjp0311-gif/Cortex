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
from .kernels import kernels_status
from .progress_glyphs import progress_glyph_registry
from .ranker.model import ranker_status
from .vectors.index import hnsw_status

SCHEMA = "cortex-interconnect/1.1"
GLYPH = "⧉"


def _continuity_slice(store: Any, repo: str) -> dict[str, Any]:
    """v7.0: body epoch + phase + plane roots for mesh (read/seal, no host mutation)."""
    try:
        from .epoch import ensure_current_epoch, verify_body_epoch
        from .phases import current_phase

        ep = ensure_current_epoch(store, repo, reason="interconnect_mesh")
        ph = current_phase(store, repo)
        ver = verify_body_epoch(store, repo, ep)
        return {
            "plane": "continuity",
            "body_epoch_id": ep.epoch_id,
            "epoch_verified": bool(ver.get("ok")),
            "epoch_mismatches": list(ver.get("mismatches") or []),
            "runtime_phase": ph.phase,
            "phase_epoch_id": ph.epoch_id,
            "phase_bound": ph.epoch_id == ep.epoch_id,
            "evidence_root_hash": ep.evidence_root_hash[:16],
            "adaptive_root_hash": ep.adaptive_root_hash[:16],
            "constitutional_config_hash": ep.constitutional_config_hash[:16],
            "cortex_version": ep.cortex_version,
            "repository_id": ep.repository_id,
            "receipt_hash": ep.receipt_hash[:16],
        }
    except Exception as exc:
        return {"plane": "continuity", "error": f"{type(exc).__name__}: {exc}"}


def mesh_status(
    store: Any,
    repo: str,
    *,
    governor: Any | None = None,
    home: Any | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """Single-pane mesh health. Telemetry only; never authorization.

    compact=True (default) omits full glyph registry to save tokens.
    """

    graph = load_metric_graph(store, repo)
    ranker = ranker_status(store, repo)
    hnsw = hnsw_status(store, repo)
    causal = causal_report(store, repo, limit=10)
    frozen = bool((store.get_setting(f"ranker_frozen:{repo}", {}) or {}).get("frozen"))
    multi_agent = bool(
        (store.get_setting(f"multi_agent:{repo}", {}) or {}).get("enabled")
    )
    last_prune = store.get_setting(f"prune:{repo}", {}) or {}
    try:
        kernels = kernels_status(store, repo)
    except Exception as exc:
        kernels = {"error": f"{type(exc).__name__}: {exc}"}
    intel_pulse = store.get_setting(f"intel_pulse:{repo}", {}) or {}
    continuity = _continuity_slice(store, repo)

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
    # v7.0 continuity bottlenecks (executable stale-state signals)
    if continuity.get("error"):
        bottlenecks.append("continuity_unavailable")
    else:
        if continuity.get("epoch_verified") is False:
            bottlenecks.append("epoch_stale_or_mismatched")
        if continuity.get("phase_bound") is False:
            bottlenecks.append("phase_epoch_unbound")
        if not continuity.get("body_epoch_id"):
            bottlenecks.append("body_epoch_missing")

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
        and continuity.get("epoch_verified") is not False
        and continuity.get("phase_bound") is not False
        and not continuity.get("error")
    )

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "spoken": "interconnect mesh",
        "repo": repo,
        "ts": round(time.time(), 3),
        "mesh_green": mesh_green,
        "bottlenecks": bottlenecks,
        "continuity": continuity,
        "planes": {
            "E": "evidence",
            "A": "adaptation",
            "I": "immunity",
            "C": "constitutional",
            "W": "witness",
        },
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
        "spectral": {
            "glyph": "≋",
            "dominant": kernels.get("dominant"),
            "retention": kernels.get("retention")
            or (graph.get("retention_by_class")),
            "profile": kernels.get("profile"),
            "clock_neq_memory_neq_decision": True,
        },
        "intelligence": {
            "glyph": "☰",
            "last_pulse": intel_pulse.get("at"),
            "resonance": intel_pulse.get("resonance"),
            "pass_count": intel_pulse.get("pass_count"),
            "version": intel_pulse.get("version"),
            "pulse_every": 2,
            "seal_every": 7,
        },
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
        "progress_glyphs": (
            {
                "symbols": {
                    k: v.get("symbol")
                    for k, v in (progress_glyph_registry().get("glyphs") or {}).items()
                },
                "automatic_execution": False,
            }
            if compact
            else progress_glyph_registry()
        ),
        "claim_boundary": (
            "Interconnect mesh is local operational health; not consciousness "
            "and not host mutation authority."
        ),
    }


def mesh_dashboard(store: Any, repo: str, *, governor: Any | None = None, home: Any | None = None) -> dict[str, Any]:
    """One-screen mesh + spectral field + continuity for operators."""

    mesh = mesh_status(store, repo, governor=governor, home=home)
    spectrum = (mesh.get("spectral") or {}).get("retention") or {}
    cont = mesh.get("continuity") or {}
    return {
        "schema_version": "cortex-mesh-dashboard/1.1",
        "glyph": "⧉",
        "repo": repo,
        "mesh_green": mesh.get("mesh_green"),
        "bottlenecks": mesh.get("bottlenecks"),
        "xi_spectrum": spectrum,
        "dominant_kernel": (mesh.get("spectral") or {}).get("dominant"),
        "connect_pass_count": (mesh.get("connect") or {}).get("pass_count"),
        "ranker": mesh.get("ranker"),
        "hnsw": mesh.get("hnsw"),
        "graph": mesh.get("graph"),
        "causal": mesh.get("causal"),
        "gates": mesh.get("gates"),
        "immune": mesh.get("immune"),
        "intelligence": mesh.get("intelligence"),
        "continuity": cont,
        "body_epoch_id": cont.get("body_epoch_id"),
        "runtime_phase": cont.get("runtime_phase"),
        "resonance": (mesh.get("intelligence") or {}).get("resonance"),
        "law": "common_pulse_through_kernel_spectrum_and_body_epoch",
        "claim_boundary": mesh.get("claim_boundary"),
    }
