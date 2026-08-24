"""v7.1.1 Authorized evidence-refresh edge — G_evidence only, audited path.

observe_drift → authorize_evidence_refresh → refresh_evidence_only
→ recompute_epoch/controller → select_path

Never issues adaptive authority. Never seals host mutation.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

SCHEMA = "cortex-evidence-refresh-edge/1.0"
GLYPH = "◇E"

CLAIM = (
    "Evidence refresh is an explicit constitutional edge on G_evidence. "
    "It is not adaptive learning and not host mutation authority."
)

EDGE_STEPS = (
    "observe_drift",
    "authorize_evidence_refresh",
    "refresh_evidence_only",
    "recompute_epoch_controller",
    "select_path",
)


def authorize_evidence_refresh(
    *,
    refresh_mode: str,
    manifest_current: bool,
    force: bool = False,
) -> dict[str, Any]:
    """Decide whether the evidence-refresh edge may fire."""
    mode = (refresh_mode or "never").casefold().strip()
    if mode == "never" and not force:
        return {
            "authorized": False,
            "reason": "refresh_mode_never",
            "edge": "EVIDENCE_REFRESH",
        }
    if mode == "always" or force:
        return {
            "authorized": True,
            "reason": "refresh_always_or_force",
            "edge": "EVIDENCE_REFRESH",
        }
    if mode == "auto" and not manifest_current:
        return {
            "authorized": True,
            "reason": "manifest_drift_detected",
            "edge": "EVIDENCE_REFRESH",
        }
    return {
        "authorized": False,
        "reason": "manifest_current_no_refresh",
        "edge": "EVIDENCE_REFRESH",
    }


def run_evidence_refresh_edge(
    home: Path,
    store: Any,
    repo: str,
    *,
    root: Path,
    config: Any,
    refresh_mode: str = "auto",
    governor: Any | None = None,
    memory_controller: str | None = None,
    force_evidence_baseline: bool = False,
    force: bool = False,
    observed_manifest: str | None = None,
) -> dict[str, Any]:
    """Execute the audited evidence-refresh edge. Mutates evidence plane only."""
    from .epoch import compute_body_epoch, ensure_current_epoch, observe_current_epoch
    from .graph import resolve_graph
    from .indexer import current_manifest_hash, index_repository
    from .telemetry import ingest_git
    from .verify import verify_repository

    t0 = time.time()
    steps_done: list[str] = []
    audit: dict[str, Any] = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "edge": "EVIDENCE_REFRESH",
        "steps": list(EDGE_STEPS),
        "steps_completed": steps_done,
        "claim_boundary": CLAIM,
    }

    # 1. observe_drift
    # The activation caller already performed this exact pre-refresh scan. It
    # may provide that observation as an optimization; it is never reused as
    # the post-activation host-immutability measurement.
    observed = observed_manifest or current_manifest_hash(root, config)
    row = store.repo(repo)
    stored = (row["manifest_hash"] or "") if row else ""
    manifest_current = observed == stored and bool(stored)
    drift = {
        "manifest_current": manifest_current,
        "stored_manifest_prefix": stored[:16] if stored else "",
        "observed_manifest_prefix": observed[:16] if observed else "",
    }
    steps_done.append("observe_drift")
    audit["observe_drift"] = drift

    # 2. authorize
    auth = authorize_evidence_refresh(
        refresh_mode=refresh_mode,
        manifest_current=manifest_current,
        force=force,
    )
    steps_done.append("authorize_evidence_refresh")
    audit["authorize"] = auth
    if not auth.get("authorized"):
        audit["ok"] = False
        audit["refreshed"] = False
        audit["selected_path"] = "skip_refresh"
        audit["elapsed_s"] = round(time.time() - t0, 4)
        audit["receipt_hash"] = _receipt(audit)
        return audit

    # 3. refresh_evidence_only
    refresh_result: dict[str, Any]
    try:
        refresh_result = index_repository(store, repo, config, force=False)
        resolve_graph(store, repo)
        try:
            ingest_git(store, repo, root, config.git_commit_limit)
        except Exception as exc:
            refresh_result["git_ingest_error"] = f"{type(exc).__name__}:{exc}"
        steps_done.append("refresh_evidence_only")
        audit["refresh_evidence_only"] = {
            "ok": True,
            "indexed_files_this_run": refresh_result.get("indexed_files_this_run"),
            "unchanged_files": refresh_result.get("unchanged_files"),
        }
        audit["refresh_result"] = refresh_result
    except Exception as exc:
        steps_done.append("refresh_evidence_only")
        audit["refresh_evidence_only"] = {
            "ok": False,
            "error": f"{type(exc).__name__}:{exc}",
        }
        audit["ok"] = False
        audit["refreshed"] = False
        audit["selected_path"] = "refresh_failed"
        audit["elapsed_s"] = round(time.time() - t0, 4)
        audit["receipt_hash"] = _receipt(audit)
        return audit

    # 4. recompute epoch/controller (observe + optional ensure for identity; path select later)
    row = store.repo(repo)
    observed = str(refresh_result.get("manifest_hash") or "")
    if not observed:
        observed = current_manifest_hash(root, config)
    stored = (row["manifest_hash"] or "") if row else ""
    manifest_current = observed == stored and bool(stored)
    epoch_obs = observe_current_epoch(store, repo)
    live = compute_body_epoch(store, repo, transition_reason="post_evidence_refresh")
    controller_resolution: dict[str, Any] = {}
    if governor is not None:
        try:
            from .activation import resolve_activation_controller

            controller_resolution = resolve_activation_controller(
                governor,
                repo,
                memory_controller=memory_controller,
                force_evidence_baseline=force_evidence_baseline,
                manifest_current=manifest_current,
            )
        except Exception as exc:
            controller_resolution = {"error": f"{type(exc).__name__}:{exc}"}
    steps_done.append("recompute_epoch_controller")
    audit["recompute_epoch_controller"] = {
        "manifest_current": manifest_current,
        "epoch_present": epoch_obs.get("present"),
        "epoch_verified": epoch_obs.get("verified"),
        "live_epoch_id": live.epoch_id,
        "controller": controller_resolution.get("controller"),
        "controller_reason": controller_resolution.get("reason"),
    }

    # 5. select_path
    path = "evidence_baseline"
    if controller_resolution.get("controller") == "advanced":
        path = "advanced"
    elif force_evidence_baseline:
        path = "evidence_baseline_forced"
    steps_done.append("select_path")
    audit["select_path"] = path
    audit["selected_path"] = path
    audit["controller_resolution"] = controller_resolution
    audit["ok"] = True
    audit["refreshed"] = True
    audit["refresh_result"] = {
        k: refresh_result.get(k)
        for k in (
            "indexed_files_this_run",
            "unchanged_files",
            "manifest_hash",
            "error",
        )
        if k in refresh_result or refresh_result.get(k) is not None
    }
    audit["manifest_current"] = manifest_current
    try:
        cert = verify_repository(
            home,
            store,
            repo,
            config,
            write_certificate=True,
            observed_manifest=observed,
        )
        audit["certificate_status"] = cert.get("status") if isinstance(cert, dict) else None
    except Exception as exc:
        audit["certificate_error"] = f"{type(exc).__name__}:{exc}"
        cert = None
    audit["elapsed_s"] = round(time.time() - t0, 4)
    audit["receipt_hash"] = _receipt(audit)
    # Soft seal epoch after evidence change (identity material) — mutation path explicit
    try:
        sealed = ensure_current_epoch(store, repo, reason="evidence_refresh_edge")
        audit["body_epoch_id"] = sealed.epoch_id
    except Exception as exc:
        audit["epoch_seal_error"] = f"{type(exc).__name__}:{exc}"
    return audit


def _receipt(audit: dict[str, Any]) -> str:
    material = {
        "edge": audit.get("edge"),
        "repo": audit.get("repo"),
        "steps": audit.get("steps_completed"),
        "authorize": (audit.get("authorize") or {}).get("reason"),
        "path": audit.get("selected_path"),
        "manifest_current": audit.get("manifest_current")
        or (audit.get("observe_drift") or {}).get("manifest_current"),
    }
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()
