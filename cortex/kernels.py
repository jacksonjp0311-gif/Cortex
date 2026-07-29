"""Spectral memory kernels — distributed retention, not one scalar ρ.

Classes: reset (fast decay) · integrate (medium) · retain (slow).
Common connect pulse is projected through this spectrum. Telemetry only;
never mutation authority. Biology motivates structure, not identity.
"""

from __future__ import annotations

import json
import math
import time
from typing import Any

SCHEMA = "cortex-kernels/1.0"
GLYPH = "≋"
CLASSES = ("reset", "integrate", "retain")

# Default degradation rates (per connect interval T=1): δ_reset >> δ_integrate >> δ_retain
# ρ = e^{-δ T}
DEFAULT_DELTAS: dict[str, float] = {
    "reset": 2.3,  # ρ ≈ 0.10
    "integrate": 0.35,  # ρ ≈ 0.70
    "retain": 0.023,  # ρ ≈ 0.977
}


def rho_from_delta(delta: float, interval: float = 1.0) -> float:
    return float(math.exp(-max(0.0, float(delta)) * max(0.0, float(interval))))


def default_kernel_profile() -> dict[str, Any]:
    classes = {}
    for name, delta in DEFAULT_DELTAS.items():
        classes[name] = {
            "delta": delta,
            "rho": round(rho_from_delta(delta), 6),
            "role": {
                "reset": "ephemeral_hits_and_prune_candidates",
                "integrate": "connect_ranker_prefetch",
                "retain": "cards_canonical_hierarchy",
            }[name],
        }
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "classes": classes,
        "law": "clock_neq_memory_neq_decision",
        "claim_boundary": (
            "Kernel profile is routing telemetry; not consciousness or host rights."
        ),
    }


def load_kernel_profile(store: Any, repo: str) -> dict[str, Any]:
    raw = store.get_setting(f"kernel_profile:{repo}", None) if hasattr(store, "get_setting") else None
    if isinstance(raw, dict) and raw.get("schema_version") == SCHEMA and raw.get("classes"):
        return raw
    profile = default_kernel_profile()
    try:
        store.set_setting(f"kernel_profile:{repo}", profile)
    except Exception:
        pass
    return profile


def classify_relation(relation: str, metadata: dict[str, Any] | None = None) -> str:
    """Map edge/memory kind to spectral class."""

    meta = metadata or {}
    if meta.get("kernel_class") in CLASSES:
        return str(meta["kernel_class"])
    if meta.get("hierarchical") or relation in {"contains", "child_of"}:
        return "retain"
    if relation in {"tested_by", "documents", "described_by", "covers", "covered_by"}:
        return "retain"
    if relation in {"calls", "dataflow_def", "dataflow_use", "resolves_to", "imports"}:
        return "integrate"
    if relation.startswith("reverse:"):
        return "integrate"
    if relation in {"co_changed", "references"}:
        return "integrate"
    return "reset"


def classify_memory_kind(kind: str, path: str = "") -> str:
    k = (kind or "").casefold()
    p = (path or "").replace("\\", "/")
    if k in {"discovery_card", "invariant", "lesson", "constraint"}:
        return "retain"
    if "memory-packets" in p or "docs/intelligence/" in p or "docs/COVENANT" in p:
        return "retain"
    if k in {"discovery", "decision", "fix", "outcome"}:
        return "integrate"
    if k in {"focus", "telemetry"}:
        return "reset"
    return "integrate"


def annotate_synapses(store: Any, repo: str) -> dict[str, Any]:
    """Write kernel_class into synapse metadata (idempotent)."""

    profile = load_kernel_profile(store, repo)
    counts = {c: 0 for c in CLASSES}
    synapses = store.neural_synapses(repo)
    updated = 0
    with store.transaction() as conn:
        for row in synapses:
            meta = json.loads(row["metadata"] or "{}")
            klass = classify_relation(str(row["relation"] or ""), meta)
            counts[klass] = counts.get(klass, 0) + 1
            if meta.get("kernel_class") == klass:
                continue
            meta["kernel_class"] = klass
            meta["rho"] = (profile.get("classes") or {}).get(klass, {}).get("rho")
            conn.execute(
                """
                UPDATE neural_synapses SET metadata=?, updated_at=?
                WHERE repo=? AND synapse_id=?
                """,
                (json.dumps(meta, sort_keys=True), time.time(), repo, row["synapse_id"]),
            )
            updated += 1
    return {
        "annotated": updated,
        "counts": counts,
        "profile": profile.get("classes"),
        "claim_boundary": "Annotation is topology metadata only.",
    }


def retention_by_class(
    store: Any,
    repo: str,
    *,
    metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute spectral retention snapshot for mesh/connect."""

    profile = load_kernel_profile(store, repo)
    classes = profile.get("classes") or {}
    # Mass: count synapses + evidence hints
    mass = {c: 0.0 for c in CLASSES}
    try:
        for row in store.neural_synapses(repo):
            meta = json.loads(row["metadata"] or "{}")
            klass = meta.get("kernel_class") or classify_relation(
                str(row["relation"] or ""), meta
            )
            mass[klass] = mass.get(klass, 0.0) + float(row["weight"] or 0)
    except Exception:
        pass
    total_mass = sum(mass.values()) or 1.0
    spectrum = {}
    for c in CLASSES:
        rho = float((classes.get(c) or {}).get("rho") or rho_from_delta(DEFAULT_DELTAS[c]))
        delta = float((classes.get(c) or {}).get("delta") or DEFAULT_DELTAS[c])
        share = mass[c] / total_mass
        # Ξ-like load: retained mass share * rho (bounded)
        xi = round(min(1.0, share * rho * (1.0 + math.log1p(mass[c]))), 6)
        spectrum[c] = {
            "delta": delta,
            "rho": round(rho, 6),
            "mass": round(mass[c], 4),
            "share": round(share, 4),
            "xi": xi,
        }
    # Optional pulse modulation from metrics
    if metrics:
        if (metrics.get("immune") or {}).get("block"):
            for c in spectrum:
                spectrum[c]["xi"] = round(spectrum[c]["xi"] * 0.5, 6)
                spectrum[c]["gated"] = "immune_block"
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "spectrum": spectrum,
        "dominant": max(CLASSES, key=lambda c: spectrum[c]["xi"]),
        "law": "common_pulse_through_kernel_spectrum",
        "claim_boundary": (
            "Spectral Ξ is local telemetry; commit still requires Governor/immune/host."
        ),
    }


def kernels_status(store: Any, repo: str) -> dict[str, Any]:
    profile = load_kernel_profile(store, repo)
    retention = retention_by_class(store, repo)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "profile": profile.get("classes"),
        "retention": retention.get("spectrum"),
        "dominant": retention.get("dominant"),
        "clock_neq_memory_neq_decision": True,
        "claim_boundary": profile.get("claim_boundary"),
    }
