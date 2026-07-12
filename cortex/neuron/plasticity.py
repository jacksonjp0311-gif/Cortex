from __future__ import annotations

import math
import time
from dataclasses import dataclass


# ── Decay constants ──────────────────────────────────────────────────────────
# Default decay rate: weights lose 0.5% per day when not co-activated
# Synapses that have been recently active decay slower (grace period)
DECAY_RATE_PER_DAY = 0.005
DECAY_GRACE_HOURS = 24.0  # Synapses updated in last 24h don't decay
DECAY_FLOOR = 0.001       # Never decay below this (preserve existence)


@dataclass(frozen=True)
class PlasticityProposal:
    synapse_id: str
    old_weight: float
    proposed_weight: float
    delta: float
    reason: str

    def to_dict(self) -> dict[str, float | str]:
        return {
            "synapse_id": self.synapse_id,
            "old_weight": self.old_weight,
            "proposed_weight": self.proposed_weight,
            "delta": self.delta,
            "reason": self.reason,
        }


def bounded_hebbian(
    *,
    synapse_id: str,
    weight: float,
    minimum_weight: float,
    maximum_weight: float,
    pre: float,
    post: float,
    learning_rate: float,
) -> PlasticityProposal:
    """Move a weight toward its upper bound according to bounded co-activation."""

    raw_delta = learning_rate * max(0.0, pre) * max(0.0, post) * (maximum_weight - weight)
    proposed = min(maximum_weight, max(minimum_weight, weight + raw_delta))
    return PlasticityProposal(
        synapse_id=synapse_id,
        old_weight=weight,
        proposed_weight=proposed,
        delta=proposed - weight,
        reason="bounded_hebbian_coactivation",
    )


def bounded_decay(
    *,
    synapse_id: str,
    weight: float,
    minimum_weight: float,
    maximum_weight: float,
    last_updated: float | None = None,
    now: float | None = None,
    decay_rate: float = DECAY_RATE_PER_DAY,
    grace_hours: float = DECAY_GRACE_HOURS,
) -> PlasticityProposal:
    """Pull a weight toward its minimum when not recently co-activated.

    Uses exponential decay: w(t) = w_0 * exp(-rate * days_since_update).
    Synapses updated within grace_hours are exempt (they're "fresh").
    Result is clamped to [minimum_weight + floor, maximum_weight].
    """
    if now is None:
        now = time.time()

    # Grace period: recent updates don't decay
    if last_updated is not None:
        hours_since = (now - last_updated) / 3600.0
        if hours_since < grace_hours:
            return PlasticityProposal(
                synapse_id=synapse_id,
                old_weight=weight,
                proposed_weight=weight,
                delta=0.0,
                reason="decay_grace_period",
            )
        days_since = hours_since / 24.0
    else:
        # Never updated: assume it should decay at full rate
        days_since = 30.0  # effective ~14% decay for stale synapses

    # Exponential decay toward minimum
    raw_delta = -decay_rate * days_since * (weight - minimum_weight)
    proposed = max(minimum_weight + DECAY_FLOOR, weight + raw_delta)
    proposed = min(maximum_weight, proposed)
    return PlasticityProposal(
        synapse_id=synapse_id,
        old_weight=weight,
        proposed_weight=proposed,
        delta=proposed - weight,
        reason=f"bounded_decay:{days_since:.1f}d",
    )


def decay_proposals(
    synapses: list[dict],
    *,
    now: float | None = None,
    decay_rate: float = DECAY_RATE_PER_DAY,
    grace_hours: float = DECAY_GRACE_HOURS,
) -> list[PlasticityProposal]:
    """Batch decay: generate decay proposals for many synapses at once.

    `synapses` is a list of dicts with keys: synapse_id, weight, minimum_weight,
    maximum_weight, last_updated (epoch seconds, optional).
    """
    proposals: list[PlasticityProposal] = []
    for syn in synapses:
        proposal = bounded_decay(
            synapse_id=syn["synapse_id"],
            weight=syn["weight"],
            minimum_weight=syn["minimum_weight"],
            maximum_weight=syn["maximum_weight"],
            last_updated=syn.get("last_updated"),
            now=now,
            decay_rate=decay_rate,
            grace_hours=grace_hours,
        )
        proposals.append(proposal)
    return proposals


def decay_stats(synapses: list[dict], *, now: float | None = None) -> dict:
    """Summary of decay state across a set of synapses.

    Returns counts and weight distribution after applying decay proposals.
    Useful for reporting and verification.
    """
    proposals = decay_proposals(synapses, now=now)
    decayed = sum(1 for p in proposals if abs(p.delta) > 1e-6)
    in_grace = sum(1 for p in proposals if p.reason == "decay_grace_period")
    total_delta = sum(p.delta for p in proposals)
    avg_old = sum(p.old_weight for p in proposals) / max(1, len(proposals))
    avg_new = sum(p.proposed_weight for p in proposals) / max(1, len(proposals))
    return {
        "total": len(proposals),
        "decayed": decayed,
        "in_grace_period": in_grace,
        "total_weight_delta": round(total_delta, 6),
        "avg_old_weight": round(avg_old, 4),
        "avg_new_weight": round(avg_new, 4),
        "weight_preservation_ratio": round(avg_new / max(1e-9, avg_old), 4),
    }
