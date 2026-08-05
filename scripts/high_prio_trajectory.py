"""Operator high-prio path: full trajectory + membrane under healed epoch."""

from __future__ import annotations

import time
from pathlib import Path

from cortex.distillation_candidates import (
    extract_session_distillation_candidates,
    flatten_candidates,
)
from cortex.membrane import apply_will_bound_membrane
from cortex.store import Store
from cortex.symbiosis import (
    _sha,
    consolidate_session,
    open_symbiotic_session,
    record_joint_action,
    record_outcome,
    record_proposal,
)
from cortex.will import issue_will, verify_will
from cortex.witness import ensure_witness_tables


def main() -> None:
    home = Path.home() / ".cortex"
    store = Store(home / "cortex.db")
    ensure_witness_tables(store)
    repo = "Cortex"

    session = open_symbiotic_session(
        store,
        repo,
        task="high-prio full trajectory under 8.5.1 healed body",
        provider="xai",
        model_id="grok-build",
    )
    print(
        "open",
        session.get("session_id"),
        "epoch_ok",
        session.get("epoch_verified"),
        str(session.get("body_epoch_id") or "")[:16],
    )

    session = record_proposal(
        store,
        repo,
        session,
        interpreted_objective="Establish healed-epoch baseline measurement",
        proposed_action="record_joint_action_and_witnessed_outcome_for_trajectory",
        evidence_citations=["realign_8.5.1", "field_16_16", "observer_n_16", "hnsw_v1"],
        declared_uncertainty=0.2,
    )
    print(
        "t1 decision",
        session.get("latest_decision"),
        "epoch",
        session.get("epoch_verified"),
        "frame",
        session.get("latest_frame_overall_state"),
    )

    session = record_joint_action(
        store,
        repo,
        session,
        tool_action={"name": "trajectory_probe", "executed": True, "host_mutate": False},
        measured_result={"ok": True, "note": "advisory measurement only"},
    )
    joint = (session.get("receipts") or {}).get("joint_action") or {}
    metrics = {"trajectory": 1, "score": 1.0, "healed_epoch": True}
    turn = int(joint.get("turn_id") or session.get("current_turn_id") or 1)
    # Must match outcome_receipt subject exactly for witnessed=true.
    subject = {
        "outcome_kind": "task_result",
        "success": True,
        "metrics": dict(metrics),
        "external_reference": "high-prio-trajectory-1",
        "joint_action_receipt_hash": str(joint.get("receipt_hash") or ""),
        "session_id": str(session.get("session_id") or ""),
        "turn_id": turn,
        "body_epoch_id": str(session.get("body_epoch_id") or ""),
        "repository_id": str(session.get("repository_id") or ""),
        "repo": repo,
    }
    subject_hash = _sha(subject)
    witness = {
        "witness_kind": "OUTCOME",
        "verifier": "operator.high_prio_trajectory",
        "subject_receipt_hash": subject_hash,
        "evidence_hashes": [subject_hash, "realign_8.5.1", "observer_n_16"],
        "passed": True,
        "issued_at": time.time(),
    }
    witness["witness_id"] = "ow_" + _sha(witness)[:24]
    session = record_outcome(
        store,
        repo,
        session,
        success=True,
        metrics=metrics,
        external_reference="high-prio-trajectory-1",
        witness=witness,
    )
    outcome = (session.get("receipts") or {}).get("outcome") or {}
    print("outcome", outcome.get("status"), "witnessed", outcome.get("witnessed"))

    session = record_proposal(
        store,
        repo,
        session,
        interpreted_objective="Second turn after witnessed success — extract trajectory lesson",
        proposed_action="emit_distillation_candidates_from_verified_transition",
        evidence_citations=["outcome_turn1", "interconnect_frame"],
        declared_uncertainty=0.25,
    )
    batch = (session.get("receipts") or {}).get("distillation_candidates") or {}
    transition = (session.get("receipts") or {}).get("interconnect_transition") or {}
    print(
        "t2 decision",
        session.get("latest_decision"),
        "distill",
        batch.get("extraction_status"),
        batch.get("candidate_count"),
        "by_type",
        batch.get("by_type"),
        "transition",
        session.get("latest_transition_class"),
        "causal",
        transition.get("causal_status"),
    )

    will = issue_will(
        store,
        repo,
        principal_id="heal-op",
        secret="cortex-heal-8.5-membrane",
        session_id=session.get("session_id"),
        body_epoch_id=session.get("body_epoch_id"),
        repository_id=session.get("repository_id"),
        clauses=None,
    )
    print(
        "will",
        will.get("issued"),
        "from_default",
        will.get("from_default_policy"),
        "verified",
        verify_will(store, repo, will, secret="cortex-heal-8.5-membrane").get(
            "verified"
        ),
    )

    batches = extract_session_distillation_candidates(session)
    cands = flatten_candidates(batches)
    print(
        "batches",
        len(batches),
        "flat_cands",
        len(cands),
        "types",
        sorted({str(c.get("candidate_type")) for c in cands}),
    )

    admission = apply_will_bound_membrane(
        store,
        repo,
        will=will,
        will_secret="cortex-heal-8.5-membrane",
        candidates=cands,
        batches=batches,
        constitutional_gate=True,
        epoch_compatible=True,
        witness_present=True,
        outcome_closed=True,
        stable_regime=True,
        session_id=session.get("session_id"),
        body_epoch_id=session.get("body_epoch_id"),
        turn_id=int(session.get("current_turn_id") or 0),
    )
    print(
        "membrane admitted",
        admission.get("admitted_count"),
        "rejected",
        admission.get("rejected_count"),
        "deferred",
        admission.get("deferred_count"),
        "durable",
        admission.get("durable_write_authorized"),
        "invented",
        admission.get("invented_count"),
        "admitted_types",
        [c.get("candidate_type") for c in admission.get("admitted") or []],
    )
    for r in (admission.get("rejected") or [])[:8]:
        print("  reject", r.get("candidate_type"), r.get("rejection_reason"), r.get("support_level"))

    sealed = consolidate_session(
        store,
        repo,
        session,
        constitutional_gate=True,
        epoch_compatible=True,
        witness_present=True,
        outcome_closed=True,
        stable_regime=True,
        will=will,
        will_secret="cortex-heal-8.5-membrane",
    )
    cons = (sealed.get("receipts") or {}).get("symbiotic_consolidation") or {}
    print(
        "consolidate retained",
        cons.get("retained_count"),
        "rejected",
        cons.get("rejected_count"),
        "durable_session",
        sealed.get("durable_write_authorized"),
        "host_mutate",
        sealed.get("host_mutate_authorized"),
        "exec",
        sealed.get("execution_authorized"),
    )
    store.close()
    print("DONE")


if __name__ == "__main__":
    main()
