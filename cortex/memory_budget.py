"""v8.9 — Trial-guided projection budgets.

Uses cross-instantiation trial gains (G_rehydration, G_credit) to refine
*projection shape* (max_memories, feedback inclusion, type priority mode).

Never rewrites admitted truth status, invents memories, mutates host, or
auto-executes. Measurement ≠ authority. Utility ≠ truth.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__
from .admitted_memory import list_admitted_memories

SCHEMA = "cortex-projection-budget/1.0"
AGGREGATE_SCHEMA = "cortex-trial-aggregate/1.0"
APPLY_SCHEMA = "cortex-budget-apply/1.0"
VERSION = "8.9.0"
GLYPH = "⧉⚖↗📐"
CLAIM_BOUNDARY = (
    "Trial-guided budgets refine projection shape under operator seal. "
    "They do not prove continuity of mind, authorize host mutation, rewrite "
    "evidence, or promote memories. Measurement ≠ authority. Utility ≠ truth."
)

K_MIN = 3
EPSILON_REHYDRATE = 0.02
EPSILON_CREDIT = 0.01
MAX_MEMORIES_MIN = 4
MAX_MEMORIES_MAX = 24
DEFAULT_MAX_MEMORIES = 12

MODES = (
    "DEFAULT",
    "STRUCTURE_ONLY",
    "EXPAND_CAUTIOUS",
    "CONTRACT",
    "FEEDBACK_ON",
    "FREEZE",
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def default_budget_policy() -> dict[str, Any]:
    return {
        "max_memories": DEFAULT_MAX_MEMORIES,
        "include_use_feedback": False,
        "type_priority": "will_order",
        "forbid_stale_as_fact": True,
        "min_support": None,
        "mode": "DEFAULT",
        "calibrated": False,
        "structure_only": False,
    }


def _clip_max_memories(n: int) -> int:
    return max(MAX_MEMORIES_MIN, min(MAX_MEMORIES_MAX, int(n)))


def _admitted_count(store: Any, repo: str) -> int:
    try:
        return len(list_admitted_memories(store, repo, limit=5000))
    except Exception:
        return 0


def _freeze_reasons(store: Any, repo: str) -> list[str]:
    """Detect conditions that freeze budget apply (not trial measurement).

    Absent body epoch does not freeze — hermetic/bootstrap hosts may apply
    structure defaults. A *present but stale* sealed epoch freezes apply.
    """
    reasons: list[str] = []
    try:
        from .epoch import observe_current_epoch

        obs = observe_current_epoch(store, repo)
        if obs.get("present") and (obs.get("stale") or not obs.get("verified")):
            reasons.append("epoch_stale_or_mismatched")
    except Exception:
        pass
    # Lightweight immune / governor tip if present
    try:
        immune = store.get_setting(f"immune_latest:{repo}", None) or {}
        if immune.get("block") is True:
            reasons.append("immune_block")
    except Exception:
        pass
    try:
        gov = store.get_setting(f"governor_latest:{repo}", None) or {}
        if str(gov.get("mode") or "") == "read_only":
            reasons.append("governor_read_only")
    except Exception:
        pass
    return reasons


def aggregate_trial_history(
    store: Any,
    repo: str,
    *,
    window: int = 32,
    persist: bool = True,
) -> dict[str, Any]:
    """Rolling aggregate of last N trial history tips."""
    history = list(store.get_setting(f"memory_trial_history:{repo}", []) or [])
    recent = [h for h in history if isinstance(h, Mapping)][-max(1, int(window)) :]
    g_r: list[float] = []
    g_c: list[float] = []
    for h in recent:
        try:
            if h.get("G_rehydration") is not None:
                g_r.append(float(h["G_rehydration"]))
            if h.get("G_credit") is not None:
                g_c.append(float(h["G_credit"]))
        except (TypeError, ValueError):
            continue
    k = len(recent)
    mean_r = statistics.fmean(g_r) if g_r else None
    mean_c = statistics.fmean(g_c) if g_c else None
    stdev_r = statistics.stdev(g_r) if len(g_r) >= 2 else None
    stdev_c = statistics.stdev(g_c) if len(g_c) >= 2 else None
    measured = k >= K_MIN and mean_r is not None
    material = {
        "schema_version": AGGREGATE_SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "trial_aggregate",
        "repo": repo,
        "K": k,
        "K_min": K_MIN,
        "window": window,
        "G_rehydration_mean": round(mean_r, 6) if mean_r is not None else None,
        "G_credit_mean": round(mean_c, 6) if mean_c is not None else None,
        "G_rehydration_stdev": round(stdev_r, 6) if stdev_r is not None else None,
        "G_credit_stdev": round(stdev_c, 6) if stdev_c is not None else None,
        "measured": measured,
        "measurement_status": "measured" if measured else "unmeasured",
        "epsilon": {
            "rehydrate": EPSILON_REHYDRATE,
            "credit": EPSILON_CREDIT,
        },
        "history_receipt_hashes": [h.get("receipt_hash") for h in recent],
        "advisory_only": True,
        "policy_effect": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
        "created_at": time.time(),
    }
    material["receipt_hash"] = _sha(material)
    if persist:
        store.set_setting(f"trial_aggregate_latest:{repo}", material)
    return material


def propose_budget(
    store: Any,
    repo: str,
    *,
    aggregate: Mapping[str, Any] | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Advisory budget proposal from trial aggregate + ledger emptiness."""
    agg = dict(aggregate or aggregate_trial_history(store, repo, persist=False))
    admitted_n = _admitted_count(store, repo)
    freeze = _freeze_reasons(store, repo)
    base = default_budget_policy()
    mode = "DEFAULT"
    reasons: list[str] = []
    max_m = DEFAULT_MAX_MEMORIES
    include_fb = False
    type_priority = "will_order"
    calibrated = False

    # Shape mode first; freeze is an apply gate (may coexist with STRUCTURE_ONLY).
    if admitted_n == 0:
        mode = "STRUCTURE_ONLY"
        type_priority = "structure_only"
        include_fb = False
        reasons.append("admitted_count_zero")
    else:
        k = int(agg.get("K") or 0)
        mean_r = agg.get("G_rehydration_mean")
        mean_c = agg.get("G_credit_mean")
        if k < K_MIN or mean_r is None:
            mode = "DEFAULT"
            reasons.append("K_below_min" if k < K_MIN else "G_rehydration_unmeasured")
        else:
            calibrated = True
            gr = float(mean_r)
            if gr > EPSILON_REHYDRATE:
                mode = "EXPAND_CAUTIOUS"
                max_m = _clip_max_memories(DEFAULT_MAX_MEMORIES + 4)
                reasons.append("G_rehydration_above_epsilon")
            elif gr < -EPSILON_REHYDRATE:
                mode = "CONTRACT"
                max_m = _clip_max_memories(DEFAULT_MAX_MEMORIES - 4)
                reasons.append("G_rehydration_below_neg_epsilon")
            else:
                mode = "DEFAULT"
                reasons.append("G_rehydration_within_band")
            if mean_c is not None and float(mean_c) > EPSILON_CREDIT:
                include_fb = True
                reasons.append("G_credit_above_epsilon")
                if mode == "EXPAND_CAUTIOUS":
                    mode = "FEEDBACK_ON"

    if freeze:
        reasons.extend(freeze)
        reasons.append("budget_apply_frozen")
        if mode != "STRUCTURE_ONLY":
            mode = "FREEZE"

    policy = {
        **base,
        "max_memories": max_m,
        "include_use_feedback": bool(include_fb),
        "type_priority": type_priority,
        "mode": mode,
        "calibrated": calibrated,
        "structure_only": mode == "STRUCTURE_ONLY" or type_priority == "structure_only",
    }
    apply_frozen = bool(freeze) or mode == "FREEZE"
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "projection_budget_proposal",
        "repo": repo,
        "policy": policy,
        "mode": mode,
        "reasons": reasons,
        "admitted_count": admitted_n,
        "aggregate": {
            "K": agg.get("K"),
            "measured": agg.get("measured"),
            "G_rehydration_mean": agg.get("G_rehydration_mean"),
            "G_credit_mean": agg.get("G_credit_mean"),
            "measurement_status": agg.get("measurement_status"),
        },
        "freeze_reasons": freeze,
        "apply_allowed": (not apply_frozen)
        and (calibrated or mode == "STRUCTURE_ONLY"),
        "apply_requires_authorization": True,
        "apply_blocked_if_unmeasured": not calibrated and mode not in {
            "STRUCTURE_ONLY",
            "FREEZE",
        },
        "advisory_only": True,
        "policy_effect": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "learning_authorized": False,
        "truth_status_rewritten": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
        "created_at": time.time(),
    }
    material["receipt_hash"] = _sha(
        {k: v for k, v in material.items() if k != "receipt_hash"}
    )
    if persist:
        store.set_setting(f"projection_budget_proposal_latest:{repo}", material)
    return material


def apply_budget(
    store: Any,
    repo: str,
    *,
    authorized: bool = False,
    force_unmeasured: bool = False,
    policy_override: Mapping[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Operator-authorized application of a projection budget tip."""
    proposal = propose_budget(store, repo, persist=False)
    if not authorized:
        return {
            **proposal,
            "kind": "projection_budget_apply",
            "applied": False,
            "errors": ["missing_i_authorize_budget"],
            "active_policy": resolve_active_budget(store, repo),
        }
    if proposal.get("mode") == "FREEZE" or proposal.get("freeze_reasons"):
        return {
            **proposal,
            "kind": "projection_budget_apply",
            "applied": False,
            "errors": ["budget_frozen"] + list(proposal.get("freeze_reasons") or ()),
            "active_policy": resolve_active_budget(store, repo),
        }
    if proposal.get("apply_blocked_if_unmeasured") and not force_unmeasured:
        return {
            **proposal,
            "kind": "projection_budget_apply",
            "applied": False,
            "errors": ["unmeasured_aggregate_requires_force_or_more_trials"],
            "active_policy": resolve_active_budget(store, repo),
            "hint": f"need K>={K_MIN} measured trials or --force-unmeasured",
        }

    policy = dict(proposal.get("policy") or default_budget_policy())
    if policy_override:
        # Only allow safe shape fields
        for key in (
            "max_memories",
            "include_use_feedback",
            "type_priority",
            "min_support",
            "mode",
        ):
            if key in policy_override:
                policy[key] = policy_override[key]
        policy["max_memories"] = _clip_max_memories(
            int(policy.get("max_memories") or DEFAULT_MAX_MEMORIES)
        )
        policy["forbid_stale_as_fact"] = True  # never overridable
        policy["structure_only"] = policy.get("mode") == "STRUCTURE_ONLY" or policy.get(
            "type_priority"
        ) == "structure_only"

    tip = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "projection_budget_policy",
        "repo": repo,
        "policy": policy,
        "mode": policy.get("mode"),
        "source_proposal_hash": proposal.get("receipt_hash"),
        "aggregate_K": (proposal.get("aggregate") or {}).get("K"),
        "G_rehydration_mean": (proposal.get("aggregate") or {}).get("G_rehydration_mean"),
        "G_credit_mean": (proposal.get("aggregate") or {}).get("G_credit_mean"),
        "is_default": False,
        "operator_authorized": True,
        "advisory_only": False,
        "policy_effect": True,  # affects projection shape only
        "truth_status_rewritten": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "learning_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
        "created_at": time.time(),
    }
    tip["budget_policy_hash"] = _sha(
        {k: tip[k] for k in ("policy", "mode", "repo", "source_proposal_hash")}
    )
    tip["receipt_hash"] = _sha(tip)

    apply_receipt = {
        "schema_version": APPLY_SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "projection_budget_apply",
        "repo": repo,
        "applied": True,
        "errors": [],
        "policy": policy,
        "mode": policy.get("mode"),
        "budget_policy_hash": tip["budget_policy_hash"],
        "proposal_hash": proposal.get("receipt_hash"),
        "force_unmeasured": bool(force_unmeasured),
        "truth_status_rewritten": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
        "created_at": time.time(),
    }
    apply_receipt["receipt_hash"] = _sha(apply_receipt)
    event_id = "evt_" + _sha(
        {"kind": "budget_apply", "repo": repo, "h": tip["budget_policy_hash"]}
    )[:24]
    apply_receipt["event_id"] = event_id

    if persist:
        try:
            store.append_projection_budget_receipt(repo, apply_receipt)
        except Exception:
            pass
        store.set_setting(f"projection_budget_active:{repo}", tip)
        history = list(store.get_setting(f"projection_budget_history:{repo}", []) or [])
        history.append(
            {
                "budget_policy_hash": tip["budget_policy_hash"],
                "mode": tip.get("mode"),
                "max_memories": policy.get("max_memories"),
                "include_use_feedback": policy.get("include_use_feedback"),
                "created_at": tip["created_at"],
            }
        )
        store.set_setting(f"projection_budget_history:{repo}", history[-32:])
    return {
        **apply_receipt,
        "active_policy": tip,
        "proposal": {
            "receipt_hash": proposal.get("receipt_hash"),
            "mode": proposal.get("mode"),
            "reasons": proposal.get("reasons"),
        },
    }


def resolve_active_budget(store: Any, repo: str) -> dict[str, Any]:
    """Active sealed tip or fail-closed default (never invents)."""
    tip = store.get_setting(f"projection_budget_active:{repo}", None)
    if isinstance(tip, Mapping) and tip.get("policy"):
        return dict(tip)
    policy = default_budget_policy()
    # Empty ledger: structure-only default without requiring apply
    if _admitted_count(store, repo) == 0:
        policy = {
            **policy,
            "mode": "STRUCTURE_ONLY",
            "type_priority": "structure_only",
            "structure_only": True,
            "include_use_feedback": False,
        }
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "kind": "projection_budget_policy",
        "repo": repo,
        "policy": policy,
        "mode": policy.get("mode"),
        "budget_policy_hash": _sha({"policy": policy, "repo": repo, "default": True}),
        "is_default": True,
        "operator_authorized": False,
        "advisory_only": True,
        "policy_effect": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }


def budget_status(store: Any, repo: str) -> dict[str, Any]:
    agg = aggregate_trial_history(store, repo, persist=False)
    proposal = propose_budget(store, repo, aggregate=agg, persist=False)
    active = resolve_active_budget(store, repo)
    history = list(store.get_setting(f"projection_budget_history:{repo}", []) or [])
    return {
        "schema_version": "cortex-projection-budget-status/1.0",
        "version": VERSION,
        "glyph": GLYPH,
        "repo": repo,
        "active": {
            "mode": active.get("mode"),
            "budget_policy_hash": active.get("budget_policy_hash"),
            "policy": active.get("policy"),
            "is_default": active.get("is_default", False),
            "operator_authorized": active.get("operator_authorized", False),
        },
        "proposal": {
            "mode": proposal.get("mode"),
            "reasons": proposal.get("reasons"),
            "policy": proposal.get("policy"),
            "apply_allowed": proposal.get("apply_allowed"),
            "receipt_hash": proposal.get("receipt_hash"),
        },
        "aggregate": {
            "K": agg.get("K"),
            "measured": agg.get("measured"),
            "measurement_status": agg.get("measurement_status"),
            "G_rehydration_mean": agg.get("G_rehydration_mean"),
            "G_credit_mean": agg.get("G_credit_mean"),
        },
        "admitted_count": proposal.get("admitted_count"),
        "freeze_reasons": proposal.get("freeze_reasons"),
        "history_len": len(history),
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "truth_status_rewritten": False,
    }


def refresh_after_trial(store: Any, repo: str) -> dict[str, Any]:
    """Called after a memory trial persists — refresh aggregate tip only."""
    return aggregate_trial_history(store, repo, persist=True)


__all__ = [
    "AGGREGATE_SCHEMA",
    "APPLY_SCHEMA",
    "CLAIM_BOUNDARY",
    "DEFAULT_MAX_MEMORIES",
    "EPSILON_CREDIT",
    "EPSILON_REHYDRATE",
    "K_MIN",
    "MODES",
    "SCHEMA",
    "VERSION",
    "aggregate_trial_history",
    "apply_budget",
    "budget_status",
    "default_budget_policy",
    "propose_budget",
    "refresh_after_trial",
    "resolve_active_budget",
]
