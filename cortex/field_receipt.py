"""v7.3 Resonant Frame receipts — hashed identity, observation-only.

Integrity does not depend on a desirable classification.
A valid STALE_ECHO or OVERBOUND receipt remains cryptographically intact.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, TYPE_CHECKING

from . import __version__

if TYPE_CHECKING:
    from .resonant_frame import ResonantFrame

SCHEMA = "cortex-field-receipt/1.0"
GLYPH = "⌘⟳"

CLAIM_BOUNDARY = (
    "A frame receipt is a falsifiable stamp of bounded temporal telemetry. "
    "It never satisfies evidence, authority, epoch, or witness axes. "
    "It is supporting diagnostic context only."
)


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canonical(obj).encode()).hexdigest()


def issue_frame_receipt(frame: "ResonantFrame" | dict[str, Any]) -> dict[str, Any]:
    if hasattr(frame, "to_dict"):
        base = frame.to_dict()
    else:
        base = dict(frame)

    # Drop samples body from receipt identity mass? Spec says sample_digest is enough
    # but metrics/classification/policy/truth panel must be in hash.
    payload = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "frame_id": base.get("frame_id"),
        "repo": base.get("repo"),
        "body_epoch_id": base.get("body_epoch_id"),
        "start_tick": base.get("start_tick"),
        "end_tick": base.get("end_tick"),
        "sample_digest": base.get("sample_digest"),
        "baseline_digest": base.get("baseline_digest"),
        "threshold_config_digest": base.get("threshold_config_digest"),
        "channel_truth_panel": base.get("channel_truth_panel") or {},
        "metrics": base.get("metrics") or {},
        "frame_vector": base.get("frame_vector")
        or (base.get("metrics") or {}),
        "classification": base.get("classification"),
        "reasons": base.get("reasons") or [],
        "policy": base.get("policy") or {},
        "measurement_basis": base.get("measurement_basis") or "direct_snapshot",
        "policy_eligible": bool(base.get("policy_eligible", True)),
        "baseline_eligible": bool(base.get("baseline_eligible", True)),
        "active_edges": base.get("active_edges") or [],
        "contributor_digest": _sha(
            {
                "paths": sorted(
                    {
                        p
                        for s in (base.get("samples") or [])
                        for p in (s.get("paths") or [])
                    }
                ),
                "sample_digest": base.get("sample_digest"),
            }
        ),
        "constitutional_coordinate_observed": _first_bits(base),
        "cortex_version": base.get("cortex_version") or __version__,
        "issued_at": base.get("issued_at") or time.time(),
        "claim_boundary": CLAIM_BOUNDARY,
        "advisory_only": True,
        "authority_satisfying": False,
        "witness_satisfying": False,
        "epoch_satisfying": False,
        "evidence_satisfying": False,
    }
    # Hash excludes only receipt_hash
    payload["receipt_hash"] = _sha(payload)
    return payload


def _first_bits(base: dict[str, Any]) -> list[int]:
    for s in base.get("samples") or []:
        bits = s.get("constitutional_bits") or []
        if bits:
            return list(bits)[:4]
    return []


def verify_frame_receipt(
    store: Any,
    repo: str,
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Separate integrity_ok, epoch_ok, baseline_digest_ok, config_digest_ok."""
    if receipt is None:
        receipt = store.get_setting(f"field_frame_latest:{repo}")
    if not receipt:
        return {
            "ok": False,
            "integrity_ok": False,
            "epoch_ok": False,
            "baseline_digest_ok": False,
            "config_digest_ok": False,
            "operationally_current": False,
            "error": "no_receipt",
        }

    material = {k: v for k, v in receipt.items() if k != "receipt_hash"}
    expected = _sha(material)
    integrity_ok = expected == receipt.get("receipt_hash")

    epoch_ok = False
    operationally_current = False
    try:
        from .epoch import observe_current_epoch

        obs = observe_current_epoch(store, repo)
        live = str(obs.get("epoch_id") or obs.get("live_epoch_id") or "")
        epoch_ok = bool(live) and live == str(receipt.get("body_epoch_id") or "")
        operationally_current = bool(obs.get("verified") or obs.get("is_current")) and epoch_ok
    except Exception:
        pass

    bas = store.get_setting(f"field_baseline:{repo}", {}) or {}
    baseline_digest_ok = (not bas.get("digest")) or bas.get("digest") == receipt.get(
        "baseline_digest"
    )

    from .resonant_frame import DEFAULT_THRESHOLDS

    config_digest_ok = receipt.get("threshold_config_digest") == DEFAULT_THRESHOLDS.digest() or bool(
        receipt.get("threshold_config_digest")
    )

    return {
        "ok": integrity_ok,
        "integrity_ok": integrity_ok,
        "epoch_ok": epoch_ok,
        "baseline_digest_ok": bool(baseline_digest_ok),
        "config_digest_ok": bool(config_digest_ok),
        "operationally_current": operationally_current,
        "frame_id": receipt.get("frame_id"),
        "classification": receipt.get("classification"),
        "receipt_hash": receipt.get("receipt_hash"),
        "claim_boundary": CLAIM_BOUNDARY,
        "note": "integrity does not depend on desirable classification",
    }
