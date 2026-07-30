from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .hippocampus import active_session


class Governor:
    """Negative-feedback controller for repository memory trust and context scope."""

    def __init__(self, home: Path, store: Any) -> None:
        self.home = home
        self.store = store

    def evaluate(
        self,
        repo: str,
        *,
        retrieval_confidence: float = 0.0,
        manifest_current: bool | None = None,
        certificate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        repository = self.store.repo(repo)
        if not repository:
            return {
                "stability": 0.0,
                "mode": "read_only",
                "reason": "repository is not attached",
                "components": {},
            }

        certificate_row = self.store.latest_bootstrap(repo)
        certificate = certificate or {}
        if not certificate and certificate_row:
            try:
                certificate = json.loads(certificate_row["certificate"] or "{}")
            except json.JSONDecodeError:
                certificate = {}

        integrity = 1.0 if self.store.integrity_check() else 0.0
        certificate_status = certificate.get("status")
        if certificate_status == "verified":
            integrity *= 1.0
        elif certificate_status == "degraded":
            integrity *= 0.65
        else:
            integrity *= 0.25

        focus = 1.0 if active_session(self.home, repo) else 0.35
        if manifest_current is True:
            freshness = 1.0
        elif manifest_current is False:
            freshness = 0.20
        else:
            last_indexed = repository["last_indexed"] or 0
            age_hours = max(0.0, (time.time() - last_indexed) / 3600.0)
            freshness = max(0.25, 1.0 - min(age_hours, 168.0) / 210.0)

        latest_session = self.store.latest_session(repo)
        continuity = 0.80 if latest_session else 0.45
        if latest_session and latest_session["status"] == "active":
            continuity = 1.0

        confidence = max(0.0, min(1.0, retrieval_confidence))
        # M1: unified uncertainty U (single number); confidence = 1 - U
        u_packet: dict[str, Any] = {}
        try:
            from .math_net.uncertainty import compute_uncertainty

            u_packet = compute_uncertainty(
                retrieval_confidence=confidence,
                certificate_status=str(certificate_status or "unknown"),
                manifest_current=manifest_current,
                governor_stability=None,  # avoid circular use of S
            )
            unified_conf = float(u_packet.get("confidence") or confidence)
            # U may only *lower* confidence for S (never inflate past retrieval).
            # Prevents verified-cert soft blend from pushing mode to normal after drift.
            if confidence > 0:
                unified_conf = min(confidence, unified_conf)
        except Exception:
            unified_conf = confidence
            u_packet = {"u": round(1.0 - confidence, 6), "confidence": confidence}

        # M5/v6.13: live calibration if promoted; else shadow blend; else priors
        w_i, w_f, w_r, w_c, w_k = 0.30, 0.25, 0.20, 0.15, 0.10
        coeff_source = "prior"
        try:
            from .math_net.calibration import load_shadow_calibration
            from .math_net.spectral_memory import load_live_calibration

            live = load_live_calibration(self.store, repo)
            if live and live.get("governor_weights"):
                gw = live["governor_weights"]
                w_i = float(gw.get("integrity", w_i))
                w_f = float(gw.get("focus", w_f))
                w_r = float(gw.get("freshness", w_r))
                w_c = float(gw.get("confidence", w_c))
                w_k = float(gw.get("continuity", w_k))
                s = w_i + w_f + w_r + w_c + w_k or 1.0
                w_i, w_f, w_r, w_c, w_k = w_i / s, w_f / s, w_r / s, w_c / s, w_k / s
                coeff_source = "live_calibrated"
            else:
                shadow = load_shadow_calibration(self.store, repo)
                gw = shadow.get("governor_weights") or {}
                if shadow.get("n_outcomes", 0) >= 5 and gw:
                    w_i = 0.7 * w_i + 0.3 * float(gw.get("integrity", w_i))
                    w_f = 0.7 * w_f + 0.3 * float(gw.get("focus", w_f))
                    w_r = 0.7 * w_r + 0.3 * float(gw.get("freshness", w_r))
                    w_c = 0.7 * w_c + 0.3 * float(gw.get("confidence", w_c))
                    w_k = 0.7 * w_k + 0.3 * float(gw.get("continuity", w_k))
                    s = w_i + w_f + w_r + w_c + w_k
                    w_i, w_f, w_r, w_c, w_k = w_i / s, w_f / s, w_r / s, w_c / s, w_k / s
                    coeff_source = "shadow_blend"
        except Exception:
            pass

        stability = (
            w_i * integrity
            + w_f * focus
            + w_r * freshness
            + w_c * unified_conf
            + w_k * continuity
        )
        stability = round(stability, 6)

        if certificate_status != "verified" or manifest_current is False:
            mode = "read_only"
            reason = "bootstrap certificate missing/degraded or repository manifest drifted"
        elif stability >= 0.72:
            mode = "normal"
            reason = "repository memory is certified, current, focused, and sufficiently confident"
        elif stability >= 0.55:
            mode = "constrained"
            reason = "memory is usable but scope should remain narrow and dry-run-first"
        else:
            mode = "read_only"
            reason = "stability is below the mutation-support threshold"

        # v6.24 Memory Simplex — recommend trusted controller under read_only
        memory_controller = "advanced"
        transfer_to_baseline = False
        if mode == "read_only":
            memory_controller = "evidence_baseline"
            transfer_to_baseline = True
        try:
            from .memory_simplex import resolve_controller

            sx = resolve_controller(
                governance_mode=mode, force_baseline=transfer_to_baseline
            )
            memory_controller = str(sx.get("controller") or memory_controller)
            transfer_to_baseline = bool(sx.get("transfer_to_baseline"))
        except Exception:
            pass

        return {
            "stability": stability,
            "mode": mode,
            "reason": reason,
            "memory_controller": memory_controller,
            "transfer_to_baseline": transfer_to_baseline,
            "uncertainty": u_packet,
            "u": u_packet.get("u"),
            "coeffs_prior": {
                "integrity": 0.30,
                "focus": 0.25,
                "freshness": 0.20,
                "confidence": 0.15,
                "continuity": 0.10,
                "note": "priors; shadow blend after n_outcomes>=5",
            },
            "coeffs_used": {
                "integrity": round(w_i, 4),
                "focus": round(w_f, 4),
                "freshness": round(w_r, 4),
                "confidence": round(w_c, 4),
                "continuity": round(w_k, 4),
            },
            "coeffs_source": coeff_source,
            "components": {
                "integrity": round(integrity, 6),
                "focus": round(focus, 6),
                "freshness": round(freshness, 6),
                "retrieval_confidence": round(confidence, 6),
                "unified_confidence": round(unified_conf, 6),
                "continuity": round(continuity, 6),
            },
            "authority": {
                "cortex_may_authorize_mutation": False,
                "host_repository_rules_control": True,
                "human_authorization_required": True,
            },
        }
