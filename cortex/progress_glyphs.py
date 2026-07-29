"""ARIA progress glyphs — capability-free symbols for rapid operational surfaces.

These lower to ordinary Cortex calls in documentation and packet metadata.
They introduce no opcode, capability, or mutation authority.
"""

from __future__ import annotations

from typing import Any

# Executable function aliases in the ARIA sense: pure labels for operator speed.
ARIA_PROGRESS_GLYPHS: dict[str, dict[str, str]] = {
    "transcend_check": {
        "symbol": "⟡",
        "spoken": "transcend check",
        "target": "TranscendCheck",
        "maps_to": "cortex transcend-check",
    },
    "packet_profile": {
        "symbol": "▣",
        "spoken": "packet profile",
        "target": "PacketProfile",
        "maps_to": "cortex activate --profile",
    },
    "control_error": {
        "symbol": "⚠",
        "spoken": "control error",
        "target": "ControlError",
        "maps_to": "packet.control_error",
    },
    "immune_gate": {
        "symbol": "⚠",
        "spoken": "immune gate",
        "target": "ImmuneGate",
        "maps_to": "cortex immune / packet.control_error.immune_action",
    },
    "connect_pass": {
        "symbol": "⧉",
        "spoken": "connect pass",
        "target": "ConnectPass",
        "maps_to": "cortex metrics / packet.connect_pass",
    },
    "retrieval_gate": {
        "symbol": "⌖",
        "spoken": "retrieval gate",
        "target": "RetrievalGate",
        "maps_to": "cortex evaluate retrieval corpus",
    },
    "ritual_idempotent": {
        "symbol": "⟳",
        "spoken": "ritual idempotent",
        "target": "RitualIdempotent",
        "maps_to": "cortex ritual",
    },
    "surprise_metric": {
        "symbol": "Δ",
        "spoken": "incremental surprise",
        "target": "SurpriseMetric",
        "maps_to": "packet.efficiency.surprise",
    },
    "teach_surface": {
        "symbol": "☰",
        "spoken": "teach surface",
        "target": "TeachSurface",
        "maps_to": "cortex teach",
    },
    "organism_pulse": {
        "symbol": "⊛",
        "spoken": "organism pulse",
        "target": "OrganismPulse",
        "maps_to": "packet.organism / cortex organism",
    },
    "organism_breathe": {
        "symbol": "∽",
        "spoken": "organism breathe",
        "target": "OrganismBreathe",
        "maps_to": "cortex breathe",
    },
    "hnsw_vectors": {
        "symbol": "▦",
        "spoken": "hnsw vectors",
        "target": "HnswVectors",
        "maps_to": "cortex vectors",
    },
    "ranker": {
        "symbol": "⇅",
        "spoken": "ranker",
        "target": "LocalRanker",
        "maps_to": "cortex ranker",
    },
    "predict": {
        "symbol": "⇢",
        "spoken": "predict prefetch",
        "target": "PredictPrefetch",
        "maps_to": "cortex predict",
    },
    "contract": {
        "symbol": "▤",
        "spoken": "contract check",
        "target": "ContractCheck",
        "maps_to": "cortex contract",
    },
    "causal": {
        "symbol": "↻",
        "spoken": "causal ledger",
        "target": "CausalLedger",
        "maps_to": "cortex causal",
    },
    "interconnect_mesh": {
        "symbol": "⧉",
        "spoken": "interconnect mesh",
        "target": "InterconnectMesh",
        "maps_to": "cortex interconnect",
    },
    "graph_prune": {
        "symbol": "✂",
        "spoken": "graph prune",
        "target": "GraphPrune",
        "maps_to": "cortex prune",
    },
    "spectral_kernels": {
        "symbol": "≋",
        "spoken": "spectral kernels",
        "target": "SpectralKernels",
        "maps_to": "cortex kernels",
    },
    "distill_intel": {
        "symbol": "☰",
        "spoken": "distill intelligence",
        "target": "DistillIntel",
        "maps_to": "cortex distill",
    },
}


def progress_glyph_registry() -> dict[str, Any]:
    return {
        "schema_version": "cortex-progress-glyphs/1.0",
        "glyphs": ARIA_PROGRESS_GLYPHS,
        "automatic_execution": False,
        "grants_mutation_authority": False,
        "claim_boundary": (
            "Progress glyphs are capability-free labels for operator/agent speed; "
            "they never execute ARIA plans or authorize mutation."
        ),
    }
