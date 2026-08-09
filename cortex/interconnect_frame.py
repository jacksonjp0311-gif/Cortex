"""Turn-bound interconnect frames and verified frame trajectories (v8.4.4).

v8.4.3 synchronized each turn with a frame of digests.
v8.4.4 adds atomic snapshot capture, tri-state validity planes, transitions
between frames, trajectory ledgers, freshness, and context deltas.

Logical claim: frames prove co-presence under one DB snapshot when available.
They do not grant execution or learning authority.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA = "cortex-interconnect-frame/1.1"
TRANSITION_SCHEMA = "cortex-interconnect-transition/1.0"
DELTA_SCHEMA = "cortex-context-delta/1.0"
VERSION = "8.6.0"
GLYPH = "⧉⤒"
CLAIM_BOUNDARY = (
    "Interconnect frames and transitions are turn-bound compatibility and "
    "trajectory telemetry. They do not grant authority, mutate host source, "
    "prove consciousness, or authorize learning. structural_valid ≠ "
    "measurement_complete ≠ temporally_coherent."
)

GATE_PASS = "pass"
GATE_FAIL = "fail"
GATE_UNKNOWN = "unknown"
GATE_RANK = {GATE_FAIL: 0, GATE_UNKNOWN: 1, GATE_PASS: 2}

# Maximum acceptable age (ms) by surface family for freshness_state.
FRESHNESS_LIMITS_MS: dict[str, int] = {
    "measured_state": 0,  # must be current turn / epoch-bound when present
    "self_sensing": 300_000,
    "binding": 300_000,
    "resonance": 600_000,
    "information_interlock": 600_000,
    "ostt": 3_600_000,
    "source_admission": 600_000,
    "geometric_echo": 600_000,
}

SURFACE_KEYS = (
    ("measured_state", "measured_event_latest"),
    ("self_sensing", "self_sensing_latest"),
    ("binding", "binding_field_latest"),
    ("resonance", "resonance_sweep_latest"),
    ("information_interlock", "interlock_shadow_latest"),
    ("ostt", "ostt_residual_latest"),
    ("source_admission", "source_admission_latest"),
    ("geometric_echo", "geometric_echo_latest"),
)

TRAJECTORY_CLASSES = frozenset(
    {
        "stable_continuation",
        "evidence_gain",
        "measurement_loss",
        "temporal_drift",
        "constitutional_block",
        "symbiotic_progress",
        "symbiotic_regression",
        "distillation_ready",
        "distillation_blocked",
        "schema_transition",
        "epoch_transition",
        "unknown_transition",
    }
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


def _min_gate(states: Sequence[str]) -> str:
    if not states:
        return GATE_UNKNOWN
    return min(states, key=lambda s: GATE_RANK.get(s, 1))


def _surface_payload_meta(payload: Any, *, now: float, limit_ms: int) -> dict[str, Any]:
    if not payload:
        return {
            "present": False,
            "digest": None,
            "schema_version": None,
            "captured_at": None,
            "source_event_id": None,
            "body_epoch_id": None,
            "measurement_cohort_id": None,
            "freshness_ms": None,
            "freshness_state": GATE_UNKNOWN,
            "status": "absent",
        }
    captured = None
    if isinstance(payload, Mapping):
        for key in (
            "captured_at",
            "measured_at",
            "issued_at",
            "created_at",
            "ts",
            "at",
        ):
            if payload.get(key) is not None:
                try:
                    captured = float(payload[key])
                    break
                except (TypeError, ValueError):
                    continue
    freshness_ms = None
    if captured is not None:
        freshness_ms = max(0.0, (now - captured) * 1000.0)
    if not payload:
        freshness_state = GATE_UNKNOWN
        status = "absent"
    elif freshness_ms is None:
        freshness_state = GATE_UNKNOWN
        status = "present_age_unknown"
    elif limit_ms <= 0:
        # measured_state: presence is required; age alone is advisory
        freshness_state = GATE_PASS
        status = "present"
    elif freshness_ms <= float(limit_ms):
        freshness_state = GATE_PASS
        status = "present"
    else:
        freshness_state = GATE_FAIL
        status = "present_but_stale"
    schema_version = None
    source_event_id = None
    body_epoch_id = None
    measurement_cohort_id = None
    if isinstance(payload, Mapping):
        schema_version = payload.get("schema_version") or payload.get("version")
        source_event_id = (
            payload.get("event_id")
            or payload.get("receipt_hash")
            or payload.get("activation_id")
        )
        body_epoch_id = payload.get("body_epoch_id") or payload.get("epoch_id")
        measurement_cohort_id = payload.get("measurement_cohort_id") or payload.get(
            "cohort_id"
        )
    return {
        "present": True,
        "digest": _sha(payload)[:32],
        "schema_version": schema_version,
        "captured_at": captured,
        "source_event_id": source_event_id,
        "body_epoch_id": body_epoch_id,
        "measurement_cohort_id": measurement_cohort_id,
        "freshness_ms": round(freshness_ms, 3) if freshness_ms is not None else None,
        "freshness_state": freshness_state,
        "status": status,
    }


def _read_surfaces_snapshot(store: Any, repo: str) -> dict[str, Any]:
    """Read all interconnect surfaces under one BEGIN IMMEDIATE snapshot when possible."""
    now = time.time()
    snapshot_id = "snap_" + uuid.uuid4().hex[:16]
    started = time.time()
    surfaces: dict[str, Any] = {}
    wal_frame = None
    atomic = False
    try:
        # Prefer a transactional snapshot so concurrent writers cannot interleave
        # between surface reads.
        with store.transaction() as conn:
            atomic = True
            try:
                row = conn.execute("PRAGMA wal_checkpoint(PASSIVE)").fetchone()
                if row is not None:
                    wal_frame = {
                        "busy": row[0] if len(row) > 0 else None,
                        "log": row[1] if len(row) > 1 else None,
                        "checkpointed": row[2] if len(row) > 2 else None,
                    }
            except Exception:
                wal_frame = None
            for name, prefix in SURFACE_KEYS:
                key = f"{prefix}:{repo}"
                try:
                    row = conn.execute(
                        "SELECT value FROM settings WHERE key=?", (key,)
                    ).fetchone()
                    if row is None:
                        payload = None
                    else:
                        raw = row["value"] if hasattr(row, "keys") else row[0]
                        payload = json.loads(raw) if isinstance(raw, str) else raw
                except Exception:
                    payload = store.get_setting(key, None)
                surfaces[name] = _surface_payload_meta(
                    payload, now=now, limit_ms=FRESHNESS_LIMITS_MS.get(name, 600_000)
                )
    except Exception:
        atomic = False
        for name, prefix in SURFACE_KEYS:
            key = f"{prefix}:{repo}"
            payload = store.get_setting(key, None)
            surfaces[name] = _surface_payload_meta(
                payload, now=now, limit_ms=FRESHNESS_LIMITS_MS.get(name, 600_000)
            )
    completed = time.time()
    return {
        "snapshot_transaction_id": snapshot_id,
        "snapshot_started_at": started,
        "snapshot_completed_at": completed,
        "atomic_snapshot": atomic,
        "database_wal_frame": wal_frame,
        "surfaces": surfaces,
    }


def _frame_validity_planes(
    *,
    repo: str,
    repository_id: str,
    session_id: str,
    turn_id: int,
    body_epoch_id: str,
    epoch: Mapping[str, Any],
    surfaces: Mapping[str, Any],
    coordinate_schema_digest: str,
    measurement_cohort_id: str,
    symbiosis_chain_tip: str | None,
) -> dict[str, str]:
    structural = (
        GATE_PASS
        if repo and repository_id and session_id and int(turn_id) >= 0 and body_epoch_id
        else GATE_FAIL
        if not repo or not session_id
        else GATE_UNKNOWN
    )
    # Prefer live_epoch_id: a claim that diverges from live fails even when no
    # sealed epoch is present (present=False still carries live_epoch_id).
    live = str(epoch.get("live_epoch_id") or epoch.get("epoch_id") or "")
    if not body_epoch_id:
        epoch_state = GATE_UNKNOWN
    elif live and body_epoch_id != live:
        epoch_state = GATE_FAIL
    elif (
        bool(epoch.get("present"))
        and bool(epoch.get("verified"))
        and body_epoch_id == live
    ):
        epoch_state = GATE_PASS
    else:
        # Sealed absent, unverified, or live unknown — do not invent pass.
        epoch_state = GATE_UNKNOWN

    measured = surfaces.get("measured_state") or {}
    if not measured.get("present"):
        measurement_state = GATE_UNKNOWN
        schema_state = GATE_UNKNOWN
        cohort_state = GATE_UNKNOWN
    else:
        measurement_state = GATE_PASS
        schema_state = (
            GATE_PASS if coordinate_schema_digest else GATE_UNKNOWN
        )
        cohort_state = GATE_PASS if measurement_cohort_id else GATE_UNKNOWN

    freshness_states = [
        str((surfaces.get(name) or {}).get("freshness_state") or GATE_UNKNOWN)
        for name, _ in SURFACE_KEYS
        if (surfaces.get(name) or {}).get("present")
    ]
    freshness_state = _min_gate(freshness_states) if freshness_states else GATE_UNKNOWN

    if symbiosis_chain_tip:
        chain_state = GATE_PASS
    else:
        chain_state = GATE_UNKNOWN if int(turn_id) == 0 else GATE_UNKNOWN

    overall = _min_gate(
        [
            structural,
            epoch_state,
            schema_state,
            cohort_state,
            freshness_state,
            measurement_state,
            chain_state,
        ]
    )
    return {
        "structural_state": structural,
        "epoch_state": epoch_state,
        "schema_state": schema_state,
        "cohort_state": cohort_state,
        "freshness_state": freshness_state,
        "measurement_state": measurement_state,
        "chain_state": chain_state,
        "overall_state": overall,
    }


def capture_atomic_interconnect_frame(
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
    """Capture one frame under a single DB snapshot when the store allows it."""
    if not repository_id:
        repository = store.repo(repo)
        repository_id = str(repository["repository_id"] or "") if repository else ""

    snapshot = _read_surfaces_snapshot(store, repo)
    surfaces = snapshot["surfaces"]
    try:
        from .epoch import observe_current_epoch

        epoch = observe_current_epoch(store, repo)
    except Exception:
        epoch = {}

    measured_payload = store.get_setting(f"measured_event_latest:{repo}", {}) or {}
    coordinate_schema_digest = str(
        (measured_payload or {}).get("coordinate_schema_digest") or ""
    )
    measurement_cohort_id = str(
        (measured_payload or {}).get("measurement_cohort_id")
        or store.get_setting(f"measurement_cohort:{repo}", "")
        or ""
    )
    continuity_digest = _sha(
        {
            "body_epoch_id": body_epoch_id,
            "epoch_verified": bool(epoch.get("verified")),
            "live_epoch_id": epoch.get("live_epoch_id") or epoch.get("epoch_id"),
        }
    )[:32]

    validity = _frame_validity_planes(
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        turn_id=int(turn_id),
        body_epoch_id=body_epoch_id,
        epoch=epoch,
        surfaces=surfaces,
        coordinate_schema_digest=coordinate_schema_digest,
        measurement_cohort_id=measurement_cohort_id,
        symbiosis_chain_tip=symbiosis_chain_tip,
    )

    # Legacy fields for 8.4.3 callers
    digests = {
        f"{name}_digest": (surfaces.get(name) or {}).get("digest")
        for name, _ in SURFACE_KEYS
    }
    digests["measured_state_digest"] = digests.pop("measured_state_digest", None)
    # normalize naming used previously
    digests = {
        "measured_state_digest": (surfaces.get("measured_state") or {}).get("digest"),
        "self_sensing_digest": (surfaces.get("self_sensing") or {}).get("digest"),
        "binding_digest": (surfaces.get("binding") or {}).get("digest"),
        "resonance_digest": (surfaces.get("resonance") or {}).get("digest"),
        "information_interlock_digest": (
            surfaces.get("information_interlock") or {}
        ).get("digest"),
        "ostt_digest": (surfaces.get("ostt") or {}).get("digest"),
        "source_admission_digest": (surfaces.get("source_admission") or {}).get(
            "digest"
        ),
        "geometric_echo_digest": (surfaces.get("geometric_echo") or {}).get("digest"),
    }

    compatibility_results = {
        "repo_bound": bool(repo and repository_id),
        "epoch_claimed": bool(body_epoch_id),
        "epoch_matches_live": validity["epoch_state"] == GATE_PASS,
        "turn_nonnegative": int(turn_id) >= 0,
        "session_present": bool(session_id),
        "measured_surface_present": bool(
            (surfaces.get("measured_state") or {}).get("present")
        ),
        "schema_present": bool(coordinate_schema_digest),
        "cohort_present": bool(measurement_cohort_id),
        "chain_tip_present": bool(symbiosis_chain_tip),
        "atomic_snapshot": bool(snapshot.get("atomic_snapshot")),
    }
    # Structural validity: identity fields only
    structurally_valid = all(
        compatibility_results[k]
        for k in (
            "repo_bound",
            "epoch_claimed",
            "turn_nonnegative",
            "session_present",
        )
    )
    # Measurement complete requires a typed measured surface with both
    # coordinate-schema and cohort bindings.  Presence alone is not evidence.
    measurement_complete = validity["measurement_state"] == GATE_PASS and (
        validity["schema_state"] == GATE_PASS
        and validity["cohort_state"] == GATE_PASS
    )
    temporally_coherent = (
        validity["epoch_state"] == GATE_PASS
        and validity["freshness_state"] != GATE_FAIL
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
        "surfaces": surfaces,
        "snapshot_transaction_id": snapshot["snapshot_transaction_id"],
        "snapshot_started_at": snapshot["snapshot_started_at"],
        "snapshot_completed_at": snapshot["snapshot_completed_at"],
        "atomic_snapshot": snapshot["atomic_snapshot"],
        "database_wal_frame": snapshot.get("database_wal_frame"),
        "validity": validity,
        "structurally_valid": structurally_valid,
        "measurement_complete": measurement_complete,
        "temporally_coherent": temporally_coherent,
        "compatible": structurally_valid,  # legacy name = structural only
        "compatibility_results": compatibility_results,
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    frame_id = "ifr_" + _sha(material)[:24]
    event_id = "evt_" + _sha(
        {
            "session_id": session_id,
            "turn_id": int(turn_id),
            "kind": "interconnect_frame",
            "body_epoch_id": body_epoch_id,
            "snapshot": snapshot["snapshot_transaction_id"],
        }
    )[:24]
    receipt_hash = _sha({**material, "frame_id": frame_id, "event_id": event_id})
    return {
        **material,
        "frame_id": frame_id,
        "event_id": event_id,
        "receipt_hash": receipt_hash,
        "captured_at": time.time(),
    }


# Backward-compatible alias
def capture_interconnect_frame(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return capture_atomic_interconnect_frame(*args, **kwargs)


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
        "frame_structurally_valid": bool(
            frame.get("structurally_valid", frame.get("compatible"))
        ),
        "epoch_state_not_fail": str(
            (frame.get("validity") or {}).get("epoch_state") or GATE_UNKNOWN
        )
        != GATE_FAIL,
    }
    return {
        "compatible": all(checks.values()),
        "checks": checks,
        "frame_hash": frame.get("receipt_hash"),
        "proposal_hash": proposal.get("receipt_hash"),
        "frame_overall_state": (frame.get("validity") or {}).get("overall_state"),
    }


def _digest_map(frame: Mapping[str, Any]) -> dict[str, str | None]:
    keys = (
        "measured_state_digest",
        "self_sensing_digest",
        "binding_digest",
        "resonance_digest",
        "information_interlock_digest",
        "ostt_digest",
        "source_admission_digest",
        "geometric_echo_digest",
        "continuity_digest",
    )
    return {key: frame.get(key) for key in keys}


def classify_transition(
    prior: Mapping[str, Any],
    nxt: Mapping[str, Any],
    *,
    outcome: Mapping[str, Any] | None = None,
) -> str:
    """Deterministic trajectory class labels for analysis only."""
    if str(prior.get("body_epoch_id") or "") != str(nxt.get("body_epoch_id") or ""):
        return "epoch_transition"
    if str(prior.get("coordinate_schema_digest") or "") != str(
        nxt.get("coordinate_schema_digest") or ""
    ):
        return "schema_transition"
    prior_v = dict(prior.get("validity") or {})
    next_v = dict(nxt.get("validity") or {})
    if next_v.get("epoch_state") == GATE_FAIL:
        return "constitutional_block"
    prior_d = _digest_map(prior)
    next_d = _digest_map(nxt)
    changed = [k for k in prior_d if prior_d.get(k) != next_d.get(k)]
    lost = [
        k
        for k in prior_d
        if prior_d.get(k) and not next_d.get(k)
    ]
    gained = [
        k
        for k in next_d
        if next_d.get(k) and not prior_d.get(k)
    ]
    if lost and not gained:
        return "measurement_loss"
    if gained and not lost:
        return "evidence_gain"
    prior_ready = prior_v.get("overall_state")
    next_ready = next_v.get("overall_state")
    if prior_ready == GATE_PASS and next_ready != GATE_PASS:
        return "symbiotic_regression"
    if prior_ready != GATE_PASS and next_ready == GATE_PASS:
        return "symbiotic_progress"
    if next_v.get("freshness_state") == GATE_FAIL:
        return "temporal_drift"
    if outcome and outcome.get("witnessed") and outcome.get("success") is True:
        return "distillation_ready"
    if outcome and outcome.get("witnessed") is False:
        return "distillation_blocked"
    if not changed:
        return "stable_continuation"
    return "unknown_transition"


def build_interconnect_transition(
    *,
    prior_frame: Mapping[str, Any],
    next_frame: Mapping[str, Any],
    proposal: Mapping[str, Any] | None = None,
    evaluation: Mapping[str, Any] | None = None,
    joint_action: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build InterconnectTransitionReceipt binding F_k → F_{k+1} with turn artifacts."""
    prior_d = _digest_map(prior_frame)
    next_d = _digest_map(next_frame)
    changed = {
        key: {"prior": prior_d.get(key), "next": next_d.get(key)}
        for key in prior_d
        if prior_d.get(key) != next_d.get(key)
    }
    # Temporal adjacency only — not full causal credit. Artifacts P_k/A_k/O_k
    # belong to the turn that produced the step from F_k → F_{k+1}, so identity
    # is checked against the prior frame's session/repo/turn (not F_{k+1}'s turn).
    def _identity_bound(artifact: Mapping[str, Any] | None) -> bool:
        if not artifact or not artifact.get("receipt_hash"):
            return False
        anchor = prior_frame if prior_frame.get("session_id") else next_frame
        checks = []
        if artifact.get("session_id") is not None:
            checks.append(
                str(artifact.get("session_id") or "")
                == str(anchor.get("session_id") or next_frame.get("session_id") or "")
            )
        if artifact.get("repo") is not None:
            checks.append(
                str(artifact.get("repo") or "")
                == str(anchor.get("repo") or next_frame.get("repo") or "")
            )
        if artifact.get("turn_id") is not None:
            prior_turn = int(prior_frame.get("turn_id") or -3)
            next_turn = int(next_frame.get("turn_id") or -2)
            art_turn = int(artifact.get("turn_id") or -1)
            # Accept the producing turn (prior) or the arrival turn (next).
            checks.append(art_turn == prior_turn or art_turn == next_turn)
        # If the artifact carries no identity fields, refuse outcome credit.
        return bool(checks) and all(checks)

    outcome_bound = _identity_bound(outcome)
    action_bound = _identity_bound(joint_action)
    proposal_bound = _identity_bound(proposal)
    if outcome_bound:
        causal_status = "outcome_bound"
    elif action_bound or proposal_bound:
        causal_status = "temporally_bound"
    else:
        causal_status = "unmeasured"
    if (
        prior_frame.get("coordinate_schema_digest")
        and next_frame.get("coordinate_schema_digest")
        and prior_frame.get("coordinate_schema_digest")
        == next_frame.get("coordinate_schema_digest")
        and changed
        and causal_status == "outcome_bound"
    ):
        causal_status = "comparison_supported"

    # Only record hashes for identity-bound artifacts so unrelated outcomes
    # cannot appear on the transition receipt.
    outcome_hash = (outcome or {}).get("receipt_hash") if outcome_bound else None
    transition_class = classify_transition(
        prior_frame,
        next_frame,
        outcome=outcome if outcome_bound else None,
    )

    material = {
        "schema_version": TRANSITION_SCHEMA,
        "version": VERSION,
        "kind": "interconnect_transition",
        "repo": next_frame.get("repo"),
        "repository_id": next_frame.get("repository_id"),
        "session_id": next_frame.get("session_id"),
        "turn_id": next_frame.get("turn_id"),
        "prior_frame_hash": prior_frame.get("receipt_hash"),
        "next_frame_hash": next_frame.get("receipt_hash"),
        "proposal_hash": (
            (proposal or {}).get("receipt_hash") if proposal_bound else None
        ),
        "evaluation_hash": (evaluation or {}).get("receipt_hash"),
        "joint_action_hash": (
            (joint_action or {}).get("receipt_hash") if action_bound else None
        ),
        "outcome_hash": outcome_hash,
        "changed_surface_mask": sorted(changed),
        "transition_vector": changed,
        "transition_class": transition_class,
        "causal_status": causal_status,
        "witness_ids": [
            wid
            for wid in (
                ((outcome or {}).get("witness") or {}).get("witness_id"),
            )
            if wid and outcome_bound
        ],
        "validity": {
            "prior_overall": (prior_frame.get("validity") or {}).get("overall_state"),
            "next_overall": (next_frame.get("validity") or {}).get("overall_state"),
        },
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    event_id = "evt_" + _sha(
        {
            "prior": material["prior_frame_hash"],
            "next": material["next_frame_hash"],
            "kind": "interconnect_transition",
        }
    )[:24]
    receipt_hash = _sha({**material, "event_id": event_id})
    return {
        **material,
        "event_id": event_id,
        "receipt_hash": receipt_hash,
        "created_at": time.time(),
    }


def build_context_delta(
    *,
    prior_context: Mapping[str, Any] | None,
    next_context: Mapping[str, Any],
    prior_frame: Mapping[str, Any] | None = None,
    next_frame: Mapping[str, Any] | None = None,
    outcome: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspectable ΔC_k between successive context projections."""
    prior_context = prior_context or {}
    prior_frame = prior_frame or {}
    next_frame = next_frame or {}
    prior_pred = dict(prior_context.get("predictions") or {})
    next_pred = dict(next_context.get("predictions") or {})
    prior_unresolved = set(prior_context.get("unresolved_contradictions") or ())
    next_unresolved = set(next_context.get("unresolved_contradictions") or ())
    prior_d = _digest_map(prior_frame) if prior_frame else {}
    next_d = _digest_map(next_frame) if next_frame else {}
    new_information = sorted(
        k for k in next_d if next_d.get(k) and prior_d.get(k) != next_d.get(k)
    )
    invalidated = sorted(
        k for k in prior_d if prior_d.get(k) and not next_d.get(k)
    )
    material = {
        "schema_version": DELTA_SCHEMA,
        "version": VERSION,
        "kind": "cortex_context_delta",
        "repo": next_context.get("repo"),
        "session_id": next_context.get("session_id"),
        "turn_id": next_context.get("turn_id"),
        "prior_context_hash": prior_context.get("receipt_hash"),
        "next_context_hash": next_context.get("receipt_hash"),
        "new_information": new_information,
        "invalidated_information": invalidated,
        "persistent_constraints": list(
            next_context.get("constitutional_restrictions") or ()
        ),
        "new_failures": sorted(next_unresolved - prior_unresolved),
        "resolved_questions": sorted(prior_unresolved - next_unresolved),
        "unresolved_questions": sorted(next_unresolved),
        "evidence_priority_changes": {
            "prior_predictions": prior_pred,
            "next_predictions": next_pred,
        },
        "outcome_hash": (outcome or {}).get("receipt_hash"),
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    receipt_hash = _sha(material)
    return {**material, "receipt_hash": receipt_hash, "created_at": time.time()}


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
    """Non-compensatory readiness with tri-state planes."""
    continuity = continuity or {}
    symbiosis = symbiosis or {}
    self_sensing = self_sensing or {}
    binding = binding or {}
    resonance = resonance or {}
    interlock = interlock or {}
    ostt = ostt or {}
    frame = frame or {}
    validity = dict(frame.get("validity") or {})

    def _bool_plane(value: bool | None, *, unknown_if_none: bool = True) -> str:
        if value is True:
            return GATE_PASS
        if value is False:
            return GATE_FAIL
        return GATE_UNKNOWN if unknown_if_none else GATE_FAIL

    constitutional = GATE_PASS if mesh_green_constitutional else GATE_FAIL
    if continuity.get("error"):
        continuity_state = GATE_FAIL
    elif continuity.get("epoch_verified") is True:
        continuity_state = GATE_PASS
    elif continuity.get("epoch_verified") is False:
        continuity_state = GATE_FAIL
    else:
        continuity_state = GATE_UNKNOWN

    conformance = ostt.get("residual_evidence") or {}
    activation_operator = (conformance.get("operator_statuses") or {}).get(
        "activation_observation"
    ) or {}
    verified_activation = False
    for receipt in conformance.get("receipts") or []:
        if str(receipt.get("operator_id") or "") != "activation_observation":
            continue
        verification = receipt.get("canonical_verification") or {}
        verified_activation = bool(
            activation_operator.get("status") == "conformance_ready"
            and verification.get("receipt_hash_valid") is True
            and verification.get("chain_valid") is True
            and verification.get("measurement_conformance_valid") is True
            and verification.get("measurement_witness_valid") is True
            and verification.get("epoch_current") is True
            and verification.get("cohort_current") is True
            and verification.get("exactly_once_event") is True
        )
        if verified_activation:
            break
    measurement_state = (
        GATE_PASS
        if verified_activation
        else validity.get("measurement_state")
        or (
            GATE_PASS
            if frame.get("measurement_complete")
            else GATE_UNKNOWN
            if not frame
            else GATE_FAIL
            if frame.get("structurally_valid") and not frame.get("measured_state_digest")
            else GATE_UNKNOWN
        )
    )
    if (symbiosis.get("status") or "cold") in {"cold", None}:
        circulation_state = GATE_UNKNOWN
    elif (symbiosis.get("ledger") or {}).get("valid") is False:
        circulation_state = GATE_FAIL
    elif (symbiosis.get("ledger") or {}).get("valid") is True:
        circulation_state = GATE_PASS
    else:
        circulation_state = GATE_UNKNOWN

    sensing = str(
        self_sensing.get("classification") or self_sensing.get("status") or ""
    ).upper()
    bind = str(binding.get("classification") or "").upper()
    if not sensing and not bind and not resonance:
        temporal_state = GATE_UNKNOWN
    elif sensing in {"STRESSED", "UNBOUND"} or bind == "DRIFT_REGIME":
        temporal_state = GATE_FAIL
    elif str(resonance.get("status") or "") == "no_stable_peak":
        temporal_state = GATE_FAIL
    elif sensing in {"COLD", "INDETERMINATE"} or bind in {
        "BINDING_GAP",
        "BUFFER_PENDING",
        "COLD_FIELD",
        "INDETERMINATE",
        "TRANSITION_REGIME",
    }:
        # Non-ready observer states must not fall through to temporal pass.
        temporal_state = GATE_UNKNOWN
    elif str(resonance.get("status") or "") != "stable_peak":
        # A candidate or missing resonance is not a verified temporal field.
        temporal_state = GATE_UNKNOWN
    else:
        temporal_state = GATE_PASS

    ostt_status = str(
        ostt.get("status")
        or (ostt.get("residual_evidence") or {}).get("status")
        or ""
    )
    if interlock.get("data_ready") is True or ostt_status in {
        "conformance_measured",
        "measured",
    }:
        distillation_state = GATE_PASS
    elif interlock or ostt:
        distillation_state = GATE_FAIL if interlock.get("data_ready") is False else GATE_UNKNOWN
    else:
        distillation_state = GATE_UNKNOWN

    planes = {
        "constitutional_ready": constitutional,
        "continuity_ready": continuity_state,
        "measurement_ready": measurement_state,
        "circulation_ready": circulation_state,
        "temporal_ready": temporal_state,
        "distillation_ready": distillation_state,
    }
    overall = _min_gate(list(planes.values()))
    return {
        "schema_version": "cortex-interconnect-readiness/1.1",
        **planes,
        # Boolean convenience views (unknown collapses to False for legacy)
        "planes_boolean": {k: v == GATE_PASS for k, v in planes.items()},
        "overall_state": overall,
        "overall_ready": overall == GATE_PASS,
        "mesh_green_legacy": mesh_green_constitutional,
        "composition": "min_gate(fail < unknown < pass) — no plane compensates",
        "advisory_only": True,
        "policy_effect": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_trajectory(
    frames: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify F_k.hash = T_k.prior and F_{k+1}.hash = T_k.next and outcome binding."""
    errors: list[str] = []
    if len(frames) < 2:
        return {
            "valid": False,
            "errors": ["need_at_least_two_frames"],
            "advisory_only": True,
        }
    frame_by_hash = {str(f.get("receipt_hash")): f for f in frames}
    for index, transition in enumerate(transitions):
        prior_h = str(transition.get("prior_frame_hash") or "")
        next_h = str(transition.get("next_frame_hash") or "")
        if prior_h not in frame_by_hash:
            errors.append(f"transition_{index}_prior_missing")
        if next_h not in frame_by_hash:
            errors.append(f"transition_{index}_next_missing")
        if transition.get("outcome_hash"):
            # Presence is required for outcome_bound credit; full subject recheck
            # is done at the symbiotic outcome layer.
            pass
    # Order frames by turn
    ordered = sorted(frames, key=lambda f: int(f.get("turn_id") or 0))
    for i in range(len(ordered) - 1):
        a = ordered[i]
        b = ordered[i + 1]
        matching = [
            t
            for t in transitions
            if t.get("prior_frame_hash") == a.get("receipt_hash")
            and t.get("next_frame_hash") == b.get("receipt_hash")
        ]
        if not matching:
            errors.append(
                f"missing_transition_turn_{a.get('turn_id')}_to_{b.get('turn_id')}"
            )
    return {
        "valid": not errors,
        "errors": errors,
        "frame_count": len(frames),
        "transition_count": len(transitions),
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "FRESHNESS_LIMITS_MS",
    "GATE_FAIL",
    "GATE_PASS",
    "GATE_UNKNOWN",
    "GLYPH",
    "SCHEMA",
    "TRAJECTORY_CLASSES",
    "TRANSITION_SCHEMA",
    "VERSION",
    "build_context_delta",
    "build_interconnect_transition",
    "capture_atomic_interconnect_frame",
    "capture_interconnect_frame",
    "classify_transition",
    "frame_compatible_with_proposal",
    "readiness_panel",
    "verify_trajectory",
]
