"""Organism-like synapse pruning — drop dead weight, keep proven edges.

Prune never deletes evidence (files/memories). Only weak unused synapses
and optional orphan multi-res nodes. Recommend-only topology hygiene.

v6.10: named policies (safe | integrate_soft | aggressive) so hygiene and
prune dry-run agree.
"""

from __future__ import annotations

import json
import time
from typing import Any

SCHEMA = "cortex-prune/1.1"
GLYPH = "✂"

# Named policies — operator-facing, spectral class aware.
POLICIES: dict[str, dict[str, Any]] = {
    "safe": {
        "min_weight": 0.08,
        "protect_retain": True,
        "keep_hierarchical": True,
        "description": "Default floor; rarely prunes after mild decay.",
    },
    "integrate_soft": {
        "min_weight": 0.12,
        "protect_retain": True,
        "keep_hierarchical": True,
        "description": "Cut soft integrate tail post-cadence; keep retain hierarchy.",
    },
    "aggressive": {
        "min_weight": 0.15,
        "protect_retain": False,
        "keep_hierarchical": True,
        "description": "Lab/ops explicit only; may cut weak non-hierarchical retain.",
        "requires_authorize": True,
    },
}


def resolve_policy(
    policy: str | None = None,
    *,
    min_weight: float | None = None,
    protect_retain: bool | None = None,
    keep_hierarchical: bool | None = None,
) -> dict[str, Any]:
    name = (policy or "safe").casefold().strip()
    if name not in POLICIES:
        raise ValueError(f"Unknown prune policy: {policy}. Choose: {sorted(POLICIES)}")
    base = dict(POLICIES[name])
    base["policy"] = name
    if min_weight is not None:
        base["min_weight"] = float(min_weight)
    if protect_retain is not None:
        base["protect_retain"] = bool(protect_retain)
    if keep_hierarchical is not None:
        base["keep_hierarchical"] = bool(keep_hierarchical)
    return base


def prune_graph(
    store: Any,
    repo: str,
    *,
    min_weight: float | None = None,
    max_unused_age_updates: int = 0,
    dry_run: bool = False,
    keep_hierarchical: bool | None = None,
    protect_retain: bool | None = None,
    policy: str | None = "safe",
    authorize_aggressive: bool = False,
) -> dict[str, Any]:
    """Prune synapses with very low weight and zero plasticity updates.

    Hierarchical contains/child_of and retain-class edges protected by default.
    Prefer pruning reset/integrate dead weight (spectral organism hygiene).
    """

    cfg = resolve_policy(
        policy,
        min_weight=min_weight,
        protect_retain=protect_retain,
        keep_hierarchical=keep_hierarchical,
    )
    if cfg.get("requires_authorize") and not dry_run and not authorize_aggressive:
        return {
            "schema_version": SCHEMA,
            "glyph": GLYPH,
            "repo": repo,
            "dry_run": dry_run,
            "policy": cfg["policy"],
            "applied": False,
            "error": "aggressive_requires_authorize",
            "hint": "Pass authorize_aggressive=True or --authorize-aggressive",
            "claim_boundary": (
                "Aggressive prune is opt-in; never silent. Evidence never deleted."
            ),
        }

    min_w = float(cfg["min_weight"])
    protect_ret = bool(cfg["protect_retain"])
    keep_hier = bool(cfg["keep_hierarchical"])

    synapses = store.neural_synapses(repo)
    candidates: list[dict[str, Any]] = []
    kept = 0
    by_class_cand: dict[str, int] = {"reset": 0, "integrate": 0, "retain": 0, "other": 0}
    for row in synapses:
        relation = str(row["relation"] or "")
        weight = float(row["weight"] or 0)
        updates = int(row["update_count"] or 0)
        meta = json.loads(row["metadata"] or "{}")
        hierarchical = relation in {"contains", "child_of"} or bool(
            meta.get("hierarchical")
        )
        kernel_class = str(
            meta.get("kernel_class")
            or ("retain" if hierarchical else "reset")
        )
        if keep_hier and hierarchical:
            kept += 1
            continue
        if protect_ret and kernel_class == "retain":
            kept += 1
            continue
        # Dead weight: near floor and never plasticized; class-aware threshold
        threshold = min_w if kernel_class == "reset" else min_w * 0.5
        if kernel_class == "integrate":
            threshold = min_w * 0.75
        if weight <= threshold and updates <= max_unused_age_updates:
            candidates.append(
                {
                    "synapse_id": row["synapse_id"],
                    "source_id": row["source_id"],
                    "target_id": row["target_id"],
                    "relation": relation,
                    "weight": weight,
                    "update_count": updates,
                    "kernel_class": kernel_class,
                }
            )
            key = kernel_class if kernel_class in by_class_cand else "other"
            by_class_cand[key] = by_class_cand.get(key, 0) + 1
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
                    "min_weight": min_w,
                    "policy": cfg["policy"],
                    "candidates": len(candidates),
                    "by_class": by_class_cand,
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
                "min_weight": min_w,
                "policy": cfg["policy"],
            },
        )
    elif dry_run:
        pruned = 0

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "dry_run": dry_run,
        "policy": cfg["policy"],
        "policy_description": cfg.get("description"),
        "min_weight": min_w,
        "protect_retain": protect_ret,
        "keep_hierarchical": keep_hier,
        "candidates": len(candidates),
        "pruned": pruned if not dry_run else 0,
        "would_prune": len(candidates) if dry_run else pruned,
        "kept": kept,
        "by_class": by_class_cand,
        "sample": candidates[:12],
        "applied": (not dry_run) and pruned > 0,
        "claim_boundary": (
            "Prune removes weak unused associations only; never host source "
            "and never evidence memories."
        ),
    }


def policy_preview(store: Any, repo: str) -> dict[str, Any]:
    """Dry-run all policies for hygiene alignment."""

    previews: dict[str, Any] = {}
    for name in POLICIES:
        r = prune_graph(store, repo, policy=name, dry_run=True)
        previews[name] = {
            "would_prune": r.get("would_prune"),
            "kept": r.get("kept"),
            "by_class": r.get("by_class"),
            "min_weight": r.get("min_weight"),
            "description": r.get("policy_description"),
        }
    recommended = "safe"
    if (previews.get("integrate_soft") or {}).get("would_prune", 0) > 0:
        recommended = "integrate_soft"
    if (previews.get("safe") or {}).get("would_prune", 0) > 0:
        recommended = "safe"
    return {
        "schema_version": "cortex-prune-preview/1.0",
        "glyph": GLYPH,
        "repo": repo,
        "policies": previews,
        "recommended": recommended,
        "claim_boundary": "Preview only; apply requires explicit prune without --dry-run.",
    }


def graph_census(store: Any, repo: str) -> dict[str, Any]:
    """Graph census: class counts, weight percentiles, weak-by-class, regions."""

    nodes = store.neural_nodes(repo)
    synapses = store.neural_synapses(repo)
    weights: list[float] = []
    class_counts: dict[str, int] = {}
    relation_counts: dict[str, int] = {}
    weak_by_class: dict[str, dict[str, int]] = {
        "0.08": {},
        "0.12": {},
        "0.15": {},
    }
    regions: dict[str, int] = {}
    resolutions: dict[str, int] = {}

    for row in nodes:
        meta = json.loads(row["metadata"] or "{}")
        region = str(meta.get("neural_region") or "repository")
        regions[region] = regions.get(region, 0) + 1
        res = str(meta.get("resolution") or getattr(row, "resolution", None) or "file")
        try:
            res = str(row["resolution"] or res)
        except (KeyError, IndexError, TypeError):
            pass
        resolutions[res] = resolutions.get(res, 0) + 1

    for row in synapses:
        w = float(row["weight"] or 0)
        weights.append(w)
        meta = json.loads(row["metadata"] or "{}")
        klass = str(meta.get("kernel_class") or "unset")
        class_counts[klass] = class_counts.get(klass, 0) + 1
        rel = str(row["relation"] or "unknown")
        relation_counts[rel] = relation_counts.get(rel, 0) + 1
        for thr_s, thr in (("0.08", 0.08), ("0.12", 0.12), ("0.15", 0.15)):
            if w < thr:
                weak_by_class[thr_s][klass] = weak_by_class[thr_s].get(klass, 0) + 1

    weights.sort()
    n = len(weights)

    def pct(p: float) -> float | None:
        if not weights:
            return None
        idx = min(n - 1, max(0, int(round((p / 100.0) * (n - 1)))))
        return round(weights[idx], 6)

    # Orphan multi-res: nodes with no incident synapse
    linked: set[str] = set()
    for row in synapses:
        linked.add(str(row["source_id"]))
        linked.add(str(row["target_id"]))
    orphans = 0
    orphan_sample: list[str] = []
    for row in nodes:
        nid = str(row["node_id"])
        if nid not in linked:
            orphans += 1
            if len(orphan_sample) < 8:
                orphan_sample.append(str(row["path"] or nid)[:120])

    preview = policy_preview(store, repo)
    return {
        "schema_version": "cortex-graph-census/1.0",
        "glyph": "⧉",
        "repo": repo,
        "nodes": {
            "total": len(nodes),
            "regions": regions,
            "resolutions": resolutions,
            "orphans_no_synapse": orphans,
            "orphan_sample": orphan_sample,
        },
        "synapses": {
            "total": n,
            "by_kernel_class": class_counts,
            "by_relation": relation_counts,
            "weight": {
                "min": round(weights[0], 6) if weights else None,
                "max": round(weights[-1], 6) if weights else None,
                "mean": round(sum(weights) / n, 6) if n else None,
                "p10": pct(10),
                "p50": pct(50),
                "p90": pct(90),
            },
            "weak_by_class": weak_by_class,
        },
        "prune_preview": preview,
        "claim_boundary": (
            "Census is topology telemetry; never deletes evidence or grants mutation rights."
        ),
    }


def decay_unused_weights(
    store: Any,
    repo: str,
    *,
    factor: float = 0.97,
    floor: float = 0.05,
) -> dict[str, Any]:
    """Spectral decay: faster on reset, milder on integrate, skip retain hierarchy."""

    factor = max(0.5, min(0.999, float(factor)))
    floor = max(0.01, min(0.5, float(floor)))
    class_factor = {
        "reset": min(factor, 0.94),
        "integrate": factor,
        "retain": 0.995,
    }
    synapses = store.neural_synapses(repo)
    touched = 0
    by_class = {"reset": 0, "integrate": 0, "retain": 0}
    with store.transaction() as conn:
        for row in synapses:
            meta = json.loads(row["metadata"] or "{}")
            if meta.get("hierarchical") or row["relation"] in {"contains", "child_of"}:
                continue
            klass = str(meta.get("kernel_class") or "reset")
            if klass == "retain":
                continue
            if int(row["update_count"] or 0) > 0 and klass == "integrate":
                continue
            f = class_factor.get(klass, factor)
            w = float(row["weight"] or 0)
            nw = max(floor, min(float(row["maximum_weight"] or 0.98), w * f))
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
            by_class[klass] = by_class.get(klass, 0) + 1
    if touched:
        try:
            store.append_neural_event(
                repo,
                event_type="weight_decay",
                entity_id=repo,
                payload={
                    "touched": touched,
                    "factor": factor,
                    "floor": floor,
                    "by_class": by_class,
                },
            )
        except Exception:
            pass
    return {
        "schema_version": "cortex-weight-decay/1.1",
        "repo": repo,
        "touched": touched,
        "by_class": by_class,
        "factor": factor,
        "floor": floor,
        "claim_boundary": "Spectral decay is topology hygiene; not authority change.",
    }
