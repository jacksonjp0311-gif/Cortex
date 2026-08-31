"""Zero-paid-call modern source-experience commissioning."""

from __future__ import annotations

import time
from typing import Any

from .competence import derive_competence_candidate, verify_competence_candidate
from .distillation_witness import resolve_distillation_support
from .epistemic_kernel import append_epistemic_event, verify_epistemic_history
from .evaluation import TaskEvaluationContract
from .model_circulation import FixtureAdapter, run_model_circulation, verify_model_circulation
from .symbiosis import open_symbiotic_session


def forge_structural_source_experience(store: Any, repo: str) -> dict[str, Any]:
    """Commission the full modern lineage using synthetic mechanism evidence.

    The result proves architecture only. Fixture provenance is preserved and
    can never satisfy a live-empirical transfer gate.
    """
    observed = {
        "text": "fresh value observed",
        "data": {
            "operation": "invalidate cache before reread",
            "effect": "fresh value observed",
        },
    }
    contract = TaskEvaluationContract(
        contract_id="alpha16-structural-source-experience-v1",
        task_type="text_contains",
        target_field="text",
        expected_value="fresh value observed",
    )
    session = open_symbiotic_session(
        store, repo, task="commission a modern structural source experience"
    )
    circulation = run_model_circulation(
        store,
        repo,
        session,
        adapter=FixtureAdapter(
            model_id="alpha16-structural-fixture",
            text="fresh value observed",
            action="invalidate cache before reread",
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
        public_description=(
            "Invalidate persistent cached state before trusting a reread after mutation."
        ),
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


__all__ = ["forge_structural_source_experience"]
