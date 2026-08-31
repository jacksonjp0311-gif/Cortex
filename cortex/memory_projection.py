"""v8.7 — Eligibility gates and task-bound memory projection (rehydration)."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Mapping
from typing import Any

from . import __version__
from .admitted_memory import list_admitted_memories
from .memory_state import (
    current_memory_state,
)
from .will import verify_will

SCHEMA = "cortex-memory-projection/1.0"
ELIGIBILITY_SCHEMA = "cortex-memory-eligibility/1.0"
VERSION = "8.9.3"
GLYPH = "⧉↗"
CLAIM_BOUNDARY = (
    "Memory projection is a governed rehydration of admitted memories into a "
    "task-bound context. It does not invent memories, authorize host mutation, "
    "or execute tools. available ≠ cited ≠ useful."
)

SUPPORT_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}
ACTIVE_OK = frozenset({"active"})  # only active enters guidance; contested surfaces separately


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]{3,}", (text or "").lower()) if t}


def evaluate_memory_eligibility(
    store: Any,
    repo: str,
    memory: Mapping[str, Any],
    *,
    live_epoch_id: str | None = None,
    current_will: Mapping[str, Any] | None = None,
    will_secret: str | None = None,
    task: str = "",
    min_support: str = "low",
    require_deep_lineage: bool = True,
    structural_inspection: bool = False,
) -> dict[str, Any]:
    """Noncompensatory gates G_M. G_M=0 excludes from active guidance."""
    from .admitted_memory import deep_verify_admitted_memory

    memory_id = str(memory.get("memory_id") or "")
    # Eligibility is observational.  In particular, it must never seed an
    # overlay or append ``epoch_stale`` merely because the caller read a row.
    tip = current_memory_state(store, repo, memory_id)
    state = str(tip.get("state") or "active")
    gates = {
        "integrity": True,
        "state": state in ACTIVE_OK,
        "epoch": True,
        "schema": True,
        "scope": True,
        "will": True,
        "support": True,
    }
    exclusions: list[str] = []

    # integrity / lineage
    if require_deep_lineage:
        deep = deep_verify_admitted_memory(store, repo, memory)
        gates["integrity"] = bool(deep.get("lineage_validity"))
        if not gates["integrity"]:
            exclusions.append("lineage_invalid")
    else:
        structural = bool(memory.get("receipt_hash")) and bool(memory.get("candidate_id"))
        if memory.get("host_mutate_authorized") or memory.get("execution_authorized"):
            structural = False
        if memory.get("from_chat_text") or memory.get("invented"):
            structural = False
        gates["integrity"] = structural
        if not structural:
            exclusions.append("lineage_invalid")

    if state not in ACTIVE_OK:
        if state == "contested":
            exclusions.append("contradiction_unresolved")
        elif state == "superseded":
            exclusions.append("state_not_active")
        elif state == "epoch_stale":
            exclusions.append("epoch_mismatch")
        else:
            exclusions.append("state_not_active")

    mem_epoch = str(memory.get("body_epoch_id") or "")
    if live_epoch_id and mem_epoch and mem_epoch != str(live_epoch_id):
        gates["epoch"] = False
        if "epoch_mismatch" not in exclusions:
            exclusions.append("epoch_mismatch")

    support = str(memory.get("support_level") or "none")
    if SUPPORT_RANK.get(support, 0) < SUPPORT_RANK.get(min_support, 0):
        gates["support"] = False
        exclusions.append("support_below_threshold")

    # will: if current will forbids this type, exclude from active projection
    if current_will:
        v = verify_will(store, repo, current_will, secret=will_secret)
        latest = store.get_setting(f"will_latest:{repo}", None) or {}
        same_canonical_tip = bool(
            latest
            and latest.get("receipt_hash") == current_will.get("receipt_hash")
            and latest.get("will_id") == current_will.get("will_id")
        )
        if will_secret is not None:
            current_will_valid = v.get("verified") is True
        else:
            structural_checks = dict(v.get("checks") or {})
            for deferred in (
                "signature",
                "signature_deferred",
                "principal_secret_match",
            ):
                structural_checks.pop(deferred, None)
            current_will_valid = same_canonical_tip and all(structural_checks.values())
        if not current_will_valid:
            gates["will"] = False
            exclusions.append("current_will_forbids")
        else:
            ctype = str(memory.get("candidate_type") or "")
            forbid: set[str] = set()
            admit: set[str] = set()
            for clause in current_will.get("clauses") or ():
                if not isinstance(clause, Mapping):
                    continue
                kind = str(clause.get("kind") or "")
                types = {str(t) for t in (clause.get("candidate_types") or ())}
                if kind == "forbid_type":
                    forbid |= types
                if kind in {"admit_type", "prioritize_type"}:
                    admit |= types
            if ctype in forbid:
                gates["will"] = False
                exclusions.append("current_will_forbids")
            # If will declares admit types, require membership when non-empty
            if admit and ctype not in admit:
                gates["will"] = False
                if "current_will_forbids" not in exclusions:
                    exclusions.append("current_will_forbids")

    # soft scope: if task tokens share nothing with summary, exclude as outside scope
    # only when task is non-empty
    if task.strip():
        tset = _tokens(task)
        mset = _tokens(str(memory.get("summary") or "") + " " + str(memory.get("candidate_type") or ""))
        if tset and mset and not (tset & mset):
            # do not hard-fail scope for constraints/warnings — they are global
            ctype = str(memory.get("candidate_type") or "")
            if ctype not in {
                "persistent_constraint",
                "regime_warning",
                "unresolved_ambiguity",
            }:
                gates["scope"] = False
                exclusions.append("outside_task_scope")

    product = 1 if all(gates.values()) else 0
    return {
        "schema_version": ELIGIBILITY_SCHEMA,
        "version": VERSION,
        "kind": "memory_eligibility",
        "repo": repo,
        "memory_id": memory_id,
        "gates": gates,
        "G_M": product,
        "eligible": product == 1,
        "current_state": state,
        "exclusions": sorted(set(exclusions)),
        "contested_visible": state == "contested",
        "historical_visible": True,
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
    }


def _rank_score(
    memory: Mapping[str, Any],
    *,
    task: str,
    utility: float = 0.0,
) -> float:
    """Deterministic ranking for eligible memories only."""
    tset = _tokens(task)
    mset = _tokens(str(memory.get("summary") or "") + " " + str(memory.get("candidate_type") or ""))
    rel = (len(tset & mset) / max(1, len(tset))) if tset else 0.15
    support = SUPPORT_RANK.get(str(memory.get("support_level") or "none"), 0) / 3.0
    recency = 0.5  # without timestamps diversity; created_at optional
    try:
        age = time.time() - float(memory.get("created_at") or time.time())
        recency = max(0.0, min(1.0, 1.0 - age / (86400 * 30)))
    except (TypeError, ValueError):
        pass
    cost = min(1.0, len(str(memory.get("summary") or "")) / 400.0)
    # conflict burden lower for non-contested (eligibility already filtered)
    conflict = 0.0
    return (
        0.35 * rel
        + 0.25 * support
        + 0.20 * max(0.0, utility)
        + 0.15 * recency
        - 0.10 * cost
        - 0.15 * conflict
    )


def project_memories(
    store: Any,
    repo: str,
    *,
    task: str,
    session_id: str = "",
    turn_id: int = 0,
    body_epoch_id: str | None = None,
    current_will: Mapping[str, Any] | None = None,
    will_secret: str | None = None,
    max_memories: int | None = None,
    min_support: str | None = None,
    require_deep_lineage: bool = True,
    structural_inspection: bool = False,
    budget: Mapping[str, Any] | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Build deterministic MemoryProjectionReceipt for a task.

    When max_memories / min_support are omitted, resolves active projection
    budget tip (v8.9). Explicit args always win over the budget tip.
    """
    budget_tip: dict[str, Any] | None = None
    if budget is not None:
        budget_tip = dict(budget)
    else:
        try:
            from .memory_budget import resolve_active_budget

            budget_tip = resolve_active_budget(store, repo)
        except Exception:
            budget_tip = None
    policy = dict((budget_tip or {}).get("policy") or {})
    resolved_max = (
        int(max_memories)
        if max_memories is not None
        else int(policy.get("max_memories") or 12)
    )
    resolved_max = max(1, resolved_max)
    resolved_min_support = (
        str(min_support)
        if min_support is not None
        else str(policy.get("min_support") or "low")
    )
    if policy.get("min_support") is None and min_support is None:
        resolved_min_support = "low"
    max_memories = resolved_max
    min_support = resolved_min_support

    live_epoch = str(body_epoch_id or "")
    if not live_epoch:
        try:
            from .epoch import observe_current_epoch

            obs = observe_current_epoch(store, repo)
            live_epoch = str(obs.get("live_epoch_id") or obs.get("epoch_id") or "")
        except Exception:
            live_epoch = ""

    memories = list_admitted_memories(store, repo, limit=5000)
    state_before: dict[str, list[dict[str, Any]]] = {
        str(mem.get("memory_id") or ""): list(
            store.list_memory_state_receipts(repo, str(mem.get("memory_id") or ""))
        )
        for mem in memories
    }

    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    contested: list[dict[str, Any]] = []
    for mem in memories:
        elig = evaluate_memory_eligibility(
            store,
            repo,
            mem,
            live_epoch_id=live_epoch or None,
            current_will=current_will,
            will_secret=will_secret,
            task=task,
            min_support=min_support,
            # Structural inspection can describe a shallow row, but it can
            # never make that row active model guidance.
            require_deep_lineage=(not structural_inspection) or require_deep_lineage,
        )
        item = {
            "memory_id": mem.get("memory_id"),
            "candidate_type": mem.get("candidate_type"),
            "summary": mem.get("summary"),
            "support_level": mem.get("support_level"),
            "current_state": elig.get("current_state"),
            "source": mem.get("source"),
            "receipt_hash": mem.get("receipt_hash"),
            "eligibility": elig,
            "historically_admitted": True,
            "admission_was_authorized": bool(mem.get("memory_write_authorized") or mem.get("durable_write_authorized")),
            "current_memory_write_authorized": False,
            "current_host_mutate_authorized": False,
            "current_execution_authorized": False,
        }
        if elig.get("contested_visible"):
            contested.append(item)
        if elig.get("eligible") and not structural_inspection:
            score = _rank_score(mem, task=task)
            item["rank_score"] = round(score, 6)
            item["why_selected"] = (
                f"eligible G_M=1; score={item['rank_score']}; "
                f"type={mem.get('candidate_type')}; support={mem.get('support_level')}"
            )
            eligible.append(item)
        else:
            item["exclusion_reasons"] = elig.get("exclusions")
            excluded.append(item)

    # type_priority from budget: structure_only keeps score order without type boosts
    type_priority = str(policy.get("type_priority") or "will_order")
    if type_priority == "structure_only":
        # No type ranking innovations — stable memory_id order after score
        eligible.sort(
            key=lambda x: (
                -float(x.get("rank_score") or 0),
                str(x.get("memory_id") or ""),
            )
        )
    else:
        eligible.sort(
            key=lambda x: (
                -float(x.get("rank_score") or 0),
                str(x.get("memory_id") or ""),
            )
        )
    selected = eligible[: max(1, int(max_memories))]
    # Historical evidence remains inspectable even when it is not active
    # guidance.  It is never promoted by ranking.
    historical_memory_ids = [str(mem.get("memory_id") or "") for mem in memories]
    counterevidence_memory_ids = [
        str(mem.get("memory_id") or "")
        for mem in memories
        if str(mem.get("candidate_type") or "") in {"counterevidence", "failed_hypothesis"}
    ]
    task_hash = _sha({"task": task, "repo": repo})
    projection_id = "proj_" + _sha(
        {
            "repo": repo,
            "session": session_id,
            "turn": turn_id,
            "task": task_hash,
            "selected": [s.get("memory_id") for s in selected],
        }
    )[:20]

    # Continuity seed buckets
    seed = {
        "CURRENT_INVARIANTS": [
            s
            for s in selected
            if s.get("candidate_type") == "persistent_constraint"
        ],
        "PROVEN_PROCEDURES": [
            s for s in selected if s.get("candidate_type") == "successful_procedure"
        ],
        "ACTIVE_CONSTRAINTS": [
            s
            for s in selected
            if s.get("candidate_type")
            in {"persistent_constraint", "regime_warning"}
        ],
        "RECENT_FAILURES": [
            s
            for s in selected
            if s.get("candidate_type") in {"failed_hypothesis", "counterevidence"}
        ],
        "CONTESTED_MEMORIES": contested[: max_memories],
        "SUPERSEDED_ROUTES": [
            e
            for e in excluded
            if "state_not_active" in (e.get("exclusion_reasons") or ())
            and e.get("current_state") == "superseded"
        ][: max_memories],
        "OPEN_QUESTIONS": [
            s for s in selected if s.get("candidate_type") == "unresolved_ambiguity"
        ],
        "EVIDENCE_THAT_WOULD_CHANGE_THE_STATE": [
            "new_witnessed_outcome_against_summary",
            "epoch_transition_with_schema_change",
            "challenge_with_stronger_support",
            "will_clause_forbid_type",
        ],
    }

    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "memory_projection",
        "repo": repo,
        "projection_id": projection_id,
        "session_id": session_id,
        "turn_id": int(turn_id),
        "body_epoch_id": live_epoch,
        "current_will_hash": (current_will or {}).get("receipt_hash"),
        "task": task,
        "task_hash": task_hash,
        "query_terms": sorted(_tokens(task)),
        "eligible_memory_ids": [e.get("memory_id") for e in eligible],
        "selected_memory_ids": [s.get("memory_id") for s in selected],
        "historical_memory_ids": historical_memory_ids,
        "counterevidence_memory_ids": counterevidence_memory_ids,
        "selected": selected,
        "excluded_memory_ids_with_reasons": [
            {
                "memory_id": e.get("memory_id"),
                "reasons": e.get("exclusion_reasons"),
                "state": e.get("current_state"),
            }
            for e in excluded
        ],
        "contested": contested,
        "continuity_seed": seed,
        "token_budget": max_memories,
        "selection_algorithm": "deterministic_rank_v1",
        "budget_policy_hash": (budget_tip or {}).get("budget_policy_hash"),
        "budget_mode": (budget_tip or {}).get("mode") or policy.get("mode"),
        "budget_include_use_feedback": bool(policy.get("include_use_feedback")),
        "budget_structure_only": bool(
            policy.get("structure_only") or type_priority == "structure_only"
        ),
        "advisory_only": True,
        "policy_effect": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "learning_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    event_id = "evt_" + _sha(
        {"kind": "memory_projection", "projection_id": projection_id}
    )[:24]
    projection_digest = _sha(material)[:32]
    receipt_hash = _sha({**material, "event_id": event_id, "projection_digest": projection_digest})
    receipt = {
        **material,
        "projection_digest": projection_digest,
        "event_id": event_id,
        "receipt_hash": receipt_hash,
        "created_at": time.time(),
    }
    state_after: dict[str, list[dict[str, Any]]] = {
        str(mem.get("memory_id") or ""): list(
            store.list_memory_state_receipts(repo, str(mem.get("memory_id") or ""))
        )
        for mem in memories
    }
    receipt["durable_state_before"] = _sha(state_before)
    receipt["durable_state_after"] = _sha(state_after)
    receipt["durable_state_unchanged"] = state_before == state_after
    receipt["projection_write_scope"] = "receipt_only" if persist else "none"
    if persist:
        try:
            append_result = store.append_memory_projection_receipt(repo, receipt)
        except Exception as exc:
            return {
                **receipt,
                "canonical_persistence": "failed",
                "canonical_persistence_error": f"{type(exc).__name__}:{exc}",
                "persisted": False,
            }
        receipt = {
            **receipt,
            "canonical_persistence": "duplicate" if append_result.get("duplicate") else "committed",
            "persisted": True,
        }
        store.set_setting(f"memory_projection_latest:{repo}", receipt)
    else:
        receipt["canonical_persistence"] = "not_requested"
        receipt["persisted"] = False
    return receipt


__all__ = [
    "CLAIM_BOUNDARY",
    "ELIGIBILITY_SCHEMA",
    "SCHEMA",
    "VERSION",
    "evaluate_memory_eligibility",
    "project_memories",
]
