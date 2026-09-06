"""Read-only epistemic views and bounded host instrument audits.

No universal truth verifier: host control labels and local execution are declared
anchors. A view never substitutes for a domain's admission/authorization gate.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contract_aligned_repair import _sha, audit_contract_aligned_controls
from .symbiosis import open_symbiotic_session

SCHEMA = "cortex-instrument-assurance/1.0"
AUTHORITY = {key: False for key in (
    "host_mutate_authorized", "execution_authorized",
    "memory_admission_authorized", "policy_effect",
)}
ASSURANCE_PATH = ("public_contract", "evaluator", "control_panel", "local_observation")
MAX_DEPTH = 3


def assurance_boundary(*, max_depth: int = MAX_DEPTH) -> dict[str, Any]:
    """Depth is derived from a fixed path, not supplied as evidence by a caller."""
    valid = type(max_depth) is int and 0 <= max_depth <= MAX_DEPTH
    depth = len(ASSURANCE_PATH) - 1
    return {
        "state": "PASS" if valid and depth <= max_depth else "UNKNOWN",
        "verification_depth": depth, "maximum_depth": max_depth,
        "path": list(ASSURANCE_PATH),
        "anchor_types": ["host_reviewed_control_labels", "host_observed_local_execution"],
        "assurance_scope": "finite_control_panel_only",
        "unresolved_assumptions": [
            "control labels may be wrong", "controls are not exhaustive",
            "host execution environment is trusted, not independently attested",
            "distinct patches do not prove independent repair strategies",
        ],
    }


def instrument_state(report: Mapping[str, Any], *, corpus_hash: str,
                     commitments: Mapping[str, str], max_depth: int = MAX_DEPTH) -> dict[str, Any]:
    """Preserve both accepted and rejected controls, including contradictory panels."""
    assurance = assurance_boundary(max_depth=max_depth)
    errors = []
    rows = []
    try:
        if (
            report.get("result_hash") != _sha({k: v for k, v in report.items() if k != "result_hash"})
            or report.get("schema_version") != "cortex-evaluator-control-audit/1.0"
            or report.get("corpus_hash") != corpus_hash
            or report.get("evaluator_commitments") != commitments
            or not commitments
            or report.get("evidence_class") != "local_instrument_audit"
            or report.get("expected_labels") != "host_reviewed_not_semantically_proven"
            or type(report.get("additional_model_calls")) is not int
            or report["additional_model_calls"] != 0
            or any(report.get(k) is not False for k in (*AUTHORITY, "universal_implementation_equivalence",
                                                       "semantic_transfer_established", "general_improvement_established"))
        ):
            errors.append("audit_identity_or_binding_invalid")
        rows = report["observations"]
        if not isinstance(rows, list) or any(
            r["case_id"] not in commitments
            or type(r["expected_pass"]) is not bool or type(r["observed_pass"]) is not bool
            or r["expectation_met"] is not (r["expected_pass"] == r["observed_pass"])
            or not r["patch_hash"] or not r["evaluation_hash"] for r in rows
        ):
            errors.append("observation_invalid")
        expected_state = "CONTROL_PANEL_PASS" if rows and all(r["expectation_met"] for r in rows) else "EVALUATOR_CHALLENGED"
        if report.get("state") != expected_state:
            errors.append("audit_state_invalid")
    except (KeyError, TypeError, ValueError):
        errors.append("malformed_audit")
    panels = {}
    if not errors:
        for case_id in sorted(commitments):
            panel = [r for r in rows if r["case_id"] == case_id]
            positive = [r for r in panel if r["expected_pass"]]
            negative = [r for r in panel if not r["expected_pass"]]
            if len({r["control_id"] for r in panel}) != len(panel):
                errors.append("duplicate_control")
            panels[case_id] = {
                "accepts_known_valid": {
                    "support": [r["evaluation_hash"] for r in positive if r["observed_pass"]],
                    "opposition": [r["evaluation_hash"] for r in positive if not r["observed_pass"]],
                },
                "rejects_known_invalid": {
                    "support": [r["evaluation_hash"] for r in negative if not r["observed_pass"]],
                    "opposition": [r["evaluation_hash"] for r in negative if r["observed_pass"]],
                },
                "coverage_complete": len({r["patch_hash"] for r in positive}) >= 2 and bool(negative),
                "allowed_rejection_count": sum(not r["observed_pass"] for r in positive),
                "invalid_acceptance_count": sum(r["observed_pass"] for r in negative),
                "positive_count": len(positive), "negative_count": len(negative),
            }
    over = any(p["allowed_rejection_count"] for p in panels.values())
    under = any(p["invalid_acceptance_count"] for p in panels.values())
    complete = bool(panels) and all(p["coverage_complete"] for p in panels.values())
    state = (
        "UNRESOLVED" if errors else "CONFLICTED" if over and under else
        "OVERCONSTRAINED" if over else "UNDERCONSTRAINED" if under else
        "READY" if complete and assurance["state"] == "PASS" else "UNRESOLVED"
    )
    body = {
        "schema_version": SCHEMA, "state": state, "panels": panels,
        "binding_state": "FAIL" if errors else "PASS", "errors": sorted(set(errors)),
        "audit_hash": report.get("result_hash"), "corpus_hash": corpus_hash,
        "evaluator_commitments": dict(commitments), "assurance": assurance,
        "active_guidance_authorized": False, "universal_semantic_validity": "UNKNOWN",
        **AUTHORITY,
    }
    return {**body, "projection_hash": _sha(body)}


def audit_instrument(store: Any, repo: str, *, public: Mapping, private: Mapping,
                     controls: Mapping, root: Any, source_commit: str,
                     max_depth: int = MAX_DEPTH) -> dict[str, Any]:
    """Host-only local execution entry: no caller-supplied successful observations."""
    if len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise ValueError("exact source commit required")
    report = audit_contract_aligned_controls(public, private, controls, root)
    commitments = {c["case_id"]: c["executable_case"]["private_evaluator_commitment"] for c in public["cases"]}
    state = instrument_state(report, corpus_hash=public["corpus_hash"], commitments=commitments, max_depth=max_depth)
    session = open_symbiotic_session(store, repo, task="host instrument audit", persist=True)
    return store.append_symbiotic_receipt(repo, {
        "kind": "instrument_assurance", "schema_version": SCHEMA,
        "session_id": session["session_id"], "turn_id": 0,
        "body_epoch_id": session["body_epoch_id"],
        "event_id": "instrument_audit_" + state["projection_hash"],
        "source_commit": source_commit, "audit": report, "instrument": state,
        "additional_model_calls": 0, **AUTHORITY,
    })


def verify_instrument(store: Any, repo: str, receipt_hash: str) -> dict[str, Any]:
    """Reload and recompute. Historical audit validity does not imply current readiness."""
    if store.verify_symbiotic_receipt(repo, receipt_hash).get("valid") is not True:
        return {"valid": False, "state": "UNRESOLVED", "errors": ["receipt_invalid"], **AUTHORITY}
    receipt = store.symbiotic_receipt(receipt_hash, repo=repo)
    try:
        view = receipt["instrument"]
        rebuilt = instrument_state(receipt["audit"], corpus_hash=view["corpus_hash"],
                                   commitments=view["evaluator_commitments"],
                                   max_depth=view["assurance"]["maximum_depth"])
        valid = (receipt["kind"] == "instrument_assurance" and receipt["schema_version"] == SCHEMA
                 and view == rebuilt and rebuilt["binding_state"] == "PASS"
                 and all(receipt.get(k) is False for k in AUTHORITY))
    except (KeyError, TypeError, ValueError):
        return {"valid": False, "state": "UNRESOLVED", "errors": ["instrument_invalid"], **AUTHORITY}
    return {"valid": valid, "state": rebuilt["state"], "instrument": rebuilt,
            "errors": [] if valid else ["instrument_reconstruction_invalid"], **AUTHORITY}


def inspect_measurement_claim(store: Any, repo: str, receipt_hash: str, claim: str) -> dict[str, Any]:
    """Claim-specific gates; higher research claims have no self-declaration path."""
    audit = verify_instrument(store, repo, receipt_hash)
    gates = {"source": "PASS" if audit["valid"] else "FAIL", "instrument": "UNKNOWN"}
    if audit["valid"]:
        state = audit["state"]
        gates["instrument"] = "PASS" if state == "READY" else "UNKNOWN" if state == "UNRESOLVED" else "FAIL"
        challenges = store.symbiotic_receipts_by_kind(repo, "repair_evaluator_challenge", limit=10000)
        if len(challenges) == 10000:
            gates["instrument"] = "UNKNOWN"
        elif any(c.get("evaluator_commitment") in audit["instrument"]["evaluator_commitments"].values() for c in challenges):
            gates["instrument"] = "FAIL"
    if claim != "bounded_instrument_controls":
        gates.update(experimental="UNKNOWN", causal="UNKNOWN", replication="UNKNOWN")
    rank = {"FAIL": 0, "UNKNOWN": 1, "PASS": 2}
    eligibility = min(gates.values(), key=rank.__getitem__)
    return {"claim": claim, "state": eligibility, "gates": gates,
            "claim_eligible": eligibility == "PASS", "receipt_hash": receipt_hash,
            "scope": "sampled_controls_only" if claim == "bounded_instrument_controls" else "not_established",
            **AUTHORITY}


def governed_state_view(store: Any, repo: str, receipt_hash: str) -> dict[str, Any]:
    """Minimum shared inspection interface, not shared admission semantics."""
    valid = store.verify_symbiotic_receipt(repo, receipt_hash).get("valid") is True
    row = store.symbiotic_receipt(receipt_hash, repo=repo) if valid else {}
    row = row or {}
    view = {
        "schema_version": "cortex-governed-state-view/1.0", "object_id": receipt_hash,
        "object_type": row.get("kind", "unresolved"),
        "provenance": {"integrity": "PASS" if valid else "FAIL", "roots": [receipt_hash] if valid else []},
        "native_state": row.get("state", row.get("status")),
        "support": "UNKNOWN", "opposition": "UNKNOWN", "freshness": "UNKNOWN",
        "applicability": "UNKNOWN", "supersession": "UNKNOWN",
        "known_at": row.get("created_at"), "valid_from": None, "valid_to": None,
        "domain_verification_required": True, **AUTHORITY,
    }
    if row.get("kind") == "instrument_assurance":
        checked = verify_instrument(store, repo, receipt_hash)
        if checked["valid"]:
            panels = checked["instrument"]["panels"]
            view["support"] = {key: {axis: p[axis]["support"] for axis in ("accepts_known_valid", "rejects_known_invalid")} for key, p in panels.items()}
            view["opposition"] = {key: {axis: p[axis]["opposition"] for axis in ("accepts_known_valid", "rejects_known_invalid")} for key, p in panels.items()}
            view["native_state"] = checked["state"]
    return view
