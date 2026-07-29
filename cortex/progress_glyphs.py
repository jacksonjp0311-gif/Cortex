"""ARIA progress glyphs — re-export of the Glyph Canon for compatibility.

Prefer ``cortex.glyphs.canon`` for new code. Glyphs remain capability-free.
"""

from __future__ import annotations

from typing import Any

from .glyphs.canon import GLYPH_CANON, glyph_canon_registry

# Backward-compatible map used by older packet fields and teach surface.
ARIA_PROGRESS_GLYPHS: dict[str, dict[str, str]] = {
    key: {
        "symbol": str(entry["symbol"]),
        "spoken": str(entry["spoken"]),
        "target": str(entry.get("aria_id") or key),
        "maps_to": str(entry.get("maps_to") or ""),
    }
    for key, entry in GLYPH_CANON.items()
    if entry.get("role") not in {"entity"} or key in {"ok", "block", "dormant", "awake", "in_phase"}
}


def progress_glyph_registry() -> dict[str, Any]:
    canon = glyph_canon_registry(optimized=True)
    return {
        "schema_version": "cortex-progress-glyphs/1.1",
        "glyphs": ARIA_PROGRESS_GLYPHS,
        "canon": {
            "schema_version": canon["schema_version"],
            "glyph": canon["glyph"],
            "count": canon["count"],
            "aria_role": canon["aria_role"],
        },
        "automatic_execution": False,
        "grants_mutation_authority": False,
        "claim_boundary": (
            "Progress glyphs are capability-free labels for operator/agent speed; "
            "they never execute ARIA plans or authorize mutation. Full canon: ◈."
        ),
    }
