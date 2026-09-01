"""Answer-sealed executable repair tasks for the post-semantic benchmark.

The public task contains only the defect description and buggy source.  Frozen
external tests and reference patches remain host-private.  Commissioning proves
that each evaluator distinguishes its unchanged baseline from one known repair;
it does not measure a model or authorize mutation.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .coding_workspace import CONTRACT_SCHEMA as VERIFY_SCHEMA
from .coding_workspace import (
    create_patch_proposal,
    repository_head,
    run_host_verification_step,
    verify_patch_in_isolated_worktree,
)
from .source_improvement import (
    create_source_improvement_contract,
    run_source_improvement_trial,
    verify_source_improvement_result,
)

PUBLIC_SCHEMA = "cortex-executable-repair-corpus/1.0"
PRIVATE_SCHEMA = "cortex-executable-repair-private/1.0"
RESULT_SCHEMA = "cortex-alpha31-executable-repair-forge/1.0"
CLAIM_BOUNDARY = (
    "A zero-call development forge with reference-patch discriminability. "
    "No model repair ability, general improvement, or mutation authority is established."
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def build_executable_repair_bundle(
    *, secret_seed: str, case_specs: list[Mapping[str, str]] | tuple[Mapping[str, str], ...]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a public task corpus and a separately sealable private evaluator bundle."""
    if not str(secret_seed):
        raise ValueError("a non-empty host secret seed is required")
    public_cases: list[dict[str, Any]] = []
    private_cases: list[dict[str, Any]] = []
    if not case_specs:
        raise ValueError("host-private executable case specifications are required")
    for raw in case_specs:
        required = {"case_id", "task", "source", "test", "patch"}
        if set(raw) != required or any(not str(raw.get(key) or "") for key in required):
            raise ValueError("each private case specification must contain exactly the required fields")
        salt = _sha({"seed": secret_seed, "case_id": raw["case_id"]})
        private_body = {"case_id": raw["case_id"], "external_test": raw["test"], "reference_patch": raw["patch"]}
        commitment = _sha({"salt": salt, "private": private_body})
        public_cases.append({
            "case_id": raw["case_id"],
            "task": raw["task"],
            "files": {"module.py": raw["source"]},
            "model_visible_files": ["TASK.md", "module.py"],
            "private_evaluator_commitment": commitment,
        })
        private_cases.append({**private_body, "salt": salt})
    public: dict[str, Any] = {
        "schema_version": PUBLIC_SCHEMA,
        "development_only": True,
        "case_count": len(public_cases),
        "cases": public_cases,
        "private_tests_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    public["corpus_hash"] = _sha(public)
    private: dict[str, Any] = {
        "schema_version": PRIVATE_SCHEMA,
        "corpus_hash": public["corpus_hash"],
        "cases": private_cases,
    }
    private["private_bundle_hash"] = _sha(private)
    return public, private


def verify_executable_repair_bundle(public: Mapping[str, Any], private: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    public_body = {key: value for key, value in public.items() if key != "corpus_hash"}
    private_body = {key: value for key, value in private.items() if key != "private_bundle_hash"}
    if public.get("schema_version") != PUBLIC_SCHEMA or public.get("corpus_hash") != _sha(public_body):
        errors.append("public_identity_invalid")
    if private.get("schema_version") != PRIVATE_SCHEMA or private.get("private_bundle_hash") != _sha(private_body):
        errors.append("private_identity_invalid")
    if private.get("corpus_hash") != public.get("corpus_hash"):
        errors.append("corpus_binding_invalid")
    public_cases = {str(case.get("case_id")): case for case in public.get("cases", []) if isinstance(case, Mapping)}
    private_cases = {str(case.get("case_id")): case for case in private.get("cases", []) if isinstance(case, Mapping)}
    if set(public_cases) != set(private_cases) or len(public_cases) != int(public.get("case_count") or -1):
        errors.append("case_identity_invalid")
    for case_id, case in public_cases.items():
        secret = private_cases.get(case_id, {})
        private_material = {key: secret.get(key) for key in ("case_id", "external_test", "reference_patch")}
        if case.get("private_evaluator_commitment") != _sha({"salt": secret.get("salt"), "private": private_material}):
            errors.append(f"private_commitment_invalid:{case_id}")
        if "external_test.py" in (case.get("files") or {}) or "reference_patch" in case:
            errors.append(f"private_material_disclosed:{case_id}")
    return {"valid": not errors, "errors": errors}


def _write_fixture(root: Path, case: Mapping[str, Any], private: Mapping[str, Any]) -> None:
    root.mkdir(parents=True)
    for name, content in (case.get("files") or {}).items():
        (root / str(name)).write_text(str(content), encoding="utf-8")
    (root / "TASK.md").write_text(str(case["task"]) + "\n", encoding="utf-8")
    (root / "external_test.py").write_text(str(private["external_test"]), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "cortex@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Cortex Forge"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "frozen executable task"], cwd=root, check=True)


def _verification_contract(proposal: Mapping[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": VERIFY_SCHEMA,
        "policy_id": "cortex-alpha31-frozen-external-test/1.0",
        "targets": list(proposal["targets"]),
        "steps": [{"id": "frozen_external_test", "argv": ["{python}", "external_test.py"], "timeout_seconds": 30}],
        "model_selected": False,
        "caller_selected": False,
        "promotion_authorized": False,
    }
    body["contract_hash"] = _sha(body)
    return body


def evaluate_executable_patch(
    public_case: Mapping[str, Any],
    private_case: Mapping[str, Any],
    patch_text: str,
    root: Path,
) -> dict[str, Any]:
    """Measure one proposed patch while retaining malformed candidates as FAIL."""
    _write_fixture(root, public_case, private_case)
    step = {
        "id": "frozen_external_test",
        "argv": ["{python}", "external_test.py"],
        "timeout_seconds": 30,
    }
    baseline = run_host_verification_step(root, step)
    proposal_hash: str | None = None
    candidate: dict[str, Any] = {
        "status": "held",
        "steps": [],
        "active_tree_mutated": False,
    }
    candidate_error: str | None = None
    try:
        proposal = create_patch_proposal(root, patch_text, "frontier-model executable repair candidate")
        proposal_hash = str(proposal["proposal_hash"])
        candidate = verify_patch_in_isolated_worktree(root, proposal, _verification_contract(proposal))
    except (OSError, RuntimeError, ValueError) as exc:
        candidate_error = type(exc).__name__ + ":" + str(exc)[:500]
    baseline_pass = bool(baseline.get("passed"))
    candidate_pass = candidate.get("status") == "verified"
    classification = (
        "REPAIR_MEASURED" if not baseline_pass and candidate_pass
        else "VERIFIED_MAINTENANCE" if baseline_pass and candidate_pass
        else "REGRESSION_DETECTED" if baseline_pass
        else "IMPROVEMENT_HELD"
    )
    material: dict[str, Any] = {
        "schema_version": "cortex-executable-patch-evaluation/1.0",
        "case_id": str(public_case["case_id"]),
        "source_head": repository_head(root),
        "evaluator_commitment": str(public_case["private_evaluator_commitment"]),
        "proposal_hash": proposal_hash,
        "patch_hash": hashlib.sha256(str(patch_text).encode("utf-8")).hexdigest(),
        "baseline": baseline,
        "candidate": candidate,
        "candidate_error": candidate_error,
        "baseline_pass": baseline_pass,
        "candidate_pass": candidate_pass,
        "classification": classification,
        "bounded_repair_established": classification == "REPAIR_MEASURED",
        "general_improvement_established": False,
        "active_tree_mutated": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    material["evaluation_hash"] = _sha(material)
    return material


def commission_executable_repair_forge(public: Mapping[str, Any], private: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Run deterministic baseline/reference checks without invoking a model."""
    audit = verify_executable_repair_bundle(public, private)
    if not audit["valid"]:
        raise ValueError("executable repair bundle invalid: " + ",".join(audit["errors"]))
    private_cases = {str(case["case_id"]): case for case in private["cases"]}
    cases: list[dict[str, Any]] = []
    for public_case in public["cases"]:
        case_id = str(public_case["case_id"])
        workspace = root / case_id
        secret = private_cases[case_id]
        _write_fixture(workspace, public_case, secret)
        proposal = create_patch_proposal(workspace, str(secret["reference_patch"]), "host reference repair")
        verification = verify_patch_in_isolated_worktree(workspace, proposal, _verification_contract(proposal))
        verification = {**verification, "kind": "coding_patch_verification"}
        verification["receipt_hash"] = _sha(verification)
        contract = create_source_improvement_contract(workspace, proposal, verification)
        result = run_source_improvement_trial(workspace, proposal, verification, contract)
        result_audit = verify_source_improvement_result(result)
        cases.append({
            "case_id": case_id,
            "evaluator_commitment": public_case["private_evaluator_commitment"],
            "source_head": result["source_head"],
            "baseline_pass": result["arms"]["baseline"]["all_host_checks_pass"],
            "reference_candidate_pass": result["arms"]["candidate"]["all_host_checks_pass"],
            "classification": result["status"],
            "counterfactual_result_hash": result["result_hash"],
            "canonical_result_valid": result_audit["valid"],
            "active_tree_mutated": result["active_tree_mutated"],
        })
    ready = all(
        not case["baseline_pass"] and case["reference_candidate_pass"]
        and case["classification"] == "REPAIR_MEASURED" and case["canonical_result_valid"]
        and not case["active_tree_mutated"]
        for case in cases
    )
    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        "state": "EXECUTABLE_REPAIR_FORGE_READY" if ready else "EXECUTABLE_REPAIR_FORGE_HELD",
        "corpus_hash": public["corpus_hash"],
        "case_count": len(cases),
        "cases": cases,
        "reference_repairs_measured": sum(case["classification"] == "REPAIR_MEASURED" for case in cases),
        "additional_model_calls": 0,
        "private_tests_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "private_bundle_persisted_in_artifact": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "semantic_transfer_established": False,
        "general_improvement_established": False,
        "next_action": "freeze_frontier_model_executable_repair_screen" if ready else "repair_forge",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    result["result_hash"] = _sha(result)
    return result


def verify_executable_repair_forge_result(result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("schema_version") != RESULT_SCHEMA or result.get("result_hash") != _sha(body):
        errors.append("result_identity_invalid")
    cases = result.get("cases") if isinstance(result.get("cases"), list) else []
    ready = bool(cases) and len(cases) == result.get("case_count") and all(
        case.get("baseline_pass") is False
        and case.get("reference_candidate_pass") is True
        and case.get("classification") == "REPAIR_MEASURED"
        and case.get("canonical_result_valid") is True
        and case.get("active_tree_mutated") is False
        for case in cases if isinstance(case, Mapping)
    )
    if result.get("state") != ("EXECUTABLE_REPAIR_FORGE_READY" if ready else "EXECUTABLE_REPAIR_FORGE_HELD"):
        errors.append("result_state_invalid")
    if result.get("additional_model_calls") != 0:
        errors.append("model_call_boundary_invalid")
    for field in ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect", "semantic_transfer_established", "general_improvement_established"):
        if result.get(field) is not False:
            errors.append(f"authority_or_claim_boundary_invalid:{field}")
    return {"valid": not errors, "errors": errors, "state": result.get("state")}


__all__ = [
    "PUBLIC_SCHEMA", "PRIVATE_SCHEMA", "RESULT_SCHEMA", "build_executable_repair_bundle",
    "commission_executable_repair_forge", "evaluate_executable_patch",
    "verify_executable_repair_bundle",
    "verify_executable_repair_forge_result",
]
