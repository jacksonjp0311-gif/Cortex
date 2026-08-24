"""v9.7 provider-neutral empirical competence differentiation.

This module analyzes matched A-E transfer trials already preserved by Cortex.
It never invokes a model and never uses provider or model identity as a scoring
feature.  Those identities remain in the underlying invocation provenance.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Mapping, Sequence
from typing import Any

from .adapter_provenance import (
    EVIDENCE_ATTESTED,
    EVIDENCE_LIVE,
    EVIDENCE_SIMULATED,
    EVIDENCE_SYNTHETIC,
)
from .competence_transfer import get_transfer_trial, verify_transfer_trial

SCHEMA = "cortex-competence-differentiation/1.1"
LEGACY_SCHEMA = "cortex-competence-differentiation/1.0"
VERSION = "9.7.0"
GLYPH = "Δ⟡"
CLAIM_BOUNDARY = (
    "Differentiation receipts estimate paired competence effects over canonical "
    "transfer trials. They do not prove universal competence, cognition, "
    "authority, causality outside the frozen cohort, or permission to distribute."
)

DEFAULT_POLICY: dict[str, Any] = {
    "minimum_cases": 8,
    "minimum_effect": 0.05,
    "maximum_baseline_mean": 0.90,
    "minimum_competence_mean": 0.20,
    "minimum_dynamic_range": 0.10,
    "confidence_z": 1.96,
    "maximum_negative_transfer_rate": 0.10,
    "required_evidence_class": "live_empirical",
    "require_same_epoch": True,
    "require_same_measurement_cohort": True,
}
_POLICY_KEYS = frozenset(DEFAULT_POLICY)
_EFFECTS = {
    "continuity": ("D", "A"),
    "distillation": ("D", "B"),
    "governance": ("D", "C"),
    "credit": ("E", "D"),
}


class DifferentiationError(ValueError):
    """Raised when a differentiation cohort cannot be constructed safely."""


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _repo_identity(store: Any, repo: str) -> str:
    row = store.repo(repo)
    if row is None:
        raise DifferentiationError(f"Unknown repository: {repo}")
    repository_id = str(row["repository_id"] or "")
    if not repository_id:
        raise DifferentiationError("repository identity is missing")
    return repository_id


def _policy(value: Mapping[str, Any] | None) -> dict[str, Any]:
    result = json.loads(_canonical(DEFAULT_POLICY))
    if value is not None:
        if not isinstance(value, Mapping):
            raise DifferentiationError("differentiation policy must be a mapping")
        unknown = sorted(str(key) for key in value if str(key) not in _POLICY_KEYS)
        if unknown:
            raise DifferentiationError(
                "unsupported differentiation policy fields: " + ",".join(unknown)
            )
        result.update(dict(value))
    result["minimum_cases"] = max(2, int(result["minimum_cases"]))
    for key in (
        "minimum_effect",
        "maximum_baseline_mean",
        "minimum_competence_mean",
        "minimum_dynamic_range",
        "confidence_z",
        "maximum_negative_transfer_rate",
    ):
        result[key] = float(result[key])
    if result["confidence_z"] <= 0:
        raise DifferentiationError("confidence_z must be positive")
    if str(result["required_evidence_class"]) not in {
        "live_empirical",
        "empirically_attested",
        "structural",
    }:
        raise DifferentiationError("required_evidence_class is unsupported")
    result["require_same_epoch"] = bool(result["require_same_epoch"])
    result["require_same_measurement_cohort"] = bool(
        result["require_same_measurement_cohort"]
    )
    return result


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _paired_panel(values: Sequence[float], confidence_z: float) -> dict[str, Any]:
    numbers = [float(item) for item in values]
    n = len(numbers)
    mean = _mean(numbers)
    variance = (
        sum((item - mean) ** 2 for item in numbers) / (n - 1) if n > 1 else 0.0
    )
    standard_error = math.sqrt(variance / n) if n else 0.0
    margin = confidence_z * standard_error
    return {
        "n": n,
        "mean": round(mean, 9),
        "sample_standard_deviation": round(math.sqrt(variance), 9),
        "standard_error": round(standard_error, 9),
        "lower_confidence_bound": round(mean - margin, 9),
        "upper_confidence_bound": round(mean + margin, 9),
        "negative_count": sum(1 for item in numbers if item < 0),
        "zero_count": sum(1 for item in numbers if item == 0),
        "positive_count": sum(1 for item in numbers if item > 0),
    }


def _evidence_gate(classes: Sequence[str], required: str) -> tuple[bool, str]:
    empirical = {EVIDENCE_LIVE, EVIDENCE_ATTESTED}
    if required == "structural":
        known = {
            EVIDENCE_SYNTHETIC,
            EVIDENCE_SIMULATED,
            EVIDENCE_LIVE,
            EVIDENCE_ATTESTED,
        }
        if not classes or any(item not in known for item in classes):
            return False, "canonical_structural_evidence_missing"
        return True, "structural_evidence_accepted"
    if not classes or any(item not in empirical for item in classes):
        return False, "required_empirical_evidence_missing"
    if required == "empirically_attested" and any(
        item != EVIDENCE_ATTESTED for item in classes
    ):
        return False, "provider_attestation_required"
    return True, "required_empirical_evidence_present"


def _build_receipt(
    store: Any,
    repo: str,
    *,
    competence_id: str,
    trial_ids: Sequence[str],
    policy: Mapping[str, Any],
    cohort_nonce: str,
    evaluated_at: float,
) -> dict[str, Any]:
    repository_id = _repo_identity(store, repo)
    unique_ids = [str(item) for item in trial_ids]
    if len(unique_ids) != len(set(unique_ids)):
        raise DifferentiationError("differentiation trial IDs must be unique")
    if not unique_ids:
        raise DifferentiationError("at least one canonical trial is required")

    cases: list[dict[str, Any]] = []
    epochs: set[str] = set()
    cohorts: set[str] = set()
    evidence_classes: list[str] = []
    errors: list[str] = []
    task_contract_hashes: set[str] = set()
    for trial_id in unique_ids:
        check = verify_transfer_trial(store, repo, trial_id)
        trial = get_transfer_trial(store, repo, trial_id)
        if trial is None:
            errors.append(f"trial_missing:{trial_id}")
            continue
        if check.get("valid") is not True:
            errors.append(f"trial_invalid:{trial_id}")
            continue
        if str(trial.get("competence_id") or "") != str(competence_id):
            errors.append(f"competence_mismatch:{trial_id}")
            continue
        arms = trial.get("arm_results")
        if not isinstance(arms, Mapping) or any(arm not in arms for arm in "ABCDE"):
            errors.append(f"matched_arms_missing:{trial_id}")
            continue
        scores = {
            arm: float(
                (
                    (arms[arm] or {}).get("metrics")
                    if isinstance((arms[arm] or {}).get("metrics"), Mapping)
                    else {}
                ).get("task_success")
                or 0.0
            )
            for arm in "ABCDE"
        }
        utilities = {
            arm: float((arms[arm] or {}).get("U") or 0.0) for arm in "ABCDE"
        }
        case_effects = {
            name: round(scores[left] - scores[right], 9)
            for name, (left, right) in _EFFECTS.items()
        }
        arm_classes = check.get("arm_evidence_classes")
        arm_classes = arm_classes if isinstance(arm_classes, Mapping) else {}
        evidence_components = [
            str(trial.get("origin_evidence_class") or "unknown"),
            *[str(arm_classes.get(arm) or "unknown") for arm in "ABCDE"],
        ]
        empirical = {EVIDENCE_LIVE, EVIDENCE_ATTESTED}
        evidence_class = (
            EVIDENCE_ATTESTED
            if evidence_components
            and all(item == EVIDENCE_ATTESTED for item in evidence_components)
            else EVIDENCE_LIVE
            if evidence_components and all(item in empirical for item in evidence_components)
            else str(check.get("evidence_class") or "unknown")
        )
        evidence_classes.append(evidence_class)
        epoch = str(trial.get("body_epoch_id") or "")
        cohort = str(trial.get("measurement_cohort_id") or "")
        epochs.add(epoch)
        cohorts.add(cohort)
        task_contract_hashes.add(str(trial.get("task_contract_hash") or ""))
        cases.append(
            {
                "trial_id": trial_id,
                "trial_receipt_hash": trial.get("receipt_hash"),
                "task_contract_hash": trial.get("task_contract_hash"),
                "body_epoch_id": epoch,
                "measurement_cohort_id": cohort or None,
                "evidence_class": evidence_class,
                "evidence_component_classes": evidence_components,
                "scores": scores,
                "composite_utilities": utilities,
                "effects": case_effects,
            }
        )

    if policy["require_same_epoch"] and (len(epochs) != 1 or "" in epochs):
        errors.append("epoch_cohort_incompatible")
    if policy["require_same_measurement_cohort"] and (
        len(cohorts) != 1 or "" in cohorts
    ):
        errors.append("measurement_cohort_incompatible")

    panels = {
        name: _paired_panel(
            [float(case["effects"][name]) for case in cases],
            float(policy["confidence_z"]),
        )
        for name in _EFFECTS
    }
    baseline_mean = _mean([float(case["scores"]["A"]) for case in cases])
    competence_mean = _mean([float(case["scores"]["D"]) for case in cases])
    all_primary = [
        float(case["scores"][arm]) for case in cases for arm in ("A", "D")
    ]
    dynamic_range = max(all_primary) - min(all_primary) if all_primary else 0.0
    negative_rate = (
        sum(1 for case in cases if float(case["effects"]["continuity"]) < 0)
        / len(cases)
        if cases
        else 0.0
    )
    evidence_pass, evidence_reason = _evidence_gate(
        evidence_classes, str(policy["required_evidence_class"])
    )
    gates = {
        "canonical_trials": {"passed": not errors, "observed": list(errors)},
        "minimum_cases": {
            "passed": len(cases) >= int(policy["minimum_cases"]),
            "observed": len(cases),
            "required": int(policy["minimum_cases"]),
        },
        "ceiling": {
            "passed": baseline_mean < float(policy["maximum_baseline_mean"]),
            "observed": round(baseline_mean, 9),
            "maximum": float(policy["maximum_baseline_mean"]),
        },
        "floor": {
            "passed": competence_mean >= float(policy["minimum_competence_mean"]),
            "observed": round(competence_mean, 9),
            "minimum": float(policy["minimum_competence_mean"]),
        },
        "dynamic_range": {
            "passed": dynamic_range >= float(policy["minimum_dynamic_range"]),
            "observed": round(dynamic_range, 9),
            "minimum": float(policy["minimum_dynamic_range"]),
        },
        "paired_effect": {
            "passed": all(
                panels[name]["lower_confidence_bound"]
                >= float(policy["minimum_effect"])
                for name in ("continuity", "distillation", "governance")
            ),
            "minimum": float(policy["minimum_effect"]),
        },
        "negative_transfer": {
            "passed": negative_rate
            <= float(policy["maximum_negative_transfer_rate"]),
            "observed": round(negative_rate, 9),
            "maximum": float(policy["maximum_negative_transfer_rate"]),
        },
        "evidence_class": {
            "passed": evidence_pass,
            "observed": sorted(set(evidence_classes)),
            "required": policy["required_evidence_class"],
            "reason": evidence_reason,
        },
    }
    promotion = all(bool(item["passed"]) for item in gates.values())
    if promotion and policy["required_evidence_class"] == "structural":
        status = "STRUCTURAL_DIFFERENTIATION_PASS"
    elif promotion:
        status = "EMPIRICAL_DIFFERENTIATION_VERIFIED"
    else:
        status = "DIFFERENTIATION_HELD"
    failed_gates = sorted(key for key, value in gates.items() if not value["passed"])
    identity_material = {
        "schema_version": SCHEMA,
        "repository_id": repository_id,
        "repo": repo,
        "competence_id": str(competence_id),
        "trial_bindings": [
            {
                "trial_id": case["trial_id"],
                "trial_receipt_hash": case["trial_receipt_hash"],
            }
            for case in cases
        ],
        "policy": dict(policy),
        "cohort_nonce": str(cohort_nonce),
    }
    receipt: dict[str, Any] = {
        **identity_material,
        "cohort_id": _sha(identity_material),
        "version": VERSION,
        "glyph": GLYPH,
        "evaluated_at": float(evaluated_at),
        "case_count": len(cases),
        "task_contract_hashes": sorted(task_contract_hashes),
        "cases": cases,
        "paired_effects": panels,
        "discriminability": {
            "baseline_mean": round(baseline_mean, 9),
            "competence_mean": round(competence_mean, 9),
            "dynamic_range": round(dynamic_range, 9),
            "ceiling_detected": not gates["ceiling"]["passed"],
            "floor_detected": not gates["floor"]["passed"],
        },
        "negative_transfer_rate": round(negative_rate, 9),
        "gates": gates,
        "failed_gates": failed_gates,
        "status": status,
        "promotion_eligible": promotion,
        "model_identity_used_in_scoring": False,
        "provider_identity_used_in_scoring": False,
        "primary_score_basis": "canonical_task_evaluation_success",
        "composite_utility_role": "secondary_cost_and_quality_diagnostic_only",
        "distribution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "execution_authorized": False,
        "host_mutate_authorized": False,
        "advisory_only": True,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    receipt["receipt_hash"] = _sha(receipt)
    return receipt


def ensure_differentiation_tables(store: Any) -> None:
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS competence_differentiation_receipts(
            cohort_id TEXT PRIMARY KEY CHECK(length(cohort_id) = 64),
            receipt_hash TEXT NOT NULL CHECK(length(receipt_hash) = 64),
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            competence_id TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            created_at REAL NOT NULL,
            UNIQUE(repository_id, receipt_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_competence_differentiation_repo
            ON competence_differentiation_receipts(repo, created_at DESC);
        CREATE TRIGGER IF NOT EXISTS competence_differentiation_no_update
        BEFORE UPDATE ON competence_differentiation_receipts
        BEGIN
            SELECT RAISE(ABORT, 'canonical differentiation receipts cannot be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS competence_differentiation_no_delete
        BEFORE DELETE ON competence_differentiation_receipts
        BEGIN
            SELECT RAISE(ABORT, 'canonical differentiation receipts cannot be deleted');
        END;
        """
    )
    store.db.commit()


def _append(store: Any, repo: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
    ensure_differentiation_tables(store)
    repository_id = _repo_identity(store, repo)
    body = dict(receipt)
    expected = _sha({key: value for key, value in body.items() if key != "receipt_hash"})
    if expected != str(body.get("receipt_hash") or ""):
        raise DifferentiationError("differentiation receipt hash is invalid")
    if any(
        body.get(key) is not False
        for key in (
            "distribution_authorized",
            "memory_admission_authorized",
            "policy_effect",
            "execution_authorized",
            "host_mutate_authorized",
        )
    ):
        raise DifferentiationError("differentiation receipts cannot carry authority")
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT receipt_hash, receipt_json FROM competence_differentiation_receipts WHERE cohort_id=?",
            (str(body["cohort_id"]),),
        ).fetchone()
        if existing is not None:
            if str(existing["receipt_hash"]) != str(body["receipt_hash"]):
                raise DifferentiationError("cohort identity already has different content")
            return {**json.loads(str(existing["receipt_json"])), "inserted": False, "duplicate": True}
        conn.execute(
            "INSERT INTO competence_differentiation_receipts VALUES(?, ?, ?, ?, ?, ?, ?)",
            (
                str(body["cohort_id"]),
                str(body["receipt_hash"]),
                repository_id,
                repo,
                str(body["competence_id"]),
                _canonical(body),
                float(body["evaluated_at"]),
            ),
        )
    return {**body, "inserted": True, "duplicate": False}


def get_differentiation_receipt(
    store: Any, repo: str, cohort_id: str
) -> dict[str, Any] | None:
    repository_id = _repo_identity(store, repo)
    row = store.db.execute(
        "SELECT receipt_json FROM competence_differentiation_receipts WHERE repository_id=? AND repo=? AND cohort_id=?",
        (repository_id, repo, str(cohort_id)),
    ).fetchone()
    if row is None:
        return None
    value = json.loads(str(row["receipt_json"]))
    return dict(value) if isinstance(value, Mapping) else None


def evaluate_competence_differentiation(
    store: Any,
    repo: str,
    *,
    competence_id: str,
    trial_ids: Sequence[str],
    policy: Mapping[str, Any] | None = None,
    cohort_nonce: str,
    persist: bool = True,
) -> dict[str, Any]:
    """Reconstruct paired effects from canonical trials without model features."""
    frozen_policy = _policy(policy)
    receipt = _build_receipt(
        store,
        repo,
        competence_id=competence_id,
        trial_ids=trial_ids,
        policy=frozen_policy,
        cohort_nonce=str(cohort_nonce),
        evaluated_at=time.time(),
    )
    return _append(store, repo, receipt) if persist else {**receipt, "persisted": False}


def verify_differentiation_receipt(
    store: Any, repo: str, cohort_id: str
) -> dict[str, Any]:
    stored = get_differentiation_receipt(store, repo, cohort_id)
    if stored is None:
        return {"valid": False, "errors": ["differentiation_receipt_missing"]}
    errors: list[str] = []
    expected_hash = _sha(
        {key: value for key, value in stored.items() if key != "receipt_hash"}
    )
    if expected_hash != str(stored.get("receipt_hash") or ""):
        errors.append("differentiation_receipt_hash_invalid")
    if str(stored.get("schema_version") or "") == LEGACY_SCHEMA:
        return {
            "valid": not errors,
            "errors": errors,
            "cohort_id": cohort_id,
            "receipt_hash": stored.get("receipt_hash"),
            "status": stored.get("status"),
            "promotion_eligible": False,
            "legacy_partial": True,
            "model_identity_used_in_scoring": False,
            "provider_identity_used_in_scoring": False,
            "distribution_authorized": False,
            "execution_authorized": False,
            "host_mutate_authorized": False,
            "advisory_only": True,
        }
    rebuilt = _build_receipt(
        store,
        repo,
        competence_id=str(stored.get("competence_id") or ""),
        trial_ids=[str(item.get("trial_id") or "") for item in stored.get("cases") or ()],
        policy=_policy(stored.get("policy") if isinstance(stored.get("policy"), Mapping) else None),
        cohort_nonce=str(stored.get("cohort_nonce") or ""),
        evaluated_at=float(stored.get("evaluated_at") or 0.0),
    )
    if rebuilt != stored:
        errors.append("differentiation_receipt_not_reconstructed")
    return {
        "valid": not errors,
        "errors": errors,
        "cohort_id": cohort_id,
        "receipt_hash": stored.get("receipt_hash"),
        "status": rebuilt.get("status"),
        "promotion_eligible": bool(rebuilt.get("promotion_eligible")) and not errors,
        "model_identity_used_in_scoring": False,
        "provider_identity_used_in_scoring": False,
        "distribution_authorized": False,
        "execution_authorized": False,
        "host_mutate_authorized": False,
        "advisory_only": True,
    }


__all__ = [
    "CLAIM_BOUNDARY",
    "DEFAULT_POLICY",
    "DifferentiationError",
    "evaluate_competence_differentiation",
    "get_differentiation_receipt",
    "verify_differentiation_receipt",
]
