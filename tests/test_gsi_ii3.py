"""GSI-II.3 empirical-readiness controls. Zero provider calls."""
import pytest

from cortex.autonomous_improvement import AutonomyPolicyEnvelope, issue_autonomy_policy
from cortex.coding_workspace import _git
from cortex.self_improvement import (
    GovernedImprovement, comparison_schema_noncompensatory, holdout_content_hash,
    reconstruct_realized_delta, utility_family,
)
from test_gsi_ii import contract, freeze, payload
from test_v100_alpha8_autonomy import V100Alpha8AutonomyTests as _HostFixture


@pytest.fixture
def proof_host():
    fixture = _HostFixture()
    fixture.setUp()
    _git(fixture.host, ["config", "core.autocrlf", "false"])
    (fixture.host / "app" / "value.txt").write_bytes(b"bad\n")
    (fixture.host / "app" / "rank.txt").write_bytes(b"low\n")
    _git(fixture.host, ["add", "-A"])
    _git(fixture.host, ["commit", "-qm", "gsi ii3 fixture"])
    canary = ({"id": "canary", "argv": ["{python}", "-c", "raise SystemExit(0)"], "timeout_seconds": 5},)
    policy = issue_autonomy_policy(
        fixture.store, fixture.repo,
        AutonomyPolicyEnvelope(
            principal_id="operator", policy_id="gsi-ii3", allowed_path_prefixes=("app/",),
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


def test_noncompensatory_schema_does_not_mix_gates():
    assert comparison_schema_noncompensatory() is True


def test_same_holdout_content_different_label_is_rejected(proof_host):
    freeze(proof_host, holdout_id="label-a")
    with pytest.raises(ValueError, match="holdout content already reserved"):
        freeze(proof_host, holdout_id="label-b")


def test_fresh_partition_can_share_utility_family(proof_host):
    first = freeze(proof_host, holdout_id="family-a")
    second = freeze(proof_host, contract("holdout-alt"), holdout_id="family-b")
    assert first["object"]["utility_family_hash"] == second["object"]["utility_family_hash"]
    assert first["object"]["evaluation_partition_hash"] != second["object"]["evaluation_partition_hash"]
    assert first["object"]["holdout_content_hash"] != second["object"]["holdout_content_hash"]


def test_realized_delta_comes_from_post_promotion_measurement(proof_host):
    experiment = freeze(proof_host, holdout_id="realized-delta")
    trial = proof_host.run(experiment["receipt_hash"], payload)
    promotion = proof_host.promote_verified(trial["receipt_hash"])
    generation = proof_host.record_generation(
        parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1",
        promotion_receipt=promotion["receipt_hash"],
    )["object"]
    measurement = proof_host._resolve(
        promotion["object"]["remeasurement_receipt_hash"], "gsi_post_promotion_measurement"
    )["object"]
    reconstructed = reconstruct_realized_delta(
        trial["object"]["baseline"], measurement, experiment["object"]["primary_metric"]
    )
    assert generation["delta_dev"] == reconstructed["delta_dev"]
    assert generation["delta_holdout"] == reconstructed["delta_holdout"]
    assert generation["candidate_delta_dev"] == trial["object"]["comparison"]["delta_dev"]
    assert generation["authority_before_hash"] == generation["authority_after_hash"]
    assert generation["history_utility_established"] is False


def test_chain_invalid_when_generation_delta_disagrees(proof_host):
    experiment = freeze(proof_host, holdout_id="chain-delta")
    trial = proof_host.run(experiment["receipt_hash"], payload)
    promotion = proof_host.promote_verified(trial["receipt_hash"])
    generation = proof_host.record_generation(
        parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1",
        promotion_receipt=promotion["receipt_hash"],
    )
    tampered = dict(generation["object"])
    tampered["delta_dev"] = 99
    assert tampered["delta_dev"] != generation["object"]["delta_dev"]
    reconstructed = reconstruct_realized_delta(
        trial["object"]["baseline"],
        proof_host._resolve(promotion["object"]["remeasurement_receipt_hash"], "gsi_post_promotion_measurement")["object"],
        experiment["object"]["primary_metric"],
    )
    assert reconstructed["delta_dev"] != 99


def test_authority_state_is_bound_and_unchanged(proof_host):
    experiment = freeze(proof_host, holdout_id="authority-state")["object"]
    assert experiment["authority_state_hash"]
    assert experiment["authority_state"]["host_issued"] is True
    trial = proof_host.run(freeze(proof_host, contract("holdout-alt"), holdout_id="authority-state-2")["receipt_hash"], payload)
    assert trial["object"]["constitutional"]["checks"]["authority_invariance"] == "PASS"
    assert trial["object"]["constitutional"]["checks"]["INV-GENERATION-NONSELFAUTHORIZATION"] == "PASS"


def test_capability_manifests_are_disjoint(proof_host):
    experiment = freeze(proof_host, holdout_id="capabilities")["object"]
    assert experiment["holdout_capability_intersection"] == []
    assert experiment["holdout_capability_enforcement"] == "INTERFACE_ENFORCED"
    assert experiment["live_provider_holdout_eligible"] is False
    assert not set(experiment["candidate_capability_set"]) & set(experiment["holdout_capability_set"])


def test_abc_treatments_and_search_episode(proof_host):
    family = utility_family(task_family="fixture ranking", metric="task_success",
                            epsilon_dev=1, epsilon_holdout=1, holdout_degradation_tolerance=0)
    none = proof_host.freeze_treatment(arm="A", history_kind="NO_HISTORY",
                                       utility_family_hash=family["object_hash"])
    sham = proof_host.freeze_treatment(
        arm="B", history_kind="SHAM_HISTORY", utility_family_hash=family["object_hash"],
        history_items=[{"object_hash": "a" * 64, "applicability_valid": False,
                        "influence_class": "EXPERIMENT_EVIDENCE"}],
    )
    applicable = proof_host.freeze_treatment(
        arm="C", history_kind="APPLICABLE_HISTORY", utility_family_hash=family["object_hash"],
        history_items=[{"object_hash": "b" * 64, "applicability_valid": True,
                        "influence_class": "EXPERIMENT_EVIDENCE"}],
    )
    assert sham["object"]["history_items"][0]["applicability_valid"] is False
    assert applicable["object"]["history_items"][0]["applicability_valid"] is True
    assert none["object"]["live_execution_authorized"] is False
    trial = proof_host.run(freeze(proof_host, holdout_id="episode")["receipt_hash"], payload)
    episode = proof_host.record_search_episode(
        treatment_receipt=none["receipt_hash"], trial_receipt=trial["receipt_hash"],
        candidate_evaluations=2, model_calls=0,
    )["object"]
    assert episode["eta"] == 0
    assert episode["provider_calls"] == 0
    assert episode["history_utility_established"] is False
    with pytest.raises(ValueError, match="sham history"):
        proof_host.freeze_treatment(
            arm="B", history_kind="SHAM_HISTORY", utility_family_hash=family["object_hash"],
            history_items=[{"object_hash": "c" * 64, "applicability_valid": True}],
        )


def test_holdout_identity_ignores_human_label():
    family = "f" * 64
    first = holdout_content_hash(holdout=contract("holdout"), utility_family_hash=family,
                                 evaluator_identity=contract("holdout")["contract_hash"])
    second = holdout_content_hash(holdout=contract("holdout"), utility_family_hash=family,
                                  evaluator_identity=contract("holdout")["contract_hash"])
    alt = holdout_content_hash(holdout=contract("holdout-alt"), utility_family_hash=family,
                               evaluator_identity=contract("holdout-alt")["contract_hash"])
    assert first == second
    assert first != alt


def test_source_improvement_v1_still_distinct():
    from cortex.source_improvement import CONTRACT_SCHEMA, RESULT_SCHEMA
    assert CONTRACT_SCHEMA == "cortex-source-improvement-preregistration/1.0"
    assert RESULT_SCHEMA == "cortex-source-improvement-result/1.0"
