"""GSI-II.4 causal-treatment controls; no provider calls."""
# ruff: noqa: F401,F811 -- proof_host is an imported pytest fixture.

import copy

import pytest

from cortex.causal_treatment import (
    ANALYSIS_PLAN_SCHEMA,
    CANDIDATE_CONTEXT_SCHEMA,
    TASK_SET_SCHEMA,
    TREATMENT_SCHEMA_V11,
    EXECUTION_CONTRACT_SCHEMA,
    EXECUTION_LOCK_SCHEMA,
    HOLDOUT_SEMANTIC_SCHEMA,
    MODEL_RUNTIME_SCHEMA,
    RANDOMIZATION_SCHEMA,
    READINESS_SCHEMA,
    TASK_SCHEMA,
    analysis_plan,
    arm_isolation,
    assignment,
    candidate_context,
    common_baseline,
    contamination_report,
    context_difference,
    execution_contract,
    execution_lock,
    execution_readiness,
    model_runtime_identity,
    randomization_plan,
    sealed,
    semantic_holdout_identity,
    sham_match,
    task_set,
    task_identity,
    valid,
)
from cortex.self_improvement import _sealed
from test_gsi_ii import contract, freeze, payload
from test_gsi_ii3 import proof_host


def runtime():
    return model_runtime_identity(
        provider="future-provider",
        model="exact-model",
        sampling={"temperature": 0},
        reasoning_effort="fixed",
        max_output_tokens=1000,
        tool_mode="none",
        api_mode="responses",
        system_prompt_hash="s" * 64,
        prompt_template_hash="p" * 64,
        response_schema="cortex-structured-edit-intent/2.0",
        retry_policy={"transport_retries": 2, "candidate_attempts": 1, "backoff": "fixed"},
    )


def plan():
    return analysis_plan(
        primary_endpoint="eta",
        secondary_endpoints=["eta_call"],
        estimator="paired_difference",
        exclusion_criteria=["contamination"],
        missing_data_rule="held",
        multiplicity_rule="none",
        minimum_sample_target=12,
    )


def task():
    return task_identity(
        task_family="ranking",
        source_baseline="h" * 40,
        mutation_scope=["app/value.txt"],
        objective="improve fixture",
        diagnosis_contract="d" * 64,
        evaluation_family="u" * 64,
        inclusion_criteria=["fresh"],
        source="authored",
        exposed_to_tuning=False,
    )


def exec_contract():
    return execution_contract(
        source_revision="h" * 40,
        task_set_hash="t" * 64,
        utility_family_hash="u" * 64,
        model_runtime_hash=runtime()["object_hash"],
        candidate_budget=1,
        provider_call_budget=1,
        token_budget=2000,
        wall_clock_budget_seconds=60,
        tool_surface=[],
        capabilities={"candidate": [], "holdout": ["opaque_score"]},
        mutation_scope=["app/value.txt"],
        authority_state_hash="a" * 64,
        evaluator_identities={"dev": "d", "holdout": "q"},
        stopping_rule="one_attempt",
        failure_attribution_policy="typed/1",
        treatment_definitions={"A": [], "B": [], "C": []},
        sham_tolerances={
            "count": 0,
            "bytes": 100,
            "token_estimate": 25,
            "positive": 0,
            "constraints": 0,
        },
        randomization_scheme="sha256-blocked",
        analysis_plan_hash=plan()["object_hash"],
        claim_ceiling="DETERMINISTIC_CONTROLS_ONLY",
    )


def readiness_components():
    task_obj = task_identity(
        task_family="ranking",
        source_baseline="h" * 40,
        mutation_scope=["app/value.txt"],
        objective="improve fixture",
        diagnosis_contract="d" * 64,
        evaluation_family="u" * 64,
        inclusion_criteria=["fresh"],
        source="authored",
        exposed_to_tuning=False,
    )
    taskset = task_set([task_obj])
    randomization = randomization_plan(
        task_hashes=[task_obj["object_hash"]],
        arms=["A", "B", "C"],
        algorithm="sha256",
        seed_commitment="z" * 64,
        assignment_order=[
            {"task_hash": task_obj["object_hash"], "arm": arm} for arm in ("A", "B", "C")
        ],
        execution_contract_hash=exec_contract()["object_hash"],
    )
    treatment = sealed(
        TREATMENT_SCHEMA_V11,
        arm="A",
        analysis_arm="A",
        history_objects=[],
        positive_history=[],
        failure_history=[],
        history_frozen=True,
    )
    return {
        "execution_contract": exec_contract(),
        "task_set": taskset,
        "model_runtime": runtime(),
        "randomization": randomization,
        "analysis_plan": plan(),
        "common_baseline": common_baseline(
            source_revision="h",
            task_hash="t",
            utility_family_hash="u",
            evaluator_identity={},
            authority_state_hash="a",
            model_runtime_hash=runtime()["object_hash"],
            neutral_context_hash="n",
        ),
        "treatments": treatment,
        "sham_match": sham_match([], [], {"count": 0}),
    }


def build_empirical_bundle(host, experiment, treatment, execution):
    task_obj = task_identity(
        task_family="ranking",
        source_baseline=experiment["object"]["baseline_head"],
        mutation_scope=["app/value.txt"],
        objective="improve fixture",
        diagnosis_contract="d" * 64,
        evaluation_family="u" * 64,
        inclusion_criteria=["fresh"],
        source="authored",
        exposed_to_tuning=False,
    )
    taskset = host.record_empirical_component("gsi_task_set", task_set([task_obj]))
    randomization_obj = randomization_plan(
        task_hashes=[task_obj["object_hash"]],
        arms=["A", "B", "C"],
        algorithm="sha256",
        seed_commitment="z" * 64,
        assignment_order=[
            {"task_hash": task_obj["object_hash"], "arm": arm} for arm in ("A", "B", "C")
        ],
        execution_contract_hash=execution["object"]["object_hash"],
    )
    randomization = host.record_empirical_component("gsi_randomization", randomization_obj)
    model_runtime = host.record_empirical_component("gsi_model_runtime", runtime())
    analysis = host.record_empirical_component("gsi_analysis_plan", plan())
    baseline = host.record_empirical_component(
        "gsi_common_baseline",
        common_baseline(
            source_revision=experiment["object"]["baseline_head"],
            task_hash=task_obj["object_hash"],
            utility_family_hash=experiment["object"]["utility_family_hash"],
            evaluator_identity={},
            authority_state_hash=experiment["object"]["authority_state_hash"],
            model_runtime_hash=model_runtime["object"]["object_hash"],
            neutral_context_hash="n",
        ),
    )
    sham = host.record_empirical_component("gsi_sham_match", sham_match([], [], {"count": 0}))
    components = {
        "execution_contract": (execution["receipt_hash"], "gsi_execution_contract"),
        "task_set": (taskset["receipt_hash"], "gsi_task_set"),
        "model_runtime": (model_runtime["receipt_hash"], "gsi_model_runtime"),
        "randomization": (randomization["receipt_hash"], "gsi_randomization"),
        "analysis_plan": (analysis["receipt_hash"], "gsi_analysis_plan"),
        "common_baseline": (baseline["receipt_hash"], "gsi_common_baseline"),
        "treatments": (treatment["receipt_hash"], "gsi_empirical_treatment"),
        "sham_match": (sham["receipt_hash"], "gsi_sham_match"),
    }
    readiness = host.verify_gsi_iii_readiness(
        component_receipts=components,
        implementation_ci="PASS",
        protocol_status="PROTOCOL_FROZEN",
        provider_calls=0,
        live_authorized=False,
    )
    lock = host.freeze_execution_lock(
        protocol_hash="p" * 64,
        component_receipts=components,
        readiness_receipt=readiness["receipt_hash"],
    )
    assignment_obj = assignment(
        randomization_plan_hash=randomization["object"]["object_hash"],
        task_hash=task_obj["object_hash"],
        arm=treatment["object"]["analysis_arm"],
    )
    assignment_receipt = host.record_empirical_component("gsi_assignment", assignment_obj)
    return (
        experiment["receipt_hash"],
        treatment["receipt_hash"],
        lock["receipt_hash"],
        assignment_receipt["receipt_hash"],
    )


def test_contract_schemas_and_closed_authority():
    objects = [
        (runtime(), MODEL_RUNTIME_SCHEMA),
        (plan(), ANALYSIS_PLAN_SCHEMA),
        (task(), TASK_SCHEMA),
        (exec_contract(), EXECUTION_CONTRACT_SCHEMA),
    ]
    for obj, schema in objects:
        assert obj["schema_version"] == schema and valid(obj, schema)
        assert obj["authority_effect"] is False and obj["execution_authorized"] is False


@pytest.mark.parametrize(
    "field",
    [
        "authority_effect",
        "production_effect",
        "execution_authorized",
        "host_mutate_authorized",
        "memory_admission_authorized",
        "policy_effect",
        "promotion_authorized",
        "active_guidance",
    ],
)
def test_epistemic_objects_fail_integrity_if_authority_opens(field):
    obj = runtime()
    obj[field] = True
    assert valid(obj) is False


def test_runtime_requires_exact_identity_and_separates_retries():
    with pytest.raises(ValueError):
        model_runtime_identity(
            provider="",
            model="m",
            sampling={},
            reasoning_effort=None,
            max_output_tokens=1,
            tool_mode="none",
            api_mode="x",
            system_prompt_hash="s",
            prompt_template_hash="p",
            response_schema="r",
            retry_policy={},
        )
    assert runtime()["retry_policy"]["transport_retries"] == 2
    assert runtime()["retry_policy"]["candidate_attempts"] == 1


def test_analysis_plan_freezes_sample_and_separates_pilot():
    assert plan()["minimum_sample_target"] == 12
    assert plan()["confirmatory_data_excludes_pilot"] is True
    with pytest.raises(ValueError):
        analysis_plan(
            primary_endpoint="eta",
            secondary_endpoints=[],
            estimator="x",
            exclusion_criteria=[],
            missing_data_rule="x",
            multiplicity_rule="x",
            minimum_sample_target=0,
        )


def test_semantic_holdout_ignores_cosmetic_step_metadata():
    first = contract("holdout")
    second = copy.deepcopy(first)
    second["steps"][0]["id"] = "renamed"
    second["steps"][0]["title"] = "display"
    assert (
        semantic_holdout_identity(first)["raw_semantic_hash"]
        == semantic_holdout_identity(second)["raw_semantic_hash"]
    )
    assert semantic_holdout_identity(first)["schema_version"] == HOLDOUT_SEMANTIC_SCHEMA


def test_semantic_holdout_changes_for_executable_change():
    first = contract("holdout")
    second = copy.deepcopy(first)
    second["steps"][0]["argv"] = ["{python}", "-c", "raise SystemExit(1)"]
    assert (
        semantic_holdout_identity(first)["raw_semantic_hash"]
        != semantic_holdout_identity(second)["raw_semantic_hash"]
    )


def test_randomization_object_is_valid_and_rejects_partial_arm_set():
    ec = exec_contract()
    rp = randomization_plan(
        task_hashes=[task()["object_hash"]],
        arms=["A", "B", "C"],
        algorithm="sha256",
        seed_commitment="z" * 64,
        assignment_order=[{"task_hash": task()["object_hash"], "arm": "A"}],
        execution_contract_hash=ec["object_hash"],
    )
    assert rp["schema_version"] == RANDOMIZATION_SCHEMA
    assert rp["provider_calls_at_freeze"] == 0


def test_randomization_rejects_incomplete_arms_and_unknown_task():
    with pytest.raises(ValueError):
        randomization_plan(
            task_hashes=["t"],
            arms=["A", "B"],
            algorithm="x",
            seed_commitment="s",
            assignment_order=[],
            execution_contract_hash="e",
        )
    with pytest.raises(ValueError):
        randomization_plan(
            task_hashes=["t"],
            arms=["A", "B", "C"],
            algorithm="x",
            seed_commitment="s",
            assignment_order=[{"task_hash": "x", "arm": "A"}],
            execution_contract_hash="e",
        )


def test_candidate_context_binds_exact_input_without_holdout():
    ctx = {
        "source": {"a": "x"},
        "applicable_constraints": [],
        "verified_improvement_evidence": [],
        "development_metrics": {"task_success": 0},
    }
    obj = candidate_context(
        experiment_receipt="e",
        treatment_receipt="t",
        execution_contract_receipt="x",
        source_revision="h",
        utility_family_hash="u",
        context=ctx,
        capability_manifest={},
    )
    assert obj["schema_version"] == CANDIDATE_CONTEXT_SCHEMA
    assert obj["holdout_content_included"] is False
    assert obj["serialized_byte_length"] > 0 and obj["token_estimate"] > 0
    changed = copy.deepcopy(ctx)
    changed["source"]["a"] = "y"
    assert (
        candidate_context(
            experiment_receipt="e",
            treatment_receipt="t",
            execution_contract_receipt="x",
            source_revision="h",
            utility_family_hash="u",
            context=changed,
            capability_manifest={},
        )["context_hash"]
        != obj["context_hash"]
    )


def test_context_difference_allows_only_history_fields():
    left = sealed(
        CANDIDATE_CONTEXT_SCHEMA,
        canonical_context={"source": "same", "applicable_constraints": []},
        context_hash="a",
    )
    right = sealed(
        CANDIDATE_CONTEXT_SCHEMA,
        canonical_context={"source": "same", "applicable_constraints": [1]},
        context_hash="b",
    )
    assert context_difference(left, right)["disposition"] == "PASS"
    changed = sealed(
        CANDIDATE_CONTEXT_SCHEMA,
        canonical_context={"source": "different", "applicable_constraints": []},
        context_hash="c",
    )
    assert context_difference(left, changed)["disposition"] == "HELD"


def test_candidate_context_binds_exact_bytes_and_excludes_holdout():
    context = {
        "source": {"app/value.txt": "bad\n"},
        "applicable_constraints": [],
        "verified_improvement_evidence": [],
    }
    obj = candidate_context(
        experiment_receipt="e",
        treatment_receipt="t",
        execution_contract_receipt="x",
        source_revision="h",
        utility_family_hash="u",
        context=context,
        capability_manifest={"candidate": ["declared_source"]},
    )
    assert valid(obj, CANDIDATE_CONTEXT_SCHEMA)
    assert obj["serialized_byte_length"] > 0 and obj["token_estimate"] > 0
    assert obj["holdout_content_included"] is False
    mutated = copy.deepcopy(obj)
    mutated["canonical_context"]["source"] = {}
    assert valid(mutated) is False


def test_randomization_is_content_addressed_and_pre_call():
    obj = randomization_plan(
        task_hashes=["t"],
        arms=["A", "B", "C"],
        algorithm="sha256",
        seed_commitment="s" * 64,
        assignment_order=[{"task_hash": "t", "arm": "A"}],
        execution_contract_hash="e" * 64,
    )
    assert valid(obj, RANDOMIZATION_SCHEMA)
    assert obj["provider_calls_at_freeze"] == 0
    with pytest.raises(ValueError):
        randomization_plan(
            task_hashes=["t"],
            arms=["A", "B"],
            algorithm="sha256",
            seed_commitment="s",
            assignment_order=[],
            execution_contract_hash="e",
        )


def test_sham_match_requires_applicability_and_structure():
    applicable = [
        {
            "object_hash": "a",
            "evidence_type": "X",
            "schema_version": "x",
            "channel": "H+",
            "applicability_disposition": "APPLICABLE",
        }
    ]
    sham = [
        {
            "object_hash": "b",
            "evidence_type": "X",
            "schema_version": "x",
            "channel": "H+",
            "applicability_disposition": "INAPPLICABLE",
        }
    ]
    assert (
        sham_match(
            applicable,
            sham,
            {"count": 0, "bytes": 100, "token_estimate": 25, "positive": 0, "constraints": 0},
        )["disposition"]
        == "PASS"
    )
    sham[0]["applicability_disposition"] = "APPLICABLE"
    assert (
        sham_match(
            applicable,
            sham,
            {"count": 0, "bytes": 100, "token_estimate": 25, "positive": 0, "constraints": 0},
        )["disposition"]
        == "HELD"
    )


@pytest.mark.parametrize(
    "name",
    [
        "HOLDOUT_LEAK",
        "CROSS_ARM_HISTORY_LEAK",
        "POST_RANDOMIZATION_HISTORY_MUTATION",
        "TOOL_SURFACE_MISMATCH",
        "MODEL_CONFIG_MISMATCH",
        "BUDGET_MISMATCH",
        "SOURCE_MISMATCH",
        "EVALUATOR_MUTATION",
        "TREATMENT_CONTEXT_MISMATCH",
    ],
)
def test_contamination_classes_hold_episode(name):
    assert contamination_report({name: False})["disposition"] == "FAIL"


def test_unknown_contamination_is_held_not_passed():
    report = contamination_report({"UNKNOWN_CONTAMINATION": None})
    assert report["disposition"] == "HELD"


def test_readiness_separates_technical_state_from_live_authority():
    components = readiness_components()
    ready = execution_readiness(
        components=components,
        implementation_ci="PASS",
        protocol_status="PROTOCOL_FROZEN",
        provider_calls=0,
        live_authorized=False,
    )
    assert ready["schema_version"] == READINESS_SCHEMA
    assert ready["empirical_readiness"] == "READY"
    assert ready["live_execution_authorized"] is False


@pytest.mark.parametrize(
    "ci,protocol,calls,expected",
    [
        ("PENDING", "PROTOCOL_FROZEN", 0, "HELD"),
        ("PASS", "EXECUTION_DRAFT", 0, "FAIL"),
        ("FAIL", "PROTOCOL_FROZEN", 0, "FAIL"),
        ("PASS", "PROTOCOL_FROZEN", 1, "FAIL"),
    ],
)
def test_readiness_fails_closed(ci, protocol, calls, expected):
    components = readiness_components()
    result = execution_readiness(
        components=components,
        implementation_ci=ci,
        protocol_status=protocol,
        provider_calls=calls,
        live_authorized=False,
    )
    assert result["empirical_readiness"] == expected


def test_execution_lock_never_authorizes_live_execution():
    ready = execution_readiness(
        components=readiness_components(),
        implementation_ci="PASS",
        protocol_status="PROTOCOL_FROZEN",
        provider_calls=0,
        live_authorized=False,
    )
    # Use the real required component name after constructing the fixture.
    components = {
        "execution_contract": "e",
        "task_set": "t",
        "utility_family": "u",
        "model_runtime": "m",
        "randomization": "r",
        "analysis_plan": "a",
        "common_baseline": "b",
        "treatments": "c",
        "sham_matches": "s",
    }
    obj = execution_lock(protocol_hash="p", component_hashes=components, readiness=ready)
    assert valid(obj, EXECUTION_LOCK_SCHEMA)
    assert obj["locked_before_provider_call"] is True
    assert obj["live_execution_authorized"] is False


def test_execution_lock_rejects_incomplete_treatments():
    with pytest.raises(ValueError):
        execution_lock(protocol_hash="", component_hashes={}, readiness={})


def test_empirical_no_history_arm_is_canonical_and_empty(proof_host):
    experiment = freeze(proof_host, holdout_id="ii4-a")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    assert treatment["object"]["history_objects"] == []
    assert treatment["object"]["positive_history"] == []
    assert treatment["object"]["failure_history"] == []


def test_empirical_treatment_rejects_caller_objects(proof_host):
    experiment = freeze(proof_host, holdout_id="ii4-caller")
    with pytest.raises((TypeError, ValueError)):
        proof_host.freeze_empirical_treatment(
            experiment["receipt_hash"], arm="C", history_receipts=[{"applicability_valid": True}]
        )


def test_empirical_run_binds_treatment_context_and_candidate(proof_host):
    experiment = freeze(proof_host, holdout_id="ii4-run")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = proof_host.freeze_execution_contract(
        experiment["receipt_hash"],
        model_runtime=runtime(),
        task_set_hash="t" * 64,
        analysis_plan_hash=plan()["object_hash"],
        budgets={
            "candidate_budget": 1,
            "provider_call_budget": 1,
            "token_budget": 2000,
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
    assert trial["object"]["treatment_receipt"] == treatment["receipt_hash"]
    context_receipt = trial["object"]["candidate_context_receipt"]
    context = proof_host._resolve(context_receipt, "gsi_candidate_context")["object"]
    assert context["treatment_receipt"] == treatment["receipt_hash"]
    assert context["canonical_context"]["applicable_constraints"] == []
    candidate = proof_host.store.symbiotic_receipts_by_kind(
        proof_host.repo, "gsi_generated_candidate"
    )[-1]["object"]
    assert candidate["candidate_context_hash"] == context["context_hash"]


def test_legacy_run_remains_unbound_and_reconstructable(proof_host):
    experiment = freeze(proof_host, holdout_id="ii4-legacy")
    trial = proof_host.run(experiment["receipt_hash"], payload)
    assert trial["object"]["candidate_context_receipt"] is None
    assert trial["object"]["schema_version"] == "cortex-source-improvement-result/2.0"


def test_search_episode_does_not_trust_fake_generation_hash(proof_host):
    experiment = freeze(proof_host, holdout_id="ii4-episode")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    execution = proof_host.freeze_execution_contract(
        experiment["receipt_hash"],
        model_runtime=runtime(),
        task_set_hash="t" * 64,
        analysis_plan_hash=plan()["object_hash"],
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
    episode = proof_host.record_empirical_search_episode(
        experiment_receipt=experiment["receipt_hash"],
        treatment_receipt=treatment["receipt_hash"],
        execution_contract_receipt=execution["receipt_hash"],
        assignment_receipt=bundle[3],
        candidate_context_receipt=trial["object"]["candidate_context_receipt"],
        trial_receipt=trial["receipt_hash"],
        task_hash=proof_host._resolve(bundle[3], "gsi_assignment")["object"]["task_hash"],
        randomization_assignment={},
        candidate_receipts=[],
        rejected_candidates=[],
        candidate_evaluations=1,
        provider_calls=0,
        transport_retries=0,
        candidate_attempts=1,
        token_cost=0,
        duration_ms=1,
        realized_generation_receipt="f" * 64,
    )
    assert episode["object"]["realized_verified_improvements"] == 0
    assert episode["object"]["eta"] == 0


def test_source_improvement_v1_and_claim_boundaries_remain():
    from cortex.source_improvement import CONTRACT_SCHEMA, RESULT_SCHEMA

    assert CONTRACT_SCHEMA.endswith("/1.0") and RESULT_SCHEMA.endswith("/1.0")
    assert exec_contract()["claim_ceiling"] == "DETERMINISTIC_CONTROLS_ONLY"
    assert exec_contract()["live_execution_authorized"] is False


def test_raw_holdout_cannot_become_fresh_by_changing_utility_family(proof_host):
    freeze(proof_host, holdout_id="raw-first")
    opportunity = proof_host.diagnose(
        subject="fixture ranking", contract=contract(), metric="task_success", threshold=1
    )
    with pytest.raises(ValueError, match="holdout content already reserved"):
        proof_host.freeze(
            opportunity["receipt_hash"],
            development=contract(),
            holdout=contract("holdout"),
            holdout_id="raw-second",
            epsilon_dev=2,
            epsilon_holdout=2,
        )


def test_treatment_history_is_stable_after_store_changes(proof_host):
    experiment = freeze(proof_host, holdout_id="stable-history")
    treatment = proof_host.freeze_empirical_treatment(experiment["receipt_hash"], arm="A")
    frozen_hash = treatment["object"]["object_hash"]
    proof_host._record(
        "gsi_verified_improvement",
        _sealed(
            "cortex-verified-improvement/1.0",
            status="VERIFIED_WITHIN_CONTROL",
            applicability={},
            scope=["app/value.txt"],
            counterevidence=[],
            active_defeaters=[],
            superseded_by=[],
            influence_class="EXPERIMENT_EVIDENCE",
        ),
    )
    resolved = proof_host._resolve(treatment["receipt_hash"], "gsi_empirical_treatment")["object"]
    assert resolved["object_hash"] == frozen_hash
    assert resolved["history_objects"] == []


def test_common_baseline_and_arm_isolation_are_explicit():
    baseline = common_baseline(
        source_revision="h",
        task_hash="t",
        utility_family_hash="u",
        evaluator_identity={"e": "v"},
        authority_state_hash="a",
        model_runtime_hash="m",
        neutral_context_hash="n",
    )
    isolated = arm_isolation(
        namespaces={"A": "na", "B": "nb", "C": "nc"},
        worktrees={"A": "wa", "B": "wb", "C": "wc"},
        common_baseline_hash=baseline["object_hash"],
    )
    assert isolated["mutable_state_intersection"] == []
    assert isolated["arm_outputs_shared"] is False
    with pytest.raises(ValueError):
        arm_isolation(
            namespaces={"A": "n", "B": "n", "C": "n"},
            worktrees={"A": "wa", "B": "wb", "C": "wc"},
            common_baseline_hash=baseline["object_hash"],
        )


def test_canonical_applicable_and_automatic_sham_history(proof_host):
    first = freeze(proof_host, holdout_id="history-source")
    proof_host.recycle(proof_host.run(first["receipt_hash"], payload)["receipt_hash"])
    second = freeze(proof_host, contract("holdout-alt"), holdout_id="history-target")
    exp = second["object"]
    applicable = proof_host._record(
        "gsi_verified_improvement",
        _sealed(
            "cortex-verified-improvement/1.0",
            status="VERIFIED_WITHIN_CONTROL",
            applicability={
                "environment": exp["environment"],
                "relevant_dependency_closure": exp["dependency_identity"],
                "representation_identity": exp["representation_identity"],
                "utility_family_hash": exp["utility_family_hash"],
                "instrument_identity": exp["instrument_identity"],
            },
            scope=exp["allowed_targets"],
            counterevidence=[],
            active_defeaters=[],
            superseded_by=[],
            measured_effect=1,
            influence_class="EXPERIMENT_EVIDENCE",
        ),
    )
    proof_host._record(
        "gsi_verified_improvement",
        _sealed(
            "cortex-verified-improvement/1.0",
            status="VERIFIED_WITHIN_CONTROL",
            applicability={
                "environment": exp["environment"],
                "relevant_dependency_closure": {"different": True},
                "representation_identity": exp["representation_identity"],
                "utility_family_hash": exp["utility_family_hash"],
            },
            scope=exp["allowed_targets"],
            counterevidence=[],
            active_defeaters=[],
            superseded_by=[],
            measured_effect=1,
            influence_class="EXPERIMENT_EVIDENCE",
        ),
    )
    pool = proof_host.build_history_pool(second["receipt_hash"])["object"]["items"]
    applicable_receipt = next(
        item["canonical_receipt_hash"]
        for item in pool
        if item["object_hash"] == applicable["object"]["object_hash"]
        and item["applicability_disposition"] == "APPLICABLE"
    )
    treatment_c = proof_host.freeze_empirical_treatment(
        second["receipt_hash"], arm="C", history_receipts=[applicable_receipt]
    )
    assert len(treatment_c["object"]["positive_history"]) == 1
    treatment_b, match = proof_host.build_sham_history(
        second["receipt_hash"],
        [applicable_receipt],
        tolerances={
            "count": 0,
            "bytes": 10000,
            "token_estimate": 2500,
            "positive": 0,
            "constraints": 0,
        },
    )
    assert match["object"]["disposition"] == "PASS"
    assert (
        treatment_b["object"]["history_objects"][0]["applicability_disposition"] == "INAPPLICABLE"
    )
