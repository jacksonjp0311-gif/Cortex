"""v7.0 Resonant Continuity — compose planes under body epoch + phase.

Planes: E evidence · A adaptation · I immunity · C constitutional · W witness
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any

from . import __version__
from .epoch import (
    BodyEpoch,
    ensure_current_epoch,
    observe_current_epoch,
    require_current_epoch,
    verify_body_epoch,
)
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
    """Assemble five-plane continuity snapshot (observe-only; never seals)."""
    obs = observe_current_epoch(store, repo)
    sealed = obs.get("sealed")
    if sealed:
        ep_dict = sealed
    else:
        # Present live computation for reporting only — not sealed
        from .epoch import compute_body_epoch

        ep_dict = compute_body_epoch(store, repo, transition_reason="observe").to_dict()
        ep_dict["sealed"] = False
        ep_dict["observe_only_unsealed"] = True
    ph = current_phase(store, repo)
    evidence = {
        "manifest_hash": ep_dict.get("manifest_hash"),
        "evidence_root_hash": ep_dict.get("evidence_root_hash"),
        "certificate_hash": ep_dict.get("certificate_hash"),
    }
    adaptive = {
        "adaptive_root_hash": ep_dict.get("adaptive_root_hash"),
        "lineage_root_hash": ep_dict.get("lineage_root_hash"),
    }
    immunity: dict[str, Any] = {}
    try:
        from .immunity import immunity_status

        immunity = immunity_status(store, repo)
    except Exception as exc:
        immunity = {"error": f"{type(exc).__name__}:{exc}"}
    constitutional = {
        "constitutional_config_hash": ep_dict.get("constitutional_config_hash"),
        "schema_hash": ep_dict.get("schema_hash"),
        "cortex_version": ep_dict.get("cortex_version"),
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
        body_epoch=ep_dict,
        runtime_phase=ph.to_dict(),
        evidence_plane=evidence,
        adaptive_plane=adaptive,
        immunity_plane=immunity,
        constitutional_plane=constitutional,
        witness_plane=witness,
    )


def continuity_report(store: Any, repo: str) -> dict[str, Any]:
    state = snapshot_continuity(store, repo)
    obs = observe_current_epoch(store, repo)
    ver = {
        "ok": bool(obs.get("verified")),
        "present": bool(obs.get("present")),
        "claimed_epoch_id": obs.get("epoch_id"),
        "live_epoch_id": obs.get("live_epoch_id"),
        "mismatches": list(obs.get("mismatches") or []),
        "observe_only": True,
    }
    if obs.get("present") and obs.get("sealed"):
        try:
            ver = {
                **verify_body_epoch(
                    store, repo, BodyEpoch.from_dict(obs["sealed"])
                ),
                "observe_only": True,
            }
        except Exception:
            pass
    return {
        **state.to_dict(),
        "epoch_verified": ver,
        "phase": phase_report(store, repo),
        "observe_only": True,
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
    from .epoch import BodyEpoch, compare_epochs, observe_current_epoch

    def _side(repo: str) -> tuple[dict[str, Any], BodyEpoch | None]:
        obs = observe_current_epoch(store, repo)
        ep = None
        if obs.get("sealed"):
            ep = BodyEpoch.from_dict(obs["sealed"])
        return obs, ep

    lo, left = _side(left_repo)
    ro, right = _side(right_repo)
    reasons: list[str] = []
    if not lo.get("present") or left is None:
        reasons.append("left_epoch_absent")
    if not ro.get("present") or right is None:
        reasons.append("right_epoch_absent")
    if left is None or right is None:
        return {
            "schema_version": "cortex-epoch-compatible-influence/1.0",
            "allowed": False,
            "left": {"repo": left_repo, "verified": False},
            "right": {"repo": right_repo, "verified": False},
            "reasons_if_denied": reasons,
            "claim_boundary": CLAIM,
        }
    if not lo.get("verified"):
        reasons.append("left_epoch_stale")
    if not ro.get("verified"):
        reasons.append("right_epoch_stale")
    version_ok = left.cortex_version == right.cortex_version
    constitution_ok = left.constitutional_config_hash == right.constitutional_config_hash
    if left.repo != right.repo and left.epoch_id == right.epoch_id:
        reasons.append("cross_repo_epoch_id_collision")
    if not version_ok:
        reasons.append("cortex_version_mismatch")
    if not constitution_ok:
        reasons.append("constitutional_config_mismatch")
    if left.repo == right.repo:
        allowed = bool(lo.get("verified")) and bool(ro.get("verified"))
    else:
        allowed = (
            bool(lo.get("verified"))
            and bool(ro.get("verified"))
            and version_ok
            and constitution_ok
            and left.epoch_id != right.epoch_id
        )
    return {
        "schema_version": "cortex-epoch-compatible-influence/1.0",
        "allowed": allowed and not reasons,
        "left": {
            "repo": left.repo,
            "epoch_id": left.epoch_id,
            "version": left.cortex_version,
            "verified": lo.get("verified"),
        },
        "right": {
            "repo": right.repo,
            "epoch_id": right.epoch_id,
            "version": right.cortex_version,
            "verified": ro.get("verified"),
        },
        "compare": compare_epochs(left, right).to_dict(),
        "reasons_if_denied": [] if allowed and not reasons else reasons,
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
