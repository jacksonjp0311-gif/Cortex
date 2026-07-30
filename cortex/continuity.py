"""v7.0 Resonant Continuity — compose planes under body epoch + phase.

Planes: E evidence · A adaptation · I immunity · C constitutional · W witness
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from . import __version__
from .epoch import BodyEpoch, ensure_current_epoch, verify_body_epoch
from .phases import current_phase, phase_report, transition_phase

SCHEMA = "cortex-continuity/1.0"
GLYPH = "∿"

CLAIM = (
    "Resonant Continuity composes evidence, adaptation, immunity, constitutional "
    "control, and witness under a body epoch and legal runtime phase. "
    "Not consciousness. Not host mutation authority."
)


@dataclass
class CortexState:
    repo: str
    body_epoch: dict[str, Any]
    runtime_phase: dict[str, Any]
    evidence_plane: dict[str, Any] = field(default_factory=dict)
    adaptive_plane: dict[str, Any] = field(default_factory=dict)
    immunity_plane: dict[str, Any] = field(default_factory=dict)
    constitutional_plane: dict[str, Any] = field(default_factory=dict)
    witness_plane: dict[str, Any] = field(default_factory=dict)
    forbidden_flows: list[str] = field(
        default_factory=lambda: [
            "A_must_not_silently_rewrite_E",
            "A_must_not_manufacture_authority_in_C",
            "A_must_not_inspect_hidden_W",
            "I_must_not_mutate_A_without_C",
            "W_must_not_certify_different_epoch_than_promoted",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["schema_version"] = SCHEMA
        d["glyph"] = GLYPH
        d["version"] = __version__
        d["claim_boundary"] = CLAIM
        return d


def snapshot_continuity(store: Any, repo: str) -> CortexState:
    """Assemble five-plane continuity snapshot for a repository."""
    ep = ensure_current_epoch(store, repo, reason="continuity_snapshot")
    ph = current_phase(store, repo)
    evidence = {
        "manifest_hash": ep.manifest_hash,
        "evidence_root_hash": ep.evidence_root_hash,
        "certificate_hash": ep.certificate_hash,
    }
    adaptive = {
        "adaptive_root_hash": ep.adaptive_root_hash,
        "lineage_root_hash": ep.lineage_root_hash,
    }
    immunity: dict[str, Any] = {}
    try:
        from .immunity import immunity_status

        immunity = immunity_status(store, repo)
    except Exception as exc:
        immunity = {"error": f"{type(exc).__name__}:{exc}"}
    constitutional = {
        "constitutional_config_hash": ep.constitutional_config_hash,
        "schema_hash": ep.schema_hash,
        "cortex_version": ep.cortex_version,
    }
    witness: dict[str, Any] = {}
    try:
        row = store.db.execute(
            "SELECT witness_id, commitment_root, created_at, revealed_at FROM witness_commitments ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        witness = {
            "recent": [dict(r) for r in row],
            "plane": "W",
        }
    except Exception:
        witness = {"recent": [], "plane": "W"}

    return CortexState(
        repo=repo,
        body_epoch=ep.to_dict(),
        runtime_phase=ph.to_dict(),
        evidence_plane=evidence,
        adaptive_plane=adaptive,
        immunity_plane=immunity,
        constitutional_plane=constitutional,
        witness_plane=witness,
    )


def continuity_report(store: Any, repo: str) -> dict[str, Any]:
    state = snapshot_continuity(store, repo)
    ver = verify_body_epoch(store, repo, BodyEpoch.from_dict(state.body_epoch))
    return {
        **state.to_dict(),
        "epoch_verified": ver,
        "phase": phase_report(store, repo),
        "at": time.time(),
    }


def enter_phase(store: Any, repo: str, phase: str, *, reason: str = "") -> dict[str, Any]:
    """Legal phase entry under current epoch."""
    ensure_current_epoch(store, repo, reason=f"enter_phase:{phase}")
    return transition_phase(store, repo, phase, reason=reason)
