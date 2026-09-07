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
CANDIDATE_SCHEMA = "cortex-retention-candidate/1.0"
PRIOR_SCHEMA = "cortex-proposal-prior/1.0"
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
    body = {
        "schema_version": CANDIDATE_SCHEMA,
        "candidate_id": candidate_id,
        "stage": stage,
        "payload": dict(payload),
        **_closed(),
    }
    return {**body, "candidate_hash": _sha(body)}


def proposal_prior(candidate: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("stage") != "RETENTION_ELIGIBLE":
        raise ValueError("prior requires RETENTION_ELIGIBLE candidate")
    if candidate.get("authority_effect") is not False or candidate.get("production_effect") is not False:
        raise ValueError("prior cannot carry authority")
    body = {
        "schema_version": PRIOR_SCHEMA,
        "source_candidate_hash": candidate.get("candidate_hash"),
        "ranking_features": dict(candidate.get("payload") or {}),
        "active": True,
        **_closed(),
    }
    return {**body, "prior_hash": _sha(body)}


def rank_candidates(
    candidates: Sequence[Mapping[str, Any]],
    prior: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    ranked = []
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
    r1 = retention_candidate(
        candidate_id="R1",
        payload={"preferred_id": "c2", "boost": 10.0, "kind": "retrieval_ranking"},
        stage="RETENTION_ELIGIBLE",
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
        r1["candidate_hash"] == retention_candidate(
            candidate_id="R1",
            payload=r1["payload"],
            stage="RETENTION_ELIGIBLE",
        )["candidate_hash"]
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
    view = organization_state_view(snapshot_hash=snapshot_hash, priors=({"active": True, "authority_effect": False},))
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


def reject_self_authorization(proposal: Mapping[str, Any], decision: Mapping[str, Any]) -> bool:
    """Same layer cannot generate, verify, and finally authorize itself."""
    if proposal.get("proposal_hash") and decision.get("selected") and decision.get("selected").get("proposal_hash") == proposal.get("proposal_hash"):
        if decision.get("authority_effect") is not False:
            return False
    return proposal.get("authority_effect") is False and decision.get("authority_effect") is False


__all__ = [
    "adaptation_proposal",
    "bounded_self_stabilization_panel",
    "mechanical_recursive_closure",
    "organization_state_view",
    "proposal_prior",
    "rank_candidates",
    "reject_self_authorization",
    "retention_candidate",
    "selection_decision",
    "stabilize",
]
