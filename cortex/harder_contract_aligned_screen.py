"""Canonical alpha.39 screen bound to the harder contract-aligned forge."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .harder_contract_aligned_forge import verify_harder_contract_aligned_forge
from .structured_repair_screen import (
    freeze_structured_repair_screen,
    verify_structured_repair_screen,
)

SCHEMA = "cortex-alpha39-harder-contract-aligned-screen-binding/1.0"


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _identity(adapter: Any) -> dict[str, str]:
    return {
        key: str(getattr(adapter, key, "") or "")
        for key in ("provider_family", "model_id", "model_version", "adapter_id", "adapter_version")
    }


def aligned_forge_view(harder_forge: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct the verified aligned forge body consumed by the shared screen."""
    view = dict(harder_forge.get("contract_forge_result") or {})
    view["public_corpus"] = harder_forge.get("public_corpus") or {}
    view["result_hash"] = _sha({key: value for key, value in view.items() if key != "result_hash"})
    return view


def _prerequisite(
    harder_forge: Mapping[str, Any], aligned_view: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "harder_forge_result_hash": harder_forge["result_hash"],
        "harder_forge_source_commit": harder_forge["source_commit"],
        "prior_result_receipt_hash": harder_forge["prior_result_receipt_hash"],
        "difficulty_transition": "move_harder",
        "aligned_forge_result_hash": aligned_view["result_hash"],
        "aligned_corpus_hash": (harder_forge.get("public_corpus") or {})["corpus_hash"],
        "private_bundle_hash": harder_forge["private_bundle_hash"],
    }


def freeze_harder_contract_aligned_screen(
    store: Any,
    repo: str,
    *,
    harder_forge: Mapping[str, Any],
    private_bundle: Mapping[str, Any],
    adapter: Any,
) -> dict[str, Any]:
    audit = verify_harder_contract_aligned_forge(
        store, repo, harder_forge, private_bundle=private_bundle
    )
    if (
        audit.get("valid") is not True
        or harder_forge.get("state") != "HARDER_CONTRACT_ALIGNED_FORGE_READY"
    ):
        raise ValueError("canonical harder contract-aligned forge is required")
    if _identity(adapter) != harder_forge.get("prior_model_identity"):
        raise ValueError("same-model harder frontier baseline is required")
    aligned = aligned_forge_view(harder_forge)
    return freeze_structured_repair_screen(
        store,
        repo,
        forge_artifact=aligned,
        private_bundle=private_bundle,
        adapter=adapter,
        governed_prerequisite=_prerequisite(harder_forge, aligned),
    )


def verify_harder_contract_aligned_screen(
    store: Any,
    repo: str,
    *,
    result_receipt_hash: str,
    harder_forge: Mapping[str, Any],
    private_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    base = verify_structured_repair_screen(store, repo, result_receipt_hash=result_receipt_hash)
    errors = list(base.get("errors") or ())
    harder_audit = verify_harder_contract_aligned_forge(
        store, repo, harder_forge, private_bundle=private_bundle
    )
    if harder_audit.get("valid") is not True:
        errors.append("harder_forge_invalid")
    result = store.symbiotic_receipt(result_receipt_hash, repo=repo) or {}
    prereg = (
        store.symbiotic_receipt(str(result.get("preregistration_receipt_hash") or ""), repo=repo)
        or {}
    )
    aligned = aligned_forge_view(harder_forge)
    if prereg.get("governed_prerequisite") != _prerequisite(harder_forge, aligned):
        errors.append("harder_prerequisite_binding_invalid")
    if prereg.get("forge_result_hash") != aligned["result_hash"]:
        errors.append("aligned_forge_binding_invalid")
    alignment = prereg.get("contract_alignment_binding") or {}
    if alignment.get("alignment_result_hash") != aligned["result_hash"]:
        errors.append("alignment_proof_binding_invalid")
    if result.get("model_identity") != harder_forge.get("prior_model_identity"):
        errors.append("same_model_binding_invalid")
    return {
        **base,
        "valid": not errors,
        "errors": errors,
        "harder_forge_result_hash": harder_forge.get("result_hash"),
    }


__all__ = [
    "SCHEMA",
    "aligned_forge_view",
    "freeze_harder_contract_aligned_screen",
    "verify_harder_contract_aligned_screen",
]
