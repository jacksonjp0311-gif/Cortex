"""M10 — Temporal–structural edge model: age, co-change × calls."""

from __future__ import annotations

import json
import time
from typing import Any

SCHEMA = "cortex-temporal-edges/1.0"


def temporal_structural_report(
    store: Any,
    repo: str,
    *,
    now: float | None = None,
    sample_limit: int = 50,
) -> dict[str, Any]:
    """Annotate synapse sample with effective age and structural tags."""
    now = float(now if now is not None else time.time())
    rows = []
    cochange = 0
    calls = 0
    aged = 0
    try:
        for row in store.neural_synapses(repo) or []:
            meta = json.loads(row["metadata"] or "{}")
            rel = str(row["relation"] or "")
            updated = float(row["updated_at"] or row["created_at"] or now)
            age_hours = max(0.0, (now - updated) / 3600.0)
            # effective age damped by regime rho if present
            rho = float(meta.get("rho") or 0.7)
            effective_age = age_hours * (1.0 - 0.5 * rho)
            is_co = rel in {"co_changed", "cochange"} or "co_change" in rel
            is_call = rel in {"calls", "imports", "dataflow_def", "dataflow_use"}
            if is_co:
                cochange += 1
            if is_call:
                calls += 1
            if effective_age > 24:
                aged += 1
            # joint score: structural strength * temporal freshness
            w = float(row["weight"] or 0)
            joint = w * (1.0 / (1.0 + effective_age / 168.0))
            if is_co and is_call:
                joint *= 1.25
            elif is_co or is_call:
                joint *= 1.1
            if len(rows) < sample_limit:
                rows.append(
                    {
                        "synapse_id": row["synapse_id"],
                        "relation": rel,
                        "weight": round(w, 6),
                        "age_hours": round(age_hours, 3),
                        "effective_age_hours": round(effective_age, 3),
                        "rho": rho,
                        "co_change": is_co,
                        "call_or_import": is_call,
                        "joint_temporal_structural": round(joint, 6),
                    }
                )
    except Exception as exc:
        return {"schema_version": SCHEMA, "ok": False, "error": f"{type(exc).__name__}: {exc}"}

    rows.sort(key=lambda r: r["joint_temporal_structural"], reverse=True)
    return {
        "schema_version": SCHEMA,
        "ok": True,
        "counts": {
            "sampled": len(rows),
            "co_change_edges_seen": cochange,
            "call_import_edges_seen": calls,
            "aged_over_24h_effective": aged,
        },
        "top_joint": rows[:15],
        "model": "joint = w / (1 + age_days) * structural_boost; age damped by regime ρ",
        "claim_boundary": (
            "Descriptive temporal–structural scoring; not full link-prediction training."
        ),
    }


def lifecycle_effective_age(
    last_activation_ts: float | None,
    regime_rho: float,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    """Lifecycle age from activation + class ρ (not wall-clock alone)."""
    now = float(now if now is not None else time.time())
    if not last_activation_ts:
        return {"effective_age_hours": None, "wall_age_hours": None, "rho": regime_rho}
    wall = max(0.0, (now - float(last_activation_ts)) / 3600.0)
    # high rho (retain) ages slower
    eff = wall * (1.0 - 0.6 * max(0.0, min(1.0, regime_rho)))
    return {
        "wall_age_hours": round(wall, 4),
        "effective_age_hours": round(eff, 4),
        "rho": regime_rho,
    }
