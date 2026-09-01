"""Live structured-edit baseline over an external-private executable corpus."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import __version__
from .adapter_provenance import EVIDENCE_LIVE, resolve_adapter_provenance, verify_adapter_provenance
from .edit_intent import INTENT_SCHEMA, compile_edit_intent
from .executable_repair_forge import evaluate_executable_patch, verify_executable_repair_bundle
from .native_agent import NativeAgentRuntime, verify_native_agent_trajectory
from .symbiosis import open_symbiotic_session

PLANNED_CALLS = 4


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _identity(adapter: Any) -> dict[str, str]:
    return {key: str(getattr(adapter, key, "") or "") for key in ("provider_family", "model_id", "model_version", "adapter_id", "adapter_version")}


def _screen(successes: int) -> dict[str, Any]:
    calibrated = successes == 2
    return {
        "case_count": 4, "success_count": successes, "success_rate": successes / 4,
        "target_window": {"minimum": 0.30, "maximum": 0.70},
        "state": "structured_baseline_calibrated" if calibrated else "screening_floor" if successes <= 1 else "screening_ceiling",
        "recommended_action": "freeze_fresh_sham_relevant_treatment" if calibrated else "forge_easier_structured_tasks" if successes <= 1 else "forge_harder_structured_tasks",
        "development_only": True, "confirmatory_eligible": False,
    }


def freeze_structured_repair_screen(store: Any, repo: str, *, forge_artifact: Mapping[str, Any], private_bundle: Mapping[str, Any], adapter: Any) -> dict[str, Any]:
    public = forge_artifact.get("public_corpus") or {}
    if forge_artifact.get("state") != "EXECUTABLE_REPAIR_FORGE_READY" or verify_executable_repair_bundle(public, private_bundle).get("valid") is not True:
        raise ValueError("valid external-private executable forge is required")
    identity = _identity(adapter)
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if not all(identity.values()) or verify_adapter_provenance(store, repo, provenance).get("valid") is not True or provenance.get("evidence_class") != EVIDENCE_LIVE:
        raise ValueError("host-registered live adapter provenance is required")
    cases = list(public.get("cases") or ())
    if len(cases) != PLANNED_CALLS:
        raise ValueError("structured screen requires exactly four cases")
    response_contract = {
        "schema_version": INTENT_SCHEMA,
        "format": "one JSON object only; no markdown fences",
        "exact_top_level_keys": ["schema_version", "summary", "edits"],
        "edit_keys": ["path", "old", "new"],
        "allowed_paths": ["module.py"],
        "rule": "old must be an exact unique source substring; express the smallest complete repair",
    }
    material = {
        "schema_version": "cortex-structured-repair-preregistration/1.0", "version": __version__,
        "kind": "structured_repair_preregistration", "forge_result_hash": forge_artifact["result_hash"],
        "corpus_hash": public["corpus_hash"], "private_bundle_hash": private_bundle["private_bundle_hash"],
        "cases": cases, "planned_calls": 4, "context_treatment": "task_only_control",
        "tools": [], "response_contract": response_contract, "model_identity": identity,
        "adapter_provenance": provenance, "status": "frozen_before_execution",
        "private_specs_origin": "outside_repository", "development_only": True,
        "semantic_transfer_established": False, "advisory_only": True,
        "host_mutate_authorized": False, "execution_authorized": False,
        "memory_admission_authorized": False, "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze external-private structured repair screen", persist=True)
    return store.append_symbiotic_receipt(repo, {**material, "session_id": session["session_id"], "turn_id": 0, "event_id": f"structured_repair_prereg_{_sha(material)[:24]}", "body_epoch_id": session["body_epoch_id"]})


def execute_structured_repair_screen(store: Any, repo: str, *, preregistration: Mapping[str, Any], private_bundle: Mapping[str, Any], adapter: Any, tools: Any, grant: Any) -> dict[str, Any]:
    prereg_hash = str(preregistration.get("receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        raise ValueError("canonical structured preregistration required")
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    if prereg.get("kind") != "structured_repair_preregistration" or _identity(adapter) != prereg.get("model_identity") or resolve_adapter_provenance(store, repo, adapter) != prereg.get("adapter_provenance"):
        raise ValueError("structured runtime binding invalid")
    private_cases = {str(case["case_id"]): case for case in private_bundle["cases"]}
    runtime = NativeAgentRuntime(store, repo, tools=tools)
    sealed = []
    for case in prereg["cases"]:
        task = f"{case['task']}\n\nFILE: module.py\n```python\n{case['files']['module.py']}\n```\n\nRESPONSE_CONTRACT\n{_canonical(prereg['response_contract'])}"
        run = runtime.run(task, adapter=adapter, grant=grant, context_treatment="task_only_control")
        trajectory_hash = str(run["trajectory_receipt_hash"])
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            raise ValueError(f"trajectory invalid:{case['case_id']}")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        output = str(trajectory.get("final_answer") or "")
        compilation = None
        compiler_error = None
        with tempfile.TemporaryDirectory(prefix="cortex-alpha34-compile-") as parent:
            compile_root = Path(parent)
            (compile_root / "module.py").write_text(str(case["files"]["module.py"]), encoding="utf-8")
            try:
                compilation = compile_edit_intent(compile_root, output, allowed_targets=["module.py"])
                candidate_text = compilation["proposal"]["patch"]
            except (OSError, ValueError) as exc:
                compiler_error = type(exc).__name__ + ":" + str(exc)[:500]
                candidate_text = output
        with tempfile.TemporaryDirectory(prefix="cortex-alpha34-eval-") as parent:
            evaluation = evaluate_executable_patch(case, private_cases[str(case["case_id"])], candidate_text, Path(parent) / "repo")
        material = {
            "schema_version": "cortex-structured-repair-case/1.0", "version": __version__,
            "kind": "structured_repair_case", "preregistration_receipt_hash": prereg_hash,
            "case_id": case["case_id"], "case_hash": _sha(case), "trajectory_receipt_hash": trajectory_hash,
            "public_output_hash": hashlib.sha256(output.encode()).hexdigest(),
            "compilation_hash": compilation.get("compilation_hash") if compilation else None,
            "proposal_hash": compilation.get("proposal_hash") if compilation else None,
            "compiler_error": compiler_error, "evaluation": evaluation,
            "task_success": evaluation["candidate_pass"], "evidence_class": EVIDENCE_LIVE,
            "caller_success_authoritative": False, "advisory_only": True,
            "host_mutate_authorized": False, "execution_authorized": False,
            "memory_admission_authorized": False, "policy_effect": False,
        }
        session = open_symbiotic_session(store, repo, task=f"seal structured repair {case['case_id']}", persist=True)
        sealed.append(store.append_symbiotic_receipt(repo, {**material, "session_id": session["session_id"], "turn_id": 0, "event_id": f"structured_repair_case_{_sha(material)[:24]}", "body_epoch_id": session["body_epoch_id"]}))
    screen = _screen(sum(case["task_success"] is True for case in sealed))
    material = {
        "schema_version": "cortex-structured-repair-result/1.0", "version": __version__,
        "kind": "structured_repair_result", "preregistration_receipt_hash": prereg_hash,
        "case_receipt_hashes": [case["receipt_hash"] for case in sealed], "model_identity": prereg["model_identity"],
        "evidence_class": EVIDENCE_LIVE, "screen": screen, "calls_executed": len(sealed),
        "baseline_calibrated": screen["state"] == "structured_baseline_calibrated",
        "semantic_transfer_established": False, "general_improvement_established": False,
        "next_action": screen["recommended_action"], "status": "STRUCTURED_REPAIR_SCREEN_RECONSTRUCTED",
        "advisory_only": True, "host_mutate_authorized": False, "execution_authorized": False,
        "memory_admission_authorized": False, "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="seal structured repair result", persist=True)
    return store.append_symbiotic_receipt(repo, {**material, "session_id": session["session_id"], "turn_id": 0, "event_id": f"structured_repair_result_{_sha(material)[:24]}", "body_epoch_id": session["body_epoch_id"]})


def verify_structured_repair_screen(store: Any, repo: str, *, result_receipt_hash: str) -> dict[str, Any]:
    errors = []
    if store.verify_symbiotic_receipt(repo, result_receipt_hash).get("valid") is not True:
        return {"valid": False, "errors": ["result_receipt_invalid"]}
    result = store.symbiotic_receipt(result_receipt_hash, repo=repo) or {}
    prereg_hash = str(result.get("preregistration_receipt_hash") or "")
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True or prereg.get("kind") != "structured_repair_preregistration":
        errors.append("preregistration_invalid")
    observed = []
    successes = 0
    for receipt_hash in result.get("case_receipt_hashes") or ():
        if store.verify_symbiotic_receipt(repo, str(receipt_hash)).get("valid") is not True:
            errors.append(f"case_invalid:{receipt_hash}")
            continue
        case = store.symbiotic_receipt(str(receipt_hash), repo=repo) or {}
        observed.append(str(case.get("case_id") or ""))
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True or case.get("public_output_hash") != hashlib.sha256(str(trajectory.get("final_answer") or "").encode()).hexdigest():
            errors.append(f"trajectory_binding_invalid:{case.get('case_id')}")
        evaluation = case.get("evaluation") or {}
        if evaluation.get("evaluation_hash") != _sha({key: value for key, value in evaluation.items() if key != "evaluation_hash"}) or case.get("task_success") is not evaluation.get("candidate_pass"):
            errors.append(f"evaluation_binding_invalid:{case.get('case_id')}")
        successes += case.get("task_success") is True
    if observed != [str(case["case_id"]) for case in prereg.get("cases") or ()] or result.get("screen") != _screen(successes):
        errors.append("screen_reconstruction_invalid")
    for field in ("semantic_transfer_established", "general_improvement_established", "host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"):
        if result.get(field) is not False:
            errors.append(f"authority_or_claim_invalid:{field}")
    return {"valid": not errors, "errors": errors, "screen": _screen(successes), "result_receipt_hash": result_receipt_hash, "preregistration_receipt_hash": prereg_hash}


__all__ = ["freeze_structured_repair_screen", "execute_structured_repair_screen", "verify_structured_repair_screen"]
