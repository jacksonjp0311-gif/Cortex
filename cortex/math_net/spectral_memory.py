"""End-to-end calibrated spectral memory — live path (v6.13).

Closes the gap between M0–M10 *surface* and a single activate/retrieve pass that:
  1. Computes unified U
  2. Updates Λ_g on pulse
  3. Builds operator A diffusion features
  4. Optionally promotes shadow calibration
  5. Emits a spectral_memory packet for context

Recommend-only; never host mutation.
"""

from __future__ import annotations

import time
from typing import Any

from .calibration import load_shadow_calibration, observe_outcome_for_calibration
from .diffusion import diffusion_features
from .info_account import info_account
from .kernel_state import update_lambda_on_pulse
from .operator import build_operator_A, dual_graph_report
from .regimes import PRIOR_DELTAS, rho_from_delta
from .spectral import spectral_slice
from .uncertainty import compute_uncertainty

SCHEMA = "cortex-spectral-memory-e2e/1.0"


def path_to_node_guess(store: Any, repo: str, path: str) -> str | None:
    """Best-effort map memory path → neural node_id."""
    p = (path or "").replace("\\", "/")
    if not p:
        return None
    try:
        for row in store.neural_nodes(repo) or []:
            rp = str(row["path"] or "").replace("\\", "/")
            if rp == p or rp.endswith(p) or p.endswith(rp):
                return str(row["node_id"])
            # symbol nodes often path::name
            if rp.split("::")[0] == p:
                return str(row["node_id"])
    except Exception:
        return None
    return None


def enrich_hits_with_diffusion(
    store: Any,
    repo: str,
    hits: list[Any],
    *,
    max_nodes: int = 280,
) -> dict[str, Any]:
    """Attach ppr/heat/degree into hit metadata for ranker-primary features."""
    seed_ids: list[str] = []
    for hit in hits[:12]:
        path = hit.get("path") if isinstance(hit, dict) else getattr(hit, "path", "")
        nid = path_to_node_guess(store, repo, str(path or ""))
        if nid:
            seed_ids.append(nid)
    diff = diffusion_features(store, repo, seed_ids or None, max_nodes=max_nodes)
    by_node = diff.get("by_node") or {}
    # also index by path suffix for memories without exact node id
    path_feats: dict[str, dict[str, float]] = {}
    try:
        index_ids = {nid: feats for nid, feats in by_node.items()}
        for row in store.neural_nodes(repo) or []:
            nid = str(row["node_id"])
            if nid not in index_ids:
                continue
            rp = str(row["path"] or "").replace("\\", "/")
            path_feats[rp] = index_ids[nid]
            path_feats[rp.split("::")[0]] = index_ids[nid]
    except Exception:
        pass

    enriched = 0
    for hit in hits:
        if isinstance(hit, dict):
            path = str(hit.get("path") or "").replace("\\", "/")
            meta = dict(hit.get("metadata") or {})
        else:
            path = str(getattr(hit, "path", "") or "").replace("\\", "/")
            meta = dict(getattr(hit, "metadata", None) or {})
        nid = path_to_node_guess(store, repo, path)
        feats = by_node.get(nid or "") or path_feats.get(path) or path_feats.get(path.split("::")[0])
        if not feats:
            continue
        meta["ppr"] = feats.get("ppr", 0.0)
        meta["heat"] = feats.get("heat", 0.0)
        meta["degree_centrality"] = feats.get("degree_centrality", 0.0)
        meta["spectral_enriched"] = True
        enriched += 1
        if isinstance(hit, dict):
            hit["metadata"] = meta
        else:
            try:
                hit.metadata = meta
            except Exception:
                pass
    return {
        "enriched": enriched,
        "diffusion_ok": bool(diff.get("ok")),
        "n_graph": diff.get("n"),
        "seed_node_ids": diff.get("seed_node_ids"),
    }


def fit_regime_deltas_from_mass(
    store: Any,
    repo: str,
    *,
    class_mass: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Schedule/fit soft δ_g from mass distribution (not full MLE, but data-driven).

    High mass + high update activity → lower δ (retain-like); low mass → higher δ.
    Writes kernel_profile if promoted flag set separately.
    """
    import json

    mass = {g: 0.0 for g in ("reset", "integrate", "retain")}
    updates = {g: 0.0 for g in mass}
    try:
        for row in store.neural_synapses(repo) or []:
            meta = json.loads(row["metadata"] or "{}")
            g = str(meta.get("kernel_class") or meta.get("retention_regime") or "reset")
            if g not in mass:
                g = "integrate"
            mass[g] += float(row["weight"] or 0)
            updates[g] += float(row["update_count"] or 0)
    except Exception:
        if class_mass:
            mass = {**mass, **class_mass}

    total = sum(mass.values()) or 1.0
    fitted: dict[str, Any] = {}
    for g, prior_d in PRIOR_DELTAS.items():
        share = mass[g] / total
        activity = updates[g] / (1.0 + mass[g])
        # more share/activity → slower decay
        delta = prior_d * (1.2 - 0.6 * share) * (1.0 - min(0.4, activity * 0.05))
        delta = max(0.01, min(3.5, delta))
        fitted[g] = {
            "delta": round(delta, 6),
            "rho": round(rho_from_delta(delta), 6),
            "prior_delta": prior_d,
            "mass_share": round(share, 6),
            "kind": "data_scheduled",
        }
    packet = {
        "schema_version": "cortex-regime-fit/1.0",
        "fitted": fitted,
        "at": time.time(),
        "claim_boundary": "Scheduled δ from mass/activity; not full likelihood MLE.",
    }
    try:
        store.set_setting(f"regime_fit:{repo}", packet)
    except Exception:
        pass
    return packet


def promote_calibration(
    store: Any,
    repo: str,
    *,
    min_outcomes: int = 8,
    force: bool = False,
) -> dict[str, Any]:
    """Promote shadow calibration + fitted regimes into live settings when ready."""
    shadow = load_shadow_calibration(store, repo)
    n = int(shadow.get("n_outcomes") or 0)
    fit = store.get_setting(f"regime_fit:{repo}", None) if hasattr(store, "get_setting") else None
    if not force and n < min_outcomes:
        return {
            "promoted": False,
            "reason": "insufficient_outcomes",
            "n_outcomes": n,
            "min_outcomes": min_outcomes,
        }
    live = {
        "schema_version": "cortex-calibration-live/1.0",
        "promoted_at": time.time(),
        "governor_weights": shadow.get("governor_weights"),
        "constitutional_weights": shadow.get("constitutional_weights"),
        "regime_fit": fit,
        "n_outcomes": n,
        "mode": "live",
    }
    try:
        store.set_setting(f"calibration_live:{repo}", live)
        # Also push regime deltas into kernel_profile
        if isinstance(fit, dict) and fit.get("fitted"):
            from ..kernels import load_kernel_profile

            profile = load_kernel_profile(store, repo)
            classes = dict(profile.get("classes") or {})
            for g, row in (fit.get("fitted") or {}).items():
                classes[g] = {
                    **(classes.get(g) or {}),
                    "delta": row["delta"],
                    "rho": row["rho"],
                    "kind": "data_scheduled",
                }
            profile["classes"] = classes
            profile["regimes"] = classes
            profile["fitted"] = True
            store.set_setting(f"kernel_profile:{repo}", profile)
    except Exception as exc:
        return {"promoted": False, "error": f"{type(exc).__name__}: {exc}"}
    return {"promoted": True, "live": live}


def load_live_calibration(store: Any, repo: str) -> dict[str, Any] | None:
    raw = store.get_setting(f"calibration_live:{repo}", None) if hasattr(store, "get_setting") else None
    if isinstance(raw, dict) and raw.get("mode") == "live":
        return raw
    return None


def spectral_memory_pulse(
    store: Any,
    repo: str,
    *,
    retrieval_confidence: float = 0.5,
    certificate_status: str = "verified",
    manifest_current: bool | None = None,
    budget_tokens: int = 400,
    auto_promote: bool = True,
    u_before: float | None = None,
) -> dict[str, Any]:
    """One end-to-end spectral memory pulse for activate/context."""
    u_pkt = compute_uncertainty(
        retrieval_confidence=retrieval_confidence,
        certificate_status=certificate_status,
        manifest_current=manifest_current,
        budget_tokens=budget_tokens,
    )
    lam = update_lambda_on_pulse(store, repo)
    fit = fit_regime_deltas_from_mass(store, repo)
    try:
        observe_outcome_for_calibration(
            store,
            repo,
            reward=0.0,
            features={"uncertainty": u_pkt["u"], "gov_confidence": retrieval_confidence},
        )
    except Exception:
        pass

    promoted = None
    if auto_promote:
        shadow = load_shadow_calibration(store, repo)
        if int(shadow.get("n_outcomes") or 0) >= 8:
            promoted = promote_calibration(store, repo, min_outcomes=8)

    # light spectral telemetry (capped)
    try:
        spec = spectral_slice(store, repo, max_nodes=160)
    except Exception as exc:
        spec = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        dual = dual_graph_report(store, repo)
    except Exception as exc:
        dual = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    try:
        op = build_operator_A(store, repo, max_nodes=160)
        op_summary = {"n": op.get("n"), "edges": op.get("edge_count")}
    except Exception:
        op_summary = {"n": 0, "edges": 0}

    ub = float(u_before) if u_before is not None else min(1.0, float(u_pkt["u"]) + 0.08)
    info = info_account(
        u_before=ub,
        u_after=u_pkt["u"],
        budget_tokens=budget_tokens,
        evidence_fidelity=max(0.0, retrieval_confidence),
        reversibility=1.0,
    )

    live = load_live_calibration(store, repo)
    return {
        "schema_version": SCHEMA,
        "glyph": "≋L",
        "end_to_end": True,
        "u": u_pkt,
        "Lambda": lam.get("Lambda"),
        "regime_fit": fit.get("fitted"),
        "operator": op_summary,
        "spectral": {
            "ok": spec.get("ok"),
            "lambda2": spec.get("lambda2"),
            "n": spec.get("n"),
            "edge_underuse_top": (spec.get("edge_underuse_top") or [])[:5],
        },
        "dual_graph": {
            "neural_synapses": dual.get("neural_synapses"),
            "structural_edges": dual.get("structural_edges"),
            "ratio": dual.get("ratio_neural_to_structural"),
        },
        "info_account": info,
        "calibration_live": bool(live),
        "promotion": promoted,
        "claim_boundary": (
            "Spectral memory pulse is live telemetry+ranking fuel; still recommend-only. "
            "Calibrated when calibration_live is set after enough outcomes."
        ),
        "at": time.time(),
    }
