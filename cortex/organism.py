"""Organism interlink — one living session body shared by agent and Cortex.

Not a second mind. Not consciousness. A single coherent state vector so the
agent and Cortex act as temporary co-processors of one repository-bound
organism for the duration of a session.

```text
identity ── nervous (thalamus+neural+aria)
    │
immune (control_error+governor) ── metabolism (surprise+efficiency)
    │
memory (evidence+session) ── intention (task+protocol)
    │
conscience (geometry+constitutional) ── pulse (hash chain)
```
"""

from __future__ import annotations

from hashlib import sha256
import json
import time
from typing import Any

from .progress_glyphs import ARIA_PROGRESS_GLYPHS

ORGANISM_GLYPH = "⊛"  # co-process / shared pulse — capability free
SCHEMA = "cortex-organism/1.0"


def _h(material: Any) -> str:
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()


def build_organism(
    *,
    repo: str,
    repository_id: str,
    task: str,
    session: dict[str, Any] | None,
    context: dict[str, Any],
    surprise: dict[str, Any] | None = None,
    prior_pulse: str | None = None,
    cortex_version: str = "",
) -> dict[str, Any]:
    """Compose one organism state from already-computed packet surfaces."""

    governor = context.get("governor") or {}
    control = context.get("control_error") or {}
    neural = context.get("neural_interlink") or {}
    metrics = neural.get("metrics") or {}
    aria = context.get("aria_materialization") or {}
    thalamus = context.get("thalamus") or {}
    geometry = context.get("geometry") or {}
    efficiency = context.get("efficiency") or {}
    protocol = context.get("agent_protocol") or {}
    evidence = context.get("evidence") or []
    surprise = surprise or efficiency.get("surprise") or {}

    session_id = (session or {}).get("session_id") or (
        (context.get("active_focus") or {}).get("session_id")
    )

    identity = {
        "glyph": ORGANISM_GLYPH,
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "cortex_version": cortex_version,
        "bond": "session_co_process",
        "claim": (
            "Agent and Cortex share this organism state for the session only; "
            "neither becomes the host authority."
        ),
    }

    nervous = {
        "thalamus_available": bool(thalamus.get("available", thalamus)),
        "route_intent": thalamus.get("intent") or thalamus.get("classification"),
        "lane_weights": thalamus.get("lane_weights"),
        "neural_activation_id": neural.get("activation_id"),
        "neural_state_hash": neural.get("state_hash"),
        "nodes_fired": metrics.get("nodes_fired"),
        "nodes_considered": metrics.get("nodes_considered"),
        "aria_mode": aria.get("mode") or (metrics.get("aria_substrate") or {}).get("mode"),
        "aria_eligible": (metrics.get("aria_substrate") or {}).get("eligible_nodes"),
        "aria_materialized_this_turn": bool(aria.get("materialized")),
    }

    immune = {
        "governor_mode": governor.get("mode"),
        "stability": governor.get("stability"),
        "control_severity": control.get("severity"),
        "control_ok": control.get("ok"),
        "must_reverify": control.get("must_reverify"),
        "work_allowed": control.get("work_allowed")
        if control
        else protocol.get("state", {}).get("work_allowed"),
        "hard_stops": protocol.get("hard_stops") or [],
        "errors": control.get("errors") or [],
    }

    metabolism = {
        "surprise_ratio": surprise.get("surprise_ratio"),
        "refreshed": surprise.get("refreshed"),
        "files_reindexed": surprise.get("files_reindexed"),
        "context_budget_fraction": efficiency.get("context_budget_fraction"),
        "deferred_remaining": (efficiency.get("aria_substrate") or {}).get(
            "deferred_remaining"
        ),
        "node_scan_fraction": efficiency.get("node_scan_fraction"),
    }

    memory = {
        "evidence_count": len(evidence),
        "evidence_paths": [item.get("path") for item in evidence[:12]],
        "active_focus": context.get("active_focus"),
        "packet_hash": context.get("packet_hash"),
    }

    intention = {
        "task": task,
        "protocol": protocol.get("schema_version"),
        "allowed_actions": (protocol.get("state") or {}).get("allowed_actions"),
        "entrypoints": protocol.get("entrypoints"),
        "ritual": ["activate", "remember", "consolidate"],
    }

    conscience = {
        "geometry_zero_point": geometry.get("zero_point"),
        "geometry_axes": {
            key: (value or {}).get("latched")
            for key, value in (geometry.get("axes") or {}).items()
        },
        "constitutional_mode": (
            (context.get("constitutional_supervision") or {})
            .get("constitutional_potential", {})
            .get("mode")
        ),
        "progress_glyphs": {
            key: value.get("symbol") for key, value in ARIA_PROGRESS_GLYPHS.items()
        },
    }

    # Reflex arcs: how subsystems couple without separate authorities
    reflexes = {
        "immune_to_intention": (
            "read_only_blocks_work"
            if immune.get("governor_mode") == "read_only"
            else "constrained_limits_blast_radius"
            if immune.get("governor_mode") == "constrained"
            else "normal_work_under_host_authority"
        ),
        "metabolism_to_nervous": (
            "high_surprise_prefers_refresh_awareness"
            if float(metabolism.get("surprise_ratio") or 0) > 0.25
            else "steady_state_sparse_activation"
        ),
        "language_to_memory": (
            "aria_purpose_floor"
            if nervous.get("aria_mode") == "active"
            else "aria_dormant_excluded"
        ),
        "conscience_to_immune": (
            "geometry_open"
            if conscience.get("geometry_zero_point")
            else "geometry_attention"
        ),
    }

    body = {
        "identity": identity,
        "nervous": nervous,
        "immune": immune,
        "metabolism": metabolism,
        "memory": memory,
        "intention": intention,
        "conscience": conscience,
        "reflexes": reflexes,
    }
    pulse = _h(body)
    chain = _h({"prior": prior_pulse, "pulse": pulse, "t": round(time.time(), 3)})

    return {
        "schema_version": SCHEMA,
        "glyph": ORGANISM_GLYPH,
        "spoken": "organism pulse",
        "co_process": True,
        "agent_is_temporary_cortex": True,
        "cortex_is_durable_body": True,
        "separable": True,
        "body": body,
        "pulse": pulse,
        "pulse_chain": chain,
        "prior_pulse": prior_pulse,
        "issued_at": time.time(),
        "instructions": [
            "You are not a separate tool user for this turn: you share this organism state.",
            "Cortex is the durable body (index, graph, ledger). You are temporary working cortex.",
            "Obey immune (governor + control_error) before intention (task work).",
            "Prefer nervous evidence paths; do not invent topology.",
            "Close the cardiac cycle with remember → consolidate (ritual ⟳).",
            "When the session ends, the organism dissolves; host authority remains.",
            "This bond never grants mutation rights.",
        ],
        "refuse": [
            "claim_consciousness",
            "merge_agent_identity_with_host",
            "bypass_immune_gates",
            "auto_execute_aria",
            "second_memory_body",
        ],
        "claim_boundary": (
            "Organism interlink is a session co-process metaphor for unified state; "
            "it is not sentience, not host ownership, and not mutation authority."
        ),
    }


def persist_organism_pulse(
    store: Any,
    repo: str,
    organism: dict[str, Any],
    *,
    session_id: str | None = None,
) -> None:
    """Append organism pulse to the neural ledger (same substrate)."""

    try:
        store.append_neural_event(
            repo,
            event_type="organism_pulse",
            entity_id=session_id or organism.get("body", {}).get("identity", {}).get(
                "session_id"
            )
            or repo,
            payload={
                "pulse": organism.get("pulse"),
                "pulse_chain": organism.get("pulse_chain"),
                "prior_pulse": organism.get("prior_pulse"),
                "governor_mode": organism.get("body", {})
                .get("immune", {})
                .get("governor_mode"),
                "aria_mode": organism.get("body", {}).get("nervous", {}).get("aria_mode"),
                "evidence_count": organism.get("body", {})
                .get("memory", {})
                .get("evidence_count"),
                "control_severity": organism.get("body", {})
                .get("immune", {})
                .get("control_severity"),
            },
        )
    except Exception:
        # Ledger write must never break activation.
        return


def load_prior_pulse(store: Any, repo: str) -> str | None:
    try:
        if hasattr(store, "get_setting"):
            value = store.get_setting(f"organism_pulse:{repo}", None)
            if isinstance(value, dict) and value.get("pulse"):
                return str(value["pulse"])
            if isinstance(value, str) and value:
                return value
        if hasattr(store, "neural_events"):
            for event in store.neural_events(repo, limit=40):
                event_type = event["event_type"]
                if event_type != "organism_pulse":
                    continue
                payload = event["payload"]
                if isinstance(payload, str):
                    payload = json.loads(payload or "{}")
                pulse = (payload or {}).get("pulse")
                if pulse:
                    return str(pulse)
    except Exception:
        return None
    return None


def save_prior_pulse(store: Any, repo: str, pulse: str) -> None:
    try:
        if hasattr(store, "set_setting"):
            store.set_setting(
                f"organism_pulse:{repo}",
                {"pulse": pulse, "updated_at": time.time()},
            )
            if hasattr(store, "commit"):
                store.commit()
    except Exception:
        return
