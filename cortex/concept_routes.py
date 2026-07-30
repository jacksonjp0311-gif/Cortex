"""Concept routes — map hard paraphrases to implementation paths.

Measure-gate hard suite uses natural-language queries that avoid filenames.
This table is frozen, recommend-only routing mass: boost cited modules when
phrase clusters match. Not host authority. Not consciousness.
"""

from __future__ import annotations

from typing import Any

SCHEMA = "cortex-concept-routes/1.0"

# Frozen routes for hard paraphrase IR (v6.15.3 measure-gate misses).
CONCEPT_ROUTES: list[dict[str, Any]] = [
    {
        "id": "structure_invent",
        "paths": ["cortex/structure_invent.py"],
        "phrases": (
            "coactivation topology",
            "simultaneous path fire",
            "structure invent",
            "invent topology",
            "invented synapses",
            "propose new coactivation",
            "topology edges from simultaneous",
            "gated topology invention",
            "invent new integrate synapses",
            "co-fire and no edge",
            "two nodes co-fire",
        ),
    },
    {
        "id": "plasticity_rct",
        "paths": [
            "cortex/math_net/plasticity_rct.py",
            "cortex/neuron/plasticity.py",
        ],
        "phrases": (
            "randomized controlled trial",
            "plasticity rct",
            "hebbian on vs off",
            "hebbian on versus off",
            "optional synapse weight",
            "opted in",
            "opt-in only",
            "rct arm",
            "rct experiment",
            "synapse weight updates only when",
            "comparing hebbian",
        ),
    },
    {
        "id": "operator_a",
        "paths": ["cortex/math_net/operator.py"],
        "phrases": (
            "graph adjacency operator",
            "dual reverse-edge",
            "reverse-edge operator",
            "build graph adjacency",
            "adjacency matrix builder",
            "operator a",
            "a_ij",
            "undirected weighted adjacency",
            "from neural synapses",
            "synapse weights and dual",
        ),
    },
    {
        "id": "uncertainty_u",
        "paths": ["cortex/math_net/uncertainty.py"],
        "phrases": (
            "single scalar that may only decrease",
            "never inflate certainty",
            "unified uncertainty",
            "unified u scalar",
            "immune stress rises",
            "confidence c=1-u",
            "u only lowers",
            "may only decrease when immune",
            "governor consumes everywhere",
            "confidence inverse",
        ),
    },
    {
        "id": "calibration",
        "paths": ["cortex/math_net/calibration.py"],
        "phrases": (
            "map predicted confidence",
            "observed hit rates",
            "clamp drift floor",
            "shadow calibration",
            "shadow profile",
            "drift floor after outcomes",
            "predicted confidence to observed",
            "constitutional drift",
            "clamps constitutional",
        ),
    },
    {
        "id": "info_account",
        "paths": ["cortex/math_net/info_account.py"],
        "phrases": (
            "information accounting",
            "information budget accounting",
            "budget bits spent",
            "delta-u",
            "delta u",
            "delta-u per",
            "promotion gate",
            "promotion_score",
            "efficiency delta_u",
            "bits spent on retrieval",
            "learning decisions",
        ),
    },
    {
        "id": "coherence_field",
        "paths": ["cortex/coherence.py"],
        "phrases": (
            "multi-seam coactivation",
            "emergent coupling",
            "blood geometry spectral",
            "coherence score threshold",
            "couple indicators",
        ),
    },
    {
        "id": "fusion_coprocess",
        "paths": ["cortex/coprocess.py", "cortex/fuse_proxy.py"],
        "phrases": (
            "fuse tick",
            "regenerate geometry",
            "mind hash",
            "openai compatible",
            "sse content delta",
            "auto ticks geometry",
            "http openai-compatible",
            "auto fuse_ticks",
            "forwards chat completions",
        ),
    },
    {
        "id": "emergence_log",
        "paths": ["cortex/emergence_log.py"],
        "phrases": (
            "durable progress journal",
            "must-read progress",
            "must read progress",
            "couple activations",
            "measure_gate events",
            "emergence log",
            "couple history",
            "progress journal",
            "append-only agent progress",
            "couple activation history",
        ),
    },
    {
        "id": "host_mesh",
        "paths": ["cortex/host_mesh.py"],
        "phrases": (
            "host mesh",
            "attached repository with role",
            "without merging identities",
            "mesh_role",
            "multi-host mesh",
            "lists every attached repository",
        ),
    },
]


def match_concept_routes(query: str) -> list[dict[str, Any]]:
    """Return routes with phrase-hit counts for this query (best first)."""
    q = " ".join((query or "").casefold().split())
    if not q:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    for route in CONCEPT_ROUTES:
        hits = [p for p in route["phrases"] if p in q]
        if hits:
            scored.append(
                (
                    len(hits),
                    {
                        "id": route["id"],
                        "paths": list(route["paths"]),
                        "matched_phrases": hits,
                        "score": len(hits),
                    },
                )
            )
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    return [r for _, r in scored]


def concept_route_paths(query: str) -> list[str]:
    """Unique implementation paths suggested by concept routes."""
    out: list[str] = []
    seen: set[str] = set()
    for route in match_concept_routes(query):
        for path in route.get("paths") or []:
            p = str(path).replace("\\", "/")
            if p not in seen:
                seen.add(p)
                out.append(p)
    return out
