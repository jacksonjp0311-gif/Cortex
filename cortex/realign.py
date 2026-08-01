"""v7.4 Continuity Realignment — explicit rebind when seal lags the living tree.

Tagline: When the seal lags the living tree, realign explicitly — never silently.

Diagnose (observe-only) → plan → apply (operator-authorized seal + optional field warm).
Never host mutation. Never auto-seal on import or interconnect.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from . import __version__

SCHEMA = "cortex-realign/1.0"
GLYPH = "∿◆"
RECEIPT_SCHEMA = "cortex-realign-receipt/1.0"

CLAIM = (
    "Continuity Realignment is an operator-authorized rebind of body epoch and "
    "optional field warm-in after version or constitutional config drift. "
    "It does not grant host mutation, consciousness, or automatic promotion authority. "
    "Observation never seals; apply requires explicit authorization."
)

CANONICAL = (
    "Cortex may report drift freely. Cortex may seal a new body epoch only when "
    "the operator authorizes realign. No silent seal on interconnect, activate, "
    "or import."
)

# Steps that appear in plans (ordered)
STEP_ORDER = (
    "observe_drift",
    "seal_epoch",
    "bind_phase",
    "field_warm_seed",
    "issue_receipt",
    "verify_mesh",
)


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _receipt_key(repo: str) -> str:
    return f"realign_receipt_latest:{repo}"


def _index_key(repo: str) -> str:
    return f"realign_receipt_index:{repo}"


def diagnose_realign(store: Any, repo: str) -> dict[str, Any]:
    """Observe-only drift diagnosis. Never seals."""
    from .epoch import observe_current_epoch
    from .resonant_frame import baseline_warmup_status, field_report, load_baseline

    obs = observe_current_epoch(store, repo)
    mismatches = list(obs.get("mismatches") or [])
    sealed = obs.get("sealed") or {}
    live = obs.get("live") or {}

    needs_epoch = bool(
        not obs.get("present")
        or obs.get("stale")
        or obs.get("verified") is False
        or mismatches
    )

    field = field_report(store, repo)
    warm = field.get("baseline_warmup") or baseline_warmup_status(load_baseline(store, repo))
    needs_field_warm = not bool(warm.get("baseline_ready"))

    # Mesh-oriented bottlenecks (cheap; no full interconnect reindex if possible)
    bottlenecks: list[str] = []
    if needs_epoch:
        bottlenecks.append("epoch_stale_or_mismatched")
    if needs_field_warm:
        bottlenecks.append("field_baseline_cold")
    if not obs.get("present"):
        bottlenecks.append("body_epoch_missing")

    severity = "ok"
    if needs_epoch and mismatches:
        severity = "high"
    elif needs_epoch:
        severity = "medium"
    elif needs_field_warm:
        severity = "low"

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "version": __version__,
        "observation_only": True,
        "severity": severity,
        "needs_realign": needs_epoch,
        "needs_field_warm": needs_field_warm,
        "bottlenecks": bottlenecks,
        "epoch": {
            "present": obs.get("present"),
            "verified": obs.get("verified"),
            "stale": obs.get("stale"),
            "sealed_epoch_id": (sealed.get("epoch_id") if isinstance(sealed, dict) else None)
            or obs.get("epoch_id"),
            "live_epoch_id": obs.get("live_epoch_id")
            or (live.get("epoch_id") if isinstance(live, dict) else None),
            "sealed_cortex_version": sealed.get("cortex_version")
            if isinstance(sealed, dict)
            else None,
            "live_cortex_version": live.get("cortex_version")
            if isinstance(live, dict)
            else __version__,
            "mismatches": mismatches,
        },
        "field_warmup": warm,
        "recommended_action": (
            "cortex realign apply --repo {repo} --i-authorize-realign".format(repo=repo)
            if needs_epoch
            else (
                "cortex realign warm --repo {repo}".format(repo=repo)
                if needs_field_warm
                else "none — continuity current"
            )
        ),
        "canonical_statement": CANONICAL,
        "claim_boundary": CLAIM,
    }


def plan_realign(store: Any, repo: str, *, warm_field: bool = True) -> dict[str, Any]:
    """Build ordered realign plan from diagnosis (still observe-only)."""
    diag = diagnose_realign(store, repo)
    steps: list[dict[str, Any]] = [
        {
            "id": "observe_drift",
            "required": True,
            "status": "ready",
            "description": "Re-observe sealed vs live epoch (no seal)",
        }
    ]
    if diag["needs_realign"]:
        steps.append(
            {
                "id": "seal_epoch",
                "required": True,
                "status": "pending_authorization",
                "description": "Operator-authorized seal_epoch_transition (parent = current sealed)",
            }
        )
        steps.append(
            {
                "id": "bind_phase",
                "required": True,
                "status": "pending_authorization",
                "description": "Transition phase to QUIESCENT under new epoch",
            }
        )
    else:
        steps.append(
            {
                "id": "seal_epoch",
                "required": False,
                "status": "skip",
                "description": "Epoch already verified — no seal",
            }
        )
    if warm_field and diag.get("needs_field_warm"):
        steps.append(
            {
                "id": "field_warm_seed",
                "required": False,
                "status": "optional",
                "description": "Seed Resonant Frame samples (does not force 16/16)",
            }
        )
    steps.append(
        {
            "id": "issue_receipt",
            "required": True,
            "status": "pending",
            "description": "Hash realign receipt (drift panel + actions)",
        }
    )
    steps.append(
        {
            "id": "verify_mesh",
            "required": False,
            "status": "pending",
            "description": "Re-check epoch_verified for mesh_green path",
        }
    )
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "plan_id": f"plan_{_sha({'repo': repo, 'diag': diag['epoch'], 'v': __version__})[:16]}",
        "diagnosis": diag,
        "steps": steps,
        "authorization_required": bool(diag["needs_realign"]),
        "authorization_flag": "--i-authorize-realign",
        "claim_boundary": CLAIM,
        "observation_only": True,
    }


def apply_realign(
    store: Any,
    repo: str,
    *,
    authorize: bool = False,
    warm_field: bool = True,
    warm_ticks: int = 3,
    reason: str = "continuity_realign_v74",
) -> dict[str, Any]:
    """Execute realign. Seals epoch only if authorize=True and drift present."""
    plan = plan_realign(store, repo, warm_field=warm_field)
    diag = plan["diagnosis"]
    actions: list[dict[str, Any]] = []
    errors: list[str] = []

    if diag["needs_realign"] and not authorize:
        return {
            "ok": False,
            "applied": False,
            "error": "authorization_required",
            "hint": f"python -m cortex realign apply --repo {repo} --i-authorize-realign",
            "plan": plan,
            "claim_boundary": CLAIM,
        }

    # 1 observe
    actions.append({"id": "observe_drift", "ok": True, "detail": diag["epoch"]})

    new_epoch: dict[str, Any] | None = None
    if diag["needs_realign"] and authorize:
        try:
            from .epoch import current_body_epoch, seal_epoch_transition
            from .phases import transition_phase

            parent = current_body_epoch(store, repo)
            ep = seal_epoch_transition(
                store, repo, reason=reason, parent=parent
            )
            new_epoch = ep.to_dict() if hasattr(ep, "to_dict") else dict(ep)
            actions.append(
                {
                    "id": "seal_epoch",
                    "ok": True,
                    "epoch_id": new_epoch.get("epoch_id"),
                    "cortex_version": new_epoch.get("cortex_version"),
                }
            )
            try:
                transition_phase(store, repo, "QUIESCENT", reason=reason)
                actions.append({"id": "bind_phase", "ok": True, "phase": "QUIESCENT"})
            except Exception as exc:
                actions.append(
                    {"id": "bind_phase", "ok": False, "error": f"{type(exc).__name__}:{exc}"}
                )
                errors.append(f"bind_phase:{exc}")
        except Exception as exc:
            actions.append(
                {"id": "seal_epoch", "ok": False, "error": f"{type(exc).__name__}:{exc}"}
            )
            errors.append(f"seal_epoch:{exc}")
            return {
                "ok": False,
                "applied": False,
                "error": f"seal_failed:{exc}",
                "actions": actions,
                "plan": plan,
                "claim_boundary": CLAIM,
            }
    else:
        actions.append({"id": "seal_epoch", "ok": True, "skipped": True})

    # 2 optional field warm seeds
    field_seed: dict[str, Any] | None = None
    if warm_field and diag.get("needs_field_warm"):
        try:
            field_seed = warm_field_baseline(
                store, repo, ticks=max(1, min(8, int(warm_ticks)))
            )
            actions.append(
                {
                    "id": "field_warm_seed",
                    "ok": True,
                    "ticks": field_seed.get("ticks_seeded"),
                    "closed": field_seed.get("closed"),
                }
            )
        except Exception as exc:
            actions.append(
                {
                    "id": "field_warm_seed",
                    "ok": False,
                    "error": f"{type(exc).__name__}:{exc}",
                }
            )
            errors.append(f"field_warm:{exc}")

    # 3 re-diagnose
    post = diagnose_realign(store, repo)
    actions.append(
        {
            "id": "verify_mesh",
            "ok": not post["needs_realign"],
            "epoch_verified": post["epoch"].get("verified"),
            "needs_realign": post["needs_realign"],
        }
    )

    receipt = issue_realign_receipt(
        store,
        repo,
        diagnosis_before=diag,
        diagnosis_after=post,
        actions=actions,
        authorized=bool(authorize),
        new_epoch=new_epoch,
    )
    actions.append({"id": "issue_receipt", "ok": True, "receipt_hash": receipt.get("receipt_hash")})

    return {
        "ok": len(errors) == 0 and not post["needs_realign"],
        "applied": True,
        "authorized": bool(authorize),
        "actions": actions,
        "errors": errors,
        "diagnosis_before": diag,
        "diagnosis_after": post,
        "receipt": receipt,
        "field_warm": field_seed,
        "claim_boundary": CLAIM,
        "next": (
            "interconnect --repo {repo}  # expect epoch bottleneck clear".format(repo=repo)
            if not post["needs_realign"]
            else "inspect errors / re-run diagnose"
        ),
    }


def warm_field_baseline(
    store: Any,
    repo: str,
    *,
    ticks: int = 3,
    task: str = "realign field warm",
) -> dict[str, Any]:
    """Seed a few field ticks + optional close — does not claim full calibration."""
    from .field_channels import collect_activation_channels
    from .resonant_frame import append_field_samples, field_close, field_report, load_field_state

    state = load_field_state(store, repo)
    start_tick = int(state.get("tick") or 0)
    closed_any = False
    for i in range(ticks):
        tick = start_tick + i + 1
        samples = collect_activation_channels(
            store,
            repo,
            tick=tick,
            task=task,
            governor_mode="normal",
        )
        r = append_field_samples(store, repo, samples, reason="realign_warm")
        if r.get("closed"):
            closed_any = True
    # explicit close if buffer has content but not closed
    if not closed_any:
        c = field_close(store, repo)
        closed_any = bool(c.get("closed"))
    report = field_report(store, repo)
    return {
        "ticks_seeded": ticks,
        "closed": closed_any,
        "baseline_frames_display": report.get("baseline_frames_display"),
        "baseline_warmup": report.get("baseline_warmup"),
        "last_classification": report.get("last_classification"),
        "note": "Warm seeds start baseline; 16 epoch-current frames still required for ready",
    }


def issue_realign_receipt(
    store: Any,
    repo: str,
    *,
    diagnosis_before: dict[str, Any],
    diagnosis_after: dict[str, Any],
    actions: list[dict[str, Any]],
    authorized: bool,
    new_epoch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "schema_version": RECEIPT_SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "cortex_version": __version__,
        "authorized": authorized,
        "diagnosis_before": {
            "needs_realign": diagnosis_before.get("needs_realign"),
            "epoch": diagnosis_before.get("epoch"),
            "severity": diagnosis_before.get("severity"),
            "bottlenecks": diagnosis_before.get("bottlenecks"),
        },
        "diagnosis_after": {
            "needs_realign": diagnosis_after.get("needs_realign"),
            "epoch": diagnosis_after.get("epoch"),
            "severity": diagnosis_after.get("severity"),
            "bottlenecks": diagnosis_after.get("bottlenecks"),
        },
        "actions": actions,
        "new_epoch_id": (new_epoch or {}).get("epoch_id"),
        "issued_at": time.time(),
        "claim_boundary": CLAIM,
        "host_mutation": False,
        "auto_seal": False,
    }
    payload["receipt_hash"] = _sha(payload)
    store.set_setting(_receipt_key(repo), payload)
    idx = list(store.get_setting(_index_key(repo), []) or [])
    idx.append(payload["receipt_hash"][:24])
    store.set_setting(_index_key(repo), idx[-32:])
    return payload


def latest_realign_receipt(store: Any, repo: str) -> dict[str, Any] | None:
    return store.get_setting(_receipt_key(repo))


def realign_status(store: Any, repo: str) -> dict[str, Any]:
    diag = diagnose_realign(store, repo)
    latest = latest_realign_receipt(store, repo)
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "diagnosis": diag,
        "latest_receipt": latest,
        "claim_boundary": CLAIM,
    }
