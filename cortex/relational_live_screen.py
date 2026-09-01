"""Bounded live screen for the answer-sealed intermediate relational corpus."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from . import __version__
from .adapter_provenance import EVIDENCE_LIVE, resolve_adapter_provenance, verify_adapter_provenance
from .information_calibration import assess_sequential_level
from .intermediate_relational_forge import verify_intermediate_relational_bundle
from .native_agent import NativeAgentRuntime, verify_native_agent_trajectory
from .relational_causal_evaluator import (
    EVALUATOR_ID,
    evaluate_relational_causal_response,
    verify_relational_evaluator_bundle,
)
from .symbiosis import open_symbiotic_session


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _adapter_identity(adapter: Any) -> dict[str, str]:
    return {
        key: str(getattr(adapter, key, "") or "")
        for key in (
            "provider_family",
            "model_id",
            "model_version",
            "adapter_id",
            "adapter_version",
        )
    }


def freeze_bridge_low_screen(
    store: Any,
    repo: str,
    *,
    forge_preflight_receipt_hash: str,
    corpus_bundle: Mapping[str, Any],
    evaluator_bundle: Mapping[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Freeze exactly four bridge-low calls from canonical alpha.27 evidence."""
    forge_hash = str(forge_preflight_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, forge_hash).get("valid") is not True:
        raise ValueError("canonical alpha.27 forge preflight is required")
    forge = store.symbiotic_receipt(forge_hash, repo=repo) or {}
    if (
        forge.get("kind") != "intermediate_relational_forge_preflight"
        or forge.get("state") != "INTERMEDIATE_RELATIONAL_FORGE_READY"
        or int(forge.get("planned_live_calls", -1)) != 0
        or int(forge.get("maximum_future_calls_without_new_authority", -1)) != 0
    ):
        raise ValueError("alpha.27 forge does not satisfy the screen boundary")
    if verify_intermediate_relational_bundle(corpus_bundle).get("valid") is not True:
        raise ValueError("intermediate corpus bundle is invalid")
    if verify_relational_evaluator_bundle(evaluator_bundle).get("valid") is not True:
        raise ValueError("relational evaluator bundle is invalid")
    manifest = corpus_bundle["manifest"]
    evaluator_manifest = evaluator_bundle["manifest"]
    if (
        forge.get("corpus_manifest") != manifest
        or forge.get("source_evaluator_hash") != evaluator_manifest.get("evaluator_hash")
    ):
        raise ValueError("forge/corpus/evaluator binding is invalid")
    case_ids = list(manifest["band_case_ids"]["bridge_low"])
    cases_by_id = {str(row["case_id"]): row for row in manifest["cases"]}
    cases = [cases_by_id[case_id] for case_id in case_ids]
    if len(cases) != 4:
        raise ValueError("bridge-low screen requires exactly four cases")
    identity = _adapter_identity(adapter)
    if not all(identity.values()):
        raise ValueError("complete adapter identity is required")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if (
        verify_adapter_provenance(store, repo, provenance).get("valid") is not True
        or provenance.get("evidence_class") != EVIDENCE_LIVE
    ):
        raise ValueError("live host-registered adapter provenance is required")
    material = {
        "schema_version": "cortex-relational-live-preregistration/1.0",
        "version": __version__,
        "kind": "relational_live_preregistration",
        "forge_preflight_receipt_hash": forge_hash,
        "corpus_hash": manifest["corpus_hash"],
        "private_key_commitment": manifest["private_key_commitment"],
        "evaluator_hash": evaluator_manifest["evaluator_hash"],
        "evaluator_id": EVALUATOR_ID,
        "relation_ontology": evaluator_manifest["relation_ontology"],
        "difficulty_band": "bridge_low",
        "cases": cases,
        "planned_calls": 4,
        "stop_window": {"minimum": 0.30, "maximum": 0.70},
        "context_treatment": "task_only_control",
        "tools": [],
        "model_identity": identity,
        "adapter_provenance": provenance,
        "status": "frozen_before_execution",
        "development_only": True,
        "confirmatory_eligible": False,
        "semantic_transfer_established": False,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze bridge-low relational screen", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"relational_live_prereg_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def _screen(outcomes: list[bool], unknown_count: int) -> dict[str, Any]:
    if unknown_count:
        return {
            "state": "screening_held_unknown",
            "recommended_action": "repair_response_contract_or_transport",
            "case_count": len(outcomes) + unknown_count,
            "known_outcome_count": len(outcomes),
            "unknown_count": unknown_count,
            "success_count": sum(outcomes),
            "success_rate": None,
            "development_only": True,
            "confirmatory_eligible": False,
        }
    return {**assess_sequential_level(outcomes), "unknown_count": 0}


def execute_bridge_low_screen(
    store: Any,
    repo: str,
    *,
    preregistration: Mapping[str, Any],
    corpus_bundle: Mapping[str, Any],
    adapter: Any,
    tools: Any,
    grant: Any,
) -> dict[str, Any]:
    prereg_hash = str(preregistration.get("receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        raise ValueError("canonical relational preregistration is required")
    canonical_prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    if canonical_prereg.get("kind") != "relational_live_preregistration":
        raise ValueError("relational preregistration binding is invalid")
    # The caller supplies only the identity to resolve. All execution fields
    # come from the canonical persisted receipt, never the caller-held mapping.
    preregistration = canonical_prereg
    if verify_intermediate_relational_bundle(corpus_bundle).get("valid") is not True:
        raise ValueError("intermediate corpus bundle is invalid")
    manifest = corpus_bundle["manifest"]
    contracts = corpus_bundle["private_key"]["contracts"]
    if (
        preregistration.get("corpus_hash") != manifest.get("corpus_hash")
        or preregistration.get("private_key_commitment") != manifest.get("private_key_commitment")
        or _adapter_identity(adapter) != preregistration.get("model_identity")
        or resolve_adapter_provenance(store, repo, adapter) != preregistration.get("adapter_provenance")
    ):
        raise ValueError("runtime binding changed after preregistration")
    runtime = NativeAgentRuntime(store, repo, tools=tools)
    sealed_cases: list[dict[str, Any]] = []
    for case in preregistration.get("cases") or ():
        case_id = str(case.get("case_id") or "")
        contract = contracts.get(case_id)
        if not isinstance(contract, Mapping):
            raise ValueError(f"private relational contract missing for {case_id}")
        response_contract = {
            "format": "one JSON object only; no markdown fences",
            "exact_keys": [
                "cause",
                "repair",
                "causal_relations",
                "repair_relations",
                "evidence_ids",
                "uncertainty",
            ],
            "relation_object_keys": ["subject", "relation", "object"],
            "relation_ontology": preregistration["relation_ontology"],
            "uncertainty": ["low", "medium", "high", "unknown"],
            "rule": "use only public entity identifiers; include an ordered sufficient evidence proof",
        }
        task = (
            f"{case['instruction']}\n\nEVENT_RECORD\n"
            + "\n".join(str(item) for item in case.get("events") or ())
            + "\n\nPUBLIC_ENTITIES\n"
            + _canonical(case["entities"])
            + "\n\nRESPONSE_CONTRACT\n"
            + _canonical(response_contract)
        )
        run = runtime.run(task, adapter=adapter, grant=grant, context_treatment="task_only_control")
        trajectory_hash = str(run["trajectory_receipt_hash"])
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            raise ValueError(f"native trajectory invalid for {case_id}")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        evaluation = evaluate_relational_causal_response(contract, str(trajectory.get("final_answer") or ""))
        material = {
            "schema_version": "cortex-relational-live-case/1.0",
            "version": __version__,
            "kind": "relational_live_case",
            "preregistration_receipt_hash": prereg_hash,
            "case_id": case_id,
            "case_hash": _sha(case),
            "contract_hash": contract["contract_hash"],
            "trajectory_receipt_hash": trajectory_hash,
            "evaluation": evaluation,
            "task_success": evaluation.get("success"),
            "evidence_class": EVIDENCE_LIVE,
            "caller_success_authoritative": False,
            "advisory_only": True,
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        }
        session = open_symbiotic_session(store, repo, task=f"seal relational case {case_id}", persist=True)
        sealed_cases.append(
            store.append_symbiotic_receipt(
                repo,
                {
                    **material,
                    "session_id": session["session_id"],
                    "turn_id": 0,
                    "event_id": f"relational_live_case_{_sha(material)[:24]}",
                    "body_epoch_id": session["body_epoch_id"],
                },
            )
        )
    outcomes = [case["task_success"] for case in sealed_cases if case["task_success"] is not None]
    unknown_count = sum(case["task_success"] is None for case in sealed_cases)
    screen = _screen([value is True for value in outcomes], unknown_count)
    material = {
        "schema_version": "cortex-relational-live-result/1.0",
        "version": __version__,
        "kind": "relational_live_result",
        "preregistration_receipt_hash": prereg_hash,
        "case_receipt_hashes": [case["receipt_hash"] for case in sealed_cases],
        "model_identity": preregistration["model_identity"],
        "evidence_class": EVIDENCE_LIVE,
        "screen": screen,
        "calls_executed": len(sealed_cases),
        "calibration_established": screen.get("state") == "calibrated",
        "semantic_transfer_established": False,
        "status": "RELATIONAL_LIVE_SCREEN_RECONSTRUCTED",
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="seal bridge-low relational result", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"relational_live_result_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def verify_bridge_low_screen(
    store: Any,
    repo: str,
    *,
    result_receipt_hash: str,
    corpus_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    result_hash = str(result_receipt_hash or "")
    if verify_intermediate_relational_bundle(corpus_bundle).get("valid") is not True:
        return {"valid": False, "errors": ["corpus_bundle_invalid"]}
    if store.verify_symbiotic_receipt(repo, result_hash).get("valid") is not True:
        return {"valid": False, "errors": ["result_receipt_invalid"]}
    result = store.symbiotic_receipt(result_hash, repo=repo) or {}
    prereg_hash = str(result.get("preregistration_receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        return {"valid": False, "errors": ["preregistration_receipt_invalid"]}
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    contracts = corpus_bundle["private_key"]["contracts"]
    outcomes: list[bool] = []
    unknown_count = 0
    case_hashes = list(result.get("case_receipt_hashes") or ())
    for receipt_hash in case_hashes:
        if store.verify_symbiotic_receipt(repo, str(receipt_hash)).get("valid") is not True:
            errors.append(f"case_receipt_invalid:{receipt_hash}")
            continue
        case = store.symbiotic_receipt(str(receipt_hash), repo=repo) or {}
        case_id = str(case.get("case_id") or "")
        contract = contracts.get(case_id)
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        if not isinstance(contract, Mapping) or verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            errors.append(f"case_source_invalid:{case_id}")
            continue
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        rebuilt = evaluate_relational_causal_response(contract, str(trajectory.get("final_answer") or ""))
        if (
            case.get("kind") != "relational_live_case"
            or case.get("preregistration_receipt_hash") != prereg_hash
            or case.get("contract_hash") != contract.get("contract_hash")
            or case.get("evaluation") != rebuilt
            or case.get("task_success") != rebuilt.get("success")
        ):
            errors.append(f"case_binding_invalid:{case_id}")
        if rebuilt.get("success") is None:
            unknown_count += 1
        else:
            outcomes.append(rebuilt.get("success") is True)
    rebuilt_screen = _screen(outcomes, unknown_count)
    if result.get("screen") != rebuilt_screen:
        errors.append("screen_reconstruction_invalid")
    if (
        result.get("kind") != "relational_live_result"
        or prereg.get("kind") != "relational_live_preregistration"
        or prereg.get("difficulty_band") != "bridge_low"
        or result.get("model_identity") != prereg.get("model_identity")
        or len(case_hashes) != 4
        or result.get("calls_executed") != 4
        or result.get("status") != "RELATIONAL_LIVE_SCREEN_RECONSTRUCTED"
        or result.get("semantic_transfer_established") is not False
    ):
        errors.append("result_binding_invalid")
    for field in (
        "host_mutate_authorized",
        "execution_authorized",
        "memory_admission_authorized",
        "policy_effect",
    ):
        if result.get(field) is not False or prereg.get(field) is not False:
            errors.append(f"authority_open:{field}")
    return {
        "valid": not errors,
        "errors": errors,
        "result_receipt_hash": result_hash,
        "preregistration_receipt_hash": prereg_hash,
        "screen": rebuilt_screen,
        "model_identity": prereg.get("model_identity"),
        "adapter_provenance": prereg.get("adapter_provenance"),
        "corpus_hash": prereg.get("corpus_hash"),
    }


__all__ = [
    "execute_bridge_low_screen",
    "freeze_bridge_low_screen",
    "verify_bridge_low_screen",
]
