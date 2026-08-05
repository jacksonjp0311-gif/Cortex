"""Turn-bound interconnect frames — one synchronized heartbeat for one turn.

v8.4.3 binds sensing surfaces, circulation identity, and measurement digests
into a single InterconnectFrameReceipt.  Panels may still be collected
independently; a frame proves they answer the same operational event.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from typing import Any

from . import __version__

SCHEMA = "cortex-interconnect-frame/1.0"
VERSION = "8.4.3"
GLYPH = "⧉⤒"
CLAIM_BOUNDARY = (
    "An interconnect frame is a turn-bound compatibility envelope. It does not "
    "grant authority, mutate host source, or claim consciousness. It only proves "
    "which digests were co-present for one circulation turn."
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=str,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _surface_digest(store: Any, key: str) -> str | None:
    payload = store.get_setting(key, None)
    if not payload:
        return None
    return _sha(payload)[:32]


def capture_interconnect_frame(
    store: Any,
    repo: str,
    *,
    session_id: str,
    turn_id: int,
    body_epoch_id: str,
    repository_id: str = "",
    case_id: str | None = None,
    invocation_id: str | None = None,
    prior_outcome_hash: str | None = None,
    prior_frame_hash: str | None = None,
    symbiosis_chain_tip: str | None = None,
) -> dict[str, Any]:
    """Capture one turn-bound interconnect frame from live advisory surfaces."""
    if not repository_id:
        repository = store.repo(repo)
        repository_id = str(repository["repository_id"] or "") if repository else ""

    digests = {
        "measured_state_digest": _surface_digest(store, f"measured_event_latest:{repo}"),
        "self_sensing_digest": _surface_digest(store, f"self_sensing_latest:{repo}"),
        "binding_digest": _surface_digest(store, f"binding_field_latest:{repo}"),
        "resonance_digest": _surface_digest(store, f"resonance_sweep_latest:{repo}"),
        "information_interlock_digest": _surface_digest(
            store, f"interlock_shadow_latest:{repo}"
        ),
        "ostt_digest": _surface_digest(store, f"ostt_residual_latest:{repo}"),
        "source_admission_digest": _surface_digest(
            store, f"source_admission_latest:{repo}"
        ),
        "geometric_echo_digest": _surface_digest(
            store, f"geometric_echo_latest:{repo}"
        ),
    }
    try:
        from .epoch import observe_current_epoch

        epoch = observe_current_epoch(store, repo)
    except Exception:
        epoch = {}
    continuity_digest = _sha(
        {
            "body_epoch_id": body_epoch_id,
            "epoch_verified": bool(epoch.get("verified")),
            "live_epoch_id": epoch.get("live_epoch_id") or epoch.get("epoch_id"),
        }
    )[:32]

    measured = store.get_setting(f"measured_event_latest:{repo}", {}) or {}
    coordinate_schema_digest = str(
        (measured or {}).get("coordinate_schema_digest") or ""
    )
    measurement_cohort_id = str(
        (measured or {}).get("measurement_cohort_id")
        or store.get_setting(f"measurement_cohort:{repo}", "")
        or ""
    )

    compatibility = {
        "repo_bound": bool(repo and repository_id),
        "epoch_claimed": bool(body_epoch_id),
        "epoch_matches_live": bool(
            body_epoch_id
            and body_epoch_id
            == str(epoch.get("epoch_id") or epoch.get("live_epoch_id") or "")
        )
        if epoch.get("verified")
        else False,
        "turn_nonnegative": int(turn_id) >= 0,
        "session_present": bool(session_id),
        "measured_surface_present": digests["measured_state_digest"] is not None,
    }
    compatible = all(
        compatibility[key]
        for key in (
            "repo_bound",
            "epoch_claimed",
            "turn_nonnegative",
            "session_present",
        )
    )

    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "interconnect_frame",
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "turn_id": int(turn_id),
        "case_id": case_id or f"case_{session_id}_{turn_id}",
        "invocation_id": invocation_id or f"inv_{session_id}",
        "body_epoch_id": body_epoch_id,
        "measurement_cohort_id": measurement_cohort_id,
        "coordinate_schema_digest": coordinate_schema_digest,
        "continuity_digest": continuity_digest,
        "prior_outcome_hash": prior_outcome_hash,
        "prior_frame_hash": prior_frame_hash,
        "symbiosis_chain_tip": symbiosis_chain_tip,
        **digests,
        "compatibility_results": compatibility,
        "compatible": compatible,
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    frame_id = "ifr_" + _sha(material)[:24]
    receipt_hash = _sha({**material, "frame_id": frame_id})
    return {
        **material,
        "frame_id": frame_id,
        "receipt_hash": receipt_hash,
        "event_id": "evt_" + _sha(
            {
                "session_id": session_id,
                "turn_id": int(turn_id),
                "kind": "interconnect_frame",
                "body_epoch_id": body_epoch_id,
            }
        )[:24],
        "captured_at": time.time(),
    }


def frame_compatible_with_proposal(
    frame: Mapping[str, Any],
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Prove a measurement frame and proposal share the same operational identity."""
    checks = {
        "repo": str(frame.get("repo") or "") == str(proposal.get("repo") or ""),
        "repository_id": str(frame.get("repository_id") or "")
        == str(proposal.get("repository_id") or ""),
        "session_id": str(frame.get("session_id") or "")
        == str(proposal.get("session_id") or ""),
        "turn_id": int(frame.get("turn_id") or -1)
        == int(proposal.get("turn_id") or -2),
        "body_epoch_id": str(frame.get("body_epoch_id") or "")
        == str(proposal.get("body_epoch_id") or ""),
        "case_id": (
            not proposal.get("case_id")
            or str(frame.get("case_id") or "") == str(proposal.get("case_id") or "")
        ),
        "invocation_id": (
            not proposal.get("invocation_id")
            or str(frame.get("invocation_id") or "")
            == str(proposal.get("invocation_id") or "")
        ),
    }
    return {
        "compatible": all(checks.values()),
        "checks": checks,
        "frame_hash": frame.get("receipt_hash"),
        "proposal_hash": proposal.get("receipt_hash"),
    }


def readiness_panel(
    *,
    mesh_green_constitutional: bool,
    continuity: Mapping[str, Any] | None = None,
    symbiosis: Mapping[str, Any] | None = None,
    self_sensing: Mapping[str, Any] | None = None,
    binding: Mapping[str, Any] | None = None,
    resonance: Mapping[str, Any] | None = None,
    interlock: Mapping[str, Any] | None = None,
    ostt: Mapping[str, Any] | None = None,
    frame: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Split readiness planes — one plane never compensates for another."""
    continuity = continuity or {}
    symbiosis = symbiosis or {}
    self_sensing = self_sensing or {}
    binding = binding or {}
    resonance = resonance or {}
    interlock = interlock or {}
    ostt = ostt or {}
    frame = frame or {}

    constitutional_ready = bool(mesh_green_constitutional)
    continuity_ready = bool(
        continuity.get("epoch_verified") is True
        and continuity.get("phase_bound") is not False
        and not continuity.get("error")
    )
    measurement_ready = bool(
        frame.get("compatible")
        and frame.get("measured_state_digest")
    ) or bool(symbiosis.get("ledger", {}).get("valid") is True and frame.get("measured_state_digest"))
    circulation_ready = bool(
        (symbiosis.get("status") or "cold") not in {"cold", None}
        and (symbiosis.get("ledger") or {}).get("valid") is not False
    )
    sensing = str(self_sensing.get("classification") or self_sensing.get("status") or "").upper()
    bind = str(binding.get("classification") or "").upper()
    temporal_ready = bool(
        sensing
        and sensing not in {"STRESSED", "UNBOUND"}
        and bind not in {"DRIFT_REGIME"}
        and str(resonance.get("status") or "") != "no_stable_peak"
    )
    distillation_ready = bool(
        interlock.get("data_ready") is True
        or str(ostt.get("status") or "") in {"conformance_measured", "measured"}
    )

    planes = {
        "constitutional_ready": constitutional_ready,
        "continuity_ready": continuity_ready,
        "measurement_ready": bool(measurement_ready),
        "circulation_ready": circulation_ready,
        "temporal_ready": temporal_ready,
        "distillation_ready": distillation_ready,
    }
    # min-like overall: false if any plane false; do not invent unknown→true
    overall = all(planes.values())
    return {
        "schema_version": "cortex-interconnect-readiness/1.0",
        **planes,
        "overall_ready": overall,
        "mesh_green_legacy": constitutional_ready,
        "composition": "min(planes) — no plane compensates for another",
        "advisory_only": True,
        "policy_effect": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "GLYPH",
    "SCHEMA",
    "VERSION",
    "capture_interconnect_frame",
    "frame_compatible_with_proposal",
    "readiness_panel",
]
