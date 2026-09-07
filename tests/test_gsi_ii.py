"""GSI-II controls use local fixture cognition; no provider calls."""
import copy
import hashlib
import json

import pytest

from cortex.autonomous_improvement import AutonomyPolicyEnvelope, issue_autonomy_policy
from cortex.coding_workspace import CONTRACT_SCHEMA, _git, _sha
from cortex.self_improvement import (
    HARD_GATES, GovernedImprovement, _safe_targets, improvement_disposition,
    inspect_v2_arm,
)
import test_v100_alpha8_autonomy as legacy_fixture


def contract(mode="dev"):
    code = "from pathlib import Path; assert Path('app/value.txt').read_text().strip() == 'good'"
    if mode == "holdout":
        code = "from pathlib import Path; assert Path('app/value.txt').read_bytes() == b'good\\n'"
    if mode == "reject":
        code = "raise SystemExit(1)"
    body = {"schema_version": CONTRACT_SCHEMA, "policy_id": mode,
            "targets": ["app/value.txt"], "steps": [{"id": mode, "argv": ["{python}", "-c", code], "timeout_seconds": 5}],
            "model_selected": False, "caller_selected": False, "promotion_authorized": False}
    return {**body, "contract_hash": _sha(body)}


@pytest.fixture
def host():
    fixture = legacy_fixture.V100Alpha8AutonomyTests()
    fixture.setUp()
    # v2 declares exact LF bytes; preserve the legacy v1 fixture unchanged.
    (fixture.host / "app/value.txt").write_bytes(b"bad\n")
    _git(fixture.host, ["config", "core.autocrlf", "false"])
    _git(fixture.host, ["add", "app/value.txt"])
    _git(fixture.host, ["commit", "--allow-empty", "-qm", "exact LF v2 fixture"])
    _git(fixture.host, ["config", "core.autocrlf", "false"])
    (fixture.host / "app" / "value.txt").write_bytes(b"bad\n")
    _git(fixture.host, ["add", "-A"])
    _git(fixture.host, ["commit", "-qm", "lf-exact fixture"])
    policy = issue_autonomy_policy(fixture.store, fixture.repo,
        AutonomyPolicyEnvelope(principal_id="operator", policy_id="gsi", allowed_path_prefixes=("app/",)),
        secret=fixture.secret)
    coordinator = GovernedImprovement(fixture.store, fixture.repo, fixture.host,
        policy_receipt_hash=policy["receipt_hash"], secret=fixture.secret)
    yield coordinator
    fixture.tearDown()


def payload(context=None):
    return {"schema_version": "cortex-structured-edit-intent/2.0", "summary": "fixture repair",
            "edits": [{"path": "app/value.txt", "old": "bad", "new": "good"}]}


def freeze(host, holdout=None, holdout_id="fresh-panel"):
    opportunity = host.diagnose(subject="fixture ranking", contract=contract(), metric="task_success", threshold=1)
    return host.freeze(opportunity["receipt_hash"], development=contract(),
                       holdout=holdout or contract("holdout"), holdout_id=holdout_id)


def test_real_worktrees_attested_matched_repair(host):
    experiment = freeze(host)
    seen = []
    def generate(context):
        seen.append(context)
        return payload()
    receipt = host.run(experiment["receipt_hash"], generate)
    result = receipt["object"]
    assert result["status"] == "REPAIR_MEASURED", result
    assert result["comparison"]["primary_delta"] == 1
    assert result["holdout_used_for_generation"] is False
    assert "holdout" not in json.dumps(seen)
    assert seen[0]["applicable_constraints"] == []
    assert (host.root / "app/value.txt").read_text() == "bad\n"
    retained = host.recycle(receipt["receipt_hash"])["object"]
    assert retained["schema_version"] == "cortex-verified-improvement/1.0"
    assert retained["active_guidance"] is False
    assert retained["authority_effect"] is False
    with pytest.raises(ValueError, match="exhausted"):
        host.run(experiment["receipt_hash"], payload)


def test_missing_opportunity_held(host):
    with pytest.raises(ValueError, match="missing"):
        host.freeze("absent", development=contract(), holdout=contract("holdout"), holdout_id="x")


def test_defeated_opportunity_held(host):
    opportunity = host.diagnose(subject="x", contract=contract(), metric="task_success", threshold=1, active_defeaters=["instrument challenge"])
    assert opportunity["object"]["disposition"] == "HELD"
    with pytest.raises(ValueError, match="HELD"):
        host.freeze(opportunity["receipt_hash"], development=contract(), holdout=contract("holdout"), holdout_id="x")


def test_no_deficit_remains_held(host):
    opportunity = host.diagnose(subject="x", contract=contract(), metric="task_success", threshold=0)
    assert opportunity["object"]["disposition"] == "HELD"
    assert opportunity["object"]["opportunity_id"]
    assert opportunity["object"]["authority_effect"] is False
    assert opportunity["object"]["production_effect"] is False


@pytest.mark.parametrize("field", ["evaluator", "metric", "experiment", "allowed_targets"])
def test_candidate_cannot_change_rules(host, field):
    experiment = freeze(host)
    candidate = {**payload(), field: "override"}
    trial = host.run(experiment["receipt_hash"], lambda _: candidate)
    assert trial["object"]["status"] == "HELD"
    assert trial["object"]["errors"]
    constraint = host.recycle(trial["receipt_hash"])
    assert constraint["object"]["status"] == "HELD_CONSTRAINT"
    assert host.store.symbiotic_receipt(trial["receipt_hash"], repo=host.repo)


@pytest.mark.parametrize("path", ["tests/test.py", ".github/workflows/test.yml", "cortex/will.py",
    "cortex/native_agent.py", "cortex/source_improvement.py", "cortex/self_improvement.py",
    "cortex/transduction_policy.py", "../escape.py", "C:/escape.py", "app/../tests/x.py"])
def test_scope_is_closed(path):
    with pytest.raises(ValueError):
        _safe_targets([path])


@pytest.mark.parametrize("gate", HARD_GATES)
@pytest.mark.parametrize("state", ["FAIL", "UNKNOWN"])
def test_performance_cannot_compensate_for_gate(gate, state):
    gates = dict.fromkeys(HARD_GATES, "PASS")
    gates[gate] = state
    result = improvement_disposition({"task_success": 0}, {"task_success": 10**12},
                                    metric="task_success", epsilon=1, gates=gates)
    assert result["feasible"] is False
    assert result["status"] not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}


def test_speed_does_not_compensate_for_correctness():
    result = improvement_disposition({"duration_ms": 100, "correctness": True},
        {"duration_ms": 1, "correctness": False}, metric="duration_ms", epsilon=1,
        gates=dict.fromkeys(HARD_GATES, "PASS"))
    assert result["status"] == "REGRESSION_DETECTED"


def test_dev_gain_holdout_failure(host):
    experiment = freeze(host, contract("reject"))
    result = host.run(experiment["receipt_hash"], payload)["object"]
    assert result["comparison"]["gates"]["workload_correctness"] == "FAIL"
    assert result["status"] in {"HELD", "REGRESSION_DETECTED"}
    assert result["status"] not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}


def test_baseline_head_changed_aborts(host):
    experiment = freeze(host)
    _git(host.root, ["commit", "--allow-empty", "-qm", "new head"])
    with pytest.raises(ValueError, match="HEAD changed"):
        host.run(experiment["receipt_hash"], payload)


def test_holdout_cannot_be_reserved_twice(host):
    freeze(host)
    with pytest.raises(ValueError, match="reserved"):
        freeze(host)


def test_raw_tamper_rejected_even_with_outer_rehash(host):
    experiment = freeze(host)
    result = host.run(experiment["receipt_hash"], payload)["object"]
    arm = copy.deepcopy(result["candidates"]["development"])
    arm["receipt"]["raw_observations"][0]["stdout_sha256"] = hashlib.sha256(b"fake").hexdigest()
    arm["receipt"]["receipt_hash"] = _sha({k: v for k, v in arm["receipt"].items() if k != "receipt_hash"})
    exp = experiment["object"]
    check = inspect_v2_arm(host.root, arm, exp["transduction_policies"]["development"], exp["contracts"]["development"])
    assert check["valid"] is False


def test_policy_secret_required(host):
    with pytest.raises(PermissionError):
        GovernedImprovement(host.store, host.repo, host.root, policy_receipt_hash=host.policy_receipt_hash, secret="wrong")


def test_generation_cannot_self_verify_or_imply_next(host):
    experiment = freeze(host)
    trial = host.run(experiment["receipt_hash"], payload)
    with pytest.raises(ValueError, match="self-verify"):
        host.record_generation(parent="G1", trial_receipt=trial["receipt_hash"], candidate_generation="G1")
    generation = host.record_generation(parent="G0", trial_receipt=trial["receipt_hash"], candidate_generation="G1")
    assert generation["object"]["cumulative_improvement_established"] is False
    assert generation["object"]["status"] == "HELD"
    assert "recursive_generation_not_delegated" in generation["object"]["errors"]


def test_constraint_scope_does_not_universalize(host):
    experiment = freeze(host, contract("reject"))
    trial = host.run(experiment["receipt_hash"], payload)
    constraint = host.recycle(trial["receipt_hash"])["object"]
    assert constraint["status"] == "HELD_CONSTRAINT"
    env = dict((constraint.get("applicability") or {}).get("environment") or {})
    env["os_family"] = "Linux"
    linux = env
    assert host.constraint_applies(constraint, environment=linux, targets=["other.py"]) is False
    unknown = dict(env)
    unknown.pop("os_family", None)
    assert host.constraint_applies(constraint, environment=unknown, targets=["app/value.txt"]) is False
    same = dict((constraint.get("applicability") or {}).get("environment") or {})
    assert host.constraint_applies(constraint, environment=same, targets=["app/value.txt"]) is True
    assert host.store.symbiotic_receipt(trial["receipt_hash"], repo=host.repo)


def test_next_generation_consumes_scoped_constraints(host):
    first = freeze(host, contract("reject"), holdout_id="panel-a")
    trial = host.run(first["receipt_hash"], payload)
    constraint = host.recycle(trial["receipt_hash"])["object"]
    assert constraint["status"] == "HELD_CONSTRAINT"
    seen = []
    second = freeze(host, holdout_id="panel-b")
    def generate(context):
        seen.append(context)
        return payload()
    later = host.run(second["receipt_hash"], generate)["object"]
    assert constraint["object_hash"] in later["constraints_present"]
    assert later["constraints_consumed"] == []
    persistence = host.constraint_persistence(
        constraint, environment=second["object"]["environment"], targets=["app/value.txt"],
        subject_identity=second["object"]["subject_identity"],
        instrument_identity=second["object"]["instrument_identity"])
    assert persistence == "REVALIDATION_REQUIRED"
    assert "holdout" not in json.dumps(seen)


def test_source_improvement_v1_still_distinct():
    from cortex.source_improvement import CONTRACT_SCHEMA, RESULT_SCHEMA
    assert CONTRACT_SCHEMA == "cortex-source-improvement-preregistration/1.0"
    assert RESULT_SCHEMA == "cortex-source-improvement-result/1.0"
