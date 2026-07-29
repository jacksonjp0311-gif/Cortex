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
    contract: str = "default",
) -> dict[str, Any]:
    """Run the full Cortex session loop on an attached repository.

    memories: optional list of {kind, text} events recorded after activate.
    contract: default | strict | off — seal gates (constrain only).
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
    # Seal gates: must_reverify OR immune block (unless force)
    blocked = bool(
        ((control.get("must_reverify") or control.get("block")) and not force)
    )
    block_reason = None
    if blocked:
        if control.get("block"):
            block_reason = "immune_block"
        elif control.get("must_reverify"):
            block_reason = "must_reverify"

    # Contract gate on seal
    contract_check: dict[str, Any] | None = None
    if contract not in {"off", "none", ""} and consolidate_session and not blocked:
        try:
            from .contract.check import DEFAULT_CONTRACT, STRICT_CONTRACT, check_contract

            profile_c = STRICT_CONTRACT if contract == "strict" else DEFAULT_CONTRACT
            full_ctx = activation.get("context_full") or activation.get("context") or {}
            packet_like = {
                "governor": full_ctx.get("governor") or {"mode": control.get("work_allowed")},
                "control_error": control,
                "authority": {
                    "cortex_may_mutate": False,
                    "packet_is_not_authorization": True,
                },
                "claim_boundary": full_ctx.get("claim_boundary") or "ritual",
                "operational_state": {
                    "evidence_ids": [
                        e.get("memory_id")
                        for e in (full_ctx.get("evidence") or [])
                        if e.get("memory_id")
                    ]
                },
                "geometry": full_ctx.get("geometry"),
            }
            # normalize governor mode
            if not (packet_like["governor"] or {}).get("mode"):
                packet_like["governor"] = {
                    "mode": (full_ctx.get("governor") or {}).get("mode") or "normal"
                }
            contract_check = check_contract(
                packet_like,
                contract=profile_c,
                context=full_ctx,
                store=store,
                repo=repo,
                persist=True,
            )
            if contract == "strict" and not contract_check.get("passed") and not force:
                blocked = True
                block_reason = "contract_strict_failed"
        except Exception as exc:
            contract_check = {"error": f"{type(exc).__name__}: {exc}"}

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
                "status": "blocked_by_gate",
                "reason": block_reason
                or "control_error.must_reverify; re-verify or pass force",
                "control_error": control,
                "contract_check": contract_check,
            }
        else:
            card = consolidate(home, store, repo, session_id)
    context = activation.get("context") or {}
    full = activation.get("context_full") or context
    sealed = bool((card or {}).get("created"))
    return {
        "schema_version": "cortex-session-ritual/2.0",
        "glyph": "⟳",
        "repo": repo,
        "task": task,
        "profile": profile,
        "session_id": session_id,
        "activation": activation.get("activation"),
        "control_error": control,
        "blocked_by_control_error": blocked,
        "block_reason": block_reason,
        "contract": contract,
        "contract_check": contract_check,
        "gates_sealed": sealed and not blocked,
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
        "connect_pass": activation.get("connect_pass"),
        "remembered": recorded,
        "consolidate": card,
        "ritual": ["activate", "remember", "consolidate"],
        "cardiac_cycle": {
            "systole": "activate+work",
            "diastole": "remember+consolidate",
            "pulse": (activation.get("organism") or {}).get("pulse"),
            "sealed": sealed,
        },
        "authority": {
            "cortex_may_mutate": False,
            "packet_is_not_authorization": True,
        },
        "claim_boundary": (
            "Session ritual records and consolidates explicit events only; "
            "gates seal under immune/contract; never authorizes repository mutation."
        ),
    }
