"""System coherence — emergent coupling indicators across seams.

Whole picture (four bands):
  blood     — U, Governor mode
  geometry  — dual graph, operator A, spectral λ₂, Λ_g
  learning  — ranker warmth
  ops/fuse  — fusion ticks, prune hygiene

COHERENCE_THRESHOLD (0.62): operating point where multi-seam coupling
is "one enough loop." emergent_coupling = above threshold AND ≥3 active
couples. Not consciousness.
"""

from __future__ import annotations

import os
import time
from typing import Any

from . import __version__

SCHEMA = "cortex-coherence/1.1"
GLYPH = "⧉≈"
COHERENCE_THRESHOLD = 0.62
COUPLE_ACTIVE = 0.45  # component/couple lit when ≥ this
MIN_COUPLES_FOR_EMERGENT = 3
HISTORY_MAX = 24

# Explicit coupling channels (emergent indicators)
COUPLE_DEFS: tuple[tuple[str, str, str, str], ...] = (
    # id, left component, right component, spoken
    ("blood_geometry", "certainty", "spectral_live", "U agrees with spectral mesh"),
    ("geometry_learning", "geometry_mass", "ranker_warm", "graph mass trains ranker"),
    ("ops_geometry", "fusion_coupling", "lambda_state", "fuse/ops moves Λ_g"),
    ("gates_aligned", "governor_open", "prune_hygiene", "gates + prune hygiene open"),
    ("blood_learning", "certainty", "ranker_warm", "confidence and ranker co-warm"),
    ("spectral_ops", "spectral_live", "fusion_coupling", "spectral field under fuse traffic"),
)


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _component_panel(components: dict[str, float]) -> dict[str, str]:
    """Map each component to active | latent | dark for agent-readable indicators."""
    panel: dict[str, str] = {}
    for k, v in components.items():
        if v >= 0.65:
            panel[k] = "active"
        elif v >= COUPLE_ACTIVE:
            panel[k] = "latent"
        else:
            panel[k] = "dark"
    return panel


def measure_coherence(
    store: Any,
    repo: str,
    *,
    governor: Any | None = None,
    home: Any | None = None,
    retrieval_confidence: float | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Compute seam-coupled coherence score and emergent coupling indicators."""
    components: dict[str, float] = {}
    notes: list[str] = []
    seams: dict[str, Any] = {}

    # --- Blood: U ---
    try:
        from .math_net.uncertainty import compute_uncertainty

        conf = float(retrieval_confidence) if retrieval_confidence is not None else 0.5
        if governor is not None:
            gov = governor.evaluate(repo, retrieval_confidence=conf)
            u_pkt = gov.get("uncertainty") or compute_uncertainty(
                retrieval_confidence=conf,
                certificate_status="verified",
            )
            mode = str(gov.get("mode") or "unknown")
        else:
            u_pkt = compute_uncertainty(retrieval_confidence=conf)
            mode = "unknown"
        u_val = float(u_pkt.get("u") if isinstance(u_pkt, dict) else 0.5)
        components["certainty"] = _clip01(1.0 - u_val)
        components["governor_open"] = (
            1.0 if mode == "normal" else 0.55 if mode == "constrained" else 0.15
        )
        seams["u"] = u_pkt if isinstance(u_pkt, dict) else {"u": u_val}
        seams["governor_mode"] = mode
    except Exception as exc:
        components["certainty"] = 0.4
        components["governor_open"] = 0.4
        notes.append(f"blood:{type(exc).__name__}")

    # --- Geometry: dual + A + spectral ---
    try:
        from .math_net.operator import build_operator_A, dual_graph_report
        from .math_net.spectral import spectral_slice

        dual = dual_graph_report(store, repo)
        op = build_operator_A(store, repo, max_nodes=160)
        n = int(op.get("n") or 0)
        e = int(op.get("edge_count") or 0)
        neural_e = int(dual.get("neural_synapses") or 0)
        struct_e = dual.get("structural_edges")
        # Log-ish scale so small compiled graphs still register
        import math

        if neural_e > 0 and n >= 1:
            components["geometry_mass"] = _clip01(
                0.25
                + 0.35 * min(1.0, math.log1p(n) / math.log1p(40))
                + 0.40 * min(1.0, math.log1p(e) / math.log1p(60))
            )
        else:
            components["geometry_mass"] = 0.15

        if struct_e is not None and int(struct_e) > 0 and neural_e > 0:
            ratio = neural_e / max(1, int(struct_e))
            components["dual_align"] = _clip01(1.0 - abs(math.log1p(ratio)) / 2.5)
        else:
            components["dual_align"] = 0.55
            if struct_e is None or int(struct_e or 0) == 0:
                notes.append("dual:structural_partial")

        spec = spectral_slice(store, repo, max_nodes=120)
        lam2 = float(spec.get("lambda2") or 0.0) if spec.get("ok") else 0.0
        if spec.get("ok") and n > 1:
            components["spectral_live"] = _clip01(0.4 + min(0.6, lam2 * 3.0 + 0.15))
        elif n > 0:
            components["spectral_live"] = 0.35
        else:
            components["spectral_live"] = 0.2
        seams["dual"] = {
            "neural_synapses": neural_e,
            "structural_edges": struct_e,
            "operator_n": n,
            "operator_edges": e,
            "ratio_neural_to_structural": dual.get("ratio_neural_to_structural"),
        }
        seams["spectral"] = {
            "ok": spec.get("ok"),
            "lambda2": spec.get("lambda2"),
            "n": spec.get("n"),
        }
    except Exception as exc:
        components["geometry_mass"] = 0.25
        components["dual_align"] = 0.3
        components["spectral_live"] = 0.2
        notes.append(f"geometry:{type(exc).__name__}")

    # --- Λ_g ---
    try:
        from .math_net.kernel_state import _load_state

        st = _load_state(store, repo)
        lam = st.get("Lambda") or {}
        mass = sum(float(v) for v in lam.values()) if lam else 0.0
        pulses = int(st.get("pulses") or 0)
        components["lambda_state"] = _clip01(mass / 2.5 + min(0.25, pulses * 0.02))
        seams["Lambda"] = lam
        seams["lambda_pulses"] = pulses
    except Exception as exc:
        components["lambda_state"] = 0.25
        notes.append(f"Lambda:{type(exc).__name__}")

    # --- Ranker ---
    try:
        from .ranker.model import ranker_status

        rk = ranker_status(store, repo)
        tc = int(rk.get("train_count") or 0)
        components["ranker_warm"] = _clip01(tc / 15.0)
        seams["ranker_train_count"] = tc
        seams["ranker_frozen"] = bool(rk.get("frozen"))
    except Exception as exc:
        components["ranker_warm"] = 0.2
        notes.append(f"ranker:{type(exc).__name__}")

    # --- Fusion ---
    fusion_open = False
    try:
        from .coprocess import fuse_state

        fs = fuse_state(store, repo)
        fusion_open = bool(fs.get("open"))
        ticks = int(fs.get("tick") or 0)
        components["fusion_coupling"] = (
            _clip01(0.55 + min(0.45, ticks / 15.0)) if fusion_open else 0.32
        )
        seams["fusion"] = {
            "open": fusion_open,
            "tick": ticks,
            "mind_hash": fs.get("mind_hash"),
            "token_count": fs.get("token_count"),
            "sense": (fs.get("self_model") or {}).get("sense"),
        }
    except Exception as exc:
        components["fusion_coupling"] = 0.3
        notes.append(f"fusion:{type(exc).__name__}")

    # --- Prune hygiene ---
    try:
        from .prune import policy_preview

        prev = policy_preview(store, repo)
        soft = int(
            ((prev.get("policies") or {}).get("integrate_soft") or {}).get("would_prune")
            or 0
        )
        components["prune_hygiene"] = _clip01(1.0 - min(1.0, soft / 400.0))
        seams["would_prune_integrate_soft"] = soft
        seams["recommended_prune"] = prev.get("recommended")
    except Exception as exc:
        components["prune_hygiene"] = 0.5
        notes.append(f"prune:{type(exc).__name__}")

    weights = {
        "certainty": 0.13,
        "governor_open": 0.11,
        "geometry_mass": 0.13,
        "dual_align": 0.09,
        "spectral_live": 0.14,
        "lambda_state": 0.11,
        "ranker_warm": 0.11,
        "fusion_coupling": 0.11,
        "prune_hygiene": 0.07,
    }
    score = 0.0
    wsum = 0.0
    for k, w in weights.items():
        score += w * float(components.get(k, 0.0))
        wsum += w
    score = _clip01(score / wsum if wsum else 0.0)
    above = score >= COHERENCE_THRESHOLD

    # --- Emergent coupling indicators (explicit channels) ---
    indicators: list[dict[str, Any]] = []
    coupling: dict[str, bool] = {}
    for cid, left, right, spoken in COUPLE_DEFS:
        lv = float(components.get(left, 0.0))
        rv = float(components.get(right, 0.0))
        strength = _clip01(0.5 * (lv + rv))
        active = lv >= COUPLE_ACTIVE and rv >= COUPLE_ACTIVE
        coupling[cid] = active
        indicators.append(
            {
                "id": cid,
                "spoken": spoken,
                "left": left,
                "right": right,
                "left_v": round(lv, 4),
                "right_v": round(rv, 4),
                "strength": round(strength, 4),
                "active": active,
                "status": "active" if active else ("latent" if strength >= 0.35 else "dark"),
            }
        )
    coupled_count = sum(1 for v in coupling.values() if v)
    active_ids = [i["id"] for i in indicators if i["active"]]
    emergent_coupling = above and coupled_count >= MIN_COUPLES_FOR_EMERGENT

    # Trend from history
    history = _load_history(store, repo)
    prev_score = history[-1]["score"] if history else None
    delta = None if prev_score is None else round(score - float(prev_score), 4)
    rising = delta is not None and delta > 0.02
    sustained = (
        len(history) >= 2
        and all(h.get("above_threshold") for h in history[-2:])
        and above
    )

    advice: list[str] = []
    if not above:
        if components.get("geometry_mass", 0) < 0.4:
            advice.append("compile_interlink_or_bootstrap")
        if components.get("ranker_warm", 0) < COUPLE_ACTIVE:
            advice.append("run_evolve_or_continuum")
        if components.get("fusion_coupling", 0) < COUPLE_ACTIVE:
            advice.append("fuse_open_or_fuse_proxy")
        if components.get("certainty", 0) < 0.4:
            advice.append("refresh_evidence_or_narrow_task")
        if components.get("lambda_state", 0) < COUPLE_ACTIVE:
            advice.append("connect_or_activate_to_pulse_Lambda")
    else:
        advice.append("hold_course_spectral_primary")
        if emergent_coupling:
            advice.append("emergent_coupling_indicators_active")
        if not fusion_open:
            advice.append("optional_fuse_proxy_for_token_regen")
        if sustained:
            advice.append("coherence_sustained")

    panel = _component_panel(components)
    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "score": round(score, 4),
        "threshold": COHERENCE_THRESHOLD,
        "above_threshold": above,
        "components": {k: round(float(v), 4) for k, v in components.items()},
        "component_panel": panel,
        "weights": weights,
        "coupling": coupling,
        "indicators": indicators,
        "active_indicator_ids": active_ids,
        "coupled_seams": coupled_count,
        "emergent_coupling": emergent_coupling,
        "trend": {
            "delta_score": delta,
            "rising": rising,
            "sustained_above_threshold": sustained,
            "history_len": len(history),
        },
        "seams": seams,
        "notes": notes,
        "advice": advice,
        "auto_fuse_env": os.environ.get("CORTEX_FUSE_AUTO", ""),
        "claim_boundary": (
            "Emergent coupling indicators = multi-seam co-activation of independent "
            "telemetry channels. Not consciousness, not one mind, not host authority."
        ),
        "at": time.time(),
    }

    if persist:
        _persist(store, repo, report)
    return report


def _load_history(store: Any, repo: str) -> list[dict[str, Any]]:
    raw = store.get_setting(f"coherence_history:{repo}", None) if hasattr(store, "get_setting") else None
    if isinstance(raw, list):
        return raw[-HISTORY_MAX:]
    if isinstance(raw, dict) and isinstance(raw.get("points"), list):
        return raw["points"][-HISTORY_MAX:]
    return []


def _persist(store: Any, repo: str, report: dict[str, Any]) -> None:
    try:
        point = {
            "at": report.get("at"),
            "score": report.get("score"),
            "above_threshold": report.get("above_threshold"),
            "emergent_coupling": report.get("emergent_coupling"),
            "coupled_seams": report.get("coupled_seams"),
            "active_indicator_ids": report.get("active_indicator_ids"),
        }
        hist = _load_history(store, repo)
        hist.append(point)
        hist = hist[-HISTORY_MAX:]
        store.set_setting(f"coherence_history:{repo}", {"points": hist})
        store.set_setting(
            f"coherence_latest:{repo}",
            {
                "score": report.get("score"),
                "above_threshold": report.get("above_threshold"),
                "emergent_coupling": report.get("emergent_coupling"),
                "active_indicator_ids": report.get("active_indicator_ids"),
                "component_panel": report.get("component_panel"),
                "at": report.get("at"),
            },
        )
    except Exception:
        pass


def soft_bind_fusion(
    home: Any,
    store: Any,
    governor: Any,
    repo: str,
    *,
    task: str = "",
    force: bool | None = None,
) -> dict[str, Any]:
    """Open fusion if CORTEX_FUSE_AUTO=1 or force — soft seam to token path."""
    auto = force if force is not None else str(
        os.environ.get("CORTEX_FUSE_AUTO", "")
    ).strip().lower() in {"1", "true", "yes", "on"}
    if not auto:
        return {"bound": False, "reason": "CORTEX_FUSE_AUTO not set"}
    try:
        from .coprocess import fuse_open, fuse_state

        st = fuse_state(store, repo)
        if st.get("open"):
            return {"bound": True, "already_open": True, "state": st}
        opened = fuse_open(
            home,
            store,
            governor,
            repo,
            task=task or "auto fusion bind",
            invent_structure=True,
            spectral_primary=True,
        )
        return {"bound": True, "already_open": False, "opened": opened}
    except Exception as exc:
        return {"bound": False, "error": f"{type(exc).__name__}: {exc}"}


def compact_coherence(report: dict[str, Any] | None) -> dict[str, Any]:
    """Agent-facing compact indicators for packets / fuse injection."""
    if not report or report.get("error"):
        return {"available": False}
    return {
        "glyph": GLYPH,
        "score": report.get("score"),
        "threshold": report.get("threshold"),
        "above_threshold": report.get("above_threshold"),
        "emergent_coupling": report.get("emergent_coupling"),
        "active_indicator_ids": report.get("active_indicator_ids") or [],
        "component_panel": report.get("component_panel") or {},
        "trend": report.get("trend") or {},
        "advice": (report.get("advice") or [])[:4],
        "claim_boundary": "Indicators only; not consciousness.",
    }
