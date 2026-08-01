"""v7.1.2 Claim receipts — falsifiable stamped promote (and future) claims.

When a live gate allows promote, emit a receipt with:
  body_epoch_id, gate_bits, axis truth sources, phase binding,
  holdout/foreign/witness digests, receipt_hash.

Never grants host mutation authority. Never auto-mutates the host.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from . import __version__

SCHEMA = "cortex-claim-receipt/1.0"
GLYPH = "⌘◆"

CLAIM = (
    "A claim receipt is a falsifiable stamp that a promote (or similar) decision "
    "was allowed under measured geometry, verified epoch, and utility reports. "
    "It is not host mutation authority, not consciousness, and not a universal law."
)

CLAIM_KINDS = frozenset({"promote", "shadow_calibration", "system_learning"})


def _sha(material: Any) -> str:
    return hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()


def _axis_truth_panel(coordinate_detail: dict[str, Any] | None) -> dict[str, Any]:
    detail = coordinate_detail or {}
    panel: dict[str, Any] = {}
    for name in ("evidence", "authority", "epoch", "witness"):
        ax = detail.get(name) or {}
        panel[name] = {
            "valid": ax.get("valid"),
            "gate_eligible": ax.get("gate_eligible"),
            "truth_source": ax.get("truth_source"),
            "reason": ax.get("reason"),
        }
    return panel


def _report_digest(report: dict[str, Any] | None, *, keys: tuple[str, ...]) -> str | None:
    if not report or report.get("error"):
        return None
    slim = {k: report.get(k) for k in keys if k in report}
    # Also pull common nested utility fields
    ab = (report.get("ablations") or {}).get("baseline") or {}
    slim["recall_at_k"] = ab.get("recall_at_k")
    slim["winner"] = report.get("winner")
    slim["gate"] = report.get("gate")
    return _sha(slim)[:32]


def issue_promote_claim_receipt(
    store: Any,
    repo: str,
    *,
    promotion: dict[str, Any],
    geometry: dict[str, Any] | None = None,
    holdout_report: dict[str, Any] | None = None,
    foreign_report: dict[str, Any] | None = None,
    witness_report: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Stamp a promote claim when allow_promote is true; else return denied receipt."""
    geo = geometry or promotion.get("geometry") or {}
    allow = bool(promotion.get("allow_promote"))
    body_epoch_id = (
        promotion.get("body_epoch_id")
        or (geo.get("coordinate_detail") or {}).get("epoch", {}).get("epoch_id")
        or ""
    )
    if not body_epoch_id:
        try:
            from .epoch import observe_current_epoch

            obs = observe_current_epoch(store, repo)
            body_epoch_id = str(obs.get("epoch_id") or obs.get("live_epoch_id") or "")
        except Exception:
            body_epoch_id = ""

    phase_binding = geo.get("phase_binding") or {}
    coord_detail = geo.get("coordinate_detail") or {}
    gate_bits = geo.get("gate_bits") or coord_detail.get("gate_bits") or []
    raw_bits = geo.get("coordinate") or coord_detail.get("bits") or []

    # v7.3 supporting context only — never satisfies e/a/t/w axes
    frame_ctx: dict[str, Any] = {}
    try:
        from .resonant_frame import latest_frame

        lf = latest_frame(store, repo)
        if lf:
            frame_ctx = {
                "frame_id": lf.get("frame_id"),
                "frame_receipt_hash": lf.get("receipt_hash"),
                "frame_classification": lf.get("classification"),
                "frame_body_epoch_id": lf.get("body_epoch_id"),
                "satisfies_axes": False,
            }
    except Exception:
        frame_ctx = {}

    identity = {
        "kind": "promote",
        "repo": repo,
        "body_epoch_id": body_epoch_id,
        "gate_bits": list(gate_bits),
        "resonant_frame_context": frame_ctx,
        "allow_promote": allow,
        "holdout_freeze_id": promotion.get("holdout_freeze_id"),
        "holdout_digest": _report_digest(
            holdout_report, keys=("repo", "winner", "gate", "holdout_freeze_id")
        ),
        "foreign_digest": _report_digest(
            foreign_report, keys=("repo", "winner", "gate")
        ),
        "witness_digest": _report_digest(
            witness_report, keys=("witness_id", "recall_at_k", "suite_kind", "ok")
        ),
        "holdout_recall": promotion.get("holdout_recall"),
        "foreign_recall": promotion.get("foreign_recall"),
        "witness_recall": promotion.get("witness_recall"),
        "emergent_coupling": promotion.get("emergent_coupling"),
        "phase_binding": phase_binding.get("binding"),
        "cortex_version": __version__,
    }
    receipt_hash = _sha(identity)
    claim_id = "claim_" + receipt_hash[:20]

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "claim_id": claim_id,
        "kind": "promote",
        "repo": repo,
        "issued_at": time.time(),
        "status": "allowed" if allow else "denied",
        "body_epoch_id": body_epoch_id,
        "gate_bits": list(gate_bits),
        "raw_bits": list(raw_bits),
        "axis_truth": _axis_truth_panel(coord_detail),
        "phase_binding": phase_binding,
        "utility": {
            "holdout_recall": promotion.get("holdout_recall"),
            "foreign_recall": promotion.get("foreign_recall"),
            "development_transfer_recall": promotion.get("development_transfer_recall"),
            "witness_recall": promotion.get("witness_recall"),
            "train_recall": promotion.get("train_recall"),
            "emergent_coupling": promotion.get("emergent_coupling"),
            "coupling_role": promotion.get("coupling_role"),
            "holdout_freeze_id": promotion.get("holdout_freeze_id"),
            "holdout_digest": identity["holdout_digest"],
            "foreign_digest": identity["foreign_digest"],
            "witness_digest": identity["witness_digest"],
        },
        "geometry": {
            "allowed": geo.get("allowed"),
            "missing_axes": geo.get("missing_axes"),
            "truth_ineligible_axes": geo.get("truth_ineligible_axes"),
            "reasons": geo.get("reasons"),
        },
        # Supporting context only — must match identity hash material in verify
        "resonant_frame_context": frame_ctx,
        "reasons_if_denied": list(promotion.get("reasons_if_denied") or []),
        "cortex_version": __version__,
        "receipt_hash": receipt_hash,
        "claim_boundary": CLAIM,
        "law": (
            "Claim is valid only for this body_epoch_id and these digests. "
            "Re-evaluate after epoch drift. Never host mutation authority."
        ),
    }

    if persist and store is not None:
        try:
            store.set_setting(f"claim_receipt_latest:{repo}", receipt)
            store.set_setting(f"claim_receipt:{repo}:{claim_id}", receipt)
            # append index (bounded)
            idx_key = f"claim_receipt_index:{repo}"
            prev = store.get_setting(idx_key, {}) or {}
            ids = list(prev.get("claim_ids") or [])
            if claim_id not in ids:
                ids.append(claim_id)
            store.set_setting(
                idx_key,
                {
                    "claim_ids": ids[-64:],
                    "latest": claim_id,
                    "updated_at": time.time(),
                },
            )
        except Exception as exc:
            receipt["persist_error"] = f"{type(exc).__name__}:{exc}"

    return receipt


def latest_claim_receipt(store: Any, repo: str) -> dict[str, Any] | None:
    try:
        r = store.get_setting(f"claim_receipt_latest:{repo}", None)
        return r if isinstance(r, dict) else None
    except Exception:
        return None


def verify_claim_receipt(
    store: Any,
    repo: str,
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recompute identity hash and check epoch still verified (observe-only)."""
    rec = receipt or latest_claim_receipt(store, repo)
    if not rec:
        return {"ok": False, "error": "no_claim_receipt", "claim_boundary": CLAIM}

    # Must mirror issue_promote_claim_receipt identity keys exactly
    frame_ctx = rec.get("resonant_frame_context")
    if frame_ctx is None:
        frame_ctx = {}
    identity = {
        "kind": rec.get("kind"),
        "repo": rec.get("repo"),
        "body_epoch_id": rec.get("body_epoch_id"),
        "gate_bits": rec.get("gate_bits"),
        "resonant_frame_context": frame_ctx,
        "allow_promote": rec.get("status") == "allowed",
        "holdout_freeze_id": (rec.get("utility") or {}).get("holdout_freeze_id"),
        "holdout_digest": (rec.get("utility") or {}).get("holdout_digest"),
        "foreign_digest": (rec.get("utility") or {}).get("foreign_digest"),
        "witness_digest": (rec.get("utility") or {}).get("witness_digest"),
        "holdout_recall": (rec.get("utility") or {}).get("holdout_recall"),
        "foreign_recall": (rec.get("utility") or {}).get("foreign_recall"),
        "witness_recall": (rec.get("utility") or {}).get("witness_recall"),
        "emergent_coupling": (rec.get("utility") or {}).get("emergent_coupling"),
        "phase_binding": (rec.get("phase_binding") or {}).get("binding"),
        "cortex_version": rec.get("cortex_version"),
    }
    expected = _sha(identity)
    hash_ok = expected == rec.get("receipt_hash")

    epoch_ok = False
    epoch_mismatches: list[str] = []
    try:
        from .epoch import observe_current_epoch

        obs = observe_current_epoch(store, repo)
        epoch_ok = bool(obs.get("verified")) and (
            obs.get("epoch_id") == rec.get("body_epoch_id")
        )
        if not epoch_ok:
            if obs.get("epoch_id") != rec.get("body_epoch_id"):
                epoch_mismatches.append("body_epoch_id")
            if not obs.get("verified"):
                epoch_mismatches.append("epoch_stale")
    except Exception as exc:
        epoch_mismatches.append(f"epoch_error:{type(exc).__name__}")

    return {
        "ok": hash_ok and epoch_ok and rec.get("status") == "allowed",
        "hash_ok": hash_ok,
        "epoch_ok": epoch_ok,
        "epoch_mismatches": epoch_mismatches,
        "claim_id": rec.get("claim_id"),
        "status": rec.get("status"),
        "receipt_hash": rec.get("receipt_hash"),
        "recomputed_hash": expected,
        "claim_boundary": CLAIM,
    }


def claim_report(store: Any, repo: str) -> dict[str, Any]:
    latest = latest_claim_receipt(store, repo)
    ver = verify_claim_receipt(store, repo, latest) if latest else {
        "ok": False,
        "error": "no_claim_receipt",
    }
    idx = store.get_setting(f"claim_receipt_index:{repo}", {}) or {}
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "latest": latest,
        "verify": ver,
        "index": idx,
        "claim_boundary": CLAIM,
    }
