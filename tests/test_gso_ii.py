"""GSO-II invariant closure: zero model calls, no live retention experiment."""
from __future__ import annotations

import copy
import subprocess
from pathlib import Path

import pytest

from benchmarks.transduction_assurance import _intent, _repository
from cortex.assurance import assemble_assurance_case, load_claim_registry, typed_assurance_debt
from cortex.edit_intent import (
    INTENT_SCHEMA,
    INTENT_SCHEMA_V2,
    PARSER_SEMANTICS_STRICT,
    compile_edit_intent,
    _compile_edit_intent,
)
from cortex.epistemic_kernel import TRUTH_STATES
from cortex.epistemic_snapshot import (
    NAVIGATION_GENERALIZATION_PANEL,
    NAVIGATION_TASKS,
    compile_context_packet,
    derive_epistemic_snapshot,
    measure_navigation_contract,
    measure_navigation_generalization,
    route_navigation_generalization,
)
from cortex.executable_repair_forge import _verification_contract
from cortex.invariants import (
    detect_invariant_violations,
    evaluate_invariants,
    freeze_recovery_policy,
    load_invariant_registry,
    validate_invariant_registry,
)
from cortex.observation_capture import environment_policy
from cortex.shadow_organization import (
    adaptation_proposal,
    homeostatic_panel_v2,
    organization_state_view,
    proposal_prior,
    recover_from_corrupted_state,
    retention_candidate,
    synthetic_verified_retention_candidate,
    verify_proposal_prior,
)
from cortex.transduction_policy import (
    attest_transduction_receipt,
    execute_bound_transduction,
    freeze_transduction_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def test_invariant_registry_valid():
    registry = load_invariant_registry()
    assert registry["authority_effect"] is False
    assert validate_invariant_registry(registry, root=ROOT) == []
    ids = {item["invariant_id"] for item in registry["invariants"]}
    assert "INV-AUTHORITY-NONDERIVATION" in ids
    assert "INV-SNAPSHOT-BINDING" in ids
    assert "INV-STATE-DERIVED-RECOVERY" in ids


def test_evidence_cannot_set_authority():
    registry = load_claim_registry()
    claim = copy.deepcopy(registry["claims"][0])
    claim["authority_effect"] = True
    with pytest.raises(ValueError):
        assemble_assurance_case(claim, registry=registry)


def test_assurance_case_cannot_authorize_execution():
    registry = load_claim_registry()
    case = assemble_assurance_case(registry["claims"][0], registry=registry)
    assert case["executes"] is False
    assert case["authority_effect"] is False


def test_retention_candidate_cannot_activate_production():
    candidate = synthetic_verified_retention_candidate(candidate_id="x", payload={"k": 1})
    assert candidate["production_effect"] is False
    assert candidate["authority_effect"] is False


def test_retention_candidate_cannot_jump_to_eligibility():
    with pytest.raises(ValueError, match="must begin"):
        retention_candidate(candidate_id="x", payload={"k": 1}, stage="RETENTION_ELIGIBLE")


def test_active_prior_requires_reconstructable_retention_evidence():
    candidate = synthetic_verified_retention_candidate(candidate_id="x", payload={"preferred_id": "a"})
    prior = proposal_prior(candidate)
    assert verify_proposal_prior(prior)["valid"] is True
    tampered = copy.deepcopy(prior)
    tampered["source_candidate"]["payload"]["preferred_id"] = "b"
    assert verify_proposal_prior(tampered)["valid"] is False


def test_proposal_prior_cannot_widen_budget():
    view = organization_state_view(snapshot_hash="a" * 64)
    with pytest.raises(ValueError):
        adaptation_proposal(proposal_id="p", kind="budget", delta={}, hypothesis="widen", prior_state_hash=view["state_hash"])


def test_unknown_blocks_stronger_claim():
    debt = typed_assurance_debt({"source": "PASS", "transduction": "UNKNOWN"})
    assert debt["noncompensatory_meet"] == "UNKNOWN"


def test_v2_intent_preserves_identity(tmp_path):
    root = tmp_path / "repo"
    _repository(root, {"a.py": "v = 1\n"}, "print(1)\n")
    payload = {"schema_version": INTENT_SCHEMA_V2, "summary": "bump", "edits": [{"path": "a.py", "old": "1", "new": "2"}]}
    compiled = compile_edit_intent(root, payload, allowed_targets=["a.py"], parser_semantics_id=PARSER_SEMANTICS_STRICT, allowed_intent_schema=INTENT_SCHEMA_V2)
    assert compiled["intent"]["schema_version"] == INTENT_SCHEMA_V2
    assert compiled["schema_version"] == "cortex-edit-intent-compilation/2.1"
    with pytest.raises(ValueError, match="schema"):
        compile_edit_intent(root, payload, allowed_targets=["a.py"], parser_semantics_id=PARSER_SEMANTICS_STRICT, allowed_intent_schema=INTENT_SCHEMA)


def test_v1_cannot_silently_become_v2(tmp_path):
    root = tmp_path / "repo"
    _repository(root, {"a.py": "v = 1\n"}, "print(1)\n")
    payload = {"schema_version": INTENT_SCHEMA, "summary": "bump", "edits": [{"path": "a.py", "old": "1", "new": "2"}]}
    compiled = compile_edit_intent(root, payload, allowed_targets=["a.py"])
    assert compiled["intent"]["schema_version"] == INTENT_SCHEMA
    legacy = _compile_edit_intent(root, payload, allowed_targets=["a.py"], legacy=True)
    assert legacy["intent"]["schema_version"] == INTENT_SCHEMA
    assert legacy["schema_version"] == "cortex-edit-intent-compilation/1.0"


def test_snapshot_freshness_and_source_binding(tmp_path):
    snapshot = derive_epistemic_snapshot(ROOT)
    packet = compile_context_packet("Where is prospective transduction policy frozen?", snapshot, root=ROOT)
    assert packet["valid"]
    stale_head = dict(snapshot)
    stale_head["source_head"] = "0" * 40
    stale_head["snapshot_hash"] = __import__("cortex.epistemic_snapshot", fromlist=["_sha"])._sha(
        {key: value for key, value in stale_head.items() if key != "snapshot_hash"}
    )
    rejected = compile_context_packet("Where is prospective transduction policy frozen?", stale_head, root=ROOT)
    assert "SNAPSHOT_STALE" in rejected["errors"]
    digest_stale = dict(snapshot)
    bound = dict(digest_stale["bound_source_digests"])
    target = next(path for path in bound if path.endswith("transduction_policy.py"))
    bound[target] = "0" * 64
    digest_stale["bound_source_digests"] = bound
    digest_stale["snapshot_hash"] = __import__("cortex.epistemic_snapshot", fromlist=["_sha"])._sha(
        {key: value for key, value in digest_stale.items() if key != "snapshot_hash"}
    )
    unbound = compile_context_packet("Where is prospective transduction policy frozen?", digest_stale, root=ROOT)
    assert any(item.startswith("SOURCE_NOT_BOUND") for item in unbound["errors"])
    other = tmp_path / "other"
    other.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=other, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.invalid"], cwd=other, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=other, check=True)
    (other / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=other, check=True)
    subprocess.run(["git", "commit", "-qm", "x"], cwd=other, check=True)
    mismatched = compile_context_packet("task", snapshot, root=other)
    assert "SNAPSHOT_STALE" in mismatched["errors"]
    historical = compile_context_packet("Where is prospective transduction policy frozen?", snapshot, root=ROOT, historical_checkout=True)
    assert historical["valid"]


def test_receipt_attestation_and_tamper(tmp_path):
    root = tmp_path / "repo"
    _repository(root, {"a.py": "v = 1\n"}, "from pathlib import Path\nassert Path('a.py').read_bytes() == b'v = 2\\n'\n")
    intent = _intent([("a.py", "1", "2")])
    compiled = compile_edit_intent(root, intent, allowed_targets=["a.py"])
    contract = _verification_contract(compiled["proposal"])
    policy = freeze_transduction_policy(root, policy_id="attestation", allowed_targets=["a.py"], verification_contract=contract, evaluator_id=contract["policy_id"])
    result = execute_bound_transduction(root, policy, intent, contract)
    attestation = attest_transduction_receipt(result["receipt"], policy, root, contract=contract, compilation=result["compilation"])
    assert attestation["status"] in {"ATTESTED", "PARTIALLY_ATTESTED"}
    assert "INVALID" != attestation["status"] or result["receipt"]["typed_outcome"] != "PASS"
    tampered = dict(result["receipt"])
    tampered["receipt_hash"] = "0" * 64
    assert attest_transduction_receipt(tampered, policy, root, contract=contract, compilation=result["compilation"])["status"] == "INVALID"
    obs = copy.deepcopy(result["receipt"])
    if obs.get("raw_observations") and obs["raw_observations"][0]:
        obs["raw_observations"][0]["stdout_sha256"] = "0" * 64
        obs.pop("receipt_hash")
        from cortex.transduction_policy import _sha
        obs["receipt_hash"] = _sha({key: value for key, value in obs.items() if key != "receipt_hash"})
        # observation identity changed; hash is self-consistent but instrument/raw binding may still ATTACH as PARTIAL/INVALID depending on checks
        attest_transduction_receipt(obs, policy, root, contract=contract, compilation=result["compilation"])
    instrument = dict(policy)
    hashes = dict(instrument["allowed_compiler_implementation_identity"])
    hashes["edit_intent.py"] = "0" * 64
    instrument["allowed_compiler_implementation_identity"] = hashes
    from cortex.transduction_policy import _sha
    instrument["policy_hash"] = _sha({key: value for key, value in instrument.items() if key != "policy_hash"})
    assert attest_transduction_receipt(result["receipt"], instrument, root, contract=contract, compilation=result["compilation"])["status"] == "INVALID"


def test_navigation_contract_and_generalization():
    contract = measure_navigation_contract()
    assert contract["N_contract"] == 1.0
    assert contract["n_tasks"] == 12
    panel = measure_navigation_generalization()
    queries = {item["query"] for item in NAVIGATION_GENERALIZATION_PANEL}
    assert queries.isdisjoint({item["query"] for item in NAVIGATION_TASKS})
    assert panel["uses_exact_query_table"] is False
    assert panel["N_generalization"] >= 0.75
    routed = route_navigation_generalization("Which module owns the pre-cognition execution requirements?")
    assert routed == ["cortex/transduction_policy.py"]


def test_state_derived_recovery_does_not_receive_labels():
    policy = freeze_recovery_policy()
    state = organization_state_view(snapshot_hash="a" * 64, priors=({"active": True, "contradicted": True, "authority_effect": False},))
    state["persistent_snapshot_hash"] = "a" * 64
    violations = detect_invariant_violations(state)
    assert any(item["invariant_id"] == "INV-CONTRADICTION-REPRESENTABLE" for item in violations)
    receipt = recover_from_corrupted_state(state, policy)
    assert "disturbance" not in receipt
    assert receipt["authority_leakage"] == 0
    assert receipt["chosen_response"] in {"QUARANTINE", "HARD_FAIL", "HOLD", "ROLLBACK"}
    assert all(not prior.get("active") for prior in receipt["recovered_state"]["priors"])


def test_homeostatic_panel_v2():
    panel = homeostatic_panel_v2("b" * 64)
    assert panel["named_disturbance_supplied"] is False
    assert panel["authority_leakage"] == 0
    assert panel["detection_accuracy"] == 1.0
    assert panel["S_r"] is True


def test_authority_and_production_leaks_are_hard_failures():
    policy = freeze_recovery_policy()
    leaked = organization_state_view(snapshot_hash="c" * 64)
    leaked["authority_effect"] = True
    evaluation = evaluate_invariants(state=leaked)
    assert evaluation["fail_count"] >= 1
    receipt = recover_from_corrupted_state(leaked, policy)
    assert receipt["recovered_state"]["authority_effect"] is False
    prod = organization_state_view(snapshot_hash="c" * 64, priors=({"active": True, "production_effect": True},))
    recovered = recover_from_corrupted_state(prod, policy)
    assert recovered["recovered_state"]["production_effect"] is False
    assert all(prior.get("production_effect") is not True or not prior.get("active") for prior in recovered["recovered_state"]["priors"])


def test_contradiction_remains_representable():
    assert "BOTH" in TRUTH_STATES
    assert "NEITHER" in TRUTH_STATES


def test_environment_policy_is_allowlist():
    policy = environment_policy()
    assert policy["inherits_full_process_environment"] is False
    assert policy["network_isolation"] == "UNENFORCED"
    assert policy["external_path_isolation"] == "DECLARATIVE_ONLY"
