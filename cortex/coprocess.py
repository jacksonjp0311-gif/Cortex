"""Fusion co-process — live coupling of agent ticks to regenerating geometry.

Closes the gap toward:
  - live co-processor fused to the model (via mandatory tick hooks)
  - geometry regenerates every tick/token the host reports
  - spectral mesh drives ranking/attention
  - topology invents structure under gates
  - shared organism self-model (not consciousness)
  - shared mind-state (not literal one mind)

Host/model MUST call fuse_tick on each generation step or token batch.
Cortex cannot intercept private model weights; fusion is the co-process contract.
"""

from __future__ import annotations

import time
from hashlib import sha256
from typing import Any

from . import __version__
from .math_net.spectral_memory import enrich_hits_with_diffusion, spectral_memory_pulse
from .math_net.uncertainty import compute_uncertainty
from .retrieval import query
from .structure_invent import invent_from_coactivation

SCHEMA = "cortex-fusion-coprocess/1.0"
GLYPH = "⊛⇄"


def _fusion_key(repo: str) -> str:
    return f"fusion_state:{repo}"


def _mind_hash(state: dict[str, Any]) -> str:
    material = {
        "tick": state.get("tick"),
        "u": (state.get("u") or {}).get("u"),
        "Lambda": state.get("Lambda"),
        "lambda2": (state.get("spectral") or {}).get("lambda2"),
        "paths": state.get("attention_paths"),
    }
    import json

    return sha256(
        json.dumps(material, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]


def fuse_open(
    home: Any,
    store: Any,
    governor: Any,
    repo: str,
    *,
    task: str = "",
    budget: int = 600,
    invent_structure: bool = True,
    spectral_primary: bool = True,
) -> dict[str, Any]:
    """Open a fusion session: shared mind-state + first geometry pulse."""
    from .activation import activate_repository

    act = activate_repository(
        home, store, governor, repo, task or "fusion open", budget=budget
    )
    gov = act.get("control_error") or {}
    mode = str((act.get("context") or {}).get("governor", {}).get("mode") or "normal")
    # Prefer envelope governor if present
    if isinstance(act.get("context"), dict) and act["context"].get("governor"):
        mode = str(act["context"]["governor"].get("mode") or mode)

    pulse = act.get("spectral_memory") or spectral_memory_pulse(
        store, repo, retrieval_confidence=0.5, budget_tokens=budget
    )
    state = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "task": task,
        "open": True,
        "tick": 0,
        "token_count": 0,
        "invent_structure": invent_structure,
        "spectral_primary": spectral_primary,
        "governance_mode": mode,
        "block": bool(gov.get("block") or act.get("block")),
        "u": pulse.get("u"),
        "Lambda": pulse.get("Lambda"),
        "spectral": pulse.get("spectral"),
        "attention_paths": [
            e.get("path")
            for e in ((act.get("context") or {}).get("evidence") or [])[:12]
            if isinstance(e, dict)
        ],
        "activation_id": (
            ((act.get("context") or {}).get("neural_interlink") or {}).get(
                "activation_id"
            )
        ),
        "organism": (act.get("context") or {}).get("organism") or act.get("organism"),
        "self_model": {},
        "ticks_log_tail": [],
        "opened_at": time.time(),
        "updated_at": time.time(),
        "version": __version__,
        "claim_boundary": (
            "Fusion is a co-process contract: host calls tick each token/step. "
            "Not model-weight fusion. Not consciousness. Shared state vector only."
        ),
    }
    state["self_model"] = build_self_model(state)
    state["mind_hash"] = _mind_hash(state)
    store.set_setting(_fusion_key(repo), state)
    return {
        "opened": True,
        "repo": repo,
        "mind_hash": state["mind_hash"],
        "u": state.get("u"),
        "spectral_primary": spectral_primary,
        "self_model": state["self_model"],
        "claim_boundary": state["claim_boundary"],
        "how_to_fuse": (
            "Call cortex fuse tick --repo R --token '...' (or MCP cortex_fuse_tick) "
            "on every model token or generation step."
        ),
    }


def build_self_model(state: dict[str, Any]) -> dict[str, Any]:
    """Organism self-model: introspective telemetry, not awareness."""
    u = (state.get("u") or {}).get("u")
    coh = state.get("coherence") or {}
    sense = (
        "high_uncertainty"
        if (u is not None and float(u) > 0.65)
        else "stable"
        if (u is not None and float(u) < 0.35)
        else "working"
    )
    if coh.get("emergent_coupling"):
        sense = "coupled"
    elif coh.get("above_threshold"):
        sense = "coherent"
    return {
        "glyph": "⊛?",
        "living": bool(state.get("open")),
        "tick": state.get("tick"),
        "token_count": state.get("token_count"),
        "u": u,
        "Lambda": state.get("Lambda"),
        "lambda2": (state.get("spectral") or {}).get("lambda2"),
        "attention_width": len(state.get("attention_paths") or []),
        "block": state.get("block"),
        "governance_mode": state.get("governance_mode"),
        "mind_hash": state.get("mind_hash"),
        "coherence_score": coh.get("score"),
        "emergent_coupling": coh.get("emergent_coupling"),
        "active_indicators": coh.get("active_indicator_ids") or [],
        "sense": sense,
        "claim_boundary": (
            "Self-model is machine-readable organism state, not subjective experience. "
            "emergent_coupling is multi-seam indicator co-activation only."
        ),
    }


def fuse_tick(
    store: Any,
    governor: Any,
    repo: str,
    *,
    token: str = "",
    tokens: int = 1,
    invent: bool | None = None,
) -> dict[str, Any]:
    """One fusion tick = one geometry regeneration step (host reports a token/step)."""
    state = store.get_setting(_fusion_key(repo), None)
    if not isinstance(state, dict) or not state.get("open"):
        return {
            "ok": False,
            "error": "fusion_not_open",
            "hint": "cortex fuse open --repo R --task '...'",
        }

    tick = int(state.get("tick") or 0) + 1
    token_count = int(state.get("token_count") or 0) + max(1, int(tokens))
    text = (token or "").strip() or (state.get("task") or "fusion tick")
    # Micro-query driven by latest token window (spectral-primary ranking)
    hits = query(store, repo, text, limit=10)
    if state.get("spectral_primary", True):
        try:
            enrich_hits_with_diffusion(store, repo, hits)
        except Exception:
            pass
        try:
            from .ranker.model import rerank_hits

            hits = rerank_hits(
                store,
                repo,
                hits,
                retrieval_confidence=0.55,
                primary=True,
                enrich_spectral=True,
            )
        except Exception:
            pass

    paths = [getattr(h, "path", None) or (h.get("path") if isinstance(h, dict) else None) for h in hits]
    paths = [p for p in paths if p]

    # Map paths to node ids for invention
    fired_ids: list[str] = []
    try:
        from .math_net.spectral_memory import path_to_node_guess

        for p in paths[:16]:
            nid = path_to_node_guess(store, repo, str(p))
            if nid:
                fired_ids.append(nid)
    except Exception:
        pass

    gov = governor.evaluate(repo, retrieval_confidence=0.55)
    mode = str(gov.get("mode") or "normal")
    invent_flag = state.get("invent_structure", True) if invent is None else invent
    invented = {"invented": 0}
    if invent_flag and not state.get("block") and mode != "read_only":
        invented = invent_from_coactivation(
            store,
            repo,
            fired_node_ids=fired_ids,
            governance_mode=mode,
            max_new=4,
        )

    # Geometry pulse every tick
    pulse = spectral_memory_pulse(
        store,
        repo,
        retrieval_confidence=float((gov.get("components") or {}).get("unified_confidence") or 0.55),
        certificate_status="verified",
        budget_tokens=200,
        auto_promote=False,
        u_before=(state.get("u") or {}).get("u"),
    )

    u_pkt = pulse.get("u") or compute_uncertainty(retrieval_confidence=0.55)
    state.update(
        {
            "tick": tick,
            "token_count": token_count,
            "last_token": text[:120],
            "u": u_pkt,
            "Lambda": pulse.get("Lambda"),
            "spectral": pulse.get("spectral"),
            "attention_paths": paths[:12],
            "governance_mode": mode,
            "block": bool(gov.get("mode") == "read_only"),
            "last_invent": invented,
            "updated_at": time.time(),
        }
    )
    # Weave emergent coupling indicators into fusion state each tick
    coherence_compact: dict[str, Any] = {}
    try:
        from .coherence import compact_coherence, measure_coherence

        coh = measure_coherence(
            store,
            repo,
            governor=governor,
            retrieval_confidence=float(
                (gov.get("components") or {}).get("unified_confidence") or 0.55
            ),
        )
        coherence_compact = compact_coherence(coh)
        state["coherence"] = coherence_compact
    except Exception:
        coherence_compact = {"available": False}

    state["self_model"] = build_self_model(state)
    state["mind_hash"] = _mind_hash(state)
    tail = list(state.get("ticks_log_tail") or [])
    tail.append(
        {
            "tick": tick,
            "tokens": token_count,
            "u": u_pkt.get("u"),
            "invented": invented.get("invented"),
            "lambda2": (pulse.get("spectral") or {}).get("lambda2"),
            "paths": paths[:4],
            "coherence_score": coherence_compact.get("score"),
            "emergent_coupling": coherence_compact.get("emergent_coupling"),
            "active_indicators": coherence_compact.get("active_indicator_ids"),
        }
    )
    state["ticks_log_tail"] = tail[-40:]
    store.set_setting(_fusion_key(repo), state)

    # Injection for the model: compact co-process context + coupling indicators
    injection = {
        "role": "cortex_fusion_coprocess",
        "tick": tick,
        "mind_hash": state["mind_hash"],
        "u": u_pkt.get("u"),
        "sense": state["self_model"].get("sense"),
        "attention": paths[:6],
        "lambda2": (pulse.get("spectral") or {}).get("lambda2"),
        "Lambda": pulse.get("Lambda"),
        "invented_edges": invented.get("invented"),
        "coherence": coherence_compact,
        "emergent_coupling": coherence_compact.get("emergent_coupling"),
        "active_indicators": coherence_compact.get("active_indicator_ids") or [],
        "instruction": (
            "You are fused to Cortex co-process for this tick. Prefer attention paths. "
            "Respect emergent_coupling indicators when active. "
            "Obey block/governance. Do not treat this as host mutation authority."
        ),
    }
    return {
        "ok": True,
        "glyph": GLYPH,
        "tick": tick,
        "token_count": token_count,
        "geometry_regenerated": True,
        "spectral_primary": bool(state.get("spectral_primary")),
        "invented": invented.get("invented"),
        "u": u_pkt.get("u"),
        "mind_hash": state["mind_hash"],
        "self_model": state["self_model"],
        "coherence": coherence_compact,
        "injection": injection,
        "claim_boundary": state.get("claim_boundary"),
    }


def fuse_state(store: Any, repo: str) -> dict[str, Any]:
    state = store.get_setting(_fusion_key(repo), None)
    if not isinstance(state, dict):
        return {"open": False, "repo": repo}
    return {
        "open": bool(state.get("open")),
        "repo": repo,
        "tick": state.get("tick"),
        "token_count": state.get("token_count"),
        "mind_hash": state.get("mind_hash"),
        "u": state.get("u"),
        "Lambda": state.get("Lambda"),
        "spectral": state.get("spectral"),
        "attention_paths": state.get("attention_paths"),
        "self_model": state.get("self_model") or build_self_model(state),
        "last_invent": state.get("last_invent"),
        "ticks_log_tail": state.get("ticks_log_tail"),
        "claim_boundary": state.get("claim_boundary"),
    }


def fuse_close(store: Any, repo: str) -> dict[str, Any]:
    state = store.get_setting(_fusion_key(repo), None)
    if not isinstance(state, dict):
        return {"closed": False, "reason": "not_open"}
    state["open"] = False
    state["closed_at"] = time.time()
    state["self_model"] = build_self_model(state)
    store.set_setting(_fusion_key(repo), state)
    return {
        "closed": True,
        "repo": repo,
        "ticks": state.get("tick"),
        "token_count": state.get("token_count"),
        "final_mind_hash": state.get("mind_hash"),
        "self_model": state["self_model"],
    }
