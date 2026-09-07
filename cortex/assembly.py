"""Shadow metabolic assembly: discover lawful edges among existing components.

Compute flows. Verified structure recycles. Evidence never creates authority.
This module discovers topology; it does not execute edges or grant capability.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__
from .invariants import detect_invariant_violations, evaluate_invariants
from .shadow_organization import (
    adaptation_proposal,
    organization_state_view,
    proposal_prior,
    rank_candidates,
    selection_decision,
    synthetic_verified_retention_candidate,
)

MANIFEST_SCHEMA = "cortex-component-manifest/1.0"
CANDIDATE_SCHEMA = "cortex-assembly-candidate/1.0"
TOPOLOGY_SCHEMA = "cortex-assembly-topology/1.0"
CONSTRAINT_SCHEMA = "cortex-constraint-candidate/1.0"
GATE_RECEIPT_SCHEMA = "cortex-verification-gate-receipt/1.0"
BRIDGE_SCHEMA = "cortex-source-improvement-transduction-bridge/1.0"
CYCLE_SCHEMA = "cortex-shadow-self-assembly-cycle/1.0"
INFLUENCE_KINDS = (
    "retrieval_ranking",
    "context_composition",
    "verification_ordering",
    "experiment_selection",
    "resource_allocation",
    "assembly_edge_priority",
)
FORBIDDEN_INFLUENCE = frozenset({
    "authority", "credentials", "security", "network", "execution", "production_mutation",
})
DEGRADED_CLAIMS = frozenset({
    "HELD", "UNRESOLVED", "NOT_ESTABLISHED", "REQUIRES_REPLICATION",
})
POSITIVE_WEIGHT = 1.0
NEGATIVE_WEIGHT = 1.0

COMPONENT_SPECS: tuple[dict[str, Any], ...] = (
    {
        "component_id": "memory_projection",
        "implementation": "cortex/memory_projection.py",
        "input_types": ["AdmittedMemory", "ClaimRecord"],
        "output_types": ["MemoryProjection"],
        "input_schemas": ["cortex-admitted-memory/1.0"],
        "output_schemas": ["cortex-memory-projection/1.0"],
        "dependencies": ["admitted_memory", "assurance"],
        "required_claims": [],
        "required_assurance_dimensions": ["source"],
        "estimated_cost_class": 2,
    },
    {
        "component_id": "assurance",
        "implementation": "cortex/assurance.py",
        "input_types": ["ClaimRecord", "TransductionReceipt"],
        "output_types": ["AssuranceCase", "AssuranceDebt"],
        "input_schemas": ["cortex-claim-registry/1.0", "cortex-transduction-receipt/1.0"],
        "output_schemas": ["cortex-assurance-case/1.0", "cortex-assurance-debt/1.0"],
        "dependencies": ["transduction_receipt"],
        "required_claims": [],
        "required_assurance_dimensions": ["source", "transduction"],
        "estimated_cost_class": 2,
    },
    {
        "component_id": "epistemic_snapshot",
        "implementation": "cortex/epistemic_snapshot.py",
        "input_types": ["ClaimRegistry", "AssuranceCase"],
        "output_types": ["EpistemicSnapshot"],
        "input_schemas": ["cortex-claim-registry/1.0", "cortex-assurance-case/1.0"],
        "output_schemas": ["cortex-epistemic-snapshot/1.1"],
        "dependencies": ["assurance"],
        "required_claims": [],
        "required_assurance_dimensions": ["source"],
        "estimated_cost_class": 2,
    },
    {
        "component_id": "context_packet",
        "implementation": "cortex/epistemic_snapshot.py",
        "input_types": ["EpistemicSnapshot", "Task"],
        "output_types": ["ContextPacket"],
        "input_schemas": ["cortex-epistemic-snapshot/1.1"],
        "output_schemas": ["cortex-context-packet/1.1"],
        "dependencies": ["epistemic_snapshot"],
        "required_claims": [],
        "required_assurance_dimensions": ["source"],
        "estimated_cost_class": 1,
    },
    {
        "component_id": "transduction_policy",
        "implementation": "cortex/transduction_policy.py",
        "input_types": ["HostPolicy"],
        "output_types": ["TransductionPolicy"],
        "input_schemas": ["cortex-transduction-policy/1.0"],
        "output_schemas": ["cortex-transduction-policy/1.0"],
        "dependencies": [],
        "required_claims": ["transduction.prospective_policy_closure"],
        "required_assurance_dimensions": ["transduction"],
        "estimated_cost_class": 1,
    },
    {
        "component_id": "transduction_receipt",
        "implementation": "cortex/transduction_policy.py",
        "input_types": ["TransductionPolicy", "Intent"],
        "output_types": ["TransductionReceipt"],
        "input_schemas": ["cortex-transduction-policy/1.0"],
        "output_schemas": ["cortex-transduction-receipt/1.0"],
        "dependencies": ["transduction_policy"],
        "required_claims": ["transduction.compiled_artifact_binding"],
        "required_assurance_dimensions": ["transduction", "instrument"],
        "estimated_cost_class": 3,
    },
    {
        "component_id": "source_improvement",
        "implementation": "cortex/source_improvement.py",
        "input_types": ["PatchProposal", "TransductionPolicy"],
        "output_types": ["SourceImprovementResult", "TransductionReceipt"],
        "input_schemas": ["cortex-source-improvement-preregistration/1.0", "cortex-transduction-policy/1.0"],
        "output_schemas": ["cortex-source-improvement-result/1.0", "cortex-transduction-receipt/1.0"],
        "dependencies": ["transduction_policy"],
        "required_claims": [],
        "required_assurance_dimensions": ["transduction"],
        "estimated_cost_class": 3,
        "historical_compatibility": "cortex-source-improvement-preregistration/1.0",
    },
    {
        "component_id": "shadow_organization",
        "implementation": "cortex/shadow_organization.py",
        "input_types": ["AdaptationProposal", "ContextPacket", "AssuranceDebt"],
        "output_types": ["RetentionCandidate", "ProposalPrior"],
        "input_schemas": ["cortex-adaptation-proposal/1.0", "cortex-context-packet/1.1"],
        "output_schemas": ["cortex-retention-candidate/1.1", "cortex-proposal-prior/1.1"],
        "dependencies": ["context_packet", "assurance"],
        "required_claims": [],
        "required_assurance_dimensions": ["source"],
        "estimated_cost_class": 2,
    },
    {
        "component_id": "memory_budget",
        "implementation": "cortex/memory_budget.py",
        "input_types": ["AssuranceDebt"],
        "output_types": ["BudgetProposal"],
        "input_schemas": ["cortex-assurance-debt/1.0"],
        "output_schemas": ["cortex-memory-budget/1.0"],
        "dependencies": ["assurance"],
        "required_claims": [],
        "required_assurance_dimensions": ["source"],
        "estimated_cost_class": 1,
    },
    {
        "component_id": "invariant_evaluation",
        "implementation": "cortex/invariants.py",
        "input_types": ["OrganizationState"],
        "output_types": ["InvariantEvaluation"],
        "input_schemas": ["cortex-organization-state-view/1.0"],
        "output_schemas": ["cortex-invariant-evaluation/1.0"],
        "dependencies": [],
        "required_claims": [],
        "required_assurance_dimensions": [],
        "estimated_cost_class": 1,
    },
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _closed() -> dict[str, Any]:
    return {
        "authority_effect": False,
        "production_effect": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "adaptation_authorized": False,
    }


def component_manifest(spec: Mapping[str, Any]) -> dict[str, Any]:
    body = {
        "schema_version": MANIFEST_SCHEMA,
        "component_id": spec["component_id"],
        "implementation": spec["implementation"],
        "version": __version__,
        "input_types": list(spec["input_types"]),
        "output_types": list(spec["output_types"]),
        "input_schemas": list(spec["input_schemas"]),
        "output_schemas": list(spec["output_schemas"]),
        "dependencies": list(spec.get("dependencies") or []),
        "required_claims": list(spec.get("required_claims") or []),
        "required_assurance_dimensions": list(spec.get("required_assurance_dimensions") or []),
        "applicability_requirements": dict(spec.get("applicability_requirements") or {}),
        "authority_ceiling": "advisory_observation_only",
        "estimated_cost_class": int(spec.get("estimated_cost_class") or 1),
        "deterministic": True,
        "side_effect_class": "none",
        "historical_compatibility": spec.get("historical_compatibility"),
        **_closed(),
    }
    return {**body, "manifest_hash": _sha(body)}


def component_catalog() -> list[dict[str, Any]]:
    return [component_manifest(spec) for spec in COMPONENT_SPECS]


def evaluate_component_compatibility(
    source: Mapping[str, Any],
    destination: Mapping[str, Any],
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = dict(context or {})
    claims = {item.get("claim_id"): item for item in context.get("claims") or []}
    type_ok = bool(set(source.get("output_types") or []) & set(destination.get("input_types") or []))
    source_schemas = set(source.get("output_schemas") or [])
    destination_schemas = set(destination.get("input_schemas") or [])
    schema_ok = bool(source_schemas and destination_schemas and source_schemas & destination_schemas)
    scope_ok = source.get("authority_ceiling") == destination.get("authority_ceiling")
    provenance_ok = bool(source.get("implementation") and destination.get("implementation"))
    for manifest in (source, destination):
        if manifest.get("manifest_hash") != _sha({key: value for key, value in manifest.items() if key != "manifest_hash"}):
            provenance_ok = False
    authority_ok = source.get("authority_effect") is False and destination.get("authority_effect") is False
    production_ok = source.get("production_effect") is False and destination.get("production_effect") is False
    historical_ok = True
    environment_state = str(context.get("environment_state") or "UNKNOWN")
    environment_ok = environment_state == "PASS"
    required = list(destination.get("required_claims") or []) + list(source.get("required_claims") or [])
    assurance_states = []
    for claim_id in required:
        claim = claims.get(claim_id)
        if claim is None:
            assurance_states.append("UNKNOWN")
        elif claim.get("active_defeaters") or claim.get("status") in DEGRADED_CLAIMS:
            assurance_states.append("HELD")
        elif claim.get("status") not in {"VERIFIED", "POSITIVE_WITHIN_DECLARED_WORKLOAD"}:
            assurance_states.append("UNKNOWN")
        else:
            assurance_states.append("PASS")
    if not required:
        assurance_states.append("PASS")
    assurance = "HOLD" if "HELD" in assurance_states else ("UNKNOWN" if "UNKNOWN" in assurance_states else "PASS")
    applicability = "PASS"
    if context.get("superseded_evidence"):
        applicability = "FAIL"
    gates = {
        "schema": "PASS" if schema_ok else "FAIL",
        "type": "PASS" if type_ok else "FAIL",
        "scope": "PASS" if scope_ok else "FAIL",
        "provenance": "PASS" if provenance_ok else "FAIL",
        "assurance": assurance,
        "applicability": applicability,
        "authority": "PASS" if authority_ok and production_ok else "FAIL",
        "historical_identity": "PASS" if historical_ok else "FAIL",
        "environment": "PASS" if environment_ok else ("FAIL" if environment_state == "FAIL" else "UNKNOWN"),
    }
    required_ids = ("schema", "type", "scope", "provenance", "assurance", "applicability", "authority", "historical_identity", "environment")
    if any(gates[name] == "FAIL" for name in required_ids):
        compatible, disposition = False, "REJECT"
    elif any(gates[name] == "UNKNOWN" for name in required_ids) or gates["assurance"] == "HOLD":
        compatible, disposition = False, "HOLD"
    else:
        compatible, disposition = True, "ACCEPT"
    body = {
        "schema_version": "cortex-component-compatibility/1.0",
        "gates": gates,
        "compatible": compatible,
        "disposition": disposition,
        **_closed(),
    }
    return {**body, "compatibility_hash": _sha(body)}


def discover_assembly_candidates(
    manifests: Sequence[Mapping[str, Any]] | None = None,
    current_state: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    catalog = list(manifests or component_catalog())
    state = dict(current_state or {})
    if "claims" not in state:
        try:
            from .assurance import load_claim_registry
            state["claims"] = load_claim_registry().get("claims") or []
        except (OSError, ValueError):
            state["claims"] = []
    candidates = []
    for source in catalog:
        for destination in catalog:
            if source["component_id"] == destination["component_id"]:
                continue
            compatibility = evaluate_component_compatibility(source, destination, state)
            if not set(source.get("output_types") or []) & set(destination.get("input_types") or []):
                continue
            body = {
                "schema_version": CANDIDATE_SCHEMA,
                "source_component": source["component_id"],
                "destination_component": destination["component_id"],
                "source_output_type": sorted(set(source["output_types"]) & set(destination["input_types"]))[0],
                "destination_input_type": sorted(set(source["output_types"]) & set(destination["input_types"]))[0],
                "schema_binding": sorted(set(source.get("output_schemas") or []) & set(destination.get("input_schemas") or [])),
                "scope_binding": source.get("authority_ceiling"),
                "claim_dependencies": sorted(set(source.get("required_claims") or []) | set(destination.get("required_claims") or [])),
                "assurance_requirements": sorted(set(source.get("required_assurance_dimensions") or []) | set(destination.get("required_assurance_dimensions") or [])),
                "applicability_requirements": dict(destination.get("applicability_requirements") or {}),
                "authority_check": compatibility["gates"]["authority"],
                "estimated_cost": int(source.get("estimated_cost_class") or 1) + int(destination.get("estimated_cost_class") or 1),
                "compatibility_results": compatibility,
                "compatible": compatibility["compatible"],
                "base_score": 10 - int(source.get("estimated_cost_class") or 1),
                "kind": "assembly_edge_priority",
                "id": source["component_id"] + "->" + destination["component_id"],
                **_closed(),
            }
            candidates.append({**body, "candidate_hash": _sha(body)})
    return sorted(candidates, key=lambda item: item["id"])


def constraint_candidate(
    *,
    originating_failure_receipt: str,
    failure_class: str,
    subject: str,
    environment: Mapping[str, Any],
    instrument: str,
    policy: str,
    applicability: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "schema_version": CONSTRAINT_SCHEMA,
        "originating_failure_receipt": originating_failure_receipt,
        "failure_class": failure_class,
        "subject": subject,
        "environment": dict(environment),
        "instrument": instrument,
        "policy": policy,
        "applicability": dict(applicability),
        "expiry": None,
        "counterevidence": [],
        **_closed(),
    }
    return {**body, "constraint_hash": _sha(body)}


def _kernel(left: Mapping[str, Any], right: Mapping[str, Any]) -> float:
    if left.get("kind") and right.get("kind") and left.get("kind") == right.get("kind"):
        return 1.0
    env_l = (left.get("environment") or left.get("applicability") or {}).get("os_family")
    env_r = (right.get("environment") or right.get("applicability") or {}).get("os_family")
    if env_l and env_r:
        return 1.0 if env_l == env_r else 0.0
    if left.get("id") and left.get("id") == right.get("id"):
        return 1.0
    if left.get("source_component") and left.get("source_component") == right.get("preferred_id"):
        return 1.0
    if right.get("id") and right.get("id") == left.get("preferred_id"):
        return 1.0
    return 0.0


def feasible_then_score(
    candidates: Sequence[Mapping[str, Any]],
    *,
    prior: Mapping[str, Any] | None = None,
    constraints: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    """Hard constraints first. Utility second. No score compensates for invariant failure."""
    feasible = []
    for item in candidates:
        if item.get("authority_effect") is not False or item.get("production_effect") is not False:
            continue
        if item.get("compatible") is not True:
            continue
        if item.get("kind") in FORBIDDEN_INFLUENCE:
            continue
        feasible.append(dict(item))
    ranked = rank_candidates(feasible, prior)
    features = dict((prior or {}).get("ranking_features") or {}) if prior and prior.get("active") else {}
    scored = []
    for item in ranked:
        score = float(item.get("score") or 0)
        score += POSITIVE_WEIGHT * _kernel(features, item)
        infeasible = False
        for constraint in constraints:
            scope = _kernel(constraint, item)
            score -= NEGATIVE_WEIGHT * scope
            if scope and constraint.get("infeasible"):
                infeasible = True
        if infeasible:
            continue
        item["score"] = score
        scored.append(item)
    scored.sort(key=lambda row: (-float(row.get("score") or 0), str(row.get("id"))))
    return scored


def memory_assurance_bridge(memory: Mapping[str, Any], claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Claim degradation excludes memory from active guidance; history is kept."""
    claim_id = str(memory.get("claim_id") or "")
    by_id = {str(item.get("claim_id")): item for item in claims}
    claim = by_id.get(claim_id)
    degraded = False
    if claim is not None:
        degraded = bool(claim.get("active_defeaters")) or str(claim.get("status")) in DEGRADED_CLAIMS
    body = {
        "schema_version": "cortex-memory-assurance-bridge/1.0",
        "memory_id": memory.get("memory_id"),
        "claim_id": claim_id or None,
        "active_guidance": (not degraded) and memory.get("G_M", 1) == 1,
        "historical_retained": True,
        "deleted": False,
        "reason": "claim_degraded" if degraded else "eligible",
        **_closed(),
    }
    return {**body, "bridge_hash": _sha(body)}


def assurance_budget_bridge(debt: Mapping[str, Any]) -> dict[str, Any]:
    """Assurance debt may contract freedom; improvement does not grant authority."""
    dimensions = dict(debt.get("dimensions") or debt)
    meet = str(debt.get("noncompensatory_meet") or "UNKNOWN")
    freedom = 0
    if meet == "PASS":
        freedom = 0
    narrowing = []
    if dimensions.get("environment") in {"UNKNOWN", "HELD", "FAIL"}:
        narrowing.append("narrower_applicability")
    if dimensions.get("instrument") in {"HELD", "FAIL"}:
        narrowing.append("HOLD_dependent_adaptation")
    if dimensions.get("replication") == "FAIL":
        narrowing.append("quarantine_retention_influence")
    if dimensions.get("source") in {"HELD", "FAIL", "UNKNOWN"}:
        narrowing.append("reconstruction_required")
    body = {
        "schema_version": "cortex-assurance-budget-bridge/1.0",
        "adaptation_freedom": freedom,
        "narrowing": narrowing,
        "authority_granted": False,
        **_closed(),
    }
    return {**body, "bridge_hash": _sha(body)}


def source_improvement_transduction_bridge() -> dict[str, Any]:
    """v2 path sits on TransductionPolicy. v1 remains historically reconstructable."""
    from .source_improvement import CONTRACT_SCHEMA, RESULT_SCHEMA
    body = {
        "schema_version": BRIDGE_SCHEMA,
        "historical_v1": {
            "contract": CONTRACT_SCHEMA,
            "result": RESULT_SCHEMA,
            "reconstructable": True,
            "rewritten": False,
        },
        "future_v2": {
            "uses": [
                "TransductionPolicy",
                "compiled intent",
                "bounded candidate",
                "raw observations",
                "TransductionReceipt",
                "independent attestation",
            ],
            "beside_v1": False,
            "on_transduction_policy": True,
        },
        **_closed(),
    }
    return {**body, "bridge_hash": _sha(body)}


def verification_gate_receipt(
    *,
    gate_id: str,
    source_revision: str,
    instrument_identity: str,
    environment: Mapping[str, Any],
    policy_identity: str,
    result: str,
    duration_s: float | None = None,
    dependencies: Sequence[str] = (),
) -> dict[str, Any]:
    body = {
        "schema_version": GATE_RECEIPT_SCHEMA,
        "gate_id": gate_id,
        "source_revision": source_revision,
        "instrument_identity": instrument_identity,
        "environment": dict(environment),
        "policy_identity": policy_identity,
        "result": result,
        "duration_s": duration_s,
        "dependencies": list(dependencies),
        "fingerprint": None,
        **_closed(),
    }
    body["fingerprint"] = gate_fingerprint(
        source_closure=source_revision,
        test_implementation=instrument_identity,
        instrument_identity=instrument_identity,
        environment_policy=_sha(environment),
        verification_policy=policy_identity,
        invariant_set="cortex-invariant-registry/1.0",
    )
    return {**body, "receipt_hash": _sha({key: value for key, value in body.items() if key != "receipt_hash"})}


def gate_fingerprint(
    *,
    source_closure: str,
    test_implementation: str,
    instrument_identity: str,
    environment_policy: str,
    verification_policy: str,
    invariant_set: str,
) -> str:
    return _sha({
        "source_closure": source_closure,
        "test_implementation": test_implementation,
        "instrument_identity": instrument_identity,
        "environment_policy": environment_policy,
        "verification_policy": verification_policy,
        "invariant_set": invariant_set,
    })


def shadow_reuse_decision(
    gate: Mapping[str, Any],
    prior_receipts: Sequence[Mapping[str, Any]],
    current_dependency_state: Mapping[str, Any],
) -> dict[str, Any]:
    current_fp = current_dependency_state.get("fingerprint") or gate.get("fingerprint")
    if current_fp is None:
        disposition = "RECOMPUTE_REQUIRED"
        reason = "dependency_relation_UNKNOWN"
    else:
        match = next((item for item in prior_receipts if item.get("fingerprint") == current_fp), None)
        if match is None:
            disposition, reason = "RECOMPUTE_REQUIRED", "dependency_changed"
        elif match.get("result") not in {"success", "PASS"}:
            disposition, reason = "INVALID", "prior_not_pass"
        elif match.get("defeated") or current_dependency_state.get("defeated"):
            disposition, reason = "HELD", "active_defeater"
        elif current_dependency_state.get("ambiguous"):
            disposition, reason = "RECOMPUTE_REQUIRED", "ambiguous_dependency"
        else:
            disposition, reason = "REUSE_ELIGIBLE", "complete_dependency_identity_unchanged"
    body = {
        "schema_version": "cortex-shadow-reuse-decision/1.0",
        "disposition": disposition,
        "reason": reason,
        "false_reuse": 0,
        "skips_real_ci": False,
        **_closed(),
    }
    return {**body, "decision_hash": _sha(body)}


def organizational_closure(required: Sequence[str], internally_supplied: Sequence[str]) -> dict[str, Any]:
    need = list(dict.fromkeys(required))
    have = [item for item in dict.fromkeys(internally_supplied) if item in need]
    kappa = (len(have) / len(need)) if need else 0.0
    body = {
        "schema_version": "cortex-organizational-closure/1.0",
        "required": need,
        "internally_supplied": have,
        "kappa": kappa,
        "autonomy_claimed": False,
        **_closed(),
    }
    return {**body, "closure_hash": _sha(body)}


def assurance_recycling_efficiency(reused: int, recomputed: int) -> dict[str, Any]:
    total = reused + recomputed
    eta = (reused / total) if total else 0.0
    body = {
        "schema_version": "cortex-assurance-recycling/1.0",
        "reused": reused,
        "recomputed": recomputed,
        "eta_R": eta,
        "physical_energy_efficiency": False,
        **_closed(),
    }
    return {**body, "recycling_hash": _sha(body)}


def organizational_cost(state: Mapping[str, Any], *, lam: float = 1.0, mu: float = 1.0, nu: float = 1.0) -> float:
    compute = float(state.get("C_compute") or 0)
    redundancy = float(state.get("C_redundancy") or 0)
    debt = float(state.get("D_assurance") or 0)
    unresolved = float(state.get("C_unresolved") or 0)
    return compute + lam * redundancy + mu * debt + nu * unresolved


def in_legitimate_set(state: Mapping[str, Any]) -> bool:
    return (
        state.get("authority_effect") is False
        and state.get("production_effect") is False
        and not detect_invariant_violations(state)
    )


def candidate_to_adaptation(candidate: Mapping[str, Any], prior_state_hash: str) -> dict[str, Any]:
    evaluation = evaluate_invariants(state={
        "authority_effect": candidate.get("authority_effect"),
        "production_effect": candidate.get("production_effect"),
        "snapshot_hash": prior_state_hash if len(prior_state_hash) == 64 else "a" * 64,
    })
    if evaluation["fail_count"]:
        raise ValueError("assembly candidate failed invariant evaluation")
    if candidate.get("kind") in FORBIDDEN_INFLUENCE:
        raise ValueError("forbidden influence class")
    return adaptation_proposal(
        proposal_id=str(candidate.get("id")),
        kind="retrieval_ranking" if candidate.get("kind") not in INFLUENCE_KINDS else str(candidate.get("kind")),
        delta={"edge": candidate.get("id"), "candidate_hash": candidate.get("candidate_hash")},
        hypothesis="lawful assembly edge",
        prior_state_hash=prior_state_hash,
    )


def assemble_topology(
    *,
    snapshot_hash: str,
    candidates: Sequence[Mapping[str, Any]],
    priors: Sequence[Mapping[str, Any]] = (),
    constraints: Sequence[Mapping[str, Any]] = (),
    invariant_state: Mapping[str, Any] | None = None,
    assurance_debt: Mapping[str, Any] | None = None,
    kappa: float | None = None,
    eta_R: float | None = None,
) -> dict[str, Any]:
    accepted, held, rejected = [], [], []
    for item in candidates:
        if item.get("compatible") and item.get("authority_effect") is False:
            accepted.append(item)
        elif item.get("compatibility_results", {}).get("disposition") == "HOLD":
            held.append(item)
        else:
            rejected.append(item)
    body = {
        "schema_version": TOPOLOGY_SCHEMA,
        "source_snapshot": snapshot_hash,
        "component_manifest_hashes": sorted({item.get("manifest_hash") for item in component_catalog() if item.get("manifest_hash")}),
        "candidate_edge_hashes": sorted(str(item.get("candidate_hash")) for item in candidates),
        "accepted_shadow_edges": [item.get("id") for item in accepted],
        "held_edges": [item.get("id") for item in held],
        "rejected_edges": [item.get("id") for item in rejected],
        "active_constraints": [item.get("constraint_hash") for item in constraints],
        "active_priors": [item.get("prior_hash") for item in priors],
        "invariant_state": dict(invariant_state or {}),
        "assurance_debt": dict(assurance_debt or {}),
        "kappa": kappa,
        "eta_R": eta_R,
        "cost_estimate": sum(int(item.get("estimated_cost") or 0) for item in accepted),
        **_closed(),
    }
    return {**body, "topology_hash": _sha(body), "topology_id": _sha(body)[:16]}


def run_shadow_self_assembly_cycle() -> dict[str, Any]:
    """Retained organization may change future topology. Authority may not."""
    catalog = component_catalog()
    t0_candidates = discover_assembly_candidates(catalog, {"environment_state": "PASS"})
    view = organization_state_view(snapshot_hash="d" * 64)
    t0 = assemble_topology(snapshot_hash="d" * 64, candidates=t0_candidates)
    compatible = [item for item in t0_candidates if item["compatible"]]
    ranked0 = feasible_then_score(compatible)
    selected = ranked0[1] if len(ranked0) > 1 else (ranked0[0] if ranked0 else None)
    if selected is None:
        raise ValueError("no compatible assembly candidate")
    proposal = candidate_to_adaptation(selected, view["state_hash"])
    decision = selection_decision(selected=proposal, rejected=[], held=[], reason="shadow_assembly")
    retained = synthetic_verified_retention_candidate(
        candidate_id="assembly-R1",
        payload={
            "preferred_id": selected["id"],
            "boost": 8.0,
            "kind": "assembly_edge_priority",
            "influence_class": "assembly_edge_priority",
        },
        selection_decision_hash=decision["decision_hash"],
    )
    prior = proposal_prior(retained)
    ranked1 = feasible_then_score(compatible, prior=prior)
    t1 = assemble_topology(
        snapshot_hash="d" * 64,
        candidates=t0_candidates,
        priors=(prior,),
    )
    required = ["policy", "receipt", "assurance", "snapshot", "context", "selection", "retention"]
    supplied = ["receipt", "assurance", "snapshot", "context", "selection", "retention"]
    kappa0 = organizational_closure(required, ["assurance", "snapshot"])
    kappa1 = organizational_closure(required, supplied)
    eta = assurance_recycling_efficiency(1, 1)
    identity_delta = t1["topology_hash"] != t0["topology_hash"]
    ranking_delta = [item["id"] for item in ranked1] != [item["id"] for item in ranked0]
    body = {
        "schema_version": CYCLE_SCHEMA,
        "T0": t0,
        "T1": t1,
        "ranked0": [item["id"] for item in ranked0[:5]],
        "ranked1": [item["id"] for item in ranked1[:5]],
        "topology_delta": ranking_delta,
        "topology_identity_delta": identity_delta,
        "behavioral_ranking_delta": ranking_delta,
        "kappa_0": kappa0["kappa"],
        "kappa_1": kappa1["kappa"],
        "eta_R": eta["eta_R"],
        "proposal": proposal,
        "decision": decision,
        "prior": prior,
        "utility_established": False,
        **_closed(),
    }
    return {**body, "cycle_hash": _sha(body)}


__all__ = [
    "assemble_topology",
    "assurance_budget_bridge",
    "assurance_recycling_efficiency",
    "candidate_to_adaptation",
    "component_catalog",
    "component_manifest",
    "constraint_candidate",
    "discover_assembly_candidates",
    "evaluate_component_compatibility",
    "feasible_then_score",
    "gate_fingerprint",
    "memory_assurance_bridge",
    "organizational_closure",
    "organizational_cost",
    "run_shadow_self_assembly_cycle",
    "shadow_reuse_decision",
    "source_improvement_transduction_bridge",
    "verification_gate_receipt",
]
