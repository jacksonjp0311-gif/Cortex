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


def epoch_compatible_influence(
    left_repo: str,
    right_repo: str,
    store: Any,
) -> dict[str, Any]:
    """Whether federated/influence exchange may compose across two hosts.

    Distinct body_epoch_ids are required (identity isolation). Compatible when
    cortex_version and constitutional_config_hash match and both epochs verify.
    Adaptive roots may differ — influence still blocked if constitution/version skew.
    """
    from .epoch import compare_epochs, ensure_current_epoch, verify_body_epoch

    left = ensure_current_epoch(store, left_repo, reason="influence_check")
    right = ensure_current_epoch(store, right_repo, reason="influence_check")
    lv = verify_body_epoch(store, left_repo, left)
    rv = verify_body_epoch(store, right_repo, right)
    version_ok = left.cortex_version == right.cortex_version
    constitution_ok = left.constitutional_config_hash == right.constitutional_config_hash
    reasons: list[str] = []
    if not lv.get("ok"):
        reasons.append("left_epoch_stale")
    if not rv.get("ok"):
        reasons.append("right_epoch_stale")
    if left.repo != right.repo and left.epoch_id == right.epoch_id:
        reasons.append("cross_repo_epoch_id_collision")
    if not version_ok:
        reasons.append("cortex_version_mismatch")
    if not constitution_ok:
        reasons.append("constitutional_config_mismatch")
    if left.repo == right.repo:
        allowed = bool(lv.get("ok")) and bool(rv.get("ok"))
    else:
        allowed = (
            bool(lv.get("ok"))
            and bool(rv.get("ok"))
            and version_ok
            and constitution_ok
            and left.epoch_id != right.epoch_id
        )
    return {
        "schema_version": "cortex-epoch-compatible-influence/1.0",
        "allowed": allowed,
        "left": {
            "repo": left.repo,
            "epoch_id": left.epoch_id,
            "version": left.cortex_version,
            "verified": lv.get("ok"),
        },
        "right": {
            "repo": right.repo,
            "epoch_id": right.epoch_id,
            "version": right.cortex_version,
            "verified": rv.get("ok"),
        },
        "compare": compare_epochs(left, right).to_dict(),
        "reasons_if_denied": [] if allowed else reasons,
        "claim_boundary": CLAIM,
    }


def mesh_continuity_report(store: Any, repos: list[str] | None = None) -> dict[str, Any]:
    """Multi-host continuity rollup for interconnect expansion."""
    if repos is None:
        try:
            repos = [
                str(r["name"])
                for r in store.db.execute(
                    "SELECT name FROM repositories ORDER BY name"
                ).fetchall()
            ]
        except Exception:
            repos = []
    hosts: list[dict[str, Any]] = []
    for repo in repos:
        try:
            st = snapshot_continuity(store, repo)
            hosts.append(
                {
                    "repo": repo,
                    "body_epoch_id": (st.body_epoch or {}).get("epoch_id"),
                    "runtime_phase": (st.runtime_phase or {}).get("phase"),
                    "cortex_version": (st.body_epoch or {}).get("cortex_version"),
                    "constitutional_config_hash": (st.constitutional_plane or {}).get(
                        "constitutional_config_hash"
                    ),
                    "evidence_root_hash": (st.evidence_plane or {}).get("evidence_root_hash"),
                }
            )
        except Exception as exc:
            hosts.append({"repo": repo, "error": f"{type(exc).__name__}: {exc}"})
    versions = {h.get("cortex_version") for h in hosts if h.get("cortex_version")}
    constitutions = {
        h.get("constitutional_config_hash")
        for h in hosts
        if h.get("constitutional_config_hash")
    }
    return {
        "schema_version": "cortex-mesh-continuity/1.0",
        "glyph": GLYPH,
        "host_count": len(hosts),
        "hosts": hosts,
        "version_aligned": len(versions) <= 1,
        "constitution_aligned": len(constitutions) <= 1,
        "claim_boundary": CLAIM,
        "at": time.time(),
    }
