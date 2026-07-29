"""Distill operational intelligence into the durable body.

Reads the living lattice (mesh, kernels, ranker, causal, immune), folds it with
fixed doctrine claims, and seals via ritual — same substrate, recommend-only.
Glyphic medium ☰; never mutation authority.

v6.4: pulse_on_connect resonates intelligence at connect frequency.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from . import __version__
from .governor import Governor
from .interconnect import mesh_dashboard
from .kernels import kernels_status
from .resonance import clamp
from .session_ritual import run_session_ritual

GLYPH = "☰"
SCHEMA = "cortex-distill-intel/1.1"
PULSE_EVERY = 2  # light doctrine beat every N connects
SEAL_EVERY = 7  # full distill seal every N connects

# Fixed intelligence distilled from building/operating the lattice (v3→v6.2).
# These are architecture lessons, not lab claims or host rights.
DOCTRINE_CLAIMS: list[dict[str, str]] = [
    {
        "kind": "invariant",
        "text": (
            "[intel] One body law holds: single SQLite, single Governor, single "
            "consolidation path. New organs must couple to connect pulse or they are junk."
        ),
    },
    {
        "kind": "invariant",
        "text": (
            "[intel] Clock ≠ memory ≠ decision. Connect/Thalamus broadcast; "
            "kernels/graph/cards filter; Governor/immune/host decide. Relevance never rights."
        ),
    },
    {
        "kind": "lesson",
        "text": (
            "[intel] Memory is a spectrum (reset|integrate|retain), not one ρ. "
            "Prune reset dead weight; protect retain hierarchy and evidence rows."
        ),
    },
    {
        "kind": "lesson",
        "text": (
            "[intel] Fat packets waste agent tokens. Lean agent profile + budget 800 + "
            "path diversity beats dumping full neural/environment trees."
        ),
    },
    {
        "kind": "lesson",
        "text": (
            "[intel] Fold before inventing: when docs lag the lattice, heal with "
            "DATA_MODEL/ARCHITECTURE/packets — not a second database."
        ),
    },
    {
        "kind": "constraint",
        "text": (
            "[intel] Multi-agent is opt-in; tokens never mint host.mutate. "
            "Default single-agent remains the efficient path."
        ),
    },
    {
        "kind": "lesson",
        "text": (
            "[intel] Glyphs are the medium for speed (immune ⚠, mesh ⧉, kernels ≋, "
            "prune ✂) — labels only, never opcodes or auto-ARIA execution."
        ),
    },
    {
        "kind": "discovery",
        "text": (
            "[intel] Growth pressure is real after rapid v5–v6 climbs: prefer "
            "steady-state cadence (measure mesh, prune, distill) over new organs."
        ),
    },
    {
        "kind": "lesson",
        "text": (
            "[intel] Efficient loop: immune → interconnect/kernels (compact) → "
            "activate lean → remember → ritual seal → dashboard --mesh."
        ),
    },
    {
        "kind": "invariant",
        "text": (
            "[intel] Pulse frequency: intelligence rides the connect beat — light "
            "doctrine every 2 passes, full distill seal every 7. Same substrate rhythm."
        ),
    },
    {
        "kind": "lesson",
        "text": (
            "[intel] Resonate means mesh_green + spectral balance + immune open + "
            "lean packets in phase — not louder metrics or new organs."
        ),
    },
    {
        "kind": "invariant",
        "text": (
            "[intel] Identity continuity: same filesystem path with different repo "
            "names (e.g. CortexV5CI vs CortexTeach) are separate durable namespaces — "
            "never merge teaching mass without cortex identity check."
        ),
    },
    {
        "kind": "lesson",
        "text": (
            "[intel] Integrity can hold while evidence selection fails: ARIA-active "
            "passes must materialize substrate and prove implementation (cortex/*.py + "
            "vendor anchors), not only rank Discovery Cards."
        ),
    },
]


def lattice_resonance(obs: dict[str, Any], metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Coherence score at lattice frequency (not consciousness)."""

    metrics = metrics or {}
    immune = metrics.get("immune") or {}
    spectrum = obs.get("xi_spectrum") or {}
    # Component strings of the intelligence fork
    mesh = 1.0 if obs.get("mesh_green") else 0.35
    if obs.get("bottlenecks"):
        mesh = clamp(mesh - 0.08 * len(obs["bottlenecks"]))
    immune_s = 0.25 if immune.get("block") or obs.get("immune_block") else 1.0
    # Spectral balance: prefer integrate+retain mass without reset monopoly
    shares = []
    for name in ("reset", "integrate", "retain"):
        row = spectrum.get(name) or {}
        shares.append(float(row.get("share") or 0.0))
    if sum(shares) <= 0:
        spectral = 0.55
    else:
        # Balanced field: not all mass in one class
        mx = max(shares)
        spectral = clamp(1.0 - max(0.0, mx - 0.75) * 2.0)
        if float((spectrum.get("retain") or {}).get("rho") or 0) > 0.9:
            spectral = clamp(spectral + 0.1)
    hnsw = 1.0 if obs.get("hnsw") else 0.45
    ranker = 0.4 if obs.get("ranker_frozen") else clamp(
        0.55 + 0.05 * min(10, int(obs.get("ranker_train") or 0))
    )
    pulse = clamp(0.4 + 0.06 * min(10, int(obs.get("pass_count") or 0)))
    components = {
        "mesh": round(mesh, 4),
        "immune": round(immune_s, 4),
        "spectral": round(spectral, 4),
        "hnsw": round(hnsw, 4),
        "ranker": round(ranker, 4),
        "pulse": round(pulse, 4),
    }
    values = [v for v in components.values() if v > 0]
    harmonic = len(values) / sum(1.0 / v for v in values) if values else 0.0
    intensity = clamp(harmonic)
    if intensity >= 0.88:
        brightness = "resonant"
    elif intensity >= 0.72:
        brightness = "in_phase"
    elif intensity >= 0.55:
        brightness = "steady"
    else:
        brightness = "detuned"
    return {
        "schema_version": "cortex-lattice-resonance/1.0",
        "glyph": "☰",
        "intensity": round(intensity, 4),
        "brightness": brightness,
        "components": components,
        "in_phase": brightness in {"resonant", "in_phase"},
        "claim_boundary": "Lattice resonance is telemetry; not consciousness or rights.",
    }


def observe_lattice(
    store: Any,
    repo: str,
    *,
    governor: Any | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    """Snapshot mesh + kernels + gates for distillation (telemetry only)."""

    mesh = mesh_dashboard(store, repo, governor=governor, home=home)
    kernels = kernels_status(store, repo)
    return {
        "version": __version__,
        "mesh_green": mesh.get("mesh_green"),
        "bottlenecks": mesh.get("bottlenecks") or [],
        "pass_count": mesh.get("connect_pass_count"),
        "dominant_kernel": mesh.get("dominant_kernel") or kernels.get("dominant"),
        "xi_spectrum": mesh.get("xi_spectrum") or kernels.get("retention"),
        "ranker_train": (mesh.get("ranker") or {}).get("train_count"),
        "ranker_frozen": (mesh.get("ranker") or {}).get("frozen"),
        "hnsw": (mesh.get("hnsw") or {}).get("available"),
        "causal": mesh.get("causal"),
        "immune_block": (mesh.get("immune") or {}).get("block"),
        "claim_boundary": "Observation is telemetry; not authorization.",
    }


def claims_from_observation(obs: dict[str, Any]) -> list[dict[str, str]]:
    """Turn live lattice state into short durable claims."""

    out: list[dict[str, str]] = []
    out.append(
        {
            "kind": "discovery",
            "text": (
                f"[intel/live] Cortex {obs.get('version')} mesh_green="
                f"{obs.get('mesh_green')} pass_count={obs.get('pass_count')} "
                f"dominant_kernel={obs.get('dominant_kernel')} "
                f"hnsw={obs.get('hnsw')} immune_block={obs.get('immune_block')} "
                f"ranker_train={obs.get('ranker_train')} frozen={obs.get('ranker_frozen')}."
            ),
        }
    )
    bottlenecks = obs.get("bottlenecks") or []
    if bottlenecks:
        out.append(
            {
                "kind": "wound",
                "text": (
                    "[intel/live] Mesh bottlenecks: "
                    + ", ".join(str(b) for b in bottlenecks[:8])
                    + ". Prefer prune/heal over new organs."
                ),
            }
        )
    else:
        out.append(
            {
                "kind": "discovery",
                "text": (
                    "[intel/live] No mesh bottlenecks reported; maintain steady-state "
                    "cadence (connect, prune, distill) rather than feature sprawl."
                ),
            }
        )
    spectrum = obs.get("xi_spectrum") or {}
    if spectrum:
        parts = []
        for name in ("reset", "integrate", "retain"):
            row = spectrum.get(name) or {}
            if row:
                parts.append(
                    f"{name}:ρ={row.get('rho')} ξ={row.get('xi')} mass={row.get('mass')}"
                )
        if parts:
            out.append(
                {
                    "kind": "discovery",
                    "text": "[intel/live] Spectral field " + " | ".join(parts),
                }
            )
    return out


def distill_intelligence(
    home: Path,
    store: Any,
    governor: Governor | Any,
    repo: str,
    *,
    seal: bool = True,
    include_doctrine: bool = True,
    force: bool = True,
) -> dict[str, Any]:
    """Observe lattice, fold doctrine + live claims, ritual into durable body."""

    obs = observe_lattice(store, repo, governor=governor, home=home)
    resonance = lattice_resonance(obs)
    memories: list[dict[str, str]] = [
        {
            "kind": "focus",
            "text": f"{GLYPH} Distill intelligence pass — Cortex {__version__}",
        }
    ]
    if include_doctrine:
        memories.extend(DOCTRINE_CLAIMS)
    memories.extend(claims_from_observation(obs))
    memories.append(
        {
            "kind": "discovery",
            "text": (
                f"[intel/resonate] brightness={resonance.get('brightness')} "
                f"intensity={resonance.get('intensity')} "
                f"components={resonance.get('components')}"
            ),
        }
    )
    memories.append(
        {
            "kind": "constraint",
            "text": (
                "[intel] Refuse: second DB, auto-ARIA exec, packet-as-authorization, "
                "host.mutate from relevance, unsolicited foreign scans."
            ),
        }
    )

    ritual = run_session_ritual(
        home,
        store,
        governor,
        repo,
        "Distill operational intelligence into durable Cortex body",
        memories=memories,
        consolidate_session=seal,
        profile="agent",
        force=force,
        contract="default",
    )
    result = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "version": __version__,
        "observation": obs,
        "resonance": resonance,
        "claims_count": len(memories),
        "doctrine_count": len(DOCTRINE_CLAIMS) if include_doctrine else 0,
        "ritual": {
            "activation": ritual.get("activation"),
            "gates_sealed": ritual.get("gates_sealed"),
            "blocked": ritual.get("blocked_by_control_error"),
            "block_reason": ritual.get("block_reason"),
            "consolidate": ritual.get("consolidate"),
            "session_id": ritual.get("session_id"),
        },
        "claim_boundary": (
            "Distilled intelligence is local operational doctrine and telemetry; "
            "it never authorizes host mutation."
        ),
    }
    try:
        store.set_setting(
            f"intel_pulse:{repo}",
            {
                "at": time.time(),
                "resonance": resonance,
                "observation": {
                    k: obs.get(k)
                    for k in (
                        "mesh_green",
                        "dominant_kernel",
                        "pass_count",
                        "hnsw",
                        "immune_block",
                    )
                },
                "version": __version__,
            },
        )
    except Exception:
        pass
    return result


def pulse_intelligence(
    store: Any,
    home: Path | None,
    repo: str,
    *,
    metrics: dict[str, Any] | None = None,
    pass_count: int = 0,
    session_id: str | None = None,
    governor: Any | None = None,
    pulse_every: int = PULSE_EVERY,
    seal_every: int = SEAL_EVERY,
) -> dict[str, Any]:
    """Ride the connect beat: light doctrine pulse, periodic full distill seal.

    Never blocks activation. Skips heavy seal when immune blocked or no home.
    """

    metrics = metrics or {}
    out: dict[str, Any] = {
        "schema_version": "cortex-intel-pulse/1.0",
        "glyph": GLYPH,
        "pass_count": pass_count,
        "beat": None,
    }
    if pass_count <= 0:
        out["beat"] = "silent"
        return out

    # Always compute resonance (cheap-ish observation)
    try:
        obs = observe_lattice(store, repo, governor=governor, home=home)
        # overlay immune from this pass metrics
        if metrics.get("immune"):
            obs["immune_block"] = bool(
                (metrics.get("immune") or {}).get("block") or obs.get("immune_block")
            )
        resonance = lattice_resonance(obs, metrics)
        out["resonance"] = resonance
        out["observation"] = {
            "mesh_green": obs.get("mesh_green"),
            "dominant_kernel": obs.get("dominant_kernel"),
            "bottlenecks": obs.get("bottlenecks"),
        }
        store.set_setting(
            f"intel_pulse:{repo}",
            {
                "at": time.time(),
                "resonance": resonance,
                "pass_count": pass_count,
                "version": __version__,
            },
        )
    except Exception as exc:
        out["resonance_error"] = f"{type(exc).__name__}: {exc}"
        return out

    if (metrics.get("immune") or {}).get("block"):
        out["beat"] = "held_immune"
        return out

    # Full seal on cadence
    if home is not None and seal_every > 0 and pass_count % seal_every == 0:
        try:
            gov = governor or Governor(home, store)
            sealed = distill_intelligence(
                home, store, gov, repo, seal=True, force=True
            )
            out["beat"] = "seal"
            out["distill"] = {
                "claims_count": sealed.get("claims_count"),
                "gates_sealed": (sealed.get("ritual") or {}).get("gates_sealed"),
                "resonance": sealed.get("resonance"),
            }
            try:
                store.append_neural_event(
                    repo,
                    event_type="intel_pulse_seal",
                    entity_id=session_id or repo,
                    payload={
                        "pass_count": pass_count,
                        "intensity": (sealed.get("resonance") or {}).get("intensity"),
                        "brightness": (sealed.get("resonance") or {}).get("brightness"),
                    },
                )
            except Exception:
                pass
            return out
        except Exception as exc:
            out["beat"] = "seal_error"
            out["error"] = f"{type(exc).__name__}: {exc}"
            return out

    # Light doctrine pulse (single rotating claim) — no full ritual
    if home is not None and pulse_every > 0 and pass_count % pulse_every == 0:
        try:
            from .hippocampus import remember

            idx = (pass_count // pulse_every) % len(DOCTRINE_CLAIMS)
            claim = DOCTRINE_CLAIMS[idx]
            result = remember(
                home,
                store,
                repo,
                claim["kind"],
                f"[pulse/{pass_count}] {claim['text']}",
                session_id=session_id,
            )
            out["beat"] = "doctrine"
            out["claim_index"] = idx
            out["recorded"] = bool(result.get("recorded") or result.get("duplicate"))
            try:
                store.append_neural_event(
                    repo,
                    event_type="intel_pulse",
                    entity_id=session_id or repo,
                    payload={
                        "pass_count": pass_count,
                        "claim_index": idx,
                        "intensity": (out.get("resonance") or {}).get("intensity"),
                        "brightness": (out.get("resonance") or {}).get("brightness"),
                    },
                )
            except Exception:
                pass
            return out
        except Exception as exc:
            out["beat"] = "pulse_error"
            out["error"] = f"{type(exc).__name__}: {exc}"
            return out

    out["beat"] = "resonate_only"
    return out
