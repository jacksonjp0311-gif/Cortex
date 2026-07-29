"""Distill operational intelligence into the durable body.

Reads the living lattice (mesh, kernels, ranker, causal, immune), folds it with
fixed doctrine claims, and seals via ritual — same substrate, recommend-only.
Glyphic medium ☰; never mutation authority.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import __version__
from .governor import Governor
from .interconnect import mesh_dashboard
from .kernels import kernels_status
from .session_ritual import run_session_ritual

GLYPH = "☰"
SCHEMA = "cortex-distill-intel/1.0"

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
]


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
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "version": __version__,
        "observation": obs,
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
