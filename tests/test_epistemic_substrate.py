"""Zero-call adversarial panel for the epistemic substrate and shadow kernel."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from benchmarks.transduction_assurance import _intent, _repository
from cortex.assurance import assemble_assurance_case, load_claim_registry, typed_assurance_debt, validate_claim_registry
from cortex.coding_workspace import run_host_verification_step
from cortex.edit_intent import (
    INTENT_SCHEMA_V2,
    PARSER_SEMANTICS_STRICT,
    compile_edit_intent,
    _compile_edit_intent,
)
from cortex.epistemic_snapshot import compile_context_packet, derive_epistemic_snapshot, measure_navigation_fidelity
from cortex.executable_repair_forge import _verification_contract
from cortex.shadow_organization import (
    adaptation_proposal,
    bounded_self_stabilization_panel,
    mechanical_recursive_closure,
    organization_state_view,
    selection_decision,
)
from cortex.transduction_policy import (
    execute_bound_transduction,
    freeze_transduction_policy,
    inspect_observation_conformance,
    receipt_satisfies_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def fixture(tmp_path, evaluator="from pathlib import Path\nassert Path('a.py').read_bytes() == b'v = 2\\n'\n"):
    root = tmp_path / "repo"
    _repository(root, {"a.py": "v = 1\n"}, evaluator)
    return root


def policy_for(root):
    intent = _intent([("a.py", "1", "2")])
    compiled = compile_edit_intent(root, intent, allowed_targets=["a.py"])
    contract = _verification_contract(compiled["proposal"])
    policy = freeze_transduction_policy(
        root,
        policy_id="test-policy",
        allowed_targets=["a.py"],
        verification_contract=contract,
        evaluator_id=contract["policy_id"],
    )
    return intent, contract, policy


def test_bound_transduction_pass(tmp_path):
    root = fixture(tmp_path)
    intent, contract, policy = policy_for(root)
    result = execute_bound_transduction(root, policy, intent, contract)
    assert result["receipt"]["typed_outcome"] == "PASS"
    assert result["receipt"]["failure_attribution"] == "OBSERVED_CANDIDATE_PASS"
    assert result["conformance"]["valid"]
    assert result["receipt"]["authority_effect"] is False


def test_policy_modified_after_cognition_rejected(tmp_path):
    root = fixture(tmp_path)
    intent, contract, policy = policy_for(root)
    policy = dict(policy)
    policy["timeout_seconds"] = 1
    result = execute_bound_transduction(root, policy, intent, contract)
    assert result["receipt"]["failure_attribution"] == "POLICY_BINDING_FAILURE"


def test_wrong_policy_receipt_binding(tmp_path):
    root = fixture(tmp_path)
    intent, contract, policy = policy_for(root)
    result = execute_bound_transduction(root, policy, intent, contract)
    other = dict(policy)
    other["policy_id"] = "other"
    other.pop("policy_hash")
    from cortex.transduction_policy import _sha
    other["policy_hash"] = _sha({key: value for key, value in other.items() if key != "policy_hash"})
    check = receipt_satisfies_policy(result["receipt"], other)
    assert not check["valid"]
    assert "wrong_policy_receipt_binding" in check["errors"]


def test_stale_subject_head_rejected(tmp_path):
    root = fixture(tmp_path)
    intent, contract, policy = policy_for(root)
    (root / "extra.txt").write_text("x\n", encoding="utf-8")
    from cortex.coding_workspace import _git
    assert _git(root, ["add", "extra.txt"]).returncode == 0
    assert _git(root, ["commit", "-qm", "stale"]).returncode == 0
    result = execute_bound_transduction(root, policy, intent, contract)
    assert result["receipt"]["failure_attribution"] == "SUBJECT_SOURCE_BINDING_FAILURE"


def test_compiler_implementation_mismatch(tmp_path):
    root = fixture(tmp_path)
    intent, contract, policy = policy_for(root)
    mutated = dict(policy)
    hashes = dict(mutated["allowed_compiler_implementation_identity"])
    hashes["edit_intent.py"] = "0" * 64
    mutated["allowed_compiler_implementation_identity"] = hashes
    from cortex.transduction_policy import _sha
    mutated["policy_hash"] = _sha({key: value for key, value in mutated.items() if key != "policy_hash"})
    result = execute_bound_transduction(root, mutated, intent, contract)
    assert result["receipt"]["failure_attribution"] == "COMPILER_BINDING_FAILURE"


def test_environment_requirement_mismatch_holds(tmp_path):
    root = fixture(tmp_path)
    intent, contract, policy = policy_for(root)
    mutated = dict(policy)
    mutated["environment_requirements"] = {**mutated["environment_requirements"], "os_family": "NotThisOS"}
    from cortex.transduction_policy import _sha
    mutated["policy_hash"] = _sha({key: value for key, value in mutated.items() if key != "policy_hash"})
    result = execute_bound_transduction(root, mutated, intent, contract)
    assert result["receipt"]["failure_attribution"] == "ENVIRONMENT_MISMATCH"
    assert result["receipt"]["typed_outcome"] == "HELD"


def test_evaluator_write_outside_surface(tmp_path):
    root = fixture(tmp_path, "from pathlib import Path\nPath('evil.txt').write_text('x')\n")
    intent, contract, policy = policy_for(root)
    result = execute_bound_transduction(root, policy, intent, contract)
    assert result["receipt"]["failure_attribution"] == "OBSERVATION_SURFACE_VIOLATION"


def test_stdout_and_stderr_limits(tmp_path):
    root = tmp_path
    stdout = run_host_verification_step(root, {
        "argv": ["{python}", "-c", "import sys; sys.stdout.buffer.write(b'x'*200)"],
        "timeout_seconds": 10,
        "max_stdout_bytes": 50,
        "observation_schema": "cortex-host-raw-observation/1.2",
    })
    assert stdout["failure_attribution"] == "OUTPUT_LIMIT_EXCEEDED"
    assert not stdout["passed"]
    assert stdout["raw_observation"]["capture_complete"] is False
    stderr = run_host_verification_step(root, {
        "argv": ["{python}", "-c", "import sys; sys.stderr.buffer.write(b'y'*200)"],
        "timeout_seconds": 10,
        "max_stderr_bytes": 50,
        "observation_schema": "cortex-host-raw-observation/1.2",
    })
    assert stderr["failure_attribution"] == "OUTPUT_LIMIT_EXCEEDED"


def test_timeout_partial_capture_incomplete(tmp_path):
    result = run_host_verification_step(tmp_path, {
        "argv": ["{python}", "-c", "import sys,time; sys.stdout.buffer.write(b'partial'); sys.stdout.buffer.flush(); time.sleep(30)"],
        "timeout_seconds": 1,
        "max_stdout_bytes": 1024,
        "observation_schema": "cortex-host-raw-observation/1.2",
    })
    assert not result["passed"]
    assert result["raw_observation"]["timed_out"]
    assert result["raw_observation"]["capture_complete"] is False
    assert result["raw_observation"]["stdout_sha256"] == hashlib.sha256(b"partial").hexdigest()
    assert result["failure_attribution"] in {"PROCESS_TIMEOUT", "CAPTURE_INCOMPLETE"}


def test_identical_preview_distinct_raw_bytes_under_limits(tmp_path):
    first = run_host_verification_step(tmp_path, {
        "argv": ["{python}", "-c", "import sys; sys.stdout.buffer.write(b'\\xff'+b'x'*5000)"],
        "timeout_seconds": 10,
        "max_stdout_bytes": 100_000,
        "observation_schema": "cortex-host-raw-observation/1.2",
    })
    second = run_host_verification_step(tmp_path, {
        "argv": ["{python}", "-c", "import sys; sys.stdout.buffer.write(b'\\xfe'+b'x'*5000)"],
        "timeout_seconds": 10,
        "max_stdout_bytes": 100_000,
        "observation_schema": "cortex-host-raw-observation/1.2",
    })
    assert first["output"] == second["output"]
    assert first["raw_observation"]["stdout_sha256"] != second["raw_observation"]["stdout_sha256"]


def test_historical_intent_under_new_parser_rejected(tmp_path):
    root = fixture(tmp_path)
    payload = {"schema_version": INTENT_SCHEMA_V2, "summary": "x", "edits": [{"path": "a.py", "old": "1", "new": "2"}]}
    with pytest.raises(ValueError, match="historical intent interpreted under new parser semantics"):
        _compile_edit_intent(root, payload, allowed_targets=["a.py"], legacy=True)
    numeric = {"schema_version": "cortex-structured-edit-intent/1.0", "summary": "x",
               "edits": [{"path": "a.py", "old": 1, "new": 2}]}
    legacy = _compile_edit_intent(root, numeric, allowed_targets=["a.py"], legacy=True)
    with pytest.raises(ValueError, match="strings"):
        compile_edit_intent(root, numeric, allowed_targets=["a.py"], parser_semantics_id=PARSER_SEMANTICS_STRICT)
    rebuilt = compile_edit_intent(root, legacy["intent"], allowed_targets=["a.py"], parser_semantics_id=PARSER_SEMANTICS_STRICT)
    assert rebuilt["schema_version"] != legacy["schema_version"]


def test_observation_conformance_rejects_malformed_success():
    step = {
        "passed": True,
        "returncode": 0,
        "argv": ["python", "external_test.py"],
        "raw_observation": {
            "stdout_byte_length": -1,
            "stderr_byte_length": 0,
            "timed_out": True,
            "capture_complete": False,
            "returncode": 0,
        },
        "environment": {"authority_effect": True},
    }
    result = inspect_observation_conformance(step, frozen_argv=["python", "external_test.py"])
    assert not result["valid"]
    assert "successful_but_incomplete_capture" in result["errors"]
    assert "successful_but_timed_out_capture" in result["errors"]
    assert "negative_stdout_byte_length" in result["errors"]
    assert "environment_authority_leak" in result["errors"]


def test_active_defeater_blocks_verified_claim():
    registry = load_claim_registry(ROOT / "docs/CORTEX_CLAIM_REGISTRY.json")
    claim = copy.deepcopy(next(item for item in registry["claims"] if item["claim_id"] == "platform.declared_ci_matrix"))
    claim["status"] = "VERIFIED"
    claim["active_defeaters"] = ["instrument_challenged"]
    case = assemble_assurance_case(claim, registry=registry)
    assert case["disposition"] == "HELD"
    assert case["stronger_claim_blocked"] is True
    assert case["authority_effect"] is False


def test_unknown_dimension_blocks_stronger_claim():
    debt = typed_assurance_debt({
        "source": "PASS", "transduction": "UNKNOWN", "environment": "PASS", "instrument": "PASS",
        "experiment": "PASS", "causal": "PASS", "applicability": "PASS", "replication": "PASS",
    })
    assert debt["noncompensatory_meet"] == "UNKNOWN"
    registry = load_claim_registry(ROOT / "docs/CORTEX_CLAIM_REGISTRY.json")
    claim = copy.deepcopy(next(item for item in registry["claims"] if item["claim_id"] == "platform.declared_ci_matrix"))
    claim["status"] = "VERIFIED"
    claim["assurance_debt"]["transduction"] = "UNKNOWN"
    claim["required_dimensions"] = ["source", "transduction"]
    case = assemble_assurance_case(claim, registry=registry)
    assert case["stronger_claim_blocked"] is True


def test_stale_evidence_marked_current_fails_docs_check():
    registry = load_claim_registry(ROOT / "docs/CORTEX_CLAIM_REGISTRY.json")
    changed = copy.deepcopy(registry)
    changed["claims"][0]["evidence"] = [{"path": "docs/STATUS.md", "currency": "current", "superseded": True}]
    errors = validate_claim_registry(changed, root=ROOT)
    assert any(item.startswith("stale_evidence_marked_current") for item in errors)


def test_snapshot_and_context_packet_reject_unbound_and_historical():
    snapshot = derive_epistemic_snapshot(ROOT)
    rebuilt = derive_epistemic_snapshot(ROOT)
    assert snapshot["snapshot_hash"] == rebuilt["snapshot_hash"]
    packet = compile_context_packet("Where is prospective transduction policy frozen?", snapshot, root=ROOT)
    assert packet["valid"]
    assert packet["snapshot_identity"] == snapshot["snapshot_hash"]
    stale = dict(snapshot)
    stale["source_head"] = "0" * 40
    with pytest.raises(ValueError):
        compile_context_packet("task", {"schema_version": "nope"}, root=ROOT)
    mixed = compile_context_packet("transduction observation compiler", stale, root=ROOT)
    assert mixed["valid"] is False
    assert "stale_snapshot_identity" in mixed["errors"]


def test_navigation_fidelity_finite_panel():
    panel = measure_navigation_fidelity()
    assert panel["n_tasks"] == 12
    assert panel["correct"] == 12
    assert panel["N_f"] == 1.0


def test_claim_registry_valid():
    registry = load_claim_registry(ROOT / "docs/CORTEX_CLAIM_REGISTRY.json")
    assert validate_claim_registry(registry, root=ROOT) == []
    held = [claim["claim_id"] for claim in registry["claims"] if claim["status"] == "HELD"]
    assert "environment.full_applicability" in held
    assert next(claim["status"] for claim in registry["claims"] if claim["claim_id"] == "gso.retention_utility") == "NOT_ESTABLISHED"


def test_mechanical_recursive_closure_and_self_authorization():
    closure = mechanical_recursive_closure()
    assert closure["R_c"] == "PASS_MECHANICAL"
    assert closure["difference"]["with"] != closure["difference"]["without"]
    assert closure["utility_established"] is False
    assert closure["authority_effect"] is False
    view = organization_state_view(snapshot_hash="abc")
    proposal = adaptation_proposal(
        proposal_id="p1", kind="retrieval_ranking", delta={"boost": 1}, hypothesis="rank", prior_state_hash=view["state_hash"],
    )
    decision = selection_decision(selected=proposal, rejected=[], held=[], reason="shadow")
    assert decision["authority_effect"] is False
    with pytest.raises(ValueError):
        adaptation_proposal(proposal_id="bad", kind="authority", delta={}, hypothesis="widen", prior_state_hash=view["state_hash"])


def test_contradicted_prior_and_homeostatic_stabilization():
    panel = bounded_self_stabilization_panel("snapshot")
    assert panel["S_r"] is True
    assert panel["authority_leakage"] == 0
    assert panel["T_s"] >= 1
    by_name = {item["disturbance"]: item for item in panel["results"]}
    assert by_name["contradicted_prior"]["response"] == "QUARANTINE"
    recovered_priors = by_name["contradicted_prior"]["recovered_state"]["priors"]
    assert all(not prior.get("active") for prior in recovered_priors)


def test_post_hoc_replay_not_independent_replication():
    registry = load_claim_registry(ROOT / "docs/CORTEX_CLAIM_REGISTRY.json")
    claim = next(item for item in registry["claims"] if item["claim_id"] == "gso.organizational_heredity")
    case = assemble_assurance_case(claim, registry=registry)
    assert case["replication_state"] == "NOT_TESTED"
    assert case["disposition"] == "NOT_ESTABLISHED"
