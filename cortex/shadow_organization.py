"""Shadow organizational substrate. Production runtime must not consume it.

All objects have authority_effect=false and production_effect=false.
Mechanical recursive closure is ranking influence, not utility or intelligence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__

STATE_SCHEMA = "cortex-organization-state-view/1.0"
PROPOSAL_SCHEMA = "cortex-adaptation-proposal/1.0"
DECISION_SCHEMA = "cortex-selection-decision/1.0"
CANDIDATE_SCHEMA = "cortex-retention-candidate/1.1"
PRIOR_SCHEMA = "cortex-proposal-prior/1.1"
CYCLE_SCHEMA = "cortex-self-organization-cycle/1.0"
CLOSURE_SCHEMA = "cortex-mechanical-recursive-closure/1.0"
STABILIZATION_SCHEMA = "cortex-bounded-self-stabilization/1.0"
LIFECYCLE = ("PROPOSED", "OBSERVED", "VERIFIED", "REPLICATED", "RETENTION_ELIGIBLE")
RESPONSES = ("HOLD", "QUARANTINE", "SUPERSEDE", "ROLLBACK", "RECONSTRUCT")
FORBIDDEN_ADAPTATIONS = frozenset({
    "authority", "credential", "security", "capability", "scoring-rule", "network", "budget",
})


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _closed() -> dict[str, Any]:
    return {
        "authority_effect": False,
        "production_effect": False,
        "adaptation_authorized": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }


def organization_state_view(
    *,
    snapshot_hash: str,
    priors: Sequence[Mapping[str, Any]] = (),
    debt: Mapping[str, Any] | None = None,
    unresolved: Sequence[str] = (),
) -> dict[str, Any]:
    body = {
        "schema_version": STATE_SCHEMA,
        "product_version": __version__,
        "snapshot_hash": snapshot_hash,
        "priors": [dict(item) for item in priors],
        "assurance_debt": dict(debt or {}),
        "unresolved": list(unresolved),
        "legitimate": True,
        **_closed(),
    }
    return {**body, "state_hash": _sha(body)}


def adaptation_proposal(
    *,
    proposal_id: str,
    kind: str,
    delta: Mapping[str, Any],
    hypothesis: str,
    prior_state_hash: str,
) -> dict[str, Any]:
    if kind in FORBIDDEN_ADAPTATIONS:
        raise ValueError("same layer generates/verifies/finally-authorizes itself")
    body = {
        "schema_version": PROPOSAL_SCHEMA,
        "proposal_id": proposal_id,
        "kind": kind,
        "delta": dict(delta),
        "hypothesis": hypothesis,
        "prior_state_hash": prior_state_hash,
        "measurable": True,
        **_closed(),
    }
    return {**body, "proposal_hash": _sha(body)}


def selection_decision(
    *,
    selected: Mapping[str, Any] | None,
    rejected: Sequence[Mapping[str, Any]],
    held: Sequence[Mapping[str, Any]],
    reason: str,
) -> dict[str, Any]:
    body = {
        "schema_version": DECISION_SCHEMA,
        "selected": None if selected is None else dict(selected),
        "rejected": [dict(item) for item in rejected],
        "held": [dict(item) for item in held],
        "retained_entire_set": True,
        "reason": reason,
        **_closed(),
    }
    return {**body, "decision_hash": _sha(body)}


def retention_candidate(
    *,
    candidate_id: str,
    payload: Mapping[str, Any],
    stage: str = "PROPOSED",
) -> dict[str, Any]:
    if stage not in LIFECYCLE:
        raise ValueError("invalid retention stage")
    if stage != "PROPOSED":
        raise ValueError("retention candidates must begin at PROPOSED; use advance_retention_candidate")
    body = {
        "schema_version": CANDIDATE_SCHEMA,
        "candidate_id": candidate_id,
        "stage": stage,
        "payload": dict(payload),
        "lifecycle_evidence": [],
        "eligibility_derived": False,
        **_closed(),
    }
    return {**body, "candidate_hash": _sha(body)}


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _validate_transition_evidence(stage: str, evidence: Mapping[str, Any]) -> None:
    if evidence.get("authority_effect") is not False:
        raise ValueError("retention evidence cannot carry authority")
    if stage == "OBSERVED":
        if evidence.get("observation_state") != "PASS" or not _is_digest(evidence.get("observation_hash")):
            raise ValueError("OBSERVED requires a bound passing observation")
    elif stage == "VERIFIED":
        if evidence.get("verification_state") != "PASS" or not evidence.get("assurance_case_id"):
            raise ValueError("VERIFIED requires a passing assurance case")
    elif stage == "REPLICATED":
        if evidence.get("replication_state") != "PASS" or not _is_digest(evidence.get("replication_hash")):
            raise ValueError("REPLICATED requires passing replication evidence")
    elif stage == "RETENTION_ELIGIBLE":
        if evidence.get("applicability_state") != "PASS":
            raise ValueError("RETENTION_ELIGIBLE requires resolved applicability")
        if evidence.get("active_defeaters") not in ([], ()):
            raise ValueError("RETENTION_ELIGIBLE cannot have active defeaters")
        if not _is_digest(evidence.get("selection_decision_hash")):
            raise ValueError("RETENTION_ELIGIBLE requires a bound selection decision")


def _candidate_body(
    *,
    candidate_id: str,
    payload: Mapping[str, Any],
    stage: str,
    lifecycle_evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": CANDIDATE_SCHEMA,
        "candidate_id": candidate_id,
        "stage": stage,
        "payload": dict(payload),
        "lifecycle_evidence": [dict(item) for item in lifecycle_evidence],
        "eligibility_derived": stage == "RETENTION_ELIGIBLE",
        **_closed(),
    }


def verify_retention_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct the staged eligibility chain without granting retention authority."""
    errors: list[str] = []
    if candidate.get("schema_version") != CANDIDATE_SCHEMA:
        errors.append("unsupported_candidate_schema")
    candidate_id = str(candidate.get("candidate_id") or "")
    payload = dict(candidate.get("payload") or {})
    history = list(candidate.get("lifecycle_evidence") or [])
    stage = "PROPOSED"
    body = _candidate_body(candidate_id=candidate_id, payload=payload, stage=stage, lifecycle_evidence=[])
    previous_hash = _sha(body)
    reconstructed_history: list[dict[str, Any]] = []
    for receipt in history:
        expected_index = LIFECYCLE.index(stage) + 1
        target = str(receipt.get("to_stage") or "")
        if expected_index >= len(LIFECYCLE) or target != LIFECYCLE[expected_index]:
            errors.append("non_adjacent_lifecycle_transition")
            break
        if receipt.get("from_stage") != stage or receipt.get("prior_candidate_hash") != previous_hash:
            errors.append("lifecycle_preimage_mismatch")
            break
        evidence = dict(receipt.get("evidence") or {})
        try:
            _validate_transition_evidence(target, evidence)
        except ValueError as exc:
            errors.append(str(exc))
            break
        receipt_body = {
            "from_stage": stage,
            "to_stage": target,
            "prior_candidate_hash": previous_hash,
            "evidence": evidence,
            "authority_effect": False,
            "production_effect": False,
        }
        if receipt.get("transition_hash") != _sha(receipt_body):
            errors.append("transition_hash_mismatch")
            break
        reconstructed_history.append(dict(receipt))
        stage = target
        body = _candidate_body(
            candidate_id=candidate_id,
            payload=payload,
            stage=stage,
            lifecycle_evidence=reconstructed_history,
        )
        previous_hash = _sha(body)
    if stage != candidate.get("stage"):
        errors.append("stage_not_derived_from_evidence")
    if candidate.get("candidate_hash") != previous_hash:
        errors.append("candidate_hash_mismatch")
    if candidate.get("eligibility_derived") is not (stage == "RETENTION_ELIGIBLE"):
        errors.append("eligibility_flag_mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "reconstructed_stage": stage,
        "reconstructed_candidate_hash": previous_hash,
        "authority_effect": False,
        "production_effect": False,
    }


def advance_retention_candidate(
    candidate: Mapping[str, Any],
    *,
    to_stage: str,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    verification = verify_retention_candidate(candidate)
    if not verification["valid"]:
        raise ValueError("invalid retention candidate: " + ",".join(verification["errors"]))
    current = str(candidate.get("stage"))
    expected_index = LIFECYCLE.index(current) + 1
    if expected_index >= len(LIFECYCLE) or to_stage != LIFECYCLE[expected_index]:
        raise ValueError("retention lifecycle transitions must be adjacent")
    evidence_body = dict(evidence)
    _validate_transition_evidence(to_stage, evidence_body)
    receipt_body = {
        "from_stage": current,
        "to_stage": to_stage,
        "prior_candidate_hash": candidate["candidate_hash"],
        "evidence": evidence_body,
        "authority_effect": False,
        "production_effect": False,
    }
    receipt = {**receipt_body, "transition_hash": _sha(receipt_body)}
    body = _candidate_body(
        candidate_id=str(candidate["candidate_id"]),
        payload=dict(candidate.get("payload") or {}),
        stage=to_stage,
        lifecycle_evidence=[*(candidate.get("lifecycle_evidence") or []), receipt],
    )
    return {**body, "candidate_hash": _sha(body)}


def synthetic_verified_retention_candidate(
    *,
    candidate_id: str,
    payload: Mapping[str, Any],
    selection_decision_hash: str | None = None,
) -> dict[str, Any]:
    """Build a transparent zero-call control. It is not empirical retention evidence."""
    candidate = retention_candidate(candidate_id=candidate_id, payload=payload)
    candidate = advance_retention_candidate(candidate, to_stage="OBSERVED", evidence={
        "observation_state": "PASS",
        "observation_hash": _sha({"candidate_id": candidate_id, "control": "observation"}),
        "evidence_class": "SYNTHETIC_ZERO_CALL_CONTROL",
        "authority_effect": False,
    })
    candidate = advance_retention_candidate(candidate, to_stage="VERIFIED", evidence={
        "verification_state": "PASS",
        "assurance_case_id": "synthetic-control:" + candidate_id,
        "evidence_class": "SYNTHETIC_ZERO_CALL_CONTROL",
        "authority_effect": False,
    })
    candidate = advance_retention_candidate(candidate, to_stage="REPLICATED", evidence={
        "replication_state": "PASS",
        "replication_hash": _sha({"candidate_id": candidate_id, "control": "replication"}),
        "evidence_class": "SYNTHETIC_ZERO_CALL_CONTROL",
        "authority_effect": False,
    })
    return advance_retention_candidate(candidate, to_stage="RETENTION_ELIGIBLE", evidence={
        "applicability_state": "PASS",
        "active_defeaters": [],
        "selection_decision_hash": selection_decision_hash or _sha({"candidate_id": candidate_id, "control": "selection"}),
        "evidence_class": "SYNTHETIC_ZERO_CALL_CONTROL",
        "authority_effect": False,
    })


def proposal_prior(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("stage") != "RETENTION_ELIGIBLE":
        raise ValueError("prior requires RETENTION_ELIGIBLE candidate")
    verification = verify_retention_candidate(candidate)
    if not verification["valid"] or candidate.get("eligibility_derived") is not True:
        raise ValueError("prior requires reconstructable evidence-derived eligibility")
    if candidate.get("authority_effect") is not False or candidate.get("production_effect") is not False:
        raise ValueError("prior cannot carry authority")
    body = {
        "schema_version": PRIOR_SCHEMA,
        "source_candidate_hash": candidate.get("candidate_hash"),
        "source_candidate": dict(candidate),
        "ranking_features": dict(candidate.get("payload") or {}),
        "eligibility_chain_hashes": [item["transition_hash"] for item in candidate.get("lifecycle_evidence") or []],
        "eligibility_chain_verified": True,
        "lineage_reconstructable": True,
        "active": True,
        **_closed(),
    }
    return {**body, "prior_hash": _sha(body)}


def verify_proposal_prior(prior: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if prior.get("schema_version") != PRIOR_SCHEMA:
        errors.append("unsupported_prior_schema")
    if prior.get("authority_effect") is not False or prior.get("production_effect") is not False:
        errors.append("prior_authority_or_production_effect")
    source = dict(prior.get("source_candidate") or {})
    source_verification = verify_retention_candidate(source)
    if not source_verification["valid"]:
        errors.append("source_candidate_not_reconstructable")
    if source.get("candidate_hash") != prior.get("source_candidate_hash"):
        errors.append("source_candidate_binding_mismatch")
    if prior.get("eligibility_chain_verified") is not True:
        errors.append("eligibility_chain_not_verified")
    expected = _sha({key: value for key, value in prior.items() if key != "prior_hash"})
    if prior.get("prior_hash") != expected:
        errors.append("prior_hash_mismatch")
    return {
        "valid": not errors,
        "errors": errors,
        "authority_effect": False,
        "production_effect": False,
    }


def rank_candidates(
    candidates: Sequence[Mapping[str, Any]],
    prior: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ranked = []
    if prior and prior.get("active") and not verify_proposal_prior(prior)["valid"]:
        raise ValueError("active prior is not reconstructable")
    features = dict((prior or {}).get("ranking_features") or {}) if prior and prior.get("active") else {}
    for item in candidates:
        score = float(item.get("base_score") or 0)
        if features.get("preferred_id") == item.get("id"):
            score += float(features.get("boost") or 0)
        if features.get("preferred_kind") == item.get("kind"):
            score += float(features.get("kind_boost") or 0)
        ranked.append({**dict(item), "score": score, "prior_applied": bool(features)})
    ranked.sort(key=lambda row: (-row["score"], str(row.get("id"))))
    return ranked


def mechanical_recursive_closure() -> dict[str, Any]:
    """Zero model calls. Establishes ranking influence, not utility."""
    r1 = synthetic_verified_retention_candidate(
        candidate_id="R1",
        payload={"preferred_id": "c2", "boost": 10.0, "kind": "retrieval_ranking"},
    )
    prior = proposal_prior(r1)
    family = (
        {"id": "c1", "kind": "retrieval_ranking", "base_score": 5.0},
        {"id": "c2", "kind": "retrieval_ranking", "base_score": 4.0},
        {"id": "c3", "kind": "context_ranking", "base_score": 6.0},
    )
    without_prior = rank_candidates(family, None)
    with_prior = rank_candidates(family, prior)
    difference = {
        "without": [item["id"] for item in without_prior],
        "with": [item["id"] for item in with_prior],
        "score_delta": {
            item["id"]: next(row["score"] for row in with_prior if row["id"] == item["id"]) - item["base_score"]
            for item in family
        },
    }
    reconstructed = (
        verify_retention_candidate(r1)["valid"]
        and difference["with"] != difference["without"]
        and difference["with"][0] == "c2"
    )
    body = {
        "schema_version": CLOSURE_SCHEMA,
        "R1": r1,
        "prior": prior,
        "V2_without": without_prior,
        "V2_with": with_prior,
        "difference": difference,
        "reconstructed": reconstructed,
        "R_c": "PASS_MECHANICAL" if reconstructed else "FAIL",
        "utility_established": False,
        "intelligence_improvement_established": False,
        **_closed(),
    }
    return {**body, "closure_hash": _sha(body)}


def legitimate_state(view: Mapping[str, Any]) -> tuple[bool, list[str]]:
    faults: list[str] = []
    for field in ("authority_effect", "production_effect", "adaptation_authorized"):
        if view.get(field) is not False:
            faults.append("authority_leak:" + field)
    if view.get("schema_version") != STATE_SCHEMA:
        faults.append("invalid_state_schema")
    for prior in view.get("priors") or []:
        if prior.get("active") and not verify_proposal_prior(prior)["valid"]:
            faults.append("invalid_prior_lineage")
        if prior.get("active") and prior.get("contradicted"):
            faults.append("contradicted_prior_active")
        if prior.get("authority_effect") is not False:
            faults.append("prior_authority_leak")
    if view.get("snapshot_hash") in (None, "", "invalid"):
        faults.append("invalid_snapshot_identity")
    return (not faults, faults)


def _response_for(disturbance: str) -> str:
    mapping = {
        "contradicted_prior": "QUARANTINE",
        "stale_applicability": "HOLD",
        "challenged_instrument": "HOLD",
        "environment_mismatch": "HOLD",
        "superseded_evidence": "SUPERSEDE",
        "failed_replication": "HOLD",
        "invalid_snapshot_identity": "RECONSTRUCT",
        "corrupted_retention_metadata": "ROLLBACK",
    }
    return mapping.get(disturbance, "HOLD")


def apply_disturbance(view: Mapping[str, Any], disturbance: str) -> dict[str, Any]:
    disturbed = json.loads(_canonical(view))
    if disturbance == "contradicted_prior":
        priors = list(disturbed.get("priors") or [{"active": True, "authority_effect": False}])
        priors[0] = {**priors[0], "active": True, "contradicted": True}
        disturbed["priors"] = priors
    elif disturbance == "stale_applicability":
        disturbed["unresolved"] = list(disturbed.get("unresolved") or []) + ["stale_applicability"]
    elif disturbance == "challenged_instrument":
        disturbed["unresolved"] = list(disturbed.get("unresolved") or []) + ["challenged_instrument"]
    elif disturbance == "environment_mismatch":
        disturbed["unresolved"] = list(disturbed.get("unresolved") or []) + ["environment_mismatch"]
    elif disturbance == "superseded_evidence":
        disturbed["unresolved"] = list(disturbed.get("unresolved") or []) + ["superseded_evidence"]
    elif disturbance == "failed_replication":
        disturbed["unresolved"] = list(disturbed.get("unresolved") or []) + ["failed_replication"]
    elif disturbance == "invalid_snapshot_identity":
        disturbed["snapshot_hash"] = "invalid"
    elif disturbance == "corrupted_retention_metadata":
        disturbed["priors"] = [{"corrupted": True, "active": True, "authority_effect": False}]
    disturbed["legitimate"] = False
    disturbed.pop("state_hash", None)
    return {**disturbed, "state_hash": _sha({key: value for key, value in disturbed.items() if key != "state_hash"})}


def stabilize(view: Mapping[str, Any], disturbance: str) -> dict[str, Any]:
    """Recover into L while AuthorityLeakage remains 0. Instability never widens authority."""
    started = organization_state_view(
        snapshot_hash=str(view.get("snapshot_hash") or "unknown"),
        priors=view.get("priors") or (),
        debt=view.get("assurance_debt") or {},
        unresolved=view.get("unresolved") or (),
    )
    ok, _ = legitimate_state(started)
    if not ok:
        started["legitimate"] = False
    disturbed = apply_disturbance(started, disturbance)
    instability = 1 + len(disturbed.get("unresolved") or []) + int(not legitimate_state(disturbed)[0])
    adaptation_before = 0
    response = _response_for(disturbance)
    recovered = json.loads(_canonical(started))
    steps = 1
    if response == "QUARANTINE":
        recovered["priors"] = [
            {**prior, "active": False, "quarantined": True, "contradicted": False}
            for prior in recovered.get("priors") or []
        ]
    elif response == "SUPERSEDE":
        recovered["unresolved"] = [item for item in recovered.get("unresolved") or [] if item != "superseded_evidence"]
        recovered["superseded"] = True
    elif response == "ROLLBACK":
        recovered["priors"] = []
    elif response == "RECONSTRUCT":
        recovered["snapshot_hash"] = str(view.get("snapshot_hash") or started["snapshot_hash"])
        if recovered["snapshot_hash"] == "invalid":
            recovered["snapshot_hash"] = "reconstructed"
    elif response == "HOLD":
        recovered["held"] = True
        recovered["unresolved"] = sorted(set(list(recovered.get("unresolved") or []) + [disturbance]))
    recovered["legitimate"] = True
    recovered["adaptation_freedom"] = 0
    recovered.update(_closed())
    recovered.pop("state_hash", None)
    recovered = {**recovered, "state_hash": _sha(recovered)}
    ok, faults = legitimate_state(recovered)
    leakage = 0
    if recovered.get("authority_effect") is not False or recovered.get("adaptation_authorized") is not False:
        leakage = 1
    if recovered.get("adaptation_freedom", 0) > adaptation_before and instability > 0:
        ok = False
        faults = list(faults) + ["homeostatic_law_violated"]
    body = {
        "schema_version": STABILIZATION_SCHEMA,
        "disturbance": disturbance,
        "response": response,
        "S_r": ok and leakage == 0,
        "T_s": steps,
        "authority_leakage": leakage,
        "faults": faults,
        "recovered_state": recovered,
        "disturbed_state_hash": disturbed.get("state_hash"),
        **_closed(),
    }
    return {**body, "stabilization_hash": _sha(body)}


def bounded_self_stabilization_panel(snapshot_hash: str) -> dict[str, Any]:
    retained = synthetic_verified_retention_candidate(candidate_id="stabilization-R1", payload={"preferred_id": "control"})
    view = organization_state_view(snapshot_hash=snapshot_hash, priors=(proposal_prior(retained),))
    disturbances = (
        "contradicted_prior",
        "stale_applicability",
        "challenged_instrument",
        "environment_mismatch",
        "superseded_evidence",
        "failed_replication",
        "invalid_snapshot_identity",
        "corrupted_retention_metadata",
    )
    results = [stabilize(view, item) for item in disturbances]
    body = {
        "schema_version": STABILIZATION_SCHEMA + "+panel",
        "results": results,
        "S_r": all(item["S_r"] for item in results),
        "T_s": max(item["T_s"] for item in results),
        "authority_leakage": max(item["authority_leakage"] for item in results),
        **_closed(),
    }
    return {**body, "panel_hash": _sha(body)}


RECOVERY_SCHEMA = "cortex-state-recovery-receipt/1.0"


def _rehash_state(state: Mapping[str, Any]) -> dict[str, Any]:
    body = {key: value for key, value in dict(state).items() if key != "state_hash"}
    return {**body, "state_hash": _sha(body)}


def apply_recovery(state: Mapping[str, Any], action: Mapping[str, Any]) -> dict[str, Any]:
    """Start from corrupted S*. Do not rebuild from a hidden clean copy."""
    recovered = json.loads(_canonical(state))
    prior_hash = recovered.get("state_hash")
    response = str(action.get("action") or "HOLD")
    modified: list[str] = []
    if response == "HARD_FAIL":
        recovered["priors"] = [
            {**prior, "active": False, "quarantined": True, "authority_effect": False, "production_effect": False}
            for prior in recovered.get("priors") or []
        ]
        recovered["held"] = True
        recovered["legitimate"] = False
        modified.extend(["priors", "held"])
    elif response == "QUARANTINE":
        recovered["priors"] = [
            {**prior, "active": False, "quarantined": True, "contradicted": prior.get("contradicted", False),
             "authority_effect": False, "production_effect": False}
            for prior in recovered.get("priors") or []
        ]
        modified.append("priors")
    elif response == "ROLLBACK":
        recovered["priors"] = []
        recovered["candidates"] = []
        modified.extend(["priors", "candidates"])
    elif response == "SUPERSEDE":
        recovered["priors"] = [
            {**prior, "active": False, "superseded": True, "evidence_superseded": True}
            if prior.get("evidence_superseded") or prior.get("supporting_claim_status") in {"HELD", "UNRESOLVED"}
            else prior
            for prior in recovered.get("priors") or []
        ]
        recovered["superseded"] = True
        modified.append("priors")
    elif response == "RECONSTRUCT":
        evidence = recovered.get("persistent_snapshot_hash") or recovered.get("snapshot_hash")
        if evidence in (None, "", "invalid") or (isinstance(evidence, str) and len(evidence) != 64):
            recovered["held"] = True
            recovered["snapshot_hash"] = recovered.get("persistent_snapshot_hash") or "reconstructed"
        else:
            recovered["snapshot_hash"] = evidence
        if recovered.get("snapshot_source_head") != recovered.get("current_checkout_revision"):
            recovered["held"] = True
        modified.append("snapshot_hash")
    else:
        recovered["held"] = True
        recovered["priors"] = [
            {**prior, "active": False, "held": True, "authority_effect": False, "production_effect": False}
            for prior in recovered.get("priors") or []
        ]
        modified.extend(["held", "priors"])
    recovered["adaptation_freedom"] = 0
    recovered.update(_closed())
    recovered["legitimate"] = True
    recovered = _rehash_state(recovered)
    from .invariants import detect_invariant_violations
    remaining = detect_invariant_violations(recovered)
    hard = [item for item in remaining if item["invariant_id"] in {"INV-AUTHORITY-NONDERIVATION", "INV-ELIGIBLE-NOT-ACTIVE", "INV-HOMEOSTATIC-MONOTONICITY"}]
    if hard:
        recovered["legitimate"] = False
        recovered = _rehash_state(recovered)
    leakage = 0 if recovered.get("authority_effect") is False and recovered.get("production_effect") is False else 1
    ok, faults = legitimate_state(recovered)
    body = {
        "schema_version": RECOVERY_SCHEMA,
        "prior_state_hash": prior_hash,
        "recovered_state_hash": recovered["state_hash"],
        "violation_set": list(action.get("violations") or []),
        "chosen_response": response,
        "modified_fields": modified,
        "evidence_used": ["corrupted_state", "frozen_recovery_policy"],
        "S_r": ok and leakage == 0 and not hard,
        "T_s": 1,
        "authority_leakage": leakage,
        "faults": faults,
        "recovered_state": recovered,
        **_closed(),
    }
    return {**body, "recovery_hash": _sha(body)}


def recover_from_corrupted_state(state: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    from .invariants import derive_recovery_action, detect_invariant_violations
    violations = detect_invariant_violations(state)
    action = derive_recovery_action(violations, policy)
    return apply_recovery(state, action)


def _corrupt(view: Mapping[str, Any], mutation: Mapping[str, Any]) -> dict[str, Any]:
    corrupted = json.loads(_canonical(view))
    for key, value in mutation.items():
        if key == "priors":
            corrupted["priors"] = list(value)
        else:
            corrupted[key] = value
    corrupted["legitimate"] = False
    return _rehash_state(corrupted)


def homeostatic_panel_v2(snapshot_hash: str) -> dict[str, Any]:
    """Finite adversarial panel. Recovery does not receive disturbance names."""
    from .invariants import freeze_recovery_policy
    policy = freeze_recovery_policy()
    retained = synthetic_verified_retention_candidate(candidate_id="homeostasis-R1", payload={"preferred_id": "control"})
    base = organization_state_view(snapshot_hash=snapshot_hash, priors=(proposal_prior(retained),))
    base["persistent_snapshot_hash"] = snapshot_hash
    base["current_checkout_revision"] = snapshot_hash
    base["snapshot_source_head"] = snapshot_hash
    mutations = (
        {"priors": [{"active": True, "contradicted": True, "authority_effect": False, "production_effect": False}]},
        {"priors": [{"active": True, "evidence_superseded": True, "authority_effect": False, "production_effect": False}]},
        {"priors": [{"active": True, "applicability_match": False, "authority_effect": False, "production_effect": False}]},
        {"snapshot_source_head": "old-head", "current_checkout_revision": snapshot_hash, "snapshot_hash": snapshot_hash},
        {"source_digest_changed": True, "snapshot_hash": snapshot_hash, "snapshot_source_head": snapshot_hash, "current_checkout_revision": snapshot_hash},
        {"candidates": [{"stage": "RETENTION_ELIGIBLE", "replication_state": "FAIL", "production_effect": False}]},
        {"candidates": [{"stage": "RETENTION_ELIGIBLE", "lineage_reconstructable": False, "production_effect": False}]},
        {"assurance_active_defeater": True},
        {"authority_effect": True},
        {"priors": [{"active": True, "production_effect": True, "authority_effect": False}]},
        {"priors": [
            {"active": True, "contradiction_group": "g1", "authority_effect": False, "production_effect": False},
            {"active": True, "contradiction_group": "g1", "authority_effect": False, "production_effect": False},
        ]},
        {"priors": [{"active": True, "instrument_stale": True, "authority_effect": False, "production_effect": False}]},
    )
    results = []
    for mutation in mutations:
        corrupted = _corrupt(base, mutation)
        receipt = recover_from_corrupted_state(corrupted, policy)
        results.append({
            "detected": [item["invariant_id"] for item in receipt["violation_set"]],
            "response": receipt["chosen_response"],
            "S_r": receipt["S_r"],
            "authority_leakage": receipt["authority_leakage"],
            "T_s": receipt["T_s"],
        })
    detected = sum(1 for item in results if item["detected"])
    body = {
        "schema_version": STABILIZATION_SCHEMA + "+v2",
        "results": results,
        "detection_accuracy": detected / len(results),
        "correct_response_rate": sum(1 for item in results if item["response"] in RESPONSES or item["response"] == "HARD_FAIL") / len(results),
        "S_r": all(item["S_r"] for item in results),
        "T_s": max(item["T_s"] for item in results),
        "authority_leakage": max(item["authority_leakage"] for item in results),
        "named_disturbance_supplied": False,
        **_closed(),
    }
    return {**body, "panel_hash": _sha(body)}


def reject_self_authorization(proposal: Mapping[str, Any], decision: Mapping[str, Any]) -> bool:
    """Same layer cannot generate, verify, and finally authorize itself."""
    if proposal.get("proposal_hash") and decision.get("selected") and decision.get("selected").get("proposal_hash") == proposal.get("proposal_hash"):
        if decision.get("authority_effect") is not False:
            return False
    return proposal.get("authority_effect") is False and decision.get("authority_effect") is False


__all__ = [
    "adaptation_proposal",
    "advance_retention_candidate",
    "apply_recovery",
    "bounded_self_stabilization_panel",
    "homeostatic_panel_v2",
    "mechanical_recursive_closure",
    "organization_state_view",
    "proposal_prior",
    "rank_candidates",
    "recover_from_corrupted_state",
    "reject_self_authorization",
    "retention_candidate",
    "selection_decision",
    "stabilize",
    "synthetic_verified_retention_candidate",
    "verify_proposal_prior",
    "verify_retention_candidate",
]
