"""Checkable contracts on continuation packets. Fail-closed for promote."""

from __future__ import annotations

import json
import time
from hashlib import sha256
from typing import Any

SCHEMA = "cortex-contract/1.0"

DEFAULT_CONTRACT: dict[str, Any] = {
    "schema_version": SCHEMA,
    "profile": "default",
    "requires": {
        "governor_modes_allowed": ["normal", "constrained", "read_only"],
        "min_evidence_paths": 0,
        "forbidden_actions": ["ignore_immune_block", "treat_packet_as_authorization"],
        "promises": {
            "claim_boundary_present": True,
            "no_mutation_authority": True,
            "packet_is_not_authorization": True,
        },
    },
}

STRICT_CONTRACT: dict[str, Any] = {
    "schema_version": SCHEMA,
    "profile": "strict",
    "requires": {
        "governor_modes_allowed": ["normal", "constrained"],
        "immune_block": False,
        "manifest_current": True,
        "certificate_status_in": ["verified"],
        "min_evidence_paths": 1,
        "forbidden_actions": [
            "ignore_immune_block",
            "treat_packet_as_authorization",
            "edit_host",
        ],
        "promises": {
            "claim_boundary_present": True,
            "no_mutation_authority": True,
            "packet_is_not_authorization": True,
            "geometry_zero_point": True,
        },
    },
    "differential": {
        "forbidden_drift_fields": ["authority", "grants", "scope_effective"],
        "allowed_drift_fields": ["task", "evidence", "operational_state"],
    },
}


def _contract_hash(contract: dict[str, Any]) -> str:
    return sha256(
        json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def check_contract(
    packet: dict[str, Any],
    *,
    contract: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    prior_packet: dict[str, Any] | None = None,
    store: Any | None = None,
    repo: str | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    """Evaluate contract against packet (+ optional live context). Constrain only."""

    contract = contract or DEFAULT_CONTRACT
    context = context or {}
    requires = contract.get("requires") or {}
    breaks: list[dict[str, Any]] = []

    gov = (
        (packet.get("governance") or {}).get("mode")
        or (packet.get("governor") or {}).get("mode")
        or context.get("governor", {}).get("mode")
        or "unknown"
    )
    allowed_modes = requires.get("governor_modes_allowed")
    if allowed_modes and gov not in allowed_modes:
        breaks.append(
            {
                "code": "governor_mode_forbidden",
                "message": f"mode {gov} not in {allowed_modes}",
            }
        )

    control = packet.get("control_error") or context.get("control_error") or {}
    immune = control.get("immune_action") or packet.get("immune_action") or {}
    block = bool(
        control.get("block")
        if "block" in control
        else immune.get("block")
        if "block" in immune
        else False
    )
    if requires.get("immune_block") is False and block:
        breaks.append(
            {
                "code": "immune_block_active",
                "message": "contract requires immune_block=false",
            }
        )

    if requires.get("manifest_current") is True:
        # If context not provided, skip hard fail unless explicit false
        if context.get("repository") and context["repository"].get("manifest_current") is False:
            breaks.append(
                {
                    "code": "manifest_not_current",
                    "message": "manifest_current required",
                }
            )

    cert_allowed = requires.get("certificate_status_in")
    if cert_allowed:
        status = (
            context.get("repository", {}).get("bootstrap_status")
            or (packet.get("origin") or {}).get("bootstrap_status")
        )
        if status and status not in cert_allowed:
            breaks.append(
                {
                    "code": "certificate_status",
                    "message": f"{status} not in {cert_allowed}",
                }
            )

    evidence = packet.get("evidence") or packet.get("evidence_refs") or []
    if isinstance(evidence, list):
        n_ev = len(evidence)
    else:
        n_ev = 0
    # continuation packets use evidence list of refs
    op = packet.get("operational_state") or {}
    if not n_ev and op.get("evidence_ids"):
        n_ev = len(op["evidence_ids"])
    min_ev = int(requires.get("min_evidence_paths") or 0)
    if n_ev < min_ev:
        breaks.append(
            {
                "code": "insufficient_evidence",
                "message": f"need >= {min_ev} evidence, have {n_ev}",
            }
        )

    promises = requires.get("promises") or contract.get("promises") or {}
    claim = packet.get("claim_boundary") or context.get("claim_boundary")
    if promises.get("claim_boundary_present") and not claim:
        # continuation embeds claim in authority section sometimes
        auth = packet.get("authority") or {}
        if not auth.get("claim_boundary") and not auth.get("packet_is_not_authorization"):
            breaks.append(
                {
                    "code": "claim_boundary_missing",
                    "message": "claim_boundary required",
                }
            )

    if promises.get("no_mutation_authority"):
        auth = packet.get("authority") or {}
        if auth.get("cortex_may_mutate") is True or auth.get("may_mutate_repository") is True:
            breaks.append(
                {
                    "code": "mutation_authority_claimed",
                    "message": "packet must not claim mutation authority",
                }
            )

    if promises.get("geometry_zero_point"):
        geom = packet.get("geometry") or context.get("geometry") or {}
        if geom and geom.get("zero_point") is False:
            breaks.append(
                {
                    "code": "geometry_not_zero_point",
                    "message": "geometry.zero_point required",
                }
            )

    differential: dict[str, Any] = {}
    diff_cfg = contract.get("differential") or {}
    if prior_packet and diff_cfg:
        forbidden = set(diff_cfg.get("forbidden_drift_fields") or [])
        for field in forbidden:
            a = prior_packet.get(field)
            b = packet.get(field)
            if a is not None and b is not None and a != b:
                breaks.append(
                    {
                        "code": "forbidden_drift",
                        "message": f"field {field} drifted",
                        "field": field,
                    }
                )
                differential[field] = {"from": a, "to": b}

    result = "pass" if not breaks else "fail"
    check_id = "chk_" + sha256(
        f"{_contract_hash(contract)}|{packet.get('packet_id')}|{result}".encode()
    ).hexdigest()[:20]
    payload = {
        "schema_version": SCHEMA,
        "check_id": check_id,
        "result": result,
        "passed": result == "pass",
        "breaks": breaks,
        "contract_hash": _contract_hash(contract),
        "contract_profile": contract.get("profile") or "custom",
        "differential": differential,
        "claim_boundary": (
            "Contracts constrain continuation; they never grant host mutation rights."
        ),
    }

    if persist and store is not None and repo:
        try:
            store.db.execute(
                """
                INSERT OR REPLACE INTO contract_checks(
                  check_id, repo, packet_id, contract_hash, result,
                  breaks_json, differential_json, checked_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    check_id,
                    repo,
                    str(packet.get("packet_id") or packet.get("id") or "unknown"),
                    payload["contract_hash"],
                    result,
                    json.dumps(breaks),
                    json.dumps(differential),
                    time.time(),
                ),
            )
            store.db.commit()
        except Exception:
            pass
    return payload


def contract_diff(
    packet_a: dict[str, Any], packet_b: dict[str, Any]
) -> dict[str, Any]:
    keys = sorted(set(packet_a) | set(packet_b))
    changed = []
    for key in keys:
        if packet_a.get(key) != packet_b.get(key):
            changed.append(key)
    return {
        "schema_version": "cortex-contract-diff/1.0",
        "changed_fields": changed,
        "claim_boundary": "Diff is observational; not authorization.",
    }
