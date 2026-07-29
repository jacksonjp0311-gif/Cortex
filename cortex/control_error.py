"""Control-error vector — single error signal agents must read first."""

from __future__ import annotations

from typing import Any


def build_control_error(
    *,
    certificate: dict[str, Any] | None,
    governance: dict[str, Any] | None,
    manifest_current: bool | None,
    retrieval_confidence: float,
    aria_materialization: dict[str, Any] | None,
    task: str = "",
) -> dict[str, Any]:
    certificate = certificate or {}
    governance = governance or {}
    aria = aria_materialization or {}
    cert_status = str(certificate.get("status") or "unknown")
    gov_mode = str(governance.get("mode") or "unknown")
    conf = float(retrieval_confidence or 0.0)

    errors: list[dict[str, Any]] = []
    if manifest_current is False:
        errors.append(
            {
                "code": "manifest_drift",
                "severity": "high",
                "action": "refresh_or_bootstrap",
            }
        )
    if cert_status in {"failed", "unknown", ""}:
        errors.append(
            {
                "code": "certificate_failed",
                "severity": "high",
                "action": "verify_or_bootstrap",
            }
        )
    elif cert_status == "degraded":
        errors.append(
            {
                "code": "certificate_degraded",
                "severity": "medium",
                "action": "verify_and_constrain_work",
            }
        )
    if gov_mode == "read_only":
        errors.append(
            {
                "code": "governor_read_only",
                "severity": "high",
                "action": "diagnose_only_no_mutation",
            }
        )
    elif gov_mode == "constrained":
        errors.append(
            {
                "code": "governor_constrained",
                "severity": "medium",
                "action": "minimal_reversible_edits_only",
            }
        )
    if conf < 0.15 and cert_status == "verified" and gov_mode == "normal":
        errors.append(
            {
                "code": "low_retrieval_confidence",
                "severity": "low",
                "action": "narrow_task_or_expand_evidence",
            }
        )
    # Unexpected: ARIA active on tasks that look purely implementation (soft)
    aria_mode = aria.get("mode") or "dormant"
    if aria_mode == "active" and conf < 0.05:
        errors.append(
            {
                "code": "aria_active_low_confidence",
                "severity": "low",
                "action": "confirm_task_needs_aria",
            }
        )

    hard = [e for e in errors if e["severity"] == "high"]
    must_reverify = any(
        e["code"] in {"manifest_drift", "certificate_failed", "governor_read_only"}
        for e in errors
    )
    severity = (
        "high"
        if hard
        else "medium"
        if any(e["severity"] == "medium" for e in errors)
        else "low"
        if errors
        else "none"
    )
    return {
        "schema_version": "cortex-control-error/1.0",
        "glyph": "⚠",
        "ok": not hard and severity in {"none", "low"},
        "severity": severity,
        "must_reverify": must_reverify,
        "work_allowed": gov_mode != "read_only" and cert_status != "failed",
        "errors": errors,
        "summary": (
            "ok"
            if not errors
            else "; ".join(f"{e['code']}({e['severity']})" for e in errors)
        ),
        "read_first": True,
        "claim_boundary": (
            "Control error is a routing signal for agents; it does not grant or "
            "deny host authority by itself — host/human rules remain controlling."
        ),
    }
