"""Deterministic equivalence-aware relational proof policy for alpha.29."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from . import __version__
from .intermediate_relational_forge import verify_intermediate_relational_bundle
from .native_agent import verify_native_agent_trajectory
from .symbiosis import open_symbiotic_session

CONTRACT_SCHEMA = "cortex-relational-equivalence-contract/4.0"
PRIVATE_SCHEMA = "cortex-relational-equivalence-key/4.0"
PUBLIC_SCHEMA = "cortex-relational-equivalence-manifest/4.0"
EVALUATION_SCHEMA = "cortex-relational-equivalence-evaluation/4.0"
EVALUATOR_ID = "cortex.relational-equivalence-proof.v4"
EDGE_KEYS = ("subject", "relation", "object")
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
    return tuple(str(value.get(key) or "") for key in EDGE_KEYS)  # type: ignore[return-value]


def _alternatives(
    edge: Mapping[str, Any], *, source: str, snapshot: str, derived: str
) -> list[dict[str, str]]:
    alternatives = [dict(edge)]
    value = _edge_tuple(edge)
    if value == (snapshot, "older_than", source):
        alternatives.append(_edge("generation_41", "older_than", "generation_42"))
    if value == (snapshot, "must_match_generation", source):
        alternatives.append(_edge(derived, "must_match_generation", source))
    if value == ("snapshot_validation", "precedes", derived):
        alternatives.append(_edge("snapshot_validation", "precedes", "publication"))
    return alternatives


def build_equivalence_evaluator_bundle(
    corpus_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile proposition alternatives from a verified private v3 corpus."""
    if verify_intermediate_relational_bundle(corpus_bundle).get("valid") is not True:
        raise ValueError("verified intermediate corpus bundle is required")
    manifest = corpus_bundle["manifest"]
    private = corpus_bundle["private_key"]
    public_by_id = {str(row["case_id"]): row for row in manifest["cases"]}
    contracts: dict[str, Any] = {}
    ontology: set[str] = set()
    for case_id, source_contract in private["contracts"].items():
        public_case = public_by_id[case_id]
        source = str(public_case["entities"][0])
        snapshot = str(public_case["entities"][1])
        derived = str(public_case["entities"][2])
        causal = [
            _alternatives(edge, source=source, snapshot=snapshot, derived=derived)
            for edge in source_contract["required_causal_relations"]
        ]
        repair = [
            _alternatives(edge, source=source, snapshot=snapshot, derived=derived)
            for edge in source_contract["required_repair_relations"]
        ]
        for proposition in causal + repair:
            ontology.update(edge["relation"] for edge in proposition)
        for field in ("allowed_causal_relations", "allowed_repair_relations"):
            ontology.update(edge["relation"] for edge in source_contract[field])
        forbidden = [
            _edge(source, "older_than", snapshot),
            _edge("generation_42", "older_than", "generation_41"),
            _edge(derived, "precedes", "snapshot_validation"),
            _edge("publication", "precedes", "snapshot_validation"),
        ]
        event_ids = [
            match.group(1)
            for event in public_case["events"]
            if (match := re.match(r"^([A-Z]\d+):", str(event)))
        ]
        material = {
            "schema_version": CONTRACT_SCHEMA,
            "case_id": case_id,
            "required_causal_propositions": causal,
            "required_repair_propositions": repair,
            "forbidden_relations": forbidden,
            "allowed_entities": list(public_case["entities"]),
            "allowed_relation_ontology": [],
            "evidence_event_order": event_ids,
            "minimal_evidence_proof_sets": source_contract[
                "minimal_evidence_proof_sets"
            ],
            "allowed_response_keys": list(RESPONSE_KEYS),
            "uncertainty_states": ["low", "medium", "high", "unknown"],
            "additional_grounded_relations_allowed": True,
            "public_rationale_scored": False,
            "caller_success_authoritative": False,
            "model_identity_used_in_scoring": False,
        }
        contracts[case_id] = material
    relation_ontology = sorted(ontology)
    sealed_contracts: dict[str, Any] = {}
    for case_id, material in contracts.items():
        material["allowed_relation_ontology"] = relation_ontology
        sealed_contracts[case_id] = {**material, "contract_hash": _sha(material)}
    private_key = {
        "schema_version": PRIVATE_SCHEMA,
        "source_corpus_hash": manifest["corpus_hash"],
        "contracts": sealed_contracts,
    }
    public_material = {
        "schema_version": PUBLIC_SCHEMA,
        "version": __version__,
        "evaluator_id": EVALUATOR_ID,
        "source_corpus_hash": manifest["corpus_hash"],
        "source_private_key_commitment": manifest["private_key_commitment"],
        "case_ids": sorted(sealed_contracts),
        "relation_ontology": relation_ontology,
        "equivalence_policy": "host_frozen_finite_alternatives_per_required_proposition",
        "additional_relation_policy": "bounded_and_retained_but_non_satisfying",
        "private_key_commitment": _sha(private_key),
        "private_contracts_present": False,
        "public_rationale_scored": False,
        "model_identity_in_scoring": False,
        "development_only": True,
        "confirmatory_eligible": False,
    }
    return {
        "manifest": {**public_material, "evaluator_hash": _sha(public_material)},
        "private_key": private_key,
    }


def verify_equivalence_evaluator_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
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
        if any(
            not proposition
            for field in ("required_causal_propositions", "required_repair_propositions")
            for proposition in contract.get(field) or ()
        ):
            errors.append(f"empty_proposition:{case_id}")
    if manifest.get("private_contracts_present") is not False:
        errors.append("private_boundary_invalid")
    return {"valid": not errors, "errors": errors}


def evaluate_equivalent_relational_response(
    contract: Mapping[str, Any], public_text: str
) -> dict[str, Any]:
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
    if set(response) != set(contract["allowed_response_keys"]):
        errors.append("response_keys_invalid")

    def parse(field: str) -> tuple[set[tuple[str, str, str]], bool]:
        value = response.get(field)
        if not isinstance(value, list) or any(
            not isinstance(edge, Mapping) or set(edge) != set(EDGE_KEYS)
            for edge in value
        ):
            return set(), False
        return {_edge_tuple(edge) for edge in value}, True

    cause, cause_shape = parse("causal_relations")
    repair, repair_shape = parse("repair_relations")
    if not cause_shape or not repair_shape:
        errors.append("relation_shape_invalid")

    def missing(field: str, observed: set[tuple[str, str, str]]) -> list[int]:
        missing_indices = []
        for index, alternatives in enumerate(contract.get(field) or ()):
            if not ({_edge_tuple(edge) for edge in alternatives} & observed):
                missing_indices.append(index)
        return missing_indices

    missing_cause = missing("required_causal_propositions", cause)
    missing_repair = missing("required_repair_propositions", repair)
    if missing_cause:
        errors.append("required_causal_propositions_missing")
    if missing_repair:
        errors.append("required_repair_propositions_missing")
    all_edges = cause | repair
    forbidden = {_edge_tuple(edge) for edge in contract.get("forbidden_relations") or ()}
    if all_edges & forbidden:
        errors.append("contradictory_relation_claim")
    ontology = set(contract.get("allowed_relation_ontology") or ())
    entities = set(contract.get("allowed_entities") or ())
    ungrounded = sorted(
        edge
        for edge in all_edges
        if edge[1] not in ontology or edge[0] not in entities or edge[2] not in entities
    )
    if ungrounded:
        errors.append("ungrounded_relation_claim")
    satisfying = {
        _edge_tuple(edge)
        for field in ("required_causal_propositions", "required_repair_propositions")
        for proposition in contract.get(field) or ()
        for edge in proposition
    }
    additional = sorted(all_edges - satisfying)
    evidence = response.get("evidence_ids")
    submitted = [str(item) for item in evidence] if isinstance(evidence, list) else []
    order = list(contract.get("evidence_event_order") or ())
    ordered = submitted == [item for item in order if item in set(submitted)]
    known = set(submitted).issubset(set(order))
    proof_sets = [
        {str(item) for item in proof}
        for proof in contract.get("minimal_evidence_proof_sets") or ()
    ]
    satisfied = [index for index, proof in enumerate(proof_sets) if proof.issubset(set(submitted))]
    if not isinstance(evidence, list) or not ordered or not known or not satisfied:
        errors.append("causal_evidence_insufficient")
    if str(response.get("uncertainty") or "") not in set(contract["uncertainty_states"]):
        errors.append("uncertainty_state_invalid")
    return {
        "schema_version": EVALUATION_SCHEMA,
        "state": "pass" if not errors else "fail",
        "success": not errors,
        "errors": errors,
        "missing_causal_proposition_indices": missing_cause,
        "missing_repair_proposition_indices": missing_repair,
        "additional_grounded_relations": [list(edge) for edge in additional],
        "ungrounded_relations": [list(edge) for edge in ungrounded],
        "satisfied_evidence_proof_set_indices": satisfied,
        "submitted_evidence_is_minimal": any(set(submitted) == proof for proof in proof_sets),
        "public_rationale_scored": False,
        "evaluator_id": EVALUATOR_ID,
        "contract_hash": contract.get("contract_hash"),
        "response_hash": _sha(response),
        "independent": True,
        "caller_success_authoritative": False,
    }


def equivalence_evaluator_self_test(bundle: Mapping[str, Any]) -> dict[str, Any]:
    contract = next(iter(bundle["private_key"]["contracts"].values()))
    cause = [proposition[0] for proposition in contract["required_causal_propositions"]]
    repair = [proposition[0] for proposition in contract["required_repair_propositions"]]
    base = {
        "cause": "public words",
        "repair": "public words",
        "causal_relations": cause,
        "repair_relations": repair,
        "evidence_ids": ["E1", "E2", "E3", "E4"],
        "uncertainty": "low",
    }
    checks: list[tuple[str, bool | None, bool | None]] = []

    def run(name: str, payload: Any, expected: bool | None) -> None:
        text = payload if isinstance(payload, str) else json.dumps(payload)
        checks.append((name, evaluate_equivalent_relational_response(contract, text).get("success"), expected))

    run("exact", base, True)
    alternative = json.loads(json.dumps(base))
    alternative["causal_relations"] = [p[-1] for p in contract["required_causal_propositions"]]
    alternative["repair_relations"] = [p[-1] for p in contract["required_repair_propositions"]]
    run("finite_alternatives", alternative, True)
    distractor = dict(base, evidence_ids=["E1", "E2", "E3", "E4", "E5", "D1"])
    run("bounded_evidence_superset", distractor, True)
    missing = dict(base, causal_relations=base["causal_relations"][:-1])
    run("missing_proposition", missing, False)
    reversed_time = json.loads(json.dumps(base))
    reversed_time["causal_relations"].append(contract["forbidden_relations"][0])
    run("reversed_time", reversed_time, False)
    unknown_relation = json.loads(json.dumps(base))
    unknown_relation["causal_relations"].append(_edge("stale_snapshot", "imagines", "publication"))
    run("unknown_relation", unknown_relation, False)
    unknown_entity = json.loads(json.dumps(base))
    unknown_entity["causal_relations"].append(_edge("invented", "causes", "publication"))
    run("unknown_entity", unknown_entity, False)
    caller = dict(base, success=True)
    run("caller_success", caller, False)
    run("malformed_unknown", "not-json", None)
    return {
        "passed": all(observed is expected for _, observed, expected in checks),
        "check_count": len(checks),
        "checks": [
            {"id": name, "observed": observed, "expected": expected}
            for name, observed, expected in checks
        ],
    }


def freeze_equivalence_policy(
    store: Any,
    repo: str,
    *,
    instrument_audit_receipt_hash: str,
    corpus_bundle: Mapping[str, Any],
    evaluator_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    audit_hash = str(instrument_audit_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, audit_hash).get("valid") is not True:
        raise ValueError("canonical alpha.28 instrument audit is required")
    audit = store.symbiotic_receipt(audit_hash, repo=repo) or {}
    if (
        audit.get("kind") != "bridge_low_instrument_audit"
        or audit.get("state") != "BRIDGE_LOW_INTERPRETATION_HELD"
        or int(audit.get("additional_model_calls", -1)) != 0
        or audit.get("historical_scores_rewritten") is not False
        or audit.get("difficulty_interpretation_confounded") is not True
    ):
        raise ValueError("alpha.28 audit does not open equivalence closure")
    if verify_equivalence_evaluator_bundle(evaluator_bundle).get("valid") is not True:
        raise ValueError("equivalence evaluator bundle is invalid")
    self_test = equivalence_evaluator_self_test(evaluator_bundle)
    if self_test.get("passed") is not True:
        raise ValueError("equivalence evaluator self-test failed")
    result_hash = str(audit.get("result_receipt_hash") or "")
    result = store.symbiotic_receipt(result_hash, repo=repo) or {}
    contracts = evaluator_bundle["private_key"]["contracts"]
    shadow: list[dict[str, Any]] = []
    for receipt_hash in result.get("case_receipt_hashes") or ():
        case = store.symbiotic_receipt(str(receipt_hash), repo=repo) or {}
        case_id = str(case.get("case_id") or "")
        trajectory_hash = str(case.get("trajectory_receipt_hash") or "")
        if verify_native_agent_trajectory(store, repo, trajectory_hash).get("valid") is not True:
            raise ValueError("source trajectory reconstruction failed")
        trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
        verdict = evaluate_equivalent_relational_response(
            contracts[case_id], str(trajectory.get("final_answer") or "")
        )
        shadow.append({"case_id": case_id, "success": verdict.get("success"), "errors": verdict.get("errors")})
    material = {
        "schema_version": "cortex-relational-equivalence-preflight/4.0",
        "version": __version__,
        "kind": "relational_equivalence_preflight",
        "source_instrument_audit_receipt_hash": audit_hash,
        "source_result_receipt_hash": result_hash,
        "evaluator_manifest": evaluator_bundle["manifest"],
        "self_test": self_test,
        "post_hoc_shadow": shadow,
        "post_hoc_shadow_success_count": sum(row["success"] is True for row in shadow),
        "historical_scores_rewritten": False,
        "additional_model_calls": 0,
        "ruler_building_closed": True,
        "baseline_difficulty_established": False,
        "semantic_transfer_established": False,
        "state": "RELATIONAL_EQUIVALENCE_V4_READY",
        "next_action": "freeze_one_final_fresh_screen_or_switch_to_executable_tasks",
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(store, repo, task="freeze relational equivalence v4", persist=True)
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"relational_equivalence_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


__all__ = [
    "EVALUATOR_ID",
    "build_equivalence_evaluator_bundle",
    "equivalence_evaluator_self_test",
    "evaluate_equivalent_relational_response",
    "freeze_equivalence_policy",
    "verify_equivalence_evaluator_bundle",
]
