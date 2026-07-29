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
from pathlib import Path
from typing import Any

from .progress_glyphs import ARIA_PROGRESS_GLYPHS

ORGANISM_GLYPH = "⊛"  # co-process / shared pulse — capability free
BREATHE_GLYPH = "∽"  # mid-session rebind — capability free
SCHEMA = "cortex-organism/1.1"


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
    phase: str = "systole",
    event_count: int | None = None,
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
        "phase": phase,
        "living": phase != "sealed",
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
        "block": control.get("block"),
        "immune_action": control.get("immune_action"),
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
        "session_event_count": event_count,
        "last_event_kind": (session or {}).get("last_event_kind"),
        "last_event_hash": (session or {}).get("last_event_hash"),
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
        "glyph": ORGANISM_GLYPH if phase != "breathe" else BREATHE_GLYPH,
        "spoken": "organism pulse" if phase != "breathe" else "organism breathe",
        "co_process": True,
        "agent_is_temporary_cortex": True,
        "cortex_is_durable_body": True,
        "separable": True,
        "phase": phase,
        "living": phase != "sealed",
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
            "Mid-session: remember() continues the pulse; breathe rebinds without full re-assimilate.",
            "Close the cardiac cycle with remember → consolidate (ritual ⟳) to seal.",
            "When sealed or session ends, the organism dissolves; host authority remains.",
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


def _active_session_path(home: Path, repo: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in repo)
    return Path(home) / "sessions" / f"{safe}-active.json"


def beat(
    home: Path,
    store: Any,
    repo: str,
    *,
    kind: str = "beat",
    text: str = "",
    phase: str = "diastole",
    cortex_version: str = "",
) -> dict[str, Any]:
    """Continue the organism pulse mid-session without full re-activation.

    Uses the latest runtime packet + active session + event counts so the
    co-process stays alive as the agent works and remembers.
    """

    from .config import load_repo_config, runtime_directory
    from .hippocampus import active_session

    active = active_session(home, repo)
    repository = store.repo(repo)
    if not repository:
        return {"error": "unknown_repo", "repo": repo}
    root = Path(repository["path"])
    config = load_repo_config(root)
    runtime_path = runtime_directory(root, config) / "context_latest.json"
    context: dict[str, Any] = {}
    if runtime_path.is_file():
        try:
            context = json.loads(runtime_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            context = {}
    session_id = (active or {}).get("session_id")
    events = list(store.events(repo, session_id)) if session_id else []
    prior = load_prior_pulse(store, repo)
    task = (active or {}).get("task") or context.get("task") or "session"
    organism = build_organism(
        repo=repo,
        repository_id=str(repository["repository_id"] or ""),
        task=str(task),
        session=active,
        context=context
        if context
        else {"governor": {}, "control_error": {}, "agent_protocol": {}},
        surprise=(context.get("efficiency") or {}).get("surprise"),
        prior_pulse=prior,
        cortex_version=cortex_version,
        phase=phase,
        event_count=len(events),
    )
    organism["body"]["memory"]["beat"] = {
        "kind": kind,
        "text_preview": (text or "")[:240],
        "event_count": len(events),
    }
    organism["pulse"] = _h(organism["body"])
    organism["pulse_chain"] = _h(
        {"prior": prior, "pulse": organism["pulse"], "t": round(time.time(), 3)}
    )
    persist_organism_pulse(store, repo, organism, session_id=session_id)
    save_prior_pulse(store, repo, organism["pulse"])
    if active:
        active["organism_pulse"] = organism["pulse"]
        active["organism_phase"] = phase
        active["updated_at"] = time.time()
        try:
            _active_session_path(home, repo).write_text(
                json.dumps(active, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            pass
    return organism


def breathe(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    task: str | None = None,
    *,
    budget: int = 800,
    profile: str = "agent",
) -> dict[str, Any]:
    """Mid-session rebind: packet-fast activate + living phase, no full assimilate."""

    from . import __version__
    from .activation import activate_repository
    from .hippocampus import active_session

    active = active_session(home, repo)
    resolved_task = task or (active or {}).get("task") or "continue session"
    result = activate_repository(
        home,
        store,
        governor,
        repo,
        str(resolved_task),
        budget=budget,
        refresh="never",
        profile=profile,
    )
    # Re-tag phase as breathe (rebind) while keeping chain from activate.
    org = result.get("organism") or {}
    if org:
        org["phase"] = "breathe"
        org["glyph"] = BREATHE_GLYPH
        org["spoken"] = "organism breathe"
        org["living"] = True
        result["organism"] = org
        if isinstance(result.get("context"), dict):
            result["context"]["organism"] = org
    result["evolution"] = "living_organism_breathe"
    result["version"] = __version__
    return result


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
                "phase": organism.get("phase")
                or organism.get("body", {}).get("identity", {}).get("phase"),
                "governor_mode": organism.get("body", {})
                .get("immune", {})
                .get("governor_mode"),
                "aria_mode": organism.get("body", {}).get("nervous", {}).get("aria_mode"),
                "nodes_fired": organism.get("body", {})
                .get("nervous", {})
                .get("nodes_fired"),
                "nodes_considered": organism.get("body", {})
                .get("nervous", {})
                .get("nodes_considered"),
                "evidence_count": organism.get("body", {})
                .get("memory", {})
                .get("evidence_count"),
                "control_severity": organism.get("body", {})
                .get("immune", {})
                .get("control_severity"),
                "block": organism.get("body", {}).get("immune", {}).get("block"),
                "immune_code": (
                    (organism.get("body", {}).get("immune", {}) or {}).get(
                        "immune_action"
                    )
                    or {}
                ).get("code"),
                "surprise_ratio": (
                    (organism.get("body", {}).get("metabolism", {}) or {}).get(
                        "surprise"
                    )
                    or {}
                ).get("surprise_ratio"),
                "node_scan_fraction": (
                    (organism.get("body", {}).get("metabolism", {}) or {}).get(
                        "efficiency"
                    )
                    or {}
                ).get("node_scan_fraction"),
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
