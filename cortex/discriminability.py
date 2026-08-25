"""v9.8.1 information diagnostics for causal competence experiments.

These functions measure whether an experiment can distinguish treatment from
control.  They are advisory design evidence; no score produced here grants
execution, memory, distribution, or policy authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA_VERSION = "cortex-discriminability/1.0"
VERSION = "9.8.1"
_STATE_ORDER = {"fail": 0, "unknown": 1, "pass": 2}


class DiscriminabilityError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def binary_entropy(success_probability: float) -> float:
    """Return Bernoulli entropy in bits, including honest zero-entropy edges."""
    probability = float(success_probability)
    if not 0.0 <= probability <= 1.0:
        raise DiscriminabilityError("success probability must be between zero and one")
    if probability in {0.0, 1.0}:
        return 0.0
    return -(probability * math.log2(probability) + (1.0 - probability) * math.log2(1.0 - probability))


def assess_binary_task_family(
    outcomes: Sequence[bool | int | float],
    *,
    minimum_cases: int = 4,
    minimum_success_rate: float = 0.30,
    maximum_success_rate: float = 0.70,
) -> dict[str, Any]:
    """Classify a development-only task family as floor, informative, or ceiling."""
    if minimum_cases < 2:
        raise DiscriminabilityError("minimum_cases must be at least two")
    if not 0.0 <= minimum_success_rate < maximum_success_rate <= 1.0:
        raise DiscriminabilityError("calibration success-rate bounds are invalid")
    normalized = [int(float(value) >= 0.5) for value in outcomes]
    count = len(normalized)
    success_count = sum(normalized)
    success_rate = success_count / count if count else None
    if count < minimum_cases:
        state, classification = "unknown", "insufficient_sample"
    elif success_rate is not None and success_rate > maximum_success_rate:
        state, classification = "fail", "ceiling"
    elif success_rate is not None and success_rate < minimum_success_rate:
        state, classification = "fail", "floor"
    else:
        state, classification = "pass", "informative"
    entropy = binary_entropy(success_rate) if success_rate is not None else None
    return {
        "state": state,
        "classification": classification,
        "case_count": count,
        "success_count": success_count,
        "failure_count": count - success_count,
        "success_rate": round(success_rate, 9) if success_rate is not None else None,
        "binary_entropy_bits": round(entropy, 9) if entropy is not None else None,
        "minimum_cases": int(minimum_cases),
        "target_success_rate": [float(minimum_success_rate), float(maximum_success_rate)],
        "confirmatory_candidate": state == "pass",
    }


def assess_paired_information(
    control: Sequence[bool | int | float],
    treatment: Sequence[bool | int | float],
) -> dict[str, Any]:
    """Expose the discordant pairs that constitute effective causal information."""
    if len(control) != len(treatment):
        raise DiscriminabilityError("paired panels must have equal length")
    pairs = [(int(float(a) >= 0.5), int(float(b) >= 0.5)) for a, b in zip(control, treatment)]
    benefit = sum(1 for a, b in pairs if a == 0 and b == 1)
    harm = sum(1 for a, b in pairs if a == 1 and b == 0)
    discordant = benefit + harm
    total = len(pairs)
    return {
        "case_count": total,
        "benefit_pairs": benefit,
        "harm_pairs": harm,
        "discordant_pairs": discordant,
        "effective_causal_sample": discordant,
        "discordance_rate": round(discordant / total, 9) if total else None,
        "paired_risk_difference": round((benefit - harm) / total, 9) if total else None,
        "state": "pass" if discordant else ("unknown" if not total else "fail"),
        "reason": "discordant_pairs_observed" if discordant else ("empty_panel" if not total else "measurement_collapse"),
    }


def assess_task_panel(
    family_outcomes: Mapping[str, Sequence[bool | int | float]],
    *,
    minimum_cases: int = 4,
    minimum_success_rate: float = 0.30,
    maximum_success_rate: float = 0.70,
) -> dict[str, Any]:
    """Create a hash-bound, development-only calibration panel."""
    families = {
        str(name): assess_binary_task_family(
            outcomes,
            minimum_cases=minimum_cases,
            minimum_success_rate=minimum_success_rate,
            maximum_success_rate=maximum_success_rate,
        )
        for name, outcomes in sorted(family_outcomes.items())
    }
    states = [row["state"] for row in families.values()]
    overall = min(states, key=lambda state: _STATE_ORDER[state]) if states else "unknown"
    material = {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "families": families,
        "overall_state": overall,
        "selected_families": sorted(name for name, row in families.items() if row["state"] == "pass"),
        "development_only": True,
        "confirmatory_eligible": False,
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }
    return {**material, "calibration_hash": _sha(material)}


def verify_task_panel(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the calibration hash and its permanently non-confirmatory type."""
    material = {str(key): value for key, value in receipt.items() if str(key) != "calibration_hash"}
    errors: list[str] = []
    if material.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if receipt.get("calibration_hash") != _sha(material):
        errors.append("calibration_hash_invalid")
    if material.get("development_only") is not True or material.get("confirmatory_eligible") is not False:
        errors.append("calibration_type_invalid")
    families = material.get("families")
    if not isinstance(families, Mapping):
        errors.append("family_panel_missing")
    return {"valid": not errors, "errors": errors, "state": "pass" if not errors else "fail"}


def evidence_geometry(
    *,
    semantic_evidence: str,
    discriminability: str,
    independent_replication: str,
    diagnostic_strengths: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Compose E/D/I noncompensatorily; continuous quality stays diagnostic."""
    axes = {
        "semantic_evidence": str(semantic_evidence).lower(),
        "discriminability": str(discriminability).lower(),
        "independent_replication": str(independent_replication).lower(),
    }
    if any(state not in _STATE_ORDER for state in axes.values()):
        raise DiscriminabilityError("evidence geometry states must be fail, unknown, or pass")
    readiness = min(axes.values(), key=lambda state: _STATE_ORDER[state])
    quality = None
    if diagnostic_strengths is not None:
        values = [float(diagnostic_strengths[name]) for name in ("semantic_evidence", "discriminability", "independent_replication")]
        if any(not 0.0 <= value <= 1.0 for value in values):
            raise DiscriminabilityError("diagnostic strengths must be between zero and one")
        quality = round(math.prod(values) ** (1.0 / 3.0), 9)
    return {
        "axes": axes,
        "readiness": readiness,
        "composition_law": "minimum_noncompensatory",
        "diagnostic_geometric_mean": quality,
        "diagnostic_can_open_gate": False,
        "claim_boundary": "Evidence geometry measures research readiness, not cognition or authority.",
    }


__all__ = [
    "DiscriminabilityError",
    "SCHEMA_VERSION",
    "VERSION",
    "assess_binary_task_family",
    "assess_paired_information",
    "assess_task_panel",
    "binary_entropy",
    "evidence_geometry",
    "verify_task_panel",
]
