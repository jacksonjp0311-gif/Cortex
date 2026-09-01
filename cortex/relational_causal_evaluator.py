"""Deterministic relational causal proof and evidence-sufficiency policy.

Public prose is retained as rationale but never scored.  The model must expose
its causal claim through typed relations; Cortex verifies those relations and
their independently frozen evidence proof sets without provider-specific logic.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from . import __version__
from .native_agent import verify_native_agent_trajectory
from .semantic_causal_evaluator import verify_live_semantic_screen_v2
from .symbiosis import open_symbiotic_session

CONTRACT_SCHEMA = "cortex-relational-causal-contract/3.0"
PRIVATE_SCHEMA = "cortex-relational-causal-key/3.0"
PUBLIC_SCHEMA = "cortex-relational-causal-manifest/3.0"
EVALUATION_SCHEMA = "cortex-relational-causal-evaluation/3.0"
EVALUATOR_ID = "cortex.relational-causal-proof.v3"
RELATION_KEYS = ("subject", "relation", "object")
RESPONSE_KEYS = (
    "cause",
    "repair",
    "causal_relations",
    "repair_relations",
    "evidence_ids",
    "uncertainty",
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _edge(subject: str, relation: str, object_: str) -> dict[str, str]:
    return {"subject": subject, "relation": relation, "object": object_}


def _edge_tuple(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return tuple(str(value.get(key) or "") for key in RELATION_KEYS)  # type: ignore[return-value]


def _level_four_contract(case_id: str) -> dict[str, Any]:
    cause = [
        _edge("committed_source", "has_generation", "generation_42"),
        _edge("snapshot_cache", "has_generation", "generation_41"),
        _edge("snapshot_cache", "older_than", "committed_source"),
        _edge("index_rebuild", "reads_from", "snapshot_cache"),
        _edge("stale_snapshot", "causes", "mislabeled_derived_index"),
    ]
    repair = [
        _edge("snapshot_cache", "must_match_generation", "committed_source"),
        _edge("snapshot_validation", "precedes", "index_rebuild"),
        _edge("generation_mismatch", "blocks", "index_seal"),
    ]
    material = {
        "schema_version": CONTRACT_SCHEMA,
        "case_id": case_id,
        "required_causal_relations": cause,
        "required_repair_relations": repair,
        "allowed_causal_relations": cause,
        "allowed_repair_relations": repair,
        "evidence_event_order": ["E1", "E2", "E3", "E4", "E5"],
        "minimal_evidence_proof_sets": [
            ["E1", "E2", "E3", "E4"],
            ["E2", "E3", "E4", "E5"],
        ],
        "corroborating_evidence_ids": ["E5"],
        "allowed_response_keys": list(RESPONSE_KEYS),
        "uncertainty_states": ["low", "medium", "high", "unknown"],
        "public_rationale_scored": False,
        "extra_relations_allowed": False,
        "caller_success_authoritative": False,
        "model_identity_used_in_scoring": False,
    }
    return {**material, "contract_hash": _sha(material)}


def build_relational_evaluator_bundle(
    corpus_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile a private level-four graph contract and answer-free manifest."""
    level_four = [
        row
        for row in corpus_manifest.get("cases") or ()
        if int(row.get("difficulty_level") or 0) == 4
    ]
    if len(level_four) != 4:
        raise ValueError("relational evaluator requires four level-four source cases")
    contracts = {
        str(row["case_id"]): _level_four_contract(str(row["case_id"]))
        for row in level_four
    }
    private_key = {
        "schema_version": PRIVATE_SCHEMA,
        "source_corpus_hash": str(corpus_manifest.get("corpus_hash") or ""),
        "contracts": contracts,
    }
    public_material = {
        "schema_version": PUBLIC_SCHEMA,
        "version": __version__,
        "evaluator_id": EVALUATOR_ID,
        "source_corpus_hash": str(corpus_manifest.get("corpus_hash") or ""),
        "source_private_key_commitment": str(
            corpus_manifest.get("private_key_commitment") or ""
        ),
        "case_ids": sorted(contracts),
        "relation_schema": list(RELATION_KEYS),
        "response_schema": list(RESPONSE_KEYS),
        "relation_ontology": sorted(
            {
                edge["relation"]
                for contract in contracts.values()
                for field in ("required_causal_relations", "required_repair_relations")
                for edge in contract[field]
            }
        ),
        "evidence_policy": (
            "ordered_submitted_evidence_must_contain_one_independently_frozen_"
            "minimal_proof_set; corroborating_evidence_may_be_retained"
        ),
        "private_key_commitment": _sha(private_key),
        "private_contracts_present": False,
        "public_rationale_scored": False,
        "model_identity_in_scoring": False,
        "development_only": True,
        "confirmatory_eligible": False,
    }
    manifest = {**public_material, "evaluator_hash": _sha(public_material)}
    return {"manifest": manifest, "private_key": private_key}


def verify_relational_evaluator_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    manifest = bundle.get("manifest") if isinstance(bundle, Mapping) else None
    private = bundle.get("private_key") if isinstance(bundle, Mapping) else None
    errors: list[str] = []
    if not isinstance(manifest, Mapping) or not isinstance(private, Mapping):
        return {"valid": False, "errors": ["bundle_shape_invalid"]}
    public_material = {key: value for key, value in manifest.items() if key != "evaluator_hash"}
    if manifest.get("schema_version") != PUBLIC_SCHEMA:
        errors.append("manifest_schema_invalid")
    if manifest.get("evaluator_hash") != _sha(public_material):
        errors.append("evaluator_hash_invalid")
    if private.get("schema_version") != PRIVATE_SCHEMA:
        errors.append("private_schema_invalid")
    if manifest.get("private_key_commitment") != _sha(private):
        errors.append("private_key_commitment_invalid")
    contracts = private.get("contracts") or {}
    if sorted(contracts) != list(manifest.get("case_ids") or ()):
        errors.append("case_binding_invalid")
    for case_id, contract in contracts.items():
        material = {key: value for key, value in contract.items() if key != "contract_hash"}
        if (
            contract.get("schema_version") != CONTRACT_SCHEMA
            or contract.get("case_id") != case_id
            or contract.get("contract_hash") != _sha(material)
        ):
            errors.append(f"contract_invalid:{case_id}")
        proof_sets = contract.get("minimal_evidence_proof_sets") or ()
        if not proof_sets or any(not proof for proof in proof_sets):
            errors.append(f"evidence_proof_sets_invalid:{case_id}")
    if manifest.get("private_contracts_present") is not False:
        errors.append("private_boundary_invalid")
    return {"valid": not errors, "errors": errors}


def evaluate_relational_causal_response(
    contract: Mapping[str, Any], public_text: str
) -> dict[str, Any]:
    """Verify typed causal relations and sufficient ordered evidence."""
    material = {key: value for key, value in contract.items() if key != "contract_hash"}
    if (
        contract.get("schema_version") != CONTRACT_SCHEMA
        or contract.get("contract_hash") != _sha(material)
    ):
        return {"state": "unknown", "success": None, "errors": ["contract_invalid"]}
    try:
        response = json.loads(str(public_text))
    except json.JSONDecodeError:
        response = None
    if not isinstance(response, Mapping):
        return {"state": "unknown", "success": None, "errors": ["response_json_object_required"]}
    errors: list[str] = []
    if set(response) != set(contract.get("allowed_response_keys") or ()):
        errors.append("response_keys_invalid")

    def relations(field: str) -> tuple[set[tuple[str, str, str]], bool]:
        value = response.get(field)
        if not isinstance(value, list) or any(
            not isinstance(item, Mapping) or set(item) != set(RELATION_KEYS)
            for item in value
        ):
            return set(), False
        return {_edge_tuple(item) for item in value}, True

    observed_cause, cause_shape = relations("causal_relations")
    observed_repair, repair_shape = relations("repair_relations")
    required_cause = {
        _edge_tuple(item) for item in contract.get("required_causal_relations") or ()
    }
    required_repair = {
        _edge_tuple(item) for item in contract.get("required_repair_relations") or ()
    }
    allowed_cause = {
        _edge_tuple(item) for item in contract.get("allowed_causal_relations") or ()
    }
    allowed_repair = {
        _edge_tuple(item) for item in contract.get("allowed_repair_relations") or ()
    }
    if not cause_shape or not repair_shape:
        errors.append("relation_shape_invalid")
    missing_cause = sorted(required_cause - observed_cause)
    missing_repair = sorted(required_repair - observed_repair)
    unsupported = sorted(
        (observed_cause - allowed_cause) | (observed_repair - allowed_repair)
    )
    if missing_cause:
        errors.append("required_causal_relations_missing")
    if missing_repair:
        errors.append("required_repair_relations_missing")
    if unsupported:
        errors.append("unsupported_relation_claim")

    evidence = response.get("evidence_ids")
    submitted = [str(item) for item in evidence] if isinstance(evidence, list) else []
    event_order = [str(item) for item in contract.get("evidence_event_order") or ()]
    ordered = submitted == [item for item in event_order if item in set(submitted)]
    known = set(submitted).issubset(set(event_order))
    proof_sets = [
        {str(item) for item in proof}
        for proof in contract.get("minimal_evidence_proof_sets") or ()
    ]
    satisfied = [index for index, proof in enumerate(proof_sets) if proof.issubset(set(submitted))]
    if not isinstance(evidence, list) or not ordered or not known or not satisfied:
        errors.append("causal_evidence_insufficient")
    if str(response.get("uncertainty") or "") not in set(
        contract.get("uncertainty_states") or ()
    ):
        errors.append("uncertainty_state_invalid")
    return {
        "schema_version": EVALUATION_SCHEMA,
        "state": "pass" if not errors else "fail",
        "success": not errors,
        "errors": errors,
        "missing_causal_relations": [list(item) for item in missing_cause],
        "missing_repair_relations": [list(item) for item in missing_repair],
        "unsupported_relations": [list(item) for item in unsupported],
        "satisfied_evidence_proof_set_indices": satisfied,
        "submitted_evidence_is_minimal": any(
            set(submitted) == proof for proof in proof_sets
        ),
        "public_rationale_scored": False,
        "contract_hash": contract.get("contract_hash"),
        "response_hash": _sha(response),
        "evaluator_id": EVALUATOR_ID,
        "independent": True,
        "caller_success_authoritative": False,
    }


def relational_evaluator_self_test(bundle: Mapping[str, Any]) -> dict[str, Any]:
    contract = next(iter(bundle["private_key"]["contracts"].values()))
    base = {
        "cause": "arbitrary public paraphrase",
        "repair": "arbitrary public repair rationale",
        "causal_relations": contract["required_causal_relations"],
        "repair_relations": contract["required_repair_relations"],
        "evidence_ids": ["E1", "E2", "E3", "E4"],
        "uncertainty": "low",
    }
    checks: list[dict[str, Any]] = []

    def check(name: str, response: Any, expected: bool | None, error: str | None = None) -> None:
        payload = response if isinstance(response, str) else json.dumps(response)
        verdict = evaluate_relational_causal_response(contract, payload)
        checks.append(
            {
                "id": name,
                "expected": expected,
                "observed": verdict.get("success"),
                "expected_error_present": error is None or error in verdict.get("errors", ()),
            }
        )

    check("reference_minimal_proof_a", base, True)
    paraphrase = dict(base, cause="completely different words", repair="different words again")
    check("prose_invariance", paraphrase, True)
    alternative = dict(base, evidence_ids=["E2", "E3", "E4", "E5"])
    check("alternative_minimal_proof_b", alternative, True)
    corroborated = dict(base, evidence_ids=["E1", "E2", "E3", "E4", "E5"])
    check("corroborating_superset", corroborated, True)
    insufficient = dict(base, evidence_ids=["E1", "E2", "E3"])
    check("insufficient_evidence", insufficient, False, "causal_evidence_insufficient")
    reversed_evidence = dict(base, evidence_ids=["E4", "E3", "E2", "E1"])
    check("reversed_evidence", reversed_evidence, False, "causal_evidence_insufficient")
    missing_cause = dict(base, causal_relations=base["causal_relations"][:-1])
    check("missing_causal_edge", missing_cause, False, "required_causal_relations_missing")
    wrong_direction = json.loads(json.dumps(base))
    wrong_direction["repair_relations"][1] = _edge("index_rebuild", "precedes", "snapshot_validation")
    check("wrong_temporal_direction", wrong_direction, False, "required_repair_relations_missing")
    unsupported = json.loads(json.dumps(base))
    unsupported["causal_relations"].append(_edge("timeout", "causes", "stale_snapshot"))
    check("unsupported_relation", unsupported, False, "unsupported_relation_claim")
    caller_score = dict(base, success=True)
    check("caller_success_field", caller_score, False, "response_keys_invalid")
    check("malformed_json_unknown", "not json", None, "response_json_object_required")
    passed = all(
        row["observed"] is row["expected"] and row["expected_error_present"]
        for row in checks
    )
    return {"passed": passed, "check_count": len(checks), "checks": checks}


def freeze_relational_evaluator_v3(
    store: Any,
    repo: str,
    *,
    instrument_audit_receipt_hash: str,
    v2_bundle: Mapping[str, Any],
    v3_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Commission v3 only from independently reconstructed alpha.25 evidence."""
    audit_hash = str(instrument_audit_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, audit_hash).get("valid") is not True:
        raise ValueError("canonical instrument audit is required")
    audit = store.symbiotic_receipt(audit_hash, repo=repo) or {}
    if (
        audit.get("kind") != "semantic_screen_instrument_audit"
        or audit.get("state") != "DIFFICULTY_INTERPOLATION_HELD"
        or audit.get("historical_scores_rewritten") is not False
        or int(audit.get("additional_model_calls", -1)) != 0
        or audit.get("difficulty_interpolation_ready") is not False
    ):
        raise ValueError("instrument audit does not open relational commissioning")
    result_hash = str(audit.get("result_receipt_hash") or "")
    result_audit = verify_live_semantic_screen_v2(
        store,
        repo,
        result_receipt_hash=result_hash,
        evaluator_bundle=v2_bundle,
    )
    if (
        result_audit.get("valid") is not True
        or result_audit.get("difficulty_levels") != [4]
        or (result_audit.get("screen") or {}).get("state") != "screening_floor"
    ):
        raise ValueError("source level-four result reconstruction failed")
    result = store.symbiotic_receipt(result_hash, repo=repo) or {}
    evidence_rejections = 0
    semantic_rejections = 0
    for case_hash in result.get("case_receipt_hashes") or ():
        case = store.symbiotic_receipt(str(case_hash), repo=repo) or {}
        if verify_native_agent_trajectory(
            store, repo, str(case.get("trajectory_receipt_hash") or "")
        ).get("valid") is not True:
            raise ValueError("source trajectory reconstruction failed")
        errors = set((case.get("evaluation") or {}).get("errors") or ())
        evidence_rejections += int("causal_evidence_binding_invalid" in errors)
        semantic_rejections += int(
            bool(
                errors
                & {
                    "required_cause_semantics_missing",
                    "required_repair_semantics_missing",
                }
            )
        )
    if (
        evidence_rejections != int(audit.get("evidence_binding_rejection_count", -1))
        or semantic_rejections != int(audit.get("semantic_clause_rejection_count", -1))
    ):
        raise ValueError("instrument rejection reconstruction failed")
    verification = verify_relational_evaluator_bundle(v3_bundle)
    if verification.get("valid") is not True:
        raise ValueError("relational evaluator bundle is invalid")
    self_test = relational_evaluator_self_test(v3_bundle)
    if self_test.get("passed") is not True:
        raise ValueError("relational evaluator self-test failed")
    material = {
        "schema_version": "cortex-relational-causal-preflight/3.0",
        "version": __version__,
        "kind": "relational_causal_evaluator_preflight",
        "source_instrument_audit_receipt_hash": audit_hash,
        "source_result_receipt_hash": result_hash,
        "source_result_audit": result_audit,
        "evaluator_manifest": v3_bundle["manifest"],
        "self_test": self_test,
        "historical_scores_rewritten": False,
        "historical_v2_receipts_immutable": True,
        "planned_live_calls": 0,
        "difficulty_interpolation_ready": True,
        "baseline_difficulty_established": False,
        "semantic_transfer_established": False,
        "state": "RELATIONAL_CAUSAL_EVALUATOR_V3_READY",
        "next_action": "forge_intermediate_relational_cases_zero_call",
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze relational causal evaluator v3", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"relational_causal_v3_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


__all__ = [
    "EVALUATOR_ID",
    "build_relational_evaluator_bundle",
    "evaluate_relational_causal_response",
    "freeze_relational_evaluator_v3",
    "relational_evaluator_self_test",
    "verify_relational_evaluator_bundle",
]
