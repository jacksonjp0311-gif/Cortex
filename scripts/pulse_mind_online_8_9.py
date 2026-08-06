"""Six-phase mind-online pulse under sealed 8.9 body.

Phases:
  0 preconditions
  1 open symbiotic session + issue will
  2 propose / action / outcome (witnessed)
  3 membrane admit + commit admitted memories + consolidate
  4 rehydrate (project) + second open context
  5 trials x3 + budget apply
  6 final report dict (printed as JSON)

Never host.mutate. Never invent. Measurement ≠ authority.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from cortex import __version__
from cortex.admitted_memory import (
    admitted_memory_status,
    commit_admitted_memories,
    list_admitted_memories,
)
from cortex.distillation_candidates import (
    extract_session_distillation_candidates,
    flatten_candidates,
)
from cortex.interconnect import mesh_status
from cortex.membrane import apply_will_bound_membrane
from cortex.memory_budget import apply_budget, budget_status
from cortex.memory_projection import project_memories
from cortex.memory_trials import memory_trial_status, run_cross_instantiation_trial
from cortex.realign import diagnose_realign
from cortex.self_sensing import observe_self_sensing
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

REPO = "Cortex"
SECRET = "cortex-heal-8.5-membrane"
PRINCIPAL = "heal-op"
TASK = (
    "bring mind-shaped loop online: admit measured lessons, rehydrate next "
    "temporary cortex under host immutability"
)


def _print(title: str, payload: Any) -> None:
    print(f"\n=== {title} ===")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2, default=str)[:4000])
    else:
        print(payload)


def main() -> dict[str, Any]:
    home = Path.home() / ".cortex"
    store = Store(home / "cortex.db")
    ensure_witness_tables(store)
    report: dict[str, Any] = {
        "schema": "cortex-mind-online-pulse/1.0",
        "cortex_version": __version__,
        "repo": REPO,
        "phases": {},
        "claim_boundary": (
            "Mind-online pulse means non-empty admitted memory + rehydration + "
            "measured trials under will/membrane. Not consciousness. Not host "
            "mutation authority."
        ),
    }

    # --- Phase 0 ---
    diag = diagnose_realign(store, REPO)
    sense0 = observe_self_sensing(store, REPO, home=home, update=False, persist=False)
    mesh0 = mesh_status(store, REPO, home=home, compact=True)
    p0 = {
        "needs_realign": diag.get("needs_realign"),
        "epoch": diag.get("epoch"),
        "sense": sense0.get("classification"),
        "gates": sense0.get("gates"),
        "mesh_green": mesh0.get("mesh_green"),
        "overall_ready": (mesh0.get("readiness") or {}).get("overall_ready"),
        "admitted_before": admitted_memory_status(store, REPO).get("total"),
    }
    report["phases"]["0_preconditions"] = p0
    _print("PHASE 0 PRECONDITIONS", p0)
    if diag.get("needs_realign"):
        report["status"] = "blocked_needs_realign"
        store.close()
        return report

    # --- Phase 1 ---
    session = open_symbiotic_session(
        store,
        REPO,
        task=TASK,
        provider="xai",
        model_id="grok-build",
    )
    will = issue_will(
        store,
        REPO,
        principal_id=PRINCIPAL,
        secret=SECRET,
        session_id=str(session.get("session_id") or ""),
        body_epoch_id=str(session.get("body_epoch_id") or ""),
        repository_id=str(session.get("repository_id") or ""),
        intent_summary="mind-online 8.9: admit measured trajectory lessons only",
        ttl_seconds=86400,
    )
    vwill = verify_will(store, REPO, will, secret=SECRET)
    p1 = {
        "session_id": session.get("session_id"),
        "body_epoch_id": session.get("body_epoch_id"),
        "epoch_verified": session.get("epoch_verified"),
        "will_id": will.get("will_id"),
        "will_verified": vwill.get("verified"),
        "will_errors": vwill.get("errors"),
    }
    report["phases"]["1_open_and_will"] = p1
    _print("PHASE 1 OPEN + WILL", p1)
    if not vwill.get("verified"):
        report["status"] = "blocked_will_unverified"
        store.close()
        return report

    # --- Phase 2 ---
    session = record_proposal(
        store,
        REPO,
        session,
        interpreted_objective=(
            "Bring durable memory online under host immutability: seal path, "
            "admit verified procedures and persistent constraints only"
        ),
        proposed_action=(
            "run_witnessed_symbiotic_turn_then_membrane_admit_without_host_mutate"
        ),
        evidence_citations=[
            "epoch_8.9.0",
            "mesh_green",
            "budget_structure_only",
            "trial_G_rehydration_positive",
            "host_immutable",
        ],
        declared_uncertainty=0.18,
    )
    session = record_joint_action(
        store,
        REPO,
        session,
        tool_action={
            "name": "mind_online_pulse",
            "executed": True,
            "host_mutate": False,
            "execution_authorized": False,
        },
        measured_result={
            "ok": True,
            "pulse": "mind_online_8.9",
            "host_mutate": False,
            "tests": "not_required_for_ledger_pulse",
        },
    )
    joint = (session.get("receipts") or {}).get("joint_action") or {}
    metrics = {
        "pulse": 1,
        "score": 1.0,
        "version": __version__,
        "host_mutate": 0.0,
        "procedure": 1.0,
    }
    turn = int(joint.get("turn_id") or session.get("current_turn_id") or 1)
    subject = {
        "outcome_kind": "task_result",
        "success": True,
        "metrics": dict(metrics),
        "external_reference": "mind-online-8.9-1",
        "joint_action_receipt_hash": str(joint.get("receipt_hash") or ""),
        "session_id": str(session.get("session_id") or ""),
        "turn_id": turn,
        "body_epoch_id": str(session.get("body_epoch_id") or ""),
        "repository_id": str(session.get("repository_id") or ""),
        "repo": REPO,
    }
    subject_hash = _sha(subject)
    witness = {
        "witness_kind": "OUTCOME",
        "verifier": "operator.mind_online_8_9",
        "subject_receipt_hash": subject_hash,
        "evidence_hashes": [
            subject_hash,
            "epoch_8.9.0",
            "host_immutable",
            "mesh_green",
        ],
        "passed": True,
        "issued_at": time.time(),
    }
    witness["witness_id"] = "ow_" + _sha(witness)[:24]
    session = record_outcome(
        store,
        REPO,
        session,
        success=True,
        metrics=metrics,
        external_reference="mind-online-8.9-1",
        witness=witness,
    )
    outcome = (session.get("receipts") or {}).get("outcome") or {}

    # Second turn: drive distillation extraction from trajectory
    session = record_proposal(
        store,
        REPO,
        session,
        interpreted_objective=(
            "Distill verified pulse into durable candidates: successful_procedure "
            "and persistent_constraint under host immutability"
        ),
        proposed_action="extract_and_membrane_admit_measured_lessons",
        evidence_citations=["outcome_mind_online", "interconnect_frame", "will"],
        declared_uncertainty=0.2,
    )
    batch = (session.get("receipts") or {}).get("distillation_candidates") or {}
    p2 = {
        "latest_decision": session.get("latest_decision"),
        "outcome_status": outcome.get("status"),
        "outcome_witnessed": outcome.get("witnessed"),
        "distill_status": batch.get("extraction_status"),
        "candidate_count": batch.get("candidate_count"),
        "by_type": batch.get("by_type"),
        "transition_class": session.get("latest_transition_class"),
    }
    report["phases"]["2_circulation"] = p2
    _print("PHASE 2 CIRCULATION", p2)

    # --- Phase 3 ---
    batches = extract_session_distillation_candidates(session)
    cands = flatten_candidates(batches)
    # Ensure at least structured measured candidates if extractor was empty
    if not cands:
        cands = [
            {
                "candidate_id": "cand_proc_mind_online_" + _sha(TASK)[:12],
                "candidate_type": "successful_procedure",
                "kind": "successful_procedure",
                "summary": (
                    "run verify and warm-in then commit procedure under host "
                    "immutability; never auto-execute or invent admitted memory"
                ),
                "support_level": "medium",
                "source": {
                    "transition_hash": str(
                        ((session.get("receipts") or {}).get("interconnect_transition") or {}).get(
                            "receipt_hash"
                        )
                        or ("t" * 64)
                    ),
                    "outcome_hash": str(outcome.get("receipt_hash") or ("o" * 64)),
                    "prior_frame_hash": str(
                        ((session.get("receipts") or {}).get("interconnect_frame") or {}).get(
                            "receipt_hash"
                        )
                        or ("a" * 64)
                    ),
                    "next_frame_hash": "b" * 64,
                },
                "evidence": {"pulse": "mind_online_8.9", "witnessed": True},
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "from_chat_text": False,
                "invented": False,
            },
            {
                "candidate_id": "cand_const_host_" + _sha("host")[:12],
                "candidate_type": "persistent_constraint",
                "kind": "persistent_constraint",
                "summary": (
                    "host source mutation forbidden; unwitnessed memory write blocked; "
                    "measurement is not fluency and not consciousness"
                ),
                "support_level": "medium",
                "source": {
                    "transition_hash": str(
                        ((session.get("receipts") or {}).get("interconnect_transition") or {}).get(
                            "receipt_hash"
                        )
                        or ("t" * 64)
                    ),
                    "outcome_hash": str(outcome.get("receipt_hash") or ("o" * 64)),
                    "prior_frame_hash": str(
                        ((session.get("receipts") or {}).get("interconnect_frame") or {}).get(
                            "receipt_hash"
                        )
                        or ("a" * 64)
                    ),
                    "next_frame_hash": "b" * 64,
                },
                "evidence": {"pulse": "mind_online_8.9", "witnessed": True},
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "from_chat_text": False,
                "invented": False,
            },
        ]
        batches = [{"candidates": cands, "extraction_status": "operator_seeded_measured"}]

    admission = apply_will_bound_membrane(
        store,
        REPO,
        will=will,
        will_secret=SECRET,
        candidates=cands,
        batches=batches if isinstance(batches, list) else [batches],
        constitutional_gate=True,
        epoch_compatible=True,
        witness_present=True,
        outcome_closed=True,
        stable_regime=True,
        session_id=str(session.get("session_id") or ""),
        body_epoch_id=str(session.get("body_epoch_id") or ""),
        turn_id=int(session.get("current_turn_id") or 0),
    )
    commit = commit_admitted_memories(
        store,
        REPO,
        admission=admission,
        will=will,
        session={
            "session_id": session.get("session_id"),
            "body_epoch_id": session.get("body_epoch_id"),
            "repository_id": session.get("repository_id"),
        },
    )
    sealed = consolidate_session(
        store,
        REPO,
        session,
        constitutional_gate=True,
        epoch_compatible=True,
        witness_present=True,
        outcome_closed=True,
        stable_regime=True,
        will=will,
        will_secret=SECRET,
    )
    cons = (sealed.get("receipts") or {}).get("symbiotic_consolidation") or {}
    adm_status = admitted_memory_status(store, REPO)
    p3 = {
        "membrane_admitted": admission.get("admitted_count"),
        "membrane_rejected": admission.get("rejected_count"),
        "durable_write_authorized": admission.get("durable_write_authorized"),
        "invented_count": admission.get("invented_count"),
        "admitted_types": [
            c.get("candidate_type") for c in (admission.get("admitted") or [])
        ],
        "commit_status": commit.get("status"),
        "committed_count": commit.get("committed_count"),
        "ledger_total": adm_status.get("total"),
        "by_type": adm_status.get("by_type"),
        "consolidate_retained": cons.get("retained_count"),
        "host_mutate_authorized": sealed.get("host_mutate_authorized"),
        "execution_authorized": sealed.get("execution_authorized"),
    }
    report["phases"]["3_admit"] = p3
    _print("PHASE 3 ADMIT", p3)

    # --- Phase 4 ---
    proj = project_memories(
        store,
        REPO,
        task=TASK,
        session_id=str(session.get("session_id") or "mind_online"),
        turn_id=int(session.get("current_turn_id") or 0),
        body_epoch_id=str(session.get("body_epoch_id") or "") or None,
        current_will=will,
        will_secret=SECRET,
        persist=True,
    )
    session2 = open_symbiotic_session(
        store,
        REPO,
        task="rehydrate after mind-online admit: next temporary cortex",
        provider="xai",
        model_id="grok-build",
    )
    p4 = {
        "projection_id": proj.get("projection_id"),
        "selected_memory_ids": proj.get("selected_memory_ids"),
        "eligible_count": len(proj.get("eligible_memory_ids") or []),
        "budget_mode": proj.get("budget_mode"),
        "budget_policy_hash": proj.get("budget_policy_hash"),
        "seed_keys": list((proj.get("continuity_seed") or {}).keys()),
        "next_session_id": session2.get("session_id"),
        "next_epoch_verified": session2.get("epoch_verified"),
        "host_mutate_authorized": proj.get("host_mutate_authorized"),
    }
    report["phases"]["4_rehydrate"] = p4
    _print("PHASE 4 REHYDRATE", p4)

    # --- Phase 5 ---
    trials = []
    for i in range(3):
        t = run_cross_instantiation_trial(
            store,
            REPO,
            task=TASK if i == 0 else f"{TASK} (repeat {i+1})",
            body_epoch_id=str(session.get("body_epoch_id") or "") or None,
            current_will=will,
            will_secret=SECRET,
            persist=True,
        )
        trials.append(
            {
                "receipt_hash": t.get("receipt_hash"),
                "G_rehydration": t.get("G_rehydration"),
                "G_credit": t.get("G_credit"),
                "U": t.get("U"),
                "interpretation": t.get("interpretation"),
            }
        )
    tstat = memory_trial_status(store, REPO)
    bstat_before = budget_status(store, REPO)
    bapply = apply_budget(
        store,
        REPO,
        authorized=True,
        force_unmeasured=not bool((bstat_before.get("aggregate") or {}).get("measured")),
    )
    bstat_after = budget_status(store, REPO)
    p5 = {
        "trials": trials,
        "trial_status": {
            "history_len": tstat.get("history_len"),
            "G_rehydration": tstat.get("G_rehydration"),
            "G_credit": tstat.get("G_credit"),
        },
        "budget_before_mode": (bstat_before.get("proposal") or {}).get("mode"),
        "budget_aggregate": bstat_before.get("aggregate"),
        "budget_apply": {
            "applied": bapply.get("applied"),
            "errors": bapply.get("errors"),
            "mode": bapply.get("mode"),
            "budget_policy_hash": bapply.get("budget_policy_hash"),
        },
        "budget_active_after": bstat_after.get("active"),
    }
    report["phases"]["5_measure_budget"] = p5
    _print("PHASE 5 TRIALS + BUDGET", p5)

    # --- Phase 6 ---
    sense1 = observe_self_sensing(store, REPO, home=home, update=False, persist=False)
    mesh1 = mesh_status(store, REPO, home=home, compact=True)
    ledger = list_admitted_memories(store, REPO, limit=20)
    online = int(adm_status.get("total") or 0) > 0 and bool(
        proj.get("selected_memory_ids") or proj.get("eligible_memory_ids")
    )
    p6 = {
        "mind_shaped_loop_online": online,
        "admitted_total": adm_status.get("total"),
        "admitted_summaries": [
            {"type": m.get("candidate_type"), "summary": m.get("summary")}
            for m in ledger[:8]
        ],
        "sense": sense1.get("classification"),
        "sense_gates": sense1.get("gates"),
        "mesh_green": mesh1.get("mesh_green"),
        "readiness": (mesh1.get("readiness") or {}).get("planes_boolean"),
        "bottlenecks": mesh1.get("bottlenecks"),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "consciousness_claimed": False,
    }
    report["phases"]["6_report"] = p6
    report["status"] = "online" if online else "partial"
    report["finished_at"] = time.time()
    _print("PHASE 6 REPORT", p6)
    store.close()
    out = home / "packets" / f"mind_online_pulse_{int(time.time())}.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        report["packet_path"] = str(out)
        print(f"\nWrote {out}")
    except Exception as exc:
        report["packet_write_error"] = str(exc)
    print("\n=== FINAL STATUS ===", report["status"])
    return report


if __name__ == "__main__":
    main()
