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
