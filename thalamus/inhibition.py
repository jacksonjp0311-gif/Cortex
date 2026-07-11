from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


HARD_EXCLUDED_PREFIXES = ("node_modules/", ".venv/", "venv/", "dist/", "build/", ".cortex/runtime/")
GENERATED_SUFFIXES = (".lock", ".min.js", ".map")


def inhibit(hits: Iterable[Any], lane_weights: dict[str, float]) -> list[Any]:
    """Apply deterministic reticular-style gating and retain an evidence audit on hits."""

    items = list(hits)
    duplicates = Counter((item.path, item.content_hash) for item in items)
    selected: list[Any] = []
    for hit in items:
        path = hit.path.replace("\\", "/").lower()
        hard = path.startswith(HARD_EXCLUDED_PREFIXES)
        duplicate = max(0.0, (duplicates[(hit.path, hit.content_hash)] - 1) / max(1, len(items) - 1))
        generated = 1.0 if path.endswith(GENERATED_SUFFIXES) else 0.0
        lane = lane_for_hit(hit)
        out_of_scope = 1.0 - lane_weights.get(lane, lane_weights.get("source", 0.05))
        inhibition = 1.0 if hard else min(1.0, 0.20 * duplicate + 0.30 * out_of_scope + 0.10 * generated)
        hit.metadata["thalamus"] = {
            "lane": lane,
            "inhibition": round(inhibition, 6),
            "hard_excluded": hard,
            "gated_score": round(float(hit.score) * (1.0 - inhibition), 8),
        }
        if not hard:
            hit.score = float(hit.metadata["thalamus"]["gated_score"])
            selected.append(hit)
    return sorted(selected, key=lambda hit: (-hit.score, hit.path, hit.start_line))


def lane_for_hit(hit: Any) -> str:
    path = hit.path.replace("\\", "/").lower()
    if hit.kind == "telemetry":
        return "git"
    if hit.kind == "discovery_card":
        return "decisions"
    if path.startswith("tests/") or "/test_" in path or path.startswith("test_"):
        return "tests"
    if path.startswith(("docs/", "examples/")) or path.endswith((".md", ".rst")):
        return "documentation"
    if path.endswith((".toml", ".yaml", ".yml", ".json", ".ini", ".cfg")):
        return "configuration"
    return "source"
