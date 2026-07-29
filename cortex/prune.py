"""Organism-like synapse pruning — drop dead weight, keep proven edges.

Prune never deletes evidence (files/memories). Only weak unused synapses
and optional orphan multi-res nodes. Recommend-only topology hygiene.
"""

from __future__ import annotations

import json
import time
from typing import Any

SCHEMA = "cortex-prune/1.0"
GLYPH = "✂"


def prune_graph(
    store: Any,
    repo: str,
    *,
    min_weight: float = 0.08,
    max_unused_age_updates: int = 0,
    dry_run: bool = False,
    keep_hierarchical: bool = True,
) -> dict[str, Any]:
    """Prune synapses with very low weight and zero plasticity updates.

    Hierarchical contains/child_of edges are kept by default (structure).
    """

    synapses = store.neural_synapses(repo)
    candidates: list[dict[str, Any]] = []
    kept = 0
    for row in synapses:
        relation = str(row["relation"] or "")
        weight = float(row["weight"] or 0)
        updates = int(row["update_count"] or 0)
        hierarchical = relation in {"contains", "child_of"} or bool(
            json.loads(row["metadata"] or "{}").get("hierarchical")
        )
        if keep_hierarchical and hierarchical:
            kept += 1
            continue
        # Dead weight: near floor and never plasticized
        if weight <= min_weight and updates <= max_unused_age_updates:
            candidates.append(
                {
                    "synapse_id": row["synapse_id"],
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                    "relation": relation,
                    "weight": weight,
                    "update_count": updates,
                }
            )
        else:
            kept += 1

    pruned = 0
    if not dry_run and candidates:
        with store.transaction() as conn:
            for item in candidates:
                conn.execute(
                    "DELETE FROM neural_synapses WHERE repo=? AND synapse_id=?",
                    (repo, item["synapse_id"]),
                )
                pruned += 1
        try:
            store.append_neural_event(
                repo,
                event_type="graph_pruned",
                entity_id=repo,
                payload={
                    "pruned": pruned,
                    "kept": kept,
                    "min_weight": min_weight,
                    "candidates": len(candidates),
                },
            )
        except Exception:
            pass
        store.set_setting(
            f"prune:{repo}",
            {
                "pruned": pruned,
                "kept": kept,
                "at": time.time(),
                "min_weight": min_weight,
            },
        )
    elif dry_run:
        pruned = 0

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "dry_run": dry_run,
        "candidates": len(candidates),
        "pruned": pruned if not dry_run else 0,
        "would_prune": len(candidates) if dry_run else pruned,
        "kept": kept,
        "sample": candidates[:12],
        "claim_boundary": (
            "Prune removes weak unused associations only; never host source "
            "and never evidence memories."
        ),
    }


def decay_unused_weights(
    store: Any,
    repo: str,
    *,
    factor: float = 0.97,
    floor: float = 0.05,
) -> dict[str, Any]:
    """Gentle organism-like decay on non-hierarchical synapses with no updates."""

    factor = max(0.5, min(0.999, float(factor)))
    floor = max(0.01, min(0.5, float(floor)))
    synapses = store.neural_synapses(repo)
    touched = 0
    with store.transaction() as conn:
        for row in synapses:
            meta = json.loads(row["metadata"] or "{}")
            if meta.get("hierarchical") or row["relation"] in {"contains", "child_of"}:
                continue
            if int(row["update_count"] or 0) > 0:
                continue
            w = float(row["weight"] or 0)
            nw = max(floor, min(float(row["maximum_weight"] or 0.98), w * factor))
            if abs(nw - w) < 1e-9:
                continue
            conn.execute(
                """
                UPDATE neural_synapses SET weight=?, updated_at=?
                WHERE repo=? AND synapse_id=?
                """,
                (round(nw, 6), time.time(), repo, row["synapse_id"]),
            )
            touched += 1
    if touched:
        try:
            store.append_neural_event(
                repo,
                event_type="weight_decay",
                entity_id=repo,
                payload={"touched": touched, "factor": factor, "floor": floor},
            )
        except Exception:
            pass
    return {
        "schema_version": "cortex-weight-decay/1.0",
        "repo": repo,
        "touched": touched,
        "factor": factor,
        "floor": floor,
        "claim_boundary": "Decay is topology hygiene; not authority change.",
    }
