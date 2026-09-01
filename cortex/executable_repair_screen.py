"""Frozen live frontier-model screen over answer-sealed executable repairs."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import __version__
from .adapter_provenance import EVIDENCE_LIVE, resolve_adapter_provenance, verify_adapter_provenance
from .executable_repair_forge import evaluate_executable_patch, verify_executable_repair_bundle
from .native_agent import NativeAgentRuntime, verify_native_agent_trajectory
from .symbiosis import open_symbiotic_session

PLANNED_CALLS = 4


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _adapter_identity(adapter: Any) -> dict[str, str]:
    return {
        key: str(getattr(adapter, key, "") or "")
        for key in ("provider_family", "model_id", "model_version", "adapter_id", "adapter_version")
    }


def _extract_patch(output: str) -> str:
    text = str(output or "").strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    marker = text.find("diff --git ")
    if marker < 0:
        return text
    return text[marker:].strip() + "\n"


def _screen(successes: int, case_count: int) -> dict[str, Any]:
    rate = successes / case_count if case_count else 0.0
    calibrated = successes == 2 and case_count == 4
    return {
        "case_count": case_count,
        "success_count": successes,
        "success_rate": rate,
        "target_window": {"minimum": 0.30, "maximum": 0.70},
        "state": "executable_baseline_calibrated" if calibrated else "screening_floor" if successes <= 1 else "screening_ceiling",
        "recommended_action": "freeze_sham_relevant_treatment" if calibrated else "forge_easier_executable_tasks" if successes <= 1 else "forge_harder_executable_tasks",
        "development_only": True,
        "confirmatory_eligible": False,
    }


def freeze_executable_repair_screen(
    store: Any,
    repo: str,
    *,
    forge_artifact: Mapping[str, Any],
    private_bundle: Mapping[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    public = forge_artifact.get("public_corpus") or {}
    if forge_artifact.get("state") != "EXECUTABLE_REPAIR_FORGE_READY":
        raise ValueError("canonical ready alpha.31 forge artifact is required")
    if verify_executable_repair_bundle(public, private_bundle).get("valid") is not True:
        raise ValueError("alpha.31 public/private bundle binding is invalid")
    if forge_artifact.get("corpus_hash") != public.get("corpus_hash"):
        raise ValueError("forge artifact corpus binding is invalid")
    identity = _adapter_identity(adapter)
    if not all(identity.values()):
        raise ValueError("complete adapter identity is required")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if verify_adapter_provenance(store, repo, provenance).get("valid") is not True or provenance.get("evidence_class") != EVIDENCE_LIVE:
        raise ValueError("host-registered live adapter provenance is required")
    cases = list(public.get("cases") or ())
    if len(cases) != PLANNED_CALLS:
        raise ValueError("alpha.32 requires exactly four public repair cases")
    material = {
        "schema_version": "cortex-executable-repair-preregistration/1.0",
        "version": __version__,
        "kind": "executable_repair_preregistration",
        "source_forge_result_hash": forge_artifact.get("result_hash"),
        "corpus_hash": public["corpus_hash"],
        "private_bundle_hash": private_bundle["private_bundle_hash"],
        "cases": cases,
        "planned_calls": PLANNED_CALLS,
        "context_treatment": "task_only_control",
        "model_visible_files": ["TASK.md", "module.py"],
        "withheld": ["external_test.py", "reference_patch", "private_commitment_salt"],
        "tools": [],
        "model_identity": identity,
        "adapter_provenance": provenance,
        "response_contract": "Return only one git unified diff beginning with diff --git. Modify module.py only.",
        "status": "frozen_before_execution",
        "development_only": True,
        "semantic_transfer_established": False,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze executable repair screen", persist=True)
    return store.append_symbiotic_receipt(repo, {
        **material,
        "session_id": session["session_id"], "turn_id": 0,
        "event_id": f"executable_repair_prereg_{_sha(material)[:24]}",
        "body_epoch_id": session["body_epoch_id"],
    })


def execute_executable_repair_screen(
    store: Any,
    repo: str,
    *,
    preregistration: Mapping[str, Any],
    private_bundle: Mapping[str, Any],
    adapter: Any,
    tools: Any,
    grant: Any,
) -> dict[str, Any]:
    prereg_hash = str(preregistration.get("receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        raise ValueError("canonical executable preregistration is required")
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    if prereg.get("kind") != "executable_repair_preregistration":
        raise ValueError("executable preregistration kind invalid")
    public = {"schema_version": "cortex-executable-repair-corpus/1.0", "development_only": True, "case_count": 4, "cases": prereg["cases"], "private_tests_in_model_context": False, "private_reference_patches_in_model_context": False, "claim_boundary": "A zero-call development forge with reference-patch discriminability. No model repair ability, general improvement, or mutation authority is established.", "corpus_hash": prereg["corpus_hash"]}
    if verify_executable_repair_bundle(public, private_bundle).get("valid") is not True:
        raise ValueError("runtime public/private bundle invalid")
    if _adapter_identity(adapter) != prereg.get("model_identity") or resolve_adapter_provenance(store, repo, adapter) != prereg.get("adapter_provenance"):
        raise ValueError("runtime adapter binding changed after preregistration")
    private_cases = {str(case["case_id"]): case for case in private_bundle["cases"]}
    runtime = NativeAgentRuntime(store, repo, tools=tools)
    sealed: list[dict[str, Any]] = []
    for case in prereg["cases"]:
        task = f"{case['task']}\n\nFILE: module.py\n```python\n{case['files']['module.py']}\n```\n\n{prereg['response_contract']}"
        run = runtime.run(task, adapter=adapter, grant=grant, context_treatment="task_only_control")
        trajectory_hash = str(run["trajectory_receipt_hash"])
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            raise ValueError(f"native trajectory invalid for {case['case_id']}")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        patch = _extract_patch(str(trajectory.get("final_answer") or ""))
        with tempfile.TemporaryDirectory(prefix="cortex-alpha32-case-") as parent:
            evaluation = evaluate_executable_patch(case, private_cases[str(case["case_id"])], patch, Path(parent) / "repo")
        material = {
            "schema_version": "cortex-executable-repair-case/1.0", "version": __version__,
            "kind": "executable_repair_case", "preregistration_receipt_hash": prereg_hash,
            "case_id": case["case_id"], "case_hash": _sha(case),
            "trajectory_receipt_hash": trajectory_hash, "patch_hash": evaluation["patch_hash"],
            "evaluation": evaluation, "task_success": evaluation["candidate_pass"],
            "evidence_class": EVIDENCE_LIVE, "caller_success_authoritative": False,
            "advisory_only": True, "host_mutate_authorized": False, "execution_authorized": False,
            "memory_admission_authorized": False, "policy_effect": False,
        }
        session = open_symbiotic_session(store, repo, task=f"seal executable repair {case['case_id']}", persist=True)
        sealed.append(store.append_symbiotic_receipt(repo, {
            **material, "session_id": session["session_id"], "turn_id": 0,
            "event_id": f"executable_repair_case_{_sha(material)[:24]}", "body_epoch_id": session["body_epoch_id"],
        }))
    screen = _screen(sum(case["task_success"] is True for case in sealed), len(sealed))
    material = {
        "schema_version": "cortex-executable-repair-result/1.0", "version": __version__,
        "kind": "executable_repair_result", "preregistration_receipt_hash": prereg_hash,
        "case_receipt_hashes": [case["receipt_hash"] for case in sealed],
        "model_identity": prereg["model_identity"], "evidence_class": EVIDENCE_LIVE,
        "screen": screen, "calls_executed": len(sealed),
        "baseline_calibrated": screen["state"] == "executable_baseline_calibrated",
        "semantic_transfer_established": False, "general_improvement_established": False,
        "next_action": screen["recommended_action"], "status": "EXECUTABLE_REPAIR_SCREEN_RECONSTRUCTED",
        "advisory_only": True, "host_mutate_authorized": False, "execution_authorized": False,
        "memory_admission_authorized": False, "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="seal executable repair result", persist=True)
    return store.append_symbiotic_receipt(repo, {
        **material, "session_id": session["session_id"], "turn_id": 0,
        "event_id": f"executable_repair_result_{_sha(material)[:24]}", "body_epoch_id": session["body_epoch_id"],
    })


def verify_executable_repair_screen(store: Any, repo: str, *, result_receipt_hash: str) -> dict[str, Any]:
    errors: list[str] = []
    if store.verify_symbiotic_receipt(repo, result_receipt_hash).get("valid") is not True:
        return {"valid": False, "errors": ["result_receipt_invalid"]}
    result = store.symbiotic_receipt(result_receipt_hash, repo=repo) or {}
    prereg_hash = str(result.get("preregistration_receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        errors.append("preregistration_receipt_invalid")
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    observed: list[str] = []
    successes = 0
    for receipt_hash in result.get("case_receipt_hashes") or ():
        if store.verify_symbiotic_receipt(repo, str(receipt_hash)).get("valid") is not True:
            errors.append(f"case_receipt_invalid:{receipt_hash}")
            continue
        case = store.symbiotic_receipt(str(receipt_hash), repo=repo) or {}
        observed.append(str(case.get("case_id") or ""))
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            errors.append(f"trajectory_invalid:{case.get('case_id')}")
        evaluation = case.get("evaluation") or {}
        evaluation_body = {key: value for key, value in evaluation.items() if key != "evaluation_hash"}
        if evaluation.get("evaluation_hash") != _sha(evaluation_body):
            errors.append(f"evaluation_identity_invalid:{case.get('case_id')}")
        if case.get("patch_hash") != evaluation.get("patch_hash") or case.get("task_success") is not evaluation.get("candidate_pass"):
            errors.append(f"evaluation_binding_invalid:{case.get('case_id')}")
        successes += case.get("task_success") is True
    expected_ids = [str(case["case_id"]) for case in prereg.get("cases") or ()]
    if observed != expected_ids or len(observed) != PLANNED_CALLS:
        errors.append("case_sequence_invalid")
    rebuilt = _screen(successes, len(observed))
    if result.get("screen") != rebuilt or result.get("calls_executed") != len(observed):
        errors.append("screen_aggregate_invalid")
    for field in ("semantic_transfer_established", "general_improvement_established", "host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"):
        if result.get(field) is not False:
            errors.append(f"authority_or_claim_boundary_invalid:{field}")
    return {"valid": not errors, "errors": errors, "screen": rebuilt, "result_receipt_hash": result_receipt_hash, "preregistration_receipt_hash": prereg_hash}


__all__ = ["freeze_executable_repair_screen", "execute_executable_repair_screen", "verify_executable_repair_screen"]
