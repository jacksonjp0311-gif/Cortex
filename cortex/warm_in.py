"""v7.6 Verified Operating Regime — Warm-In Closure.

Closes the v7.5 self-sensing milestone:
  diagnose → optional authorized realign → field warm ticks → observer updates
  → replay stability → hashed milestone receipt.

Never: host mutation, silent epoch seal, constitutional bit writes, capability
grant, promote, ARIA auto-exec, consciousness claims.

Epoch seal only when operator passes authorize_realign=True (same bar as v7.4).
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from . import __version__

SCHEMA = "cortex-warm-in/1.0"
GLYPH = "◈∿"
RECEIPT_SCHEMA = "cortex-warm-in-receipt/1.0"

FIELD_TARGET = 16
OBSERVER_TARGET = 16
CHANNEL_MIN = 3
DEFAULT_FIELD_TICKS = 4
DEFAULT_SENSE_UPDATES = 4
MAX_ROUNDS = 8

CLAIM = (
    "Warm-In Protocol brings Resonant Frame and Self-Sensing baselines to a "
    "verified operating regime under explicit operator control for epoch seal. "
    "It does not mutate host source, grant capability, promote learned evidence, "
    "or establish consciousness. Milestone pass is telemetry readiness, not authority."
)

CANONICAL = (
    "A Verified Operating Regime is a warm, replay-stable self-sensing classification "
    "under current epoch and phase binding. It never moves a constitutional bit."
)


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _latest_key(repo: str) -> str:
    return f"warm_in_latest:{repo}"


def _receipt_key(repo: str) -> str:
    return f"warm_in_receipt:{repo}"


def warm_in_status(store: Any, repo: str) -> dict[str, Any]:
    """Observe-only readiness snapshot."""
    from .realign import diagnose_realign
    from .resonant_frame import field_report
    from .self_sensing import milestone_holdout_check, self_sensing_report

    diag = diagnose_realign(store, repo)
    field = field_report(store, repo)
    sense = self_sensing_report(store, repo)
    mile = milestone_holdout_check(store, repo)
    warm = field.get("baseline_warmup") or {}
    latest_sense = sense.get("latest") or {}

    field_frames = int(warm.get("baseline_frames_seen") or 0)
    channels = int(warm.get("baseline_channels_warm") or 0)
    observer_n = int(sense.get("baseline_n_updates") or 0)

    checks = {
        "epoch_current": not bool(diag.get("needs_realign")),
        "field_frames_ge_16": field_frames >= FIELD_TARGET or bool(warm.get("baseline_ready")),
        "channels_ge_3": channels >= CHANNEL_MIN,
        "observer_ge_16": observer_n >= OBSERVER_TARGET,
        "no_false_nominal_unbound": mile.get("checks", {}).get(
            "no_false_healthy_when_unbound", True
        ),
        "advisory_only": True,
    }
    # replay filled by verify path
    ready = all(checks.values()) and not diag.get("needs_realign")

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "ready": ready,
        "checks": checks,
        "epoch": diag.get("epoch"),
        "needs_realign": diag.get("needs_realign"),
        "field_frames_display": warm.get("baseline_frames_display")
        or f"{min(field_frames, FIELD_TARGET)}/{FIELD_TARGET}",
        "observer_baseline_display": f"{min(observer_n, OBSERVER_TARGET)}/{OBSERVER_TARGET}",
        "channels_warm": channels,
        "latest_sense_classification": latest_sense.get("classification"),
        "recommended_action": (
            f"python -m cortex warm-in run --repo {repo} --i-authorize-realign"
            if diag.get("needs_realign")
            else f"python -m cortex warm-in run --repo {repo}"
        ),
        "claim_boundary": CLAIM,
        "canonical_statement": CANONICAL,
        "observation_only": True,
    }


def run_warm_in(
    store: Any,
    repo: str,
    *,
    home: Any | None = None,
    authorize_realign: bool = False,
    field_ticks: int = DEFAULT_FIELD_TICKS,
    sense_updates: int = DEFAULT_SENSE_UPDATES,
    rounds: int = 3,
    close_field: bool = True,
    reason: str = "warm_in_v76",
) -> dict[str, Any]:
    """Execute warm-in protocol. Epoch seal only if authorize_realign and needed."""
    from .realign import apply_realign, diagnose_realign, warm_field_baseline
    from .resonant_frame import field_close, field_report, seed_from_activation
    from .self_sensing import (
        observe_self_sensing,
        verify_observation_replay,
    )

    log: list[dict[str, Any]] = []
    errors: list[str] = []
    before = warm_in_status(store, repo)

    # 1) Continuity gate
    diag = diagnose_realign(store, repo)
    if diag.get("needs_realign"):
        if not authorize_realign:
            return {
                "ok": False,
                "ready": False,
                "error": "realign_authorization_required",
                "hint": (
                    f"python -m cortex warm-in run --repo {repo} --i-authorize-realign"
                ),
                "status_before": before,
                "claim_boundary": CLAIM,
            }
        ar = apply_realign(
            store,
            repo,
            authorize=True,
            warm_field=True,
            warm_ticks=max(2, field_ticks // 2),
            reason=reason,
        )
        log.append({"step": "realign_apply", "ok": ar.get("ok"), "result": {
            "applied": ar.get("applied"),
            "errors": ar.get("errors"),
            "receipt_hash": (ar.get("receipt") or {}).get("receipt_hash"),
        }})
        if not ar.get("ok") and ar.get("errors"):
            errors.extend(ar.get("errors") or [])
    else:
        log.append({"step": "realign_apply", "ok": True, "skipped": True})

    # 2) Field warm rounds
    total_field_ticks = 0
    for rnd in range(max(1, min(MAX_ROUNDS, int(rounds)))):
        try:
            w = warm_field_baseline(
                store,
                repo,
                ticks=max(1, min(8, int(field_ticks))),
                task=f"{reason} field round {rnd+1}",
            )
            total_field_ticks += int(w.get("ticks_seeded") or 0)
            log.append({"step": "field_warm", "round": rnd + 1, "ok": True, "detail": {
                "ticks": w.get("ticks_seeded"),
                "closed": w.get("closed"),
                "display": w.get("baseline_frames_display"),
            }})
        except Exception as exc:
            # fallback: seed_from_activation loop
            try:
                for i in range(max(1, field_ticks)):
                    seed_from_activation(
                        store, repo, task=f"{reason}-{rnd}-{i}", governor_mode="normal"
                    )
                    total_field_ticks += 1
                if close_field:
                    field_close(store, repo)
                log.append({
                    "step": "field_warm",
                    "round": rnd + 1,
                    "ok": True,
                    "fallback": "seed_from_activation",
                })
            except Exception as exc2:
                log.append({
                    "step": "field_warm",
                    "round": rnd + 1,
                    "ok": False,
                    "error": f"{type(exc2).__name__}:{exc2}",
                })
                errors.append(f"field_warm:{exc2}")

        # close frame if buffer pending
        if close_field:
            try:
                field_close(store, repo)
            except Exception:
                pass

        # 3) Self-sensing observer updates (EMA when epoch current)
        for i in range(max(1, min(8, int(sense_updates)))):
            try:
                sense = observe_self_sensing(
                    store,
                    repo,
                    home=home,
                    update=True,
                    persist=True,
                )
                log.append({
                    "step": "sense_update",
                    "round": rnd + 1,
                    "i": i + 1,
                    "ok": True,
                    "classification": sense.get("classification"),
                    "baseline_n": sense.get("baseline_n_updates"),
                    "residual_r": sense.get("residual_r"),
                })
            except Exception as exc:
                log.append({
                    "step": "sense_update",
                    "ok": False,
                    "error": f"{type(exc).__name__}:{exc}",
                })
                errors.append(f"sense:{exc}")

    # 4) Replay stability
    replay = verify_observation_replay(store, repo, home=home)
    log.append({
        "step": "replay",
        "ok": bool(replay.get("stable_across_replay")),
        "detail": {
            "stable": replay.get("stable_across_replay"),
            "classification": (replay.get("first") or {}).get("classification"),
        },
    })

    after = warm_in_status(store, repo)
    after["checks"]["replay_stable"] = bool(replay.get("stable_across_replay"))
    after["ready"] = all(
        v is not False for v in after["checks"].values()
    ) and not after.get("needs_realign")

    # Optional: force close one more frame for receipt material
    try:
        fr = field_report(store, repo)
    except Exception:
        fr = {}

    receipt = issue_warm_in_receipt(
        store,
        repo,
        before=before,
        after=after,
        log=log,
        replay=replay,
        authorized_realign=authorize_realign,
        field_ticks=total_field_ticks,
    )

    return {
        "ok": after.get("ready") and len(errors) == 0,
        "ready": after.get("ready"),
        "repo": repo,
        "status_before": before,
        "status_after": after,
        "log": log,
        "errors": errors,
        "replay": replay,
        "receipt": receipt,
        "field_report_compact": {
            "baseline_frames_display": fr.get("baseline_frames_display"),
            "last_classification": fr.get("last_classification"),
        },
        "claim_boundary": CLAIM,
        "canonical_statement": CANONICAL,
        "next": (
            "python -m cortex sense observe --repo {repo} --json".format(repo=repo)
            if after.get("ready")
            else (
                "re-run warm-in with more --rounds / --field-ticks; "
                "or realign if needs_realign"
            )
        ),
    }


def issue_warm_in_receipt(
    store: Any,
    repo: str,
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    log: list[dict[str, Any]],
    replay: dict[str, Any],
    authorized_realign: bool,
    field_ticks: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": RECEIPT_SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "cortex_version": __version__,
        "ready": bool(after.get("ready")),
        "authorized_realign": authorized_realign,
        "field_ticks": field_ticks,
        "checks_before": before.get("checks"),
        "checks_after": after.get("checks"),
        "field_frames_display": after.get("field_frames_display"),
        "observer_baseline_display": after.get("observer_baseline_display"),
        "latest_sense_classification": after.get("latest_sense_classification"),
        "replay_stable": bool(replay.get("stable_across_replay")),
        "log_digest": _sha([
            {k: e.get(k) for k in ("step", "ok", "round", "classification", "error")}
            for e in log
        ]),
        "issued_at": time.time(),
        "claim_boundary": CLAIM,
        "host_mutation": False,
        "auto_seal": False,
        "authority_satisfying": False,
    }
    payload["receipt_hash"] = _sha(payload)
    payload["receipt_id"] = f"warm_{payload['receipt_hash'][:20]}"
    store.set_setting(_receipt_key(repo), payload)
    store.set_setting(_latest_key(repo), {
        "ready": payload["ready"],
        "receipt_id": payload["receipt_id"],
        "receipt_hash": payload["receipt_hash"],
        "at": payload["issued_at"],
        "classification": after.get("latest_sense_classification"),
    })
    return payload


def latest_warm_in_receipt(store: Any, repo: str) -> dict[str, Any] | None:
    return store.get_setting(_receipt_key(repo))


def verify_warm_in_receipt(store: Any, repo: str) -> dict[str, Any]:
    rec = latest_warm_in_receipt(store, repo)
    if not rec:
        return {"ok": False, "error": "no_receipt", "claim_boundary": CLAIM}
    material = {k: v for k, v in rec.items() if k not in {"receipt_hash", "receipt_id"}}
    # receipt_id derived from hash — recompute without both
    expected = _sha(material)
    # When we hashed, receipt_id wasn't in payload yet — material above excludes both
    # But original hash included everything except receipt_hash before receipt_id was added
    # Re-issue compatible: recompute from same keys as issue
    rebuild = {
        k: rec.get(k)
        for k in (
            "schema_version",
            "glyph",
            "repo",
            "cortex_version",
            "ready",
            "authorized_realign",
            "field_ticks",
            "checks_before",
            "checks_after",
            "field_frames_display",
            "observer_baseline_display",
            "latest_sense_classification",
            "replay_stable",
            "log_digest",
            "issued_at",
            "claim_boundary",
            "host_mutation",
            "auto_seal",
            "authority_satisfying",
        )
    }
    expected = _sha(rebuild)
    ok = expected == rec.get("receipt_hash")
    return {
        "ok": ok,
        "hash_ok": ok,
        "ready": rec.get("ready"),
        "receipt_id": rec.get("receipt_id"),
        "receipt_hash": rec.get("receipt_hash"),
        "recomputed_hash": expected,
        "claim_boundary": CLAIM,
    }
