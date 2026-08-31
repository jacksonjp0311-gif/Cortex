"""Preregistered ordinary-context versus Cortex-governed agent trials.

The control arm is still observed and sealed by Cortex, but it receives only
the task, tool declarations, and constitutional safety restrictions.  The
treatment arm receives Cortex's governed context projection.  Model identity,
tool fabric, capability profile, task, evaluator, source snapshot, and budgets
are frozen before either arm runs.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .adapter_provenance import (
    EVIDENCE_LIVE,
    EVIDENCE_ORDER,
    EVIDENCE_UNKNOWN,
    resolve_adapter_provenance,
    verify_adapter_provenance,
)
from .causal_trial import (
    exact_matched_binary,
    matched_binary_power_plan,
    paired_bootstrap_interval,
)
from .coding_workspace import repository_head
from .evaluation import TaskEvaluationContract, evaluate_task_result
from .native_agent import (
    AgentModelAdapter,
    CapabilityGrant,
    NativeAgentRuntime,
    ToolRegistry,
    verify_native_agent_trajectory,
)
from .symbiosis import open_symbiotic_session

PREREG_SCHEMA = "cortex-autonomy-differential-preregistration/1.0"
CASE_SCHEMA = "cortex-autonomy-differential-case/1.0"
RESULT_SCHEMA = "cortex-autonomy-differential-result/1.0"
VERSION = "10.0.0-alpha.15"
ARMS = ("task_only_control", "cortex_governed")
_PREREG_MATERIAL_FIELDS = (
    "schema_version",
    "repo",
    "repository_id",
    "source_head",
    "arms",
    "cases",
    "planned_cases",
    "model_identity",
    "model_identity_hash",
    "adapter_implementation_digest",
    "adapter_provenance",
    "tool_catalog_hash",
    "grant_profile",
    "grant_profile_hash",
    "randomization_seed_commitment",
    "primary_metric",
    "primary_test",
    "minimum_effect",
    "maximum_regression_rate",
    "alpha",
    "power_analysis",
    "budgets",
    "efficiency_weights",
    "efficiency_normalizers",
    "model_identity_used_in_scoring",
    "provider_identity_used_in_scoring",
    "caller_success_fields_authoritative",
    "host_mutate_authorized",
    "execution_authorized",
    "memory_admission_authorized",
    "competence_promotion_authorized",
    "policy_effect",
)


class AutonomyDifferentialError(ValueError):
    """Raised when a differential loses its frozen comparison geometry."""


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


def randomization_seed_commitment(seed: str) -> str:
    """Return the canonical commitment used before arm-order revelation."""

    return _sha(str(seed))


def _closed_authority() -> dict[str, bool]:
    return {
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "competence_promotion_authorized": False,
        "policy_effect": False,
    }


def _identity(adapter: AgentModelAdapter) -> dict[str, str]:
    fields = (
        "provider_family",
        "model_id",
        "model_version",
        "adapter_id",
        "adapter_version",
    )
    identity = {field: str(getattr(adapter, field, "") or "undeclared") for field in fields}
    if not identity["provider_family"] or not identity["model_id"] or not identity["adapter_id"]:
        raise AutonomyDifferentialError("adapter identity is incomplete")
    return identity


def _grant_profile(grant: CapabilityGrant) -> dict[str, Any]:
    material = grant.material()
    keys = (
        "schema_version",
        "workspace_root",
        "allowed_tools",
        "allowed_command_vectors",
        "max_tool_output_bytes",
        "max_command_seconds",
        "max_tool_calls",
        "max_total_tool_seconds",
        "delegable",
        "host_mutate_authorized",
        "execution_authorized",
        "memory_admission_authorized",
        "policy_effect",
    )
    return {key: material.get(key) for key in keys}


def _tool_catalog(tools: ToolRegistry) -> list[dict[str, Any]]:
    return sorted(
        (dict(item) for item in tools.manifests()),
        key=lambda item: (str(item.get("tool_id") or ""), str(item.get("version") or "")),
    )


def _session(store: Any, repo: str, task: str) -> dict[str, Any]:
    return open_symbiotic_session(
        store,
        repo,
        task=task,
        provider="autonomy-differential",
        model_id="none",
        capability_profile={"paired_agent_measurement": True},
        tool_scopes=(),
        persist=True,
    )


def _canonical_receipt(
    store: Any, repo: str, receipt_hash: str, kind: str
) -> dict[str, Any]:
    receipt = store.symbiotic_receipt(str(receipt_hash), repo=repo)
    if not receipt or receipt.get("kind") != kind:
        raise AutonomyDifferentialError(f"canonical {kind} receipt required")
    if store.verify_symbiotic_receipt(repo, str(receipt_hash)).get("valid") is not True:
        raise AutonomyDifferentialError(f"canonical {kind} receipt invalid")
    return receipt


def _by_id(store: Any, repo: str, kind: str, field: str, value: str) -> dict[str, Any] | None:
    return next(
        (
            receipt
            for receipt in store.symbiotic_receipts_by_kind(repo, kind)
            if str(receipt.get(field) or "") == str(value)
        ),
        None,
    )


def create_autonomy_differential_preregistration(
    store: Any,
    repo: str,
    root: str | Path,
    *,
    adapter: AgentModelAdapter,
    tools: ToolRegistry,
    grant: CapabilityGrant,
    cases: Sequence[Mapping[str, Any]],
    randomization_seed_commitment: str,
    minimum_effect: float = 0.10,
    maximum_regression_rate: float = 0.10,
    alpha: float = 0.05,
    expected_discordance: float = 0.50,
    target_power: float = 0.80,
    maximum_total_tokens: int = 100_000,
    maximum_latency_ms: float = 600_000.0,
    maximum_cost: float = 100.0,
    efficiency_weights: Mapping[str, float] | None = None,
    efficiency_normalizers: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Freeze one complete paired panel before the first model invocation."""

    workspace = Path(root).resolve()
    if len(cases) < 2:
        raise AutonomyDifferentialError("at least two frozen matched cases are required")
    if not randomization_seed_commitment or len(str(randomization_seed_commitment)) != 64:
        raise AutonomyDifferentialError("randomization seed commitment must be SHA-256")
    if not 0 < float(alpha) < 1:
        raise AutonomyDifferentialError("alpha must be between zero and one")
    if not -1 <= float(minimum_effect) <= 1:
        raise AutonomyDifferentialError("minimum effect must be in [-1, 1]")
    if not 0 <= float(maximum_regression_rate) <= 1:
        raise AutonomyDifferentialError("maximum regression rate must be in [0, 1]")
    power_analysis = matched_binary_power_plan(
        minimum_effect=float(minimum_effect),
        expected_discordance=float(expected_discordance),
        alpha=float(alpha),
        target_power=float(target_power),
        # The preregistration only needs to establish whether its declared
        # panel is sufficient. Searching beyond that frozen panel would add
        # cost without changing the gate.
        max_cases=len(cases),
    )
    frozen_cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in cases:
        case_id = str(raw.get("case_id") or "").strip()
        task = str(raw.get("task") or "").strip()
        if not case_id or case_id in seen or not task:
            raise AutonomyDifferentialError("case IDs must be unique and tasks nonempty")
        seen.add(case_id)
        contract = TaskEvaluationContract.from_mapping(
            raw.get("evaluation_contract")
            if isinstance(raw.get("evaluation_contract"), Mapping)
            else {}
        )
        frozen_cases.append(
            {
                "case_id": case_id,
                "task": task,
                "task_hash": _sha(task),
                "task_family": str(raw.get("task_family") or "unspecified"),
                "evaluation_contract": contract.to_dict(),
                "evaluation_contract_hash": contract.contract_hash,
            }
        )
    identity = _identity(adapter)
    provenance = resolve_adapter_provenance(store, repo, adapter)
    provenance_check = verify_adapter_provenance(store, repo, provenance)
    if provenance_check.get("valid") is not True:
        raise AutonomyDifferentialError("adapter provenance is invalid")
    weights = {"tokens": 1.0, "time": 1.0, "cost": 1.0}
    weights.update({key: float(value) for key, value in (efficiency_weights or {}).items()})
    normalizers = {"tokens": 1_000.0, "time": 1_000.0, "cost": 1.0}
    normalizers.update(
        {key: float(value) for key, value in (efficiency_normalizers or {}).items()}
    )
    if set(weights) != {"tokens", "time", "cost"} or any(value < 0 for value in weights.values()):
        raise AutonomyDifferentialError("efficiency weights must be nonnegative token/time/cost values")
    if set(normalizers) != {"tokens", "time", "cost"} or any(value <= 0 for value in normalizers.values()):
        raise AutonomyDifferentialError("efficiency normalizers must be positive token/time/cost values")
    material = {
        "schema_version": PREREG_SCHEMA,
        "repo": str(repo),
        "repository_id": str(store.repo(repo)["repository_id"]),
        "source_head": repository_head(workspace),
        "arms": list(ARMS),
        "cases": frozen_cases,
        "planned_cases": len(frozen_cases),
        "model_identity": identity,
        "model_identity_hash": _sha(identity),
        "adapter_implementation_digest": str(provenance.get("implementation_digest") or ""),
        "adapter_provenance": provenance,
        "tool_catalog_hash": _sha(_tool_catalog(tools)),
        "grant_profile": _grant_profile(grant),
        "grant_profile_hash": _sha(_grant_profile(grant)),
        "randomization_seed_commitment": str(randomization_seed_commitment),
        "primary_metric": "independently_evaluated_task_success",
        "primary_test": "exact_conditional_binomial_on_discordant_pairs",
        "minimum_effect": float(minimum_effect),
        "maximum_regression_rate": float(maximum_regression_rate),
        "alpha": float(alpha),
        "power_analysis": power_analysis,
        "budgets": {
            "maximum_total_tokens_per_arm": int(maximum_total_tokens),
            "maximum_latency_ms_per_arm": float(maximum_latency_ms),
            "maximum_cost_per_arm": float(maximum_cost),
        },
        "efficiency_weights": weights,
        "efficiency_normalizers": normalizers,
        "model_identity_used_in_scoring": False,
        "provider_identity_used_in_scoring": False,
        "caller_success_fields_authoritative": False,
        **_closed_authority(),
    }
    preregistration_id = _sha(material)
    existing = _by_id(
        store,
        repo,
        "autonomy_differential_preregistration",
        "preregistration_id",
        preregistration_id,
    )
    if existing:
        return {**existing, "duplicate": True, "inserted": False}
    session = _session(store, repo, "freeze autonomy differential")
    return store.append_symbiotic_receipt(
        repo,
        {
            **material,
            "kind": "autonomy_differential_preregistration",
            "status": "frozen_before_execution",
            "version": VERSION,
            "preregistration_id": preregistration_id,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"autonomy_prereg_{preregistration_id[:24]}",
            "body_epoch_id": session["body_epoch_id"],
            "advisory_only": True,
        },
    )


def verify_autonomy_differential_preregistration(
    store: Any, repo: str, preregistration_id: str
) -> dict[str, Any]:
    try:
        receipt = _canonical_receipt(
            store,
            repo,
            str((_by_id(store, repo, "autonomy_differential_preregistration", "preregistration_id", preregistration_id) or {}).get("receipt_hash") or ""),
            "autonomy_differential_preregistration",
        )
    except AutonomyDifferentialError as exc:
        return {"valid": False, "errors": [str(exc)]}
    errors: list[str] = []
    if receipt.get("schema_version") != PREREG_SCHEMA:
        errors.append("preregistration_schema_invalid")
    reconstructed_material = {
        field: receipt.get(field) for field in _PREREG_MATERIAL_FIELDS
    }
    if receipt.get("preregistration_id") != _sha(reconstructed_material):
        errors.append("preregistration_identity_invalid")
    if receipt.get("arms") != list(ARMS):
        errors.append("preregistration_arms_invalid")
    if int(receipt.get("planned_cases") or 0) != len(receipt.get("cases") or ()):
        errors.append("preregistration_case_count_invalid")
    provenance = receipt.get("adapter_provenance")
    provenance_check = verify_adapter_provenance(
        store, repo, provenance if isinstance(provenance, Mapping) else None
    )
    if provenance_check.get("valid") is not True:
        errors.append("preregistration_adapter_provenance_invalid")
    if receipt.get("model_identity_hash") != _sha(receipt.get("model_identity")):
        errors.append("preregistration_model_identity_invalid")
    if receipt.get("grant_profile_hash") != _sha(receipt.get("grant_profile")):
        errors.append("preregistration_grant_profile_invalid")
    for field in _closed_authority():
        if receipt.get(field) is not False:
            errors.append(f"preregistration_authority_open:{field}")
    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "receipt": receipt,
        "evidence_class": provenance_check.get("evidence_class", EVIDENCE_UNKNOWN),
        **_closed_authority(),
    }


def _usage_metrics(trajectory: Mapping[str, Any]) -> dict[str, Any]:
    input_tokens = output_tokens = total_tokens = 0.0
    tokens_available = False
    cost = 0.0
    cost_available = False
    for response in trajectory.get("responses") or ():
        usage = response.get("token_usage") if isinstance(response, Mapping) else {}
        if isinstance(usage, Mapping):
            raw_total = usage.get("total_tokens")
            raw_input = usage.get("input_tokens", usage.get("prompt_tokens"))
            raw_output = usage.get("output_tokens", usage.get("completion_tokens"))
            if isinstance(raw_input, (int, float)):
                input_tokens += float(raw_input)
                tokens_available = True
            if isinstance(raw_output, (int, float)):
                output_tokens += float(raw_output)
                tokens_available = True
            if isinstance(raw_total, (int, float)):
                total_tokens += float(raw_total)
                tokens_available = True
            elif isinstance(raw_input, (int, float)) or isinstance(raw_output, (int, float)):
                total_tokens += float(raw_input or 0) + float(raw_output or 0)
        raw_cost = response.get("cost") if isinstance(response, Mapping) else {}
        if isinstance(raw_cost, Mapping):
            value = raw_cost.get("total", raw_cost.get("total_cost"))
            if isinstance(value, (int, float)):
                cost += float(value)
                cost_available = True
    telemetry = trajectory.get("telemetry") if isinstance(trajectory.get("telemetry"), Mapping) else {}
    return {
        "input_tokens": input_tokens if tokens_available else None,
        "output_tokens": output_tokens if tokens_available else None,
        "total_tokens": total_tokens if tokens_available else None,
        "token_measurement": "provider_reported" if tokens_available else "unavailable",
        "latency_ms": float(telemetry.get("total_latency_ms") or 0.0),
        "latency_measurement": "measured",
        "cost": cost if cost_available else None,
        "cost_measurement": "provider_reported" if cost_available else "unavailable",
        "tool_calls": len(trajectory.get("tool_results") or ()),
        "tool_failures": sum(
            str(item.get("status") or "") not in {"completed", "success"}
            for item in trajectory.get("tool_results") or ()
            if isinstance(item, Mapping)
        ),
        "model_iterations": len(trajectory.get("responses") or ()),
    }


def run_autonomy_differential_case(
    store: Any,
    repo: str,
    root: str | Path,
    *,
    preregistration_id: str,
    case_id: str,
    randomization_seed: str,
    control_adapter: AgentModelAdapter,
    cortex_adapter: AgentModelAdapter,
    tools: ToolRegistry,
    grant: CapabilityGrant,
) -> dict[str, Any]:
    """Execute one randomized pair and derive success independently."""

    prereg_check = verify_autonomy_differential_preregistration(
        store, repo, preregistration_id
    )
    if prereg_check.get("valid") is not True:
        raise AutonomyDifferentialError("canonical preregistration is invalid")
    prereg = prereg_check["receipt"]
    if randomization_seed_commitment(randomization_seed) != prereg.get(
        "randomization_seed_commitment"
    ):
        raise AutonomyDifferentialError("randomization seed does not match commitment")
    if repository_head(root) != prereg.get("source_head"):
        raise AutonomyDifferentialError("source snapshot changed after preregistration")
    case = next(
        (item for item in prereg.get("cases") or () if item.get("case_id") == case_id),
        None,
    )
    if not isinstance(case, Mapping):
        raise AutonomyDifferentialError("case is not in the frozen panel")
    existing = _by_id(
        store,
        repo,
        "autonomy_differential_case",
        "case_binding_id",
        _sha([preregistration_id, case_id]),
    )
    if existing:
        return {**existing, "duplicate": True, "inserted": False}
    expected_identity = dict(prereg.get("model_identity") or {})
    provenances = {}
    for arm, adapter in (
        ("task_only_control", control_adapter),
        ("cortex_governed", cortex_adapter),
    ):
        if _identity(adapter) != expected_identity:
            raise AutonomyDifferentialError(f"{arm} model identity mismatch")
        provenance = resolve_adapter_provenance(store, repo, adapter)
        check = verify_adapter_provenance(store, repo, provenance)
        if check.get("valid") is not True:
            raise AutonomyDifferentialError(f"{arm} adapter provenance invalid")
        if str(provenance.get("implementation_digest") or "") != str(
            prereg.get("adapter_implementation_digest") or ""
        ):
            raise AutonomyDifferentialError(f"{arm} adapter implementation mismatch")
        provenances[arm] = provenance
    if _sha(_tool_catalog(tools)) != prereg.get("tool_catalog_hash"):
        raise AutonomyDifferentialError("tool catalog changed after preregistration")
    if _sha(_grant_profile(grant)) != prereg.get("grant_profile_hash"):
        raise AutonomyDifferentialError("capability profile changed after preregistration")
    order = list(ARMS)
    if int(_sha([randomization_seed, case_id])[:2], 16) % 2:
        order.reverse()
    adapters = {
        "task_only_control": control_adapter,
        "cortex_governed": cortex_adapter,
    }
    runtime = NativeAgentRuntime(store, repo, tools=tools)
    arms: dict[str, Any] = {}
    contract = TaskEvaluationContract.from_mapping(case["evaluation_contract"])
    for arm in order:
        run = runtime.run(
            str(case["task"]),
            adapter=adapters[arm],
            grant=grant,
            context_treatment=arm,
        )
        trajectory = _canonical_receipt(
            store,
            repo,
            str(run["trajectory_receipt_hash"]),
            "native_agent_trajectory",
        )
        trajectory_check = verify_native_agent_trajectory(
            store, repo, str(trajectory["receipt_hash"])
        )
        if trajectory_check.get("valid") is not True:
            raise AutonomyDifferentialError(f"{arm} trajectory invalid")
        evaluation = evaluate_task_result(
            contract, {"text": str(trajectory.get("final_answer") or "")}
        )
        arms[arm] = {
            "trajectory_receipt_hash": trajectory["receipt_hash"],
            "context_treatment": str(trajectory.get("context_treatment") or ""),
            "evaluation": evaluation,
            "task_success": evaluation.get("success"),
            "metrics": _usage_metrics(trajectory),
            "adapter_provenance": provenances[arm],
        }
    case_binding_id = _sha([preregistration_id, case_id])
    evidence_class = min(
        (str(item.get("evidence_class") or EVIDENCE_UNKNOWN) for item in provenances.values()),
        key=lambda value: EVIDENCE_ORDER.get(value, -1),
    )
    budgets = prereg["budgets"]
    budget_states: dict[str, bool | None] = {}
    for arm in ARMS:
        metrics = arms[arm]["metrics"]
        budget_states[f"{arm}:tokens"] = (
            None
            if metrics["total_tokens"] is None
            else metrics["total_tokens"] <= budgets["maximum_total_tokens_per_arm"]
        )
        budget_states[f"{arm}:latency"] = (
            metrics["latency_ms"] <= budgets["maximum_latency_ms_per_arm"]
        )
        budget_states[f"{arm}:cost"] = (
            None
            if metrics["cost"] is None
            else metrics["cost"] <= budgets["maximum_cost_per_arm"]
        )
    session = _session(store, repo, f"seal autonomy differential case {case_id}")
    return store.append_symbiotic_receipt(
        repo,
        {
            "schema_version": CASE_SCHEMA,
            "kind": "autonomy_differential_case",
            "status": "paired_observation_sealed",
            "version": VERSION,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"autonomy_case_{case_binding_id[:24]}",
            "body_epoch_id": session["body_epoch_id"],
            "preregistration_id": preregistration_id,
            "preregistration_receipt_hash": prereg["receipt_hash"],
            "case_binding_id": case_binding_id,
            "case_id": case_id,
            "task_hash": case["task_hash"],
            "evaluation_contract_hash": case["evaluation_contract_hash"],
            "source_head": prereg["source_head"],
            "execution_order": order,
            "arms": arms,
            "evidence_class": evidence_class,
            "budget_states": budget_states,
            "all_required_budgets_observed": all(
                value is not None for value in budget_states.values()
            ),
            "caller_success_fields_authoritative": False,
            "advisory_only": True,
            **_closed_authority(),
        },
    )


def _mean(values: Sequence[float | None]) -> float | None:
    observed = [float(value) for value in values if value is not None]
    return round(statistics.mean(observed), 9) if len(observed) == len(values) and observed else None


def evaluate_autonomy_differential(
    store: Any,
    repo: str,
    *,
    preregistration_id: str,
    persist: bool = True,
) -> dict[str, Any]:
    """Reconstruct the frozen panel and estimate the Cortex treatment effect."""

    prereg_check = verify_autonomy_differential_preregistration(
        store, repo, preregistration_id
    )
    if prereg_check.get("valid") is not True:
        raise AutonomyDifferentialError("canonical preregistration is invalid")
    prereg = prereg_check["receipt"]
    rows = sorted(
        (
            item
            for item in store.symbiotic_receipts_by_kind(
                repo, "autonomy_differential_case"
            )
            if item.get("preregistration_id") == preregistration_id
        ),
        key=lambda item: str(item.get("case_id") or ""),
    )
    errors: list[str] = []
    case_ids: set[str] = set()
    control: list[float] = []
    treatment: list[float] = []
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if case_id in case_ids:
            errors.append(f"duplicate_case:{case_id}")
        case_ids.add(case_id)
        if store.verify_symbiotic_receipt(repo, str(row["receipt_hash"])).get("valid") is not True:
            errors.append(f"case_receipt_invalid:{case_id}")
            continue
        frozen = next(
            (item for item in prereg["cases"] if item["case_id"] == case_id), None
        )
        if not frozen or row.get("task_hash") != frozen.get("task_hash"):
            errors.append(f"case_task_binding_invalid:{case_id}")
            continue
        contract = TaskEvaluationContract.from_mapping(frozen["evaluation_contract"])
        reconstructed_success: dict[str, bool] = {}
        for arm in ARMS:
            arm_row = (row.get("arms") or {}).get(arm) or {}
            trajectory_hash = str(arm_row.get("trajectory_receipt_hash") or "")
            check = verify_native_agent_trajectory(store, repo, trajectory_hash)
            trajectory = store.symbiotic_receipt(trajectory_hash, repo=repo) or {}
            if check.get("valid") is not True:
                errors.append(f"trajectory_invalid:{case_id}:{arm}")
                continue
            if trajectory.get("context_treatment") != arm:
                errors.append(f"context_treatment_invalid:{case_id}:{arm}")
            expected = evaluate_task_result(
                contract, {"text": str(trajectory.get("final_answer") or "")}
            )
            if expected != arm_row.get("evaluation"):
                errors.append(f"evaluation_reconstruction_invalid:{case_id}:{arm}")
            expected_success = expected.get("success") is True
            reconstructed_success[arm] = expected_success
            if arm_row.get("task_success") is not expected.get("success"):
                errors.append(f"task_success_assertion_mismatch:{case_id}:{arm}")
        control.append(1.0 if reconstructed_success.get("task_only_control") else 0.0)
        treatment.append(1.0 if reconstructed_success.get("cortex_governed") else 0.0)
    exact = exact_matched_binary(control, treatment)
    exact["confidence_interval"] = paired_bootstrap_interval(
        control,
        treatment,
        seed_material=preregistration_id,
    )
    regression_rate = (
        exact["harm_pairs"] / exact["n"] if exact["n"] else None
    )
    resources: dict[str, Any] = {}
    for metric in ("total_tokens", "latency_ms", "cost", "tool_calls", "tool_failures"):
        baseline_mean = _mean(
            [((row.get("arms") or {}).get("task_only_control") or {}).get("metrics", {}).get(metric) for row in rows]
        )
        cortex_mean = _mean(
            [((row.get("arms") or {}).get("cortex_governed") or {}).get("metrics", {}).get(metric) for row in rows]
        )
        resources[metric] = {
            "control_mean": baseline_mean,
            "cortex_mean": cortex_mean,
            "delta": (
                round(cortex_mean - baseline_mean, 9)
                if baseline_mean is not None and cortex_mean is not None
                else None
            ),
        }
    weights = prereg["efficiency_weights"]
    normalizers = prereg["efficiency_normalizers"]
    efficiency_inputs = {
        "tokens": resources["total_tokens"]["cortex_mean"],
        "time": resources["latency_ms"]["cortex_mean"],
        "cost": resources["cost"]["cortex_mean"],
    }
    denominator = None
    if all(value is not None for value in efficiency_inputs.values()):
        denominator = sum(
            float(weights[key]) * float(efficiency_inputs[key]) / float(normalizers[key])
            for key in ("tokens", "time", "cost")
        )
    effect = exact.get("paired_risk_difference")
    efficiency = (
        round(float(effect) / denominator, 12)
        if effect is not None and float(effect) > 0 and denominator and denominator > 0
        else None
    )
    evidence_classes = {str(row.get("evidence_class") or EVIDENCE_UNKNOWN) for row in rows}
    empirical = evidence_classes == {EVIDENCE_LIVE}
    gates = {
        "canonical_reconstruction": not errors,
        "planned_sample_complete": len(rows) == int(prereg["planned_cases"]),
        "preregistered_power_sufficient": (
            prereg.get("power_analysis", {}).get("state") == "complete"
            and int(prereg.get("planned_cases") or 0)
            >= int(prereg.get("power_analysis", {}).get("required_cases") or 10**9)
        ),
        "all_frozen_cases_present": case_ids == {item["case_id"] for item in prereg["cases"]},
        "live_empirical_evidence": empirical,
        "discordant_information_present": int(exact.get("discordant_pairs") or 0) > 0,
        "minimum_effect": effect is not None and float(effect) >= float(prereg["minimum_effect"]),
        "exact_significance": float(exact.get("exact_two_sided_p") or 1.0) <= float(prereg["alpha"]),
        "regression_bounded": regression_rate is not None and regression_rate <= float(prereg["maximum_regression_rate"]),
        "budgets_observed_and_passed": bool(rows)
        and all(
            row.get("all_required_budgets_observed") is True
            and all(value is True for value in (row.get("budget_states") or {}).values())
            for row in rows
        ),
    }
    advantage = all(gates.values())
    status = (
        "EMPIRICAL_AUTONOMY_ADVANTAGE_VERIFIED"
        if advantage
        else "STRUCTURAL_DIFFERENTIAL_MEASURED"
        if rows and not empirical and not errors
        else "AUTONOMY_DIFFERENTIAL_HELD"
    )
    identity = {
        "schema_version": RESULT_SCHEMA,
        "preregistration_id": preregistration_id,
        "preregistration_receipt_hash": prereg["receipt_hash"],
        "case_receipt_hashes": [row["receipt_hash"] for row in rows],
    }
    result_id = _sha(identity)
    existing = _by_id(
        store,
        repo,
        "autonomy_differential_result",
        "result_id",
        result_id,
    )
    if existing:
        return {**existing, "duplicate": True, "inserted": False}
    body = {
        **identity,
        "kind": "autonomy_differential_result",
        "status": status,
        "version": VERSION,
        "result_id": result_id,
        "exact_matched_binary": exact,
        "regression_rate": regression_rate,
        "resource_metrics": resources,
        "efficiency": {
            "value": efficiency,
            "numerator": effect,
            "denominator": denominator,
            "weights": weights,
            "normalizers": normalizers,
            "state": "estimated" if efficiency is not None else "not_estimable",
        },
        "gates": gates,
        "failed_gates": sorted(name for name, passed in gates.items() if not passed),
        "verification_errors": sorted(set(errors)),
        "empirical_advantage_established": advantage,
        "model_identity_used_in_scoring": False,
        "provider_identity_used_in_scoring": False,
        "advisory_only": True,
        "claim_boundary": (
            "A paired panel estimates one frozen Cortex context treatment. "
            "Structural fixtures are not empirical advantage; positive empirical "
            "status requires live registered evidence, discordance, exact significance, "
            "bounded regression, complete budgets, and canonical reconstruction."
        ),
        **_closed_authority(),
    }
    if not persist:
        return body
    session = _session(store, repo, "seal autonomy differential result")
    return store.append_symbiotic_receipt(
        repo,
        {
            **body,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"autonomy_result_{result_id[:24]}",
            "body_epoch_id": session["body_epoch_id"],
        },
    )


__all__ = [
    "ARMS",
    "AutonomyDifferentialError",
    "CASE_SCHEMA",
    "PREREG_SCHEMA",
    "RESULT_SCHEMA",
    "VERSION",
    "create_autonomy_differential_preregistration",
    "evaluate_autonomy_differential",
    "run_autonomy_differential_case",
    "randomization_seed_commitment",
    "verify_autonomy_differential_preregistration",
]
