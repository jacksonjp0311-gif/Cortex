"""Prospective 4+4 development calibration over existing one-shot screens.

No treatment effect or population inference follows from this selected cohort.
The host-facing stage runner gates confirmation; reconstruction also checks the
ordering independently so standalone calls cannot retrospectively qualify.
"""
from __future__ import annotations

from .epistemic_instrumentation import AUTHORITY
from .information_calibration import assess_sequential_level
from .structured_repair_screen import (
    _repeat_binding_errors, _sha, execute_structured_repair_screen,
    fresh_task_fingerprints, verify_structured_repair_screen,
)
from .symbiosis import open_symbiotic_session

SCHEMA = "cortex-repair-calibration-cohort/1.0"
POLICY = {
    "screening_calls": 4, "confirmation_calls": 4, "maximum_total_calls": 8,
    "confirmation_requires": "mixed_screen", "automatic_retries": 0,
    "minimum_success_rate": 0.3, "maximum_success_rate": 0.7,
    "difficulty_change_authorized": False, "confirmatory_effect_eligible": False,
}


def _load(store, repo, identity, kind):
    if store.verify_symbiotic_receipt(repo, identity).get("valid") is not True:
        raise ValueError("canonical receipt required")
    row = store.symbiotic_receipt(identity, repo=repo)
    if row.get("kind") != kind:
        raise ValueError("receipt kind mismatch")
    return row


def _screens(store, repo, hashes):
    if len(hashes) != 2 or len(set(hashes)) != 2:
        raise ValueError("two distinct prospective screens required")
    screens = [_load(store, repo, h, "structured_repair_preregistration") for h in hashes]
    for row in screens:
        if (row.get("schema_version") != "cortex-structured-repair-preregistration/1.3"
                or _repeat_binding_errors(store, repo, row)
                or row.get("context_treatment") != "task_only_control"
                or row.get("tools") != [] or row.get("planned_calls") != 4
                or len(row.get("cases", [])) != 4
                or any(row.get(k) is not False for k in AUTHORITY)):
            raise ValueError("audited task-only frontier screen required")
    for field in ("model_identity", "adapter_provenance", "tools", "context_treatment", "screening_policy", "governed_prerequisite"):
        if screens[0].get(field) != screens[1].get(field):
            raise ValueError("fixed cohort boundary changed: " + field)
    contracts = [{k: v for k, v in row["response_contract"].items() if k != "allowed_paths"} for row in screens]
    if contracts[0] != contracts[1]:
        raise ValueError("response contract changed")
    if screens[0]["frontier_binding"]["stratum"] != screens[1]["frontier_binding"]["stratum"]:
        raise ValueError("difficulty stratum changed")
    fresh_task_fingerprints([c for row in screens for c in row["cases"]])
    return screens


def freeze_repair_cohort(store, repo, *, screen_receipt_hashes, source_commit):
    screens = _screens(store, repo, screen_receipt_hashes)
    if len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise ValueError("source commit required")
    for screen in screens:
        instrument = _load(store, repo, screen["frontier_binding"]["instrument_receipt_hash"], "instrument_assurance")
        if instrument["source_commit"] != source_commit:
            raise ValueError("instrument source mismatch")
    claims = store.symbiotic_receipts_by_kind(repo, "structured_repair_execution_claim", limit=10000)
    if len(claims) == 10000 or any(c.get("preregistration_receipt_hash") in screen_receipt_hashes for c in claims):
        raise ValueError("freeze cohort before any model execution")
    session = open_symbiotic_session(store, repo, task="freeze prospective repair cohort", persist=True)
    return store.append_symbiotic_receipt(repo, {
        "schema_version": SCHEMA, "kind": "repair_calibration_cohort",
        "session_id": session["session_id"], "body_epoch_id": session["body_epoch_id"],
        "turn_id": 0, "event_id": "cohort_" + _sha(screen_receipt_hashes),
        "screen_receipt_hashes": list(screen_receipt_hashes), "source_commit": source_commit,
        "policy": dict(POLICY), "stratum": screens[0]["frontier_binding"]["stratum"],
        "development_only": True, **AUTHORITY,
    })


def _cohort(store, repo, identity):
    cohort = _load(store, repo, identity, "repair_calibration_cohort")
    if (cohort.get("schema_version") != SCHEMA or _sha(cohort.get("policy")) != _sha(POLICY)
            or any(cohort.get(k) is not False for k in AUTHORITY)):
        raise ValueError("cohort policy invalid")
    screens = _screens(store, repo, cohort["screen_receipt_hashes"])
    if any(_load(store, repo, row["frontier_binding"]["instrument_receipt_hash"], "instrument_assurance")["source_commit"] != cohort.get("source_commit") for row in screens):
        raise ValueError("cohort source binding mismatch")
    if cohort.get("stratum") != screens[0]["frontier_binding"]["stratum"]:
        raise ValueError("cohort stratum mismatch")
    return cohort, screens


def _stage_results(store, repo, cohort):
    rows = store.symbiotic_receipts_by_kind(repo, "structured_repair_result", limit=10000)
    if len(rows) == 10000:
        raise ValueError("result coverage unknown")
    results = []
    for prereg_hash in cohort["screen_receipt_hashes"]:
        matches = [r for r in rows if r.get("preregistration_receipt_hash") == prereg_hash]
        if len(matches) > 1:
            raise ValueError("ambiguous stage result")
        result = matches[0] if matches else None
        if result:
            verified = verify_structured_repair_screen(store, repo, result_receipt_hash=result["receipt_hash"])
            if not verified["valid"]:
                raise ValueError("stage reconstruction failed")
            claim = _load(store, repo, result["execution_claim_receipt_hash"], "structured_repair_execution_claim")
            if claim["created_at"] < cohort["created_at"]:
                raise ValueError("stage executed before cohort freeze")
        results.append(result)
    if results[1]:
        if not results[0] or not 0 < results[0]["screen"]["success_count"] < 4:
            raise ValueError("confirmation requires mixed prior screen")
        claim = _load(store, repo, results[1]["execution_claim_receipt_hash"], "structured_repair_execution_claim")
        if claim["created_at"] < results[0]["created_at"]:
            raise ValueError("confirmation executed before screening result")
    return results


def inspect_repair_cohort(store, repo, cohort_receipt_hash):
    try:
        cohort, _ = _cohort(store, repo, cohort_receipt_hash)
        results = _stage_results(store, repo, cohort)
        outcomes = [store.symbiotic_receipt(h, repo=repo)["task_success"]
                    for result in results if result for h in result["case_receipt_hashes"]]
        summary = assess_sequential_level(outcomes)
        return {"valid": True, "errors": [], "cohort_receipt_hash": cohort_receipt_hash,
                "result_receipt_hashes": [r["receipt_hash"] if r else None for r in results],
                "summary": summary, "completed_calls": len(outcomes),
                "confirmation_permitted": bool(results[0] and not results[1] and 0 < sum(outcomes) < 4),
                "development_region_selected": len(outcomes) == 8 and summary["state"] == "calibrated",
                "population_calibration_established": False, "semantic_transfer_established": False,
                "general_improvement_established": False, **AUTHORITY}
    except (KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)], "confirmation_permitted": False, **AUTHORITY}


def execute_repair_cohort_stage(store, repo, *, cohort_receipt_hash, stage, private_bundle,
                                adapter, tools, grant):
    if type(stage) is not int or stage not in (0, 1):
        raise ValueError("stage must be zero or one")
    cohort, screens = _cohort(store, repo, cohort_receipt_hash)
    from .coding_workspace import repository_head
    if repository_head(grant.workspace_root) != cohort["source_commit"]:
        raise ValueError("runtime source drift")
    results = _stage_results(store, repo, cohort)
    if results[stage] or (stage == 1 and (not results[0] or not 0 < results[0]["screen"]["success_count"] < 4)):
        raise ValueError("stage blocked by prospective stopping rule")
    return execute_structured_repair_screen(store, repo, preregistration=screens[stage],
            private_bundle=private_bundle, adapter=adapter, tools=tools, grant=grant)
