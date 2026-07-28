"""Selective lifecycle controls for learned neural associations."""

from __future__ import annotations

import json
import math
import time
from typing import Any


RELATION_RETENTION = {
    "tested_by": 0.35,
    "resolves_to": 0.45,
    "co_changed": 0.70,
    "described_by": 0.75,
    "imports": 0.80,
    "references": 0.90,
    "documents": 0.90,
    "calls": 0.85,
}


def _last_activated(store: Any, repo: str, limit: int = 10_000) -> dict[str, float]:
    latest: dict[str, float] = {}
    for row in store.neural_events(repo, limit):
        if row["event_type"] != "sparse_activation":
            continue
        payload = json.loads(row["payload"] or "{}")
        for synapse_id in payload.get("traversed_synapses", []):
            latest.setdefault(str(synapse_id), float(row["created_at"]))
    return latest


def lifecycle_plan(
    store: Any,
    repo: str,
    *,
    now: float | None = None,
    grace_hours: float = 24.0,
    decay_per_day: float = 0.05,
) -> dict[str, Any]:
    """Propose selective decay of learned deviation toward structural priors.

    Structural edges are evidence-plane topology and never disappear here.
    Lifecycle decay retires only learned weight deviation, making the operation
    recoverable through recompilation and preserving low-activation evidence.
    """
    observed_at = time.time() if now is None else now
    last_activated = _last_activated(store, repo)
    proposals: list[dict[str, Any]] = []
    protected = 0
    unchanged = 0
    for row in store.neural_synapses(repo):
        last_use = max(float(row["updated_at"]), last_activated.get(row["synapse_id"], 0.0))
        age_hours = max(0.0, (observed_at - last_use) / 3600.0)
        if age_hours <= grace_hours:
            protected += 1
            continue
        old = float(row["weight"])
        base = float(row["base_weight"])
        deviation = old - base
        if abs(deviation) <= 1e-9:
            unchanged += 1
            continue
        relation = str(row["relation"]).removeprefix("reverse:")
        relation_factor = RELATION_RETENTION.get(relation, 1.0)
        active_days = (age_hours - grace_hours) / 24.0
        survival = math.exp(-max(0.0, decay_per_day) * relation_factor * active_days)
        proposed = base + deviation * survival
        proposed = max(float(row["minimum_weight"]), min(float(row["maximum_weight"]), proposed))
        proposals.append(
            {
                "synapse_id": row["synapse_id"],
                "relation": row["relation"],
                "old_weight": old,
                "base_weight": base,
                "proposed_weight": round(proposed, 8),
                "delta": round(proposed - old, 8),
                "age_hours": round(age_hours, 4),
                "survival": round(survival, 8),
                "effective_age": round(-math.log(max(survival, 1e-12)), 8),
            }
        )
    return {
        "repo": repo,
        "policy": "selective learned-deviation decay toward evidence-backed structural priors",
        "grace_hours": grace_hours,
        "decay_per_day": decay_per_day,
        "synapses": len(store.neural_synapses(repo)),
        "protected_by_grace": protected,
        "already_at_prior": unchanged,
        "proposed_updates": len(proposals),
        "proposals": proposals,
        "claim_boundary": "Decay retires learned routing deviation; it does not delete evidence or source topology.",
    }


def apply_lifecycle(
    store: Any,
    repo: str,
    *,
    governance_mode: str,
    authorized: bool,
    now: float | None = None,
    grace_hours: float = 24.0,
    decay_per_day: float = 0.05,
) -> dict[str, Any]:
    plan = lifecycle_plan(
        store,
        repo,
        now=now,
        grace_hours=grace_hours,
        decay_per_day=decay_per_day,
    )
    allowed = authorized and governance_mode in {"normal", "constrained"}
    if not allowed or not plan["proposals"]:
        return {
            **plan,
            "applied": False,
            "governance_mode": governance_mode,
            "reason": (
                "explicit authority and normal/constrained governance are required"
                if not allowed
                else "no learned deviation is eligible for decay"
            ),
        }
    with store.transaction() as conn:
        for proposal in plan["proposals"]:
            conn.execute(
                """UPDATE neural_synapses
                   SET weight=?, update_count=update_count+1, updated_at=?
                   WHERE repo=? AND synapse_id=?""",
                (
                    proposal["proposed_weight"],
                    time.time() if now is None else now,
                    repo,
                    proposal["synapse_id"],
                ),
            )
        store._append_neural_event_conn(
            conn,
            repo,
            event_type="lifecycle_decay",
            entity_id=repo,
            payload={
                "policy": plan["policy"],
                "grace_hours": grace_hours,
                "decay_per_day": decay_per_day,
                "updates": plan["proposals"],
            },
        )
    return {
        **plan,
        "applied": True,
        "governance_mode": governance_mode,
        "graph_hash_after": store.neural_graph_hash(repo),
    }
