"""v9.8.2 information-balanced task calibration.

Difficulty estimates guide development-corpus selection only.  They never
authorize a causal claim, select a model, or alter runtime policy.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .discriminability import assess_binary_task_family


SCHEMA_VERSION = "cortex-information-calibration/1.1"
VERSION = "9.8.3"
_FORBIDDEN_IDENTITY_KEYS = frozenset({"model", "model_id", "provider", "provider_family", "adapter", "adapter_id", "endpoint"})
_CALIBRATION_KEYS = frozenset({
    "schema_version", "version", "families", "selected", "overall_state",
    "reference_ability", "target_success_rate", "selection_objective",
    "development_only", "confirmatory_eligible", "model_identity_used_in_selection",
    "provider_identity_used_in_selection", "authority", "calibration_hash",
})


class InformationCalibrationError(ValueError):
    pass


def attainable_success_rates(case_count: int) -> list[float]:
    """Return the discrete Bernoulli rate lattice available at sample size n."""
    count = int(case_count)
    if count < 1:
        raise InformationCalibrationError("case_count must be positive")
    return [round(successes / count, 9) for successes in range(count + 1)]


def eligible_success_counts(
    case_count: int,
    *,
    minimum_success_rate: float = 0.30,
    maximum_success_rate: float = 0.70,
) -> list[int]:
    """Return exactly attainable success counts inside the information band."""
    if not 0.0 <= minimum_success_rate < maximum_success_rate <= 1.0:
        raise InformationCalibrationError("calibration success-rate bounds are invalid")
    rates = attainable_success_rates(case_count)
    return [
        successes
        for successes, rate in enumerate(rates)
        if minimum_success_rate <= rate <= maximum_success_rate
    ]


def assess_sequential_level(
    outcomes: Sequence[bool | int | float],
    *,
    screening_cases: int = 4,
    confirmation_cases: int = 8,
    minimum_success_rate: float = 0.30,
    maximum_success_rate: float = 0.70,
) -> dict[str, Any]:
    """Classify a level without pretending a four-case screen is calibration."""
    if screening_cases < 2 or confirmation_cases <= screening_cases:
        raise InformationCalibrationError("sequential sample sizes are invalid")
    normalized = [int(float(value) >= 0.5) for value in outcomes]
    count = len(normalized)
    successes = sum(normalized)
    if count < screening_cases:
        state, action = "insufficient_data", "collect_screening_cases"
    elif count < confirmation_cases:
        if successes == 0:
            state, action = "screening_floor", "move_easier"
        elif successes == count:
            state, action = "screening_ceiling", "move_harder"
        else:
            state, action = "screening_candidate", "collect_confirmation_cases"
    else:
        allowed = eligible_success_counts(
            count,
            minimum_success_rate=minimum_success_rate,
            maximum_success_rate=maximum_success_rate,
        )
        if successes in allowed:
            state, action = "calibrated", "retain_for_heldout_generation"
        elif successes / count > maximum_success_rate:
            state, action = "ceiling", "move_harder"
        else:
            state, action = "floor", "move_easier"
    return {
        "state": state,
        "recommended_action": action,
        "case_count": count,
        "success_count": successes,
        "success_rate": round(successes / count, 9) if count else None,
        "screening_cases": int(screening_cases),
        "confirmation_cases": int(confirmation_cases),
        "attainable_success_rates": attainable_success_rates(count) if count else [],
        "eligible_success_counts": eligible_success_counts(
            count,
            minimum_success_rate=minimum_success_rate,
            maximum_success_rate=maximum_success_rate,
        ) if count else [],
        "development_only": True,
        "confirmatory_eligible": False,
    }


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def rasch_success_probability(*, ability: float, difficulty: float) -> float:
    """Return sigma(ability-difficulty) using a numerically stable logistic."""
    offset = float(ability) - float(difficulty)
    if offset >= 0:
        decay = math.exp(-offset)
        return 1.0 / (1.0 + decay)
    growth = math.exp(offset)
    return growth / (1.0 + growth)


def item_information(*, ability: float, difficulty: float) -> float:
    """Rasch item information p(1-p), maximized at the capability boundary."""
    probability = rasch_success_probability(ability=ability, difficulty=difficulty)
    return probability * (1.0 - probability)


def estimate_difficulty(
    outcomes: Sequence[bool | int | float],
    *,
    reference_ability: float = 0.0,
) -> dict[str, Any]:
    """Estimate beta from development outcomes with Jeffreys smoothing."""
    normalized = [int(float(value) >= 0.5) for value in outcomes]
    count = len(normalized)
    if not count:
        return {
            "state": "unknown",
            "case_count": 0,
            "success_rate": None,
            "smoothed_success_probability": None,
            "estimated_difficulty": None,
            "item_information": None,
        }
    success_count = sum(normalized)
    probability = (success_count + 0.5) / (count + 1.0)
    difficulty = float(reference_ability) - math.log(probability / (1.0 - probability))
    return {
        "state": "estimated",
        "case_count": count,
        "success_count": success_count,
        "success_rate": round(success_count / count, 9),
        "smoothed_success_probability": round(probability, 9),
        "estimated_difficulty": round(difficulty, 9),
        "item_information": round(probability * (1.0 - probability), 9),
        "reference_ability": float(reference_ability),
        "estimator": "rasch_logit_with_jeffreys_smoothing",
    }


def calibrate_difficulty_ladders(
    family_ladders: Mapping[str, Mapping[str | int, Sequence[bool | int | float]]],
    *,
    reference_ability: float = 0.0,
    minimum_cases_per_level: int = 4,
    minimum_success_rate: float = 0.30,
    maximum_success_rate: float = 0.70,
) -> dict[str, Any]:
    """Select the most informative eligible level within each task family."""
    family_reports: dict[str, Any] = {}
    selected: dict[str, Any] = {}
    for family, ladder in sorted(family_ladders.items()):
        levels: dict[str, Any] = {}
        for level, outcomes in sorted(ladder.items(), key=lambda item: str(item[0])):
            discrimination = assess_binary_task_family(
                outcomes,
                minimum_cases=minimum_cases_per_level,
                minimum_success_rate=minimum_success_rate,
                maximum_success_rate=maximum_success_rate,
            )
            levels[str(level)] = {
                "difficulty_level": str(level),
                "discriminability": discrimination,
                "rasch": estimate_difficulty(outcomes, reference_ability=reference_ability),
            }
        candidates = [row for row in levels.values() if row["discriminability"]["state"] == "pass"]
        candidates.sort(key=lambda row: (-float(row["rasch"]["item_information"] or 0.0), str(row["difficulty_level"])))
        chosen = candidates[0] if candidates else None
        if chosen is not None:
            state, action = "pass", "retain_for_heldout_generation"
            selected[str(family)] = {
                "difficulty_level": chosen["difficulty_level"],
                "estimated_difficulty": chosen["rasch"]["estimated_difficulty"],
                "item_information": chosen["rasch"]["item_information"],
            }
        else:
            states = [row["discriminability"]["classification"] for row in levels.values()]
            state = "unknown" if not levels or "insufficient_sample" in states else "fail"
            if states and all(value == "ceiling" for value in states):
                action = "increase_difficulty"
            elif states and all(value == "floor" for value in states):
                action = "decrease_difficulty"
            else:
                action = "collect_or_rebalance_development_cases"
        family_reports[str(family)] = {"state": state, "recommended_action": action, "levels": levels}
    overall = "pass" if selected and len(selected) == len(family_reports) else ("unknown" if not family_reports else "held")
    material = {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "families": family_reports,
        "selected": selected,
        "overall_state": overall,
        "reference_ability": float(reference_ability),
        "target_success_rate": [float(minimum_success_rate), float(maximum_success_rate)],
        "selection_objective": "maximize_item_information_within_noncompensatory_discriminability_gate",
        "development_only": True,
        "confirmatory_eligible": False,
        "model_identity_used_in_selection": False,
        "provider_identity_used_in_selection": False,
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }
    return {**material, "calibration_hash": _sha(material)}


def verify_difficulty_calibration(receipt: Mapping[str, Any]) -> dict[str, Any]:
    material = {str(key): value for key, value in receipt.items() if str(key) != "calibration_hash"}
    errors: list[str] = []
    if material.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if receipt.get("calibration_hash") != _sha(material):
        errors.append("calibration_hash_invalid")
    if material.get("development_only") is not True or material.get("confirmatory_eligible") is not False:
        errors.append("calibration_boundary_invalid")
    if material.get("model_identity_used_in_selection") is not False or material.get("provider_identity_used_in_selection") is not False:
        errors.append("identity_leakage")
    if set(str(key) for key in receipt) != _CALIBRATION_KEYS:
        errors.append("calibration_schema_not_closed")

    def contains_identity(value: Any) -> bool:
        if isinstance(value, Mapping):
            return any(str(key).strip().lower() in _FORBIDDEN_IDENTITY_KEYS or contains_identity(nested) for key, nested in value.items())
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return any(contains_identity(item) for item in value)
        return False

    if contains_identity(receipt):
        errors.append("model_provider_identity_forbidden")
    return {"valid": not errors, "state": "pass" if not errors else "fail", "errors": errors}


__all__ = [
    "InformationCalibrationError",
    "SCHEMA_VERSION",
    "VERSION",
    "assess_sequential_level",
    "attainable_success_rates",
    "calibrate_difficulty_ladders",
    "eligible_success_counts",
    "estimate_difficulty",
    "item_information",
    "rasch_success_probability",
    "verify_difficulty_calibration",
]
