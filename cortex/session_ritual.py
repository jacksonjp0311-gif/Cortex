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
) -> dict[str, Any]:
    """Run the full Cortex session loop on an attached repository.

    memories: optional list of {kind, text} events recorded after activate.
    """

    activation = activate_repository(
        home, store, governor, repo, task, budget=budget
    )
    session_id = (activation.get("session") or {}).get("session_id")
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
        card = consolidate(home, store, repo, session_id)
    context = activation.get("context") or {}
    return {
        "schema_version": "cortex-session-ritual/1.0",
        "repo": repo,
        "task": task,
        "session_id": session_id,
        "activation": activation.get("activation"),
        "governor_mode": (context.get("governor") or {}).get("mode"),
        "geometry_zero_point": (context.get("geometry") or {}).get("zero_point"),
        "aria_materialization": context.get("aria_materialization"),
        "evidence_count": len(context.get("evidence") or []),
        "remembered": recorded,
        "consolidate": card,
        "ritual": ["activate", "remember", "consolidate"],
        "authority": {
            "cortex_may_mutate": False,
            "packet_is_not_authorization": True,
        },
        "claim_boundary": (
            "Session ritual records and consolidates explicit events only; "
            "it never authorizes repository mutation."
        ),
    }
