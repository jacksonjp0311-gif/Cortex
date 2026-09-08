"""GSI-II.5 execution-membrane controls; no provider calls."""
# ruff: noqa: F401,F811 -- proof_host is an imported pytest fixture.

import copy

import pytest

from cortex.causal_treatment import (
    ASSIGNMENT_SCHEMA,
    EXECUTION_CONTRACT_SCHEMA,
    RANDOMIZATION_SCHEMA,
    SHAM_MATCH_SCHEMA,
    TASK_SET_SCHEMA,
    assignment,
    execution_readiness,
    randomization_plan,
    sham_match,
    task_set,
    validate_randomization_plan,
    verify_execution_lock,
)
from cortex.self_improvement import _sealed
from test_gsi_ii import contract, freeze, payload
from test_gsi_ii3 import proof_host
from test_gsi_ii4 import build_empirical_bundle, readiness_components, runtime, task


def test_empirical_run_requires_execution_lock(proof_host):
    experiment = freeze(proof_host, holdout_id="ii5-missing-lock")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = proof_host.freeze_execution_contract(
        experiment["receipt_hash"],
        model_runtime=runtime(),
        task_set_hash="t" * 64,
        analysis_plan_hash=readiness_components()["analysis_plan"]["object_hash"],
        budgets={
            "candidate_budget": 1,
            "provider_call_budget": 1,
            "token_budget": 1000,
            "wall_clock_budget_seconds": 60,
        },
        sham_tolerances={
            "count": 0,
            "bytes": 100,
            "token_estimate": 25,
            "positive": 0,
            "constraints": 0,
        },
    )
    with pytest.raises(ValueError):
        proof_host.run_empirical(
            experiment["receipt_hash"],
            treatment["receipt_hash"],
            execution["receipt_hash"],
            "missing-assignment",
            payload,
        )


def test_readiness_rejects_generic_sealed_component():
    components = readiness_components()
    components["model_runtime"] = copy.deepcopy(components["model_runtime"])
    components["model_runtime"]["schema_version"] = "x/1.0"
    result = execution_readiness(
        components=components,
        implementation_ci="PASS",
        protocol_status="PROTOCOL_FROZEN",
        provider_calls=0,
        live_authorized=False,
    )
    assert result["empirical_readiness"] == "FAIL"
    assert "model_runtime" in result["invalid"]


def test_execution_lock_rejects_tampered_canonical_component():
    components = readiness_components()
    lock = _sealed(
        "cortex-gsi-execution-lock/1.0",
        protocol_preregistration_hash="p",
        component_hashes={
            "execution_contract": "wrong",
            "task_set": "t",
            "utility_family": "u",
            "model_runtime": "m",
            "randomization": "r",
            "analysis_plan": "a",
            "common_baseline": "b",
            "treatments": "c",
            "sham_matches": "s",
        },
        readiness_hash="r",
        locked_before_provider_call=True,
        provider_calls_at_lock=0,
        live_execution_authorized=False,
    )
    resolved = {name: value for name, value in components.items() if name != "sham_match"}
    resolved["sham_matches"] = components["sham_match"]
    assert verify_execution_lock(lock, resolved)["valid"] is False


def test_randomization_requires_exact_three_arms_per_task():
    task_hash = task()["object_hash"]
    incomplete = randomization_plan(
        task_hashes=[task_hash],
        arms=["A", "B", "C"],
        algorithm="sha256",
        seed_commitment="s",
        assignment_order=[{"task_hash": task_hash, "arm": "A"}],
        execution_contract_hash="e",
    )
    assert validate_randomization_plan(incomplete, [task_hash]) is False
    complete = randomization_plan(
        task_hashes=[task_hash],
        arms=["A", "B", "C"],
        algorithm="sha256",
        seed_commitment="s",
        assignment_order=[{"task_hash": task_hash, "arm": arm} for arm in ("A", "B", "C")],
        execution_contract_hash="e",
    )
    assert validate_randomization_plan(complete, [task_hash]) is True


def test_randomization_rejects_duplicate_task_arm_pair():
    task_hash = task()["object_hash"]
    plan = randomization_plan(
        task_hashes=[task_hash],
        arms=["A", "B", "C"],
        algorithm="sha256",
        seed_commitment="s",
        assignment_order=[{"task_hash": task_hash, "arm": arm} for arm in ("A", "B", "A")],
        execution_contract_hash="e",
    )
    assert validate_randomization_plan(plan, [task_hash]) is False


def test_assignment_is_typed_and_content_addressed():
    obj = assignment(randomization_plan_hash="r", task_hash="t", arm="C")
    assert obj["schema_version"] == ASSIGNMENT_SCHEMA
    assert obj["provider_calls_at_assignment"] == 0


def test_assignment_treatment_arm_mismatch_is_not_accepted(proof_host):
    experiment = freeze(proof_host, holdout_id="ii5-arm-mismatch")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    obj = assignment(randomization_plan_hash="r", task_hash="t", arm="B")
    assert obj["arm"] != treatment["object"]["analysis_arm"]


def test_assignment_treatment_arm_mismatch_is_rejected_during_run(proof_host):
    experiment = freeze(proof_host, holdout_id="ii5-assignment-order")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = proof_host.freeze_execution_contract(
        experiment["receipt_hash"],
        model_runtime=runtime(),
        task_set_hash="t" * 64,
        analysis_plan_hash=readiness_components()["analysis_plan"]["object_hash"],
        budgets={"candidate_budget": 1, "provider_call_budget": 1, "token_budget": 1000,
                 "wall_clock_budget_seconds": 60},
        sham_tolerances={"count": 0, "bytes": 100, "token_estimate": 25,
                         "positive": 0, "constraints": 0},
    )
    bundle = build_empirical_bundle(proof_host, experiment, treatment, execution)
    assignment_obj = proof_host._resolve(bundle[3], "gsi_assignment")["object"]
    forged = assignment(
        randomization_plan_hash=assignment_obj["randomization_plan_hash"],
        task_hash=assignment_obj["task_hash"], arm="C",
    )
    forged_receipt = proof_host.record_empirical_component("gsi_assignment", forged)
    with pytest.raises(ValueError, match="assignment/treatment arm mismatch"):
        proof_host.run_empirical(bundle[0], bundle[1], bundle[2], forged_receipt["receipt_hash"], payload)


@pytest.mark.parametrize("arm", ["B", "C"])
def test_confirmatory_history_arms_require_nonempty_history(proof_host, arm):
    experiment = freeze(proof_host, holdout_id=f"ii5-empty-{arm}")
    with pytest.raises(ValueError, match="nonempty history"):
        proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm=arm)


def test_b_requires_sham_match_receipt(proof_host):
    experiment = freeze(proof_host, holdout_id="ii5-sham-required")
    with pytest.raises(ValueError, match="nonempty history"):
        proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="B")


def test_sham_match_requires_type_and_schema_shape():
    c = [
        {
            "object_hash": "c",
            "evidence_type": "X",
            "schema_version": "x",
            "channel": "H+",
            "applicability_disposition": "APPLICABLE",
        }
    ]
    b = [
        {
            "object_hash": "b",
            "evidence_type": "Y",
            "schema_version": "y",
            "channel": "H+",
            "applicability_disposition": "INAPPLICABLE",
        }
    ]
    match = sham_match(
        c, b, {"count": 0, "bytes": 1000, "token_estimate": 1000, "positive": 0, "constraints": 0}
    )
    assert match["schema_version"] == SHAM_MATCH_SCHEMA
    assert match["type_shape_equal"] is False
    assert match["disposition"] == "HELD"


def test_task_set_is_schema_specific():
    obj = task_set([task()])
    assert obj["schema_version"] == TASK_SET_SCHEMA
    assert obj["task_count"] == 1


def test_episode_rejects_task_assignment_mismatch(proof_host):
    experiment = freeze(proof_host, holdout_id="ii5-task-mismatch")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = proof_host.freeze_execution_contract(
        experiment["receipt_hash"],
        model_runtime=runtime(),
        task_set_hash="t" * 64,
        analysis_plan_hash=readiness_components()["analysis_plan"]["object_hash"],
        budgets={
            "candidate_budget": 1,
            "provider_call_budget": 1,
            "token_budget": 1000,
            "wall_clock_budget_seconds": 60,
        },
        sham_tolerances={
            "count": 0,
            "bytes": 100,
            "token_estimate": 25,
            "positive": 0,
            "constraints": 0,
        },
    )
    bundle = build_empirical_bundle(proof_host, experiment, treatment, execution)
    trial = proof_host.run_empirical(*bundle, payload)
    with pytest.raises(ValueError, match="assignment episode binding"):
        proof_host.record_empirical_search_episode(
            experiment_receipt=bundle[0],
            treatment_receipt=bundle[1],
            execution_contract_receipt=execution["receipt_hash"],
            assignment_receipt=bundle[3],
            candidate_context_receipt=trial["object"]["candidate_context_receipt"],
            trial_receipt=trial["receipt_hash"],
            task_hash="wrong",
            randomization_assignment={},
            candidate_receipts=[],
            rejected_candidates=[],
            candidate_evaluations=1,
            provider_calls=0,
            transport_retries=0,
            candidate_attempts=1,
            token_cost=0,
            duration_ms=1,
        )


@pytest.mark.parametrize(
    "field", ["candidate_evaluations", "provider_calls", "token_cost", "duration_ms"]
)
def test_episode_budget_violation_is_held(proof_host, field):
    experiment = freeze(proof_host, holdout_id=f"ii5-budget-{field}")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = proof_host.freeze_execution_contract(
        experiment["receipt_hash"],
        model_runtime=runtime(),
        task_set_hash="t" * 64,
        analysis_plan_hash=readiness_components()["analysis_plan"]["object_hash"],
        budgets={
            "candidate_budget": 1,
            "provider_call_budget": 1,
            "token_budget": 10,
            "wall_clock_budget_seconds": 1,
        },
        sham_tolerances={
            "count": 0,
            "bytes": 100,
            "token_estimate": 25,
            "positive": 0,
            "constraints": 0,
        },
    )
    bundle = build_empirical_bundle(proof_host, experiment, treatment, execution)
    trial = proof_host.run_empirical(*bundle, payload)
    values = {
        "candidate_evaluations": 2,
        "provider_calls": 2,
        "token_cost": 11,
        "duration_ms": 1001,
    }
    episode = proof_host.record_empirical_search_episode(
        experiment_receipt=bundle[0],
        treatment_receipt=bundle[1],
        execution_contract_receipt=execution["receipt_hash"],
        assignment_receipt=bundle[3],
        candidate_context_receipt=trial["object"]["candidate_context_receipt"],
        trial_receipt=trial["receipt_hash"],
        task_hash=proof_host._resolve(bundle[3], "gsi_assignment")["object"]["task_hash"],
        randomization_assignment={},
        candidate_receipts=[],
        rejected_candidates=[],
        candidate_evaluations=values.get("candidate_evaluations", 1),
        provider_calls=values.get("provider_calls", 0),
        transport_retries=0,
        candidate_attempts=1,
        token_cost=values.get("token_cost", 0),
        duration_ms=values.get("duration_ms", 1),
    )
    assert episode["object"]["terminal_state"] == "HELD"


def test_hidden_fixture_digest_changes_holdout_identity():
    base = contract("holdout")
    first = copy.deepcopy(base)
    second = copy.deepcopy(base)
    first["fixture_digests"] = {"hidden.bin": b"one"}
    second["fixture_digests"] = {"hidden.bin": b"two"}
    from cortex.causal_treatment import semantic_holdout_identity

    assert (
        semantic_holdout_identity(first)["raw_semantic_hash"]
        != semantic_holdout_identity(second)["raw_semantic_hash"]
    )


def test_legacy_deterministic_run_remains_available(proof_host):
    experiment = freeze(proof_host, holdout_id="ii5-legacy")
    result = proof_host.run(experiment["receipt_hash"], payload)
    assert result["object"]["candidate_context_receipt"] is None


def test_episode_records_zero_provider_calls(proof_host):
    experiment = freeze(proof_host, holdout_id="ii5-zero-provider")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = proof_host.freeze_execution_contract(
        experiment["receipt_hash"],
        model_runtime=runtime(),
        task_set_hash="t" * 64,
        analysis_plan_hash=readiness_components()["analysis_plan"]["object_hash"],
        budgets={
            "candidate_budget": 1,
            "provider_call_budget": 1,
            "token_budget": 1000,
            "wall_clock_budget_seconds": 60,
        },
        sham_tolerances={
            "count": 0,
            "bytes": 100,
            "token_estimate": 25,
            "positive": 0,
            "constraints": 0,
        },
    )
    bundle = build_empirical_bundle(proof_host, experiment, treatment, execution)
    trial = proof_host.run_empirical(*bundle, payload)
    assignment_obj = proof_host._resolve(bundle[3], "gsi_assignment")["object"]
    episode = proof_host.record_empirical_search_episode(
        experiment_receipt=bundle[0],
        treatment_receipt=bundle[1],
        execution_contract_receipt=execution["receipt_hash"],
        assignment_receipt=bundle[3],
        candidate_context_receipt=trial["object"]["candidate_context_receipt"],
        trial_receipt=trial["receipt_hash"],
        task_hash=assignment_obj["task_hash"],
        randomization_assignment={},
        candidate_receipts=[],
        rejected_candidates=[],
        candidate_evaluations=1,
        provider_calls=0,
        transport_retries=0,
        candidate_attempts=1,
        token_cost=0,
        duration_ms=1,
    )
    assert episode["object"]["provider_calls"] == 0
