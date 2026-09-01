"""Answer-sealed intermediate relational task forge for alpha.27."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from . import __version__
from .relational_causal_evaluator import (
    CONTRACT_SCHEMA,
    RELATION_KEYS,
    RESPONSE_KEYS,
    evaluate_relational_causal_response,
)
from .symbiosis import open_symbiotic_session

PUBLIC_SCHEMA = "cortex-intermediate-relational-corpus/1.0"
PRIVATE_SCHEMA = "cortex-intermediate-relational-key/1.0"
PREFLIGHT_SCHEMA = "cortex-intermediate-relational-preflight/1.0"
BANDS = ("bridge_low", "bridge_mid", "bridge_high")


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


def _contract(
    case_id: str,
    *,
    causal_relations: list[dict[str, str]],
    repair_relations: list[dict[str, str]],
    reference_response: Mapping[str, Any],
) -> dict[str, Any]:
    material = {
        "schema_version": CONTRACT_SCHEMA,
        "case_id": case_id,
        "required_causal_relations": causal_relations,
        "required_repair_relations": repair_relations,
        "allowed_causal_relations": causal_relations,
        "allowed_repair_relations": repair_relations,
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
        "reference_response": dict(reference_response),
    }
    return {**material, "contract_hash": _sha(material)}


def build_intermediate_relational_bundle(*, secret_seed: str) -> dict[str, Any]:
    """Forge three progressive panels while holding evidence policy constant."""
    if not str(secret_seed).strip():
        raise ValueError("secret_seed is required")
    variants = (
        ("source_graph", "snapshot_cache", "derived_index"),
        ("policy_store", "policy_snapshot", "compiled_policy"),
        ("schema_registry", "schema_snapshot", "generated_validator"),
        ("route_table", "route_snapshot", "compiled_router"),
    )
    public_cases: list[dict[str, Any]] = []
    contracts: dict[str, Any] = {}
    band_cases: dict[str, list[str]] = {band: [] for band in BANDS}
    for band_index, band in enumerate(BANDS):
        for variant_index, (source, snapshot, derived) in enumerate(variants, start=1):
            identity = {
                "band": band,
                "band_index": band_index,
                "variant": variant_index,
                "source": source,
                "snapshot": snapshot,
                "derived": derived,
            }
            case_id = f"irc_{_sha({'seed': secret_seed, **identity})[:20]}"
            causal = [
                _edge(source, "has_generation", "generation_42"),
                _edge(snapshot, "has_generation", "generation_41"),
                _edge(snapshot, "older_than", source),
                _edge(derived, "reads_from", snapshot),
            ]
            repair = [
                _edge(snapshot, "must_match_generation", source),
                _edge("snapshot_validation", "precedes", derived),
            ]
            if band_index >= 1:
                causal.append(_edge("stale_snapshot", "causes", derived))
            if band_index >= 2:
                causal.extend(
                    [
                        _edge(derived, "published_as", "generation_42"),
                        _edge("generation_mismatch", "invalidates", derived),
                    ]
                )
                repair.append(_edge("generation_mismatch", "blocks", "publication"))
            reference = {
                "cause": "public rationale is retained but graph relations carry the proof",
                "repair": "validate source and snapshot generation before publication",
                "causal_relations": causal,
                "repair_relations": repair,
                "evidence_ids": ["E1", "E2", "E3", "E4"],
                "uncertainty": "low",
            }
            contract = _contract(
                case_id,
                causal_relations=causal,
                repair_relations=repair,
                reference_response=reference,
            )
            contracts[case_id] = contract
            band_cases[band].append(case_id)
            events = [
                f"E1: {source} commits generation 42",
                f"E2: {snapshot} remains at generation 41",
                f"E3: {derived} reads from {snapshot}",
                f"E4: {derived} is published as generation 42 while containing generation 41 material",
                f"E5: a direct {source} read returns generation 42",
                "D1: serialization checksum is internally consistent",
            ]
            instruction = {
                "bridge_low": "Represent the stale-input mechanism and minimum ordering safeguard.",
                "bridge_mid": "Represent the complete stale-input causal transition and safeguard.",
                "bridge_high": "Represent the causal chain, invalidity relation, and publication block.",
            }[band]
            public_cases.append(
                {
                    "case_id": case_id,
                    "family": "generation_bound_derived_state",
                    "difficulty_band": band,
                    "development_only": True,
                    "instruction": instruction,
                    "events": events,
                    "entities": [
                        source,
                        snapshot,
                        derived,
                        "generation_41",
                        "generation_42",
                        "stale_snapshot",
                        "generation_mismatch",
                        "snapshot_validation",
                        "publication",
                    ],
                    "response_schema": list(RESPONSE_KEYS),
                    "relation_schema": list(RELATION_KEYS),
                    "contract_commitment": _sha(contract),
                }
            )
    private_key = {
        "schema_version": PRIVATE_SCHEMA,
        "contracts": contracts,
        "band_case_ids": band_cases,
    }
    public_material = {
        "schema_version": PUBLIC_SCHEMA,
        "version": __version__,
        "family": "generation_bound_derived_state",
        "cases": public_cases,
        "bands": list(BANDS),
        "band_case_ids": band_cases,
        "initial_screen_band": "bridge_low",
        "sequential_rule": "screen one four-case band; stop if success rate is 0.30..0.70; otherwise move one adjacent band",
        "evidence_policy_constant_across_bands": True,
        "model_identity_in_scoring": False,
        "private_contracts_present": False,
        "private_key_commitment": _sha(private_key),
        "development_only": True,
        "confirmatory_eligible": False,
    }
    manifest = {**public_material, "corpus_hash": _sha(public_material)}
    return {"manifest": manifest, "private_key": private_key}


def verify_intermediate_relational_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    manifest = bundle.get("manifest") if isinstance(bundle, Mapping) else None
    private = bundle.get("private_key") if isinstance(bundle, Mapping) else None
    errors: list[str] = []
    if not isinstance(manifest, Mapping) or not isinstance(private, Mapping):
        return {"valid": False, "errors": ["bundle_shape_invalid"]}
    material = {key: value for key, value in manifest.items() if key != "corpus_hash"}
    if manifest.get("schema_version") != PUBLIC_SCHEMA:
        errors.append("manifest_schema_invalid")
    if manifest.get("corpus_hash") != _sha(material):
        errors.append("corpus_hash_invalid")
    if private.get("schema_version") != PRIVATE_SCHEMA:
        errors.append("private_schema_invalid")
    if manifest.get("private_key_commitment") != _sha(private):
        errors.append("private_key_commitment_invalid")
    if manifest.get("private_contracts_present") is not False:
        errors.append("private_boundary_invalid")
    contracts = private.get("contracts") or {}
    public_ids = [str(row.get("case_id") or "") for row in manifest.get("cases") or ()]
    if sorted(contracts) != sorted(public_ids) or len(public_ids) != 12:
        errors.append("case_binding_invalid")
    band_cases = private.get("band_case_ids") or {}
    if band_cases != manifest.get("band_case_ids") or any(
        len(band_cases.get(band) or ()) != 4 for band in BANDS
    ):
        errors.append("band_binding_invalid")
    for case_id, contract in contracts.items():
        contract_material = {
            key: value for key, value in contract.items() if key != "contract_hash"
        }
        if (
            contract.get("schema_version") != CONTRACT_SCHEMA
            or contract.get("case_id") != case_id
            or contract.get("contract_hash") != _sha(contract_material)
        ):
            errors.append(f"contract_invalid:{case_id}")
            continue
        reference = contract.get("reference_response") or {}
        verdict = evaluate_relational_causal_response(contract, _canonical(reference))
        if verdict.get("success") is not True:
            errors.append(f"reference_invalid:{case_id}")
    return {"valid": not errors, "errors": errors}


def freeze_intermediate_relational_forge(
    store: Any,
    repo: str,
    *,
    relational_preflight_receipt_hash: str,
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    prerequisite_hash = str(relational_preflight_receipt_hash or "")
    if store.verify_symbiotic_receipt(repo, prerequisite_hash).get("valid") is not True:
        raise ValueError("canonical alpha.26 preflight is required")
    prerequisite = store.symbiotic_receipt(prerequisite_hash, repo=repo) or {}
    if (
        prerequisite.get("kind") != "relational_causal_evaluator_preflight"
        or prerequisite.get("state") != "RELATIONAL_CAUSAL_EVALUATOR_V3_READY"
        or int(prerequisite.get("planned_live_calls", -1)) != 0
        or prerequisite.get("historical_scores_rewritten") is not False
        or prerequisite.get("difficulty_interpolation_ready") is not True
    ):
        raise ValueError("alpha.26 preflight does not open the intermediate forge")
    verification = verify_intermediate_relational_bundle(bundle)
    if verification.get("valid") is not True:
        raise ValueError("intermediate relational bundle is invalid")
    manifest = bundle["manifest"]
    material = {
        "schema_version": PREFLIGHT_SCHEMA,
        "version": __version__,
        "kind": "intermediate_relational_forge_preflight",
        "source_relational_preflight_receipt_hash": prerequisite_hash,
        "source_evaluator_hash": (prerequisite.get("evaluator_manifest") or {}).get(
            "evaluator_hash"
        ),
        "corpus_manifest": manifest,
        "initial_screen_case_ids": manifest["band_case_ids"]["bridge_low"],
        "panel_count": 3,
        "cases_per_panel": 4,
        "planned_live_calls": 0,
        "maximum_future_calls_without_new_authority": 0,
        "historical_scores_rewritten": False,
        "evidence_policy_constant_across_bands": True,
        "baseline_difficulty_established": False,
        "semantic_transfer_established": False,
        "state": "INTERMEDIATE_RELATIONAL_FORGE_READY",
        "next_action": "freeze_four_call_bridge_low_screen",
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }
    session = open_symbiotic_session(
        store, repo, task="freeze intermediate relational task forge", persist=True
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"intermediate_relational_{_sha(material)[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


__all__ = [
    "BANDS",
    "build_intermediate_relational_bundle",
    "freeze_intermediate_relational_forge",
    "verify_intermediate_relational_bundle",
]
