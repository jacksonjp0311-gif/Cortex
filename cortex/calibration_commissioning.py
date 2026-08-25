"""v9.8.3 canonical commissioning for information-balanced calibration.

The module never invokes or selects a model.  It resolves already completed
live model circulations from Cortex's immutable ledger, independently evaluates
their public output, and produces development-only calibration evidence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .adapter_provenance import EVIDENCE_LIVE
from .discriminative_forge import TASK_FAMILIES, evaluate_case
from .information_calibration import assess_sequential_level, estimate_difficulty
from .model_circulation import verify_model_circulation

SCHEMA_VERSION = "cortex-calibration-commissioning/1.0"
OBSERVATION_SCHEMA = "cortex-calibration-observation/1.0"
VERSION = "9.8.3"
CLAIM_BOUNDARY = (
    "v9.8.3 measures development-task difficulty from canonically verified live "
    "public outputs. It does not establish competence lift, confirmatory evidence, "
    "model superiority, cognition, consciousness, agency, or authority."
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _authority() -> dict[str, bool]:
    return {
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "update_authorized": False,
    }


def resolve_calibration_observation(
    store: Any,
    repo: str,
    case: Mapping[str, Any],
    *,
    session_id: str,
    turn_id: int = 1,
) -> dict[str, Any]:
    """Resolve and score one live development observation from canonical rows."""
    verification = verify_model_circulation(store, repo, str(session_id), turn_id=int(turn_id))
    rows = [
        row for row in store.symbiotic_session_receipts(repo, str(session_id))
        if int(row.get("turn_id") or 0) == int(turn_id)
    ]
    by_kind = {str(row.get("kind") or ""): row for row in rows}
    invocation = by_kind.get("model_invocation") or {}
    outcome = by_kind.get("model_outcome") or {}
    errors: list[str] = []
    if verification.get("valid") is not True:
        errors.append("canonical_circulation_invalid")
    if verification.get("evidence_class") != EVIDENCE_LIVE:
        errors.append("live_empirical_evidence_required")
    request = invocation.get("request") if isinstance(invocation, Mapping) else None
    configuration = request.get("configuration") if isinstance(request, Mapping) else None
    if not isinstance(configuration, Mapping) or str(configuration.get("task_instruction") or "") != str(case.get("prompt") or ""):
        errors.append("case_prompt_not_bound_to_invocation")
    observed = outcome.get("observed_result") if isinstance(outcome, Mapping) else None
    public_text = observed.get("text") if isinstance(observed, Mapping) else None
    if public_text is None:
        errors.append("canonical_public_output_missing")
    success = evaluate_case(dict(case), str(public_text or "")) if not errors else None
    material = {
        "schema_version": OBSERVATION_SCHEMA,
        "version": VERSION,
        "repo": str(repo),
        "case_id": str(case.get("case_id") or ""),
        "family": str(case.get("family") or ""),
        "difficulty_level": str(case.get("difficulty_level") or ""),
        "session_id": str(session_id),
        "turn_id": int(turn_id),
        "invocation_id": verification.get("invocation_id"),
        "invocation_receipt_hash": ((verification.get("receipt_bindings") or {}).get("model_invocation") or {}).get("receipt_hash"),
        "outcome_receipt_hash": ((verification.get("receipt_bindings") or {}).get("model_outcome") or {}).get("receipt_hash"),
        "witness_result_hash": verification.get("witness_result_hash"),
        "evidence_class": verification.get("evidence_class"),
        "success": success,
        "state": "observed" if not errors else "held",
        "errors": sorted(set(errors)),
        "development_only": True,
        "confirmatory_eligible": False,
        "private_chain_of_thought_stored": False,
        "authority": _authority(),
    }
    return {**material, "observation_hash": _sha(material)}


def commission_calibration_panel(
    *,
    corpus: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    screening_cases: int = 4,
    confirmation_cases: int = 8,
    store: Any | None = None,
    repo: str | None = None,
) -> dict[str, Any]:
    """Build the sequential family/level panel from resolved observations only."""
    cases = {str(row.get("case_id") or ""): row for row in corpus.get("cases") or ()}
    accepted: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_cases: set[str] = set()
    seen_invocations: set[str] = set()
    for raw in observations:
        row = dict(raw)
        case_id = str(row.get("case_id") or "")
        invocation_id = str(row.get("invocation_id") or "")
        if store is None or not str(repo or ""):
            errors.append(f"canonical_store_required:{case_id}")
            continue
        if case_id not in cases:
            errors.append(f"case_not_in_corpus:{case_id}")
            continue
        canonical = resolve_calibration_observation(
            store,
            str(repo),
            cases[case_id],
            session_id=str(row.get("session_id") or ""),
            turn_id=int(row.get("turn_id") or 0),
        )
        if canonical != row:
            errors.append(f"observation_not_canonical:{case_id}")
            continue
        material = {key: value for key, value in row.items() if key != "observation_hash"}
        if row.get("observation_hash") != _sha(material):
            errors.append(f"observation_hash_invalid:{case_id}")
            continue
        if row.get("schema_version") != OBSERVATION_SCHEMA or row.get("state") != "observed":
            errors.append(f"observation_not_admissible:{case_id}")
            continue
        if row.get("evidence_class") != EVIDENCE_LIVE:
            errors.append(f"observation_not_live_empirical:{case_id}")
            continue
        case = cases[case_id]
        if str(case.get("family")) != str(row.get("family")) or str(case.get("difficulty_level")) != str(row.get("difficulty_level")):
            errors.append(f"case_binding_invalid:{case_id}")
            continue
        if case_id in seen_cases or not invocation_id or invocation_id in seen_invocations:
            errors.append(f"duplicate_case_or_invocation:{case_id}")
            continue
        seen_cases.add(case_id)
        seen_invocations.add(invocation_id)
        accepted.append(row)

    grouped: dict[str, dict[str, list[bool]]] = {}
    for row in accepted:
        grouped.setdefault(str(row["family"]), {}).setdefault(str(row["difficulty_level"]), []).append(bool(row["success"]))
    family_reports: dict[str, Any] = {}
    selected: dict[str, Any] = {}
    for family in sorted(str(name) for name in corpus.get("task_families") or TASK_FAMILIES):
        levels: dict[str, Any] = {}
        for level, outcomes in sorted(grouped.get(family, {}).items()):
            sequential = assess_sequential_level(
                outcomes,
                screening_cases=screening_cases,
                confirmation_cases=confirmation_cases,
            )
            levels[level] = {**sequential, "rasch": estimate_difficulty(outcomes)}
        calibrated = [row for row in levels.items() if row[1]["state"] == "calibrated"]
        calibrated.sort(key=lambda item: (-float(item[1]["rasch"]["item_information"] or 0.0), item[0]))
        if calibrated:
            level, report = calibrated[0]
            selected[family] = {"difficulty_level": level, "item_information": report["rasch"]["item_information"]}
            state, action = "calibrated", "freeze_development_calibration"
        else:
            states = {row["state"] for row in levels.values()}
            state = "held" if levels else "not_executed"
            action = (
                "collect_confirmation_cases" if "screening_candidate" in states
                else "move_harder" if states and states <= {"ceiling", "screening_ceiling"}
                else "move_easier" if states and states <= {"floor", "screening_floor"}
                else "collect_screening_cases"
            )
        family_reports[family] = {"state": state, "recommended_action": action, "levels": levels}
    overall = "CALIBRATION_READY" if family_reports and len(selected) == len(family_reports) and not errors else (
        "CALIBRATION_NOT_EXECUTED" if not accepted else "CALIBRATION_HELD"
    )
    material = {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "corpus_hash": corpus.get("corpus_hash"),
        "protocol": {
            "screening_cases": int(screening_cases),
            "confirmation_cases": int(confirmation_cases),
            "success_window": [0.30, 0.70],
            "center_out": True,
            "model_selected_at_runtime": True,
            "model_identity_used_in_selection": False,
        },
        "families": family_reports,
        "selected": selected,
        "accepted_observation_hashes": sorted(str(row["observation_hash"]) for row in accepted),
        "errors": sorted(set(errors)),
        "status": overall,
        "development_only": True,
        "confirmatory_eligible": False,
        "empirical_trial_executed": bool(accepted),
        "private_chain_of_thought_stored": False,
        "authority": _authority(),
        "claim_boundary": CLAIM_BOUNDARY,
    }
    return {**material, "commissioning_hash": _sha(material)}


def verify_calibration_commissioning(receipt: Mapping[str, Any]) -> dict[str, Any]:
    material = {str(key): value for key, value in receipt.items() if str(key) != "commissioning_hash"}
    errors: list[str] = []
    if material.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if receipt.get("commissioning_hash") != _sha(material):
        errors.append("commissioning_hash_invalid")
    if material.get("development_only") is not True or material.get("confirmatory_eligible") is not False:
        errors.append("claim_boundary_invalid")
    protocol = material.get("protocol") if isinstance(material.get("protocol"), Mapping) else {}
    if protocol.get("model_identity_used_in_selection") is not False:
        errors.append("model_identity_selection_forbidden")
    authority = material.get("authority") if isinstance(material.get("authority"), Mapping) else {}
    if any(authority.get(key) is not False for key in _authority()):
        errors.append("authority_must_remain_false")
    if material.get("status") == "CALIBRATION_READY" and (
        material.get("errors") or len(material.get("selected") or {}) != len(material.get("families") or {})
    ):
        errors.append("ready_state_not_supported")
    return {"valid": not errors, "state": "pass" if not errors else "fail", "errors": errors}


__all__ = [
    "CLAIM_BOUNDARY", "OBSERVATION_SCHEMA", "SCHEMA_VERSION", "VERSION",
    "commission_calibration_panel", "resolve_calibration_observation",
    "verify_calibration_commissioning",
]
