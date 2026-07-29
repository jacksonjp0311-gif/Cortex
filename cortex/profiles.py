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
    # agent (default) — operational fields only; omits heavy neural records/neighborhood
    neural = full.get("neural_interlink") or {}
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
        "constitutional_supervision": full.get("constitutional_supervision"),
        "thalamus": full.get("thalamus"),
        "environment": full.get("environment"),
        "aria_materialization": full.get("aria_materialization"),
        "geometry": full.get("geometry"),
        "evidence": full.get("evidence"),
        "active_focus": full.get("active_focus"),
        "context_budget": full.get("context_budget"),
        "estimated_tokens": full.get("estimated_tokens"),
        "neural_interlink": {
            "activation_id": neural.get("activation_id"),
            "state_hash": neural.get("state_hash"),
            "metrics": neural.get("metrics"),
            "fired_paths": neural.get("fired_paths"),
            "support_paths": neural.get("support_paths"),
        },
        "efficiency": full.get("efficiency"),
        "progress_glyphs": full.get("progress_glyphs"),
        "organism": full.get("organism"),
        "connect_pass": full.get("connect_pass"),
        "packet_hash": full.get("packet_hash"),
        "claim_boundary": (
            "Agent profile is operational evidence routing; never mutation authority."
        ),
    }
