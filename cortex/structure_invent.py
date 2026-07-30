"""Gated topology invention — propose new neural synapses from co-activation.

Propose new coactivation topology edges from simultaneous path fire under
governor gates. Structure invent / invent topology: invented synapses only
on the memory graph — never host source files.

Does NOT invent host source structure. Only memory-graph edges under Governor.
Recommend-only for host; graph invention is internal body plasticity of kind=invented.
"""

from __future__ import annotations

import json
import time
from hashlib import sha256
from typing import Any

SCHEMA = "cortex-structure-invent/1.0"
GLYPH = "⧉+"


def _synapse_id(source: str, target: str, relation: str) -> str:
    material = f"{source}|{target}|{relation}|invented"
    return "syn_" + sha256(material.encode("utf-8")).hexdigest()[:24]


def invent_from_coactivation(
    store: Any,
    repo: str,
    *,
    fired_node_ids: list[str],
    governance_mode: str = "normal",
    max_new: int = 8,
    base_weight: float = 0.12,
) -> dict[str, Any]:
    """Create weak integrate edges between co-fired nodes that lack a direct synapse.

    Blocked in read_only. Caps max_new per call. Marks metadata invented=True.
    """
    if governance_mode == "read_only":
        return {
            "schema_version": SCHEMA,
            "glyph": GLYPH,
            "invented": 0,
            "blocked": True,
            "reason": "governor_read_only",
        }
    nodes = {str(r["node_id"]) for r in (store.neural_nodes(repo) or [])}
    fired = [n for n in fired_node_ids if n in nodes]
    if len(fired) < 2:
        return {
            "schema_version": SCHEMA,
            "glyph": GLYPH,
            "invented": 0,
            "reason": "need_two_fired_nodes",
        }

    existing: set[tuple[str, str]] = set()
    for row in store.neural_synapses(repo) or []:
        a, b = str(row["source_id"]), str(row["target_id"])
        existing.add((a, b) if a < b else (b, a))

    proposed: list[tuple[str, str]] = []
    for i, a in enumerate(fired):
        for b in fired[i + 1 :]:
            key = (a, b) if a < b else (b, a)
            if key in existing:
                continue
            proposed.append(key)
            if len(proposed) >= max_new:
                break
        if len(proposed) >= max_new:
            break

    now = time.time()
    created = 0
    samples: list[dict[str, Any]] = []
    with store.transaction() as conn:
        for a, b in proposed:
            sid = _synapse_id(a, b, "coactivated")
            meta = {
                "invented": True,
                "kernel_class": "integrate",
                "retention_regime": "integrate",
                "source": "structure_invent",
                "at": now,
                # v6.24 lineage prep for causal unlearning (ancestors = co-fired nodes)
                "ancestors": [a, b],
                "derived_from_coactivation": True,
                "lineage_plane": "G_learned",
            }
            conn.execute(
                """
                INSERT INTO neural_synapses(
                  repo, synapse_id, source_id, target_id, relation, base_weight, weight,
                  minimum_weight, maximum_weight, plasticity_rule, update_count,
                  evidence, metadata, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                ON CONFLICT(repo, synapse_id) DO UPDATE SET
                  weight=MAX(neural_synapses.weight, excluded.weight),
                  metadata=excluded.metadata,
                  updated_at=excluded.updated_at
                """,
                (
                    repo,
                    sid,
                    a,
                    b,
                    "coactivated",
                    base_weight,
                    base_weight,
                    0.01,
                    0.95,
                    "bounded_hebbian",
                    json.dumps(["coactivation_tick"], sort_keys=True),
                    json.dumps(meta, sort_keys=True),
                    now,
                ),
            )
            created += 1
            samples.append({"synapse_id": sid, "source_id": a, "target_id": b})

    try:
        store.append_neural_event(
            repo,
            event_type="structure_invented",
            entity_id=repo,
            payload={"invented": created, "samples": samples[:8]},
        )
    except Exception:
        pass

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "invented": created,
        "samples": samples[:8],
        "governance_mode": governance_mode,
        "claim_boundary": (
            "Invented synapses are internal memory edges only; never host file edits."
        ),
    }
