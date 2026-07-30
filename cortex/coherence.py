"""System coherence — wire seams into one measurable field.

Aggregates blood (U), geometry (A/dual/spectral), learning (ranker),
ops (fusion/continuum), and gates (Governor) into a single score.

COHERENCE_THRESHOLD: above this, seams are "coupled enough" for
spectral-primary + invent recommendations. Not consciousness.
"""

from __future__ import annotations

import os
import time
from typing import Any

from . import __version__

SCHEMA = "cortex-coherence/1.0"
GLYPH = "⧉≈"
# Empirical operating point: system feels "one loop" above this (0–1).
COHERENCE_THRESHOLD = 0.62


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def measure_coherence(
    store: Any,
    repo: str,
    *,
    governor: Any | None = None,
    home: Any | None = None,
    retrieval_confidence: float | None = None,
) -> dict[str, Any]:
    """Compute seam-coupled coherence score and coupling flags."""
    components: dict[str, float] = {}
    notes: list[str] = []
    seams: dict[str, Any] = {}

    # --- Blood: U ---
    u_val = 0.5
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
            gov = {}
            u_pkt = compute_uncertainty(retrieval_confidence=conf)
            mode = "unknown"
        u_val = float(u_pkt.get("u") if isinstance(u_pkt, dict) else 0.5)
        # Low U → higher coherence contribution
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

    # --- Geometry: dual graph + operator + spectral ---
    try:
        from .math_net.operator import build_operator_A, dual_graph_report
        from .math_net.spectral import spectral_slice

        dual = dual_graph_report(store, repo)
        op = build_operator_A(store, repo, max_nodes=120)
        n = int(op.get("n") or 0)
        e = int(op.get("edge_count") or 0)
        neural_e = int(dual.get("neural_synapses") or 0)
        struct_e = dual.get("structural_edges")
        # Dual seam: neural mass present and (if structural known) not absurdly empty
        if neural_e > 0 and n > 1 and e > 0:
            components["geometry_mass"] = _clip01(min(1.0, (n / 50.0) * 0.5 + (e / 80.0) * 0.5))
        else:
            components["geometry_mass"] = 0.2 if neural_e == 0 else 0.45
        if struct_e is not None and int(struct_e) > 0 and neural_e > 0:
            ratio = neural_e / max(1, int(struct_e))
            # sweet band ~0.2–3.0
            components["dual_align"] = _clip01(1.0 - abs(ratio - 1.0) / 3.0)
        else:
            components["dual_align"] = 0.55  # unknown structural table still ok
            notes.append("dual:structural_partial")

        spec = spectral_slice(store, repo, max_nodes=100)
        lam2 = float(spec.get("lambda2") or 0.0) if spec.get("ok") else 0.0
        # algebraic connectivity present and finite → geometry is spectral-live
        components["spectral_live"] = (
            _clip01(min(1.0, lam2 * 2.0 + 0.35)) if spec.get("ok") and n > 1 else 0.25
        )
        seams["dual"] = {
            "neural_synapses": neural_e,
            "structural_edges": struct_e,
            "operator_n": n,
            "operator_edges": e,
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

    # --- Filter state Λ_g ---
    try:
        from .math_net.kernel_state import _load_state

        st = _load_state(store, repo)
        lam = st.get("Lambda") or {}
        mass = sum(float(v) for v in lam.values()) if lam else 0.0
        components["lambda_state"] = _clip01(mass / 3.0)
        seams["Lambda"] = lam
        seams["lambda_pulses"] = st.get("pulses")
    except Exception as exc:
        components["lambda_state"] = 0.3
        notes.append(f"Lambda:{type(exc).__name__}")

    # --- Learning: ranker ---
    try:
        from .ranker.model import ranker_status

        rk = ranker_status(store, repo)
        tc = int(rk.get("train_count") or 0)
        components["ranker_warm"] = _clip01(tc / 20.0)
        seams["ranker_train_count"] = tc
        seams["ranker_frozen"] = rk.get("frozen")
    except Exception as exc:
        components["ranker_warm"] = 0.2
        notes.append(f"ranker:{type(exc).__name__}")

    # --- Fusion seam ---
    fusion_open = False
    try:
        from .coprocess import fuse_state

        fs = fuse_state(store, repo)
        fusion_open = bool(fs.get("open"))
        ticks = int(fs.get("tick") or 0)
        components["fusion_coupling"] = (
            _clip01(0.5 + min(0.5, ticks / 20.0)) if fusion_open else 0.35
        )
        seams["fusion"] = {
            "open": fusion_open,
            "tick": ticks,
            "mind_hash": fs.get("mind_hash"),
            "token_count": fs.get("token_count"),
        }
    except Exception as exc:
        components["fusion_coupling"] = 0.3
        notes.append(f"fusion:{type(exc).__name__}")

    # --- Hygiene / weak tail ---
    try:
        from .prune import policy_preview

        prev = policy_preview(store, repo)
        soft = int(
            ((prev.get("policies") or {}).get("integrate_soft") or {}).get("would_prune")
            or 0
        )
        # huge unpruned soft tail slightly hurts coherence (noise)
        components["prune_hygiene"] = _clip01(1.0 - min(1.0, soft / 500.0))
        seams["would_prune_integrate_soft"] = soft
        seams["recommended_prune"] = prev.get("recommended")
    except Exception as exc:
        components["prune_hygiene"] = 0.5
        notes.append(f"prune:{type(exc).__name__}")

    # Weighted field
    weights = {
        "certainty": 0.14,
        "governor_open": 0.12,
        "geometry_mass": 0.14,
        "dual_align": 0.10,
        "spectral_live": 0.14,
        "lambda_state": 0.10,
        "ranker_warm": 0.10,
        "fusion_coupling": 0.10,
        "prune_hygiene": 0.06,
    }
    score = 0.0
    wsum = 0.0
    for k, w in weights.items():
        score += w * float(components.get(k, 0.0))
        wsum += w
    score = _clip01(score / wsum if wsum else 0.0)

    above = score >= COHERENCE_THRESHOLD
    # Coupling flags (emergent *indicators*, not magic)
    coupling = {
        "blood_geometry": components.get("certainty", 0) > 0.4
        and components.get("spectral_live", 0) > 0.4,
        "geometry_learning": components.get("geometry_mass", 0) > 0.4
        and components.get("ranker_warm", 0) > 0.3,
        "ops_geometry": components.get("fusion_coupling", 0) > 0.45
        or components.get("lambda_state", 0) > 0.4,
        "gates_aligned": components.get("governor_open", 0) >= 0.55
        and components.get("prune_hygiene", 0) > 0.35,
    }
    coupled_count = sum(1 for v in coupling.values() if v)
    # "Emergent" in engineering sense: multi-seam coupling without a single driver
    emergent_coupling = above and coupled_count >= 3

    advice: list[str] = []
    if not above:
        if components.get("geometry_mass", 0) < 0.4:
            advice.append("compile_interlink_or_bootstrap")
        if components.get("ranker_warm", 0) < 0.3:
            advice.append("run_evolve_or_continuum")
        if components.get("fusion_coupling", 0) < 0.45:
            advice.append("fuse_open_or_fuse_proxy")
        if components.get("certainty", 0) < 0.4:
            advice.append("refresh_evidence_or_narrow_task")
    else:
        advice.append("hold_course_spectral_primary")
        if not fusion_open:
            advice.append("optional_fuse_proxy_for_token_regen")

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "score": round(score, 4),
        "threshold": COHERENCE_THRESHOLD,
        "above_threshold": above,
        "components": {k: round(float(v), 4) for k, v in components.items()},
        "weights": weights,
        "coupling": coupling,
        "coupled_seams": coupled_count,
        "emergent_coupling": emergent_coupling,
        "seams": seams,
        "notes": notes,
        "advice": advice,
        "auto_fuse_env": os.environ.get("CORTEX_FUSE_AUTO", ""),
        "claim_boundary": (
            "Coherence is a seam-coupling score over real telemetry. "
            "emergent_coupling means multiple independent seams are jointly high — "
            "not consciousness, not one mind, not guaranteed capability."
        ),
        "at": time.time(),
    }


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
