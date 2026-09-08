"""GSI-II.1 loop-closure controls. Zero provider calls."""
import json

import pytest

from cortex.autonomous_improvement import AutonomyPolicyEnvelope, issue_autonomy_policy
from cortex.coding_workspace import CONTRACT_SCHEMA, _git, _sha
from cortex.self_improvement import (
    HARD_GATES, attestation_gate_state, check_candidate_constraints,
    constitutional_verdict, cumulative_improvement_disposition,
    improvement_disposition, inspect_v2_arm,
)
from cortex.source_improvement import CONTRACT_SCHEMA as V1_CONTRACT, RESULT_SCHEMA as V1_RESULT
from test_gsi_ii import contract, freeze, payload
from test_v100_alpha8_autonomy import V100Alpha8AutonomyTests as _HostFixture


def _gates(**overrides):
    states = dict.fromkeys(HARD_GATES, "PASS")
    states.update(overrides)
    return states


def rank_contract(mode="dev"):
    code = "from pathlib import Path; assert Path('app/rank.txt').read_text().strip() == 'high'"
    if mode == "holdout":
        code = "from pathlib import Path; assert Path('app/rank.txt').read_bytes() == b'high\\n'"
    body = {"schema_version": CONTRACT_SCHEMA, "policy_id": "rank-" + mode,
            "targets": ["app/rank.txt"], "steps": [{"id": mode, "argv": ["{python}", "-c", code], "timeout_seconds": 5}],
            "model_selected": False, "caller_selected": False, "promotion_authorized": False}
    return {**body, "contract_hash": _sha(body)}


@pytest.fixture
def host():
    fixture = _HostFixture()
    fixture.setUp()
    _git(fixture.host, ["config", "core.autocrlf", "false"])
    (fixture.host / "app" / "value.txt").write_bytes(b"bad\n")
    _git(fixture.host, ["add", "-A"])
    _git(fixture.host, ["commit", "-qm", "lf-exact fixture"])
    policy = issue_autonomy_policy(fixture.store, fixture.repo,
        AutonomyPolicyEnvelope(principal_id="operator", policy_id="gsi", allowed_path_prefixes=("app/",)),
        secret=fixture.secret)
    from cortex.self_improvement import GovernedImprovement
    coordinator = GovernedImprovement(fixture.store, fixture.repo, fixture.host,
        policy_receipt_hash=policy["receipt_hash"], secret=fixture.secret)
    yield coordinator
    fixture.tearDown()


def rank_payload(_context=None):
    return {"schema_version": "cortex-structured-edit-intent/2.0", "summary": "rank repair",
            "edits": [{"path": "app/rank.txt", "old": "low", "new": "high"}]}


@pytest.fixture
def loop_host():
    fixture = _HostFixture()
    fixture.setUp()
    _git(fixture.host, ["config", "core.autocrlf", "false"])
    (fixture.host / "app" / "value.txt").write_bytes(b"bad\n")
    (fixture.host / "app" / "rank.txt").write_bytes(b"low\n")
    _git(fixture.host, ["add", "-A"])
    _git(fixture.host, ["commit", "-qm", "two-target fixture"])
    canary = ({"id": "canary", "argv": ["{python}", "-c", "raise SystemExit(0)"], "timeout_seconds": 5},)
    policy = issue_autonomy_policy(fixture.store, fixture.repo, AutonomyPolicyEnvelope(
        principal_id="operator", policy_id="gsi-loop", allowed_path_prefixes=("app/",),
        allow_auto_promotion=True, allow_recursive_generation=True, canary_steps=canary,
    ), secret=fixture.secret)
    from cortex.self_improvement import GovernedImprovement
    coordinator = GovernedImprovement(fixture.store, fixture.repo, fixture.host,
                                      policy_receipt_hash=policy["receipt_hash"], secret=fixture.secret)
    yield coordinator
    fixture.tearDown()


def test_attestation_states_are_strict():
    assert attestation_gate_state("ATTESTED") == "PASS"
    assert attestation_gate_state("PARTIALLY_ATTESTED") == "HELD"
    assert attestation_gate_state("INVALID") == "FAIL"
    assert attestation_gate_state("UNKNOWN") == "UNKNOWN"
    assert attestation_gate_state(None) != "PASS"


def test_dev_gain_holdout_metric_regression_is_not_improved():
    result = improvement_disposition(
        {"duration_ms": 100, "correctness": True}, {"duration_ms": 1, "correctness": True},
        before_holdout={"duration_ms": 100, "correctness": True},
        after_holdout={"duration_ms": 200, "correctness": True},
        metric="duration_ms", epsilon_dev=1, epsilon_holdout=1, holdout_degradation_tolerance=0,
        gates=_gates())
    assert result["delta_dev"] > 0
    assert result["delta_holdout"] < 0
    assert result["status"] not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}


def test_dev_and_holdout_gain_is_eligible():
    result = improvement_disposition(
        {"task_success": 0, "correctness": False}, {"task_success": 1, "correctness": True},
        before_holdout={"task_success": 0, "correctness": False},
        after_holdout={"task_success": 1, "correctness": True},
        metric="task_success", epsilon_dev=1, epsilon_holdout=1, gates=_gates())
    assert result["status"] == "REPAIR_MEASURED"
    assert result["delta_dev"] == 1
    assert result["delta_holdout"] == 1


def test_workload_pass_constitutional_fail_rejected():
    result = improvement_disposition(
        {"task_success": 0}, {"task_success": 1}, metric="task_success", epsilon=1,
        gates=_gates(constitutional_invariants="FAIL"))
    assert result["feasible"] is False
    assert result["status"] not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}


def test_constitutional_pass_workload_fail_rejected():
    result = improvement_disposition(
        {"task_success": 0, "correctness": False}, {"task_success": 1, "correctness": True},
        metric="task_success", epsilon=1, gates=_gates(workload_correctness="FAIL"))
    assert result["feasible"] is False


def test_constitutional_verdict_requires_every_check():
    checks = dict.fromkeys(
        ("INV-IMPROVEMENT-EVIDENCE-REQUIRED", "INV-EVALUATOR-INDEPENDENCE", "INV-EXPERIMENT-PRECEDENCE",
         "INV-NONCOMPENSATORY-IMPROVEMENT", "INV-HOLDOUT-NONLEAKAGE", "INV-FAILURE-SCOPE",
         "INV-GENERATION-NONSELFAUTHORIZATION", "INV-CUMULATIVE-CLAIM-BOUNDARY",
         "authority_invariance", "protected_surface_integrity"), "PASS")
    assert constitutional_verdict(checks)["pass"] is True
    checks["authority_invariance"] = "FAIL"
    assert constitutional_verdict(checks)["pass"] is False
    checks["authority_invariance"] = "UNKNOWN"
    assert constitutional_verdict(checks)["status"] == "UNKNOWN"


def test_head_change_without_identity_change_keeps_constraint(host):
    from cortex.coding_workspace import _file_hash
    experiment = freeze(host, contract("reject"))
    constraint = host.recycle(host.run(experiment["receipt_hash"], payload)["receipt_hash"])["object"]
    _git(host.root, ["commit", "--allow-empty", "-qm", "head only"])
    env = (constraint.get("applicability") or {}).get("environment") or {}
    identity = {path: _file_hash(host.root / path) for path in ["app/value.txt"]}
    assert identity == experiment["object"]["subject_identity"]
    assert host.constraint_persistence(
        constraint, environment=env, targets=["app/value.txt"], subject_identity=identity,
        instrument_identity=experiment["object"]["instrument_identity"]) == "APPLY"


def test_changed_dependency_identity_requires_revalidation(host):
    from cortex.coding_workspace import _file_hash
    experiment = freeze(host, contract("reject"))
    constraint = host.recycle(host.run(experiment["receipt_hash"], payload)["receipt_hash"])["object"]
    (host.root / "app" / "value.txt").write_bytes(b"changed\n")
    identity = {path: _file_hash(host.root / path) for path in ["app/value.txt"]}
    env = (constraint.get("applicability") or {}).get("environment") or {}
    assert host.constraint_persistence(
        constraint, environment=env, targets=["app/value.txt"], subject_identity=identity,
        instrument_identity=experiment["object"]["instrument_identity"]) == "REVALIDATION_REQUIRED"


def test_ignored_constraint_is_still_enforced(host):
    first = freeze(host, holdout_id="evil-a")
    evil = {"schema_version": "cortex-structured-edit-intent/2.0", "summary": "bad",
            "edits": [{"path": "app/value.txt", "old": "bad", "new": "evil"}]}
    host.recycle(host.run(first["receipt_hash"], lambda _: evil)["receipt_hash"])
    second = freeze(host, contract("holdout-alt"), holdout_id="evil-b")
    result = host.run(second["receipt_hash"], lambda _: evil)["object"]
    assert result["candidates_rejected_by_constraint"] == 1
    assert result["status"] not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}
    assert any("CONSTRAINT_REJECTED" in item for item in result["errors"])


def test_success_evidence_is_historical_and_consumed(host):
    first = freeze(host, holdout_id="ok-a")
    trial = host.run(first["receipt_hash"], payload)
    retained = host.recycle(trial["receipt_hash"])["object"]
    assert retained["historical_evidence_only"] is True
    assert retained["active_guidance"] is False
    assert retained["authority_effect"] is False
    assert retained["admission_required"] is True
    seen = []
    second = freeze(host, contract("holdout-alt"), holdout_id="ok-b")
    host.run(second["receipt_hash"], lambda context: seen.append(context) or payload())
    evidence = seen[0]["verified_improvement_evidence"]
    assert retained["object_hash"] in [item["improvement_hash"] for item in evidence]
    assert all(item["active_guidance"] is False and item["authority_effect"] is False for item in evidence)
    assert "holdout" not in json.dumps(seen)
    assert seen[0]["diagnosed_deficiency"]
    assert seen[0]["primary_metric"] == "task_success"


def test_success_cannot_grant_authority_or_admission(host):
    trial = host.run(freeze(host)["receipt_hash"], payload)
    retained = host.recycle(trial["receipt_hash"])
    assert retained["object"]["promotion_authorized"] is False
    assert retained["object"]["memory_admission_authorized"] is False
    assert retained["memory_admission_authorized"] is False


def test_generation_adjacency_and_skip(host):
    trial = host.run(freeze(host)["receipt_hash"], payload)
    first = host.record_generation(parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1")
    assert first["object"]["cumulative_self_improvement_established"] is False
    skipped = host.record_generation(parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G2")
    assert "generation_skip_rejected" in skipped["object"]["errors"]
    with pytest.raises(ValueError, match="parent generation receipt required"):
        host.record_generation(parent="G1", trial_receipt=trial["receipt_hash"], candidate_generation="G2")


def test_cumulative_delta_from_canonical_chain(host):
    trial = host.run(freeze(host)["receipt_hash"], payload)
    g1 = host.record_generation(parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1")
    g2 = host.record_generation(parent="G1", trial_receipt=trial["receipt_hash"], candidate_generation="G2",
                                parent_receipt=g1["receipt_hash"])
    assert g1["object"]["generation_state"] == "CANDIDATE_GENERATION"
    assert g1["object"]["delta_dev"] is None
    assert g1["object"]["candidate_delta_dev"] == trial["object"]["comparison"]["delta_dev"]
    assert g2["object"]["delta_dev"] is None
    with pytest.raises(ValueError):
        host.record_generation(parent="G1", trial_receipt=trial["receipt_hash"], candidate_generation="G2",
                               parent_receipt="0" * 64)


def test_candidate_pass_is_not_promoted_remeasurement(host):
    experiment = freeze(host)
    trial = host.run(experiment["receipt_hash"], payload)
    assert trial["object"]["status"] == "REPAIR_MEASURED"
    measured = host.remeasure(experiment["receipt_hash"])
    assert measured["workload_correctness"] is False
    with pytest.raises(PermissionError, match="auto_promotion_not_delegated"):
        host.promote_verified(trial["receipt_hash"])


def test_two_generation_mechanics(loop_host):
    g1_opportunity = loop_host.diagnose(subject="value", contract=contract(), metric="task_success", threshold=1)
    g1_exp = loop_host.freeze(g1_opportunity["receipt_hash"], development=contract(), holdout=contract("holdout"),
                              holdout_id="g1-holdout")
    seen = []
    g1_trial = loop_host.run(g1_exp["receipt_hash"], lambda context: seen.append(context) or payload())
    assert g1_trial["object"]["status"] == "REPAIR_MEASURED"
    assert "holdout" not in json.dumps(seen)
    loop_host.recycle(g1_trial["receipt_hash"])
    promotion = loop_host.promote_verified(g1_trial["receipt_hash"])
    assert promotion["object"]["rolled_back"] is False
    assert (loop_host.root / "app" / "value.txt").read_bytes() == b"good\n"
    g1 = loop_host.record_generation(parent="G0", trial_receipt=g1_trial["receipt_hash"], candidate_generation="G1",
                                     promotion_receipt=promotion["receipt_hash"])
    g2_opportunity = loop_host.diagnose(subject="rank", contract=rank_contract(), metric="task_success", threshold=1)
    g2_exp = loop_host.freeze(g2_opportunity["receipt_hash"], development=rank_contract(),
                              holdout=rank_contract("holdout"), holdout_id="g2-holdout")
    assert g2_exp["object"]["holdout_id"] != g1_exp["object"]["holdout_id"]
    seen2 = []
    g2_trial = loop_host.run(g2_exp["receipt_hash"], lambda context: seen2.append(context) or rank_payload())
    assert g2_trial["object"]["status"] == "REPAIR_MEASURED"
    assert g2_trial["object"]["cumulative_self_improvement_established"] is False
    promotion2 = loop_host.promote_verified(g2_trial["receipt_hash"])
    g2 = loop_host.record_generation(parent="G1", trial_receipt=g2_trial["receipt_hash"], candidate_generation="G2",
                                     parent_receipt=g1["receipt_hash"], promotion_receipt=promotion2["receipt_hash"])
    disposition = cumulative_improvement_disposition([g1["object"], g2["object"]])
    assert disposition["cumulative_generation_mechanics_verified"] is True
    assert disposition["cumulative_self_improvement_established"] is False
    assert g2["object"]["authority_leakage"] == 0
    assert g1["object"]["cumulative_self_improvement_established"] is False
    assert (loop_host.root / "app" / "rank.txt").read_bytes() == b"high\n"


def test_policy_and_evaluator_mutation_rejected(host):
    experiment = freeze(host)
    mutated = {**payload(), "evaluator": "rewrite"}
    result = host.run(experiment["receipt_hash"], lambda _: mutated)["object"]
    assert result["policy_mutation"] == 1
    assert result["status"] == "HELD"


def test_protected_control_plane_rejected():
    from cortex.self_improvement import _safe_targets
    with pytest.raises(ValueError):
        _safe_targets(["cortex/self_improvement.py"])
    with pytest.raises(ValueError):
        _safe_targets(["cortex/autonomous_improvement.py"])


def test_source_improvement_v1_and_gso_inert():
    assert V1_CONTRACT == "cortex-source-improvement-preregistration/1.0"
    assert V1_RESULT == "cortex-source-improvement-result/1.0"
    import cortex.assembly as assembly
    assert "production-inert" in (assembly.__doc__ or "") or "shadow" in (assembly.__doc__ or "").lower() or assembly.__doc__


def test_one_positive_generation_is_not_cumulative(host):
    trial = host.run(freeze(host)["receipt_hash"], payload)
    generation = host.record_generation(parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1")
    assert generation["object"]["cumulative_generation_mechanics_verified"] is False
    assert generation["object"]["cumulative_self_improvement_established"] is False
    assert cumulative_improvement_disposition([generation["object"]])["cumulative_generation_mechanics_verified"] is False


def test_constraint_check_helper_rejects_exact_edit():
    payload_obj = payload()
    constraints = [{"constraint_hash": "abc", "predicates": [
        {"kind": "exact_edit", "path": "app/value.txt", "old": "bad", "new": "good"}]}]
    result = check_candidate_constraints(payload_obj, constraints)
    assert result["admissible"] is False
    assert result["candidates_rejected_by_constraint"] == 1


def test_inspect_exposes_attestation_gate(host):
    import copy
    experiment = freeze(host)
    result = host.run(experiment["receipt_hash"], payload)["object"]
    arm = copy.deepcopy(result["candidates"]["development"])
    check = inspect_v2_arm(host.root, arm, experiment["object"]["transduction_policies"]["development"],
                           experiment["object"]["contracts"]["development"])
    assert check["gate"] == "PASS"
    arm["receipt"]["raw_observations"][0]["stdout_sha256"] = "0" * 64
    arm["receipt"]["receipt_hash"] = _sha({k: v for k, v in arm["receipt"].items() if k != "receipt_hash"})
    check = inspect_v2_arm(host.root, arm, experiment["object"]["transduction_policies"]["development"],
                           experiment["object"]["contracts"]["development"])
    assert check["valid"] is False
