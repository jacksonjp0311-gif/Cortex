"""Zero-paid-call modern source-experience commissioning."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from typing import Any

from .competence import derive_competence_candidate, verify_competence_candidate
from .distillation_witness import resolve_distillation_support
from .epistemic_kernel import append_epistemic_event, verify_epistemic_history
from .evaluation import TaskEvaluationContract
from .model_circulation import FixtureAdapter, run_model_circulation, verify_model_circulation
from .symbiosis import open_symbiotic_session


DEFAULT_SOURCE_EXPERIENCE = {
    "experience_id": "cache-invalidation",
    "observation": "fresh value observed",
    "operation": "invalidate cache before reread",
    "effect": "fresh value observed",
    "public_description": (
        "Invalidate persistent cached state before trusting a reread after mutation."
    ),
}

SHAM_SOURCE_EXPERIENCE = {
    "experience_id": "fixture-line-endings",
    "observation": "stable fixture hash observed",
    "operation": "normalize line endings before hashing text fixtures",
    "effect": "stable fixture hash observed",
    "public_description": (
        "Normalize line endings before hashing portable text fixtures."
    ),
}


def forge_structural_source_experience(
    store: Any,
    repo: str,
    *,
    specification: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Commission the full modern lineage using synthetic mechanism evidence.

    The result proves architecture only. Fixture provenance is preserved and
    can never satisfy a live-empirical transfer gate.
    """
    spec = dict(DEFAULT_SOURCE_EXPERIENCE if specification is None else specification)
    required = {
        "experience_id", "observation", "operation", "effect", "public_description"
    }
    missing = sorted(required - set(spec))
    if missing or any(not str(spec.get(key) or "").strip() for key in required):
        raise ValueError(f"source experience specification is incomplete: {missing}")
    observed = {
        "text": str(spec["observation"]),
        "data": {
            "operation": str(spec["operation"]),
            "effect": str(spec["effect"]),
        },
    }
    contract = TaskEvaluationContract(
        contract_id=f"alpha17-structural-source-{spec['experience_id']}-v1",
        task_type="text_contains",
        target_field="text",
        expected_value=str(spec["observation"]),
    )
    session = open_symbiotic_session(
        store, repo, task="commission a modern structural source experience"
    )
    circulation = run_model_circulation(
        store,
        repo,
        session,
        adapter=FixtureAdapter(
            model_id="alpha17-structural-fixture",
            text=str(spec["observation"]),
            action=str(spec["operation"]),
        ),
        task_contract=contract,
        observed_result=observed,
    )
    candidate = derive_competence_candidate(
        store,
        repo,
        session_id=session["session_id"],
        turn_id=1,
        capability={"operation": observed["data"]["operation"]},
        intended_outcome={"effect": observed["data"]["effect"]},
        applicability_conditions=(),
        failure_conditions=(),
        counterevidence=(),
        uncertainty=(),
        public_description=str(spec["public_description"]),
        rationale_public="Structural commissioning only; held-out transfer remains untested.",
    )
    competence_check = verify_competence_candidate(
        store, repo, str(candidate["competence_id"])
    )
    semantic_support = resolve_distillation_support(
        store, repo, str(candidate["competence_id"]), create_if_missing=True
    )
    circulation_check = verify_model_circulation(
        store, repo, session["session_id"], turn_id=1
    )
    trajectory_hash = str(
        candidate["originating_trajectories"][0]["trajectory_receipt_hash"]
    )
    prerequisite_pass = bool(
        circulation_check.get("valid") is True
        and competence_check.get("valid") is True
        and semantic_support.get("state") == "pass"
    )
    event = (
        append_epistemic_event(
            store,
            repo,
            claim_id=f"competence:{candidate['competence_id']}",
            claim_text=str(candidate["public_description"]),
            polarity="support",
            evidence_receipt_hash=str(semantic_support.get("receipt_hash") or ""),
            source_lineage_hash=trajectory_hash,
            valid_from=time.time(),
        )
        if prerequisite_pass
        else None
    )
    history = verify_epistemic_history(store, repo)
    structural_pass = bool(
        prerequisite_pass
        and history.get("valid") is True
        and event is not None
    )
    return {
        "schema_version": "cortex-modern-source-experience/1.0",
        "experience_id": str(spec["experience_id"]),
        "state": "STRUCTURAL_SOURCE_EXPERIENCE_PASS" if structural_pass else "STRUCTURAL_SOURCE_EXPERIENCE_HELD",
        "evidence_class": circulation.get("evidence_class"),
        "empirical": False,
        "production_transfer_eligible": False,
        "session_id": session["session_id"],
        "competence_id": candidate["competence_id"],
        "competence_receipt_hash": candidate["receipt_hash"],
        "distillation_witness_receipt_hash": semantic_support.get("receipt_hash"),
        "epistemic_event_hash": event["event_hash"] if event is not None else None,
        "checks": {
            "circulation": circulation_check,
            "competence": competence_check,
            "semantic_support": semantic_support,
            "epistemic_history": history,
        },
        "calls_executed": 0,
        "paid_calls_executed": 0,
        "next_action": "calibrate_held_out_non_ceiling_semantic_transfer_tasks",
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "advisory_only": True,
    }


def forge_structural_source_experience_pair(
    store: Any,
    repo: str,
    *,
    specifications: Sequence[Mapping[str, str]] = (
        DEFAULT_SOURCE_EXPERIENCE,
        SHAM_SOURCE_EXPERIENCE,
    ),
) -> dict[str, Any]:
    """Create a relevant/sham pair without confusing synthetic with empirical."""
    rows = [
        forge_structural_source_experience(store, repo, specification=spec)
        for spec in specifications
    ]
    competence_ids = {str(row.get("competence_id") or "") for row in rows}
    witness_hashes = {
        str(row.get("distillation_witness_receipt_hash") or "") for row in rows
    }
    pair_valid = bool(
        len(rows) == 2
        and len(competence_ids) == 2
        and len(witness_hashes) == 2
        and all(row.get("state") == "STRUCTURAL_SOURCE_EXPERIENCE_PASS" for row in rows)
        and all(row.get("evidence_class") == "synthetic" for row in rows)
    )
    return {
        "schema_version": "cortex-structural-source-experience-pair/1.0",
        "state": "STRUCTURAL_LESSON_PAIR_PASS" if pair_valid else "STRUCTURAL_LESSON_PAIR_HELD",
        "relevant": rows[0] if rows else None,
        "sham": rows[1] if len(rows) > 1 else None,
        "semantic_distinctness": "pass" if len(competence_ids) == 2 else "fail",
        "witness_distinctness": "pass" if len(witness_hashes) == 2 else "fail",
        "evidence_class": "synthetic",
        "empirical_transfer_established": False,
        "production_transfer_eligible": False,
        "calls_executed": 0,
        "paid_calls_executed": 0,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "advisory_only": True,
    }


__all__ = [
    "DEFAULT_SOURCE_EXPERIENCE",
    "SHAM_SOURCE_EXPERIENCE",
    "forge_structural_source_experience",
    "forge_structural_source_experience_pair",
]
