"""Live structured-edit baseline over an external-private executable corpus."""

from __future__ import annotations

import hashlib
import json
import tempfile
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import __version__
from .adapter_provenance import EVIDENCE_LIVE, resolve_adapter_provenance, verify_adapter_provenance
from .contract_aligned_repair import (
    executable_bundle_from_contract_aligned,
    verify_contract_aligned_repair_forge_result,
)
from .edit_intent import INTENT_SCHEMA, compile_edit_intent
from .executable_repair_forge import evaluate_executable_patch, verify_executable_repair_bundle
from .native_agent import NativeAgentRuntime, verify_native_agent_trajectory
from .symbiosis import open_symbiotic_session

PLANNED_CALLS = 4
REPEAT_POLICY = {
    "purpose": "fixed_corpus_repeatability",
    "new_calls": 4,
    "automatic_retries": 0,
    "difficulty_change_authorized": False,
    "fresh_distinct_tasks": 0,
    "confirmatory_eligible": False,
}


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _identity(adapter: Any) -> dict[str, str]:
    return {
        key: str(getattr(adapter, key, "") or "")
        for key in ("provider_family", "model_id", "model_version", "adapter_id", "adapter_version")
    }


def _case_task(case: Mapping[str, Any], response_contract: Mapping[str, Any]) -> str:
    return (
        f"{case['task']}\n\nFILE: module.py\n```python\n{case['files']['module.py']}\n```"
        f"\n\nRESPONSE_CONTRACT\n{_canonical(response_contract)}"
    )


def _private_binding_errors(prereg: Mapping[str, Any], private: Mapping[str, Any]) -> list[str]:
    errors = []
    body = {key: value for key, value in private.items() if key != "private_bundle_hash"}
    if private.get("private_bundle_hash") != _sha(body) or private.get("private_bundle_hash") != prereg.get("private_bundle_hash"):
        errors.append("private_bundle_hash_invalid")
    if private.get("corpus_hash") != prereg.get("corpus_hash"):
        errors.append("private_corpus_binding_invalid")
    cases = private.get("cases") or []
    expected = prereg.get("cases") or []
    if not isinstance(cases, list) or any(not isinstance(case, Mapping) for case in cases):
        return errors + ["private_cases_invalid"]
    if [case.get("case_id") for case in cases] != [case.get("case_id") for case in expected]:
        errors.append("private_case_order_invalid")
    for public, secret in zip(expected, cases):
        material = {key: secret.get(key) for key in ("case_id", "external_test", "reference_patch")}
        if public.get("private_evaluator_commitment") != _sha({"salt": secret.get("salt"), "private": material}):
            errors.append("private_evaluator_binding_invalid")
    return errors


def _assert_evaluators_unchallenged(store: Any, repo: str, cases: list[dict[str, Any]]) -> None:
    """A host challenge can close inference, never grant it or rewrite history.

    Challenges are exact-commitment scoped and append-only. A corrected evaluator
    needs a new commitment; a caller's 'resolved' flag cannot reopen this one.
    Historical receipt reconstruction deliberately does not consult this gate.
    """
    challenges = store.symbiotic_receipts_by_kind(repo, "repair_evaluator_challenge", limit=10000)
    if len(challenges) == 10000:
        raise ValueError("evaluator challenge coverage unknown; no model calls permitted")
    commitments = {case["private_evaluator_commitment"] for case in cases}
    for challenge in challenges:
        if challenge.get("evaluator_commitment") in commitments:
            raise ValueError("evaluator challenged; create and verify a corrected evaluator before new model calls")


def _screen(successes: int) -> dict[str, Any]:
    calibrated = successes == 2
    return {
        "case_count": 4,
        "success_count": successes,
        "success_rate": successes / 4,
        "target_window": {"minimum": 0.30, "maximum": 0.70},
        "state": "structured_baseline_calibrated"
        if calibrated
        else "screening_floor"
        if successes <= 1
        else "screening_ceiling",
        "recommended_action": "freeze_fresh_sham_relevant_treatment"
        if calibrated
        else "forge_easier_structured_tasks"
        if successes <= 1
        else "forge_harder_structured_tasks",
        "development_only": True,
        "confirmatory_eligible": False,
    }


def _screen_for_prereg(prereg: Mapping[str, Any], successes: int) -> dict[str, Any]:
    if prereg.get("repeatability_binding") is None:
        return _screen(successes)
    return {
        "case_count": 4,
        "success_count": successes,
        "success_rate": successes / 4,
        "state": "repeatability_observed",
        "recommended_action": "inspect_repeatability_before_fresh_case_confirmation",
        "development_only": True,
        "confirmatory_eligible": False,
    }


def _repeat_binding_errors(store: Any, repo: str, prereg: Mapping[str, Any]) -> list[str]:
    binding = prereg.get("repeatability_binding")
    if binding is None:
        return [] if prereg.get("schema_version") == "cortex-structured-repair-preregistration/1.0" else ["screen_policy_missing"]
    if (
        not isinstance(binding, Mapping)
        or set(binding) != {"prior_result_receipt_hash", "policy"}
        or _canonical(binding.get("policy")) != _canonical(REPEAT_POLICY)
        or prereg.get("schema_version") != "cortex-structured-repair-preregistration/1.1"
        or prereg.get("prior_screen_binding") is not None
    ):
        return ["repeatability_policy_invalid"]
    prior_hash = str(binding["prior_result_receipt_hash"])
    prior = store.symbiotic_receipt(prior_hash, repo=repo) or {}
    origin = store.symbiotic_receipt(str(prior.get("preregistration_receipt_hash") or ""), repo=repo) or {}
    # No recursive receipt graph: a repeat points to a legacy baseline, not another repeat.
    if origin.get("repeatability_binding") is not None:
        return ["repeatability_origin_must_be_baseline"]
    if verify_structured_repair_screen(store, repo, result_receipt_hash=prior_hash).get("valid") is not True:
        return ["repeatability_origin_invalid"]
    frozen_fields = (
        "cases", "corpus_hash", "private_bundle_hash", "response_contract",
        "model_identity", "adapter_provenance", "context_treatment", "tools", "planned_calls",
    )
    return [f"repeatability_binding_changed:{field}" for field in frozen_fields if prereg.get(field) != origin.get(field)]


def _repeat_comparison(store: Any, repo: str, prereg: Mapping[str, Any], cases: list[dict[str, Any]]) -> dict[str, Any]:
    prior = store.symbiotic_receipt(prereg["repeatability_binding"]["prior_result_receipt_hash"], repo=repo)
    origins = [store.symbiotic_receipt(value, repo=repo) for value in prior["case_receipt_hashes"]]
    rows = [{
        "case_id": new["case_id"],
        "prior_success": old["task_success"],
        "repeat_success": new["task_success"],
        "same_outcome": old["task_success"] is new["task_success"],
    } for old, new in zip(origins, cases)]
    return {
        "case_pairs": rows,
        "distinct_task_count": len(rows),
        "invocation_observations": len(rows) * 2,
        "changed_outcomes": sum(not row["same_outcome"] for row in rows),
        "repeated_failures": sum(not row["prior_success"] and not row["repeat_success"] for row in rows),
        "independent_task_sample_size": None,
        "population_inference": "not_established",
        "causal_treatment_effect": "not_tested",
    }


def freeze_structured_repair_screen(
    store: Any,
    repo: str,
    *,
    forge_artifact: Mapping[str, Any],
    private_bundle: Mapping[str, Any],
    adapter: Any,
    prior_result_receipt_hash: str | None = None,
    governed_prerequisite: Mapping[str, Any] | None = None,
    repeat_of_result_receipt_hash: str | None = None,
) -> dict[str, Any]:
    public = forge_artifact.get("public_corpus") or {}
    alignment_binding: dict[str, Any] | None = None
    if forge_artifact.get("state") == "CONTRACT_ALIGNED_REPAIR_FORGE_READY":
        alignment_audit = verify_contract_aligned_repair_forge_result(forge_artifact)
        if alignment_audit["valid"] is not True:
            raise ValueError("valid contract-aligned repair forge is required")
        aligned_corpus_hash = str(public.get("corpus_hash") or "")
        public, private_bundle = executable_bundle_from_contract_aligned(
            public,
            private_bundle,
        )
        alignment_binding = {
            "alignment_result_hash": forge_artifact["result_hash"],
            "aligned_corpus_hash": aligned_corpus_hash,
            "executable_corpus_hash": public["corpus_hash"],
            "all_private_assertions_publicly_mapped": True,
            "all_public_requirements_covered": True,
            "semantic_entailment_established": False,
        }
    elif (
        forge_artifact.get("state") != "EXECUTABLE_REPAIR_FORGE_READY"
        or verify_executable_repair_bundle(public, private_bundle).get("valid") is not True
    ):
        raise ValueError("valid external-private executable forge is required")
    identity = _identity(adapter)
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if (
        not all(identity.values())
        or verify_adapter_provenance(store, repo, provenance).get("valid") is not True
        or provenance.get("evidence_class") != EVIDENCE_LIVE
    ):
        raise ValueError("host-registered live adapter provenance is required")
    cases = list(public.get("cases") or ())
    _assert_evaluators_unchallenged(store, repo, cases)
    if len(cases) != PLANNED_CALLS:
        raise ValueError("structured screen requires exactly four cases")
    if len({case.get("case_id") for case in cases}) != PLANNED_CALLS:
        raise ValueError("structured screen requires unique case identities")
    prior_binding: dict[str, Any] | None = None
    if prior_result_receipt_hash:
        prior_audit = verify_structured_repair_screen(
            store, repo, result_receipt_hash=prior_result_receipt_hash
        )
        prior = store.symbiotic_receipt(prior_result_receipt_hash, repo=repo) or {}
        if (
            prior_audit.get("valid") is not True
            or (prior.get("screen") or {}).get("state") != "screening_ceiling"
            or prior.get("model_identity") != identity
            or prior.get("evidence_class") != EVIDENCE_LIVE
        ):
            raise ValueError("canonical same-model screening ceiling is required")
        prior_binding = {
            "prior_result_receipt_hash": prior_result_receipt_hash,
            "prior_screen_state": "screening_ceiling",
            "prior_success_count": int((prior.get("screen") or {}).get("success_count") or 0),
            "difficulty_transition": "move_harder",
        }
    response_contract = {
        "schema_version": INTENT_SCHEMA,
        "format": "one JSON object only; no markdown fences",
        "exact_top_level_keys": ["schema_version", "summary", "edits"],
        "edit_keys": ["path", "old", "new"],
        "allowed_paths": ["module.py"],
        "rule": "old must be an exact unique source substring; express the smallest complete repair",
    }
    material = {
        "schema_version": "cortex-structured-repair-preregistration/1.0",
        "version": __version__,
        "kind": "structured_repair_preregistration",
        "forge_result_hash": forge_artifact["result_hash"],
        "corpus_hash": public["corpus_hash"],
        "private_bundle_hash": private_bundle["private_bundle_hash"],
        "cases": cases,
        "planned_calls": 4,
        "context_treatment": "task_only_control",
        "tools": [],
        "response_contract": response_contract,
        "model_identity": identity,
        "adapter_provenance": provenance,
        "status": "frozen_before_execution",
        "private_specs_origin": "outside_repository",
        "development_only": True,
        "prior_screen_binding": prior_binding,
        "contract_alignment_binding": alignment_binding,
        "governed_prerequisite": dict(governed_prerequisite) if governed_prerequisite else None,
        "semantic_transfer_established": False,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    if repeat_of_result_receipt_hash:
        material["schema_version"] = "cortex-structured-repair-preregistration/1.1"
        material["repeatability_binding"] = {
            "prior_result_receipt_hash": repeat_of_result_receipt_hash,
            "policy": dict(REPEAT_POLICY),
        }
        errors = _repeat_binding_errors(store, repo, material)
        if errors:
            raise ValueError("repeatability prerequisite invalid: " + ",".join(errors))
    session = open_symbiotic_session(
        store, repo, task="freeze external-private structured repair screen", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"structured_repair_prereg_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def execute_structured_repair_screen(
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
        raise ValueError("canonical structured preregistration required")
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    if (
        prereg.get("kind") != "structured_repair_preregistration"
        or _identity(adapter) != prereg.get("model_identity")
        or resolve_adapter_provenance(store, repo, adapter) != prereg.get("adapter_provenance")
    ):
        raise ValueError("structured runtime binding invalid")
    binding_errors = _private_binding_errors(prereg, private_bundle)
    binding_errors.extend(_repeat_binding_errors(store, repo, prereg))
    if binding_errors:
        raise ValueError("structured private evaluator binding invalid: " + ",".join(binding_errors))
    _assert_evaluators_unchallenged(store, repo, prereg["cases"])
    if grant.allowed_tools or grant.max_tool_calls != 0 or grant.max_total_tool_seconds != 0:
        raise ValueError("structured screen requires a zero-tool grant")
    execution_claim = None
    if prereg.get("repeatability_binding") is not None:
        # Store's unique (repo, session, turn, kind) constraint spends this run
        # exactly once, including parallel launches. A partial run stays held;
        # it cannot silently retry paid calls under the same preregistration.
        execution_claim = store.append_symbiotic_receipt(repo, {
            "kind": "structured_repair_execution_claim",
            "session_id": prereg["session_id"], "turn_id": 1,
            "body_epoch_id": prereg["body_epoch_id"],
            "event_id": "structured_repeat_claim_" + uuid.uuid4().hex,
            "preregistration_receipt_hash": prereg_hash,
            "host_mutate_authorized": False, "execution_authorized": False,
            "memory_admission_authorized": False, "policy_effect": False,
        })
    private_cases = {str(case["case_id"]): case for case in private_bundle["cases"]}
    runtime = NativeAgentRuntime(store, repo, tools=tools, max_iterations=1)
    sealed = []
    for case in prereg["cases"]:
        task = _case_task(case, prereg["response_contract"])
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
            (compile_root / "module.py").write_text(
                str(case["files"]["module.py"]), encoding="utf-8"
            )
            try:
                compilation = compile_edit_intent(
                    compile_root, output, allowed_targets=["module.py"]
                )
                candidate_text = compilation["proposal"]["patch"]
            except (OSError, ValueError) as exc:
                compiler_error = type(exc).__name__ + ":" + str(exc)[:500]
                candidate_text = output
        with tempfile.TemporaryDirectory(prefix="cortex-alpha34-eval-") as parent:
            evaluation = evaluate_executable_patch(
                case, private_cases[str(case["case_id"])], candidate_text, Path(parent) / "repo"
            )
        material = {
            "schema_version": "cortex-structured-repair-case/1.0",
            "version": __version__,
            "kind": "structured_repair_case",
            "preregistration_receipt_hash": prereg_hash,
            "case_id": case["case_id"],
            "case_hash": _sha(case),
            "trajectory_receipt_hash": trajectory_hash,
            "public_output_hash": hashlib.sha256(output.encode()).hexdigest(),
            "compilation_hash": compilation.get("compilation_hash") if compilation else None,
            "proposal_hash": compilation.get("proposal_hash") if compilation else None,
            "compiler_error": compiler_error,
            "evaluation": evaluation,
            "task_success": evaluation["candidate_pass"],
            "evidence_class": EVIDENCE_LIVE,
            "caller_success_authoritative": False,
            "advisory_only": True,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        }
        session = open_symbiotic_session(
            store, repo, task=f"seal structured repair {case['case_id']}", persist=True
        )
        sealed.append(
            store.append_symbiotic_receipt(
                repo,
                {
                    **material,
                    "session_id": session["session_id"],
                    "turn_id": 0,
                    "event_id": f"structured_repair_case_{_sha(material)[:24]}",
                    "body_epoch_id": session["body_epoch_id"],
                },
            )
        )
    screen = _screen_for_prereg(prereg, sum(case["task_success"] is True for case in sealed))
    material = {
        "schema_version": "cortex-structured-repair-result/1.0",
        "version": __version__,
        "kind": "structured_repair_result",
        "preregistration_receipt_hash": prereg_hash,
        "case_receipt_hashes": [case["receipt_hash"] for case in sealed],
        "model_identity": prereg["model_identity"],
        "evidence_class": EVIDENCE_LIVE,
        "screen": screen,
        "calls_executed": len(sealed),
        "baseline_calibrated": screen["state"] == "structured_baseline_calibrated",
        "semantic_transfer_established": False,
        "general_improvement_established": False,
        "next_action": screen["recommended_action"],
        "status": "STRUCTURED_REPAIR_SCREEN_RECONSTRUCTED",
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    if execution_claim is not None:
        material["execution_claim_receipt_hash"] = execution_claim["receipt_hash"]
        material["repeatability"] = _repeat_comparison(store, repo, prereg, sealed)
    session = open_symbiotic_session(
        store, repo, task="seal structured repair result", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"structured_repair_result_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def _verify_structured_repair_screen(
    store: Any, repo: str, *, result_receipt_hash: str
) -> dict[str, Any]:
    errors = []
    if store.verify_symbiotic_receipt(repo, result_receipt_hash).get("valid") is not True:
        return {"valid": False, "errors": ["result_receipt_invalid"]}
    result = store.symbiotic_receipt(result_receipt_hash, repo=repo) or {}
    prereg_hash = str(result.get("preregistration_receipt_hash") or "")
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    if (
        store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True
        or prereg.get("kind") != "structured_repair_preregistration"
    ):
        errors.append("preregistration_invalid")
    expected_cases = prereg.get("cases") or []
    errors.extend(_repeat_binding_errors(store, repo, prereg))
    if prereg.get("repeatability_binding") is None and (
        "repeatability" in result or "execution_claim_receipt_hash" in result
    ):
        errors.append("unexpected_repeatability_fields")
    case_hashes = result.get("case_receipt_hashes") or []
    if (
        not isinstance(expected_cases, list)
        or len(expected_cases) != PLANNED_CALLS
        or len({case["case_id"] for case in expected_cases}) != PLANNED_CALLS
        or not isinstance(case_hashes, list)
        or len(case_hashes) != PLANNED_CALLS
        or len(set(case_hashes)) != PLANNED_CALLS
        or type(prereg.get("planned_calls")) is not int
        or prereg.get("planned_calls") != PLANNED_CALLS
    ):
        return {"valid": False, "errors": errors + ["frozen_panel_invalid"]}
    if (
        result.get("kind") != "structured_repair_result"
        or result.get("schema_version") != "cortex-structured-repair-result/1.0"
        or result.get("status") != "STRUCTURED_REPAIR_SCREEN_RECONSTRUCTED"
        or result.get("model_identity") != prereg.get("model_identity")
        or result.get("evidence_class") != EVIDENCE_LIVE
        or type(result.get("calls_executed")) is not int
        or result.get("calls_executed") != PLANNED_CALLS
    ):
        errors.append("result_contract_invalid")
    if prereg.get("context_treatment") != "task_only_control" or prereg.get("tools") != []:
        errors.append("preregistration_treatment_invalid")
    provenance = prereg.get("adapter_provenance") or {}
    if provenance.get("evidence_class") != EVIDENCE_LIVE or verify_adapter_provenance(store, repo, provenance).get("valid") is not True:
        errors.append("preregistration_provenance_invalid")
    authority_fields = ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect")
    for field in authority_fields:
        if prereg.get(field) is not False:
            errors.append(f"preregistration_authority_invalid:{field}")
    observed = []
    canonical_cases = []
    successes = 0
    for expected_case, receipt_hash in zip(expected_cases, case_hashes):
        if store.verify_symbiotic_receipt(repo, str(receipt_hash)).get("valid") is not True:
            errors.append(f"case_invalid:{receipt_hash}")
            continue
        case = store.symbiotic_receipt(str(receipt_hash), repo=repo) or {}
        canonical_cases.append(case)
        observed.append(str(case.get("case_id") or ""))
        if (
            case.get("kind") != "structured_repair_case"
            or case.get("schema_version") != "cortex-structured-repair-case/1.0"
            or case.get("preregistration_receipt_hash") != prereg_hash
            or case.get("case_hash") != _sha(expected_case)
            or case.get("evidence_class") != EVIDENCE_LIVE
            or case.get("caller_success_authoritative") is not False
            or any(case.get(field) is not False for field in authority_fields)
        ):
            errors.append(f"case_contract_invalid:{case.get('case_id')}")
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        if (
            verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True
            or case.get("public_output_hash")
            != hashlib.sha256(str(trajectory.get("final_answer") or "").encode()).hexdigest()
        ):
            errors.append(f"trajectory_binding_invalid:{case.get('case_id')}")
        expected_task = _case_task(expected_case, prereg["response_contract"])
        requests = trajectory.get("requests") or []
        grant = trajectory.get("capability_grant") or {}
        if (
            trajectory.get("task") != expected_task
            or trajectory.get("task_hash") != _sha(expected_task)
            or trajectory.get("provider_identity") != prereg.get("model_identity")
            or trajectory.get("context_treatment") != "task_only_control"
            or len(requests) != 1
            or len(trajectory.get("responses") or []) != 1
            or trajectory.get("tool_results") != []
            or grant.get("allowed_tools") != []
            or grant.get("max_tool_calls") != 0
            or grant.get("max_total_tool_seconds") != 0
        ):
            errors.append(f"trajectory_experiment_binding_invalid:{case.get('case_id')}")
        for request in requests:
            if request.get("task") != expected_task or request.get("provider_identity") != prereg.get("model_identity") or request.get("tools") != []:
                errors.append(f"request_experiment_binding_invalid:{case.get('case_id')}")
        evaluation = case.get("evaluation") or {}
        if evaluation.get("evaluation_hash") != _sha(
            {key: value for key, value in evaluation.items() if key != "evaluation_hash"}
        ) or case.get("task_success") is not evaluation.get("candidate_pass"):
            errors.append(f"evaluation_binding_invalid:{case.get('case_id')}")
        baseline, candidate = evaluation.get("baseline") or {}, evaluation.get("candidate") or {}
        baseline_pass = baseline.get("passed")
        candidate_pass = candidate.get("status") == "verified"
        classification = (
            "REPAIR_MEASURED" if baseline_pass is False and candidate_pass
            else "VERIFIED_MAINTENANCE" if baseline_pass is True and candidate_pass
            else "REGRESSION_DETECTED" if baseline_pass is True else "IMPROVEMENT_HELD"
        )
        if (
            evaluation.get("case_id") != expected_case["case_id"]
            or evaluation.get("evaluator_commitment") != expected_case["private_evaluator_commitment"]
            or type(case.get("task_success")) is not bool
            or type(baseline_pass) is not bool
            or evaluation.get("baseline_pass") is not baseline_pass
            or baseline_pass is not (baseline.get("returncode") == 0)
            or evaluation.get("candidate_pass") is not candidate_pass
            or evaluation.get("classification") != classification
            or evaluation.get("bounded_repair_established") is not (classification == "REPAIR_MEASURED")
            or any(evaluation.get(field) is not False for field in authority_fields)
        ):
            errors.append(f"evaluation_contract_invalid:{case.get('case_id')}")
        if candidate_pass and (
            len(candidate.get("steps") or []) != 1
            or any(step.get("passed") is not True or step.get("returncode") != 0 for step in candidate["steps"])
            or candidate.get("proposal_hash") != evaluation.get("proposal_hash")
            or candidate.get("source_head") != evaluation.get("source_head")
        ):
            errors.append(f"candidate_observation_invalid:{case.get('case_id')}")
        successes += case.get("task_success") is True
    if observed != [str(case["case_id"]) for case in prereg.get("cases") or ()] or result.get(
        "screen"
    ) != _screen_for_prereg(prereg, successes):
        errors.append("screen_reconstruction_invalid")
    reconstructed = _screen_for_prereg(prereg, successes)
    if result.get("baseline_calibrated") is not (reconstructed["state"] == "structured_baseline_calibrated") or result.get("next_action") != reconstructed["recommended_action"]:
        errors.append("result_disposition_invalid")
    if prereg.get("repeatability_binding") is not None and not errors:
        claim_hash = str(result.get("execution_claim_receipt_hash") or "")
        claim = store.symbiotic_receipt(claim_hash, repo=repo) or {}
        if (
            store.verify_symbiotic_receipt(repo, claim_hash).get("valid") is not True
            or claim.get("kind") != "structured_repair_execution_claim"
            or claim.get("session_id") != prereg.get("session_id")
            or claim.get("turn_id") != 1
            or claim.get("preregistration_receipt_hash") != prereg_hash
            or any(claim.get(field) is not False for field in authority_fields)
        ):
            errors.append("repeatability_execution_claim_invalid")
        prior = store.symbiotic_receipt(prereg["repeatability_binding"]["prior_result_receipt_hash"], repo=repo)
        old_trajectories = {store.symbiotic_receipt(value, repo=repo)["trajectory_receipt_hash"] for value in prior["case_receipt_hashes"]}
        new_trajectories = {case["trajectory_receipt_hash"] for case in canonical_cases}
        if len(new_trajectories) != PLANNED_CALLS or new_trajectories & old_trajectories:
            errors.append("repeatability_trajectory_replay")
        for case in canonical_cases:
            trajectory = store.symbiotic_receipt(case["trajectory_receipt_hash"], repo=repo)
            if (
                trajectory.get("created_at", 0) < claim.get("created_at", float("inf"))
                or any(request.get("requested_at", 0) < claim.get("created_at", float("inf")) for request in trajectory["requests"])
            ):
                errors.append("repeatability_chronology_invalid")
        if result.get("repeatability") != _repeat_comparison(store, repo, prereg, canonical_cases):
            errors.append("repeatability_comparison_invalid")
    for field in (
        "semantic_transfer_established",
        "general_improvement_established",
        "host_mutate_authorized",
        "execution_authorized",
        "memory_admission_authorized",
        "policy_effect",
    ):
        if result.get(field) is not False:
            errors.append(f"authority_or_claim_invalid:{field}")
    return {
        "valid": not errors,
        "errors": errors,
        "screen": reconstructed,
        "result_receipt_hash": result_receipt_hash,
        "preregistration_receipt_hash": prereg_hash,
        "verification_scope": "receipt_integrity_and_experiment_bindings",
        "external_execution_replayed": False,
    }


def verify_structured_repair_screen(store: Any, repo: str, *, result_receipt_hash: str) -> dict[str, Any]:
    """Resolve the experimental equalities as well as the receipt hashes.

    This observes persisted execution evidence; it does not rerun candidate code
    or provide independent OS/provider attestation.
    """
    try:
        return _verify_structured_repair_screen(store, repo, result_receipt_hash=result_receipt_hash)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return {"valid": False, "errors": ["malformed_structured_evidence"]}


__all__ = [
    "freeze_structured_repair_screen",
    "execute_structured_repair_screen",
    "verify_structured_repair_screen",
]
