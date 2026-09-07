"""GSO-IIb metabolic assembly: zero model calls, shadow only."""
from __future__ import annotations

import hashlib
import json

from cortex.assembly import (
    assemble_topology,
    assurance_budget_bridge,
    assurance_recycling_efficiency,
    component_catalog,
    constraint_candidate,
    discover_assembly_candidates,
    evaluate_component_compatibility,
    feasible_then_score,
    in_legitimate_set,
    memory_assurance_bridge,
    organizational_closure,
    organizational_cost,
    run_shadow_self_assembly_cycle,
    shadow_reuse_decision,
    source_improvement_transduction_bridge,
    verification_gate_receipt,
)
from cortex.invariants import detect_invariant_violations, freeze_recovery_policy
from cortex.shadow_organization import organization_state_view, recover_from_corrupted_state
from cortex.source_improvement import CONTRACT_SCHEMA, RESULT_SCHEMA, verify_source_improvement_contract


def test_manifests_hash_deterministically():
    first = component_catalog()
    second = component_catalog()
    assert [item["manifest_hash"] for item in first] == [item["manifest_hash"] for item in second]
    assert all(item["authority_effect"] is False and item["production_effect"] is False for item in first)
    ids = {item["component_id"] for item in first}
    assert {"memory_projection", "assurance", "transduction_policy", "shadow_organization"} <= ids


def test_compatible_and_incompatible_edges():
    catalog = {item["component_id"]: item for item in component_catalog()}
    ok = evaluate_component_compatibility(
        catalog["transduction_policy"],
        catalog["transduction_receipt"],
        {"environment_state": "PASS", "claims": [
            {"claim_id": "transduction.prospective_policy_closure", "status": "VERIFIED", "active_defeaters": []},
            {"claim_id": "transduction.compiled_artifact_binding", "status": "POSITIVE_WITHIN_DECLARED_WORKLOAD", "active_defeaters": []},
        ]},
    )
    assert ok["compatible"] is True
    assert ok["disposition"] == "ACCEPT"
    bad = evaluate_component_compatibility(catalog["memory_budget"], catalog["transduction_policy"])
    assert bad["compatible"] is False
    discovered = discover_assembly_candidates()
    assert all(item["compatible"] is False for item in discovered)
    assert any(item["compatibility_results"]["gates"]["environment"] == "UNKNOWN" for item in discovered)


def test_schema_and_environment_gates_fail_closed():
    catalog = {item["component_id"]: item for item in component_catalog()}
    source = dict(catalog["transduction_policy"])
    source["output_schemas"] = ["wrong/schema"]
    source.pop("manifest_hash")
    source["manifest_hash"] = hashlib.sha256(
        json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    mismatch = evaluate_component_compatibility(
        source,
        catalog["transduction_receipt"],
        {"environment_state": "PASS", "claims": [
            {"claim_id": "transduction.prospective_policy_closure", "status": "VERIFIED", "active_defeaters": []},
            {"claim_id": "transduction.compiled_artifact_binding", "status": "VERIFIED", "active_defeaters": []},
        ]},
    )
    assert mismatch["gates"]["type"] == "PASS"
    assert mismatch["gates"]["schema"] == "FAIL"
    assert mismatch["disposition"] == "REJECT"
    not_tested = evaluate_component_compatibility(
        catalog["context_packet"], catalog["shadow_organization"], {"environment_state": "NOT_TESTED"}
    )
    assert not_tested["gates"]["environment"] == "UNKNOWN"
    assert not_tested["disposition"] == "HOLD"


def test_unknown_assurance_holds_edge():
    catalog = {item["component_id"]: item for item in component_catalog()}
    held = evaluate_component_compatibility(
        catalog["transduction_policy"],
        catalog["transduction_receipt"],
        {"claims": [{"claim_id": "transduction.prospective_policy_closure", "status": "HELD", "active_defeaters": []}]},
    )
    assert held["compatible"] is False
    assert held["disposition"] == "HOLD"
    unknown = evaluate_component_compatibility(
        catalog["transduction_policy"],
        catalog["transduction_receipt"],
        {"environment_state": "UNKNOWN"},
    )
    assert unknown["compatible"] is False
    assert unknown["disposition"] == "HOLD"


def test_authority_and_production_cannot_form_or_activate_edges():
    catalog = {item["component_id"]: item for item in component_catalog()}
    source = dict(catalog["transduction_policy"])
    source["authority_effect"] = True
    denied = evaluate_component_compatibility(source, catalog["transduction_receipt"])
    assert denied["gates"]["authority"] == "FAIL"
    target = dict(catalog["shadow_organization"])
    target["production_effect"] = True
    prod = evaluate_component_compatibility(catalog["context_packet"], target)
    assert prod["compatible"] is False


def test_self_assembly_cycle_changes_topology_without_authority():
    cycle = run_shadow_self_assembly_cycle()
    assert cycle["topology_delta"] is True
    assert cycle["behavioral_ranking_delta"] is True
    assert cycle["ranked0"] != cycle["ranked1"]
    assert cycle["T0"]["topology_hash"] != cycle["T1"]["topology_hash"]
    assert cycle["authority_effect"] is False
    assert cycle["production_effect"] is False
    assert cycle["utility_established"] is False
    assert cycle["kappa_1"] >= cycle["kappa_0"]
    assert cycle["prior"]["authority_effect"] is False


def test_failure_constraint_is_scoped():
    windows = constraint_candidate(
        originating_failure_receipt="f1",
        failure_class="PATCH_APPLICATION_FAILURE",
        subject="a.py",
        environment={"os_family": "Windows"},
        instrument="isolated-worktree",
        policy="p1",
        applicability={"os_family": "Windows"},
    )
    win_edge = {"id": "win", "kind": "assembly_edge_priority", "compatible": True, "authority_effect": False, "production_effect": False, "environment": {"os_family": "Windows"}, "base_score": 5}
    linux_edge = {"id": "linux", "kind": "assembly_edge_priority", "compatible": True, "authority_effect": False, "production_effect": False, "environment": {"os_family": "Linux"}, "base_score": 5}
    scored = feasible_then_score([win_edge, linux_edge], constraints=(windows,))
    by_id = {item["id"]: item["score"] for item in scored}
    assert by_id["linux"] > by_id["win"]


def test_hard_constraint_cannot_be_compensated_by_score():
    candidate = {
        "id": "candidate",
        "kind": "assembly_edge_priority",
        "compatible": True,
        "authority_effect": False,
        "production_effect": False,
        "environment": {"os_family": "Windows"},
        "base_score": 10_000,
    }
    constraint = {
        "kind": "assembly_edge_priority",
        "environment": {"os_family": "Windows"},
        "infeasible": True,
    }
    assert feasible_then_score([candidate], constraints=(constraint,)) == []


def test_claim_degradation_excludes_memory_but_keeps_history():
    memory = {"memory_id": "m1", "claim_id": "c1", "G_M": 1}
    active = memory_assurance_bridge(memory, [{"claim_id": "c1", "status": "POSITIVE_WITHIN_DECLARED_WORKLOAD", "active_defeaters": []}])
    assert active["active_guidance"] is True
    held = memory_assurance_bridge(memory, [{"claim_id": "c1", "status": "HELD", "active_defeaters": []}])
    assert held["active_guidance"] is False
    assert held["historical_retained"] is True
    assert held["deleted"] is False
    defeated = memory_assurance_bridge(memory, [{"claim_id": "c1", "status": "VERIFIED", "active_defeaters": ["x"]}])
    assert defeated["active_guidance"] is False


def test_assurance_debt_contracts_freedom_without_granting_authority():
    tight = assurance_budget_bridge({"noncompensatory_meet": "HELD", "dimensions": {"environment": "UNKNOWN", "instrument": "HELD", "replication": "FAIL", "source": "UNKNOWN"}})
    assert tight["adaptation_freedom"] == 0
    assert "narrower_applicability" in tight["narrowing"]
    assert tight["authority_granted"] is False
    strong = assurance_budget_bridge({"noncompensatory_meet": "PASS", "dimensions": {"environment": "PASS"}})
    assert strong["authority_granted"] is False
    assert strong["authority_effect"] is False


def test_ci_receipt_and_reuse_decisions():
    env = {"os_family": "Linux"}
    receipt = verification_gate_receipt(
        gate_id="pytest",
        source_revision="abc",
        instrument_identity="pytest",
        environment=env,
        policy_identity="ci",
        result="success",
        dependencies=("cortex/assembly.py",),
    )
    assert receipt["receipt_hash"]
    same = shadow_reuse_decision(receipt, [receipt], {"fingerprint": receipt["fingerprint"]})
    assert same["disposition"] == "REUSE_ELIGIBLE"
    assert same["skips_real_ci"] is False
    changed = shadow_reuse_decision(receipt, [receipt], {"fingerprint": "0" * 64})
    assert changed["disposition"] == "RECOMPUTE_REQUIRED"
    ambiguous = shadow_reuse_decision(receipt, [receipt], {"fingerprint": receipt["fingerprint"], "ambiguous": True})
    assert ambiguous["disposition"] == "RECOMPUTE_REQUIRED"
    unknown = shadow_reuse_decision({}, [], {})
    assert unknown["disposition"] == "RECOMPUTE_REQUIRED"


def test_stale_snapshot_and_superseded_evidence_block_topology():
    catalog = component_catalog()
    stale = discover_assembly_candidates(catalog, {"superseded_evidence": True})
    assert all(item["compatible"] is False for item in stale)
    topo = assemble_topology(snapshot_hash="e" * 64, candidates=stale)
    assert topo["accepted_shadow_edges"] == []
    reconstructed = assemble_topology(snapshot_hash="e" * 64, candidates=stale)
    assert reconstructed["topology_hash"] == topo["topology_hash"]


def test_assembly_cannot_self_authorize_or_widen_freedom():
    catalog = {item["component_id"]: item for item in component_catalog()}
    edge = evaluate_component_compatibility(catalog["shadow_organization"], catalog["shadow_organization"])
    assert edge["compatible"] is False
    assert run_shadow_self_assembly_cycle()["authority_effect"] is False
    assert in_legitimate_set({"authority_effect": False, "production_effect": False, "snapshot_hash": "a" * 64})
    assert organizational_cost({"C_compute": 1, "D_assurance": 1}) > 0
    view = organization_state_view(snapshot_hash="f" * 64)
    view["authority_effect"] = True
    recovered = recover_from_corrupted_state(view, freeze_recovery_policy())
    assert recovered["recovered_state"]["adaptation_freedom"] == 0
    assert recovered["authority_leakage"] == 0


def test_kappa_and_eta_are_deterministic():
    first = organizational_closure(["a", "b", "c"], ["a", "c"])
    second = organizational_closure(["a", "b", "c"], ["a", "c"])
    assert first["kappa"] == second["kappa"] == 2 / 3
    assert first["autonomy_claimed"] is False
    rec = assurance_recycling_efficiency(3, 1)
    assert rec["eta_R"] == 0.75
    assert rec["physical_energy_efficiency"] is False


def test_source_improvement_v1_preserved_and_v2_bridge_declared():
    assert CONTRACT_SCHEMA == "cortex-source-improvement-preregistration/1.0"
    assert RESULT_SCHEMA == "cortex-source-improvement-result/1.0"
    assert verify_source_improvement_contract({"schema_version": "nope"})["valid"] is False
    bridge = source_improvement_transduction_bridge()
    assert bridge["historical_v1"]["rewritten"] is False
    assert bridge["future_v2"]["on_transduction_policy"] is True


def test_topology_corruption_recovers_from_state():
    topo_state = {
        "schema_version": "cortex-organization-state-view/1.0",
        "snapshot_hash": "a" * 64,
        "priors": [{"active": True, "authority_effect": True, "production_effect": False}],
        "authority_effect": False,
        "production_effect": False,
        "adaptation_authorized": False,
    }
    assert detect_invariant_violations(topo_state)
    receipt = recover_from_corrupted_state(topo_state, freeze_recovery_policy())
    assert receipt["authority_leakage"] == 0
    assert "disturbance" not in receipt
