"""Packet profiles — progressive disclosure of one full context packet."""

from __future__ import annotations

from typing import Any

PROFILES = ("agent", "debug", "minimal")


def project_packet(context: dict[str, Any], profile: str = "agent") -> dict[str, Any]:
    """Project a full context packet into agent | debug | minimal views."""

    name = (profile or "agent").casefold()
    if name not in PROFILES:
        name = "agent"
    full = context
    control = full.get("control_error") or {}
    block = bool(control.get("block"))
    immune_action = control.get("immune_action")
    if name == "debug":
        return {
            "profile": "debug",
            "schema_version": full.get("schema_version"),
            "read_first": True,
            "block": block,
            "immune_action": immune_action,
            "repository": full.get("repository"),
            "task": full.get("task"),
            "governor": full.get("governor"),
            "control_error": full.get("control_error"),
            "instructions": full.get("instructions"),
            "agent_protocol": full.get("agent_protocol"),
            "aria_materialization": full.get("aria_materialization"),
            "geometry": full.get("geometry"),
            "efficiency": full.get("efficiency"),
            "thalamus": full.get("thalamus"),
            "neural_interlink": full.get("neural_interlink"),
            "evidence": full.get("evidence"),
            "structural_neighborhood": full.get("structural_neighborhood"),
            "constitutional_supervision": full.get("constitutional_supervision"),
            "progress_glyphs": full.get("progress_glyphs"),
            "organism": full.get("organism"),
            "connect_pass": full.get("connect_pass"),
            "packet_hash": full.get("packet_hash"),
            "claim_boundary": full.get("claim_boundary")
            or "Debug profile is full telemetry; still recommend-only.",
        }
    if name == "minimal":
        protocol = full.get("agent_protocol") or {}
        return {
            "profile": "minimal",
            "read_first": True,
            "block": block,
            "immune_action": immune_action,
            "task": full.get("task"),
            "control_error": full.get("control_error"),
            "governor_mode": (full.get("governor") or {}).get("mode"),
            "hard_stops": protocol.get("hard_stops"),
            "allowed_actions": (protocol.get("state") or {}).get("allowed_actions"),
            "evidence": [
                {
                    "path": item.get("path"),
                    "line_range": item.get("line_range"),
                    "kind": item.get("kind"),
                    "score": item.get("score"),
                }
                for item in (full.get("evidence") or [])
            ],
            "organism_pulse": (full.get("organism") or {}).get("pulse"),
            "organism_glyph": (full.get("organism") or {}).get("glyph"),
            "may_mutate_repository": False,
            "claim_boundary": "Minimal profile: evidence + hard stops only; never mutation authority.",
        }
    # agent (default) — lean operational packet (v6.2 token efficiency)
    neural = full.get("neural_interlink") or {}
    metrics = neural.get("metrics") or {}
    # Cap evidence text already truncated upstream; strip bulky meta here
    evidence = []
    for item in (full.get("evidence") or [])[:12]:
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "path": item.get("path"),
                "line_range": item.get("line_range"),
                "kind": item.get("kind"),
                "score": item.get("score"),
                "text": (item.get("text") or "")[:800],
                "content_hash": item.get("content_hash"),
            }
        )
    thalamus = full.get("thalamus") or {}
    # Keep primary_intent (foreign/integration tests + agents) with lean extras
    thalamus_lean = {
        "primary_intent": thalamus.get("primary_intent")
        or thalamus.get("intent")
        or thalamus.get("classification"),
        "intent": thalamus.get("intent") or thalamus.get("primary_intent"),
        "confidence": thalamus.get("confidence"),
        "uncertainty": thalamus.get("uncertainty"),
        "available": thalamus.get("available", True),
        "lane_weights": thalamus.get("lane_weights"),
    }
    glyphs = full.get("progress_glyphs") or {}
    glyph_symbols = {
        k: (v.get("symbol") if isinstance(v, dict) else v)
        for k, v in (glyphs.get("glyphs") or glyphs or {}).items()
    }
    # Constitutional: keep key present (organ gates) but strip heavy trees
    const = full.get("constitutional_supervision") or {}
    const_lean = {
        "mode": (const.get("constitutional_potential") or {}).get("mode")
        or const.get("mode"),
        "claim_boundary": const.get("claim_boundary")
        or "Constitutional supervision is observational only.",
    }
    if const.get("constitutional_potential"):
        const_lean["constitutional_potential"] = {
            "mode": (const.get("constitutional_potential") or {}).get("mode"),
        }
    return {
        "profile": "agent",
        "schema_version": full.get("schema_version"),
        "read_first": True,
        "block": block,
        "immune_action": immune_action,
        "repository": full.get("repository"),
        "task": full.get("task"),
        "governor": full.get("governor"),
        "control_error": full.get("control_error"),
        "instructions": full.get("instructions"),
        "agent_protocol": full.get("agent_protocol"),
        "constitutional_supervision": const_lean,
        "thalamus": thalamus_lean,
        "aria_materialization": {
            "mode": (full.get("aria_materialization") or {}).get("mode"),
            "materialized": (full.get("aria_materialization") or {}).get("materialized"),
        },
        "geometry": {
            "zero_point": (full.get("geometry") or {}).get("zero_point"),
            "axes": (full.get("geometry") or {}).get("axes"),
        },
        "evidence": evidence,
        "active_focus": full.get("active_focus"),
        "context_budget": full.get("context_budget"),
        "estimated_tokens": full.get("estimated_tokens"),
        "neural_interlink": {
            "activation_id": neural.get("activation_id"),
            "state_hash": neural.get("state_hash"),
            "metrics": {
                "nodes_fired": metrics.get("nodes_fired"),
                "nodes_considered": metrics.get("nodes_considered"),
                "sparse_activation_ratio": metrics.get("sparse_activation_ratio"),
            },
            "fired_paths": (neural.get("fired_paths") or [])[:8],
            "support_paths": (neural.get("support_paths") or [])[:8],
        },
        "efficiency": full.get("efficiency"),
        "progress_glyphs": {"symbols": glyph_symbols, "automatic_execution": False},
        "organism": full.get("organism"),
        "connect_pass": full.get("connect_pass"),
        "packet_hash": full.get("packet_hash"),
        "claim_boundary": (
            "Agent profile is lean operational routing; never mutation authority."
        ),
    }
