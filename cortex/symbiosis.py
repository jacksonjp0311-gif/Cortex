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

SCHEMA = "cortex-symbiosis/1.1"
GLYPH = "☍"
VERSION = "8.4.1"
CLAIM_BOUNDARY = (
    "AI–Cortex symbiotic circulation is a typed two-timescale ledger: the model "
    "proposes meaning; Cortex preserves tested continuity. Receipts are advisory "
    "provenance under independent verification — not consciousness, host authority, "
    "or automatic learning."
)

EVALUATION_DECISIONS = frozenset(
    {"allow", "constrain", "ask", "abstain", "hold"}
)
CONSOLIDATION_KINDS = frozenset(
    {
        "verified_fact",
        "successful_procedure",
        "failed_hypothesis",
        "useful_route",
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
    "agent_proposal",
    "cortex_evaluation",
    "joint_action",
    "outcome",
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


def _base(
    *,
    kind: str,
    repo: str,
    repository_id: str,
    session_id: str,
    body_epoch_id: str,
    prior_receipt_hash: str | None = None,
    **fields: Any,
) -> dict[str, Any]:
    material = {
        "kind": kind,
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
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
) -> dict[str, Any]:
    """Identify one bounded model instantiation — not a persistent self."""
    return _base(
        kind="agent_instantiation",
        repo=repo,
        repository_id=repository_id,
        session_id=session_id,
        body_epoch_id=body_epoch_id,
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
    )


def measure_evaluation_gates(
    store: Any,
    repo: str,
    *,
    proposal: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind evaluation gates to live Cortex measurements — not constants."""
    from .epoch import observe_current_epoch

    epoch = observe_current_epoch(store, repo)
    epoch_current = bool(
        epoch.get("present")
        and epoch.get("verified")
        and str(proposal.get("body_epoch_id") or "")
        and str(proposal.get("body_epoch_id") or "")
        == str(epoch.get("epoch_id") or epoch.get("live_epoch_id") or "")
    )
    measured = store.get_setting(f"measured_event_latest:{repo}", {}) or {}
    measurement_complete = bool(
        isinstance(measured, Mapping)
        and (
            measured.get("status") == "measured"
            or float(measured.get("valid_fraction") or 0.0) == 1.0
        )
    )
    residual = store.get_setting(f"ostt_residual_latest:{repo}", {}) or {}
    try:
        latest_conformance = store.latest_activation_conformance_receipt(repo)
    except Exception:
        latest_conformance = None
    if latest_conformance is None and isinstance(residual, Mapping):
        latest_conformance = residual if residual.get("status") else None
    operator_contract_ready = bool(
        isinstance(latest_conformance, Mapping)
        and str(latest_conformance.get("status") or "")
        in {"conformance_measured", "measured", "conformance_ready"}
    )
    try:
        outcome_row = store.db.execute(
            "SELECT COUNT(*) AS n FROM task_outcomes WHERE repo=?",
            (repo,),
        ).fetchone()
        outcome_count = int(outcome_row["n"]) if outcome_row else 0
    except Exception:
        outcome_count = 0
    outcome_history_ready = outcome_count > 0

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
    invariants_ok = bool(
        epoch_current
        and sensing not in {"STRESSED", "UNBOUND"}
        and binding_class not in {"DRIFT_REGIME"}
        and (
            not interlock
            or interlock.get("data_ready") is True
            or interlock.get("status") not in {"blocked", "failed"}
        )
    )
    # Host immutability: prefer activation-conformance host projection when present.
    host_immutable = True
    if isinstance(latest_conformance, Mapping):
        invariants = latest_conformance.get("invariant_results") or []
        if isinstance(invariants, list):
            for item in invariants:
                if (
                    isinstance(item, Mapping)
                    and item.get("invariant_id") == "host_immutable"
                ):
                    host_immutable = item.get("passed") is True
                    break
    authority_scope_ok = True
    blast_radius = "bounded"
    if sensing in {"STRESSED", "UNBOUND"} or binding_class == "DRIFT_REGIME":
        blast_radius = "high"
    if str(resonance.get("status") or "") == "no_stable_peak":
        # Temporal instability widens risk without inventing authority.
        if blast_radius == "bounded":
            blast_radius = "elevated"
    context_bound = bool(
        context is None
        or (
            context.get("session_id") == proposal.get("session_id")
            and context.get("body_epoch_id") == proposal.get("body_epoch_id")
        )
    )
    sources = {
        "epoch": {
            "verified": bool(epoch.get("verified")),
            "epoch_id": epoch.get("epoch_id") or epoch.get("live_epoch_id"),
        },
        "measured_event": {
            "status": measured.get("status") if isinstance(measured, Mapping) else None,
            "valid_fraction": measured.get("valid_fraction")
            if isinstance(measured, Mapping)
            else None,
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
    return {
        "epoch_current": epoch_current,
        "host_immutable": host_immutable,
        "invariants_ok": invariants_ok,
        "authority_scope_ok": authority_scope_ok,
        "blast_radius": blast_radius,
        "outcome_history_ready": outcome_history_ready,
        "operator_contract_ready": operator_contract_ready,
        "measurement_complete": measurement_complete,
        "context_bound": context_bound,
        "measurement_sources": sources,
    }


def evaluate_proposal(
    *,
    proposal: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
    epoch_current: bool = False,
    host_immutable: bool = True,
    invariants_ok: bool = False,
    authority_scope_ok: bool = True,
    blast_radius: str = "unknown",
    outcome_history_ready: bool = False,
    operator_contract_ready: bool = False,
    measurement_complete: bool = False,
    forced_decision: str | None = None,
    measurement_sources: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Cortex evaluation of an AI proposal against durable constraints.

    Returns one of: allow, constrain, ask, abstain, hold.
    Default is fail-closed: missing gates produce hold/abstain, never silent allow.
    """
    gates = {
        "proposal_present": bool(proposal.get("receipt_hash")),
        "objective_declared": bool(str(proposal.get("interpreted_objective") or "").strip()),
        "action_declared": bool(str(proposal.get("proposed_action") or "").strip()),
        "epoch_current": bool(epoch_current),
        "host_immutable": bool(host_immutable),
        "invariants_ok": bool(invariants_ok),
        "authority_scope_ok": bool(authority_scope_ok),
        "outcome_history_ready": bool(outcome_history_ready),
        "operator_contract_ready": bool(operator_contract_ready),
        "measurement_complete": bool(measurement_complete),
        "context_bound": bool(
            context is None
            or (
                context.get("session_id") == proposal.get("session_id")
                and context.get("body_epoch_id") == proposal.get("body_epoch_id")
            )
        ),
    }
    missing = [name for name, passed in gates.items() if not passed]
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
    elif elevated or not gates["authority_scope_ok"]:
        decision = "hold"
        reason = "authority_or_forbidden_permission"
    elif not gates["proposal_present"] or not gates["action_declared"]:
        decision = "abstain"
        reason = "proposal_incomplete"
    elif not gates["epoch_current"] or not gates["context_bound"]:
        decision = "hold"
        reason = "epoch_or_context_not_current"
    elif not gates["host_immutable"]:
        decision = "hold"
        reason = "host_mutation_detected"
    elif not citations:
        decision = "ask"
        reason = "evidence_citations_required"
    elif uncertainty >= 0.75:
        decision = "ask"
        reason = "declared_uncertainty_high"
    elif not gates["invariants_ok"] or not gates["measurement_complete"]:
        decision = "constrain"
        reason = "invariants_or_measurement_incomplete"
    elif blast_radius in {"high", "unbounded", "elevated"}:
        decision = "constrain"
        reason = f"blast_radius:{blast_radius}"
    elif not gates["outcome_history_ready"] or not gates["operator_contract_ready"]:
        decision = "constrain"
        reason = "history_or_contract_incomplete"
    else:
        decision = "allow"
        reason = "gates_satisfied_for_bounded_review"

    # Allow never means automatic execution authority.
    return {
        "decision": decision,
        "reason": reason,
        "gates": gates,
        "missing_gates": missing,
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
) -> dict[str, Any]:
    """Typed outcome with independent MEASUREMENT-or-OUTCOME witness material.

    The witness must cover the outcome subject; a missing or failed witness
    yields ``witnessed=false`` and cannot authorize consolidation.
    """
    subject = {
        "outcome_kind": str(outcome_kind or "task_result"),
        "success": success,
        "metrics": dict(metrics or {}),
        "external_reference": external_reference,
        "joint_action_receipt_hash": str((joint_action or {}).get("receipt_hash") or ""),
        "session_id": session_id,
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
                if str(resonance.get("status") or "") not in {"resonant_candidate", ""}
                and resonance
                else None,
            )
            if item
        ],
        operating_regime={
            "self_sensing": (self_sensing.get("status") if isinstance(self_sensing, Mapping) else None),
            "resonance": resonance.get("status"),
            "geometric_field": geometric.get("field_condition"),
            "residual": (residual or {}).get("status") if isinstance(residual, Mapping) else None,
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
    )
    # Re-link context after instantiation so the chain starts at the agent seat.
    context = {
        **context,
        "prior_receipt_hash": instantiation["receipt_hash"],
        "receipt_hash": _sha(
            {
                **{
                    key: value
                    for key, value in context.items()
                    if key
                    not in {
                        "receipt_hash",
                        "created_at",
                        "prior_receipt_hash",
                    }
                },
                "prior_receipt_hash": instantiation["receipt_hash"],
            }
        ),
    }

    session = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "repo": repo,
        "repository_id": repository_id,
        "session_id": session_id,
        "task": task,
        "task_hash": _sha(task),
        "body_epoch_id": body_epoch_id,
        "epoch_verified": bool(epoch.get("verified")),
        "timescale": {
            "q_t": "AI temporary working state",
            "c_t": "Cortex durable state",
            "law": "|Δq| ≫ |Δc|; Δc=0 when Γ Ξ W O S = 0",
        },
        "symbiosis": {
            "ai_supplies": "adaptive cognition",
            "cortex_supplies": "persistent identity and disciplined memory",
            "neither_complete_alone": True,
        },
        "receipts": {
            "agent_instantiation": instantiation,
            "cortex_context": context,
        },
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
    """Append a proposal, evaluate it, and return the updated session."""
    session_body = dict(session)
    context = dict((session_body.get("receipts") or {}).get("cortex_context") or {})
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
    )
    measured_gates = measure_evaluation_gates(
        store, repo, proposal=proposal, context=context
    )
    evaluation_panel = evaluate_proposal(
        proposal=proposal,
        context=context,
        epoch_current=bool(measured_gates["epoch_current"]),
        host_immutable=bool(measured_gates["host_immutable"]),
        invariants_ok=bool(measured_gates["invariants_ok"]),
        authority_scope_ok=bool(measured_gates["authority_scope_ok"]),
        blast_radius=str(measured_gates["blast_radius"]),
        outcome_history_ready=bool(measured_gates["outcome_history_ready"]),
        operator_contract_ready=bool(measured_gates["operator_contract_ready"]),
        measurement_complete=bool(measured_gates["measurement_complete"]),
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
    )
    receipts = dict(session_body.get("receipts") or {})
    receipts["agent_proposal"] = proposal
    receipts["cortex_evaluation"] = evaluation
    chain = list(session_body.get("chain") or [])
    chain.extend([proposal["receipt_hash"], evaluation["receipt_hash"]])
    session_body.update(
        {
            "receipts": receipts,
            "chain": chain,
            "status": f"evaluated:{evaluation['decision']}",
            "latest_decision": evaluation["decision"],
            "epoch_verified": bool(measured_gates["epoch_current"]),
            "updated_at": time.time(),
        }
    )
    if persist:
        _ledger_commit_receipts(store, repo, [proposal, evaluation])
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
    )
    receipts["joint_action"] = joint
    chain = list(session_body.get("chain") or [])
    chain.append(joint["receipt_hash"])
    session_body.update(
        {
            "receipts": receipts,
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
    )
    receipts["outcome"] = outcome
    chain = list(session_body.get("chain") or [])
    chain.append(outcome["receipt_hash"])
    session_body.update(
        {
            "receipts": receipts,
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
    persist: bool = True,
) -> dict[str, Any]:
    session_body = dict(session)
    receipts = dict(session_body.get("receipts") or {})
    joint = dict(receipts.get("joint_action") or {})
    outcome = dict(receipts.get("outcome") or {})
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
    if epoch_compatible is None:
        epoch_compatible = bool(measured["epoch_current"])
    if witness_present is None:
        witness_present = bool(outcome.get("witnessed"))
    if outcome_closed is None:
        outcome_closed = bool(outcome.get("closed"))
    if stable_regime is None:
        sensing = str(
            ((measured.get("measurement_sources") or {}).get("self_sensing") or "")
        ).upper()
        binding = str(
            ((measured.get("measurement_sources") or {}).get("binding") or "")
        ).upper()
        stable_regime = sensing not in {"STRESSED", "UNBOUND"} and binding not in {
            "DRIFT_REGIME"
        }
    prior = str(outcome.get("receipt_hash") or joint.get("receipt_hash") or "")
    consolidation = symbiotic_consolidation_receipt(
        repo=str(session_body.get("repo") or repo),
        repository_id=str(session_body.get("repository_id") or ""),
        session_id=str(session_body.get("session_id") or ""),
        body_epoch_id=str(session_body.get("body_epoch_id") or ""),
        joint_action=joint or None,
        candidates=candidates,
        constitutional_gate=constitutional_gate,
        epoch_compatible=bool(epoch_compatible),
        witness_present=bool(witness_present),
        outcome_closed=bool(outcome_closed),
        stable_regime=bool(stable_regime),
        prior_receipt_hash=prior,
    )
    receipts["symbiotic_consolidation"] = consolidation
    chain = list(session_body.get("chain") or [])
    chain.append(consolidation["receipt_hash"])
    session_body.update(
        {
            "receipts": receipts,
            "chain": chain,
            "status": "consolidated",
            "closed_at": time.time(),
            "updated_at": time.time(),
            "adaptation_authorized": False,
            "durable_write_authorized": False,
        }
    )
    if persist:
        _ledger_commit_receipts(store, repo, [consolidation])
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
        "session_count": len(history),
        "timescale": latest.get("timescale"),
        "symbiosis": latest.get("symbiosis"),
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def verify_session_circulation(store: Any, repo: str, session_id: str) -> dict[str, Any]:
    """Independent verification of the canonical session receipt chain."""
    chain = store.verify_symbiotic_session(repo, session_id)
    rows = store.symbiotic_session_receipts(repo, session_id)
    by_kind = {str(row.get("kind")): row for row in rows}
    structural = {
        "has_instantiation": "agent_instantiation" in by_kind,
        "has_context": "cortex_context" in by_kind,
        "proposal_before_evaluation": (
            "agent_proposal" not in by_kind
            or "cortex_evaluation" not in by_kind
            or int(by_kind["agent_proposal"].get("chain_sequence") or 0)
            < int(by_kind["cortex_evaluation"].get("chain_sequence") or 0)
        ),
        "outcome_witnessed": bool((by_kind.get("outcome") or {}).get("witnessed")),
    }
    return {
        "schema_version": SCHEMA,
        "version": VERSION,
        "repo": repo,
        "session_id": session_id,
        "chain": chain,
        "structural": structural,
        "receipt_count": len(rows),
        "valid": bool(chain.get("valid")),
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
    return {
        "schema_version": "cortex-symbiosis-next-session/1.0",
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
        },
        "what_is_currently_believed": {
            "operating_regime": context.get("operating_regime"),
            "retained": consolidation.get("retained") or [],
        },
        "why_it_is_believed": {
            "context_packet_digest": context.get("context_packet_digest"),
            "gates": consolidation.get("gates") or evaluation.get("gates"),
        },
        "which_assumptions_failed": list(proposal.get("assumptions") or ())
        if evaluation.get("decision") in {"hold", "abstain", "ask"}
        else [],
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
        "advisory_only": True,
        "policy_effect": False,
        "update_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "status": status.get("status"),
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "CONSOLIDATION_KINDS",
    "EVALUATION_DECISIONS",
    "GLYPH",
    "RECEIPT_KINDS",
    "SCHEMA",
    "VERSION",
    "agent_instantiation_receipt",
    "agent_proposal_receipt",
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
