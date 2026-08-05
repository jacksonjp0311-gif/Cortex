"""AI–Cortex symbiotic runtime — typed receipts across the two-timescale seam.

The model is temporary working cortex. Cortex is the durable body. Neither is
the host authority. This module records the circulation:

    Cortex context → AI working state → proposal → evaluation → joint action
    → witnessed outcome → consolidation (slow, gated)

It does not run the model, grant authority, mutate the host, or write durable
memory merely because the model generated fluent text.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

SCHEMA = "cortex-symbiosis/1.7"
GLYPH = "☍"
VERSION = "8.6.0"
CLAIM_BOUNDARY = (
    "AI–Cortex symbiotic circulation is a typed two-timescale ledger: the model "
    "proposes meaning; Cortex preserves tested continuity. Distillation candidates "
    "are trajectory lessons; authenticated will supplies direction; the membrane "
    "admits under will ∧ ΓΞWOS; v8.6 writes admitted memories to an immutable "
    "ledger only — never host mutation, never invents facts, never auto-executes."
)
GATE_PASS = "pass"
GATE_FAIL = "fail"
GATE_UNKNOWN = "unknown"
GATE_STATES = frozenset({GATE_PASS, GATE_FAIL, GATE_UNKNOWN})

EVALUATION_DECISIONS = frozenset(
    {"allow", "constrain", "ask", "abstain", "hold"}
)
CONSOLIDATION_KINDS = frozenset(
    {
        "verified_fact",
        "successful_procedure",
        "failed_hypothesis",
        "counterevidence",
        "useful_route",
        "persistent_constraint",
        "regime_warning",
        "operator_correction",
        "unresolved_ambiguity",
        "model_specific_preference",
        "generalizable_project_knowledge",
        "rejected_fluent_claim",
    }
)
# Six circulation receipts plus the independently witnessed outcome receipt.
RECEIPT_KINDS = (
    "agent_instantiation",
    "cortex_context",
    "interconnect_frame",
    "agent_proposal",
    "cortex_evaluation",
    "joint_action",
    "outcome",
    "distillation_candidate_batch",
    "will_root",
    "distillation_membrane_admission",
    "symbiotic_consolidation",
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


def _clip01(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return max(0.0, min(1.0, number))


def _digest_list(items: Sequence[Any], *, limit: int = 32) -> list[str]:
    digests: list[str] = []
    for item in list(items)[:limit]:
        digests.append(_sha(item)[:24])
    return digests


def _event_id(
    *,
    session_id: str,
    turn_id: int,
    kind: str,
    body_epoch_id: str,
    salt: str = "",
) -> str:
    return "evt_" + _sha(
        {
            "session_id": session_id,
            "turn_id": int(turn_id),
            "kind": kind,
            "body_epoch_id": body_epoch_id,
            "salt": salt,
        }
    )[:24]


def _base(
    *,
    kind: str,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    turn_id: int = 0,
    event_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
    prior_receipt_hash: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    turn = int(turn_id)
    event = str(
        event_id
        or _event_id(
            session_id=session_id,
            turn_id=turn,
            kind=kind,
            body_epoch_id=body_epoch_id,
        )
    )
    case = str(case_id or f"case_{session_id}_{turn}")
    invocation = str(invocation_id or f"inv_{session_id}")
    material = {
        "kind": kind,
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "turn_id": turn,
        "event_id": event,
        "case_id": case,
        "invocation_id": invocation,
        "body_epoch_id": body_epoch_id,
        "prior_receipt_hash": prior_receipt_hash,
        **fields,
    }
    receipt_hash = _sha(material)
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": kind,
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "turn_id": turn,
        "event_id": event,
        "case_id": case,
        "invocation_id": invocation,
        "body_epoch_id": body_epoch_id,
        "prior_receipt_hash": prior_receipt_hash,
        "receipt_hash": receipt_hash,
        "created_at": time.time(),
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        **fields,
    }


def classify_assumption_status(
    *,
    evaluation_decision: str | None,
    outcome_success: bool | None = None,
    assumption: str = "",
) -> str:
    """Map a proposal assumption into a typed status bucket.

    Held/asked proposals leave assumptions unverified or blocked — never
    automatically "failed".
    """
    decision = str(evaluation_decision or "").strip().lower()
    text = str(assumption or "")
    if outcome_success is False and decision in {"allow", "constrain"}:
        return "assumptions_disconfirmed"
    if outcome_success is True and decision in {"allow", "constrain"}:
        return "assumptions_supported"
    if decision in {"hold", "abstain"}:
        return "assumptions_blocked"
    if decision == "ask":
        return "assumptions_unverified"
    if decision in {"allow", "constrain"} and outcome_success is None:
        return "assumptions_unverified"
    return "assumptions_unverified" if text else "assumptions_unverified"


def agent_instantiation_receipt(
    *,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    provider: str,
    model_id: str,
    capability_profile: Mapping[str, Any] | None = None,
    context_window_tokens: int | None = None,
    tool_scopes: Sequence[str] | None = None,
    allowed_operations: Sequence[str] | None = None,
    forbidden_operations: Sequence[str] | None = None,
    context_packet_digest: str | None = None,
    cortex_version: str | None = None,
    prior_receipt_hash: str | None = None,
    turn_id: int = 0,
    event_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    """Identify one bounded model instantiation — not a persistent self."""
    return _base(
        kind="agent_instantiation",
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        turn_id=turn_id,
        event_id=event_id,
        case_id=case_id,
        invocation_id=invocation_id,
        prior_receipt_hash=prior_receipt_hash,
        provider=str(provider or "undeclared"),
        model_id=str(model_id or "undeclared"),
        capability_profile=dict(capability_profile or {}),
        context_window_tokens=context_window_tokens,
        tool_scopes=list(tool_scopes or ()),
        allowed_operations=list(allowed_operations or ()),
        forbidden_operations=list(
            forbidden_operations
            or (
                "host_source_mutation",
                "constitutional_bit_write",
                "unwitnessed_memory_write",
                "authority_escalation",
            )
        ),
        context_packet_digest=context_packet_digest,
        cortex_version=str(cortex_version or __version__),
        identity_claim="bounded_instantiation_only",
        persistent_self=False,
    )


def cortex_context_receipt(
    *,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    evidence_items: Sequence[Mapping[str, Any]] | None = None,
    memory_episodes: Sequence[Mapping[str, Any]] | None = None,
    graph_neighbors: Sequence[Mapping[str, Any]] | None = None,
    predictions: Mapping[str, Any] | None = None,
    unresolved_contradictions: Sequence[Any] | None = None,
    operating_regime: Mapping[str, Any] | None = None,
    confidence: Mapping[str, Any] | None = None,
    constitutional_restrictions: Sequence[str] | None = None,
    packet_hash: str | None = None,
    prior_receipt_hash: str | None = None,
    turn_id: int = 0,
    event_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    """Record exactly what Cortex gave the AI for this turn."""
    evidence = [dict(item) for item in (evidence_items or ()) if isinstance(item, Mapping)]
    episodes = [
        dict(item) for item in (memory_episodes or ()) if isinstance(item, Mapping)
    ]
    neighbors = [
        dict(item) for item in (graph_neighbors or ()) if isinstance(item, Mapping)
    ]
    packet_material = {
        "evidence_digests": _digest_list(evidence),
        "episode_digests": _digest_list(episodes),
        "neighbor_digests": _digest_list(neighbors),
        "predictions": dict(predictions or {}),
        "unresolved_contradictions": list(unresolved_contradictions or ()),
        "operating_regime": dict(operating_regime or {}),
        "confidence": dict(confidence or {}),
        "constitutional_restrictions": list(constitutional_restrictions or ()),
        "packet_hash": packet_hash,
        "body_epoch_id": body_epoch_id,
        "repository_id": repository_id,
    }
    return _base(
        kind="cortex_context",
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        turn_id=turn_id,
        event_id=event_id,
        case_id=case_id,
        invocation_id=invocation_id,
        prior_receipt_hash=prior_receipt_hash,
        evidence_count=len(evidence),
        evidence_digests=packet_material["evidence_digests"],
        memory_episode_count=len(episodes),
        memory_episode_digests=packet_material["episode_digests"],
        graph_neighbor_count=len(neighbors),
        graph_neighbor_digests=packet_material["neighbor_digests"],
        predictions=dict(predictions or {}),
        unresolved_contradictions=list(unresolved_contradictions or ()),
        operating_regime=dict(operating_regime or {}),
        confidence=dict(confidence or {}),
        constitutional_restrictions=list(constitutional_restrictions or ()),
        packet_hash=packet_hash or _sha(packet_material),
        context_packet_digest=_sha(packet_material),
        reproducible_starting_point=True,
    )


def agent_proposal_receipt(
    *,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    interpreted_objective: str,
    proposed_action: str,
    evidence_citations: Sequence[str] | None = None,
    assumptions: Sequence[str] | None = None,
    declared_uncertainty: float | Mapping[str, Any] | None = None,
    expected_result: str | Mapping[str, Any] | None = None,
    alternatives_considered: Sequence[Any] | None = None,
    requested_permissions: Sequence[str] | None = None,
    predicted_state_transition: Mapping[str, Any] | None = None,
    rationale_public: str | None = None,
    prior_receipt_hash: str | None = None,
    turn_id: int = 1,
    event_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
    context_receipt_hash: str | None = None,
    interconnect_frame_hash: str | None = None,
) -> dict[str, Any]:
    """Inspectable AI proposal — external rationale, not private chain-of-thought."""
    if isinstance(declared_uncertainty, Mapping):
        uncertainty = {
            str(key): _clip01(value) for key, value in declared_uncertainty.items()
        }
        uncertainty_scalar = (
            sum(uncertainty.values()) / len(uncertainty) if uncertainty else 1.0
        )
    else:
        uncertainty_scalar = _clip01(
            1.0 if declared_uncertainty is None else declared_uncertainty
        )
        uncertainty = {"overall": uncertainty_scalar}
    return _base(
        kind="agent_proposal",
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        turn_id=turn_id,
        event_id=event_id,
        case_id=case_id,
        invocation_id=invocation_id,
        prior_receipt_hash=prior_receipt_hash,
        interpreted_objective=str(interpreted_objective or ""),
        proposed_action=str(proposed_action or ""),
        evidence_citations=list(evidence_citations or ()),
        assumptions=list(assumptions or ()),
        declared_uncertainty=uncertainty,
        declared_uncertainty_scalar=uncertainty_scalar,
        expected_result=expected_result
        if isinstance(expected_result, Mapping)
        else {"summary": str(expected_result or "")},
        alternatives_considered=list(alternatives_considered or ()),
        requested_permissions=list(requested_permissions or ()),
        predicted_state_transition=dict(predicted_state_transition or {}),
        rationale_public=str(
            rationale_public
            or "proposal declared without extended private chain-of-thought"
        ),
        private_chain_of_thought_stored=False,
        context_receipt_hash=context_receipt_hash,
        interconnect_frame_hash=interconnect_frame_hash,
    )


def _tri(state: bool | None) -> str:
    """Map boolean-or-missing evidence to pass|fail|unknown."""
    if state is True:
        return GATE_PASS
    if state is False:
        return GATE_FAIL
    return GATE_UNKNOWN


def measure_evaluation_gates(
    store: Any,
    repo: str,
    *,
    proposal: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind evaluation gates to live Cortex measurements as pass|fail|unknown.

    Unknown never inherits pass behavior.  Boolean convenience fields remain for
    callers, but decision logic must prefer the tri-state panel.
    """
    from .epoch import observe_current_epoch

    epoch = observe_current_epoch(store, repo)
    claimed_epoch = str(proposal.get("body_epoch_id") or "")
    live_epoch = str(epoch.get("epoch_id") or epoch.get("live_epoch_id") or "")
    if not epoch.get("present"):
        epoch_tri = GATE_UNKNOWN
    elif not claimed_epoch or not live_epoch:
        epoch_tri = GATE_UNKNOWN
    elif bool(epoch.get("verified")) and claimed_epoch == live_epoch:
        epoch_tri = GATE_PASS
    else:
        epoch_tri = GATE_FAIL

    measured = store.get_setting(f"measured_event_latest:{repo}", {}) or {}
    if not isinstance(measured, Mapping) or not measured:
        measurement_tri = GATE_UNKNOWN
    elif (
        measured.get("status") == "measured"
        or float(measured.get("valid_fraction") or 0.0) == 1.0
    ):
        measurement_tri = GATE_PASS
    else:
        measurement_tri = GATE_FAIL

    residual = store.get_setting(f"ostt_residual_latest:{repo}", {}) or {}
    try:
        latest_conformance = store.latest_activation_conformance_receipt(repo)
    except Exception:
        latest_conformance = None
    if latest_conformance is None and isinstance(residual, Mapping):
        latest_conformance = residual if residual.get("status") else None
    if not isinstance(latest_conformance, Mapping) or not latest_conformance:
        operator_tri = GATE_UNKNOWN
    elif str(latest_conformance.get("status") or "") in {
        "conformance_measured",
        "measured",
        "conformance_ready",
    }:
        operator_tri = GATE_PASS
    else:
        operator_tri = GATE_FAIL

    try:
        outcome_row = store.db.execute(
            "SELECT COUNT(*) AS n FROM task_outcomes WHERE repo=?",
            (repo,),
        ).fetchone()
        outcome_count = int(outcome_row["n"]) if outcome_row else 0
    except Exception:
        outcome_count = 0
    outcome_tri = GATE_PASS if outcome_count > 0 else GATE_UNKNOWN

    interlock = store.get_setting(f"interlock_shadow_latest:{repo}", {}) or {}
    self_sensing = store.get_setting(f"self_sensing_latest:{repo}", {}) or {}
    resonance = store.get_setting(f"resonance_sweep_latest:{repo}", {}) or {}
    geometric = store.get_setting(f"geometric_echo_latest:{repo}", {}) or {}
    sensing = str(
        (self_sensing.get("classification") if isinstance(self_sensing, Mapping) else None)
        or (self_sensing.get("status") if isinstance(self_sensing, Mapping) else "")
        or ""
    ).upper()
    binding = store.get_setting(f"binding_field_latest:{repo}", {}) or {}
    binding_class = str(
        (binding.get("classification") if isinstance(binding, Mapping) else "") or ""
    ).upper()

    if sensing in {"STRESSED", "UNBOUND"} or binding_class == "DRIFT_REGIME":
        invariants_tri = GATE_FAIL
    elif not sensing and not binding_class and not interlock:
        invariants_tri = GATE_UNKNOWN
    elif epoch_tri != GATE_PASS:
        invariants_tri = GATE_FAIL if epoch_tri == GATE_FAIL else GATE_UNKNOWN
    elif interlock and interlock.get("status") in {"blocked", "failed"}:
        invariants_tri = GATE_FAIL
    else:
        invariants_tri = GATE_PASS

    # Host immutability: never default to pass without evidence.
    host_tri = GATE_UNKNOWN
    if isinstance(latest_conformance, Mapping):
        invariants = latest_conformance.get("invariant_results") or []
        found = False
        if isinstance(invariants, list):
            for item in invariants:
                if (
                    isinstance(item, Mapping)
                    and item.get("invariant_id") == "host_immutable"
                ):
                    host_tri = GATE_PASS if item.get("passed") is True else GATE_FAIL
                    found = True
                    break
        if not found and latest_conformance.get("status") == "conformance_measured":
            host_tri = GATE_UNKNOWN

    # Authority scope: unknown until an explicit scope witness exists.
    authority_tri = GATE_UNKNOWN
    if isinstance(latest_conformance, Mapping) and latest_conformance.get(
        "comparison_arm"
    ):
        # Presence of a constrained comparison arm is weak evidence of scoped review.
        authority_tri = GATE_PASS

    blast_radius = "bounded"
    if sensing in {"STRESSED", "UNBOUND"} or binding_class == "DRIFT_REGIME":
        blast_radius = "high"
    if str(resonance.get("status") or "") == "no_stable_peak":
        if blast_radius == "bounded":
            blast_radius = "elevated"

    if context is None:
        context_tri = GATE_UNKNOWN
    elif (
        context.get("session_id") == proposal.get("session_id")
        and context.get("body_epoch_id") == proposal.get("body_epoch_id")
    ):
        context_tri = GATE_PASS
    else:
        context_tri = GATE_FAIL

    sources = {
        "epoch": {
            "verified": bool(epoch.get("verified")),
            "epoch_id": epoch.get("epoch_id") or epoch.get("live_epoch_id"),
            "state": epoch_tri,
        },
        "measured_event": {
            "status": measured.get("status") if isinstance(measured, Mapping) else None,
            "valid_fraction": measured.get("valid_fraction")
            if isinstance(measured, Mapping)
            else None,
            "state": measurement_tri,
        },
        "outcome_count": outcome_count,
        "operator_residual_status": (
            latest_conformance.get("status")
            if isinstance(latest_conformance, Mapping)
            else None
        ),
        "self_sensing": sensing or None,
        "binding": binding_class or None,
        "resonance": resonance.get("status") if isinstance(resonance, Mapping) else None,
        "geometric_field": geometric.get("field_condition")
        if isinstance(geometric, Mapping)
        else None,
        "interlock_data_ready": interlock.get("data_ready")
        if isinstance(interlock, Mapping)
        else None,
    }
    tri = {
        "epoch_current": epoch_tri,
        "host_immutable": host_tri,
        "invariants_ok": invariants_tri,
        "authority_scope_ok": authority_tri,
        "outcome_history_ready": outcome_tri,
        "operator_contract_ready": operator_tri,
        "measurement_complete": measurement_tri,
        "context_bound": context_tri,
    }
    return {
        **{key: value == GATE_PASS for key, value in tri.items()},
        "gate_states": tri,
        "blast_radius": blast_radius,
        "measurement_sources": sources,
    }


def evaluate_proposal(
    *,
    proposal: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
    epoch_current: bool | str = False,
    host_immutable: bool | str = GATE_UNKNOWN,
    invariants_ok: bool | str = False,
    authority_scope_ok: bool | str = GATE_UNKNOWN,
    blast_radius: str = "unknown",
    outcome_history_ready: bool | str = False,
    operator_contract_ready: bool | str = False,
    measurement_complete: bool | str = False,
    context_bound: bool | str | None = None,
    forced_decision: str | None = None,
    measurement_sources: Mapping[str, Any] | None = None,
    gate_states: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Cortex evaluation of an AI proposal against durable constraints.

    Returns one of: allow, constrain, ask, abstain, hold.
    Fail-closed: gate fail holds; gate unknown never allows.
    """

    def _as_tri(value: Any, *, default: str = GATE_UNKNOWN) -> str:
        if isinstance(value, str) and value in GATE_STATES:
            return value
        if value is True:
            return GATE_PASS
        if value is False:
            return GATE_FAIL
        return default

    tri = {
        "epoch_current": _as_tri(epoch_current),
        "host_immutable": _as_tri(host_immutable, default=GATE_UNKNOWN),
        "invariants_ok": _as_tri(invariants_ok),
        "authority_scope_ok": _as_tri(authority_scope_ok, default=GATE_UNKNOWN),
        "outcome_history_ready": _as_tri(outcome_history_ready, default=GATE_UNKNOWN),
        "operator_contract_ready": _as_tri(operator_contract_ready, default=GATE_UNKNOWN),
        "measurement_complete": _as_tri(measurement_complete),
        "context_bound": _as_tri(
            context_bound
            if context_bound is not None
            else (
                True
                if context is None
                else (
                    context.get("session_id") == proposal.get("session_id")
                    and context.get("body_epoch_id") == proposal.get("body_epoch_id")
                )
            )
        ),
    }
    if isinstance(gate_states, Mapping):
        for key, value in gate_states.items():
            if key in tri and str(value) in GATE_STATES:
                tri[key] = str(value)

    gates = {
        "proposal_present": bool(proposal.get("receipt_hash")),
        "objective_declared": bool(str(proposal.get("interpreted_objective") or "").strip()),
        "action_declared": bool(str(proposal.get("proposed_action") or "").strip()),
        **{key: value == GATE_PASS for key, value in tri.items()},
        "gate_states": tri,
    }
    missing = [
        name
        for name, value in gates.items()
        if name not in {"gate_states"} and value is False
    ]
    unknown = [name for name, value in tri.items() if value == GATE_UNKNOWN]
    failed = [name for name, value in tri.items() if value == GATE_FAIL]
    uncertainty = float(proposal.get("declared_uncertainty_scalar") or 1.0)
    citations = list(proposal.get("evidence_citations") or ())
    permissions = list(proposal.get("requested_permissions") or ())
    elevated = any(
        permission in {"host_source_mutation", "authority_escalation", "unwitnessed_memory_write"}
        for permission in permissions
    )

    if forced_decision and forced_decision in EVALUATION_DECISIONS:
        decision = forced_decision
        reason = f"forced_decision:{forced_decision}"
    elif elevated or tri["authority_scope_ok"] == GATE_FAIL:
        decision = "hold"
        reason = "authority_or_forbidden_permission"
    elif tri["authority_scope_ok"] == GATE_UNKNOWN:
        decision = "hold"
        reason = "authority_scope_unknown"
    elif not gates["proposal_present"] or not gates["action_declared"]:
        decision = "abstain"
        reason = "proposal_incomplete"
    elif tri["epoch_current"] == GATE_FAIL or tri["context_bound"] == GATE_FAIL:
        decision = "hold"
        reason = "epoch_or_context_not_current"
    elif tri["epoch_current"] == GATE_UNKNOWN or tri["context_bound"] == GATE_UNKNOWN:
        decision = "hold"
        reason = "epoch_or_context_unknown"
    elif tri["host_immutable"] == GATE_FAIL:
        decision = "hold"
        reason = "host_mutation_detected"
    elif tri["host_immutable"] == GATE_UNKNOWN:
        decision = "hold"
        reason = "host_immutability_unknown"
    elif not citations:
        decision = "ask"
        reason = "evidence_citations_required"
    elif uncertainty >= 0.75:
        decision = "ask"
        reason = "declared_uncertainty_high"
    elif tri["invariants_ok"] == GATE_FAIL or tri["measurement_complete"] == GATE_FAIL:
        decision = "constrain"
        reason = "invariants_or_measurement_incomplete"
    elif tri["invariants_ok"] == GATE_UNKNOWN or tri["measurement_complete"] == GATE_UNKNOWN:
        decision = "constrain"
        reason = "invariants_or_measurement_unknown"
    elif blast_radius in {"high", "unbounded", "elevated"}:
        decision = "constrain"
        reason = f"blast_radius:{blast_radius}"
    elif (
        tri["outcome_history_ready"] != GATE_PASS
        or tri["operator_contract_ready"] != GATE_PASS
    ):
        decision = "constrain"
        reason = "history_or_contract_incomplete_or_unknown"
    else:
        decision = "allow"
        reason = "gates_satisfied_for_bounded_review"

    # Allow never means automatic execution authority.
    return {
        "decision": decision,
        "reason": reason,
        "gates": gates,
        "missing_gates": missing,
        "unknown_gates": unknown,
        "failed_gates": failed,
        "blast_radius": blast_radius,
        "measurement_sources": dict(measurement_sources or {}),
        "execution_authorized": False,
        "learning_authorized": False,
        "review_eligible": decision in {"allow", "constrain"},
    }


def outcome_receipt(
    *,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    joint_action: Mapping[str, Any] | None = None,
    outcome_kind: str = "task_result",
    success: bool | None = None,
    metrics: Mapping[str, Any] | None = None,
    external_reference: str | None = None,
    witness: Mapping[str, Any] | None = None,
    prior_receipt_hash: str | None = None,
    turn_id: int | None = None,
    event_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    """Typed outcome with independent MEASUREMENT-or-OUTCOME witness material.

    The witness must cover the outcome subject; a missing or failed witness
    yields ``witnessed=false`` and cannot authorize consolidation.
    """
    turn = int(
        turn_id if turn_id is not None else (joint_action or {}).get("turn_id") or 1
    )
    subject = {
        "outcome_kind": str(outcome_kind or "task_result"),
        "success": success,
        "metrics": dict(metrics or {}),
        "external_reference": external_reference,
        "joint_action_receipt_hash": str((joint_action or {}).get("receipt_hash") or ""),
        "session_id": session_id,
        "turn_id": turn,
        "body_epoch_id": body_epoch_id,
        "repository_id": repository_id,
        "repo": repo,
    }
    subject_hash = _sha(subject)
    witness_body = dict(witness or {})
    if not witness_body:
        witness_body = {
            "witness_id": "",
            "witness_kind": "OUTCOME",
            "verifier": "undeclared",
            "subject_receipt_hash": subject_hash,
            "evidence_hashes": [],
            "passed": False,
            "issued_at": time.time(),
            "reason": "witness_not_supplied",
        }
    else:
        witness_body.setdefault("witness_kind", "OUTCOME")
        witness_body.setdefault("subject_receipt_hash", subject_hash)
        witness_body.setdefault("issued_at", time.time())
        if not witness_body.get("witness_id"):
            witness_body["witness_id"] = "ow_" + _sha(witness_body)[:24]
    witnessed = bool(
        witness_body.get("passed") is True
        and str(witness_body.get("subject_receipt_hash") or "") == subject_hash
        and str(witness_body.get("witness_kind") or "").upper()
        in {"OUTCOME", "MEASUREMENT"}
        and str(witness_body.get("verifier") or "").strip()
        and str(witness_body.get("witness_id") or "").strip()
    )
    return _base(
        kind="outcome",
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        turn_id=turn,
        event_id=event_id,
        case_id=case_id or (joint_action or {}).get("case_id"),
        invocation_id=invocation_id or (joint_action or {}).get("invocation_id"),
        prior_receipt_hash=prior_receipt_hash
        or str((joint_action or {}).get("receipt_hash") or ""),
        outcome_kind=subject["outcome_kind"],
        success=success,
        metrics=dict(metrics or {}),
        external_reference=external_reference,
        joint_action_receipt_hash=subject["joint_action_receipt_hash"],
        outcome_subject_hash=subject_hash,
        witness=witness_body,
        witnessed=witnessed,
        closed=witnessed and success is not None,
        status="witnessed" if witnessed else "unwitnessed",
    )


def cortex_evaluation_receipt(
    *,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    proposal: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    context_receipt_hash: str | None = None,
    prior_receipt_hash: str | None = None,
    turn_id: int | None = None,
    event_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    decision = str(evaluation.get("decision") or "hold")
    if decision not in EVALUATION_DECISIONS:
        decision = "hold"
    return _base(
        kind="cortex_evaluation",
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        turn_id=int(
            turn_id if turn_id is not None else proposal.get("turn_id") or 1
        ),
        event_id=event_id,
        case_id=case_id or proposal.get("case_id"),
        invocation_id=invocation_id or proposal.get("invocation_id"),
        prior_receipt_hash=prior_receipt_hash or str(proposal.get("receipt_hash") or ""),
        proposal_receipt_hash=str(proposal.get("receipt_hash") or ""),
        context_receipt_hash=context_receipt_hash,
        decision=decision,
        reason=str(evaluation.get("reason") or ""),
        gates=dict(evaluation.get("gates") or {}),
        missing_gates=list(evaluation.get("missing_gates") or ()),
        blast_radius=str(evaluation.get("blast_radius") or "unknown"),
        measurement_sources=dict(evaluation.get("measurement_sources") or {}),
        execution_authorized=False,
        learning_authorized=False,
        review_eligible=bool(evaluation.get("review_eligible")),
        decision_space=sorted(EVALUATION_DECISIONS),
    )


def joint_action_receipt(
    *,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    proposal: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    tool_action: Mapping[str, Any] | None = None,
    measured_result: Mapping[str, Any] | None = None,
    prior_receipt_hash: str | None = None,
    turn_id: int | None = None,
    event_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    """Bind AI proposal + Cortex evaluation + tool action + measured result."""
    decision = str(evaluation.get("decision") or "hold")
    executed = bool((tool_action or {}).get("executed"))
    if executed and decision not in {"allow", "constrain"}:
        # Fail closed on the receipt surface: execution without evaluation is recorded as invalid.
        binding_status = "invalid_execution_without_evaluation"
    elif executed:
        binding_status = "bound_executed"
    else:
        binding_status = "bound_not_executed"
    return _base(
        kind="joint_action",
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        turn_id=int(
            turn_id
            if turn_id is not None
            else proposal.get("turn_id") or evaluation.get("turn_id") or 1
        ),
        event_id=event_id,
        case_id=case_id or proposal.get("case_id"),
        invocation_id=invocation_id or proposal.get("invocation_id"),
        prior_receipt_hash=prior_receipt_hash
        or str(evaluation.get("receipt_hash") or ""),
        proposal_receipt_hash=str(proposal.get("receipt_hash") or ""),
        evaluation_receipt_hash=str(evaluation.get("receipt_hash") or ""),
        evaluation_decision=decision,
        tool_action=dict(tool_action or {"executed": False}),
        measured_result=dict(measured_result or {}),
        binding_status=binding_status,
        binding_valid=binding_status.startswith("bound"),
    )


def symbiotic_consolidation_receipt(
    *,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    joint_action: Mapping[str, Any] | None = None,
    candidates: Sequence[Mapping[str, Any]] | None = None,
    constitutional_gate: bool = False,
    epoch_compatible: bool = False,
    witness_present: bool = False,
    outcome_closed: bool = False,
    stable_regime: bool = False,
    prior_receipt_hash: str | None = None,
    turn_id: int | None = None,
    event_id: str | None = None,
    case_id: str | None = None,
    invocation_id: str | None = None,
) -> dict[str, Any]:
    """Slow-layer retention decision. Fluent generation is not durable memory."""
    gamma = 1 if constitutional_gate else 0
    xi = 1 if epoch_compatible else 0
    w = 1 if witness_present else 0
    o = 1 if outcome_closed else 0
    s = 1 if stable_regime else 0
    product = gamma * xi * w * o * s
    retained: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in candidates or ():
        if not isinstance(raw, Mapping):
            continue
        item = dict(raw)
        kind = str(item.get("kind") or "unresolved_ambiguity")
        if kind not in CONSOLIDATION_KINDS:
            kind = "unresolved_ambiguity"
            item["kind"] = kind
        if product == 1 and item.get("retain") is True:
            retained.append(item)
        else:
            item = {
                **item,
                "retain": False,
                "rejection_reason": (
                    "gates_closed"
                    if product == 0
                    else "not_marked_for_retention"
                ),
            }
            rejected.append(item)
    return _base(
        kind="symbiotic_consolidation",
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        turn_id=int(
            turn_id if turn_id is not None else (joint_action or {}).get("turn_id") or 0
        ),
        event_id=event_id,
        case_id=case_id or (joint_action or {}).get("case_id"),
        invocation_id=invocation_id or (joint_action or {}).get("invocation_id"),
        prior_receipt_hash=prior_receipt_hash
        or str((joint_action or {}).get("receipt_hash") or ""),
        joint_action_receipt_hash=str((joint_action or {}).get("receipt_hash") or ""),
        gates={
            "constitutional_admissibility": gamma,
            "epoch_cohort_compatibility": xi,
            "witness": w,
            "outcome_closure": o,
            "stability": s,
            "product": product,
        },
        adaptation_authorized=False,
        durable_write_authorized=False,
        retained=retained,
        rejected=rejected,
        retained_count=len(retained),
        rejected_count=len(rejected),
        slow_layer_law=(
            "Δc = 0 whenever Γ Ξ W O S = 0; fluent model output is never "
            "sufficient for durable retention"
        ),
    )


def complementarity_surplus(
    *,
    i_joint: float | None = None,
    i_agent: float | None = None,
    i_cortex: float | None = None,
) -> dict[str, Any]:
    """Best-singleton interaction surplus S_AC = [I(A,C;O) − max{I(A;O),I(C;O)}]+.

    Without calibrated mutual-information estimates this remains unmeasured.
    """
    if i_joint is None or i_agent is None or i_cortex is None:
        return {
            "status": "unmeasured",
            "S_AC": None,
            "formula": "[I(A,C;O) - max{I(A;O), I(C;O)}]+",
            "claim_boundary": (
                "Complementarity is not claimed without calibrated outcome "
                "mutual-information estimates."
            ),
        }
    joint = max(0.0, float(i_joint))
    singleton = max(max(0.0, float(i_agent)), max(0.0, float(i_cortex)))
    surplus = max(0.0, joint - singleton)
    return {
        "status": "measured",
        "I_AC_O": joint,
        "I_A_O": float(i_agent),
        "I_C_O": float(i_cortex),
        "S_AC": surplus,
        "complementary": surplus > 0.0,
        "formula": "[I(A,C;O) - max{I(A;O), I(C;O)}]+",
        "claim_boundary": (
            "Positive S_AC indicates joint-only outcome information under the "
            "declared estimators; it is not proof of consciousness."
        ),
    }


def open_symbiotic_session(
    store: Any,
    repo: str,
    *,
    task: str,
    provider: str = "undeclared",
    model_id: str = "undeclared",
    capability_profile: Mapping[str, Any] | None = None,
    tool_scopes: Sequence[str] | None = None,
    context_window_tokens: int | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Open one AI–Cortex symbiotic session with instantiation + context receipts."""
    repository = store.repo(repo)
    if repository is None:
        raise ValueError(f"Unknown repository: {repo}")
    repository_id = str(repository["repository_id"] or "")
    from .epoch import observe_current_epoch

    epoch = observe_current_epoch(store, repo)
    body_epoch_id = str(epoch.get("epoch_id") or epoch.get("live_epoch_id") or "")
    session_id = "sym_" + _sha(
        {
            "repo": repo,
            "repository_id": repository_id,
            "task": task,
            "t": round(time.time(), 3),
        }
    )[:20]

    # Pull lightweight durable surfaces already present — no new authority.
    evidence = store.get_setting(f"source_admission_latest:{repo}", {}) or {}
    interlock = store.get_setting(f"interlock_shadow_latest:{repo}", {}) or {}
    resonance = store.get_setting(f"resonance_sweep_latest:{repo}", {}) or {}
    geometric = store.get_setting(f"geometric_echo_latest:{repo}", {}) or {}
    residual = store.get_setting(f"ostt_residual_latest:{repo}", None)
    self_sensing = store.get_setting(f"self_sensing_latest:{repo}", {}) or {}
    measured = store.get_setting(f"measured_event_latest:{repo}", {}) or {}

    restrictions = [
        "host_source_mutation_forbidden",
        "constitutional_bits_immutable",
        "no_unwitnessed_memory_write",
        "no_automatic_policy_from_fluency",
    ]
    if not epoch.get("verified"):
        restrictions.append("epoch_unverified_hold_adaptation")

    invocation_id = f"inv_{session_id}"
    context = cortex_context_receipt(
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        evidence_items=[
            {
                "surface": "source_admission",
                "status": evidence.get("status"),
                "digest": _sha(evidence)[:24],
            }
        ]
        if evidence
        else [],
        memory_episodes=[],
        graph_neighbors=[],
        predictions={
            "measured_event_present": bool(measured),
            "interlock_data_ready": bool(interlock.get("data_ready")),
        },
        unresolved_contradictions=[
            item
            for item in (
                "epoch_unverified" if not epoch.get("verified") else None,
                "interlock_not_ready" if not interlock.get("data_ready") else None,
                "no_stable_temporal_peak"
                if str(resonance.get("status") or "")
                not in {"resonant_candidate", ""}
                and resonance
                else None,
            )
            if item
        ],
        operating_regime={
            "self_sensing": (
                self_sensing.get("status") if isinstance(self_sensing, Mapping) else None
            ),
            "resonance": resonance.get("status"),
            "geometric_field": geometric.get("field_condition"),
            "residual": (residual or {}).get("status")
            if isinstance(residual, Mapping)
            else None,
            "epoch_verified": bool(epoch.get("verified")),
        },
        confidence={
            "epoch_verified": 1.0 if epoch.get("verified") else 0.0,
            "context_surfaces": _clip01(
                sum(
                    1
                    for surface in (evidence, interlock, resonance, geometric)
                    if surface
                )
                / 4.0
            ),
        },
        constitutional_restrictions=restrictions,
        packet_hash=None,
        prior_receipt_hash=None,
        turn_id=0,
        invocation_id=invocation_id,
        case_id=f"case_{session_id}_0",
    )
    instantiation = agent_instantiation_receipt(
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        provider=provider,
        model_id=model_id,
        capability_profile=capability_profile,
        context_window_tokens=context_window_tokens,
        tool_scopes=tool_scopes,
        context_packet_digest=str(context.get("context_packet_digest") or ""),
        prior_receipt_hash=None,
        turn_id=0,
        invocation_id=invocation_id,
        case_id=f"case_{session_id}_0",
    )
    # Re-bind context prior hash after instantiation so the scientific chain starts
    # at the agent seat while remaining turn-0 open receipts.
    context = cortex_context_receipt(
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
        evidence_items=[
            {
                "surface": "source_admission",
                "status": evidence.get("status"),
                "digest": _sha(evidence)[:24],
            }
        ]
        if evidence
        else [],
        memory_episodes=[],
        graph_neighbors=[],
        predictions={
            "measured_event_present": bool(measured),
            "interlock_data_ready": bool(interlock.get("data_ready")),
        },
        unresolved_contradictions=[
            item
            for item in (
                "epoch_unverified" if not epoch.get("verified") else None,
                "interlock_not_ready" if not interlock.get("data_ready") else None,
                "no_stable_temporal_peak"
                if str(resonance.get("status") or "")
                not in {"resonant_candidate", ""}
                and resonance
                else None,
            )
            if item
        ],
        operating_regime={
            "self_sensing": (
                self_sensing.get("status") if isinstance(self_sensing, Mapping) else None
            ),
            "resonance": resonance.get("status"),
            "geometric_field": geometric.get("field_condition"),
            "residual": (residual or {}).get("status")
            if isinstance(residual, Mapping)
            else None,
            "epoch_verified": bool(epoch.get("verified")),
        },
        confidence={
            "epoch_verified": 1.0 if epoch.get("verified") else 0.0,
            "context_surfaces": _clip01(
                sum(
                    1
                    for surface in (evidence, interlock, resonance, geometric)
                    if surface
                )
                / 4.0
            ),
        },
        constitutional_restrictions=restrictions,
        packet_hash=None,
        prior_receipt_hash=instantiation["receipt_hash"],
        turn_id=0,
        invocation_id=invocation_id,
        case_id=f"case_{session_id}_0",
    )

    session = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "invocation_id": invocation_id,
        "current_turn_id": 0,
        "turn_count": 0,
        "task": task,
        "task_hash": _sha(task),
        "body_epoch_id": body_epoch_id,
        "epoch_verified": bool(epoch.get("verified")),
        "grammar": (
            "agent_instantiation → cortex_context → "
            "[proposal → evaluation → joint_action → outcome]* → consolidation"
        ),
        "timescale": {
            "q_t": "AI temporary working state",
            "c_t": "Cortex durable state",
            "law": "|Δq| ≫ |Δc|; Δc=0 when Γ Ξ W O S = 0",
        },
        "symbiosis": {
            "ai_supplies": "adaptive cognition",
            "cortex_supplies": "persistent identity and disciplined memory",
            "will_supplies": "authenticated direction (v8.5 binding via membrane)",
            "membrane_supplies": "will-bound candidate admission under ΓΞWOS",
            "neither_complete_alone": True,
        },
        "receipts": {
            "agent_instantiation": instantiation,
            "cortex_context": context,
        },
        "turns": {},
        "chain": [
            instantiation["receipt_hash"],
            context["receipt_hash"],
        ],
        "complementarity": complementarity_surplus(),
        "status": "open",
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "opened_at": time.time(),
    }
    if persist:
        _ledger_commit_receipts(store, repo, [instantiation, context])
        _persist_session(store, repo, session)
        try:
            session["ledger_chain"] = store.verify_symbiotic_session(
                repo, session_id
            )
        except Exception as exc:
            session["ledger_chain"] = {
                "valid": False,
                "error": f"{type(exc).__name__}:{exc}",
            }
    return session


def record_proposal(
    store: Any,
    repo: str,
    session: Mapping[str, Any],
    *,
    interpreted_objective: str,
    proposed_action: str,
    evidence_citations: Sequence[str] | None = None,
    assumptions: Sequence[str] | None = None,
    declared_uncertainty: float | Mapping[str, Any] | None = None,
    expected_result: str | Mapping[str, Any] | None = None,
    alternatives_considered: Sequence[Any] | None = None,
    requested_permissions: Sequence[str] | None = None,
    predicted_state_transition: Mapping[str, Any] | None = None,
    rationale_public: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Append a proposal, evaluate it, and return the updated session.

    Each call advances ``current_turn_id`` so recurrent turns are independently
    ledgered.  Before the proposal, Cortex captures a turn-bound interconnect
    frame and regenerates context C_k (reciprocal pulse).
    """
    from .distillation_candidates import extract_distillation_candidates
    from .interconnect_frame import (
        build_context_delta,
        build_interconnect_transition,
        capture_atomic_interconnect_frame,
        frame_compatible_with_proposal,
    )

    session_body = dict(session)
    prior_context = dict(
        (session_body.get("receipts") or {}).get("cortex_context") or {}
    )
    turn_id = int(session_body.get("current_turn_id") or 0) + 1
    invocation_id = str(
        session_body.get("invocation_id")
        or f"inv_{session_body.get('session_id') or ''}"
    )
    case_id = f"case_{session_body.get('session_id')}_{turn_id}"
    turns = dict(session_body.get("turns") or {})
    prior_outcome_hash = None
    prior_frame_hash = None
    prior_hash = str(prior_context.get("receipt_hash") or "")
    if turns:
        last_turn = turns.get(str(turn_id - 1)) or turns.get(turn_id - 1) or {}
        if isinstance(last_turn, Mapping):
            prior_outcome_hash = str(
                (last_turn.get("outcome") or {}).get("receipt_hash") or ""
            ) or None
            prior_frame_hash = str(
                (last_turn.get("interconnect_frame") or {}).get("receipt_hash") or ""
            ) or None
            prior_hash = str(
                (last_turn.get("cortex_context") or {}).get("receipt_hash")
                or prior_outcome_hash
                or (last_turn.get("joint_action") or {}).get("receipt_hash")
                or prior_hash
            )

    chain_tip = (session_body.get("chain") or [None])[-1]
    frame = capture_atomic_interconnect_frame(
        store,
        repo,
        session_id=str(session_body.get("session_id") or ""),
        turn_id=turn_id,
        body_epoch_id=str(session_body.get("body_epoch_id") or ""),
        repository_id=str(session_body.get("repository_id") or ""),
        case_id=case_id,
        invocation_id=invocation_id,
        prior_outcome_hash=prior_outcome_hash,
        prior_frame_hash=prior_frame_hash,
        symbiosis_chain_tip=str(chain_tip) if chain_tip else None,
    )
    transition = None
    context_delta = None
    distillation_batch = None
    last_turn_payload: Mapping[str, Any] = {}
    if turns:
        last_turn_payload = (
            turns.get(str(turn_id - 1)) or turns.get(turn_id - 1) or {}
        )
        if isinstance(last_turn_payload, Mapping) and last_turn_payload.get(
            "interconnect_frame"
        ):
            transition = build_interconnect_transition(
                prior_frame=dict(last_turn_payload.get("interconnect_frame") or {}),
                next_frame=frame,
                proposal=dict(last_turn_payload.get("agent_proposal") or {}),
                evaluation=dict(last_turn_payload.get("cortex_evaluation") or {}),
                joint_action=dict(last_turn_payload.get("joint_action") or {}),
                outcome=dict(last_turn_payload.get("outcome") or {}),
            )
    # Reciprocal pulse: project turn-specific context C_k from frame + priors.
    context = cortex_context_receipt(
        repo=str(session_body.get("repo") or repo),
        repository_id=str(session_body.get("repository_id") or ""),
        session_id=str(session_body.get("session_id") or ""),
        body_epoch_id=str(session_body.get("body_epoch_id") or ""),
        evidence_items=[
            {
                "surface": "interconnect_frame",
                "frame_id": frame.get("frame_id"),
                "digest": str(frame.get("receipt_hash") or "")[:24],
            }
        ],
        memory_episodes=[],
        graph_neighbors=[],
        predictions={
            "prior_outcome_hash": prior_outcome_hash,
            "frame_compatible": bool(frame.get("compatible")),
            "measured_state_digest": frame.get("measured_state_digest"),
            "interconnect_frame_hash": frame.get("receipt_hash"),
            "interconnect_frame_id": frame.get("frame_id"),
        },
        unresolved_contradictions=[
            key
            for key, passed in (frame.get("compatibility_results") or {}).items()
            if not passed
        ],
        operating_regime={
            "frame_id": frame.get("frame_id"),
            "self_sensing_digest": frame.get("self_sensing_digest"),
            "binding_digest": frame.get("binding_digest"),
            "resonance_digest": frame.get("resonance_digest"),
        },
        confidence={
            "frame_compatible": 1.0 if frame.get("compatible") else 0.0,
        },
        constitutional_restrictions=list(
            prior_context.get("constitutional_restrictions") or ()
        ),
        packet_hash=None,
        prior_receipt_hash=str(frame.get("receipt_hash") or prior_hash or ""),
        turn_id=turn_id,
        invocation_id=invocation_id,
        case_id=case_id,
    )

    proposal = agent_proposal_receipt(
        repo=str(session_body.get("repo") or repo),
        repository_id=str(session_body.get("repository_id") or ""),
        session_id=str(session_body.get("session_id") or ""),
        body_epoch_id=str(session_body.get("body_epoch_id") or ""),
        interpreted_objective=interpreted_objective,
        proposed_action=proposed_action,
        evidence_citations=evidence_citations,
        assumptions=assumptions,
        declared_uncertainty=declared_uncertainty,
        expected_result=expected_result,
        alternatives_considered=alternatives_considered,
        requested_permissions=requested_permissions,
        predicted_state_transition=predicted_state_transition,
        rationale_public=rationale_public,
        prior_receipt_hash=str(context.get("receipt_hash") or ""),
        turn_id=turn_id,
        invocation_id=invocation_id,
        case_id=case_id,
        context_receipt_hash=str(context.get("receipt_hash") or ""),
        interconnect_frame_hash=str(frame.get("receipt_hash") or ""),
    )
    frame_bind = frame_compatible_with_proposal(frame, proposal)
    if last_turn_payload and last_turn_payload.get("cortex_context"):
        context_delta = build_context_delta(
            prior_context=dict(last_turn_payload.get("cortex_context") or {}),
            next_context=context,
            prior_frame=dict(last_turn_payload.get("interconnect_frame") or {}),
            next_frame=frame,
            outcome=dict(last_turn_payload.get("outcome") or {}),
        )
    if transition and last_turn_payload.get("interconnect_frame"):
        distillation_batch = extract_distillation_candidates(
            prior_frame=dict(last_turn_payload.get("interconnect_frame") or {}),
            next_frame=frame,
            transition=transition,
            outcome=dict(last_turn_payload.get("outcome") or {}),
            proposal=dict(last_turn_payload.get("agent_proposal") or {}),
            evaluation=dict(last_turn_payload.get("cortex_evaluation") or {}),
            joint_action=dict(last_turn_payload.get("joint_action") or {}),
            context_delta=context_delta or {},
        )
    measured_gates = measure_evaluation_gates(
        store, repo, proposal=proposal, context=context
    )
    if not frame_bind.get("compatible"):
        # Frame/proposal identity mismatch cannot open a gate.
        gate_states = dict(measured_gates.get("gate_states") or {})
        gate_states["context_bound"] = GATE_FAIL
        measured_gates = {**measured_gates, "gate_states": gate_states}
    # Incomplete measurement frame should not open gates either.
    if str((frame.get("validity") or {}).get("measurement_state") or "") == GATE_UNKNOWN:
        gate_states = dict(measured_gates.get("gate_states") or {})
        if gate_states.get("measurement_complete") == GATE_PASS:
            gate_states["measurement_complete"] = GATE_UNKNOWN
            measured_gates = {**measured_gates, "gate_states": gate_states}
    evaluation_panel = evaluate_proposal(
        proposal=proposal,
        context=context,
        gate_states=measured_gates.get("gate_states"),
        blast_radius=str(measured_gates["blast_radius"]),
        measurement_sources=measured_gates.get("measurement_sources"),
    )
    evaluation = cortex_evaluation_receipt(
        repo=str(session_body.get("repo") or repo),
        repository_id=str(session_body.get("repository_id") or ""),
        session_id=str(session_body.get("session_id") or ""),
        body_epoch_id=str(session_body.get("body_epoch_id") or ""),
        proposal=proposal,
        evaluation=evaluation_panel,
        context_receipt_hash=str(context.get("receipt_hash") or ""),
        prior_receipt_hash=proposal["receipt_hash"],
        turn_id=turn_id,
        invocation_id=invocation_id,
        case_id=case_id,
    )
    receipts = dict(session_body.get("receipts") or {})
    receipts["cortex_context"] = context
    receipts["interconnect_frame"] = frame
    receipts["agent_proposal"] = proposal
    receipts["cortex_evaluation"] = evaluation
    turn_receipts = {
        "turn_id": turn_id,
        "case_id": case_id,
        "interconnect_frame": frame,
        "cortex_context": context,
        "agent_proposal": proposal,
        "cortex_evaluation": evaluation,
        "frame_proposal_compatible": frame_bind,
        "interconnect_transition": transition,
        "context_delta": context_delta,
        "distillation_candidates": distillation_batch,
    }
    turns[str(turn_id)] = turn_receipts
    if transition:
        receipts["interconnect_transition"] = transition
    if context_delta:
        receipts["context_delta"] = context_delta
    if distillation_batch:
        receipts["distillation_candidates"] = distillation_batch
    chain = list(session_body.get("chain") or [])
    chain.extend(
        [
            frame["receipt_hash"],
            context["receipt_hash"],
            proposal["receipt_hash"],
            evaluation["receipt_hash"],
        ]
    )
    if transition:
        chain.append(transition["receipt_hash"])
    if distillation_batch:
        chain.append(distillation_batch["receipt_hash"])
    session_body.update(
        {
            "receipts": receipts,
            "turns": turns,
            "chain": chain,
            "current_turn_id": turn_id,
            "turn_count": int(session_body.get("turn_count") or 0) + 1,
            "status": f"evaluated:{evaluation['decision']}",
            "latest_decision": evaluation["decision"],
            "latest_frame_id": frame.get("frame_id"),
            "latest_frame_overall_state": (frame.get("validity") or {}).get(
                "overall_state"
            ),
            "latest_transition_class": (transition or {}).get("transition_class"),
            "latest_distillation_count": (distillation_batch or {}).get(
                "candidate_count"
            ),
            "latest_distillation_status": (distillation_batch or {}).get(
                "extraction_status"
            ),
            "epoch_verified": measured_gates.get("gate_states", {}).get("epoch_current")
            == GATE_PASS,
            "updated_at": time.time(),
        }
    )
    if persist:
        _ledger_commit_receipts(
            store, repo, [frame, context, proposal, evaluation]
        )
        try:
            store.append_interconnect_frame(repo, dict(frame))
        except Exception:
            pass
        if transition:
            try:
                store.append_interconnect_transition(repo, dict(transition))
            except Exception:
                pass
        if distillation_batch:
            try:
                store.append_distillation_candidate_batch(
                    repo, dict(distillation_batch)
                )
            except Exception:
                pass
        _persist_session(store, repo, session_body)
    return session_body


def record_joint_action(
    store: Any,
    repo: str,
    session: Mapping[str, Any],
    *,
    tool_action: Mapping[str, Any] | None = None,
    measured_result: Mapping[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    session_body = dict(session)
    receipts = dict(session_body.get("receipts") or {})
    proposal = dict(receipts.get("agent_proposal") or {})
    evaluation = dict(receipts.get("cortex_evaluation") or {})
    turn_id = int(
        proposal.get("turn_id")
        or evaluation.get("turn_id")
        or session_body.get("current_turn_id")
        or 1
    )
    joint = joint_action_receipt(
        repo=str(session_body.get("repo") or repo),
        repository_id=str(session_body.get("repository_id") or ""),
        session_id=str(session_body.get("session_id") or ""),
        body_epoch_id=str(session_body.get("body_epoch_id") or ""),
        proposal=proposal,
        evaluation=evaluation,
        tool_action=tool_action,
        measured_result=measured_result,
        prior_receipt_hash=str(evaluation.get("receipt_hash") or ""),
        turn_id=turn_id,
        invocation_id=str(session_body.get("invocation_id") or ""),
        case_id=str(proposal.get("case_id") or ""),
    )
    receipts["joint_action"] = joint
    turns = dict(session_body.get("turns") or {})
    turn_bucket = dict(turns.get(str(turn_id)) or {})
    turn_bucket["joint_action"] = joint
    turns[str(turn_id)] = turn_bucket
    chain = list(session_body.get("chain") or [])
    chain.append(joint["receipt_hash"])
    session_body.update(
        {
            "receipts": receipts,
            "turns": turns,
            "chain": chain,
            "status": joint["binding_status"],
            "updated_at": time.time(),
        }
    )
    if persist:
        _ledger_commit_receipts(store, repo, [joint])
        _persist_session(store, repo, session_body)
    return session_body


def record_outcome(
    store: Any,
    repo: str,
    session: Mapping[str, Any],
    *,
    success: bool | None = None,
    metrics: Mapping[str, Any] | None = None,
    outcome_kind: str = "task_result",
    external_reference: str | None = None,
    witness: Mapping[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Append a typed, independently witnessed outcome receipt."""
    session_body = dict(session)
    receipts = dict(session_body.get("receipts") or {})
    joint = dict(receipts.get("joint_action") or {})
    turn_id = int(joint.get("turn_id") or session_body.get("current_turn_id") or 1)
    outcome = outcome_receipt(
        repo=str(session_body.get("repo") or repo),
        repository_id=str(session_body.get("repository_id") or ""),
        session_id=str(session_body.get("session_id") or ""),
        body_epoch_id=str(session_body.get("body_epoch_id") or ""),
        joint_action=joint or None,
        outcome_kind=outcome_kind,
        success=success,
        metrics=metrics,
        external_reference=external_reference,
        witness=witness,
        prior_receipt_hash=str(joint.get("receipt_hash") or ""),
        turn_id=turn_id,
        invocation_id=str(session_body.get("invocation_id") or ""),
        case_id=str(joint.get("case_id") or ""),
    )
    receipts["outcome"] = outcome
    turns = dict(session_body.get("turns") or {})
    turn_bucket = dict(turns.get(str(turn_id)) or {})
    turn_bucket["outcome"] = outcome
    turns[str(turn_id)] = turn_bucket
    chain = list(session_body.get("chain") or [])
    chain.append(outcome["receipt_hash"])
    session_body.update(
        {
            "receipts": receipts,
            "turns": turns,
            "chain": chain,
            "status": f"outcome:{outcome['status']}",
            "updated_at": time.time(),
        }
    )
    if persist:
        _ledger_commit_receipts(store, repo, [outcome])
        _persist_session(store, repo, session_body)
    return session_body


def consolidate_session(
    store: Any,
    repo: str,
    session: Mapping[str, Any],
    *,
    candidates: Sequence[Mapping[str, Any]] | None = None,
    constitutional_gate: bool = False,
    epoch_compatible: bool | None = None,
    witness_present: bool | None = None,
    outcome_closed: bool | None = None,
    stable_regime: bool | None = None,
    will: Mapping[str, Any] | None = None,
    will_secret: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    from .admitted_memory import commit_admitted_memories
    from .distillation_candidates import (
        extract_session_distillation_candidates,
        flatten_candidates,
    )
    from .membrane import apply_will_bound_membrane

    session_body = dict(session)
    receipts = dict(session_body.get("receipts") or {})
    joint = dict(receipts.get("joint_action") or {})
    outcome = dict(receipts.get("outcome") or {})
    # Prefer explicit candidates; otherwise flatten trajectory-derived batches.
    batches: list[dict[str, Any]] = []
    if candidates is None:
        batches = extract_session_distillation_candidates(session_body)
        candidates = flatten_candidates(batches)
        if batches:
            receipts["distillation_candidate_batches"] = batches
    measured = measure_evaluation_gates(
        store,
        repo,
        proposal={
            "body_epoch_id": session_body.get("body_epoch_id"),
            "session_id": session_body.get("session_id"),
            "receipt_hash": "consolidation",
            "interpreted_objective": "consolidate",
            "proposed_action": "retain",
        },
        context=receipts.get("cortex_context"),
    )
    gate_states = dict(measured.get("gate_states") or {})
    if epoch_compatible is None:
        epoch_compatible = gate_states.get("epoch_current") == GATE_PASS
    if witness_present is None:
        witness_present = bool(outcome.get("witnessed"))
    if outcome_closed is None:
        outcome_closed = bool(outcome.get("closed"))
    sources = dict(measured.get("measurement_sources") or {})
    sensing = str(sources.get("self_sensing") or "").upper()
    binding = str(sources.get("binding") or "").upper()
    if stable_regime is None:
        # Tri-state stability: absence of evidence is unknown, not pass.
        if sensing in {"STRESSED", "UNBOUND"} or binding == "DRIFT_REGIME":
            stable_regime = False
            stability_state = GATE_FAIL
        elif not sensing and not binding:
            stable_regime = False
            stability_state = GATE_UNKNOWN
        else:
            stable_regime = True
            stability_state = GATE_PASS
    else:
        stability_state = GATE_PASS if stable_regime else GATE_FAIL
    # Canonical retention requires every factor; unknown stability blocks it.
    if stability_state != GATE_PASS:
        stable_regime = False

    membrane = None
    consolidation_candidates: list[dict[str, Any]] = [
        dict(c) for c in (candidates or ()) if isinstance(c, Mapping)
    ]
    # Will-bound membrane: only path that may set retain=true on candidates.
    if will is not None and will_secret:
        seal_turn_for_membrane = int(session_body.get("current_turn_id") or 0)
        membrane = apply_will_bound_membrane(
            store,
            repo,
            will=will,
            will_secret=will_secret,
            candidates=consolidation_candidates,
            batches=batches,
            constitutional_gate=bool(constitutional_gate),
            epoch_compatible=bool(epoch_compatible),
            witness_present=bool(witness_present),
            outcome_closed=bool(outcome_closed),
            stable_regime=bool(stable_regime),
            session_id=str(session_body.get("session_id") or "") or None,
            body_epoch_id=str(session_body.get("body_epoch_id") or "") or None,
            turn_id=seal_turn_for_membrane,
            persist=persist,
        )
        # Feed admitted (retain=true) + rejected/deferred into consolidation.
        consolidation_candidates = list(membrane.get("admitted") or [])
        consolidation_candidates.extend(membrane.get("rejected") or [])
        consolidation_candidates.extend(membrane.get("deferred") or [])
        receipts["will_root"] = dict(will)
        receipts["distillation_membrane_admission"] = membrane

    memory_commit = None
    if membrane is not None and will is not None:
        memory_commit = commit_admitted_memories(
            store,
            repo,
            admission=membrane,
            will=will,
            session=session_body,
            persist=persist,
        )
        receipts["admitted_memory_commit"] = memory_commit

    prior = str(outcome.get("receipt_hash") or joint.get("receipt_hash") or "")
    seal_turn = int(session_body.get("current_turn_id") or 0)
    consolidation = symbiotic_consolidation_receipt(
        repo=str(session_body.get("repo") or repo),
        repository_id=str(session_body.get("repository_id") or ""),
        session_id=str(session_body.get("session_id") or ""),
        body_epoch_id=str(session_body.get("body_epoch_id") or ""),
        joint_action=joint or None,
        candidates=consolidation_candidates,
        constitutional_gate=constitutional_gate,
        epoch_compatible=bool(epoch_compatible),
        witness_present=bool(witness_present),
        outcome_closed=bool(outcome_closed),
        stable_regime=bool(stable_regime),
        prior_receipt_hash=prior,
        turn_id=seal_turn,
        invocation_id=str(session_body.get("invocation_id") or ""),
        case_id=f"case_{session_body.get('session_id')}_seal",
    )
    consolidation["gate_states"] = {
        **gate_states,
        "stability": stability_state,
        "witness": GATE_PASS if witness_present else GATE_FAIL,
        "outcome_closure": GATE_PASS if outcome_closed else GATE_FAIL,
        "epoch_compatible": GATE_PASS if epoch_compatible else GATE_FAIL,
        "constitutional": GATE_PASS if constitutional_gate else GATE_FAIL,
        "will_verified": (
            GATE_PASS
            if membrane and membrane.get("will_verified")
            else GATE_UNKNOWN
            if will is None
            else GATE_FAIL
        ),
        "membrane": (
            GATE_PASS
            if membrane and membrane.get("durable_write_authorized")
            else GATE_UNKNOWN
            if membrane is None
            else GATE_FAIL
        ),
    }
    if membrane is not None:
        consolidation["membrane_receipt_hash"] = membrane.get("receipt_hash")
        consolidation["will_receipt_hash"] = will.get("receipt_hash") if will else None
        consolidation["invented_count"] = membrane.get("invented_count", 0)
    if memory_commit is not None:
        consolidation["admitted_memory_commit_hash"] = memory_commit.get("receipt_hash")
        consolidation["admitted_memory_count"] = memory_commit.get("committed_count")
    receipts["symbiotic_consolidation"] = consolidation
    chain = list(session_body.get("chain") or [])
    if will and will.get("receipt_hash"):
        chain.append(str(will["receipt_hash"]))
    if membrane:
        chain.append(membrane["receipt_hash"])
    if memory_commit and memory_commit.get("receipt_hash"):
        chain.append(str(memory_commit["receipt_hash"]))
    chain.append(consolidation["receipt_hash"])
    durable = bool(membrane and membrane.get("durable_write_authorized"))
    memories_written = int((memory_commit or {}).get("committed_count") or 0)
    session_body.update(
        {
            "receipts": receipts,
            "chain": chain,
            "status": "consolidated",
            "closed_at": time.time(),
            "updated_at": time.time(),
            "adaptation_authorized": False,
            # Durable write only when membrane admitted under will ∧ gates.
            "durable_write_authorized": durable,
            "memory_write_authorized": durable,
            "admitted_memory_count": memories_written,
            "host_mutate_authorized": False,
            "execution_authorized": False,
        }
    )
    if persist:
        # Membrane has its own immutable ledger; keep symbiotic ledger on
        # consolidation only (exactly-once per session/turn/kind).
        try:
            _ledger_commit_receipts(store, repo, [consolidation])
        except Exception:
            pass
        _persist_session(store, repo, session_body)
    return session_body


def _ledger_commit_receipts(
    store: Any, repo: str, receipts: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Append scientific receipts into the canonical SQLite ledger."""
    committed: list[dict[str, Any]] = []
    for receipt in receipts:
        if not isinstance(receipt, Mapping) or not receipt.get("kind"):
            continue
        committed.append(store.append_symbiotic_receipt(repo, dict(receipt)))
    return committed


def _persist_session(store: Any, repo: str, session: Mapping[str, Any]) -> None:
    store.set_setting(f"symbiosis_latest:{repo}", dict(session))
    history = list(store.get_setting(f"symbiosis_history:{repo}", []) or [])
    history.append(
        {
            "session_id": session.get("session_id"),
            "status": session.get("status"),
            "chain_tip": (session.get("chain") or [None])[-1],
            "decision": session.get("latest_decision"),
            "updated_at": session.get("updated_at") or session.get("opened_at"),
        }
    )
    store.set_setting(f"symbiosis_history:{repo}", history[-32:])


def symbiotic_status(store: Any, repo: str) -> dict[str, Any]:
    latest = store.get_setting(f"symbiosis_latest:{repo}", None)
    history = store.get_setting(f"symbiosis_history:{repo}", []) or []
    if not latest:
        return {
            "schema_version": SCHEMA,
            "version": VERSION,
            "glyph": GLYPH,
            "repo": repo,
            "status": "cold",
            "session_count": len(history),
            "advisory_only": True,
            "policy_effect": False,
            "update_authorized": False,
            "claim_boundary": CLAIM_BOUNDARY,
            "symbiosis": {
                "ai_supplies": "adaptive cognition",
                "cortex_supplies": "persistent identity and disciplined memory",
            },
            "next_actions": [
                "open_symbiotic_session",
                "record_proposal",
                "evaluate_fail_closed",
                "record_joint_action",
                "record_witnessed_outcome",
                "consolidate_only_when_gates_open",
            ],
        }
    receipts = dict(latest.get("receipts") or {})
    present = sorted(receipts)
    missing = [kind for kind in RECEIPT_KINDS if kind not in receipts]
    session_id = str(latest.get("session_id") or "")
    try:
        ledger = store.verify_symbiotic_session(repo, session_id) if session_id else {
            "valid": False,
            "errors": ["session_missing"],
        }
        ledger_rows = (
            store.symbiotic_session_receipts(repo, session_id) if session_id else []
        )
    except Exception as exc:
        ledger = {"valid": False, "errors": [f"{type(exc).__name__}:{exc}"]}
        ledger_rows = []
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "repo": repo,
        "status": latest.get("status") or "open",
        "session_id": latest.get("session_id"),
        "body_epoch_id": latest.get("body_epoch_id"),
        "latest_decision": latest.get("latest_decision"),
        "receipts_present": present,
        "receipts_missing": missing,
        "chain_length": len(latest.get("chain") or []),
        "chain_tip": (latest.get("chain") or [None])[-1],
        "ledger": {
            "valid": bool(ledger.get("valid")),
            "receipt_count": ledger.get("receipt_count") or len(ledger_rows),
            "tip_receipt_hash": ledger.get("tip_receipt_hash"),
            "errors": list(ledger.get("errors") or ()),
            "kinds": [row.get("kind") for row in ledger_rows],
        },
        "complementarity": latest.get("complementarity")
        or complementarity_surplus(),
        "session_count": len(
            {
                str(item.get("session_id") or "")
                for item in history
                if item.get("session_id")
            }
        ),
        "history_transition_count": len(history),
        "turn_count": latest.get("turn_count") or 0,
        "timescale": latest.get("timescale"),
        "symbiosis": latest.get("symbiosis"),
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_session_circulation(store: Any, repo: str, session_id: str) -> dict[str, Any]:
    """Independent verification of the canonical session receipt chain.

    Structural checks are grouped by turn so recurrent proposals/evaluations
    cannot collapse into one dictionary entry per kind.
    """
    chain = store.verify_symbiotic_session(repo, session_id)
    rows = store.symbiotic_session_receipts(repo, session_id)
    by_turn: dict[int, dict[str, dict[str, Any]]] = {}
    for row in rows:
        turn = int(row.get("turn_id") or 0)
        kind = str(row.get("kind") or "")
        by_turn.setdefault(turn, {})[kind] = row

    open_kinds = by_turn.get(0, {})
    structural = {
        "has_instantiation": "agent_instantiation" in open_kinds,
        "has_context": "cortex_context" in open_kinds
        or any("cortex_context" in kinds for kinds in by_turn.values()),
        "turns": [],
        "all_turns_well_ordered": True,
        "outcome_witnessed_any": False,
    }
    for turn_id in sorted(t for t in by_turn if t >= 1):
        kinds = by_turn[turn_id]
        seq = {
            kind: int((kinds.get(kind) or {}).get("chain_sequence") or 0)
            for kind in (
                "cortex_context",
                "interconnect_frame",
                "agent_proposal",
                "cortex_evaluation",
                "joint_action",
                "outcome",
            )
            if kind in kinds
        }
        proposal_seq = seq.get("agent_proposal")
        evaluation_seq = seq.get("cortex_evaluation")
        action_seq = seq.get("joint_action")
        outcome_seq = seq.get("outcome")
        ordered = True
        if proposal_seq is not None and evaluation_seq is not None:
            ordered = ordered and proposal_seq < evaluation_seq
        if evaluation_seq is not None and action_seq is not None:
            ordered = ordered and evaluation_seq < action_seq
        if action_seq is not None and outcome_seq is not None:
            ordered = ordered and action_seq < outcome_seq
        if not ordered:
            structural["all_turns_well_ordered"] = False
        witnessed = bool((kinds.get("outcome") or {}).get("witnessed"))
        if witnessed:
            structural["outcome_witnessed_any"] = True
        structural["turns"].append(
            {
                "turn_id": turn_id,
                "kinds": sorted(kinds),
                "well_ordered": ordered,
                "outcome_witnessed": witnessed,
                "sequences": seq,
            }
        )
    structural["proposal_before_evaluation"] = structural["all_turns_well_ordered"]
    structural["outcome_witnessed"] = structural["outcome_witnessed_any"]
    structural_valid = bool(
        structural["has_instantiation"]
        and structural["has_context"]
        and structural["all_turns_well_ordered"]
    )
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "repo": repo,
        "session_id": session_id,
        "chain": chain,
        "structural": structural,
        "receipt_count": len(rows),
        "turn_count": len([t for t in by_turn if t >= 1]),
        "valid": bool(chain.get("valid")) and structural_valid,
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def reconstruct_next_session_brief(store: Any, repo: str) -> dict[str, Any]:
    """Reconstruct the cognitive environment for the next model invocation."""
    status = symbiotic_status(store, repo)
    latest = store.get_setting(f"symbiosis_latest:{repo}", None) or {}
    receipts = dict(latest.get("receipts") or {})
    context = dict(receipts.get("cortex_context") or {})
    proposal = dict(receipts.get("agent_proposal") or {})
    evaluation = dict(receipts.get("cortex_evaluation") or {})
    consolidation = dict(receipts.get("symbiotic_consolidation") or {})
    outcome = dict(receipts.get("outcome") or {})
    distill_batch = dict(receipts.get("distillation_candidates") or {})
    distill_candidates = list(distill_batch.get("candidates") or ())
    brief = {
        "schema_version": "cortex-symbiosis-next-session/1.2",
        "repo": repo,
        "what_the_project_is": {
            "repository_id": latest.get("repository_id"),
            "body_epoch_id": latest.get("body_epoch_id"),
        },
        "what_changed": {
            "joint_action": (receipts.get("joint_action") or {}).get("binding_status"),
            "measured_result": (receipts.get("joint_action") or {}).get(
                "measured_result"
            ),
            "transition_class": (
                receipts.get("interconnect_transition") or {}
            ).get("transition_class"),
        },
        "what_is_currently_believed": {
            "operating_regime": context.get("operating_regime"),
            "retained": consolidation.get("retained") or [],
            "distillation_candidates": distill_candidates,
            "distillation_by_type": distill_batch.get("by_type") or {},
            "admitted_memories": (
                ((receipts.get("admitted_memory_commit") or {}).get("committed"))
                or []
            ),
            "admitted_memory_count": (
                (receipts.get("admitted_memory_commit") or {}).get("committed_count")
                or latest.get("admitted_memory_count")
                or 0
            ),
        },
        "why_it_is_believed": {
            "context_packet_digest": context.get("context_packet_digest"),
            "interconnect_frame_hash": context.get("interconnect_frame_hash"),
            "gates": consolidation.get("gates") or evaluation.get("gates"),
            "distillation_support_ceiling": distill_batch.get("support_ceiling"),
            "distillation_extraction_status": distill_batch.get("extraction_status"),
        },
        "assumptions": {
            bucket: []
            for bucket in (
                "assumptions_disconfirmed",
                "assumptions_unverified",
                "assumptions_blocked",
                "assumptions_supported",
            )
        },
        "unresolved_questions": list(context.get("unresolved_contradictions") or ()),
        "forbidden_actions": list(
            (receipts.get("agent_instantiation") or {}).get("forbidden_operations")
            or ()
        ),
        "evidence_that_would_change_conclusion": [
            "current_epoch_witness",
            "independent_outcome_closure",
            "measurement_complete_transition",
            "stable_regime_with_complementarity",
        ],
        "prior_decision": evaluation.get("decision"),
        "turn_count": latest.get("turn_count") or 0,
        "current_turn_id": latest.get("current_turn_id"),
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "status": status.get("status"),
    }
    for assumption in list(proposal.get("assumptions") or ()):
        bucket = classify_assumption_status(
            evaluation_decision=str(evaluation.get("decision") or ""),
            outcome_success=outcome.get("success") if outcome else None,
            assumption=str(assumption),
        )
        brief["assumptions"][bucket].append(assumption)
    # Backward-compatible alias: never treat blocked/unverified as failed.
    brief["which_assumptions_failed"] = list(
        brief["assumptions"]["assumptions_disconfirmed"]
    )
    return brief


__all__ = [
    "CLAIM_BOUNDARY",
    "CONSOLIDATION_KINDS",
    "EVALUATION_DECISIONS",
    "GATE_FAIL",
    "GATE_PASS",
    "GATE_UNKNOWN",
    "GLYPH",
    "RECEIPT_KINDS",
    "SCHEMA",
    "VERSION",
    "agent_instantiation_receipt",
    "agent_proposal_receipt",
    "classify_assumption_status",
    "complementarity_surplus",
    "consolidate_session",
    "cortex_context_receipt",
    "cortex_evaluation_receipt",
    "evaluate_proposal",
    "joint_action_receipt",
    "measure_evaluation_gates",
    "open_symbiotic_session",
    "outcome_receipt",
    "record_joint_action",
    "record_outcome",
    "record_proposal",
    "reconstruct_next_session_brief",
    "symbiotic_consolidation_receipt",
    "symbiotic_status",
    "verify_session_circulation",
]
