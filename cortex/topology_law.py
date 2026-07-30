"""Typed topology law — G_host / G_evidence / G_learned / G_federated.

v6.18 Boundary Consolidation: resolve the contradiction between
"plasticity cannot invent topology" and structure_invent coactivation edges.

Host source remains immutable without host authority.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "cortex-topology-law/1.0"
GLYPH = "⬡⧉"

# Typed graph classes
G_HOST = "G_host"
G_EVIDENCE = "G_evidence"
G_LEARNED = "G_learned"
G_FEDERATED = "G_federated"

TOPOLOGY_CLASSES: dict[str, dict[str, Any]] = {
    G_HOST: {
        "mutable": False,
        "authority": "host_human",
        "description": "Repository source, tests, and host authorization surface. Immutable without host authority.",
    },
    G_EVIDENCE: {
        "mutable": True,
        "authority": "assimilation",
        "description": "Compiler-derived inventory, symbols, deps, chunks. Changes only through re-assimilation/index.",
    },
    G_LEARNED: {
        "mutable": True,
        "authority": "governor_gated",
        "description": (
            "Weak, reversible, receipted neural edges (e.g. coactivated invent). "
            "May be created under Governor gates. Never host files."
        ),
        "examples": ["structure_invent coactivated synapses", "plasticity weight updates"],
    },
    G_FEDERATED: {
        "mutable": False,
        "authority": "query_time_projection",
        "description": (
            "Cross-repo ranking projection only. Repository identities never merge; "
            "authority domains never transfer."
        ),
        "examples": ["federated_query", "host_mesh"],
    },
}

LAW_TEXT = """
G_host       immutable without host authority
G_evidence   compiler-derived; changes only through re-assimilation
G_learned    weak, reversible, receipted edges may be created under Governor gates
G_federated  query-time projection only; repository identities never merge
""".strip()


def classify_edge_kind(kind: str | None = None, *, invented: bool = False) -> str:
    """Map an edge metadata signal to a topology class."""
    if invented:
        return G_LEARNED
    k = (kind or "").casefold()
    if k in {"coactivated", "invented", "learned", "hebbian"}:
        return G_LEARNED
    if k in {"federated", "mesh"}:
        return G_FEDERATED
    if k in {"structural", "dependency", "import", "symbol"}:
        return G_EVIDENCE
    return G_EVIDENCE


def topology_law_packet() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "law": LAW_TEXT,
        "classes": TOPOLOGY_CLASSES,
        "claim_boundary": (
            "Topology law scopes what Cortex may invent: only G_learned under gates. "
            "Never G_host. Not consciousness."
        ),
    }
