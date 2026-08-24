"""v9.6 empirical commissioning over the existing canonical circulation.

The commissioning seal does not create a second evidence system.  It reloads
and checks the v9.0-v9.5 receipts after a host-registered live adapter has run.
Task success remains separate from the proposition that a real, independently
evaluated model outcome was captured correctly.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .adapter_provenance import EVIDENCE_LIVE, resolve_adapter_provenance
from .evaluation import TASK_GATE_FAIL, TASK_GATE_PASS, TaskEvaluationContract
from .model_circulation import (
    ModelAdapter,
    ModelAdapterError,
    run_model_circulation,
    verify_model_circulation,
)
from .symbiosis import open_symbiotic_session

SCHEMA = "cortex-empirical-commissioning/1.0"
VERSION = "9.6.0"
GLYPH = "⟡◉⟲"
STATUS_VERIFIED = "EMPIRICAL_CIRCULATION_VERIFIED"
STATUS_HELD = "EMPIRICAL_CIRCULATION_HELD"

CLAIM_BOUNDARY = (
    "v9.6 verifies that one host-registered live model boundary produced a "
    "canonically bound public result that Cortex independently evaluated and "
    "witnessed. It does not prove model competence, cross-model transfer, "
    "provider attestation, cognition, consciousness, agency, or authority."
)

_REQUIRED_RECEIPTS = frozenset(
    {
        "model_invocation",
        "model_proposal",
        "model_evaluation",
        "model_outcome",
        "model_witness",
        "model_trajectory",
    }
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


def _assess_empirical_circulation(
    result: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> dict[str, Any]:
    """Independently classify a completed circulation without trusting claims."""

    errors: list[str] = []
    if not isinstance(result, Mapping) or not isinstance(verification, Mapping):
        errors.append("commissioning_inputs_must_be_mappings")
        result = {}
        verification = {}

    evidence_class = str(verification.get("evidence_class") or "unknown")
    if evidence_class != EVIDENCE_LIVE:
        errors.append("live_empirical_adapter_evidence_required")
    if verification.get("valid") is not True:
        errors.append("canonical_circulation_verification_failed")
    if str(result.get("persistence_status") or "") != "committed":
        errors.append("canonical_circulation_not_committed")

    receipt_bindings = verification.get("receipt_bindings")
    receipt_bindings = receipt_bindings if isinstance(receipt_bindings, Mapping) else {}
    missing = sorted(_REQUIRED_RECEIPTS.difference(str(key) for key in receipt_bindings))
    if missing:
        errors.append("required_receipts_missing:" + ",".join(missing))
    for kind in _REQUIRED_RECEIPTS.intersection(str(key) for key in receipt_bindings):
        binding = receipt_bindings.get(kind)
        if not isinstance(binding, Mapping):
            errors.append(f"{kind}_binding_invalid")
            continue
        if len(str(binding.get("receipt_hash") or "")) != 64:
            errors.append(f"{kind}_receipt_hash_invalid")
        if len(str(binding.get("content_hash") or "")) != 64:
            errors.append(f"{kind}_content_hash_invalid")

    outcome_status = str(verification.get("outcome_status") or "")
    if outcome_status not in {"verified_success", "verified_failure"}:
        errors.append("independently_verified_outcome_required")
    witness_hash = str(verification.get("witness_result_hash") or "")
    if len(witness_hash) != 64:
        errors.append("canonical_witness_result_required")

    provenance = verification.get("adapter_provenance")
    provenance = provenance if isinstance(provenance, Mapping) else {}
    if len(str(provenance.get("registration_id") or "")) != 64:
        errors.append("host_adapter_registration_required")
    if str(provenance.get("evidence_class") or "") != EVIDENCE_LIVE:
        errors.append("adapter_registration_evidence_class_invalid")
    if provenance.get("provider_attestation_claimed") is not False:
        errors.append("unsupported_provider_attestation_claim")

    for source_name, source in (("result", result), ("verification", verification)):
        for flag in (
            "host_mutate_authorized",
            "execution_authorized",
            "memory_admission_authorized",
            "policy_mutation_authorized",
            "policy_effect",
            "update_authorized",
        ):
            if flag in source and source.get(flag) is not False:
                errors.append(f"{source_name}_{flag}_must_be_false")

    evaluation = result.get("evaluation")
    evaluation = evaluation if isinstance(evaluation, Mapping) else {}
    evaluation_state = str(evaluation.get("state") or "unknown")
    if evaluation_state not in {TASK_GATE_PASS, TASK_GATE_FAIL}:
        errors.append("task_evaluation_must_be_observed_pass_or_fail")

    status = STATUS_VERIFIED if not errors else STATUS_HELD
    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "status": status,
        "repo": verification.get("repo") or result.get("repo"),
        "repository_id": result.get("repository_id"),
        "session_id": verification.get("session_id") or result.get("session_id"),
        "turn_id": verification.get("turn_id") or result.get("turn_id"),
        "invocation_id": verification.get("invocation_id") or result.get("invocation_id"),
        "body_epoch_id": verification.get("body_epoch_id") or result.get("body_epoch_id"),
        "evidence_class": evidence_class,
        "evidence_state": verification.get("evidence_state"),
        "adapter_registration_id": provenance.get("registration_id"),
        "provider_attestation": provenance.get("provider_attestation"),
        "provider_attestation_claimed": provenance.get("provider_attestation_claimed"),
        "model_identity": dict(verification.get("model_identity") or {}),
        "context_projection_hash": verification.get("context_projection_hash"),
        "task_contract_hash": verification.get("task_contract_hash"),
        "outcome_status": outcome_status,
        "task_evaluation_state": evaluation_state,
        "task_success": evaluation.get("success") is True,
        "witness_result_hash": witness_hash,
        "receipt_bindings": {str(k): dict(v) for k, v in receipt_bindings.items()},
        "errors": sorted(set(errors)),
        "canonical_circulation_valid": verification.get("valid") is True,
        "private_chain_of_thought_required": False,
        "private_chain_of_thought_stored": False,
        "provider_specific_semantics_in_core": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "update_authorized": False,
        "advisory_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return {**material, "receipt_hash": _sha(material)}


def verify_empirical_commissioning(
    store: Any,
    repo: str,
    session_id: str,
    *,
    turn_id: int = 1,
) -> dict[str, Any]:
    """Reconstruct one commissioning seal from canonical ledger objects only."""

    verification = verify_model_circulation(
        store,
        repo,
        str(session_id),
        turn_id=int(turn_id),
    )
    rows = [
        row
        for row in store.symbiotic_session_receipts(repo, str(session_id))
        if int(row.get("turn_id") or 0) == int(turn_id)
    ]
    by_kind = {str(row.get("kind") or ""): row for row in rows}
    evaluation_row = by_kind.get("model_evaluation") or {}
    reconstructed = {
        "repo": repo,
        "repository_id": (by_kind.get("model_invocation") or {}).get("repository_id"),
        "session_id": str(session_id),
        "turn_id": int(turn_id),
        "invocation_id": (by_kind.get("model_invocation") or {}).get("invocation_id"),
        "body_epoch_id": (by_kind.get("model_invocation") or {}).get("body_epoch_id"),
        "persistence_status": (
            "committed" if _REQUIRED_RECEIPTS.issubset(by_kind) else "incomplete"
        ),
        "evaluation": dict(evaluation_row.get("evaluation") or {}),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_mutation_authorized": False,
        "policy_effect": False,
        "update_authorized": False,
    }
    seal = _assess_empirical_circulation(reconstructed, verification)
    return {
        **seal,
        "verification_errors": list(verification.get("errors") or ()),
        "reconstructed_from_canonical_ledger": True,
        "caller_result_used": False,
    }


def commission_empirical_circulation(
    store: Any,
    repo: str,
    *,
    adapter: ModelAdapter,
    task_instruction: str,
    expected_text: str,
    contract_id: str = "cortex-v960-empirical-commissioning-v1",
    tool_scopes: Sequence[str] | None = None,
    configuration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Invoke one registered live adapter and issue a reconstructed seal."""

    instruction = str(task_instruction or "").strip()
    expected = str(expected_text or "")
    if not instruction or not expected:
        raise ModelAdapterError("commissioning task instruction and expected text are required")
    provenance = resolve_adapter_provenance(store, repo, adapter)
    if str(provenance.get("evidence_class") or "") != EVIDENCE_LIVE:
        raise ModelAdapterError("commissioning requires a host-registered live adapter")

    identity = {
        "provider_family": str(getattr(adapter, "provider_family", "") or ""),
        "model_id": str(getattr(adapter, "model_id", "") or ""),
    }
    session = open_symbiotic_session(
        store,
        repo,
        task=instruction,
        provider=identity["provider_family"],
        model_id=identity["model_id"],
        capability_profile={"empirical_commissioning": True},
        tool_scopes=tool_scopes or (),
        persist=True,
    )
    contract = TaskEvaluationContract(
        contract_id=str(contract_id),
        task_type="text_contains",
        target_field="text",
        expected_value=expected,
        evaluator_id="cortex.empirical-commissioning.evaluator.v1",
        version="1",
    )
    public_configuration = {
        **dict(configuration or {}),
        "task_instruction": instruction,
        "commissioning_contract_id": contract.contract_id,
    }
    result = run_model_circulation(
        store,
        repo,
        session,
        adapter=adapter,
        task_contract=contract,
        observed_result=None,
        tool_scopes=tool_scopes or (),
        configuration=public_configuration,
        persist=True,
    )
    verification = verify_model_circulation(
        store,
        repo,
        str(result.get("session_id") or ""),
        turn_id=int(result.get("turn_id") or 0),
    )
    seal = verify_empirical_commissioning(
        store,
        repo,
        str(result.get("session_id") or ""),
        turn_id=int(result.get("turn_id") or 0),
    )
    return {
        "seal": seal,
        "result": result,
        "verification": verification,
        "task_contract": contract.to_dict(),
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "GLYPH",
    "SCHEMA",
    "STATUS_HELD",
    "STATUS_VERIFIED",
    "VERSION",
    "commission_empirical_circulation",
    "verify_empirical_commissioning",
]
