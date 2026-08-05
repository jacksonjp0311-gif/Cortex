"""v8.8 — Cross-instantiation memory trials (matched arms A–E).

Measures whether governed rehydration and memory-use feedback improve a *new*
temporary cortex relative to raw repository / summary baselines.

Arms:
  A — new AI + raw repository signals only
  B — new AI + ordinary summary
  C — new AI + unfiltered admitted memories
  D — new AI + governed memory projection
  E — new AI + projection + memory-use feedback

Gains (utilities U on [0,1]):
  G_rehydration = U_D - U_A
  G_credit      = U_E - U_D

Never mutates host, never auto-executes, never invents admitted memories.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping, Sequence
from typing import Any

from . import __version__
from .admitted_memory import list_admitted_memories
from .memory_credit import issue_memory_credit, record_memory_use
from .memory_projection import project_memories
from .memory_state import current_memory_state

SCHEMA = "cortex-memory-trial/1.0"
VERSION = "8.8.0"
GLYPH = "⧉⚖↗"
CLAIM_BOUNDARY = (
    "Cross-instantiation memory trials measure orientation and constraint "
    "retention under matched arms. They do not prove consciousness, authorize "
    "host mutation, or promote memories. U scores are deterministic probe "
    "utilities on declared ground truth — not model fluency."
)

ARMS = ("A", "B", "C", "D", "E")

DEFAULT_PROBE = {
    "task": "run tests then commit procedure under host immutability",
    "required_constraint_substrings": [
        "host",
        "mutation",
        "immutable",
        "unwitnessed",
        "fluency",
    ],
    "required_procedure_substrings": ["test", "commit", "procedure"],
    "forbidden_as_fact_states": ["superseded", "epoch_stale", "revoked", "quarantined"],
}


def _canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _summarize_memories(memories: Sequence[Mapping[str, Any]], *, limit: int = 20) -> str:
    parts: list[str] = []
    for mem in list(memories)[:limit]:
        parts.append(
            f"[{mem.get('candidate_type')}] {mem.get('summary')}"
        )
    return "\n".join(parts)


def _ordinary_summary(memories: Sequence[Mapping[str, Any]]) -> str:
    """Lossy human-style summary — not governed, may mix types."""
    if not memories:
        return "No prior admitted lessons. Work carefully on the repository."
    types: dict[str, int] = {}
    for mem in memories:
        t = str(mem.get("candidate_type") or "unknown")
        types[t] = types.get(t, 0) + 1
    lines = ["Ordinary summary of prior admitted lessons:"]
    for t, n in sorted(types.items()):
        lines.append(f"- {n}× {t}")
    # include a few raw lines without eligibility
    for mem in list(memories)[:5]:
        lines.append(f"* {mem.get('summary')}")
    return "\n".join(lines)


def _raw_repository_context(store: Any, repo: str) -> str:
    """Arm A: repository identity + non-memory surfaces only."""
    repository = store.repo(repo)
    repo_id = None
    bootstrap = None
    if repository is not None:
        try:
            repo_id = repository["repository_id"]
            bootstrap = repository["bootstrap_status"]
        except (KeyError, TypeError, IndexError):
            repo_id = getattr(repository, "repository_id", None)
            bootstrap = getattr(repository, "bootstrap_status", None)
    bits = [
        f"repo={repo}",
        f"repository_id={repo_id}",
        f"bootstrap={bootstrap}",
    ]
    for key in (
        f"source_admission_latest:{repo}",
        f"self_sensing_latest:{repo}",
    ):
        val = store.get_setting(key, None)
        if isinstance(val, Mapping):
            bits.append(f"{key.split(':')[0]}={val.get('status') or val.get('classification')}")
    return "\n".join(bits)


def build_arm_context(
    store: Any,
    repo: str,
    arm: str,
    *,
    task: str,
    body_epoch_id: str | None = None,
    current_will: Mapping[str, Any] | None = None,
    will_secret: str | None = None,
    prior_use_receipts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Construct the context package for one arm (no model call)."""
    arm = str(arm).upper()
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    memories = list_admitted_memories(store, repo, limit=5000)
    package: dict[str, Any] = {
        "arm": arm,
        "task": task,
        "memory_ids": [],
        "text": "",
        "projection_hash": None,
        "filtered": False,
        "includes_use_feedback": False,
    }

    if arm == "A":
        package["text"] = _raw_repository_context(store, repo)
        package["memory_ids"] = []
    elif arm == "B":
        package["text"] = _ordinary_summary(memories)
        package["memory_ids"] = [str(m.get("memory_id")) for m in memories[:5]]
    elif arm == "C":
        # Unfiltered admitted ledger — includes stale/superseded as plain text.
        package["text"] = _summarize_memories(memories, limit=50)
        package["memory_ids"] = [str(m.get("memory_id")) for m in memories]
        package["filtered"] = False
    elif arm in {"D", "E"}:
        proj = project_memories(
            store,
            repo,
            task=task,
            session_id=f"trial_{arm.lower()}",
            turn_id=0,
            body_epoch_id=body_epoch_id,
            current_will=current_will,
            will_secret=will_secret,
            max_memories=12,
            persist=False,
        )
        package["text"] = _canonical(proj.get("continuity_seed") or proj.get("selected"))
        package["memory_ids"] = list(proj.get("selected_memory_ids") or [])
        package["projection_hash"] = proj.get("receipt_hash")
        package["projection"] = proj
        package["filtered"] = True
        if arm == "E":
            package["includes_use_feedback"] = True
            feedback_lines: list[str] = []
            for use in prior_use_receipts or ():
                if not isinstance(use, Mapping):
                    continue
                feedback_lines.append(
                    f"prior_use cited={use.get('memory_ids_cited_by_proposal')} "
                    f"success={use.get('success')} witnessed={use.get('witnessed')}"
                )
            # synthetic credit tips from prior uses
            for mid in package["memory_ids"]:
                tip = current_memory_state(store, repo, str(mid))
                feedback_lines.append(
                    f"memory {mid} state={tip.get('state')}"
                )
            package["text"] = package["text"] + "\n" + "\n".join(feedback_lines)
    return package


def score_arm_package(
    package: Mapping[str, Any],
    *,
    probe: Mapping[str, Any] | None = None,
    ground_truth_memories: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Deterministic utility probe against declared ground truth substrings."""
    probe = dict(probe or DEFAULT_PROBE)
    text = str(package.get("text") or "").lower()
    mem_ids = [str(x) for x in (package.get("memory_ids") or ())]
    arm = str(package.get("arm") or "")

    req_c = [str(s).lower() for s in (probe.get("required_constraint_substrings") or ())]
    req_p = [str(s).lower() for s in (probe.get("required_procedure_substrings") or ())]
    forbidden_states = set(probe.get("forbidden_as_fact_states") or ())

    hit_c = sum(1 for s in req_c if s in text)
    hit_p = sum(1 for s in req_p if s in text)
    constraint_retention = hit_c / max(1, len(req_c))
    procedure_retention = hit_p / max(1, len(req_p))

    # inappropriate use: unfiltered arms dump superseded/stale as if active
    inappropriate = 0.0
    if ground_truth_memories and arm in {"B", "C"}:
        bad = 0
        total = 0
        for mem in ground_truth_memories:
            total += 1
            summary = str(mem.get("summary") or "").lower()
            state = str(mem.get("_trial_state") or mem.get("current_state") or "active")
            # match on a stable snippet, not only the first 40 chars
            snippet = summary[:48] if len(summary) >= 12 else summary
            if snippet and snippet in text and state in forbidden_states:
                bad += 1
        inappropriate = bad / max(1, total)
        if arm == "C" and bad:
            # unfiltered ledger pays full cost of each stale presentation
            inappropriate = min(1.0, inappropriate * 1.5)

    # orientation: denser relevant hits with less bulk
    bulk = max(1, len(text) // 80)
    orientation = _clip01((constraint_retention + procedure_retention) / 2.0 * (1.0 + 1.0 / bulk))
    # token cost proxy
    token_cost = _clip01(len(text) / 4000.0)
    # task success proxy: both families partially retained
    task_success = _clip01(0.5 * constraint_retention + 0.5 * procedure_retention)
    # evidence precision: selected ids only when filtered
    precision = 1.0 if package.get("filtered") else _clip01(1.0 - 0.3 * inappropriate)

    # composite U in [0,1]
    U = _clip01(
        0.28 * orientation
        + 0.22 * constraint_retention
        + 0.18 * task_success
        + 0.18 * precision
        + 0.10 * procedure_retention
        - 0.12 * token_cost
        - 0.35 * inappropriate
    )

    return {
        "arm": arm,
        "U": round(U, 6),
        "metrics": {
            "orientation": round(orientation, 6),
            "constraint_retention": round(constraint_retention, 6),
            "procedure_retention": round(procedure_retention, 6),
            "task_success": round(task_success, 6),
            "evidence_precision": round(precision, 6),
            "token_cost": round(token_cost, 6),
            "inappropriate_memory_use": round(inappropriate, 6),
            "memory_count": len(mem_ids),
            "text_chars": len(text),
        },
        "memory_ids": mem_ids,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def run_cross_instantiation_trial(
    store: Any,
    repo: str,
    *,
    task: str | None = None,
    body_epoch_id: str | None = None,
    current_will: Mapping[str, Any] | None = None,
    will_secret: str | None = None,
    probe: Mapping[str, Any] | None = None,
    simulate_e_feedback: bool = True,
    persist: bool = True,
) -> dict[str, Any]:
    """Run matched arms A–E and compute G_rehydration and G_credit."""
    probe = dict(probe or DEFAULT_PROBE)
    task = str(task or probe.get("task") or DEFAULT_PROBE["task"])
    will = current_will or store.get_setting(f"will_latest:{repo}", None) or {}

    # Annotate memories with current state for arm-C inappropriate-use scoring
    memories = list_admitted_memories(store, repo, limit=5000)
    annotated: list[dict[str, Any]] = []
    for mem in memories:
        row = dict(mem)
        tip = current_memory_state(store, repo, str(mem.get("memory_id") or ""))
        row["_trial_state"] = tip.get("state")
        annotated.append(row)

    # Prior use feedback for arm E: optionally simulate one use on D projection
    prior_uses: list[dict[str, Any]] = []
    if simulate_e_feedback:
        d_ctx = build_arm_context(
            store,
            repo,
            "D",
            task=task,
            body_epoch_id=body_epoch_id,
            current_will=will if will.get("receipt_hash") else None,
            will_secret=will_secret,
        )
        proj = d_ctx.get("projection") or {}
        if proj.get("receipt_hash"):
            use = record_memory_use(
                store,
                repo,
                projection=proj,
                proposal={
                    "receipt_hash": "trial_prop_" + _sha(task)[:16],
                    "evidence_citations": list(proj.get("selected_memory_ids") or ())[:3],
                    "interpreted_objective": task,
                },
                outcome={
                    "receipt_hash": "trial_out_" + _sha(task)[:16],
                    "success": True,
                    "witnessed": True,
                },
                memory_ids_cited=list(proj.get("selected_memory_ids") or ())[:3],
                persist=False,
            )
            prior_uses.append(use)
            for mid in list(proj.get("selected_memory_ids") or ())[:3]:
                issue_memory_credit(
                    store,
                    repo,
                    memory_id=str(mid),
                    use_receipt=use,
                    persist=False,
                )

    arm_scores: dict[str, Any] = {}
    arm_packages: dict[str, Any] = {}
    for arm in ARMS:
        package = build_arm_context(
            store,
            repo,
            arm,
            task=task,
            body_epoch_id=body_epoch_id,
            current_will=will if will.get("receipt_hash") else None,
            will_secret=will_secret,
            prior_use_receipts=prior_uses if arm == "E" else None,
        )
        score = score_arm_package(
            package, probe=probe, ground_truth_memories=annotated
        )
        arm_packages[arm] = {
            "arm": arm,
            "memory_ids": package.get("memory_ids"),
            "filtered": package.get("filtered"),
            "projection_hash": package.get("projection_hash"),
            "includes_use_feedback": package.get("includes_use_feedback"),
            "text_digest": _sha(package.get("text") or "")[:24],
            "text_chars": len(str(package.get("text") or "")),
        }
        arm_scores[arm] = score

    u_a = float(arm_scores["A"]["U"])
    u_d = float(arm_scores["D"]["U"])
    u_e = float(arm_scores["E"]["U"])
    g_rehydration = round(u_d - u_a, 6)
    g_credit = round(u_e - u_d, 6)

    material = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "glyph": GLYPH,
        "kind": "memory_cross_instantiation_trial",
        "repo": repo,
        "task": task,
        "task_hash": _sha(task),
        "body_epoch_id": body_epoch_id,
        "current_will_hash": will.get("receipt_hash") if isinstance(will, Mapping) else None,
        "arms": ARMS,
        "arm_packages": arm_packages,
        "arm_scores": {k: v for k, v in arm_scores.items()},
        "U": {arm: arm_scores[arm]["U"] for arm in ARMS},
        "G_rehydration": g_rehydration,
        "G_credit": g_credit,
        "formulas": {
            "G_rehydration": "U_D - U_A",
            "G_credit": "U_E - U_D",
        },
        "probe": {
            "required_constraint_substrings": probe.get("required_constraint_substrings"),
            "required_procedure_substrings": probe.get("required_procedure_substrings"),
        },
        "interpretation": {
            "rehydration_helps": g_rehydration > 0,
            "credit_helps": g_credit > 0,
            "governed_beats_unfiltered": arm_scores["D"]["U"] >= arm_scores["C"]["U"],
            "summary_beats_raw": arm_scores["B"]["U"] >= arm_scores["A"]["U"],
        },
        "advisory_only": True,
        "policy_effect": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "learning_authorized": False,
        "claim_boundary": CLAIM_BOUNDARY,
        "cortex_version": __version__,
    }
    event_id = "evt_" + _sha(
        {"kind": "memory_trial", "repo": repo, "task": material["task_hash"], "t": time.time()}
    )[:24]
    receipt_hash = _sha({**material, "event_id": event_id})
    receipt = {
        **material,
        "event_id": event_id,
        "receipt_hash": receipt_hash,
        "created_at": time.time(),
    }
    if persist:
        try:
            store.append_memory_trial_receipt(repo, receipt)
        except Exception:
            pass
        store.set_setting(f"memory_trial_latest:{repo}", receipt)
        history = list(store.get_setting(f"memory_trial_history:{repo}", []) or [])
        history.append(
            {
                "receipt_hash": receipt_hash,
                "G_rehydration": g_rehydration,
                "G_credit": g_credit,
                "U": material["U"],
                "created_at": receipt["created_at"],
            }
        )
        store.set_setting(f"memory_trial_history:{repo}", history[-32:])
        try:
            from .memory_budget import refresh_after_trial

            refresh_after_trial(store, repo)
        except Exception:
            pass
    return receipt


def memory_trial_status(store: Any, repo: str) -> dict[str, Any]:
    latest = store.get_setting(f"memory_trial_latest:{repo}", None) or {}
    history = list(store.get_setting(f"memory_trial_history:{repo}", []) or [])
    return {
        "schema_version": "cortex-memory-trial-status/1.0",
        "version": VERSION,
        "repo": repo,
        "latest_receipt_hash": latest.get("receipt_hash"),
        "G_rehydration": latest.get("G_rehydration"),
        "G_credit": latest.get("G_credit"),
        "U": latest.get("U"),
        "history_len": len(history),
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
    }


__all__ = [
    "ARMS",
    "CLAIM_BOUNDARY",
    "DEFAULT_PROBE",
    "SCHEMA",
    "VERSION",
    "build_arm_context",
    "memory_trial_status",
    "run_cross_instantiation_trial",
    "score_arm_package",
]
