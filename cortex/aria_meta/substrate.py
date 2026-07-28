"""Task gating for Cortex's native ARIA semantic substrate."""

from __future__ import annotations

import re
from typing import Any


INTERNAL_ARIA_PREFIX = "cortex/aria_meta/vendor/"
INTERNAL_ARIA_REGION = "internal_aria_substrate"
REPOSITORY_REGION = "repository"

_ARIA_SIGNALS = (
    "aria",
    "meta-language",
    "meta language",
    "semantic plan",
    "semantic planning",
    "semantic replay",
    "semantic handoff",
    "session handoff",
    "provider bridge",
    "cooperative mesh",
    "agent mesh",
    "glyph",
    "intent verification",
    "intent proof",
    "consent admission",
    "admission receipt",
    "capability authority",
    "governed evolution",
    "governance contract",
)


def is_internal_aria_path(path: str) -> bool:
    return path.replace("\\", "/").startswith(INTERNAL_ARIA_PREFIX)


def classify_aria_task(task: str) -> dict[str, Any]:
    """Decide whether a task should wake the always-known ARIA region."""

    normalized = " ".join(re.findall(r"[a-z0-9_-]+", task.casefold()))
    padded = f" {normalized} "
    matched = tuple(
        signal for signal in _ARIA_SIGNALS if f" {signal} " in padded
    )
    active = bool(matched)
    return {
        "schema_version": "cortex-aria-activation/1.0",
        "known": True,
        "namespace": INTERNAL_ARIA_REGION,
        "mode": "active" if active else "dormant",
        "matched_signals": list(matched),
        "reason": (
            "task requests ARIA semantic, continuity, coordination, or governance knowledge"
            if active
            else "native ARIA knowledge remains available but outside this task's evidence path"
        ),
        "automatic_execution": False,
        "grants_mutation_authority": False,
    }


__all__ = [
    "INTERNAL_ARIA_PREFIX",
    "INTERNAL_ARIA_REGION",
    "REPOSITORY_REGION",
    "classify_aria_task",
    "is_internal_aria_path",
]
