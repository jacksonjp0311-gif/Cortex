"""v9.8 preregistered, model-neutral causal competence analysis."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from collections.abc import Mapping, Sequence
from functools import lru_cache
from typing import Any

from .competence_differentiation import evaluate_competence_differentiation
from .competence_transfer import get_transfer_trial
from .discriminability import assess_paired_information, verify_task_panel
from .discriminative_forge import verify_held_out_manifest
from .distillation_witness import get_distillation_witness, verify_distillation_witness
from .information_calibration import verify_difficulty_calibration

PREREG_SCHEMA = "cortex-causal-preregistration/1.0"
RESULT_SCHEMA = "cortex-preregistered-causal-result/1.0"
VERSION = "9.8.2"
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
    expected_discordance: float | None = None,
    target_power: float = 0.80,
    calibration_receipt: Mapping[str, Any] | None = None,
    difficulty_calibration_receipt: Mapping[str, Any] | None = None,
    heldout_corpus_manifest: Mapping[str, Any] | None = None,
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
    power_analysis = (
        matched_binary_power_plan(
            minimum_effect=min(minimum.values()),
            expected_discordance=float(expected_discordance),
            alpha=float(alpha) / len(PRIMARY_COMPARISONS),
            target_power=float(target_power),
        )
        if expected_discordance is not None
        else {
            "state": "undeclared",
            "reason": "expected_discordance_required_before_confirmatory_use",
        }
    )
    if difficulty_calibration_receipt is not None:
        calibration_check = verify_difficulty_calibration(difficulty_calibration_receipt)
        selected_families = set((difficulty_calibration_receipt.get("selected") or {}).keys())
        calibration_hash = difficulty_calibration_receipt.get("calibration_hash")
    else:
        calibration_check = verify_task_panel(calibration_receipt) if calibration_receipt is not None else {"valid": False, "errors": ["calibration_missing"]}
        selected_families = set(calibration_receipt.get("selected_families") or []) if calibration_receipt is not None else set()
        calibration_hash = calibration_receipt.get("calibration_hash") if calibration_receipt is not None else None
    declared_families = {str(item) for item in task_family_strata}
    calibration_binding = {
        "state": "pass" if calibration_check["valid"] and bool(declared_families) and declared_families <= selected_families else "unknown",
        "calibration_hash": calibration_hash,
        "selected_families": sorted(selected_families),
        "declared_families": sorted(declared_families),
        "reason": "declared_families_calibrated" if calibration_check["valid"] and bool(declared_families) and declared_families <= selected_families else "calibration_missing_invalid_or_unbound",
    }
    heldout_check = verify_held_out_manifest(heldout_corpus_manifest) if heldout_corpus_manifest is not None else {"valid": False, "errors": ["heldout_manifest_missing"]}
    heldout_binding = {
        "state": "pass" if (
            heldout_check["valid"]
            and heldout_corpus_manifest is not None
            and heldout_corpus_manifest.get("source_calibration_hash") == calibration_hash
            and heldout_corpus_manifest.get("corpus_hash") == str(task_corpus_hash)
            and set((heldout_corpus_manifest.get("selected_levels") or {}).keys()) == declared_families
        ) else "unknown",
        "corpus_hash": heldout_corpus_manifest.get("corpus_hash") if heldout_corpus_manifest is not None else None,
        "source_calibration_hash": heldout_corpus_manifest.get("source_calibration_hash") if heldout_corpus_manifest is not None else None,
        "answers_present": heldout_corpus_manifest.get("answers_present_in_public_manifest") if heldout_corpus_manifest is not None else None,
        "reason": "heldout_corpus_bound" if heldout_check["valid"] and heldout_corpus_manifest is not None and heldout_corpus_manifest.get("source_calibration_hash") == calibration_hash and heldout_corpus_manifest.get("corpus_hash") == str(task_corpus_hash) and set((heldout_corpus_manifest.get("selected_levels") or {}).keys()) == declared_families else "heldout_missing_invalid_or_unbound",
    }
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
        "power_analysis": power_analysis,
        "discriminability_calibration": calibration_binding,
        "heldout_corpus_seal": heldout_binding,
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
    information = assess_paired_information(control, treatment)
    benefit = int(information["benefit_pairs"])
    harm = int(information["harm_pairs"])
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
        "effective_causal_sample": information["effective_causal_sample"],
        "discordance_rate": information["discordance_rate"],
        "information_state": information["state"],
        "paired_risk_difference": round((benefit - harm) / n, 9) if n else None,
        "exact_two_sided_p": round(p_value, 12),
        "variance_state": "estimable" if n > 1 else "not_estimable",
        "confidence_interval": None,
        "confidence_interval_state": "not_implemented_for_paired_binary_v9.8",
    }


def paired_bootstrap_interval(
    control: Sequence[float],
    treatment: Sequence[float],
    *,
    confidence: float = 0.95,
    replicates: int = 5000,
    seed_material: str = "",
) -> dict[str, Any]:
    """Deterministic case-level paired bootstrap for the risk difference."""
    if len(control) != len(treatment):
        raise CausalTrialError("matched binary panels must have equal length")
    n = len(control)
    if n < 2:
        return {
            "interval": None,
            "state": "not_estimable",
            "method": "paired_case_bootstrap_percentile",
            "replicates": 0,
        }
    if not 0 < confidence < 1 or replicates < 100:
        raise CausalTrialError("bootstrap confidence/replicates are invalid")
    pairs = [(float(a), float(b)) for a, b in zip(control, treatment)]
    seed = int(_sha({"seed_material": seed_material, "pairs": pairs})[:16], 16)
    rng = random.Random(seed)
    estimates = []
    for _ in range(int(replicates)):
        sample = [pairs[rng.randrange(n)] for _ in range(n)]
        estimates.append(sum(b - a for a, b in sample) / n)
    estimates.sort()
    tail = (1.0 - confidence) / 2.0
    lower_index = max(0, min(len(estimates) - 1, int(math.floor(tail * len(estimates)))))
    upper_index = max(0, min(len(estimates) - 1, int(math.ceil((1.0 - tail) * len(estimates))) - 1))
    return {
        "interval": [round(estimates[lower_index], 9), round(estimates[upper_index], 9)],
        "state": "estimated",
        "method": "paired_case_bootstrap_percentile",
        "confidence": confidence,
        "replicates": int(replicates),
        "seed_digest": _sha({"seed_material": seed_material, "pairs": pairs}),
    }


@lru_cache(maxsize=None)
def _exact_discordance_p(benefit: int, harm: int) -> float:
    discordant = benefit + harm
    if not discordant:
        return 1.0
    tail = min(benefit, harm)
    return min(
        1.0,
        2.0 * sum(math.comb(discordant, k) for k in range(tail + 1)) / (2**discordant),
    )


def matched_binary_power_plan(
    *,
    minimum_effect: float,
    expected_discordance: float,
    alpha: float = 0.05,
    target_power: float = 0.80,
    max_cases: int = 512,
) -> dict[str, Any]:
    """Find matched-case count from an exact discordance probability model."""
    effect = float(minimum_effect)
    discordance = float(expected_discordance)
    if not 0 < effect <= discordance <= 1:
        raise CausalTrialError("power assumptions require 0 < effect <= discordance <= 1")
    if not 0 < alpha < 1 or not 0 < target_power < 1:
        raise CausalTrialError("power alpha/target must be between zero and one")
    benefit_probability = (discordance + effect) / (2.0 * discordance)
    required = None
    achieved = 0.0
    for n in range(2, int(max_cases) + 1):
        power = 0.0
        for d in range(n + 1):
            p_d = math.comb(n, d) * (discordance**d) * ((1.0 - discordance) ** (n - d))
            for benefit in range(d + 1):
                harm = d - benefit
                if _exact_discordance_p(benefit, harm) > alpha:
                    continue
                p_b = math.comb(d, benefit) * (benefit_probability**benefit) * ((1.0 - benefit_probability) ** harm)
                power += p_d * p_b
        if power >= target_power:
            required = n
            achieved = power
            break
    return {
        "state": "complete" if required is not None else "unresolved",
        "method": "exact_mcnemar_unconditional_power_sum",
        "minimum_effect": effect,
        "expected_discordance": discordance,
        "alpha": alpha,
        "target_power": target_power,
        "required_cases": required,
        "achieved_power": round(achieved, 9) if required is not None else None,
        "max_cases": int(max_cases),
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
        panel["confidence_interval"] = paired_bootstrap_interval(
            [case["scores"][control_arm] for case in descriptive["cases"]],
            [case["scores"][treatment_arm] for case in descriptive["cases"]],
            seed_material=f"{preregistration_id}:{name}",
        )
        panel["confidence_interval_state"] = panel["confidence_interval"]["state"]
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
        "power_analysis_complete": (
            isinstance(prereg.get("power_analysis"), Mapping)
            and prereg["power_analysis"].get("state") == "complete"
            and prereg["power_analysis"].get("required_cases") is not None
            and int(prereg["planned_cases"]) >= int(prereg["power_analysis"]["required_cases"])
        ),
        "development_calibration_bound": (
            isinstance(prereg.get("discriminability_calibration"), Mapping)
            and prereg["discriminability_calibration"].get("state") == "pass"
        ),
        "heldout_corpus_sealed": (
            isinstance(prereg.get("heldout_corpus_seal"), Mapping)
            and prereg["heldout_corpus_seal"].get("state") == "pass"
        ),
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
    "matched_binary_power_plan",
    "paired_bootstrap_interval",
]
