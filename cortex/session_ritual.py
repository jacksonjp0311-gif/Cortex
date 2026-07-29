"""Session ritual: activate → remember → consolidate on one substrate.

Closes the agent loop without a second database, authority grant, or new organ.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .activation import activate_repository
from .bridge import consolidate
from .hippocampus import remember


def run_session_ritual(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    task: str,
    *,
    budget: int = 1200,
    memories: list[dict[str, str]] | None = None,
    consolidate_session: bool = True,
    profile: str = "agent",
    force: bool = False,
) -> dict[str, Any]:
    """Run the full Cortex session loop on an attached repository.

    memories: optional list of {kind, text} events recorded after activate.
    """

    activation = activate_repository(
        home, store, governor, repo, task, budget=budget, profile=profile
    )
    session_id = (activation.get("session") or {}).get("session_id")
    control = activation.get("control_error") or (
        (activation.get("context_full") or activation.get("context") or {}).get(
            "control_error"
        )
    ) or {}
    blocked = bool(control.get("must_reverify")) and not force
    recorded: list[dict[str, Any]] = []
    for item in memories or []:
        kind = str(item.get("kind") or "discovery").strip() or "discovery"
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        recorded.append(
            remember(
                home,
                store,
                repo,
                kind,
                text,
                session_id=session_id,
            )
        )
    card: dict[str, Any] | None = None
    if consolidate_session:
        if blocked:
            card = {
                "created": False,
                "status": "blocked_by_governor",
                "reason": "control_error.must_reverify; re-verify or pass force",
                "control_error": control,
            }
        else:
            card = consolidate(home, store, repo, session_id)
    context = activation.get("context") or {}
    full = activation.get("context_full") or context
    return {
        "schema_version": "cortex-session-ritual/1.1",
        "glyph": "⟳",
        "repo": repo,
        "task": task,
        "profile": profile,
        "session_id": session_id,
        "activation": activation.get("activation"),
        "control_error": control,
        "blocked_by_control_error": blocked,
        "governor_mode": (full.get("governor") or context.get("governor") or {}).get(
            "mode"
        )
        or context.get("governor_mode"),
        "geometry_zero_point": (full.get("geometry") or context.get("geometry") or {}).get(
            "zero_point"
        ),
        "aria_materialization": full.get("aria_materialization")
        or context.get("aria_materialization"),
        "evidence_count": len(
            full.get("evidence") or context.get("evidence") or []
        ),
        "surprise": activation.get("surprise"),
        "organism": activation.get("organism"),
        "remembered": recorded,
        "consolidate": card,
        "ritual": ["activate", "remember", "consolidate"],
        "cardiac_cycle": {
            "systole": "activate+work",
            "diastole": "remember+consolidate",
            "pulse": (activation.get("organism") or {}).get("pulse"),
            "sealed": bool((card or {}).get("created")),
        },
        "authority": {
            "cortex_may_mutate": False,
            "packet_is_not_authorization": True,
        },
        "claim_boundary": (
            "Session ritual records and consolidates explicit events only; "
            "it never authorizes repository mutation."
        ),
    }
