"""v8.4.5 — Distillation candidate extraction from verified trajectories.

Converts a verified frame transition into typed memory *candidates*:

    (F_k, T_k, O_k, F_{k+1}) → D_k

Candidates are not durable memory. They do not authorize learning, execution,
or policy. The future unified membrane should distill measured change linked to
an outcome — not arbitrary chat text.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA = "cortex-distillation-candidates/1.0"
VERSION = "8.9.3"
GLYPH = "⧉◇"
CLAIM_BOUNDARY = (
    "Distillation candidates are typed, trajectory-derived proposals for what "
    "might later be retained. They are not memory writes, not facts by "
    "fluency, and not authority. retain defaults to false; durable_write and "
    "memory_write remain unauthorized until the v8.5 will-bound membrane admits them."
)

CANDIDATE_TYPES = frozenset(
    {
        "verified_fact",
        "successful_procedure",
        "failed_hypothesis",
        "counterevidence",
        "useful_route",
        "persistent_constraint",
        "regime_warning",
        "unresolved_ambiguity",
    }
)

# Support levels mirror causal_status quality without inventing causality.
SUPPORT_HIGH = "high"  # comparison_supported
SUPPORT_MEDIUM = "medium"  # outcome_bound
SUPPORT_LOW = "low"  # temporally_bound
SUPPORT_NONE = "none"  # unmeasured / blocked


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


def _support_from_causal(causal_status: str) -> str:
    if causal_status == "comparison_supported":
        return SUPPORT_HIGH
    if causal_status == "outcome_bound":
        return SUPPORT_MEDIUM
    if causal_status == "temporally_bound":
        return SUPPORT_LOW
    return SUPPORT_NONE


def _candidate(
    *,
    candidate_type: str,
    summary: str,
    support_level: str,
    source: Mapping[str, Any],
    evidence: Mapping[str, Any],
    session_id: str,
    turn_id: int,
    repo: str,
    index: int,
) -> dict[str, Any]:
    kind = candidate_type if candidate_type in CANDIDATE_TYPES else "unresolved_ambiguity"
    body = {
        "candidate_type": kind,
        "kind": kind,  # alias for symbiotic consolidation kinds
        "summary": summary,
        "support_level": support_level,
        "source": dict(source),
        "evidence": dict(evidence),
        "session_id": session_id,
        "turn_id": int(turn_id),
        "repo": repo,
        "index": int(index),
        "retain": False,
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "memory_write_authorized": False,
        "durable_write_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    candidate_id = "cand_" + _sha(body)[:20]
    return {**body, "candidate_id": candidate_id}


def _trajectory_links_valid(
    prior_frame: Mapping[str, Any],
    next_frame: Mapping[str, Any],
    transition: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    prior_h = str(prior_frame.get("receipt_hash") or "")
    next_h = str(next_frame.get("receipt_hash") or "")
    t_prior = str(transition.get("prior_frame_hash") or "")
    t_next = str(transition.get("next_frame_hash") or "")
    if not prior_h or not next_h:
        errors.append("frame_hashes_missing")
    if not t_prior or not t_next:
        errors.append("transition_hashes_missing")
    if prior_h and t_prior and prior_h != t_prior:
        errors.append("prior_frame_hash_mismatch")
    if next_h and t_next and next_h != t_next:
        errors.append("next_frame_hash_mismatch")
    if prior_h and next_h and prior_h == next_h:
        errors.append("degenerate_same_frame")
    return (not errors, errors)


def extract_distillation_candidates(
    *,
    prior_frame: Mapping[str, Any],
    next_frame: Mapping[str, Any],
    transition: Mapping[str, Any],
    outcome: Mapping[str, Any] | None = None,
    proposal: Mapping[str, Any] | None = None,
    evaluation: Mapping[str, Any] | None = None,
    joint_action: Mapping[str, Any] | None = None,
    context_delta: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract typed candidates from one verified trajectory step.

    Does not write memory. ``retain`` is always false on extraction.
    """
    outcome = outcome or {}
    proposal = proposal or {}
    evaluation = evaluation or {}
    joint_action = joint_action or {}
    context_delta = context_delta or {}

    valid, link_errors = _trajectory_links_valid(prior_frame, next_frame, transition)
    session_id = str(
        next_frame.get("session_id")
        or prior_frame.get("session_id")
        or transition.get("session_id")
        or ""
    )
    turn_id = int(
        transition.get("turn_id")
        or next_frame.get("turn_id")
        or prior_frame.get("turn_id")
        or 0
    )
    repo = str(
        next_frame.get("repo") or prior_frame.get("repo") or transition.get("repo") or ""
    )
    source = {
        "prior_frame_hash": prior_frame.get("receipt_hash"),
        "next_frame_hash": next_frame.get("receipt_hash"),
        "transition_hash": transition.get("receipt_hash"),
        "measurement_cohort_id": next_frame.get("measurement_cohort_id")
        or prior_frame.get("measurement_cohort_id")
        or transition.get("measurement_cohort_id"),
        "coordinate_schema_digest": next_frame.get("coordinate_schema_digest")
        or prior_frame.get("coordinate_schema_digest")
        or transition.get("coordinate_schema_digest"),
        "outcome_hash": transition.get("outcome_hash") or outcome.get("receipt_hash"),
        "outcome_id": outcome.get("outcome_id"),
        "activation_id": outcome.get("activation_id"),
        "witness_result_hash": outcome.get("witness_result_hash")
        or outcome.get("witness_result_id"),
        "proposal_hash": transition.get("proposal_hash") or proposal.get("receipt_hash"),
        "evaluation_hash": transition.get("evaluation_hash")
        or evaluation.get("receipt_hash"),
        "joint_action_hash": transition.get("joint_action_hash")
        or joint_action.get("receipt_hash"),
        "context_delta_hash": context_delta.get("receipt_hash"),
    }

    if not valid:
        material = {
            "schema_version": SCHEMA,
            "version": VERSION,
            "glyph": GLYPH,
            "kind": "distillation_candidate_batch",
            "repo": repo,
            "repository_id": next_frame.get("repository_id")
            or prior_frame.get("repository_id"),
            "session_id": session_id,
            "turn_id": turn_id,
        "body_epoch_id": next_frame.get("body_epoch_id")
            or prior_frame.get("body_epoch_id")
            or transition.get("body_epoch_id")
            or "",
        "measurement_cohort_id": next_frame.get("measurement_cohort_id")
            or prior_frame.get("measurement_cohort_id")
            or transition.get("measurement_cohort_id")
            or "",
        "coordinate_schema_digest": next_frame.get("coordinate_schema_digest")
            or prior_frame.get("coordinate_schema_digest")
            or transition.get("coordinate_schema_digest")
            or "",
            "extraction_status": "blocked",
            "trajectory_verified": False,
            "link_errors": link_errors,
            "candidates": [],
            "candidate_count": 0,
            "by_type": {},
            "source": source,
            "transition_class": transition.get("transition_class"),
            "causal_status": transition.get("causal_status"),
            "advisory_only": True,
            "policy_effect": False,
            "update_authorized": False,
            "memory_write_authorized": False,
            "durable_write_authorized": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "cortex_version": __version__,
        }
        event_id = "evt_" + _sha(
            {
                "kind": "distillation_candidate_batch",
                "prior": source["prior_frame_hash"],
                "next": source["next_frame_hash"],
                "status": "blocked",
            }
        )[:24]
        receipt_hash = _sha({**material, "event_id": event_id})
        return {
            **material,
            "event_id": event_id,
            "receipt_hash": receipt_hash,
            "created_at": time.time(),
        }

    causal = str(transition.get("causal_status") or "unmeasured")
    support = _support_from_causal(causal)
    tclass = str(transition.get("transition_class") or "unknown_transition")
    changed = list(transition.get("changed_surface_mask") or [])
    prior_v = dict(prior_frame.get("validity") or {})
    next_v = dict(next_frame.get("validity") or {})
    candidates: list[dict[str, Any]] = []

    def add(
        ctype: str,
        summary: str,
        *,
        support_level: str | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        candidates.append(
            _candidate(
                candidate_type=ctype,
                summary=summary,
                support_level=support_level or support,
                source=source,
                evidence={
                    "transition_class": tclass,
                    "causal_status": causal,
                    "changed_surfaces": changed,
                    **dict(evidence or {}),
                },
                session_id=session_id,
                turn_id=turn_id,
                repo=repo,
                index=len(candidates),
            )
        )

    # --- Structure / regime signals (do not require causal credit) ---
    if tclass == "constitutional_block" or next_v.get("epoch_state") == "fail":
        add(
            "persistent_constraint",
            "Epoch or constitutional plane failed across the frame transition.",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
            evidence={"epoch_state": next_v.get("epoch_state")},
        )
    if tclass == "temporal_drift" or next_v.get("freshness_state") == "fail":
        add(
            "regime_warning",
            "Surface freshness failed; state may be present_but_stale.",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
            evidence={"freshness_state": next_v.get("freshness_state")},
        )
    if tclass == "measurement_loss":
        add(
            "regime_warning",
            "Measurement surfaces were lost between frames.",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
        )
    if tclass == "symbiotic_regression":
        add(
            "regime_warning",
            "Overall readiness regressed across the transition.",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
            evidence={
                "prior_overall": prior_v.get("overall_state"),
                "next_overall": next_v.get("overall_state"),
            },
        )
    if tclass == "epoch_transition":
        add(
            "persistent_constraint",
            "Body epoch changed; prior epoch-bound lessons may not transfer.",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
            evidence={
                "prior_epoch": prior_frame.get("body_epoch_id"),
                "next_epoch": next_frame.get("body_epoch_id"),
            },
        )
    if tclass == "schema_transition":
        add(
            "regime_warning",
            "Coordinate schema changed; comparisons across the seam are limited.",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
        )

    # Context delta signals
    for item in context_delta.get("unresolved_questions") or ():
        add(
            "unresolved_ambiguity",
            f"Unresolved after transition: {item}",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
            evidence={"question": item},
        )
    for item in context_delta.get("persistent_constraints") or ():
        add(
            "persistent_constraint",
            f"Persistent constraint: {item}",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
            evidence={"constraint": item},
        )
    if context_delta.get("new_failures"):
        add(
            "regime_warning",
            "New failures appeared in context after the transition.",
            support_level=SUPPORT_LOW if support == SUPPORT_NONE else support,
            evidence={"new_failures": list(context_delta.get("new_failures") or ())},
        )

    # Evaluation constraints (identity-local; not causal credit for outcomes)
    decision = str(evaluation.get("decision") or "")
    if decision in {"hold", "constrain", "abstain"}:
        add(
            "persistent_constraint",
            f"Evaluation decision was {decision}; do not treat proposal as free.",
            support_level=SUPPORT_LOW,
            evidence={"decision": decision, "gates": evaluation.get("gates")},
        )

    # --- Outcome-linked candidates require at least outcome_bound credit ---
    outcome_linked = support in {SUPPORT_HIGH, SUPPORT_MEDIUM}
    success = outcome.get("success")
    if outcome_linked and success is True:
        action = str(
            proposal.get("proposed_action")
            or joint_action.get("tool_action")
            or joint_action.get("action")
            or ""
        ).strip()
        objective = str(proposal.get("interpreted_objective") or "").strip()
        if action:
            add(
                "successful_procedure",
                f"Witnessed success after procedure: {action[:200]}",
                evidence={
                    "proposed_action": action,
                    "objective": objective,
                    "outcome_status": outcome.get("status"),
                },
            )
        if tclass in {"evidence_gain", "symbiotic_progress", "distillation_ready"}:
            add(
                "verified_fact",
                "Measured surfaces improved with a witnessed successful outcome.",
                evidence={"transition_class": tclass},
            )
        if changed and tclass not in {"stable_continuation"}:
            add(
                "useful_route",
                "Identity-bound path produced measured change under success.",
                evidence={"changed_surfaces": changed},
            )
    elif outcome_linked and success is False:
        objective = str(proposal.get("interpreted_objective") or "").strip()
        action = str(proposal.get("proposed_action") or "").strip()
        if objective or action:
            add(
                "failed_hypothesis",
                f"Witnessed failure for hypothesis: {(objective or action)[:200]}",
                evidence={
                    "objective": objective,
                    "proposed_action": action,
                    "outcome_status": outcome.get("status"),
                },
            )
        if changed:
            add(
                "counterevidence",
                "Measured surfaces changed under a failed outcome — counterevidence.",
                evidence={"changed_surfaces": changed},
            )
    elif support == SUPPORT_LOW and proposal.get("receipt_hash"):
        # Temporally adjacent proposal without outcome credit — ambiguity only.
        add(
            "unresolved_ambiguity",
            "Proposal is temporally bound but lacks outcome credit; do not retain as fact.",
            support_level=SUPPORT_LOW,
            evidence={"proposal_hash": proposal.get("receipt_hash")},
        )

    # Deduplicate by (type, summary)
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for cand in candidates:
        key = (str(cand.get("candidate_type")), str(cand.get("summary")))
        if key in seen:
            continue
        seen.add(key)
        unique.append(cand)
    candidates = unique

    if not candidates and tclass == "stable_continuation":
        # Stable continuation is still a signal: no lesson forced.
        add(
            "unresolved_ambiguity",
            "Stable continuation with no typed outcome lesson.",
            support_level=SUPPORT_NONE,
        )
    elif not candidates:
        add(
            "unresolved_ambiguity",
            "Transition verified but no typed distillation signal matched.",
            support_level=SUPPORT_NONE,
            evidence={"transition_class": tclass, "causal_status": causal},
        )

    by_type: dict[str, int] = {}
    for cand in candidates:
        by_type[str(cand["candidate_type"])] = (
            by_type.get(str(cand["candidate_type"]), 0) + 1
        )

    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "distillation_candidate_batch",
        "repo": repo,
        "repository_id": next_frame.get("repository_id")
        or prior_frame.get("repository_id"),
        "session_id": session_id,
        "turn_id": turn_id,
        "body_epoch_id": next_frame.get("body_epoch_id")
            or prior_frame.get("body_epoch_id")
            or transition.get("body_epoch_id")
            or "",
        "measurement_cohort_id": next_frame.get("measurement_cohort_id")
            or prior_frame.get("measurement_cohort_id")
            or transition.get("measurement_cohort_id")
            or "",
        "coordinate_schema_digest": next_frame.get("coordinate_schema_digest")
            or prior_frame.get("coordinate_schema_digest")
            or transition.get("coordinate_schema_digest")
            or "",
        "extraction_status": "extracted" if candidates else "empty",
        "trajectory_verified": True,
        "link_errors": [],
        "candidates": candidates,
        "candidate_count": len(candidates),
        "by_type": by_type,
        "source": source,
        "transition_class": tclass,
        "causal_status": causal,
        "support_ceiling": support,
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "memory_write_authorized": False,
        "durable_write_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    event_id = "evt_" + _sha(
        {
            "kind": "distillation_candidate_batch",
            "prior": source["prior_frame_hash"],
            "next": source["next_frame_hash"],
            "transition": source["transition_hash"],
            "types": sorted(by_type),
            "count": len(candidates),
        }
    )[:24]
    receipt_hash = _sha({**material, "event_id": event_id})
    return {
        **material,
        "event_id": event_id,
        "receipt_hash": receipt_hash,
        "created_at": time.time(),
    }


def extract_session_distillation_candidates(
    session: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Walk session turns and re-extract candidates from stored transitions."""
    turns = dict(session.get("turns") or {})
    ordered_keys = sorted(turns.keys(), key=lambda k: int(k) if str(k).isdigit() else 0)
    batches: list[dict[str, Any]] = []
    for key in ordered_keys:
        turn = turns.get(key) or {}
        if not isinstance(turn, Mapping):
            continue
        existing = turn.get("distillation_candidates")
        if isinstance(existing, Mapping) and existing.get("receipt_hash"):
            batches.append(dict(existing))
            continue
        transition = turn.get("interconnect_transition")
        frame = turn.get("interconnect_frame")
        if not isinstance(transition, Mapping) or not isinstance(frame, Mapping):
            continue
        # Prior frame is on the previous turn when available.
        prior_key = str(int(key) - 1) if str(key).isdigit() else None
        prior_turn = turns.get(prior_key) if prior_key else None
        prior_frame = (
            (prior_turn or {}).get("interconnect_frame")
            if isinstance(prior_turn, Mapping)
            else None
        )
        if not isinstance(prior_frame, Mapping):
            continue
        prior_outcome = (
            (prior_turn or {}).get("outcome") if isinstance(prior_turn, Mapping) else {}
        )
        prior_proposal = (
            (prior_turn or {}).get("agent_proposal")
            if isinstance(prior_turn, Mapping)
            else {}
        )
        prior_eval = (
            (prior_turn or {}).get("cortex_evaluation")
            if isinstance(prior_turn, Mapping)
            else {}
        )
        prior_action = (
            (prior_turn or {}).get("joint_action")
            if isinstance(prior_turn, Mapping)
            else {}
        )
        batch = extract_distillation_candidates(
            prior_frame=prior_frame,
            next_frame=frame,
            transition=transition,
            outcome=prior_outcome if isinstance(prior_outcome, Mapping) else {},
            proposal=prior_proposal if isinstance(prior_proposal, Mapping) else {},
            evaluation=prior_eval if isinstance(prior_eval, Mapping) else {},
            joint_action=prior_action if isinstance(prior_action, Mapping) else {},
            context_delta=turn.get("context_delta")
            if isinstance(turn.get("context_delta"), Mapping)
            else {},
        )
        batches.append(batch)
    return batches


def flatten_candidates(
    batches: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten batch receipts into candidate dicts for consolidation input."""
    out: list[dict[str, Any]] = []
    for batch in batches:
        for cand in batch.get("candidates") or ():
            if isinstance(cand, Mapping):
                out.append(dict(cand))
    return out


def candidates_authorize_nothing(batch: Mapping[str, Any]) -> bool:
    """Invariant: extraction never opens authority bits."""
    if batch.get("policy_effect") or batch.get("update_authorized"):
        return False
    if batch.get("memory_write_authorized") or batch.get("durable_write_authorized"):
        return False
    for cand in batch.get("candidates") or ():
        if not isinstance(cand, Mapping):
            return False
        if cand.get("retain") is True:
            return False
        if cand.get("memory_write_authorized") or cand.get("durable_write_authorized"):
            return False
        if cand.get("policy_effect") or cand.get("update_authorized"):
            return False
    return True


__all__ = [
    "CANDIDATE_TYPES",
    "CLAIM_BOUNDARY",
    "GLYPH",
    "SCHEMA",
    "SUPPORT_HIGH",
    "SUPPORT_LOW",
    "SUPPORT_MEDIUM",
    "SUPPORT_NONE",
    "VERSION",
    "candidates_authorize_nothing",
    "extract_distillation_candidates",
    "extract_session_distillation_candidates",
    "flatten_candidates",
]
