"""GSI-II.2 proof-chain controls. Deterministic; zero provider calls."""
from pathlib import Path

import pytest

from cortex.autonomous_improvement import AutonomyPolicyEnvelope, issue_autonomy_policy
from cortex.coding_workspace import _file_hash, _git
from cortex.invariants import evaluate_gsi_constitution, load_invariant_registry
from cortex.self_improvement import (
    GovernedImprovement, REALIZED_GENERATION_SCHEMA,
    _sealed,
    bounded_dependency_identity,
    cumulative_improvement_disposition,
    failure_causality,
    failure_exclusion_predicates,
)
from test_gsi_ii import contract, freeze, payload
from test_gsi_ii1 import rank_contract, rank_payload
from test_v100_alpha8_autonomy import V100Alpha8AutonomyTests as _HostFixture


@pytest.fixture
def proof_host():
    fixture = _HostFixture()
    fixture.setUp()
    _git(fixture.host, ["config", "core.autocrlf", "false"])
    (fixture.host / "app" / "value.txt").write_bytes(b"bad\n")
    (fixture.host / "app" / "rank.txt").write_bytes(b"low\n")
    _git(fixture.host, ["add", "-A"])
    _git(fixture.host, ["commit", "-qm", "gsi ii2 fixture"])
    canary = ({"id": "canary", "argv": ["{python}", "-c", "raise SystemExit(0)"],
               "timeout_seconds": 5},)
    policy = issue_autonomy_policy(
        fixture.store, fixture.repo,
        AutonomyPolicyEnvelope(
            principal_id="operator", policy_id="gsi-ii2", allowed_path_prefixes=("app/",),
            allow_auto_promotion=True, allow_recursive_generation=True, canary_steps=canary,
        ),
        secret=fixture.secret,
    )
    coordinator = GovernedImprovement(
        fixture.store, fixture.repo, fixture.host,
        policy_receipt_hash=policy["receipt_hash"], secret=fixture.secret,
    )
    yield coordinator
    fixture.tearDown()


def _rank_freeze(host, holdout_id):
    opportunity = host.diagnose(subject="rank", contract=rank_contract(), metric="task_success", threshold=1)
    return host.freeze(
        opportunity["receipt_hash"], development=rank_contract(), holdout=rank_contract("holdout"),
        holdout_id=holdout_id,
    )


def test_unknown_constitutional_evidence_is_held():
    verdict = evaluate_gsi_constitution({})
    assert verdict["status"] == "HELD"
    assert set(verdict["checks"].values()) == {"UNKNOWN"}


def test_locally_claimed_pass_cannot_replace_registry_evaluation():
    registry = load_invariant_registry()
    registry["invariants"] = [row for row in registry["invariants"]
                              if row["invariant_id"] != "INV-EVALUATOR-INDEPENDENCE"]
    evidence = dict.fromkeys((
        "measured_opportunity_evidence", "evaluator_unchanged", "experiment_preceded_candidate",
        "noncompensatory_gates", "holdout_capability_separated",
        "failure_constraints_causally_scoped", "generation_not_self_authorized",
        "cumulative_claim_closed", "authority_unchanged", "protected_surface_unchanged",
    ), True)
    verdict = evaluate_gsi_constitution(evidence, registry=registry)
    assert verdict["checks"]["INV-EVALUATOR-INDEPENDENCE"] == "UNKNOWN"
    assert verdict["status"] == "HELD"


def test_stale_head_blocks_promotion(proof_host):
    experiment = freeze(proof_host, holdout_id="stale-head")
    trial = proof_host.run(experiment["receipt_hash"], payload)
    _git(proof_host.root, ["commit", "--allow-empty", "-qm", "drift"])
    with pytest.raises(PermissionError, match="PROMOTION_HELD_STALE_BASELINE"):
        proof_host.promote_verified(trial["receipt_hash"])


def test_control_surface_drift_blocks_promotion(proof_host):
    experiment = freeze(proof_host, holdout_id="surface-drift")
    trial = proof_host.run(experiment["receipt_hash"], payload)
    (proof_host.root / "untracked-drift.txt").write_text("drift", encoding="utf-8")
    with pytest.raises(PermissionError, match="control_surface_changed"):
        proof_host.promote_verified(trial["receipt_hash"])


def test_exact_evaluated_artifact_is_promoted_and_remeasured(proof_host):
    experiment = freeze(proof_host, holdout_id="exact-artifact")
    trial = proof_host.run(experiment["receipt_hash"], payload)
    promotion = proof_host.promote_verified(trial["receipt_hash"])
    obj = promotion["object"]
    assert obj["evaluated_artifact_hash"] == obj["promoted_artifact_hash"]
    assert obj["exact_artifact_preserved"] is True
    assert obj["promoted_comparison"]["status"] == "REPAIR_MEASURED"
    assert obj["canonical_promotion_membrane"] is True


def test_promoted_state_metric_failure_rolls_back(proof_host, monkeypatch):
    experiment = freeze(proof_host, holdout_id="promotion-regression")
    trial = proof_host.run(experiment["receipt_hash"], payload)
    stale_measurement = proof_host.remeasure(experiment["receipt_hash"])
    monkeypatch.setattr(proof_host, "remeasure", lambda _receipt: stale_measurement)
    promotion = proof_host.promote_verified(trial["receipt_hash"])["object"]
    assert promotion["rolled_back"] is True
    assert promotion["status"] == "rolled_back_remeasurement_failed"
    assert (proof_host.root / "app" / "value.txt").read_bytes() == b"bad\n"


def test_dependency_change_requires_new_identity(tmp_path: Path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("import app.dep\n", encoding="utf-8")
    (tmp_path / "app" / "dep.py").write_text("VALUE = 1\n", encoding="utf-8")
    before = bounded_dependency_identity(tmp_path, ["app/main.py"])
    (tmp_path / "app" / "dep.py").write_text("VALUE = 2\n", encoding="utf-8")
    after = bounded_dependency_identity(tmp_path, ["app/main.py"])
    assert before["files"]["app/main.py"] == after["files"]["app/main.py"]
    assert before["dependency_hash"] != after["dependency_hash"]


@pytest.mark.parametrize("failure,causality", [
    ("ENVIRONMENT_MISMATCH", "ENVIRONMENT_CAUSAL"),
    ("INSTRUMENT_UNRESOLVED", "INSTRUMENT_CAUSAL"),
    ("POLICY_BINDING_FAILURE", "POLICY_CAUSAL"),
    ("EVALUATOR_REJECTION", "CANDIDATE_CAUSAL"),
])
def test_failure_causality_controls_exclusion(failure, causality):
    trial = {"errors": [], "candidates": {"development": {"receipt": {"failure_attribution": failure}}}}
    assert failure_causality(trial) == causality
    predicates = failure_exclusion_predicates(payload(), causality)
    assert bool(predicates) is (causality == "CANDIDATE_CAUSAL")


def test_experiment_evidence_is_bounded_not_active_memory(proof_host):
    first = freeze(proof_host, holdout_id="evidence-a")
    retained = proof_host.recycle(proof_host.run(first["receipt_hash"], payload)["receipt_hash"])["object"]
    assert retained["influence_class"] == "EXPERIMENT_EVIDENCE"
    assert retained["active_guidance"] is False
    assert retained["memory_admission_authorized"] is False
    assert retained["authority_effect"] is False


def test_challenged_experiment_evidence_is_not_reused(proof_host):
    first = freeze(proof_host, holdout_id="challenged-evidence-a")
    retained = proof_host.recycle(proof_host.run(first["receipt_hash"], payload)["receipt_hash"])
    proof_host.challenge_experiment_evidence(retained["receipt_hash"], reason="bounded contradiction")
    second = freeze(proof_host, contract("holdout-alt"), holdout_id="challenged-evidence-b")
    seen = []
    proof_host.run(second["receipt_hash"], lambda context: seen.append(context) or payload())
    assert seen[0]["verified_improvement_evidence"] == []


def test_holdout_capability_is_absent_from_candidate_context(proof_host):
    experiment = freeze(proof_host, holdout_id="capability-separation")
    exp = experiment["object"]
    assert not set(exp["candidate_capability_set"]) & set(exp["holdout_capability_set"])
    seen = []
    proof_host.run(experiment["receipt_hash"], lambda context: seen.append(context) or payload())
    assert "holdout" not in str(seen[0]).lower()
    assert exp["live_provider_holdout_eligible"] is False


def test_unpromoted_trial_is_candidate_generation(proof_host):
    trial = proof_host.run(freeze(proof_host, holdout_id="candidate-generation")["receipt_hash"], payload)
    generation = proof_host.record_generation(
        parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1"
    )["object"]
    assert generation["generation_state"] == "CANDIDATE_GENERATION"
    assert generation["status"] == "HELD"


def test_incompatible_utility_contracts_are_not_scalar_summed():
    common = dict(
        generation_state="REALIZED_GENERATION", authority_leakage=0, evaluator_mutation=0,
        policy_mutation=0, status="IMPROVED_WITHIN_DECLARED_WORKLOAD", delta_holdout=1,
        holdout_degradation_tolerance=0, parent_generation="G0", candidate_generation="G1",
        delta_dev=1,
    )
    g1 = _sealed(REALIZED_GENERATION_SCHEMA, **common, utility_contract_hash="a")
    g2 = _sealed(REALIZED_GENERATION_SCHEMA, **{
        **common, "parent_generation": "G1", "candidate_generation": "G2",
        "utility_contract_hash": "b",
    })
    result = cumulative_improvement_disposition([g1, g2])
    assert result["utility_contracts_compatible"] is False
    assert result["cumulative_scalar_gain"] is None
    assert len(result["cumulative_utility_vector"]) == 2


def test_compatible_utility_contracts_allow_bounded_scalar():
    common = dict(
        generation_state="REALIZED_GENERATION", authority_leakage=0, evaluator_mutation=0,
        policy_mutation=0, status="IMPROVED_WITHIN_DECLARED_WORKLOAD", delta_holdout=1,
        holdout_degradation_tolerance=0, delta_dev=1, utility_contract_hash="same",
    )
    g1 = _sealed(REALIZED_GENERATION_SCHEMA, **common, parent_generation="G0", candidate_generation="G1")
    g2 = _sealed(REALIZED_GENERATION_SCHEMA, **common, parent_generation="G1", candidate_generation="G2")
    result = cumulative_improvement_disposition([g1, g2])
    assert result["utility_contracts_compatible"] is True
    assert result["cumulative_scalar_gain"] == 2


def test_canonical_store_chain_reconstructs_realized_generations(proof_host):
    exp1 = freeze(proof_host, holdout_id="chain-g1")
    trial1 = proof_host.run(exp1["receipt_hash"], payload)
    promotion1 = proof_host.promote_verified(trial1["receipt_hash"])
    g1 = proof_host.record_generation(
        parent="G0", trial_receipt=trial1["receipt_hash"], candidate_generation="G1",
        promotion_receipt=promotion1["receipt_hash"],
    )
    exp2 = _rank_freeze(proof_host, "chain-g2")
    trial2 = proof_host.run(exp2["receipt_hash"], rank_payload)
    promotion2 = proof_host.promote_verified(trial2["receipt_hash"])
    g2 = proof_host.record_generation(
        parent="G1", trial_receipt=trial2["receipt_hash"], candidate_generation="G2",
        parent_receipt=g1["receipt_hash"], promotion_receipt=promotion2["receipt_hash"],
    )
    result = proof_host.verify_cumulative_chain([g1["receipt_hash"], g2["receipt_hash"]])
    assert result["canonical_store_reconstructed"] is True
    assert result["cumulative_generation_mechanics_verified"] is True
    assert result["cumulative_self_improvement_established"] is False
    assert result["utility_contracts_compatible"] is False
    assert result["cumulative_scalar_gain"] is None


def test_canonical_chain_rejects_noncanonical_parent(proof_host):
    result = proof_host.verify_cumulative_chain(["0" * 64])
    assert result["cumulative_generation_mechanics_verified"] is False
    assert "canonical_chain_receipt_invalid" in result["errors"]


def test_target_identity_is_still_explicit(proof_host):
    experiment = freeze(proof_host, holdout_id="target-identity")["object"]
    assert experiment["subject_identity"] == {
        "app/value.txt": _file_hash(proof_host.root / "app/value.txt")
    }
    assert experiment["call_budget"] == 0


def test_rolled_back_promotion_is_not_realized(proof_host, monkeypatch):
    experiment = freeze(proof_host, holdout_id="rollback-generation")
    trial = proof_host.run(experiment["receipt_hash"], payload)
    stale = proof_host.remeasure(experiment["receipt_hash"])
    monkeypatch.setattr(proof_host, "remeasure", lambda _receipt: stale)
    promotion = proof_host.promote_verified(trial["receipt_hash"])
    generation = proof_host.record_generation(
        parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1",
        promotion_receipt=promotion["receipt_hash"],
    )["object"]
    assert promotion["object"]["rolled_back"] is True
    assert generation["generation_state"] == "CANDIDATE_GENERATION"
    assert generation["status"] == "HELD"


def test_source_discontinuity_and_parent_mismatch_break_chain(proof_host):
    exp1 = freeze(proof_host, holdout_id="cont-g1")
    trial1 = proof_host.run(exp1["receipt_hash"], payload)
    promotion1 = proof_host.promote_verified(trial1["receipt_hash"])
    g1 = proof_host.record_generation(
        parent="G0", trial_receipt=trial1["receipt_hash"], candidate_generation="G1",
        promotion_receipt=promotion1["receipt_hash"],
    )
    _git(proof_host.root, ["commit", "--allow-empty", "-qm", "break parent continuity"])
    exp2 = _rank_freeze(proof_host, "cont-g2")
    trial2 = proof_host.run(exp2["receipt_hash"], rank_payload)
    promotion2 = proof_host.promote_verified(trial2["receipt_hash"])
    g2 = proof_host.record_generation(
        parent="G1", trial_receipt=trial2["receipt_hash"], candidate_generation="G2",
        parent_receipt=g1["receipt_hash"], promotion_receipt=promotion2["receipt_hash"],
    )
    assert g2["object"]["generation_state"] == "CANDIDATE_GENERATION"
    assert "parent_source_continuity_failure" in g2["object"]["errors"]
    reconstructed = proof_host.verify_cumulative_chain([g1["receipt_hash"], g2["receipt_hash"]])
    assert reconstructed["cumulative_generation_mechanics_verified"] is False
    reversed_chain = proof_host.verify_cumulative_chain([g2["receipt_hash"], g1["receipt_hash"]])
    assert reversed_chain["cumulative_generation_mechanics_verified"] is False


def test_subject_mismatch_blocks_positive_evidence(proof_host):
    first = freeze(proof_host, holdout_id="pos-a")
    proof_host.recycle(proof_host.run(first["receipt_hash"], payload)["receipt_hash"])
    seen = []
    second = _rank_freeze(proof_host, "pos-b")
    proof_host.run(second["receipt_hash"], lambda context: seen.append(context) or rank_payload())
    assert seen[0]["verified_improvement_evidence"] == []


def test_authority_leakage_remains_zero(proof_host):
    trial = proof_host.run(freeze(proof_host, holdout_id="authority")["receipt_hash"], payload)
    promotion = proof_host.promote_verified(trial["receipt_hash"])
    generation = proof_host.record_generation(
        parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1",
        promotion_receipt=promotion["receipt_hash"],
    )["object"]
    assert trial["object"]["authority_leakage"] == 0
    assert trial["object"]["authority_effect"] is False
    assert promotion["object"]["authority_effect"] is False
    assert generation["authority_leakage"] == 0
    assert generation["generation_state"] == "REALIZED_GENERATION"


def test_source_improvement_v1_and_gso_remain_inert():
    from cortex.source_improvement import CONTRACT_SCHEMA, RESULT_SCHEMA
    import cortex.assembly as assembly
    assert CONTRACT_SCHEMA == "cortex-source-improvement-preregistration/1.0"
    assert RESULT_SCHEMA == "cortex-source-improvement-result/1.0"
    assert assembly.__doc__
