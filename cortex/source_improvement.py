"""Preregistered counterfactual source-improvement trials for Cortex.

One unchanged baseline and one exact patched candidate are evaluated from the
same Git HEAD under a host-frozen command contract.  This establishes bounded
repair evidence; it does not establish general or autonomous self-improvement.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .coding_workspace import (
    repository_head,
    run_host_verification_step,
    verify_patch_proposal,
)

CONTRACT_SCHEMA = "cortex-source-improvement-preregistration/1.0"
RESULT_SCHEMA = "cortex-source-improvement-result/1.0"
RESULT_HASH_FIELDS = (
    "schema_version", "contract_hash", "contract", "source_head", "proposal_hash",
    "verification_receipt_hash", "execution_order", "arms", "paired_effect",
    "candidate_postimage_hashes", "status", "bounded_repair_established",
    "general_improvement_established", "active_tree_mutated",
    "operator_promotion_required", "host_mutate_authorized", "execution_authorized",
    "memory_admission_authorized", "policy_effect", "claim_boundary",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _git(root: Path, arguments: list[str], patch: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments], cwd=root, input=patch, text=True, capture_output=True,
        encoding="utf-8", errors="replace", timeout=180, check=False, shell=False,
    )


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"


def _environment_material() -> dict[str, Any]:
    return {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(),
    }


def _result_material(result: Mapping[str, Any]) -> dict[str, Any]:
    """Return the schema-defined body, excluding later immutable-ledger fields."""
    return {key: result.get(key) for key in RESULT_HASH_FIELDS}


def create_source_improvement_contract(
    root: str | Path,
    proposal: Mapping[str, Any],
    verification_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze the host evaluator before either counterfactual arm executes."""
    workspace = Path(root).resolve()
    if verification_receipt.get("kind") != "coding_patch_verification" or verification_receipt.get("status") != "verified":
        raise ValueError("a canonical passing patch verification is required")
    if verification_receipt.get("proposal_hash") != proposal.get("proposal_hash"):
        raise ValueError("verification receipt does not bind the proposal")
    if verification_receipt.get("source_head") != repository_head(workspace):
        raise ValueError("verification source HEAD is no longer current")
    verification_contract = verification_receipt.get("contract")
    if not isinstance(verification_contract, Mapping) or not isinstance(verification_contract.get("steps"), list):
        raise ValueError("verification receipt does not contain a host evaluator")
    environment = _environment_material()
    body: dict[str, Any] = {
        "schema_version": CONTRACT_SCHEMA,
        "claim_kind": "bounded_defect_repair",
        "source_head": str(verification_receipt["source_head"]),
        "proposal_hash": str(proposal["proposal_hash"]),
        "verification_receipt_hash": str(verification_receipt.get("receipt_hash") or ""),
        "evaluator_contract_hash": str(verification_receipt.get("contract_hash") or ""),
        "evaluator_steps": json.loads(_canonical(verification_contract["steps"])),
        "arm_order_commitment": _sha({"proposal_hash": proposal["proposal_hash"], "source_head": verification_receipt["source_head"]}),
        "environment": environment,
        "environment_hash": _sha(environment),
        "primary_metric": "all_host_checks_pass",
        "minimum_effect": 1.0,
        "required_baseline_state": "fail",
        "required_candidate_state": "pass",
        "model_selected_evaluator": False,
        "caller_selected_evaluator": False,
        "operator_promotion_required": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    body["contract_hash"] = _sha(body)
    return body


def verify_source_improvement_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    material = {key: value for key, value in dict(contract).items() if key != "contract_hash"}
    errors: list[str] = []
    if contract.get("schema_version") != CONTRACT_SCHEMA:
        errors.append("contract_schema_invalid")
    if contract.get("contract_hash") != _sha(material):
        errors.append("contract_hash_invalid")
    if contract.get("model_selected_evaluator") is not False or contract.get("caller_selected_evaluator") is not False:
        errors.append("evaluator_authority_invalid")
    if not isinstance(contract.get("evaluator_steps"), list) or not contract.get("evaluator_steps"):
        errors.append("evaluator_steps_missing")
    if contract.get("environment_hash") != _sha(contract.get("environment")):
        errors.append("environment_hash_invalid")
    return {"valid": not errors, "errors": errors}


def _arm(root: Path, contract: Mapping[str, Any], name: str) -> dict[str, Any]:
    started = time.perf_counter()
    steps: list[dict[str, Any]] = []
    for declared in contract["evaluator_steps"]:
        result = run_host_verification_step(root, declared)
        steps.append(result)
        if not result["passed"]:
            break
    passed = len(steps) == len(contract["evaluator_steps"]) and all(step["passed"] for step in steps)
    return {
        "arm": name,
        "steps": steps,
        "all_host_checks_pass": passed,
        "task_success": 1.0 if passed else 0.0,
        "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


def run_source_improvement_trial(
    root: str | Path,
    proposal: Mapping[str, Any],
    verification_receipt: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    workspace = Path(root).resolve()
    contract_check = verify_source_improvement_contract(contract)
    if not contract_check["valid"]:
        raise ValueError("source improvement contract invalid: " + ",".join(contract_check["errors"]))
    proposal_check = verify_patch_proposal(workspace, proposal)
    if not proposal_check["valid"] or not proposal_check["current"]:
        raise ValueError("source proposal is invalid or stale")
    if contract.get("proposal_hash") != proposal.get("proposal_hash"):
        raise ValueError("source improvement contract proposal mismatch")
    if contract.get("verification_receipt_hash") != verification_receipt.get("receipt_hash"):
        raise ValueError("source improvement contract verification mismatch")
    if contract.get("source_head") != repository_head(workspace):
        raise ValueError("repository HEAD changed before counterfactual trial")
    if contract.get("environment_hash") != _sha(_environment_material()):
        raise ValueError("host environment changed after preregistration")

    order = ["baseline", "candidate"] if int(str(contract["arm_order_commitment"])[0], 16) % 2 == 0 else ["candidate", "baseline"]
    arms: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="cortex-improvement-") as parent:
        paths = {name: Path(parent) / name for name in order}
        created: list[Path] = []
        try:
            for name in order:
                added = _git(workspace, ["worktree", "add", "--detach", str(paths[name]), str(contract["source_head"])])
                if added.returncode != 0:
                    raise RuntimeError(f"{name} counterfactual worktree could not be created")
                created.append(paths[name])
            candidate = paths["candidate"]
            applied = _git(candidate, ["apply", "--check", "--whitespace=error-all", "-"], str(proposal["patch"]))
            if applied.returncode != 0:
                raise ValueError("candidate patch does not apply to the frozen source HEAD")
            applied = _git(candidate, ["apply", "--whitespace=error-all", "-"], str(proposal["patch"]))
            if applied.returncode != 0:
                raise RuntimeError("candidate patch application failed")
            for name in order:
                arms[name] = _arm(paths[name], contract, name)
            candidate_postimages = {
                str(target): _file_hash(candidate / str(target)) for target in proposal.get("targets") or []
            }
        finally:
            for path in reversed(created):
                _git(workspace, ["worktree", "remove", "--force", str(path)])
            _git(workspace, ["worktree", "prune"])

    baseline = bool(arms["baseline"]["all_host_checks_pass"])
    candidate_pass = bool(arms["candidate"]["all_host_checks_pass"])
    effect = int(candidate_pass) - int(baseline)
    if not baseline and candidate_pass:
        status = "REPAIR_MEASURED"
    elif baseline and candidate_pass:
        status = "VERIFIED_MAINTENANCE"
    elif baseline and not candidate_pass:
        status = "REGRESSION_DETECTED"
    else:
        status = "IMPROVEMENT_HELD"
    receipt: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        "contract_hash": contract["contract_hash"],
        "contract": dict(contract),
        "source_head": contract["source_head"],
        "proposal_hash": proposal["proposal_hash"],
        "verification_receipt_hash": verification_receipt["receipt_hash"],
        "execution_order": order,
        "arms": arms,
        "paired_effect": effect,
        "candidate_postimage_hashes": candidate_postimages,
        "status": status,
        "bounded_repair_established": status == "REPAIR_MEASURED",
        "general_improvement_established": False,
        "active_tree_mutated": False,
        "operator_promotion_required": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "claim_boundary": "One matched source counterfactual; not general, autonomous, cognitive, or conscious self-improvement.",
    }
    receipt["result_hash"] = _sha(_result_material(receipt))
    return receipt


def verify_source_improvement_result(result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if result.get("schema_version") != RESULT_SCHEMA:
        errors.append("result_schema_invalid")
    if result.get("result_hash") != _sha(_result_material(result)):
        errors.append("result_hash_invalid")
    contract_check = verify_source_improvement_contract(result.get("contract") if isinstance(result.get("contract"), Mapping) else {})
    if not contract_check["valid"]:
        errors.extend(contract_check["errors"])
    contract = result.get("contract") if isinstance(result.get("contract"), Mapping) else {}
    if result.get("contract_hash") != contract.get("contract_hash"):
        errors.append("result_contract_binding_invalid")
    if result.get("proposal_hash") != contract.get("proposal_hash"):
        errors.append("result_proposal_binding_invalid")
    if result.get("source_head") != contract.get("source_head"):
        errors.append("result_source_binding_invalid")
    if result.get("verification_receipt_hash") != contract.get("verification_receipt_hash"):
        errors.append("result_verification_binding_invalid")
    arms = result.get("arms") if isinstance(result.get("arms"), Mapping) else {}
    baseline = bool((arms.get("baseline") or {}).get("all_host_checks_pass"))
    candidate = bool((arms.get("candidate") or {}).get("all_host_checks_pass"))
    expected = "REPAIR_MEASURED" if not baseline and candidate else "VERIFIED_MAINTENANCE" if baseline and candidate else "REGRESSION_DETECTED" if baseline else "IMPROVEMENT_HELD"
    if result.get("status") != expected:
        errors.append("result_classification_invalid")
    if result.get("paired_effect") != int(candidate) - int(baseline):
        errors.append("paired_effect_invalid")
    if result.get("bounded_repair_established") is not (expected == "REPAIR_MEASURED"):
        errors.append("repair_claim_invalid")
    if result.get("general_improvement_established") is not False:
        errors.append("general_improvement_claim_invalid")
    for field in ("active_tree_mutated", "host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"):
        if result.get(field) is not False:
            errors.append(f"authority_boundary_invalid:{field}")
    return {"valid": not errors, "errors": errors, "status": expected}


__all__ = [
    "CONTRACT_SCHEMA", "RESULT_SCHEMA", "create_source_improvement_contract",
    "run_source_improvement_trial", "verify_source_improvement_contract",
    "verify_source_improvement_result",
]
