"""Final prospective equivalence-aware relational screen for alpha.30."""

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
from .relational_equivalence import (
    EVALUATOR_ID,
    evaluate_equivalent_relational_response,
    verify_equivalence_evaluator_bundle,
)
from .symbiosis import open_symbiotic_session

FINAL_BAND = "bridge_mid"
PLANNED_CALLS = 4


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _adapter_identity(adapter: Any) -> dict[str, str]:
    return {
        key: str(getattr(adapter, key, "") or "")
        for key in ("provider_family", "model_id", "model_version", "adapter_id", "adapter_version")
    }


def _screen(outcomes: list[bool], unknown_count: int) -> dict[str, Any]:
    if unknown_count:
        return {
            "state": "screening_held_unknown",
            "recommended_action": "retire_synthetic_semantic_benchmark",
            "case_count": len(outcomes) + unknown_count,
            "known_outcome_count": len(outcomes),
            "unknown_count": unknown_count,
            "success_count": sum(outcomes),
            "success_rate": None,
            "development_only": True,
            "confirmatory_eligible": False,
        }
    return {**assess_sequential_level(outcomes), "unknown_count": 0}


def _disposition(screen: Mapping[str, Any]) -> dict[str, Any]:
    calibrated = screen.get("state") == "calibrated"
    return {
        "calibration_established": calibrated,
        "synthetic_semantic_benchmark_retired": not calibrated,
        "ruler_revision_permitted": False,
        "next_action": (
            "freeze_semantic_treatment_trial_under_new_authority"
            if calibrated
            else "forge_executable_code_tasks_with_frozen_external_tests"
        ),
    }


def freeze_final_relational_screen(
    store: Any,
    repo: str,
    *,
    equivalence_preflight_receipt_hash: str,
    corpus_bundle: Mapping[str, Any],
    evaluator_bundle: Mapping[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    """Freeze four unseen bridge-mid calls under the already frozen v4 ruler."""
    preflight_hash = str(equivalence_preflight_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, preflight_hash).get("valid") is not True:
        raise ValueError("canonical alpha.29 equivalence preflight is required")
    preflight = store.symbiotic_receipt(preflight_hash, repo=repo) or {}
    if (
        preflight.get("kind") != "relational_equivalence_preflight"
        or preflight.get("state") != "RELATIONAL_EQUIVALENCE_V4_READY"
        or preflight.get("ruler_building_closed") is not True
        or int(preflight.get("additional_model_calls", -1)) != 0
        or preflight.get("historical_scores_rewritten") is not False
    ):
        raise ValueError("alpha.29 preflight does not open the final screen")
    if verify_intermediate_relational_bundle(corpus_bundle).get("valid") is not True:
        raise ValueError("intermediate corpus bundle is invalid")
    if verify_equivalence_evaluator_bundle(evaluator_bundle).get("valid") is not True:
        raise ValueError("equivalence evaluator bundle is invalid")
    manifest = corpus_bundle["manifest"]
    evaluator_manifest = evaluator_bundle["manifest"]
    if (
        evaluator_manifest != preflight.get("evaluator_manifest")
        or evaluator_manifest.get("source_corpus_hash") != manifest.get("corpus_hash")
    ):
        raise ValueError("alpha.29 corpus/evaluator binding is invalid")

    source_result_hash = str(preflight.get("source_result_receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, source_result_hash).get("valid") is not True:
        raise ValueError("canonical alpha.28 source result is required")
    source_result = store.symbiotic_receipt(source_result_hash, repo=repo) or {}
    source_prereg_hash = str(source_result.get("preregistration_receipt_hash") or "")
    source_prereg = store.symbiotic_receipt(source_prereg_hash, repo=repo) or {}
    prior_case_ids = {str(case.get("case_id") or "") for case in source_prereg.get("cases") or ()}

    case_ids = list(manifest["band_case_ids"][FINAL_BAND])
    cases_by_id = {str(row["case_id"]): row for row in manifest["cases"]}
    cases = [cases_by_id[case_id] for case_id in case_ids]
    if len(cases) != PLANNED_CALLS or prior_case_ids.intersection(case_ids):
        raise ValueError("final screen cases must be exactly four and prospectively unseen")

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
        "schema_version": "cortex-relational-final-preregistration/1.0",
        "version": __version__,
        "kind": "relational_final_preregistration",
        "equivalence_preflight_receipt_hash": preflight_hash,
        "source_result_receipt_hash": source_result_hash,
        "corpus_hash": manifest["corpus_hash"],
        "private_key_commitment": manifest["private_key_commitment"],
        "evaluator_hash": evaluator_manifest["evaluator_hash"],
        "evaluator_id": EVALUATOR_ID,
        "relation_ontology": evaluator_manifest["relation_ontology"],
        "difficulty_band": FINAL_BAND,
        "cases": cases,
        "prior_screen_case_ids": sorted(prior_case_ids),
        "prospective_case_disjointness": True,
        "planned_calls": PLANNED_CALLS,
        "stop_window": {"minimum": 0.30, "maximum": 0.70},
        "context_treatment": "task_only_control",
        "tools": [],
        "model_identity": identity,
        "adapter_provenance": provenance,
        "status": "frozen_before_execution",
        "ruler_building_closed": True,
        "ruler_revision_permitted": False,
        "outside_window_disposition": "retire_synthetic_semantic_benchmark",
        "development_only": True,
        "confirmatory_eligible": False,
        "semantic_transfer_established": False,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze final relational screen", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"relational_final_prereg_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def execute_final_relational_screen(
    store: Any,
    repo: str,
    *,
    preregistration: Mapping[str, Any],
    corpus_bundle: Mapping[str, Any],
    evaluator_bundle: Mapping[str, Any],
    adapter: Any,
    tools: Any,
    grant: Any,
) -> dict[str, Any]:
    prereg_hash = str(preregistration.get("receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        raise ValueError("canonical final-screen preregistration is required")
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    if prereg.get("kind") != "relational_final_preregistration":
        raise ValueError("final-screen preregistration binding is invalid")
    if verify_intermediate_relational_bundle(corpus_bundle).get("valid") is not True:
        raise ValueError("intermediate corpus bundle is invalid")
    if verify_equivalence_evaluator_bundle(evaluator_bundle).get("valid") is not True:
        raise ValueError("equivalence evaluator bundle is invalid")
    manifest = corpus_bundle["manifest"]
    evaluator_manifest = evaluator_bundle["manifest"]
    contracts = evaluator_bundle["private_key"]["contracts"]
    if (
        prereg.get("corpus_hash") != manifest.get("corpus_hash")
        or prereg.get("private_key_commitment") != manifest.get("private_key_commitment")
        or prereg.get("evaluator_hash") != evaluator_manifest.get("evaluator_hash")
        or _adapter_identity(adapter) != prereg.get("model_identity")
        or resolve_adapter_provenance(store, repo, adapter) != prereg.get("adapter_provenance")
    ):
        raise ValueError("runtime binding changed after preregistration")

    runtime = NativeAgentRuntime(store, repo, tools=tools)
    sealed_cases: list[dict[str, Any]] = []
    for case in prereg.get("cases") or ():
        case_id = str(case.get("case_id") or "")
        contract = contracts.get(case_id)
        if not isinstance(contract, Mapping):
            raise ValueError(f"private equivalence contract missing for {case_id}")
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
            "relation_ontology": prereg["relation_ontology"],
            "uncertainty": ["low", "medium", "high", "unknown"],
            "rule": (
                "use only public entity identifiers; include every relation needed to "
                "represent the causal transition and safeguard; include an ordered "
                "sufficient evidence proof; grounded extra relations are retained"
            ),
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
        evaluation = evaluate_equivalent_relational_response(
            contract, str(trajectory.get("final_answer") or "")
        )
        material = {
            "schema_version": "cortex-relational-final-case/1.0",
            "version": __version__,
            "kind": "relational_final_case",
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
        session = open_symbiotic_session(store, repo, task=f"seal final case {case_id}", persist=True)
        sealed_cases.append(
            store.append_symbiotic_receipt(
                repo,
                {
                    **material,
                    "session_id": session["session_id"],
                    "turn_id": 0,
                    "event_id": f"relational_final_case_{_sha(material)[:24]}",
                    "body_epoch_id": session["body_epoch_id"],
                },
            )
        )

    outcomes = [case["task_success"] for case in sealed_cases if case["task_success"] is not None]
    unknown_count = sum(case["task_success"] is None for case in sealed_cases)
    screen = _screen([value is True for value in outcomes], unknown_count)
    disposition = _disposition(screen)
    material = {
        "schema_version": "cortex-relational-final-result/1.0",
        "version": __version__,
        "kind": "relational_final_result",
        "preregistration_receipt_hash": prereg_hash,
        "case_receipt_hashes": [case["receipt_hash"] for case in sealed_cases],
        "model_identity": prereg["model_identity"],
        "evidence_class": EVIDENCE_LIVE,
        "screen": screen,
        "calls_executed": len(sealed_cases),
        **disposition,
        "semantic_transfer_established": False,
        "status": "FINAL_RELATIONAL_SCREEN_RECONSTRUCTED",
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="seal final relational result", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"relational_final_result_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


def verify_final_relational_screen(
    store: Any,
    repo: str,
    *,
    result_receipt_hash: str,
    corpus_bundle: Mapping[str, Any],
    evaluator_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    result_hash = str(result_receipt_hash or "")
    if verify_intermediate_relational_bundle(corpus_bundle).get("valid") is not True:
        return {"valid": False, "errors": ["corpus_bundle_invalid"]}
    if verify_equivalence_evaluator_bundle(evaluator_bundle).get("valid") is not True:
        return {"valid": False, "errors": ["evaluator_bundle_invalid"]}
    if store.verify_symbiotic_receipt(repo, result_hash).get("valid") is not True:
        return {"valid": False, "errors": ["result_receipt_invalid"]}
    result = store.symbiotic_receipt(result_hash, repo=repo) or {}
    prereg_hash = str(result.get("preregistration_receipt_hash") or "")
    if store.verify_symbiotic_receipt(repo, prereg_hash).get("valid") is not True:
        return {"valid": False, "errors": ["preregistration_receipt_invalid"]}
    prereg = store.symbiotic_receipt(prereg_hash, repo=repo) or {}
    contracts = evaluator_bundle["private_key"]["contracts"]
    outcomes: list[bool] = []
    unknown_count = 0
    case_hashes = list(result.get("case_receipt_hashes") or ())
    expected_case_ids = [str(case["case_id"]) for case in prereg.get("cases") or ()]
    observed_case_ids: list[str] = []
    for receipt_hash in case_hashes:
        if store.verify_symbiotic_receipt(repo, str(receipt_hash)).get("valid") is not True:
            errors.append(f"case_receipt_invalid:{receipt_hash}")
            continue
        case = store.symbiotic_receipt(str(receipt_hash), repo=repo) or {}
        case_id = str(case.get("case_id") or "")
        observed_case_ids.append(case_id)
        contract = contracts.get(case_id)
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        if not isinstance(contract, Mapping) or verify_native_agent_trajectory(
            store, repo, trajectory_hash
        ).get("valid") is not True:
            errors.append(f"case_source_invalid:{case_id}")
            continue
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        rebuilt = evaluate_equivalent_relational_response(
            contract, str(trajectory.get("final_answer") or "")
        )
        expected_case = next(
            (item for item in prereg.get("cases") or () if item.get("case_id") == case_id),
            None,
        )
        if (
            case.get("kind") != "relational_final_case"
            or case.get("preregistration_receipt_hash") != prereg_hash
            or not isinstance(expected_case, Mapping)
            or case.get("case_hash") != _sha(expected_case)
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
    disposition = _disposition(rebuilt_screen)
    if result.get("screen") != rebuilt_screen:
        errors.append("screen_reconstruction_invalid")
    if any(result.get(key) != value for key, value in disposition.items()):
        errors.append("disposition_reconstruction_invalid")
    if (
        result.get("kind") != "relational_final_result"
        or prereg.get("kind") != "relational_final_preregistration"
        or prereg.get("difficulty_band") != FINAL_BAND
        or prereg.get("prospective_case_disjointness") is not True
        or prereg.get("ruler_building_closed") is not True
        or prereg.get("ruler_revision_permitted") is not False
        or result.get("model_identity") != prereg.get("model_identity")
        or expected_case_ids != observed_case_ids
        or len(case_hashes) != PLANNED_CALLS
        or result.get("calls_executed") != PLANNED_CALLS
        or result.get("status") != "FINAL_RELATIONAL_SCREEN_RECONSTRUCTED"
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
        **disposition,
        "model_identity": prereg.get("model_identity"),
        "adapter_provenance": prereg.get("adapter_provenance"),
        "corpus_hash": prereg.get("corpus_hash"),
        "evaluator_hash": prereg.get("evaluator_hash"),
    }


__all__ = [
    "execute_final_relational_screen",
    "freeze_final_relational_screen",
    "verify_final_relational_screen",
]
