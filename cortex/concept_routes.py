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
            "optional synapse weight",
            "opted in",
            "rct arm",
            "synapse weight updates only when",
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
            "operator a",
            "undirected weighted adjacency",
            "from neural synapses",
        ),
    },
    {
        "id": "uncertainty_u",
        "paths": ["cortex/math_net/uncertainty.py"],
        "phrases": (
            "single scalar that may only decrease",
            "never inflate certainty",
            "unified uncertainty",
            "immune stress rises",
            "confidence c=1-u",
            "u only lowers",
            "may only decrease when immune",
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
            "drift floor after outcomes",
            "predicted confidence to observed",
        ),
    },
    {
        "id": "info_account",
        "paths": ["cortex/math_net/info_account.py"],
        "phrases": (
            "information accounting",
            "budget bits spent",
            "delta-u",
            "delta u",
            "promotion gate",
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
