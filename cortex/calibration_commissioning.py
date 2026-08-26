"""v9.8.3 canonical commissioning for information-balanced calibration.

The module never invokes or selects a model.  It resolves already completed
live model circulations from Cortex's immutable ledger, independently evaluates
their public output, and produces development-only calibration evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections.abc import Mapping, Sequence
from typing import Any

from .adapter_provenance import EVIDENCE_LIVE
from .discriminative_forge import TASK_FAMILIES, evaluate_case
from .information_calibration import assess_sequential_level, estimate_difficulty
from .model_circulation import verify_model_circulation

SCHEMA_VERSION = "cortex-calibration-commissioning/1.1"
OBSERVATION_SCHEMA = "cortex-calibration-observation/1.1"
VERSION = "9.8.6"
CLAIM_BOUNDARY = (
    "v9.8.6 measures development-task difficulty and observational invocation cost "
    "from canonically verified live public outputs. It does not establish repeatability, "
    "competence lift, confirmatory evidence, "
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


def _numeric(mapping: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value)):
            return float(value)
    return None


def _invocation_cost_metrics(invocation: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct provider-neutral cost coordinates from a verified invocation."""
    requested = invocation.get("requested_at")
    completed = invocation.get("completed_at")
    latency = None
    if isinstance(requested, (int, float)) and isinstance(completed, (int, float)):
        candidate = float(completed) - float(requested)
        if math.isfinite(candidate) and candidate >= 0.0:
            latency = candidate
    usage = invocation.get("token_usage") if isinstance(invocation.get("token_usage"), Mapping) else {}
    cost = invocation.get("cost") if isinstance(invocation.get("cost"), Mapping) else {}
    input_tokens = _numeric(usage, "input_tokens", "input")
    output_tokens = _numeric(usage, "output_tokens", "output")
    reasoning_tokens = _numeric(usage, "reasoning_tokens", "reasoning")
    total_tokens = _numeric(usage, "total_tokens", "total")
    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens
    amount = _numeric(cost, "amount")
    currency = str(cost.get("currency") or "").upper() or None
    material = {
        "schema_version": "cortex-calibration-cost/1.0",
        "latency_seconds": round(latency, 6) if latency is not None else None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": total_tokens,
        "cost_amount": amount,
        "cost_currency": currency,
        "validity": {
            "latency": latency is not None,
            "input_tokens": input_tokens is not None,
            "output_tokens": output_tokens is not None,
            "reasoning_tokens": reasoning_tokens is not None,
            "total_tokens": total_tokens is not None,
            "cost": amount is not None and currency is not None,
        },
        "source": "canonical_model_invocation_receipt",
        "observational_only": True,
        "repeatability_established": False,
    }
    return {**material, "cost_metrics_hash": _sha(material)}


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    finite = sorted(float(value) for value in values if math.isfinite(float(value)))
    if not finite:
        return {"n": 0, "median": None, "p95": None, "mad": None, "minimum": None, "maximum": None}
    median = statistics.median(finite)
    p95 = finite[max(0, math.ceil(0.95 * len(finite)) - 1)]
    mad = statistics.median(abs(value - median) for value in finite)
    return {
        "n": len(finite), "median": round(median, 6), "p95": round(p95, 6),
        "mad": round(mad, 6), "minimum": round(finite[0], 6), "maximum": round(finite[-1], 6),
    }


def summarize_observation_costs(
    observations: Sequence[Mapping[str, Any]], cases: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Describe cross-case cost; never represent it as repeated-run variance."""
    latency: list[float] = []
    tokens: list[float] = []
    costs: list[float] = []
    efficiency: list[float] = []
    currencies: set[str] = set()
    for row in observations:
        metrics = row.get("cost_metrics") if isinstance(row.get("cost_metrics"), Mapping) else {}
        case = cases.get(str(row.get("case_id") or ""), {})
        elapsed = metrics.get("latency_seconds")
        if isinstance(elapsed, (int, float)) and float(elapsed) > 0:
            latency.append(float(elapsed))
            bits = case.get("resolved_information_bits")
            if isinstance(bits, (int, float)):
                efficiency.append(float(bits) / float(elapsed))
        total = metrics.get("total_tokens")
        if isinstance(total, (int, float)):
            tokens.append(float(total))
        amount = metrics.get("cost_amount")
        if isinstance(amount, (int, float)):
            costs.append(float(amount))
        currency = metrics.get("cost_currency")
        if currency:
            currencies.add(str(currency))
    return {
        "schema_version": "cortex-calibration-cost-panel/1.0",
        "sample_count": len(observations),
        "latency_seconds": _distribution(latency),
        "total_tokens": _distribution(tokens),
        "cost_amount": _distribution(costs),
        "cost_currencies": sorted(currencies),
        "resolved_information_bits_per_second": _distribution(efficiency),
        "distribution_kind": "cross_case_observational",
        "repeatability_established": False,
        "gate_effect": False,
        "authority_effect": False,
    }


def summarize_evidence_geometry(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    entanglement = [float(row["evidence_entanglement_ratio"]) for row in cases if isinstance(row.get("evidence_entanglement_ratio"), (int, float))]
    resolving = [float(row["resolving_coordinate_fraction"]) for row in cases if isinstance(row.get("resolving_coordinate_fraction"), (int, float))]
    return {
        "schema_version": "cortex-evidence-entanglement-panel/1.0",
        "case_count": len(cases),
        "entanglement_ratio": _distribution(entanglement),
        "resolving_coordinate_fraction": _distribution(resolving),
        "structural_only": True,
        "outcome_independent": True,
        "gate_effect": False,
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
        "cost_metrics": _invocation_cost_metrics(invocation),
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

    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for row in accepted:
        grouped.setdefault(str(row["family"]), {}).setdefault(str(row["difficulty_level"]), []).append(row)
    family_reports: dict[str, Any] = {}
    selected: dict[str, Any] = {}
    for family in sorted(str(name) for name in corpus.get("task_families") or TASK_FAMILIES):
        levels: dict[str, Any] = {}
        for level, level_rows in sorted(grouped.get(family, {}).items()):
            outcomes = [bool(row["success"]) for row in level_rows]
            level_cases = [cases[str(row["case_id"])] for row in level_rows]
            sequential = assess_sequential_level(
                outcomes,
                screening_cases=screening_cases,
                confirmation_cases=confirmation_cases,
            )
            levels[level] = {
                **sequential,
                "rasch": estimate_difficulty(outcomes),
                "cost_panel": summarize_observation_costs(level_rows, cases),
                "evidence_geometry": summarize_evidence_geometry(level_cases),
            }
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
    "summarize_evidence_geometry", "summarize_observation_costs",
    "verify_calibration_commissioning",
]
