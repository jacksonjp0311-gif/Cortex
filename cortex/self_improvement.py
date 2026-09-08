"""GSI-II.3 empirical readiness; no production activation and no provider calls.

Composes signed autonomy policy, Store receipts, TransductionPolicy, bounded
capture, independent attestation, and existing canary/apply/rollback primitives.
Source-improvement v1 and tournament promotion remain reconstructable.
"""
from __future__ import annotations

import ast
import json
import math
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from .assurance import typed_assurance_debt
from .autonomous_improvement import (
    PERMANENTLY_PROTECTED_PREFIXES, _policy_scope_errors, _session,
    execute_policy_promotion_membrane, verify_autonomy_policy,
)
from .coding_workspace import (
    _file_hash, _git, _sha, _verify_contract, repository_head,
    rollback_applied_patch, run_host_verification_step, verification_environment,
)
from .causal_treatment import (
    HISTORY_POOL_SCHEMA, SEARCH_EPISODE_SCHEMA_V11, TREATMENT_SCHEMA_V11,
    candidate_context, contamination_report,
    execution_contract as make_execution_contract, execution_lock as make_execution_lock,
    execution_readiness, sealed as causal_sealed, validate_randomization_plan,
    verify_execution_lock,
    semantic_holdout_identity, sham_match, valid as valid_causal,
)
from .invariants import evaluate_gsi_constitution
from .transduction_policy import (
    INTENT_SCHEMA_V2, attest_transduction_receipt, execute_bound_transduction,
    freeze_transduction_policy, inspect_observation_conformance,
    receipt_satisfies_policy, worktree_payload_hashes,
)

OPPORTUNITY_SCHEMA = "cortex-improvement-opportunity/1.0"
EXPERIMENT_SCHEMA = "cortex-self-improvement-experiment/1.0"
CONTRACT_SCHEMA_V2 = "cortex-source-improvement-preregistration/2.0"
RESULT_SCHEMA_V2 = "cortex-source-improvement-result/2.0"
CONSTRAINT_SCHEMA = "cortex-improvement-constraint/1.0"
VERIFIED_SCHEMA = "cortex-verified-improvement/1.0"
GENERATION_SCHEMA = "cortex-improvement-generation/1.0"
COMPARISON_SCHEMA = "cortex-improvement-comparison/1.1"
PROMOTION_SCHEMA = "cortex-gsi-promotion/1.0"
UTILITY_SCHEMA = "cortex-improvement-utility-contract/1.0"
UTILITY_FAMILY_SCHEMA = "cortex-improvement-utility-family/1.0"
PARTITION_SCHEMA = "cortex-evaluation-partition/1.0"
AUTHORITY_STATE_SCHEMA = "cortex-gsi-authority-state/1.0"
CAPABILITY_SCHEMA = "cortex-gsi-capability-manifest/1.0"
TREATMENT_SCHEMA = "cortex-gsi-treatment/1.0"
SEARCH_EPISODE_SCHEMA = "cortex-gsi-search-episode/1.0"
HOLDOUT_RESERVATION_SCHEMA = "cortex-gsi-holdout-reservation/1.0"
EXPERIMENT_EVIDENCE_SCHEMA = "cortex-experiment-evidence/1.0"
REALIZED_GENERATION_SCHEMA = "cortex-realized-improvement-generation/1.0"
REMEASUREMENT_SCHEMA = "cortex-gsi-post-promotion-measurement/1.0"
CUMULATIVE_SCHEMA = "cortex-cumulative-improvement-disposition/1.2"
METRICS = {"task_success": "increase", "duration_ms": "decrease", "output_bytes": "decrease"}
HARD_GATES = (
    "source", "transduction", "attestation", "workload_correctness",
    "constitutional_invariants", "regression", "environment",
    "evaluator_integrity", "policy_scope",
)
CONSTITUTIONAL_CHECKS = (
    "INV-IMPROVEMENT-EVIDENCE-REQUIRED", "INV-EVALUATOR-INDEPENDENCE",
    "INV-EXPERIMENT-PRECEDENCE", "INV-NONCOMPENSATORY-IMPROVEMENT",
    "INV-HOLDOUT-NONLEAKAGE", "INV-FAILURE-SCOPE",
    "INV-GENERATION-NONSELFAUTHORIZATION", "INV-CUMULATIVE-CLAIM-BOUNDARY",
    "authority_invariance", "protected_surface_integrity",
)
CONTROL_PLANE_PREFIXES = PERMANENTLY_PROTECTED_PREFIXES + (
    "cortex/self_improvement.py", "cortex/transduction_policy.py",
    "cortex/observation_capture.py", "cortex/assurance.py",
    "cortex/invariants.py", "cortex/epistemic_snapshot.py", "cortex/edit_intent.py",
)
_GEN = re.compile(r"^G(\d+)$")

_NON_CANDIDATE_FAILURES = {
    "ENVIRONMENT_MISMATCH": "ENVIRONMENT_CAUSAL",
    "ENVIRONMENT_FAILURE": "ENVIRONMENT_CAUSAL",
    "EVALUATOR_EXECUTION_FAILURE": "INSTRUMENT_CAUSAL",
    "INSTRUMENT_UNRESOLVED": "INSTRUMENT_CAUSAL",
    "RAW_OBSERVATION_BINDING_FAILURE": "INSTRUMENT_CAUSAL",
    "CAPTURE_INCOMPLETE": "INSTRUMENT_CAUSAL",
    "OUTPUT_LIMIT_EXCEEDED": "INSTRUMENT_CAUSAL",
    "PROCESS_TIMEOUT": "INSTRUMENT_CAUSAL",
    "POLICY_BINDING_FAILURE": "POLICY_CAUSAL",
    "SUBJECT_SOURCE_BINDING_FAILURE": "POLICY_CAUSAL",
    "COMPILER_BINDING_FAILURE": "INSTRUMENT_CAUSAL",
    "TRANSPORT_FAILURE": "INSTRUMENT_CAUSAL",
    "PATCH_APPLICATION_FAILURE": "INSTRUMENT_CAUSAL",
}


def _closed() -> dict[str, bool]:
    return dict.fromkeys(("authority_effect", "production_effect", "execution_authorized",
                          "host_mutate_authorized", "memory_admission_authorized",
                          "policy_effect", "promotion_authorized", "active_guidance"), False)


def _sealed(schema: str, **body: Any) -> dict[str, Any]:
    material = {"schema_version": schema, **body, **_closed()}
    return {**material, "object_hash": _sha(material)}


def _valid(obj: Mapping[str, Any]) -> bool:
    return (obj.get("object_hash") == _sha({k: v for k, v in obj.items() if k != "object_hash"})
            and all(obj.get(k) is False for k in _closed()))


def _gen_index(name: str) -> int | None:
    match = _GEN.fullmatch(str(name or ""))
    return int(match.group(1)) if match else None


def attestation_gate_state(status: str | None) -> str:
    """ATTESTED->PASS, PARTIALLY_ATTESTED->HELD, INVALID->FAIL. UNKNOWN never PASS."""
    if status == "ATTESTED":
        return "PASS"
    if status == "PARTIALLY_ATTESTED":
        return "HELD"
    if status == "INVALID":
        return "FAIL"
    return "UNKNOWN"


def combine_attestation_gates(states: Sequence[str]) -> str:
    if any(state == "FAIL" for state in states):
        return "FAIL"
    if not states or any(state != "PASS" for state in states):
        return "HELD" if any(state == "HELD" for state in states) else "UNKNOWN"
    return "PASS"


def signed_delta(before: Mapping[str, Any], after: Mapping[str, Any], metric: str) -> float | None:
    if before.get(metric) is None or after.get(metric) is None:
        return None
    delta = float(after[metric]) - float(before[metric])
    if METRICS[metric] == "decrease":
        delta = -delta
    if not math.isfinite(delta):
        raise ValueError("nonfinite metric")
    return delta


def _sound_steps(steps: Sequence[Mapping[str, Any]], contract: Mapping[str, Any]) -> bool:
    if not steps or len(steps) != len(contract["steps"]):
        return False
    for step, declared in zip(steps, contract["steps"]):
        raw = step.get("raw_observation") or {}
        env = step.get("environment") or {}
        if (not inspect_observation_conformance(step, contract_step=declared)["valid"]
                or raw.get("capture_complete") is not True or raw.get("timed_out") is not False
                or raw.get("output_limit_exceeded") is True
                or step.get("raw_observation_hash") != _sha(raw)
                or env.get("environment_hash") != _sha({k: v for k, v in env.items() if k != "environment_hash"})
                or raw.get("environment_hash") != env.get("environment_hash")
                or step.get("passed") is not (raw.get("returncode") == 0)):
            return False
    return True


def inspect_v2_arm(root: Path, arm: Mapping[str, Any], policy: Mapping[str, Any],
                   contract: Mapping[str, Any]) -> dict[str, Any]:
    receipt = arm.get("receipt") or {}
    verification = arm.get("verification") or {}
    steps = verification.get("steps") or []
    attestation = attest_transduction_receipt(receipt, policy, root, contract, arm.get("compilation"))
    gate = attestation_gate_state(attestation.get("status"))
    errors = []
    if gate != "PASS":
        errors.append("ATTESTATION_" + gate)
    if not receipt_satisfies_policy(receipt, policy)["valid"]:
        errors.append("POLICY_CONFORMANCE_FAILED")
    if not _sound_steps(steps, contract):
        errors.append("RAW_OBSERVATION_BINDING_FAILURE")
    if receipt.get("raw_observations") != [s.get("raw_observation") for s in steps]:
        errors.append("OBSERVATION_RECEIPT_MISMATCH")
    if receipt.get("observation_identities") != [s.get("raw_observation_hash") for s in steps]:
        errors.append("OBSERVATION_IDENTITY_MISMATCH")
    if receipt.get("applied_before_evaluator_hashes") != receipt.get("post_evaluator_hashes"):
        errors.append("POST_EVAL_ARTIFACT_MUTATION")
    if verification.get("observation_surface_violation"):
        errors.append("OBSERVATION_SURFACE_VIOLATION")
    return {"valid": not errors and gate == "PASS", "errors": errors, "attestation": attestation, "gate": gate}


def _safe_targets(targets: Sequence[str]) -> list[str]:
    result = sorted(set(targets))
    if not result:
        raise ValueError("empty candidate scope")
    for target in result:
        path = PurePosixPath(target)
        if (path.is_absolute() or ".." in path.parts or "\\" in target or ":" in target
                or path.as_posix() != target):
            raise ValueError("noncanonical target")
        lowered = target.lower()
        if lowered.startswith(tuple(x.lower() for x in CONTROL_PLANE_PREFIXES)):
            raise ValueError("permanently protected target")
    return result


def bounded_dependency_identity(
    root: str | Path,
    targets: Sequence[str],
    *,
    declared_dependencies: Sequence[str] = (),
) -> dict[str, Any]:
    """Hash a bounded, declared/local-import dependency closure.

    This is intentionally not whole-program analysis.  It follows direct local
    Python imports and explicit experiment dependencies, preserving unresolved
    imports rather than treating them as verified.
    """
    workspace = Path(root).resolve()
    queue = list(_safe_targets(targets)) + list(_safe_targets(declared_dependencies) if declared_dependencies else [])
    files: dict[str, str] = {}
    unresolved: set[str] = set()
    while queue:
        relative = queue.pop(0)
        if relative in files:
            continue
        path = workspace / relative
        if not path.is_file():
            unresolved.add(relative)
            continue
        files[relative] = _file_hash(path)
        if path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeError):
            unresolved.add(relative + ":imports")
            continue
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        for module in sorted(modules):
            base = module.replace(".", "/")
            for candidate in (base + ".py", base + "/__init__.py"):
                if (workspace / candidate).is_file() and candidate not in files:
                    queue.append(candidate)
                    break
    body = {
        "schema_version": "cortex-bounded-dependency-identity/1.0",
        "files": {key: files[key] for key in sorted(files)},
        "declared_dependencies": sorted(set(declared_dependencies)),
        "unresolved": sorted(unresolved),
        "authority_effect": False,
    }
    return {**body, "dependency_hash": _sha(body)}


def failure_causality(trial: Mapping[str, Any]) -> str:
    classes = list(trial.get("errors") or []) + [
        str((arm.get("receipt") or {}).get("failure_attribution") or "")
        for arm in (trial.get("candidates") or {}).values()
    ]
    for value in classes:
        for marker, causality in _NON_CANDIDATE_FAILURES.items():
            if marker in value:
                return causality
    candidate_markers = (
        "EVALUATOR_REJECTION", "INTENT_PARSE_FAILURE", "INTENT_TYPE_FAILURE",
        "INTENT_SCOPE_FAILURE", "REPRESENTATION_UNSUPPORTED",
    )
    if any(any(marker in value for marker in candidate_markers) for value in classes):
        return "CANDIDATE_CAUSAL"
    development = ((trial.get("candidates") or {}).get("development") or {}).get("receipt") or {}
    if development.get("typed_outcome") == "FAIL":
        return "CANDIDATE_CAUSAL"
    return "UNKNOWN_CAUSAL"


def failure_exclusion_predicates(payload: Mapping[str, Any], causality_class: str) -> list[dict[str, Any]]:
    """Return search-space exclusions only for attributed candidate failures."""
    if causality_class != "CANDIDATE_CAUSAL":
        return []
    predicates: list[dict[str, Any]] = []
    for edit in payload.get("edits") or []:
        predicates.append({
            "kind": "exact_edit", "path": edit.get("path"),
            "old": edit.get("old"), "new": edit.get("new"),
        })
        if "\r" in str(edit.get("old", "")) + str(edit.get("new", "")):
            predicates.append({"kind": "representation_crlf"})
    return predicates


def utility_family(
    *,
    task_family: str,
    metric: str,
    epsilon_dev: float,
    epsilon_holdout: float,
    holdout_degradation_tolerance: float,
) -> dict[str, Any]:
    if metric not in METRICS:
        raise ValueError("unknown utility metric")
    return _sealed(
        UTILITY_FAMILY_SCHEMA,
        task_family=task_family,
        metric_vector=[metric],
        metric_directions={metric: METRICS[metric]},
        metric_scales={metric: "native_declared_units"},
        aggregation_rule="single_metric_signed_delta",
        comparison_semantics="matched_baseline_candidate_and_promoted_state/1.0",
        evaluator_semantics="frozen_host_verification_contract/1.0",
        epsilon_dev=epsilon_dev,
        epsilon_holdout=epsilon_holdout,
        holdout_degradation_tolerance=holdout_degradation_tolerance,
        budget_semantics={"candidate_budget": 1, "call_budget": 0},
        applicability="declared_task_family_only",
    )


def evaluation_partition(*, development: Mapping[str, Any], holdout: Mapping[str, Any],
                         holdout_id: str, utility_family_hash: str) -> dict[str, Any]:
    return _sealed(
        PARTITION_SCHEMA,
        development_workload_identity=development["contract_hash"],
        holdout_workload_identity=holdout["contract_hash"],
        holdout_label=holdout_id,
        partition_role={"development": "tuning_forbidden_for_claim", "holdout": "one_use_withheld"},
        utility_family_hash=utility_family_hash,
        one_use=True,
    )


def holdout_content_hash(*, holdout: Mapping[str, Any], utility_family_hash: str,
                         evaluator_identity: str) -> str:
    return _sha({
        "canonical_holdout_contract": holdout["contract_hash"],
        "holdout_steps": holdout.get("steps"),
        "utility_family_hash": utility_family_hash,
        "evaluator_identity": evaluator_identity,
    })


def authority_state(policy: Mapping[str, Any], *, policy_receipt_hash: str) -> dict[str, Any]:
    return _sealed(
        AUTHORITY_STATE_SCHEMA,
        policy_receipt_hash=policy_receipt_hash,
        principal_id=policy.get("principal_id"),
        policy_hash=policy.get("policy_hash"),
        allowed_scopes=list(policy.get("allowed_path_prefixes") or ()),
        protected_scopes=list(policy.get("forbidden_path_prefixes") or CONTROL_PLANE_PREFIXES),
        allow_auto_promotion=bool(policy.get("allow_auto_promotion")),
        allow_recursive_generation=bool(policy.get("allow_recursive_generation")),
        host_issued=policy.get("host_issued") is True,
        model_may_modify_policy=bool(policy.get("model_may_modify_policy")),
        revocation_state="active",
    )


def capability_manifests() -> dict[str, Any]:
    candidate = ["declared_source", "development_metrics", "diagnosed_deficiency",
                 "allowed_targets", "experiment_evidence", "failure_constraints"]
    holdout = ["holdout_contract", "holdout_executor", "holdout_receipt", "holdout_partition_content"]
    return _sealed(
        CAPABILITY_SCHEMA,
        candidate_capabilities=candidate,
        holdout_capabilities=holdout,
        intersection=[],
        enforcement="INTERFACE_ENFORCED",
        provider_context_enforced=False,
        tool_using_agent="HELD",
        live_provider_holdout_eligible=False,
    )


def comparison_schema_noncompensatory() -> bool:
    """Hard gates are not members of the optimizable metric vector."""
    return not set(METRICS) & set(HARD_GATES)


def utilities_compatible(generations: Sequence[Mapping[str, Any]]) -> bool:
    families = [row.get("utility_family_hash") for row in generations]
    if families and None not in families and len(set(families)) == 1:
        return True
    contracts = [row.get("utility_contract_hash") for row in generations]
    return bool(contracts) and None not in contracts and len(set(contracts)) == 1


def reconstruct_realized_delta(baseline: Mapping[str, Any], measurement: Mapping[str, Any],
                               metric: str) -> dict[str, float | None]:
    measured = measurement.get("measured") or {}
    return {
        "delta_dev": signed_delta(baseline.get("development", {}).get("metrics") or {},
                                  (measured.get("development") or {}).get("metrics") or {}, metric),
        "delta_holdout": signed_delta(baseline.get("holdout", {}).get("metrics") or {},
                                      (measured.get("holdout") or {}).get("metrics") or {}, metric),
    }


def utility_contract(
    *,
    metric: str,
    development_contract: Mapping[str, Any],
    holdout_contract: Mapping[str, Any],
    epsilon_dev: float,
    epsilon_holdout: float,
    holdout_degradation_tolerance: float,
    family: Mapping[str, Any] | None = None,
    partition: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if metric not in METRICS:
        raise ValueError("unknown utility metric")
    return _sealed(
        UTILITY_SCHEMA,
        metric_vector=[metric],
        metric_directions={metric: METRICS[metric]},
        metric_scales={metric: "native_declared_units"},
        development_workload_identity=development_contract["contract_hash"],
        holdout_workload_identity=holdout_contract["contract_hash"],
        utility_family_hash=None if not family else family.get("object_hash"),
        evaluation_partition_hash=None if not partition else partition.get("object_hash"),
        aggregation_rule="single_metric_signed_delta",
        comparison_semantics="matched_baseline_candidate_and_promoted_state/1.0",
        epsilon_dev=epsilon_dev,
        epsilon_holdout=epsilon_holdout,
        holdout_degradation_tolerance=holdout_degradation_tolerance,
        applicability="declared_workload_only",
    )


def metric_vector(steps: Sequence[Mapping[str, Any]], expected_count: int) -> dict[str, Any]:
    """Only machine-observed quantities. Missing checks are not passes."""
    complete = bool(steps) and len(steps) == expected_count
    return {
        "task_success": sum(step.get("passed") is True for step in steps) / expected_count,
        "duration_ms": sum(float(step["duration_ms"]) for step in steps),
        "output_bytes": sum(int(step["raw_observation"][key]) for step in steps
                            for key in ("stdout_byte_length", "stderr_byte_length")),
        "correctness": complete and all(step.get("passed") is True for step in steps),
        "measurement_complete": complete,
        "compute_cost": None, "context_cost": None, "memory_cost": None,
    }


def constitutional_verdict(checks: Mapping[str, str]) -> dict[str, Any]:
    states = {name: checks.get(name, "UNKNOWN") for name in CONSTITUTIONAL_CHECKS}
    if any(value == "FAIL" for value in states.values()):
        status = "FAIL"
    elif any(value != "PASS" for value in states.values()):
        status = "UNKNOWN"
    else:
        status = "PASS"
    return {"status": status, "checks": states, "pass": status == "PASS"}


def improvement_disposition(before: Mapping[str, Any], after: Mapping[str, Any], *,
                            metric: str, epsilon: float | None = None, gates: Mapping[str, str],
                            before_holdout: Mapping[str, Any] | None = None,
                            after_holdout: Mapping[str, Any] | None = None,
                            epsilon_dev: float | None = None, epsilon_holdout: float | None = None,
                            holdout_degradation_tolerance: float = 0.0) -> dict[str, Any]:
    epsilon_dev = float(epsilon_dev if epsilon_dev is not None else (epsilon if epsilon is not None else 1.0))
    epsilon_holdout = float(epsilon_holdout if epsilon_holdout is not None else epsilon_dev)
    tolerance = float(holdout_degradation_tolerance)
    if metric not in METRICS or any(not math.isfinite(x) or x < 0 for x in (epsilon_dev, epsilon_holdout, tolerance)):
        raise ValueError("invalid frozen metric or epsilon")
    if epsilon_dev <= 0 or epsilon_holdout <= 0:
        raise ValueError("invalid frozen metric or epsilon")
    states = {name: gates.get(name, "UNKNOWN") for name in HARD_GATES}
    feasible = all(value == "PASS" for value in states.values())
    holdout_before = before_holdout if before_holdout is not None else before
    holdout_after = after_holdout if after_holdout is not None else after
    delta_dev = signed_delta(before, after, metric)
    delta_holdout = signed_delta(holdout_before, holdout_after, metric)
    regression = ((before.get("correctness") is True and after.get("correctness") is not True)
                  or (holdout_before.get("correctness") is True and holdout_after.get("correctness") is not True))
    holdout_ok = delta_holdout is not None and delta_holdout >= -tolerance
    strong = (delta_dev is not None and delta_holdout is not None
              and delta_dev >= epsilon_dev and delta_holdout >= epsilon_holdout)
    if regression:
        states["regression"] = "FAIL"
        status = "REGRESSION_DETECTED"
        feasible = False
    elif states.get("regression") == "FAIL":
        status = "REGRESSION_DETECTED"
        feasible = False
    elif not feasible or delta_dev is None or delta_holdout is None:
        status = "HELD"
    elif not holdout_ok:
        status = "HELD"
    elif strong:
        repaired = (not before.get("correctness") and after.get("correctness")
                    and not holdout_before.get("correctness") and holdout_after.get("correctness"))
        status = "REPAIR_MEASURED" if repaired else "IMPROVED_WITHIN_DECLARED_WORKLOAD"
    else:
        status = "VERIFIED_MAINTENANCE"
    return _sealed(COMPARISON_SCHEMA, status=status, primary_delta=delta_dev,
                   delta_dev=delta_dev, delta_holdout=delta_holdout, feasible=feasible, gates=states,
                   epsilon_dev=epsilon_dev, epsilon_holdout=epsilon_holdout,
                   holdout_degradation_tolerance=tolerance, general_improvement_established=False)


def check_candidate_constraints(payload: Mapping[str, Any], constraints: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rejected, enforced = [], []
    edits = list(payload.get("edits") or [])
    for constraint in constraints:
        for predicate in constraint.get("predicates") or []:
            enforced.append(predicate)
            kind = predicate.get("kind")
            if kind == "exact_edit" and any(edit.get("path") == predicate.get("path")
                                            and edit.get("old") == predicate.get("old")
                                            and edit.get("new") == predicate.get("new") for edit in edits):
                rejected.append({"constraint_hash": constraint.get("constraint_hash"), "predicate": predicate})
            elif kind == "forbidden_target" and any(edit.get("path") == predicate.get("value") for edit in edits):
                rejected.append({"constraint_hash": constraint.get("constraint_hash"), "predicate": predicate})
            elif kind == "forbidden_path_prefix" and any(
                    str(edit.get("path") or "").startswith(str(predicate.get("prefix") or "\0")) for edit in edits):
                rejected.append({"constraint_hash": constraint.get("constraint_hash"), "predicate": predicate})
            elif kind == "representation_crlf" and any("\r" in str(edit.get("old", "")) + str(edit.get("new", ""))
                                                       for edit in edits):
                rejected.append({"constraint_hash": constraint.get("constraint_hash"), "predicate": predicate})
    return {"admissible": not rejected, "rejected": rejected, "enforced": enforced,
            "candidates_rejected_by_constraint": int(bool(rejected))}


def cumulative_improvement_disposition(generations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Convenience inspection for already-resolved objects; not canonical assurance."""
    errors = []
    if len(generations) < 2:
        errors.append("insufficient_adjacent_generations")
    for index, generation in enumerate(generations):
        if not _valid(generation):
            errors.append("invalid_generation_record")
        if generation.get("authority_leakage", 0) != 0:
            errors.append("authority_leakage")
        if generation.get("evaluator_mutation", 0) != 0 or generation.get("policy_mutation", 0) != 0:
            errors.append("control_plane_mutation")
        if generation.get("generation_state") != "REALIZED_GENERATION":
            errors.append("generation_not_realized")
        if generation.get("status") not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}:
            errors.append("generation_not_feasible")
        if (generation.get("delta_holdout") is None
                or float(generation["delta_holdout"]) < -float(generation.get("holdout_degradation_tolerance") or 0)):
            errors.append("holdout_regression")
        if index and _gen_index(generation.get("parent_generation") or "") != _gen_index(generations[index - 1].get("candidate_generation") or ""):
            errors.append("lineage_break")
        if index and _gen_index(generation.get("candidate_generation") or "") != (_gen_index(generation.get("parent_generation") or "") or -1) + 1:
            errors.append("nonadjacent_generation")
    compatible = utilities_compatible(generations)
    scalar = sum(float(generation.get("delta_dev") or 0) for generation in generations) if compatible else None
    vector = [{"generation": generation.get("candidate_generation"),
               "utility_contract_hash": generation.get("utility_contract_hash"),
               "delta_dev": generation.get("delta_dev"),
               "delta_holdout": generation.get("delta_holdout")} for generation in generations]
    mechanics = not errors
    return _sealed(CUMULATIVE_SCHEMA, errors=errors,
                   cumulative_generation_mechanics_verified=mechanics,
                   canonical_store_reconstructed=False,
                   utility_contracts_compatible=compatible,
                   cumulative_scalar_gain=scalar,
                   cumulative_utility_vector=vector,
                   cumulative_self_improvement_established=False,
                   history_utility_established=False,
                   claim_ceiling="TWO_GENERATION_MECHANICS_VERIFIED_IN_DETERMINISTIC_CONTROLS" if mechanics
                   else "DETERMINISTIC_CONTROLS_ONLY")


class GovernedImprovement:
    """Host coordinator composing authenticated policy, Store and transduction.

    Holdout confidentiality is a callback-input boundary, not OS sandboxing.
    """

    def __init__(self, store: Any, repo: str, root: str | Path, *,
                 policy_receipt_hash: str, secret: str):
        self.store, self.repo, self.root = store, repo, Path(root).resolve()
        self.policy_receipt_hash, self._secret = policy_receipt_hash, secret
        self._policy()

    def _policy(self) -> dict[str, Any]:
        checked = verify_autonomy_policy(self.store, self.repo, self.policy_receipt_hash, secret=self._secret)
        if not checked["valid"]:
            raise PermissionError("invalid external policy: " + ",".join(checked["errors"]))
        return checked["receipt"]

    def _record(self, kind: str, obj: Mapping[str, Any], *, session: Mapping[str, Any] | None = None) -> dict[str, Any]:
        session = session or _session(self.store, self.repo, kind)
        return self.store.append_symbiotic_receipt(self.repo, {
            "kind": kind, "session_id": session["session_id"], "body_epoch_id": session["body_epoch_id"],
            "turn_id": 0, "event_id": kind + "_" + obj["object_hash"],
            "object": dict(obj), "historical_evidence_only": True, **_closed(),
        })

    def _resolve(self, receipt_hash: str, kind: str) -> dict[str, Any]:
        record = self.store.symbiotic_receipt(receipt_hash, repo=self.repo)
        if (not record or record.get("kind") != kind
                or not self.store.verify_symbiotic_receipt(self.repo, receipt_hash)["valid"]
                or not _valid(record.get("object") or {})):
            raise ValueError("missing or invalid canonical " + kind)
        return record

    def _scope(self, targets: Sequence[str]) -> list[str]:
        targets = _safe_targets(targets)
        errors = _policy_scope_errors(self._policy(), {"targets": targets, "patch": ""})
        if errors:
            raise PermissionError(",".join(errors))
        return targets

    def _measure_path(self, path: Path, contract: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
        pre = worktree_payload_hashes(path)
        steps = [run_host_verification_step(path, {
            **step, "observation_schema": policy["observation_policy"],
            "max_stdout_bytes": policy["stdout_limit"], "max_stderr_bytes": policy["stderr_limit"],
            "timeout_seconds": min(step["timeout_seconds"], policy["timeout_seconds"]),
        }) for step in contract["steps"]]
        post = worktree_payload_hashes(path)
        sound = pre == post and _sound_steps(steps, contract)
        return _sealed("cortex-improvement-baseline/1.0", steps=steps, sound=sound,
                       preimages=pre, postimages=post,
                       metrics=metric_vector(steps, len(contract["steps"])))

    def _baseline(self, contract: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="cortex-gsi-baseline-") as temp:
            path = Path(temp) / "baseline"
            if _git(self.root, ["worktree", "add", "--detach", str(path), policy["subject_source_head"]]).returncode:
                raise RuntimeError("baseline worktree creation failed")
            try:
                return self._measure_path(path, contract, policy)
            finally:
                if _git(self.root, ["worktree", "remove", "--force", str(path)]).returncode:
                    raise RuntimeError("baseline worktree cleanup failed")

    def diagnose(self, *, subject: str, contract: Mapping[str, Any], metric: str,
                 threshold: float, active_defeaters: Sequence[str] = ()) -> dict[str, Any]:
        targets = self._scope(contract["targets"])
        if metric not in METRICS or not math.isfinite(threshold):
            raise ValueError("invalid diagnosis metric")
        if not _verify_contract(contract, targets)["valid"]:
            raise ValueError("invalid diagnosis instrument")
        policy = freeze_transduction_policy(self.root, policy_id="gsi-diagnosis", allowed_targets=targets,
                                           verification_contract=contract, allowed_intent_schema=INTENT_SCHEMA_V2)
        observation = self._baseline(contract, policy)
        observed = self._record("gsi_diagnosis_observation", observation)
        value = observation["metrics"][metric]
        deficient = value < threshold if METRICS[metric] == "increase" else value > threshold
        opportunity_id = _sha({
            "subject": subject, "source_revision": repository_head(self.root),
            "metric": metric, "observation": observation["object_hash"],
        })
        obj = _sealed(OPPORTUNITY_SCHEMA, opportunity_id=opportunity_id,
                      source_revision=repository_head(self.root),
                      subject_component=subject, subject_component_identity={p: _file_hash(self.root / p) for p in targets},
                      observation_receipts=[observed["receipt_hash"]], observed_metric=metric,
                      observed_value=value, threshold=threshold, desired_direction=METRICS[metric],
                      deficiency_class="measured_workload_deficit" if deficient else "none_measured",
                      failure_class=None, evidence_roots=[observation["object_hash"]],
                      candidate_scope=targets, active_defeaters=list(active_defeaters),
                      applicability=verification_environment(), assumptions=["host evaluator fitness is bounded"],
                      protected_invariants=["authority_invariance", "evaluator_independence"],
                      confidence="measured_instrument" if observation["sound"] else "unknown",
                      disposition="ELIGIBLE" if deficient and observation["sound"] and not active_defeaters else "HELD")
        return self._record("gsi_opportunity", obj)

    def freeze(self, opportunity_receipt: str, *, development: Mapping[str, Any],
               holdout: Mapping[str, Any], holdout_id: str, epsilon: float = 1.0,
               primary_metric: str = "task_success", epsilon_dev: float | None = None,
               epsilon_holdout: float | None = None, holdout_degradation_tolerance: float = 0.0) -> dict[str, Any]:
        opportunity = self._resolve(opportunity_receipt, "gsi_opportunity")["object"]
        for observation in opportunity["observation_receipts"]:
            self._resolve(observation, "gsi_diagnosis_observation")
        if (opportunity["disposition"] != "ELIGIBLE" or opportunity["active_defeaters"]
                or opportunity["source_revision"] != repository_head(self.root)):
            raise ValueError("HELD: opportunity missing, stale or defeated")
        targets = self._scope(opportunity["candidate_scope"])
        epsilon_dev = float(epsilon if epsilon_dev is None else epsilon_dev)
        epsilon_holdout = float(epsilon_dev if epsilon_holdout is None else epsilon_holdout)
        if primary_metric not in METRICS or epsilon_dev <= 0 or epsilon_holdout <= 0:
            raise ValueError("invalid metric")
        if holdout_degradation_tolerance < 0 or not all(map(math.isfinite, (epsilon_dev, epsilon_holdout, holdout_degradation_tolerance))):
            raise ValueError("invalid metric")
        if not holdout_id or development["contract_hash"] == holdout["contract_hash"]:
            raise ValueError("distinct holdout required")
        prior_experiments = self.store.symbiotic_receipts_by_kind(self.repo, "gsi_experiment")
        if any(r["object"]["holdout_id"] == holdout_id for r in prior_experiments):
            raise ValueError("holdout partition already reserved")
        policies = {}
        for label, contract in (("development", development), ("holdout", holdout)):
            if not _verify_contract(contract, targets)["valid"]:
                raise ValueError("invalid frozen evaluator")
            policies[label] = freeze_transduction_policy(
                self.root, policy_id="gsi-" + label, allowed_targets=targets,
                verification_contract=contract, allowed_intent_schema=INTENT_SCHEMA_V2,
                environment_requirements=verification_environment())
        family = utility_family(
            task_family=str(opportunity.get("subject_component") or "declared"),
            metric=primary_metric, epsilon_dev=epsilon_dev, epsilon_holdout=epsilon_holdout,
            holdout_degradation_tolerance=float(holdout_degradation_tolerance),
        )
        partition = evaluation_partition(
            development=development, holdout=holdout, holdout_id=holdout_id,
            utility_family_hash=family["object_hash"],
        )
        semantic_holdout = semantic_holdout_identity(holdout)
        content_hash = semantic_holdout["raw_semantic_hash"]
        prior_holdouts = self.store.symbiotic_receipts_by_kind(self.repo, "gsi_holdout_reservation")
        if any((r.get("object") or {}).get("holdout_content_hash") == content_hash for r in prior_holdouts):
            raise ValueError("holdout content already reserved")
        holdout_reservation = self._record(
            "gsi_holdout_reservation",
            _sealed(HOLDOUT_RESERVATION_SCHEMA, holdout_content_hash=content_hash),
        )
        if holdout_reservation.get("inserted") is not True:
            raise ValueError("holdout content already reserved")
        utility = utility_contract(
            metric=primary_metric,
            development_contract=development,
            holdout_contract=holdout,
            epsilon_dev=epsilon_dev,
            epsilon_holdout=epsilon_holdout,
            holdout_degradation_tolerance=float(holdout_degradation_tolerance),
            family=family, partition=partition,
        )
        utility_receipt = self._record("gsi_utility_contract", utility)
        authority = authority_state(self._policy(), policy_receipt_hash=self.policy_receipt_hash)
        capabilities = capability_manifests()
        dependencies = bounded_dependency_identity(self.root, targets)
        obj = _sealed(EXPERIMENT_SCHEMA, source_contract_schema=CONTRACT_SCHEMA_V2,
                      baseline_head=repository_head(self.root), opportunity_receipt=opportunity_receipt,
                      opportunity_hash=opportunity["object_hash"], allowed_targets=targets,
                      forbidden_targets=list(CONTROL_PLANE_PREFIXES),
                      subject_component=opportunity["subject_component"],
                      subject_identity=opportunity["subject_component_identity"],
                      contracts={"development": dict(development), "holdout": dict(holdout)},
                      transduction_policies=policies, environment=verification_environment(),
                      instrument_identity={"development_contract_hash": development["contract_hash"],
                                           "holdout_contract_hash": holdout["contract_hash"],
                                           "primary_metric": primary_metric},
                      representation_identity="utf8-lf-exact-bytes/1.0",
                      dependency_identity=dependencies,
                      utility_contract_receipt=utility_receipt["receipt_hash"],
                      utility_contract_hash=utility["object_hash"],
                      utility_family=family, utility_family_hash=family["object_hash"],
                      evaluation_partition=partition, evaluation_partition_hash=partition["object_hash"],
                      holdout_content_hash=content_hash,
                      holdout_semantic_identity=semantic_holdout,
                      authority_state=authority, authority_state_hash=authority["object_hash"],
                      capability_manifest=capabilities,
                      primary_metric=primary_metric, epsilon=epsilon_dev, epsilon_dev=epsilon_dev,
                      epsilon_holdout=epsilon_holdout, holdout_degradation_tolerance=float(holdout_degradation_tolerance),
                      holdout_id=holdout_id, policy_receipt_hash=self.policy_receipt_hash,
                      policy_hash=self._policy()["policy_hash"],
                      candidate_budget=1, call_budget=0, model_provider="deterministic-host-callback",
                      stopping_rule="one_candidate_one_use", tournament_rule="feasible_then_primary",
                      canary_rule="existing_authenticated_promotion_only", rollback_rule="existing_policy_rollback",
                      holdout_used_for_generation=False, full_os_isolation="UNKNOWN",
                      candidate_capability_set=capabilities["candidate_capabilities"],
                      holdout_capability_set=capabilities["holdout_capabilities"],
                      holdout_capability_intersection=capabilities["intersection"],
                      holdout_capability_enforcement=capabilities["enforcement"],
                      live_provider_holdout_eligible=False,
                      history_utility_established=False,
                      control_surface=worktree_payload_hashes(self.root))
        return self._record("gsi_experiment", obj)

    def run(self, experiment_receipt: str, generate: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> dict[str, Any]:
        """Historical deterministic path; Store discovery semantics remain unchanged."""
        return self._run(experiment_receipt, generate)

    def _run(self, experiment_receipt: str,
             generate: Callable[[Mapping[str, Any]], Mapping[str, Any]], *,
             empirical: Mapping[str, Any] | None = None) -> dict[str, Any]:
        frozen = self._resolve(experiment_receipt, "gsi_experiment")
        exp = frozen["object"]
        if exp["policy_receipt_hash"] != self.policy_receipt_hash or exp["policy_hash"] != self._policy()["policy_hash"]:
            raise PermissionError("policy binding failure")
        if exp["baseline_head"] != repository_head(self.root):
            raise ValueError("baseline HEAD changed")
        if exp["environment"] != verification_environment():
            raise ValueError("HELD: environment changed")
        if exp["subject_identity"] != {p: _file_hash(self.root / p) for p in exp["allowed_targets"]}:
            raise ValueError("subject preimage changed")
        if exp["control_surface"] != worktree_payload_hashes(self.root):
            raise ValueError("frozen control surface changed")
        session = {"session_id": frozen["session_id"], "body_epoch_id": frozen["body_epoch_id"]}
        reservation = self._record("gsi_candidate_reservation", _sealed("cortex-gsi-reservation/1.0",
                                   experiment_receipt=experiment_receipt), session=session)
        if reservation.get("inserted") is not True:
            raise ValueError("experiment exhausted; no repeated holdout")
        baseline = {label: self._baseline(exp["contracts"][label], exp["transduction_policies"][label])
                    for label in ("development", "holdout")}
        present = self._constraint_records(exp) if empirical is None else list(empirical.get("constraints") or [])
        consumed = ([item for item in present if item["persistence"] == "APPLY"]
                    if empirical is None else list(present))
        callback_constraints = [{
            "constraint_hash": item.get("constraint_hash"),
            "status": item.get("status"),
            "failure_classes": item.get("failure_classes") or [],
            "scope": item.get("scope") or [],
            "predicates": item.get("predicates") or [],
            "persistence": item.get("persistence"),
            "causality_class": item.get("causality_class"),
        } for item in consumed]
        improvements = (self._applicable_improvements(exp) if empirical is None
                        else list(empirical.get("improvements") or []))
        opportunity = self._resolve(exp["opportunity_receipt"], "gsi_opportunity")["object"]
        context = {
            "source": {p: (self.root / p).read_text(encoding="utf-8") for p in exp["allowed_targets"]},
            "development_metrics": baseline["development"]["metrics"],
            "allowed_targets": exp["allowed_targets"], "call_budget": 0,
            "experiment_hash": exp["object_hash"], "experiment_id": exp["object_hash"],
            "opportunity_id": opportunity.get("opportunity_id"),
            "subject_component": exp.get("subject_component"),
            "diagnosed_deficiency": opportunity.get("deficiency_class"),
            "primary_metric": exp["primary_metric"], "desired_direction": METRICS[exp["primary_metric"]],
            "epsilon_dev": exp.get("epsilon_dev", exp.get("epsilon")),
            "withheld_epsilon": exp.get("epsilon_holdout", exp.get("epsilon")),
            "withheld_degradation_tolerance": exp.get("holdout_degradation_tolerance", 0.0),
            "applicable_constraints": callback_constraints,
            "verified_improvement_evidence": improvements,
        }
        context_receipt = None
        if empirical is not None:
            # Arm names and experimental interpretations are deliberately absent.
            context_receipt = self._record("gsi_candidate_context", candidate_context(
                experiment_receipt=experiment_receipt,
                treatment_receipt=empirical["treatment_receipt"],
                execution_contract_receipt=empirical["execution_contract_receipt"],
                source_revision=exp["baseline_head"], utility_family_hash=exp["utility_family_hash"],
                context=context, capability_manifest=exp["capability_manifest"],
            ), session=session)
        arms, errors, payload, rejected = {}, [], None, {"admissible": True, "rejected": [], "enforced": [],
                                                          "candidates_rejected_by_constraint": 0}
        evaluator_mutation = policy_mutation = 0
        try:
            payload = json.loads(json.dumps(generate(json.loads(json.dumps(context)))))
            if (exp["control_surface"] != worktree_payload_hashes(self.root)
                    or repository_head(self.root) != exp["baseline_head"]):
                evaluator_mutation = 1
                raise ValueError("candidate modified frozen source or evaluator")
            self._policy()
            extra = set(payload) - {"schema_version", "summary", "edits"}
            if extra:
                policy_mutation = 1
                raise ValueError("candidate cannot alter experiment")
            proposed_targets = [edit["path"] for edit in payload["edits"]]
            self._scope(proposed_targets)
            if set(proposed_targets) != set(exp["allowed_targets"]):
                raise ValueError("candidate scope mismatch")
            rejected = check_candidate_constraints(payload, consumed)
            if not rejected["admissible"]:
                raise ValueError("CONSTRAINT_REJECTED")
            self._record("gsi_generated_candidate", _sealed("cortex-gsi-candidate/1.1" if empirical else "cortex-gsi-candidate/1.0",
                         experiment_hash=exp["object_hash"], payload=payload,
                         candidate_context_receipt=(context_receipt or {}).get("receipt_hash"),
                         candidate_context_hash=((context_receipt or {}).get("object") or {}).get("context_hash"),
                         treatment_receipt=(empirical or {}).get("treatment_receipt"),
                         execution_contract_hash=(empirical or {}).get("execution_contract_hash"),
                         assignment_receipt=(empirical or {}).get("assignment_receipt"),
                         model_runtime_hash=(empirical or {}).get("model_runtime_hash")), session=session)
            for label in ("development", "holdout"):
                policy, contract = exp["transduction_policies"][label], exp["contracts"][label]
                result = execute_bound_transduction(self.root, policy, payload, contract)
                attestation = attest_transduction_receipt(result["receipt"], policy, self.root,
                                                         contract, result["compilation"])
                verification = result.get("verification") or {}
                steps = verification.get("steps") or []
                result["attestation"] = attestation
                result["inspection"] = inspect_v2_arm(self.root, result, policy, contract)
                result["metrics"] = metric_vector(steps, len(contract["steps"]))
                arms[label] = result
        except (ValueError, PermissionError, KeyError, TypeError) as exc:
            errors.append(str(exc))
        gates = {name: "UNKNOWN" for name in HARD_GATES}
        current_authority = authority_state(self._policy(), policy_receipt_hash=self.policy_receipt_hash)
        protected_now = {path: digest for path, digest in worktree_payload_hashes(self.root).items()
                         if path.startswith(CONTROL_PLANE_PREFIXES)}
        protected_then = {path: digest for path, digest in (exp.get("control_surface") or {}).items()
                          if path.startswith(CONTROL_PLANE_PREFIXES)}
        constitutional_evidence = {
            "measured_opportunity_evidence": bool(opportunity.get("evidence_roots")
                                                    and opportunity.get("observation_receipts")
                                                    and opportunity.get("disposition") == "ELIGIBLE"),
            "evaluator_unchanged": evaluator_mutation == 0 and policy_mutation == 0
                                    and exp["control_surface"] == worktree_payload_hashes(self.root),
            "experiment_preceded_candidate": reservation.get("inserted") is True,
            "noncompensatory_gates": comparison_schema_noncompensatory(),
            "holdout_capability_separated": (
                not set(exp.get("candidate_capability_set") or []) & set(exp.get("holdout_capability_set") or [])
                and not any(key.startswith("holdout") or "holdout_" in key for key in context)
            ),
            "failure_constraints_causally_scoped": all(
                item.get("causality_class") == "CANDIDATE_CAUSAL" for item in consumed
            ),
            "generation_not_self_authorized": (
                current_authority.get("host_issued") is True
                and current_authority.get("model_may_modify_policy") is False
                and exp.get("policy_hash") == current_authority.get("policy_hash")
                and exp.get("policy_receipt_hash") == self.policy_receipt_hash
                and policy_mutation == 0
            ),
            "cumulative_claim_closed": True,
            "authority_unchanged": current_authority.get("object_hash") == exp.get("authority_state_hash"),
            "protected_surface_unchanged": evaluator_mutation == 0 and protected_now == protected_then
                                           and all(not target.startswith(CONTROL_PLANE_PREFIXES)
                                                   for target in exp["allowed_targets"]),
        }
        verdict = evaluate_gsi_constitution(constitutional_evidence)
        if len(arms) == 2:
            dev, hold = arms["development"], arms["holdout"]
            representation = all(a["receipt"].get("failure_attribution") != "REPRESENTATION_UNSUPPORTED" for a in arms.values())
            env_ok = all(((a["receipt"].get("environment_identity") or {}).get("environment_hash")
                          == (exp["environment"] or {}).get("environment_hash")) for a in arms.values())
            workload = (dev["metrics"]["correctness"] and hold["metrics"]["correctness"]
                        and dev["metrics"]["measurement_complete"] and hold["metrics"]["measurement_complete"])
            gates.update({
                "source": "PASS" if repository_head(self.root) == exp["baseline_head"] else "FAIL",
                "transduction": "PASS" if all(a["receipt"]["typed_outcome"] == "PASS" for a in arms.values()) else "FAIL",
                "attestation": combine_attestation_gates(
                    [a["inspection"]["gate"] if a["inspection"]["valid"] else "FAIL" for a in arms.values()]),
                "workload_correctness": "PASS" if workload else "FAIL",
                "constitutional_invariants": verdict["status"],
                "regression": "FAIL" if ((baseline["development"]["metrics"]["correctness"] and not dev["metrics"]["correctness"])
                                         or (baseline["holdout"]["metrics"]["correctness"] and not hold["metrics"]["correctness"])) else "PASS",
                "environment": "PASS" if env_ok else "FAIL",
                "evaluator_integrity": "PASS" if all(b["sound"] for b in baseline.values()) else "FAIL",
                "policy_scope": "PASS",
            })
            if not representation:
                gates["transduction"] = "FAIL"
        elif errors:
            gates["constitutional_invariants"] = verdict["status"]
            gates["policy_scope"] = "FAIL" if policy_mutation or any("protected" in item for item in errors) else gates["policy_scope"]
        comparison = improvement_disposition(
            baseline["development"]["metrics"], (arms.get("development") or {}).get("metrics") or {},
            metric=exp["primary_metric"], epsilon_dev=float(exp.get("epsilon_dev") or exp.get("epsilon") or 1),
            epsilon_holdout=float(exp.get("epsilon_holdout") or exp.get("epsilon") or 1),
            holdout_degradation_tolerance=float(exp.get("holdout_degradation_tolerance") or 0),
            gates=gates, before_holdout=baseline["holdout"]["metrics"],
            after_holdout=(arms.get("holdout") or {}).get("metrics") or {},
        )
        constitutional_evidence["cumulative_claim_closed"] = comparison.get("general_improvement_established") is False
        verdict = evaluate_gsi_constitution(constitutional_evidence)
        if "constitutional_invariants" in gates:
            gates["constitutional_invariants"] = verdict["status"]
        obj = _sealed(RESULT_SCHEMA_V2, experiment_receipt=experiment_receipt,
                      experiment_hash=exp["object_hash"], baseline=baseline, candidates=arms,
                      candidate_payload=payload, comparison=comparison, errors=errors,
                      status=comparison["status"], holdout_used_for_generation=False,
                      policy_hash=exp["policy_hash"],
                      constraints_present=[item["constraint_hash"] for item in present],
                      constraints_consumed=[item["constraint_hash"] for item in consumed],
                      constraints_enforced=rejected["enforced"],
                      candidates_rejected_by_constraint=rejected["candidates_rejected_by_constraint"],
                      failure_constraints_consumed=[item["constraint_hash"] for item in consumed],
                      verified_improvements_consumed=[item["improvement_hash"] for item in improvements],
                      constitutional=verdict,
                      evaluator_mutation=evaluator_mutation, policy_mutation=policy_mutation,
                      assurance_debt=typed_assurance_debt({"source": gates["source"],
                          "transduction": gates["transduction"], "instrument": gates["attestation"],
                          "environment": gates["environment"], "experiment": "PASS",
                          "causal": "UNKNOWN", "applicability": "UNKNOWN", "replication": "NOT_TESTED"}),
                      claim_ceiling="DETERMINISTIC_CONTROLS_ONLY", promotion_count=0,
                      authority_leakage=0, cumulative_improvement_established=False,
                      cumulative_self_improvement_established=False,
                      history_utility_established=False,
                      candidate_context_receipt=(context_receipt or {}).get("receipt_hash"),
                      candidate_context_hash=((context_receipt or {}).get("object") or {}).get("context_hash"),
                      treatment_receipt=(empirical or {}).get("treatment_receipt"),
                      execution_contract_receipt=(empirical or {}).get("execution_contract_receipt"),
                      execution_contract_hash=(empirical or {}).get("execution_contract_hash"),
                      assignment_receipt=(empirical or {}).get("assignment_receipt"),
                      cumulative_generation_mechanics_verified=False)
        return self._record("gsi_trial", obj, session=session)

    def recycle(self, trial_receipt: str) -> dict[str, Any]:
        trial = self._resolve(trial_receipt, "gsi_trial")["object"]
        exp = self._resolve(trial["experiment_receipt"], "gsi_experiment")["object"]
        success = trial["comparison"]["feasible"] and trial["status"] in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}
        schema = VERIFIED_SCHEMA if success else CONSTRAINT_SCHEMA
        payload = trial.get("candidate_payload") or {}
        causality_class = "CANDIDATE_CAUSAL" if success else failure_causality(trial)
        predicates = [] if success else failure_exclusion_predicates(payload, causality_class)
        applicability = {
            "originating_source_head": exp["baseline_head"],
            "subject_component": exp.get("subject_component"),
            "subject_component_identity": exp["subject_identity"],
            "relevant_dependency_closure": exp["dependency_identity"],
            "environment": exp["environment"],
            "environment_identity": exp["environment"],
            "instrument_identity": exp.get("instrument_identity"),
            "representation_identity": exp.get("representation_identity"),
            "utility_family_hash": exp.get("utility_family_hash"),
            "failure_class": (trial.get("errors") or [None])[0],
            "scope": exp["allowed_targets"],
        }
        obj = _sealed(schema, originating_experiment=trial["experiment_receipt"],
                      failure_receipt=None if success else trial_receipt,
                      trial_receipt=trial_receipt, trial_hash=trial["object_hash"],
                      applicability=applicability, scope=exp["allowed_targets"],
                      predicates=predicates,
                      causality_class=causality_class,
                      status="VERIFIED_WITHIN_CONTROL" if success else "HELD_CONSTRAINT",
                      before_metrics=trial["baseline"]["development"]["metrics"],
                      after_metrics=(trial["candidates"].get("development") or {}).get("metrics"),
                      before_holdout_metrics=trial["baseline"]["holdout"]["metrics"],
                      after_holdout_metrics=(trial["candidates"].get("holdout") or {}).get("metrics"),
                      measured_effect=trial["comparison"].get("delta_dev"),
                      failure_classes=trial["errors"] + [a["receipt"]["failure_attribution"] for a in trial["candidates"].values() if a["receipt"]["failure_attribution"] != "OBSERVED_CANDIDATE_PASS"],
                      counterevidence=[], active_defeaters=[], superseded_by=[], historical_evidence_only=True,
                      influence_class="EXPERIMENT_EVIDENCE" if success else "HISTORICAL_EVIDENCE",
                      experiment_evidence=success,
                      claim_ceiling="DETERMINISTIC_CONTROLS_ONLY", admission_required=True)
        return self._record("gsi_verified_improvement" if success else "gsi_constraint", obj)

    def _constraint_records(self, exp: Mapping[str, Any]) -> list[dict[str, Any]]:
        records = []
        subject = {p: _file_hash(self.root / p) for p in exp["allowed_targets"]}
        for record in self.store.symbiotic_receipts_by_kind(self.repo, "gsi_constraint"):
            obj = record.get("object") or {}
            persistence = (self.constraint_persistence(
                obj, environment=exp["environment"], targets=exp["allowed_targets"],
                subject_identity=subject, instrument_identity=None
            ) if obj.get("causality_class") == "CANDIDATE_CAUSAL" else "NOT_APPLICABLE")
            records.append({
                "constraint_hash": obj.get("object_hash"), "status": obj.get("status"),
                "failure_classes": obj.get("failure_classes") or [], "scope": obj.get("scope") or [],
                "predicates": obj.get("predicates") or [], "persistence": persistence,
                "causality_class": obj.get("causality_class") or "UNKNOWN_CAUSAL",
                "applicability": obj.get("applicability") or {},
            })
        return records

    def _applicable_improvements(self, exp: Mapping[str, Any]) -> list[dict[str, Any]]:
        consumed = []
        defeated = {
            (record.get("object") or {}).get("improvement_hash")
            for record in self.store.symbiotic_receipts_by_kind(self.repo, "gsi_evidence_challenge")
            if _valid(record.get("object") or {})
        }
        for record in self.store.symbiotic_receipts_by_kind(self.repo, "gsi_verified_improvement"):
            obj = record.get("object") or {}
            if obj.get("schema_version") != VERIFIED_SCHEMA or not _valid(obj):
                continue
            record_hash = str(record.get("receipt_hash") or "")
            if not record_hash or self.store.verify_symbiotic_receipt(self.repo, record_hash).get("valid") is not True:
                continue
            if (obj.get("object_hash") in defeated
                    or obj.get("status") != "VERIFIED_WITHIN_CONTROL"
                    or obj.get("influence_class") != "EXPERIMENT_EVIDENCE"
                    or obj.get("counterevidence") or obj.get("active_defeaters")
                    or obj.get("superseded_by")):
                continue
            apply = obj.get("applicability") or {}
            env = apply.get("environment") or apply.get("environment_identity") or {}
            if env != (exp.get("environment") or {}):
                continue
            if not set(obj.get("scope") or []) & set(exp["allowed_targets"]):
                continue
            if apply.get("relevant_dependency_closure") != exp.get("dependency_identity"):
                continue
            if (apply.get("utility_family_hash") and exp.get("utility_family_hash")
                    and apply.get("utility_family_hash") != exp.get("utility_family_hash")):
                continue
            if apply.get("representation_identity") != exp.get("representation_identity"):
                continue
            consumed.append({
                "improvement_hash": obj.get("object_hash"),
                "measured_effect": obj.get("measured_effect"),
                "scope": obj.get("scope"), "status": obj.get("status"),
                "historical_evidence_only": True, "active_guidance": False,
                "influence_class": "EXPERIMENT_EVIDENCE",
                "authority_effect": False, "admission_required": True,
            })
        return consumed

    def challenge_experiment_evidence(self, improvement_receipt: str, *, reason: str) -> dict[str, Any]:
        """Append a defeater without rewriting the verified historical object."""
        improvement = self._resolve(improvement_receipt, "gsi_verified_improvement")["object"]
        if not reason.strip():
            raise ValueError("challenge reason required")
        obj = _sealed(
            EXPERIMENT_EVIDENCE_SCHEMA,
            improvement_hash=improvement["object_hash"],
            reason=reason.strip(),
            disposition="DEFEATED_FOR_FUTURE_GSI_CONTEXT",
            influence_class="EXPERIMENT_EVIDENCE",
        )
        return self._record("gsi_evidence_challenge", obj)

    def constraint_persistence(self, constraint: Mapping[str, Any], *, environment: Mapping[str, Any],
                               targets: Sequence[str], subject_identity: Mapping[str, str],
                               instrument_identity: Mapping[str, Any] | None = None) -> str:
        if constraint.get("schema_version") != CONSTRAINT_SCHEMA or not _valid(constraint):
            return "NOT_APPLICABLE"
        apply = constraint.get("applicability") or {}
        env = apply.get("environment") or apply.get("environment_identity") or {}
        if not env.get("os_family") or not environment.get("os_family"):
            return "NOT_APPLICABLE"
        if env.get("os_family") != environment.get("os_family"):
            return "NOT_APPLICABLE"
        scope = set(constraint.get("scope") or apply.get("scope") or [])
        if not scope or not set(targets) & scope:
            return "NOT_APPLICABLE"
        dependency = apply.get("relevant_dependency_closure") or {}
        current_dependency = bounded_dependency_identity(self.root, targets)
        identity = apply.get("subject_component_identity") or {}
        overlapping = {path: digest for path, digest in identity.items() if path in subject_identity}
        identity_ok = (bool(overlapping)
                       and overlapping == {path: subject_identity[path] for path in overlapping}
                       and dependency == current_dependency)
        recorded_instrument = apply.get("instrument_identity") or {}
        instrument_ok = instrument_identity is None or (not recorded_instrument) or recorded_instrument == instrument_identity
        if not identity_ok or not instrument_ok:
            return "REVALIDATION_REQUIRED"
        return "APPLY"

    def constraint_applies(self, constraint: Mapping[str, Any], *, environment: Mapping[str, Any],
                           targets: Sequence[str], subject_identity: Mapping[str, str] | None = None,
                           instrument_identity: Mapping[str, Any] | None = None) -> bool:
        identity = subject_identity or {p: _file_hash(self.root / p) for p in targets}
        return self.constraint_persistence(
            constraint, environment=environment, targets=targets, subject_identity=identity,
            instrument_identity=instrument_identity,
        ) == "APPLY"

    def remeasure(self, experiment_receipt: str) -> dict[str, Any]:
        """Measure the live working tree. Candidate worktree success is not promoted success."""
        exp = self._resolve(experiment_receipt, "gsi_experiment")["object"]
        measured = {label: self._measure_path(self.root, exp["contracts"][label], exp["transduction_policies"][label])
                    for label in ("development", "holdout")}
        return _sealed("cortex-gsi-remeasurement/1.0", experiment_hash=exp["object_hash"],
                       source_revision=repository_head(self.root), measured=measured,
                       workload_correctness=all(item["metrics"]["correctness"] for item in measured.values()))

    def promote_verified(self, trial_receipt: str) -> dict[str, Any]:
        """Promote an exact attested artifact through the canonical mutation membrane."""
        trial_record = self._resolve(trial_receipt, "gsi_trial")
        trial, exp = trial_record["object"], self._resolve(trial_record["object"]["experiment_receipt"], "gsi_experiment")["object"]
        policy = self._policy()
        errors = []
        if policy.get("allow_auto_promotion") is not True:
            errors.append("auto_promotion_not_delegated")
        if not policy.get("canary_steps"):
            errors.append("canary_contract_missing")
        if trial["status"] not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"} or not trial["comparison"]["feasible"]:
            errors.append("trial_not_promotable")
        if trial["status"] not in set(policy.get("allowed_trial_statuses") or ()):
            errors.append("improvement_status_not_authorized")
        if repository_head(self.root) != exp["baseline_head"]:
            errors.append("PROMOTION_HELD_STALE_BASELINE")
        if exp["control_surface"] != worktree_payload_hashes(self.root):
            errors.append("control_surface_changed")
        if exp["policy_hash"] != policy.get("policy_hash"):
            errors.append("policy_hash_changed")
        if exp["environment"] != verification_environment():
            errors.append("environment_applicability_degraded")
        if exp["subject_identity"] != {path: _file_hash(self.root / path) for path in exp["allowed_targets"]}:
            errors.append("subject_preimage_changed")
        after_authority = authority_state(policy, policy_receipt_hash=self.policy_receipt_hash)
        if exp.get("authority_state_hash") and after_authority["object_hash"] != exp.get("authority_state_hash"):
            errors.append("authority_state_changed")
        arms = trial.get("candidates") or {}
        dev, hold = arms.get("development") or {}, arms.get("holdout") or {}
        dev_compilation, hold_compilation = dev.get("compilation") or {}, hold.get("compilation") or {}
        proposal = dev_compilation.get("proposal")
        if not proposal:
            errors.append("evaluated_proposal_missing")
        elif (hold_compilation.get("proposal_hash") != dev_compilation.get("proposal_hash")
              or dev_compilation.get("proposal_hash") != proposal.get("proposal_hash")):
            errors.append("promotion_reconstruction_mismatch")
        for label, arm in (("development", dev), ("holdout", hold)):
            if not arm or not inspect_v2_arm(
                self.root, arm, exp["transduction_policies"][label], exp["contracts"][label]
            )["valid"]:
                errors.append(label + "_attestation_stale")
        if errors:
            raise PermissionError("promotion held: " + ",".join(errors))
        before_head = repository_head(self.root)
        membrane = execute_policy_promotion_membrane(
            self.root, policy=policy, proposal=proposal,
            source_head=exp["baseline_head"], canary_contract=exp["contracts"]["development"],
        )
        rolled_back = membrane["rolled_back"]
        application = membrane["application"]
        remeasurement_receipt = None
        promoted_comparison = None
        exact_artifact = False
        if not rolled_back and application:
            expected = dev_compilation["postimage_hashes"]
            exact_artifact = (proposal["proposal_hash"] == dev["receipt"]["proposal_identity"]
                              and application["proposal_hash"] == proposal["proposal_hash"]
                              and application["postimage_hashes"] == expected)
            measured = self.remeasure(trial["experiment_receipt"])
            measured_targets = {path: measured["measured"]["development"]["preimages"].get(path)
                                for path in exp["allowed_targets"]}
            exact_artifact = exact_artifact and measured_targets == expected
            promoted_gates = dict(trial["comparison"]["gates"])
            promoted_gates.update({
                "source": "PASS" if exact_artifact else "FAIL",
                "transduction": "PASS" if exact_artifact else "FAIL",
                "attestation": trial["comparison"]["gates"].get("attestation", "UNKNOWN"),
                "environment": "PASS" if exp["environment"] == verification_environment() else "FAIL",
                "constitutional_invariants": trial["constitutional"]["status"],
            })
            promoted_comparison = improvement_disposition(
                trial["baseline"]["development"]["metrics"], measured["measured"]["development"]["metrics"],
                before_holdout=trial["baseline"]["holdout"]["metrics"],
                after_holdout=measured["measured"]["holdout"]["metrics"],
                metric=exp["primary_metric"], epsilon_dev=exp["epsilon_dev"],
                epsilon_holdout=exp["epsilon_holdout"],
                holdout_degradation_tolerance=exp["holdout_degradation_tolerance"], gates=promoted_gates,
            )
            remeasurement_obj = _sealed(
                REMEASUREMENT_SCHEMA, experiment_hash=exp["object_hash"], trial_receipt=trial_receipt,
                evaluated_proposal_hash=proposal["proposal_hash"], promoted_proposal_hash=application["proposal_hash"],
                expected_postimages=expected, promoted_postimages=application["postimage_hashes"],
                post_apply_pre_eval_hashes=measured_targets, measured=measured["measured"],
                comparison=promoted_comparison, exact_artifact_preserved=exact_artifact,
            )
            remeasurement_receipt = self._record("gsi_post_promotion_measurement", remeasurement_obj)
            if promoted_comparison["status"] not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}:
                rollback_applied_patch(self.root, proposal)
                rolled_back = True
            else:
                _git(self.root, ["add", "-A"])
                _git(self.root, ["commit", "-qm", "gsi-promoted"])
        status = ("rolled_back_canary_failed" if rolled_back and remeasurement_receipt is None
                  else "rolled_back_remeasurement_failed" if rolled_back else "promoted_remeasured")
        obj = _sealed(PROMOTION_SCHEMA, trial_receipt=trial_receipt, experiment_receipt=trial["experiment_receipt"],
                      proposal_hash=proposal["proposal_hash"], evaluated_artifact_hash=proposal["proposal_hash"],
                      promoted_artifact_hash=None if not application else application["proposal_hash"],
                      application=application, membrane=membrane, remeasurement_receipt_hash=None if not remeasurement_receipt else remeasurement_receipt["receipt_hash"],
                      promoted_comparison=promoted_comparison, exact_artifact_preserved=exact_artifact,
                      rolled_back=rolled_back, status=status,
                      source_revision_before=before_head, source_revision_after=repository_head(self.root),
                      host_policy_authorized=True, canonical_promotion_membrane=True,
                      tournament_promotion=False)
        return self._record("gsi_promotion", obj)

    def record_generation(self, *, parent: str, trial_receipt: str, candidate_generation: str,
                          parent_receipt: str | None = None, promotion_receipt: str | None = None) -> dict[str, Any]:
        trial = self._resolve(trial_receipt, "gsi_trial")["object"]
        exp = self._resolve(trial["experiment_receipt"], "gsi_experiment")["object"]
        parent_index, child_index = _gen_index(parent), _gen_index(candidate_generation)
        if parent_index is None or child_index is None or parent == candidate_generation:
            raise ValueError("candidate generation cannot self-verify")
        errors = []
        if child_index != parent_index + 1:
            errors.append("nonadjacent_generation")
            if child_index > parent_index + 1:
                errors.append("generation_skip_rejected")
        parent_obj = None
        if parent_index > 0:
            if not parent_receipt:
                raise ValueError("parent generation receipt required")
            parent_obj = self._resolve(parent_receipt, "gsi_generation")["object"]
            if parent_obj.get("candidate_generation") != parent:
                raise ValueError("parent generation mismatch")
        elif parent_receipt:
            parent_obj = self._resolve(parent_receipt, "gsi_generation")["object"]
        policy = self._policy()
        if policy.get("allow_recursive_generation") is not True:
            errors.append("recursive_generation_not_delegated")
        promotion = None
        remeasurement = None
        if promotion_receipt:
            promotion = self._resolve(promotion_receipt, "gsi_promotion")["object"]
            if promotion.get("remeasurement_receipt_hash"):
                remeasurement = self._resolve(
                    promotion["remeasurement_receipt_hash"], "gsi_post_promotion_measurement"
                )["object"]
        if not promotion:
            errors.append("generation_not_realized")
        elif (promotion.get("rolled_back") is not False
              or promotion.get("status") != "promoted_remeasured"
              or not remeasurement
              or remeasurement.get("comparison", {}).get("status") not in {
                  "REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"
              }):
            errors.append("promotion_not_realized")
        if promotion and promotion.get("source_revision_before") != exp.get("baseline_head"):
            errors.append("generation_source_before_mismatch")
        if parent_obj and parent_obj.get("source_revision_after") != (promotion or {}).get("source_revision_before"):
            errors.append("parent_source_continuity_failure")
        candidate_delta_dev = trial["comparison"].get("delta_dev")
        candidate_delta_holdout = trial["comparison"].get("delta_holdout")
        realized = reconstruct_realized_delta(trial["baseline"], remeasurement or {}, exp["primary_metric"]) if remeasurement else {"delta_dev": None, "delta_holdout": None}
        delta_dev, delta_holdout = realized["delta_dev"], realized["delta_holdout"]
        after_authority = authority_state(policy, policy_receipt_hash=self.policy_receipt_hash)
        if exp.get("authority_state_hash") and after_authority["object_hash"] != exp.get("authority_state_hash"):
            errors.append("authority_state_changed")
        compatible_utility = not parent_obj or parent_obj.get("utility_family_hash") == exp.get("utility_family_hash")
        parent_cumulative = parent_obj.get("cumulative_scalar_gain") if parent_obj else 0.0
        cumulative = (None if not compatible_utility or delta_dev is None or parent_cumulative is None
                      else float(parent_cumulative) + float(delta_dev))
        generation_state = "REALIZED_GENERATION" if not errors else "CANDIDATE_GENERATION"
        status = (remeasurement or {}).get("comparison", {}).get("status") or trial["status"]
        if generation_state != "REALIZED_GENERATION":
            status = "HELD"
        obj = _sealed(REALIZED_GENERATION_SCHEMA if generation_state == "REALIZED_GENERATION" else GENERATION_SCHEMA,
                      generation_id=candidate_generation, parent_generation=parent,
                      candidate_generation=candidate_generation, verifier_generation=parent,
                      generation_state=generation_state,
                      parent_generation_receipt_hash=parent_receipt,
                      parent_source_revision_after=(parent_obj or {}).get("source_revision_after"),
                      child_source_revision_before=(promotion or {}).get("source_revision_before"),
                      trial_receipt=trial_receipt, promotion_receipt=promotion_receipt,
                      promotion_receipt_hash=promotion_receipt,
                      post_promotion_measurement_receipt=(promotion or {}).get("remeasurement_receipt_hash"),
                      post_promotion_measurement_hash=(remeasurement or {}).get("object_hash"),
                      utility_contract_receipt=exp.get("utility_contract_receipt"),
                      utility_contract_hash=exp.get("utility_contract_hash"),
                      utility_family_hash=exp.get("utility_family_hash"),
                      evaluation_partition_hash=exp.get("evaluation_partition_hash"),
                      source_revision_before=(promotion or {}).get("source_revision_before") or exp.get("baseline_head"),
                      source_revision_after=(promotion or {}).get("source_revision_after"),
                      before_dev_metrics=trial["baseline"]["development"]["metrics"],
                      after_dev_metrics=((remeasurement or {}).get("measured") or {}).get("development", {}).get("metrics")
                                        or (trial["candidates"].get("development") or {}).get("metrics"),
                      before_holdout_metrics=trial["baseline"]["holdout"]["metrics"],
                      after_holdout_metrics=((remeasurement or {}).get("measured") or {}).get("holdout", {}).get("metrics")
                                            or (trial["candidates"].get("holdout") or {}).get("metrics"),
                      candidate_delta_dev=candidate_delta_dev, candidate_delta_holdout=candidate_delta_holdout,
                      delta_dev=delta_dev, delta_holdout=delta_holdout,
                      holdout_degradation_tolerance=trial["comparison"].get("holdout_degradation_tolerance", 0),
                      cumulative_delta_from_G0=cumulative, cumulative_scalar_gain=cumulative,
                      authority_before_hash=exp.get("authority_state_hash"),
                      authority_after_hash=after_authority["object_hash"],
                      cumulative_utility_vector=[{
                          "generation": candidate_generation,
                          "utility_family_hash": exp.get("utility_family_hash"),
                          "utility_contract_hash": exp.get("utility_contract_hash"),
                          "delta_dev": delta_dev,
                          "delta_holdout": delta_holdout,
                      }],
                      failure_constraints_consumed=list(trial.get("failure_constraints_consumed") or []),
                      constraints_consumed=list(trial.get("constraints_consumed") or []),
                      verified_improvements_consumed=list(trial.get("verified_improvements_consumed") or []),
                      improvements_consumed=list(trial.get("verified_improvements_consumed") or []),
                      regression_count=int(trial["status"] == "REGRESSION_DETECTED"),
                      rollback_count=int(bool((promotion or {}).get("rolled_back"))),
                      authority_leakage=int(trial.get("authority_leakage") or 0),
                      evaluator_mutation=int(trial.get("evaluator_mutation") or 0),
                      policy_mutation=int(trial.get("policy_mutation") or 0),
                      cumulative_improvement_established=False,
                      cumulative_self_improvement_established=False,
                      history_utility_established=False,
                      cumulative_generation_mechanics_verified=False,
                      status=status, errors=errors)
        return self._record("gsi_generation", obj)

    def verify_cumulative_chain(self, generation_receipts: Sequence[str]) -> dict[str, Any]:
        """Reconstruct a generation chain exclusively from canonical Store receipts."""
        generations: list[dict[str, Any]] = []
        errors: list[str] = []
        previous_receipt = None
        previous = None
        for receipt_hash in generation_receipts:
            try:
                generation_record = self._resolve(receipt_hash, "gsi_generation")
                generation = generation_record["object"]
                trial = self._resolve(generation["trial_receipt"], "gsi_trial")["object"]
                promotion = self._resolve(generation["promotion_receipt_hash"], "gsi_promotion")["object"]
                measurement = self._resolve(
                    generation["post_promotion_measurement_receipt"], "gsi_post_promotion_measurement"
                )["object"]
                utility = self._resolve(generation["utility_contract_receipt"], "gsi_utility_contract")["object"]
            except (KeyError, TypeError, ValueError):
                errors.append("canonical_chain_receipt_invalid")
                continue
            if generation.get("generation_state") != "REALIZED_GENERATION":
                errors.append("generation_not_realized")
            if promotion.get("trial_receipt") != generation.get("trial_receipt"):
                errors.append("promotion_trial_binding_invalid")
            if promotion.get("remeasurement_receipt_hash") != generation.get("post_promotion_measurement_receipt"):
                errors.append("remeasurement_receipt_binding_invalid")
            if measurement.get("object_hash") != generation.get("post_promotion_measurement_hash"):
                errors.append("remeasurement_identity_invalid")
            if utility.get("object_hash") != generation.get("utility_contract_hash"):
                errors.append("utility_contract_binding_invalid")
            if (promotion.get("rolled_back") is not False
                    or promotion.get("exact_artifact_preserved") is not True
                    or measurement.get("comparison", {}).get("status") not in {
                        "REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"
                    }):
                errors.append("promotion_not_verified")
            if generation.get("authority_leakage") != 0 or trial.get("authority_leakage") != 0:
                errors.append("authority_leakage")
            if trial.get("evaluator_mutation") or trial.get("policy_mutation"):
                errors.append("control_plane_mutation")
            if previous is not None:
                if generation.get("parent_generation_receipt_hash") != previous_receipt:
                    errors.append("parent_receipt_mismatch")
                if previous.get("source_revision_after") != generation.get("source_revision_before"):
                    errors.append("source_state_continuity_failure")
            try:
                experiment = self._resolve(trial["experiment_receipt"], "gsi_experiment")["object"]
                reconstructed = reconstruct_realized_delta(trial["baseline"], measurement, experiment["primary_metric"])
                if (reconstructed["delta_dev"] != generation.get("delta_dev")
                        or reconstructed["delta_holdout"] != generation.get("delta_holdout")):
                    errors.append("CHAIN_INVALID")
            except (KeyError, TypeError, ValueError):
                errors.append("CHAIN_INVALID")
            previous_receipt, previous = receipt_hash, generation
            generations.append(generation)
        inspected = cumulative_improvement_disposition(generations)
        errors.extend(inspected.get("errors") or [])
        compatible = utilities_compatible(generations)
        scalar = sum(float(row.get("delta_dev") or 0) for row in generations) if compatible else None
        vector = [item for row in generations for item in row.get("cumulative_utility_vector") or []]
        unique_errors = sorted(set(errors))
        mechanics = len(generations) >= 2 and not unique_errors
        return _sealed(
            CUMULATIVE_SCHEMA,
            generation_receipts=list(generation_receipts),
            errors=unique_errors,
            canonical_store_reconstructed=True,
            utility_contracts_compatible=compatible,
            cumulative_scalar_gain=scalar,
            cumulative_utility_vector=vector,
            cumulative_generation_mechanics_verified=mechanics,
            cumulative_self_improvement_established=False,
            history_utility_established=False,
            claim_ceiling=("PROOF_CHAIN_MECHANICS_VERIFIED_IN_DETERMINISTIC_CONTROLS"
                           if mechanics else "DETERMINISTIC_CONTROLS_ONLY"),
        )

    def build_history_pool(self, experiment_receipt: str) -> dict[str, Any]:
        """Reconstruct treatment candidates from canonical Store receipts.

        Applicability is derived here; callers cannot assert it.
        """
        exp = self._resolve(experiment_receipt, "gsi_experiment")["object"]
        current_subject = {p: _file_hash(self.root / p) for p in exp["allowed_targets"]}
        applicable_positive = {item["improvement_hash"] for item in self._applicable_improvements(exp)}
        items = []
        for kind, channel, evidence_type in (
            ("gsi_constraint", "H-", "FAILURE_CONSTRAINT"),
            ("gsi_verified_improvement", "H+", "VERIFIED_EXPERIMENT_EVIDENCE"),
        ):
            for record in self.store.symbiotic_receipts_by_kind(self.repo, kind):
                receipt_hash = str(record.get("receipt_hash") or "")
                obj = record.get("object") or {}
                apply = obj.get("applicability") or {}
                integrity = bool(receipt_hash and _valid(obj)
                                 and self.store.verify_symbiotic_receipt(self.repo, receipt_hash).get("valid") is True)
                if not integrity:
                    disposition = "UNKNOWN"
                elif obj.get("superseded_by"):
                    disposition = "SUPERSEDED"
                elif obj.get("active_defeaters") or obj.get("counterevidence"):
                    disposition = "DEFEATED"
                elif kind == "gsi_constraint":
                    persistence = self.constraint_persistence(
                        obj, environment=exp["environment"], targets=exp["allowed_targets"],
                        subject_identity=current_subject,
                        instrument_identity=exp.get("instrument_identity"),
                    )
                    disposition = {"APPLY": "APPLICABLE",
                                   "REVALIDATION_REQUIRED": "REVALIDATION_REQUIRED",
                                   "NOT_APPLICABLE": "INAPPLICABLE"}.get(persistence, "UNKNOWN")
                else:
                    instrument_compatible = (
                        apply.get("instrument_identity") is None
                        or apply.get("instrument_identity") == exp.get("instrument_identity")
                    )
                    disposition = (
                        "APPLICABLE"
                        if obj.get("object_hash") in applicable_positive and instrument_compatible
                        else "INAPPLICABLE"
                    )
                payload = ({
                    "constraint_hash": obj.get("object_hash"), "status": obj.get("status"),
                    "failure_classes": obj.get("failure_classes") or [],
                    "scope": obj.get("scope") or [],
                    "predicates": obj.get("predicates") or [],
                    "persistence": "APPLY" if disposition == "APPLICABLE" else "NOT_APPLICABLE",
                    "causality_class": obj.get("causality_class") or "UNKNOWN_CAUSAL",
                } if channel == "H-" else {
                    "improvement_hash": obj.get("object_hash"), "measured_effect": obj.get("measured_effect"),
                    "scope": obj.get("scope") or [], "status": obj.get("status"),
                    "historical_evidence_only": True, "active_guidance": False,
                    "influence_class": "EXPERIMENT_EVIDENCE", "authority_effect": False,
                    "admission_required": True,
                })
                items.append({
                    "canonical_receipt_hash": receipt_hash, "object_hash": obj.get("object_hash"),
                    "schema_version": obj.get("schema_version"), "evidence_type": evidence_type,
                    "channel": channel, "origin_experiment": obj.get("originating_experiment"),
                    "subject_identity": apply.get("subject_component_identity"),
                    "dependency_identity": apply.get("relevant_dependency_closure"),
                    "environment_identity": apply.get("environment") or apply.get("environment_identity"),
                    "instrument_identity": apply.get("instrument_identity"),
                    "representation_identity": apply.get("representation_identity"),
                    "utility_family_hash": apply.get("utility_family_hash"),
                    "scope": obj.get("scope") or [], "active_defeaters": obj.get("active_defeaters") or [],
                    "supersession_state": "SUPERSEDED" if obj.get("superseded_by") else "CURRENT",
                    "applicability_disposition": disposition, "payload": payload,
                })
        items.sort(key=lambda row: (row["canonical_receipt_hash"], row["object_hash"] or ""))
        pool = causal_sealed(HISTORY_POOL_SCHEMA, experiment_receipt=experiment_receipt,
                             experiment_hash=exp["object_hash"], items=items,
                             derived_from_canonical_store=True)
        return self._record("gsi_history_pool", pool)

    def freeze_empirical_treatment(self, experiment_receipt: str, *, arm: str,
                                   history_receipts: Sequence[str] = (),
                                   sham_match_receipt: str | None = None) -> dict[str, Any]:
        """Freeze a canonical A/B/C history set; no caller applicability booleans."""
        if arm not in {"A", "B", "C"}:
            raise ValueError("invalid treatment arm")
        exp = self._resolve(experiment_receipt, "gsi_experiment")["object"]
        pool_receipt = self.build_history_pool(experiment_receipt)
        pool = pool_receipt["object"]
        wanted = set(history_receipts)
        selected = [item for item in pool["items"] if item["canonical_receipt_hash"] in wanted]
        if len(selected) != len(wanted):
            raise ValueError("history must resolve from canonical experiment pool")
        if arm == "A" and selected:
            raise ValueError("no-history arm must be empty")
        if arm in {"B", "C"} and not selected:
            raise ValueError("confirmatory B/C treatment requires nonempty history")
        expected = "APPLICABLE" if arm == "C" else "INAPPLICABLE"
        if arm in {"B", "C"} and any(item["applicability_disposition"] != expected for item in selected):
            raise ValueError("history applicability does not match arm")
        if arm == "B":
            if not sham_match_receipt:
                raise ValueError("B treatment requires a PASSing sham match")
            sham_match = self._resolve(sham_match_receipt, "gsi_sham_match")["object"]
            if sham_match.get("disposition") != "PASS" or set(sham_match.get("b_history_hashes") or []) != {
                item["object_hash"] for item in selected
            }:
                raise ValueError("B treatment sham match does not bind selected history")
        elif sham_match_receipt is not None:
            raise ValueError("sham match is only valid for B treatment")
        history = sorted(selected, key=lambda row: row["canonical_receipt_hash"])
        obj = causal_sealed(
            TREATMENT_SCHEMA_V11, opaque_treatment_id=_sha({"experiment": exp["object_hash"], "history": sorted(wanted)}),
            experiment_receipt=experiment_receipt, experiment_hash=exp["object_hash"],
            utility_family_hash=exp["utility_family_hash"], history_pool_receipt=pool_receipt["receipt_hash"],
            history_objects=history,
            positive_history=[item for item in history if item["channel"] == "H+"],
            failure_history=[item for item in history if item["channel"] == "H-"],
            history_ordering="canonical_receipt_hash", history_frozen=True,
            sham_match_receipt=sham_match_receipt,
            analysis_arm=arm,
            candidate_visible_treatment_label=False, evaluator_blinding="DECLARED_WHERE_PRACTICAL",
            empirical_arm_analysis_only=arm, live_execution_authorized=False,
            history_utility_established=False,
        )
        return self._record("gsi_empirical_treatment", obj)

    def build_sham_history(self, experiment_receipt: str, applicable_receipts: Sequence[str], *,
                           tolerances: Mapping[str, int]) -> tuple[dict[str, Any], dict[str, Any]]:
        pool = self.build_history_pool(experiment_receipt)["object"]
        applicable = [item for item in pool["items"] if item["canonical_receipt_hash"] in set(applicable_receipts)]
        if len(applicable) != len(set(applicable_receipts)) or any(i["applicability_disposition"] != "APPLICABLE" for i in applicable):
            raise ValueError("applicable history set invalid")
        sham = []
        for source in applicable:
            match = next((item for item in pool["items"] if item["applicability_disposition"] == "INAPPLICABLE"
                          and item["channel"] == source["channel"]
                          and item["canonical_receipt_hash"] not in {x["canonical_receipt_hash"] for x in sham}), None)
            if match is None:
                raise ValueError("no structurally typed inapplicable sham available")
            sham.append(match)
        match_obj = sham_match(applicable, sham, tolerances)
        match_receipt = self._record("gsi_sham_match", match_obj)
        if match_obj["disposition"] != "PASS":
            raise ValueError("sham match outside frozen tolerance")
        treatment = self.freeze_empirical_treatment(
            experiment_receipt, arm="B", history_receipts=[i["canonical_receipt_hash"] for i in sham],
            sham_match_receipt=match_receipt["receipt_hash"])
        return treatment, match_receipt

    def freeze_execution_contract(self, experiment_receipt: str, *, model_runtime: Mapping[str, Any],
                                  task_set_hash: str, analysis_plan_hash: str,
                                  budgets: Mapping[str, int], sham_tolerances: Mapping[str, int]) -> dict[str, Any]:
        exp = self._resolve(experiment_receipt, "gsi_experiment")["object"]
        if not valid_causal(model_runtime):
            raise ValueError("invalid model runtime identity")
        obj = make_execution_contract(
            source_revision=exp["baseline_head"], task_set_hash=task_set_hash,
            utility_family_hash=exp["utility_family_hash"], model_runtime_hash=model_runtime["object_hash"],
            candidate_budget=int(budgets["candidate_budget"]),
            provider_call_budget=int(budgets["provider_call_budget"]), token_budget=int(budgets["token_budget"]),
            wall_clock_budget_seconds=int(budgets["wall_clock_budget_seconds"]),
            tool_surface=[], capabilities=exp["capability_manifest"], mutation_scope=exp["allowed_targets"],
            authority_state_hash=exp["authority_state_hash"], evaluator_identities=exp["instrument_identity"],
            stopping_rule=exp["stopping_rule"], failure_attribution_policy="typed-causal-localization/1.0",
            treatment_definitions={"A": "NO_HISTORY", "B": "SHAM", "C": "APPLICABLE"},
            sham_tolerances=sham_tolerances, randomization_scheme="content-addressed-blocked/1.0",
            analysis_plan_hash=analysis_plan_hash,
            claim_ceiling="DETERMINISTIC_DELIVERY_AND_EXECUTION_LOCK_MECHANICS_ONLY")
        return self._record("gsi_execution_contract", obj)

    def record_empirical_component(self, kind: str, obj: Mapping[str, Any]) -> dict[str, Any]:
        """Persist a closed II.4 contract without creating a generic truth store."""
        allowed = {
            "gsi_model_runtime", "gsi_analysis_plan", "gsi_task", "gsi_task_set",
            "gsi_randomization", "gsi_common_baseline", "gsi_execution_readiness",
            "gsi_execution_lock", "gsi_context_difference", "gsi_assignment", "gsi_sham_match",
        }
        if kind not in allowed or not valid_causal(obj):
            raise ValueError("invalid empirical component")
        return self._record(kind, obj)

    def verify_gsi_iii_readiness(self, *, component_receipts: Mapping[str, tuple[str, str]],
                                 implementation_ci: str, protocol_status: str,
                                 provider_calls: int = 0, live_authorized: bool = False) -> dict[str, Any]:
        components = {name: self._resolve(receipt_hash, kind)["object"]
                      for name, (receipt_hash, kind) in component_receipts.items()}
        result = execution_readiness(
            components=components, implementation_ci=implementation_ci,
            protocol_status=protocol_status, provider_calls=provider_calls,
            live_authorized=live_authorized,
        )
        return self._record("gsi_execution_readiness", result)

    def freeze_execution_lock(self, *, protocol_hash: str,
                              component_receipts: Mapping[str, tuple[str, str]],
                              readiness_receipt: str) -> dict[str, Any]:
        """Materialize one canonical, non-authorizing membrane around execution."""
        readiness = self._resolve(readiness_receipt, "gsi_execution_readiness")["object"]
        components = {name: self._resolve(receipt_hash, kind)["object"]
                      for name, (receipt_hash, kind) in component_receipts.items()}
        expected = {"execution_contract", "task_set", "model_runtime", "randomization",
                    "analysis_plan", "common_baseline", "treatments", "sham_match"}
        if set(components) != expected:
            raise ValueError("execution lock components incomplete")
        execution = components["execution_contract"]
        component_hashes = {name: obj["object_hash"] for name, obj in components.items()}
        component_hashes["utility_family"] = execution["utility_family_hash"]
        component_hashes["sham_matches"] = component_hashes.pop("sham_match")
        lock = make_execution_lock(protocol_hash=protocol_hash, component_hashes=component_hashes,
                                   readiness=readiness, readiness_receipt=readiness_receipt)
        attestation_components = dict(components)
        attestation_components["sham_matches"] = attestation_components.pop("sham_match")
        check = verify_execution_lock(lock, attestation_components, expected_readiness=readiness)
        if not check["valid"]:
            raise ValueError("execution lock binding failure")
        return self._record("gsi_execution_lock", lock)

    def _resolve_object_hash(self, kind: str, object_hash: str) -> dict[str, Any]:
        for record in self.store.symbiotic_receipts_by_kind(self.repo, kind):
            if (record.get("object") or {}).get("object_hash") == object_hash:
                return record
        raise ValueError(f"canonical object not found: {kind}/{object_hash}")

    def run_empirical(self, experiment_receipt: str, treatment_receipt: str,
                      execution_lock_receipt: str, assignment_receipt: str,
                      generate: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> dict[str, Any]:
        """Deterministic empirical delivery path. It performs no provider call itself."""
        exp = self._resolve(experiment_receipt, "gsi_experiment")["object"]
        treatment = self._resolve(treatment_receipt, "gsi_empirical_treatment")["object"]
        lock = self._resolve(execution_lock_receipt, "gsi_execution_lock")["object"]
        assignment = self._resolve(assignment_receipt, "gsi_assignment")["object"]
        readiness_receipt = lock.get("readiness_receipt")
        if not readiness_receipt:
            raise ValueError("execution lock is missing canonical readiness receipt")
        readiness = (self._resolve(readiness_receipt, "gsi_execution_readiness")["object"]
                     if readiness_receipt else None)
        component_hashes = lock.get("component_hashes") or {}
        execution_record = self._resolve_object_hash("gsi_execution_contract", component_hashes.get("execution_contract"))
        execution = execution_record["object"]
        execution_contract_receipt = execution_record["receipt_hash"]
        components = {"execution_contract": execution}
        for name, kind in (("task_set", "gsi_task_set"), ("model_runtime", "gsi_model_runtime"),
                           ("randomization", "gsi_randomization"), ("analysis_plan", "gsi_analysis_plan"),
                           ("common_baseline", "gsi_common_baseline"), ("treatments", "gsi_empirical_treatment"),
                           ("sham_matches", "gsi_sham_match")):
            components[name] = self._resolve_object_hash(kind, component_hashes.get(name))["object"]
        if not verify_execution_lock(lock, components, expected_readiness=readiness)["valid"]:
            raise ValueError("execution lock binding failure")
        if (treatment.get("experiment_hash") != exp["object_hash"]
                or execution.get("source_revision") != exp["baseline_head"]
                or execution.get("utility_family_hash") != exp["utility_family_hash"]
                or treatment.get("utility_family_hash") != exp["utility_family_hash"]):
            raise ValueError("empirical lineage mismatch")
        randomization = components["randomization"]
        if assignment.get("randomization_plan_hash") != randomization.get("object_hash"):
            raise ValueError("assignment/randomization binding failure")
        if assignment.get("task_hash") not in set(randomization.get("task_hashes") or []):
            raise ValueError("assignment task is outside frozen task set")
        if (assignment.get("task_hash"), assignment.get("arm")) not in {
            (row.get("task_hash"), row.get("arm"))
            for row in randomization.get("assignment_order") or []
        }:
            raise ValueError("assignment is not present in frozen randomization order")
        if treatment.get("analysis_arm") != assignment.get("arm"):
            raise ValueError("assignment/treatment arm mismatch")
        if treatment.get("object_hash") != component_hashes.get("treatments"):
            raise ValueError("treatment is not the locked treatment")
        if not validate_randomization_plan(randomization, components["task_set"].get("task_hashes") or []):
            raise ValueError("confirmatory randomization is incomplete")
        if not treatment.get("history_frozen") or execution.get("live_execution_authorized") is not False:
            raise ValueError("empirical execution contract not closed")
        constraints = [item["payload"] for item in treatment.get("failure_history") or []]
        improvements = [item["payload"] for item in treatment.get("positive_history") or []]
        trial = self._run(experiment_receipt, generate, empirical={
            "treatment_receipt": treatment_receipt,
            "execution_contract_receipt": execution_contract_receipt,
            "execution_contract_hash": execution["object_hash"],
            "assignment_receipt": assignment_receipt,
            "model_runtime_hash": execution["model_runtime_hash"],
            "constraints": constraints, "improvements": improvements,
        })
        obj = trial["object"]
        checks = {
            "CROSS_ARM_HISTORY_LEAK": (set(obj.get("constraints_consumed") or [])
                                       <= {i["object_hash"] for i in treatment.get("failure_history") or []}),
            "POST_RANDOMIZATION_HISTORY_MUTATION": True,
            "SOURCE_MISMATCH": execution["source_revision"] == repository_head(self.root),
            "TREATMENT_CONTEXT_MISMATCH": obj.get("treatment_receipt") == treatment_receipt,
            "MODEL_CONFIG_MISMATCH": all(
                (candidate.get("model_runtime_hash") or execution["model_runtime_hash"]) == execution["model_runtime_hash"]
                for candidate in self.store.symbiotic_receipts_by_kind(self.repo, "gsi_generated_candidate")
                if (candidate.get("object") or {}).get("experiment_hash") == exp["object_hash"]
            ),
            "BUDGET_MISMATCH": (len(obj.get("candidate_payload") or {}) >= 0
                                 and 0 <= execution.get("provider_call_budget", 0)
                                 and 0 <= execution.get("token_budget", 0)),
        }
        contamination = self._record("gsi_contamination", contamination_report(checks))
        if contamination["object"]["disposition"] != "PASS":
            raise ValueError("HOLD_EPISODE: empirical contamination")
        return trial

    def freeze_treatment(self, *, arm: str, history_kind: str, utility_family_hash: str,
                         history_items: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
        """Deterministic A/B/C treatment envelope. Does not authorize live calls."""
        if arm not in {"A", "B", "C"} or history_kind not in {"NO_HISTORY", "SHAM_HISTORY", "APPLICABLE_HISTORY"}:
            raise ValueError("invalid treatment arm")
        expected = {"A": "NO_HISTORY", "B": "SHAM_HISTORY", "C": "APPLICABLE_HISTORY"}[arm]
        if history_kind != expected:
            raise ValueError("treatment history mismatch")
        applicable = []
        for item in history_items:
            if history_kind == "SHAM_HISTORY" and item.get("applicability_valid") is True:
                raise ValueError("sham history must be inapplicable")
            if history_kind == "APPLICABLE_HISTORY" and item.get("applicability_valid") is not True:
                raise ValueError("applicable history required")
            if history_kind != "NO_HISTORY":
                applicable.append({
                    "object_hash": item.get("object_hash"),
                    "influence_class": item.get("influence_class") or "EXPERIMENT_EVIDENCE",
                    "applicability_valid": item.get("applicability_valid") is True,
                    "active_guidance": False,
                })
        if history_kind == "NO_HISTORY" and history_items:
            raise ValueError("no-history arm cannot carry inherited evidence")
        obj = _sealed(
            TREATMENT_SCHEMA, arm=arm, history_kind=history_kind,
            utility_family_hash=utility_family_hash, history_items=applicable,
            live_execution_authorized=False, provider_calls=0,
            history_utility_established=False, authority_effect=False,
        )
        return self._record("gsi_treatment", obj)

    def record_search_episode(self, *, treatment_receipt: str, trial_receipt: str,
                              candidate_evaluations: int, model_calls: int = 0,
                              token_cost: int = 0, duration_ms: float = 0,
                              realized_generation_receipt: str | None = None) -> dict[str, Any]:
        treatment = self._resolve(treatment_receipt, "gsi_treatment")["object"]
        trial = self._resolve(trial_receipt, "gsi_trial")["object"]
        if candidate_evaluations < 1:
            raise ValueError("candidate evaluations required")
        realized = 1 if realized_generation_receipt else 0
        eta = realized / candidate_evaluations
        obj = _sealed(
            SEARCH_EPISODE_SCHEMA,
            treatment_receipt=treatment_receipt, treatment_arm=treatment["arm"],
            trial_receipt=trial_receipt, realized_generation_receipt=realized_generation_receipt,
            candidate_evaluations=candidate_evaluations, model_calls=model_calls,
            token_cost=token_cost, duration_ms=duration_ms,
            realized_verified_improvements=realized,
            eta=eta, provider_calls=0, live_execution_authorized=False,
            history_utility_established=False,
            trial_status=trial.get("status"),
        )
        return self._record("gsi_search_episode", obj)

    def record_empirical_search_episode(self, *, experiment_receipt: str,
                                        treatment_receipt: str,
                                        execution_contract_receipt: str,
                                        assignment_receipt: str,
                                        candidate_context_receipt: str,
                                        trial_receipt: str, task_hash: str,
                                        randomization_assignment: Mapping[str, Any],
                                        candidate_receipts: Sequence[str],
                                        rejected_candidates: Sequence[str],
                                        candidate_evaluations: int,
                                        provider_calls: int, transport_retries: int,
                                        candidate_attempts: int, token_cost: int,
                                        duration_ms: float,
                                        promotion_receipt: str | None = None,
                                        realized_generation_receipt: str | None = None) -> dict[str, Any]:
        exp = self._resolve(experiment_receipt, "gsi_experiment")["object"]
        treatment = self._resolve(treatment_receipt, "gsi_empirical_treatment")["object"]
        execution = self._resolve(execution_contract_receipt, "gsi_execution_contract")["object"]
        assignment = self._resolve(assignment_receipt, "gsi_assignment")["object"]
        context = self._resolve(candidate_context_receipt, "gsi_candidate_context")["object"]
        trial = self._resolve(trial_receipt, "gsi_trial")["object"]
        if candidate_evaluations <= 0 or provider_calls < 0 or candidate_attempts < 0 or transport_retries < 0:
            raise ValueError("invalid canonical search accounting")
        for candidate_receipt in candidate_receipts:
            candidate = self._resolve(candidate_receipt, "gsi_generated_candidate")["object"]
            if candidate.get("candidate_context_hash") != context.get("context_hash"):
                raise ValueError("candidate/context binding failure")
            if candidate.get("treatment_receipt") != treatment_receipt:
                raise ValueError("candidate/treatment binding failure")
            if candidate.get("execution_contract_hash") != execution.get("object_hash"):
                raise ValueError("candidate/execution binding failure")
        if assignment.get("task_hash") != task_hash or assignment.get("arm") != treatment.get("analysis_arm"):
            raise ValueError("assignment episode binding failure")
        if randomization_assignment and (
            randomization_assignment.get("task_hash") not in {None, assignment.get("task_hash")}
            or randomization_assignment.get("arm") not in {None, assignment.get("arm")}
        ):
            raise ValueError("caller assignment mapping does not match canonical assignment")
        if trial.get("candidate_context_hash") != context.get("context_hash"):
            raise ValueError("trial/context binding failure")
        if trial.get("treatment_receipt") != treatment_receipt:
            raise ValueError("trial/treatment binding failure")
        supplied_promotion = None
        if promotion_receipt:
            supplied_promotion = self._resolve(promotion_receipt, "gsi_promotion")["object"]
        realized, gain, generation = 0, 0.0, None
        if realized_generation_receipt:
            try:
                generation = self._resolve(realized_generation_receipt, "gsi_generation")["object"]
                promotion = self._resolve(str(generation.get("promotion_receipt")), "gsi_promotion")["object"]
                measurement = self._resolve(str(generation.get("post_promotion_measurement_receipt")),
                                            "gsi_post_promotion_measurement")["object"]
                lineage_ok = (
                    generation.get("generation_state") == "REALIZED_GENERATION"
                    and promotion.get("rolled_back") is False
                    and measurement.get("comparison", {}).get("status") in {
                        "REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"
                    }
                    and generation.get("utility_family_hash") == exp.get("utility_family_hash")
                    and trial.get("experiment_receipt") == experiment_receipt
                    and trial.get("treatment_receipt") == treatment_receipt
                    and trial.get("execution_contract_receipt") == execution_contract_receipt
                    and (promotion_receipt is None
                         or generation.get("promotion_receipt") == promotion_receipt)
                )
                if supplied_promotion is not None and supplied_promotion != promotion:
                    lineage_ok = False
                if lineage_ok:
                    realized, gain = 1, float(generation.get("delta_dev") or 0)
            except (ValueError, TypeError):
                realized = 0
        eta = realized / candidate_evaluations
        eta_call = (realized / provider_calls) if provider_calls else None
        normalized_cost = float(candidate_evaluations + provider_calls + transport_retries)
        eta_cost = gain / normalized_cost if normalized_cost else None
        model_config_ok = all(
            (self._resolve(candidate_receipt, "gsi_generated_candidate")["object"].get("model_runtime_hash")
             or execution.get("model_runtime_hash")) == execution.get("model_runtime_hash")
            for candidate_receipt in candidate_receipts
        )
        budget_ok = (
            candidate_evaluations <= execution.get("candidate_budget", 0)
            and provider_calls <= execution.get("provider_call_budget", 0)
            and token_cost <= execution.get("token_budget", 0)
            and duration_ms <= execution.get("wall_clock_budget_seconds", 0) * 1000
        )
        contamination = contamination_report({
            "SOURCE_MISMATCH": exp.get("baseline_head") == execution.get("source_revision"),
            "TREATMENT_CONTEXT_MISMATCH": context.get("treatment_receipt") == treatment_receipt,
            "MODEL_CONFIG_MISMATCH": model_config_ok,
            "BUDGET_MISMATCH": budget_ok,
            "POST_RANDOMIZATION_HISTORY_MUTATION": treatment.get("history_frozen") is True,
        })
        obj = causal_sealed(
            SEARCH_EPISODE_SCHEMA_V11, execution_contract_receipt=execution_contract_receipt,
            execution_contract_hash=execution["object_hash"], experiment_receipt=experiment_receipt,
            experiment_hash=exp["object_hash"], treatment_receipt=treatment_receipt,
            treatment_hash=treatment["object_hash"], candidate_context_receipt=candidate_context_receipt,
            candidate_context_hash=context["context_hash"], utility_family_hash=exp["utility_family_hash"],
            evaluation_partition_hash=exp["evaluation_partition_hash"], source_revision=exp["baseline_head"],
            model_runtime_hash=execution["model_runtime_hash"], provider_config_hash=execution["model_runtime_hash"],
            task_hash=task_hash,
            randomization_assignment={"task_hash": assignment["task_hash"], "arm": assignment["arm"],
                                      "randomization_plan_hash": assignment["randomization_plan_hash"]},
            assignment_receipt=assignment_receipt,
            candidate_budget=execution["candidate_budget"], candidates_produced=len(candidate_receipts),
            candidate_receipts=list(candidate_receipts), rejected_candidates=list(rejected_candidates),
            candidate_evaluations=candidate_evaluations, provider_calls=provider_calls,
            transport_retries=transport_retries, candidate_attempts=candidate_attempts,
            token_cost=token_cost, duration_ms=duration_ms, promotion_receipt=promotion_receipt,
            realized_generation_receipt=realized_generation_receipt,
            realized_verified_improvements=realized, realized_utility_gain=gain,
            eta=eta, eta_call=eta_call, eta_cost=eta_cost,
            normalized_search_cost_formula="candidate_evaluations+provider_calls+transport_retries",
            terminal_state="COMPLETE" if contamination["disposition"] == "PASS" else "HELD",
            contamination=contamination, authority_leakage=0, evaluator_mutation=0, policy_mutation=0,
            history_utility_established=False, cumulative_self_improvement_established=False,
        )
        return self._record("gsi_empirical_search_episode", obj)
