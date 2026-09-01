"""Canonical move-harder transition for contract-aligned repair calibration."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import __version__
from .contract_aligned_repair import (
    commission_contract_aligned_repair_forge,
    verify_contract_aligned_repair_bundle,
    verify_contract_aligned_repair_forge_result,
)
from .structured_repair_screen import verify_structured_repair_screen

SCHEMA = "cortex-alpha38-harder-contract-aligned-forge/1.0"


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


def freeze_harder_contract_aligned_forge(
    store: Any,
    repo: str,
    *,
    prior_result_receipt_hash: str,
    public_corpus: Mapping[str, Any],
    private_bundle: Mapping[str, Any],
    workspace: Path,
    source_commit: str,
) -> dict[str, Any]:
    """Commission a fresh harder forge after a canonical 4/4 aligned ceiling."""
    prior_audit = verify_structured_repair_screen(
        store,
        repo,
        result_receipt_hash=prior_result_receipt_hash,
    )
    prior = store.symbiotic_receipt(prior_result_receipt_hash, repo=repo) or {}
    prior_screen = prior.get("screen") or {}
    prior_prereg = store.symbiotic_receipt(
        str(prior.get("preregistration_receipt_hash") or ""),
        repo=repo,
    ) or {}
    alignment = prior_prereg.get("contract_alignment_binding") or {}
    if (
        prior_audit.get("valid") is not True
        or prior_screen.get("state") != "screening_ceiling"
        or prior_screen.get("success_count") != 4
        or alignment.get("all_private_assertions_publicly_mapped") is not True
        or alignment.get("all_public_requirements_covered") is not True
    ):
        raise ValueError("canonical contract-aligned 4/4 ceiling is required")
    bundle_audit = verify_contract_aligned_repair_bundle(public_corpus, private_bundle)
    if bundle_audit["valid"] is not True:
        raise ValueError("fresh contract-aligned bundle is invalid")
    commissioned = commission_contract_aligned_repair_forge(
        public_corpus,
        private_bundle,
        workspace,
    )
    commissioned_audit = verify_contract_aligned_repair_forge_result(commissioned)
    ready = (
        commissioned_audit["valid"] is True
        and commissioned["state"] == "CONTRACT_ALIGNED_REPAIR_FORGE_READY"
    )
    material: dict[str, Any] = {
        "schema_version": SCHEMA,
        "version": __version__,
        "state": (
            "HARDER_CONTRACT_ALIGNED_FORGE_READY"
            if ready
            else "HARDER_CONTRACT_ALIGNED_FORGE_HELD"
        ),
        "source_commit": source_commit,
        "difficulty_transition": "move_harder",
        "prior_result_receipt_hash": prior_result_receipt_hash,
        "prior_preregistration_receipt_hash": prior[
            "preregistration_receipt_hash"
        ],
        "prior_screen": {
            "state": prior_screen["state"],
            "success_count": prior_screen["success_count"],
            "case_count": prior_screen["case_count"],
        },
        "prior_model_identity": prior.get("model_identity"),
        "prior_alignment_result_hash": alignment.get("alignment_result_hash"),
        "contract_forge_result": commissioned,
        "public_corpus": public_corpus,
        "private_bundle_hash": private_bundle["private_bundle_hash"],
        "additional_model_calls": 0,
        "private_bundle_persisted_in_artifact": False,
        "baseline_calibration_established": False,
        "semantic_transfer_established": False,
        "general_improvement_established": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "next_action": (
            "freeze_harder_contract_aligned_baseline"
            if ready
            else "repair_harder_contract_forge"
        ),
    }
    material["result_hash"] = _sha(material)
    return material


def verify_harder_contract_aligned_forge(
    store: Any,
    repo: str,
    result: Mapping[str, Any],
    *,
    private_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("schema_version") != SCHEMA or result.get("result_hash") != _sha(body):
        errors.append("result_identity_invalid")
    prior_hash = str(result.get("prior_result_receipt_hash") or "")
    prior_audit = verify_structured_repair_screen(
        store,
        repo,
        result_receipt_hash=prior_hash,
    )
    prior = store.symbiotic_receipt(prior_hash, repo=repo) or {}
    prior_screen = prior.get("screen") or {}
    prior_prereg_hash = str(prior.get("preregistration_receipt_hash") or "")
    prior_prereg = store.symbiotic_receipt(prior_prereg_hash, repo=repo) or {}
    alignment = prior_prereg.get("contract_alignment_binding") or {}
    expected_screen = {
        "state": "screening_ceiling",
        "success_count": 4,
        "case_count": 4,
    }
    if (
        prior_audit.get("valid") is not True
        or prior_screen.get("state") != "screening_ceiling"
        or prior_screen.get("success_count") != 4
        or result.get("prior_screen") != expected_screen
        or result.get("prior_preregistration_receipt_hash") != prior_prereg_hash
        or result.get("prior_model_identity") != prior.get("model_identity")
        or result.get("prior_alignment_result_hash")
        != alignment.get("alignment_result_hash")
    ):
        errors.append("prior_ceiling_binding_invalid")
    public = result.get("public_corpus") or {}
    bundle_audit = verify_contract_aligned_repair_bundle(public, private_bundle)
    if bundle_audit["valid"] is not True:
        errors.append("contract_aligned_bundle_invalid")
    commissioned = result.get("contract_forge_result") or {}
    commissioned_audit = verify_contract_aligned_repair_forge_result(commissioned)
    if (
        commissioned_audit["valid"] is not True
        or commissioned.get("corpus_hash") != public.get("corpus_hash")
        or result.get("private_bundle_hash") != private_bundle.get("private_bundle_hash")
    ):
        errors.append("commissioned_forge_binding_invalid")
    ready = (
        not errors
        and commissioned.get("state") == "CONTRACT_ALIGNED_REPAIR_FORGE_READY"
    )
    expected_state = (
        "HARDER_CONTRACT_ALIGNED_FORGE_READY"
        if ready
        else "HARDER_CONTRACT_ALIGNED_FORGE_HELD"
    )
    if result.get("state") != expected_state:
        errors.append("result_state_invalid")
    if result.get("additional_model_calls") != 0:
        errors.append("model_call_boundary_invalid")
    for field in (
        "baseline_calibration_established",
        "semantic_transfer_established",
        "general_improvement_established",
        "host_mutate_authorized",
        "execution_authorized",
        "memory_admission_authorized",
        "policy_effect",
    ):
        if result.get(field) is not False:
            errors.append(f"authority_or_claim_boundary_invalid:{field}")
    return {
        "valid": not errors,
        "errors": errors,
        "state": result.get("state"),
        "prior_result_receipt_hash": prior_hash,
    }


__all__ = [
    "SCHEMA",
    "freeze_harder_contract_aligned_forge",
    "verify_harder_contract_aligned_forge",
]
