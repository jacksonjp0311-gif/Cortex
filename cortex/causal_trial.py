"""v9.8 preregistered, model-neutral causal competence analysis."""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Mapping, Sequence
from typing import Any

from .competence_differentiation import evaluate_competence_differentiation
from .competence_transfer import get_transfer_trial
from .distillation_witness import get_distillation_witness, verify_distillation_witness

PREREG_SCHEMA = "cortex-causal-preregistration/1.0"
RESULT_SCHEMA = "cortex-preregistered-causal-result/1.0"
VERSION = "9.8.0"
PRIMARY_COMPARISONS = {"continuity": ("A", "D"), "distillation": ("B", "D"), "governance": ("C", "D")}
STANDARD_ARMS = {
    "A": "ordinary_context",
    "B": "raw_public_origin_history",
    "C": "admitted_memory",
    "D": "distilled_competence",
    "E": "distilled_competence_plus_verified_feedback",
    "S": "sham_competence",
    "I": "irrelevant_competence",
    "X": "corrupted_competence",
    "H": "shuffled_competence",
    "P": "omitted_prerequisite_competence",
}
_FORBIDDEN_KEYS = frozenset({"model", "model_id", "provider", "provider_family", "endpoint", "adapter_id"})


class CausalTrialError(ValueError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _reject_model_fields(value: Any, path: str = "preregistration") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized = str(key).strip().lower()
            if normalized in _FORBIDDEN_KEYS:
                raise CausalTrialError(f"model/provider field is forbidden in causal policy: {path}.{key}")
            _reject_model_fields(nested, f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, nested in enumerate(value):
            _reject_model_fields(nested, f"{path}[{index}]")


def _repo_identity(store: Any, repo: str) -> str:
    row = store.repo(repo)
    if row is None or not str(row["repository_id"] or ""):
        raise CausalTrialError(f"Unknown repository: {repo}")
    return str(row["repository_id"])


def ensure_causal_trial_tables(store: Any) -> None:
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS causal_preregistrations(
            preregistration_id TEXT PRIMARY KEY,
            receipt_hash TEXT NOT NULL UNIQUE,
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            competence_id TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS causal_preregistration_no_update
        BEFORE UPDATE ON causal_preregistrations BEGIN
            SELECT RAISE(ABORT, 'causal preregistrations are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS causal_preregistration_no_delete
        BEFORE DELETE ON causal_preregistrations BEGIN
            SELECT RAISE(ABORT, 'causal preregistrations are immutable');
        END;
        CREATE TABLE IF NOT EXISTS causal_trial_results(
            result_id TEXT PRIMARY KEY,
            receipt_hash TEXT NOT NULL UNIQUE,
            repository_id TEXT NOT NULL,
            repo TEXT NOT NULL,
            preregistration_id TEXT NOT NULL,
            status TEXT NOT NULL,
            receipt_json TEXT NOT NULL,
            created_at REAL NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS causal_trial_result_no_update
        BEFORE UPDATE ON causal_trial_results BEGIN
            SELECT RAISE(ABORT, 'causal trial results are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS causal_trial_result_no_delete
        BEFORE DELETE ON causal_trial_results BEGIN
            SELECT RAISE(ABORT, 'causal trial results are immutable');
        END;
        """
    )


def get_causal_preregistration(store: Any, repo: str, preregistration_id: str) -> dict[str, Any] | None:
    ensure_causal_trial_tables(store)
    row = store.db.execute(
        "SELECT receipt_json FROM causal_preregistrations WHERE repo=? AND preregistration_id=?",
        (str(repo), str(preregistration_id)),
    ).fetchone()
    return json.loads(str(row["receipt_json"])) if row is not None else None


def create_causal_preregistration(
    store: Any,
    repo: str,
    *,
    competence_id: str,
    distillation_witness_id: str,
    task_corpus_hash: str,
    task_contract_hashes: Sequence[str],
    planned_cases: int,
    randomization_seed_commitment: str,
    minimum_effects: Mapping[str, float],
    negative_transfer_threshold: float,
    alpha: float,
    stopping_rule: Mapping[str, Any],
    exclusion_rules: Sequence[Mapping[str, Any] | str],
    multiplicity_policy: str = "holm",
    task_family_strata: Sequence[str] = (),
    capability_class_strata: Sequence[str] = (),
    arms: Sequence[str] = tuple(STANDARD_ARMS),
) -> dict[str, Any]:
    """Freeze the causal design before any bound transfer trial exists."""
    repository_id = _repo_identity(store, repo)
    arm_names = [str(arm) for arm in arms]
    if any(arm not in STANDARD_ARMS for arm in arm_names) or any(arm not in arm_names for arm in "ABCDE"):
        raise CausalTrialError("preregistration must contain A-E and only declared causal arms")
    if planned_cases < 2:
        raise CausalTrialError("planned_cases must come from a design with at least two matched cases")
    if multiplicity_policy != "holm":
        raise CausalTrialError("v9.8 confirmatory primary comparisons require Holm correction")
    if not 0 < float(alpha) < 1:
        raise CausalTrialError("alpha must be between zero and one")
    minimum = {name: float(minimum_effects[name]) for name in PRIMARY_COMPARISONS}
    material = {
        "schema_version": PREREG_SCHEMA,
        "repository_id": repository_id,
        "repo": str(repo),
        "competence_id": str(competence_id),
        "distillation_witness_id": str(distillation_witness_id),
        "task_corpus_hash": str(task_corpus_hash),
        "task_contract_hashes": sorted(str(item) for item in task_contract_hashes),
        "planned_cases": int(planned_cases),
        "arms": {arm: STANDARD_ARMS[arm] for arm in arm_names},
        "randomization_seed_commitment": str(randomization_seed_commitment),
        "minimum_effects": minimum,
        "negative_transfer_threshold": float(negative_transfer_threshold),
        "alpha": float(alpha),
        "primary_test": "exact_conditional_binomial_on_discordant_pairs",
        "multiplicity_policy": multiplicity_policy,
        "stopping_rule": dict(stopping_rule),
        "exclusion_rules": list(exclusion_rules),
        "task_family_strata": sorted(str(item) for item in task_family_strata),
        "capability_class_strata": sorted(str(item) for item in capability_class_strata),
        "required_evidence_class": "live_empirical",
    }
    _reject_model_fields(material)
    preregistration_id = _sha(material)
    receipt: dict[str, Any] = {
        **material,
        "preregistration_id": preregistration_id,
        "version": VERSION,
        "created_at": time.time(),
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "policy_effect": False,
        "advisory_only": True,
    }
    receipt["receipt_hash"] = _sha(receipt)
    ensure_causal_trial_tables(store)
    with store.transaction() as conn:
        existing = conn.execute(
            "SELECT receipt_json FROM causal_preregistrations WHERE preregistration_id=?",
            (preregistration_id,),
        ).fetchone()
        if existing is not None:
            return json.loads(str(existing["receipt_json"]))
        conn.execute(
            "INSERT INTO causal_preregistrations VALUES(?, ?, ?, ?, ?, ?, ?)",
            (preregistration_id, receipt["receipt_hash"], repository_id, repo, competence_id, _canonical(receipt), receipt["created_at"]),
        )
    return receipt


def exact_matched_binary(control: Sequence[float], treatment: Sequence[float]) -> dict[str, Any]:
    """Return paired risk difference and exact two-sided discordance test."""
    if len(control) != len(treatment):
        raise CausalTrialError("matched binary panels must have equal length")
    pairs = [(int(float(a) >= 0.5), int(float(b) >= 0.5)) for a, b in zip(control, treatment)]
    benefit = sum(1 for a, b in pairs if a == 0 and b == 1)
    harm = sum(1 for a, b in pairs if a == 1 and b == 0)
    discordant = benefit + harm
    tail = min(benefit, harm)
    p_value = (
        min(1.0, 2.0 * sum(math.comb(discordant, k) for k in range(tail + 1)) / (2**discordant))
        if discordant
        else 1.0
    )
    n = len(pairs)
    return {
        "n": n,
        "benefit_pairs": benefit,
        "harm_pairs": harm,
        "discordant_pairs": discordant,
        "paired_risk_difference": round((benefit - harm) / n, 9) if n else None,
        "exact_two_sided_p": round(p_value, 12),
        "variance_state": "estimable" if n > 1 else "not_estimable",
        "confidence_interval": None,
        "confidence_interval_state": "not_implemented_for_paired_binary_v9.8",
    }


def holm_adjust(p_values: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted((float(value), str(name)) for name, value in p_values.items())
    adjusted: dict[str, float] = {}
    running = 0.0
    count = len(ordered)
    for index, (value, name) in enumerate(ordered):
        running = max(running, min(1.0, value * (count - index)))
        adjusted[name] = round(running, 12)
    return adjusted


def evaluate_preregistered_causal_trial(
    store: Any,
    repo: str,
    *,
    preregistration_id: str,
    trial_ids: Sequence[str],
    persist: bool = True,
) -> dict[str, Any]:
    prereg = get_causal_preregistration(store, repo, preregistration_id)
    if prereg is None:
        raise CausalTrialError("canonical preregistration is missing")
    witness = get_distillation_witness(store, repo, str(prereg["distillation_witness_id"]))
    witness_check = verify_distillation_witness(store, repo, str(prereg["distillation_witness_id"]))
    descriptive = evaluate_competence_differentiation(
        store,
        repo,
        competence_id=str(prereg["competence_id"]),
        trial_ids=trial_ids,
        policy={
            "minimum_cases": int(prereg["planned_cases"]),
            "minimum_effect": min(float(v) for v in prereg["minimum_effects"].values()),
            "maximum_baseline_mean": 0.90,
            "minimum_competence_mean": 0.20,
            "minimum_dynamic_range": 0.10,
            "confidence_z": 1.96,
            "maximum_negative_transfer_rate": float(prereg["negative_transfer_threshold"]),
            "required_evidence_class": "live_empirical",
            "require_same_epoch": True,
            "require_same_measurement_cohort": True,
        },
        cohort_nonce=f"preregistered:{preregistration_id}",
        persist=False,
    )
    exact: dict[str, Any] = {}
    p_values: dict[str, float] = {}
    for name, (control_arm, treatment_arm) in PRIMARY_COMPARISONS.items():
        panel = exact_matched_binary(
            [case["scores"][control_arm] for case in descriptive["cases"]],
            [case["scores"][treatment_arm] for case in descriptive["cases"]],
        )
        exact[name] = panel
        p_values[name] = float(panel["exact_two_sided_p"])
    adjusted = holm_adjust(p_values)
    for name, value in adjusted.items():
        exact[name]["holm_adjusted_p"] = value

    trials = [get_transfer_trial(store, repo, trial_id) for trial_id in trial_ids]
    timing_pass = all(trial is not None and float(trial.get("created_at") or 0) >= float(prereg["created_at"]) for trial in trials)
    exact_pass = all(
        float(exact[name]["paired_risk_difference"] or 0.0) >= float(prereg["minimum_effects"][name])
        and float(exact[name]["holm_adjusted_p"]) <= float(prereg["alpha"])
        for name in PRIMARY_COMPARISONS
    )
    gates = {
        "preregistered_before_trials": timing_pass,
        "planned_sample_complete": len(descriptive["cases"]) >= int(prereg["planned_cases"]),
        "semantic_distillation_supported": witness_check.get("valid") is True and witness is not None and witness.get("status") == "SUPPORTED",
        "live_empirical_evidence": descriptive["gates"]["evidence_class"]["passed"],
        "discriminative_cohort": descriptive["gates"]["ceiling"]["passed"] and descriptive["gates"]["floor"]["passed"] and descriptive["gates"]["dynamic_range"]["passed"],
        "exact_primary_effects": exact_pass,
        "negative_transfer": descriptive["gates"]["negative_transfer"]["passed"],
    }
    promotion = all(gates.values())
    identity = {
        "schema_version": RESULT_SCHEMA,
        "repository_id": prereg["repository_id"],
        "repo": repo,
        "preregistration_id": preregistration_id,
        "preregistration_receipt_hash": prereg["receipt_hash"],
        "trial_bindings": [{"trial_id": case["trial_id"], "trial_receipt_hash": case["trial_receipt_hash"]} for case in descriptive["cases"]],
    }
    result_id = _sha(identity)
    receipt: dict[str, Any] = {
        **identity,
        "result_id": result_id,
        "version": VERSION,
        "status": "CAUSAL_COMPETENCE_EFFECT_VERIFIED" if promotion else "CAUSAL_TRIAL_HELD",
        "promotion_eligible": promotion,
        "gates": gates,
        "failed_gates": sorted(name for name, passed in gates.items() if not passed),
        "exact_matched_binary": exact,
        "descriptive_receipt_hash": descriptive["receipt_hash"],
        "model_identity_used_in_scoring": False,
        "provider_identity_used_in_scoring": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "advisory_only": True,
        "created_at": time.time(),
    }
    receipt["receipt_hash"] = _sha(receipt)
    if not persist:
        return receipt
    ensure_causal_trial_tables(store)
    with store.transaction() as conn:
        existing = conn.execute("SELECT receipt_json FROM causal_trial_results WHERE result_id=?", (result_id,)).fetchone()
        if existing is not None:
            return json.loads(str(existing["receipt_json"]))
        conn.execute(
            "INSERT INTO causal_trial_results VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (result_id, receipt["receipt_hash"], receipt["repository_id"], repo, preregistration_id, receipt["status"], _canonical(receipt), receipt["created_at"]),
        )
    return receipt


__all__ = [
    "CausalTrialError",
    "PREREG_SCHEMA",
    "RESULT_SCHEMA",
    "STANDARD_ARMS",
    "VERSION",
    "create_causal_preregistration",
    "ensure_causal_trial_tables",
    "evaluate_preregistered_causal_trial",
    "exact_matched_binary",
    "get_causal_preregistration",
    "holm_adjust",
]
