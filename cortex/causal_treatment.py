"""GSI-II.4 causal-treatment contracts and deterministic execution locks.

These objects describe a future empirical execution.  They do not call a
provider, mutate source, admit memory, or grant authority.
"""
from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .coding_workspace import _sha

CANDIDATE_CONTEXT_SCHEMA = "cortex-gsi-candidate-context/1.0"
EXECUTION_CONTRACT_SCHEMA = "cortex-gsi-execution-contract/1.0"
MODEL_RUNTIME_SCHEMA = "cortex-gsi-model-runtime-identity/1.0"
RANDOMIZATION_SCHEMA = "cortex-gsi-randomization-plan/1.0"
TASK_SCHEMA = "cortex-gsi-task/1.0"
COMMON_BASELINE_SCHEMA = "cortex-gsi-common-baseline/1.0"
SHAM_MATCH_SCHEMA = "cortex-gsi-sham-match/1.0"
CONTEXT_DIFFERENCE_SCHEMA = "cortex-gsi-context-difference/1.0"
HOLDOUT_SEMANTIC_SCHEMA = "cortex-gsi-holdout-semantic-identity/1.0"
ANALYSIS_PLAN_SCHEMA = "cortex-gsi-analysis-plan/1.0"
EXECUTION_LOCK_SCHEMA = "cortex-gsi-execution-lock/1.0"
READINESS_SCHEMA = "cortex-gsi-execution-readiness/1.0"
SEARCH_EPISODE_SCHEMA_V11 = "cortex-gsi-search-episode/1.1"
TREATMENT_SCHEMA_V11 = "cortex-gsi-treatment/1.1"
HISTORY_POOL_SCHEMA = "cortex-gsi-history-pool/1.0"
CONTAMINATION_SCHEMA = "cortex-gsi-contamination/1.0"
ARM_ISOLATION_SCHEMA = "cortex-gsi-arm-isolation/1.0"

_CLOSED = (
    "authority_effect", "production_effect", "execution_authorized",
    "host_mutate_authorized", "memory_admission_authorized", "policy_effect",
    "promotion_authorized", "active_guidance",
)


def sealed(schema: str, **body: Any) -> dict[str, Any]:
    material = {"schema_version": schema, **body, **dict.fromkeys(_CLOSED, False)}
    return {**material, "object_hash": _sha(material)}


def valid(obj: Mapping[str, Any], schema: str | None = None) -> bool:
    return bool((schema is None or obj.get("schema_version") == schema)
                and obj.get("object_hash") == _sha({k: v for k, v in obj.items() if k != "object_hash"})
                and all(obj.get(key) is False for key in _CLOSED))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def token_estimate(value: Any) -> int:
    # Declared deterministic estimate, not provider tokenization.
    return (len(canonical_bytes(value)) + 3) // 4


def model_runtime_identity(*, provider: str, model: str, sampling: Mapping[str, Any],
                           reasoning_effort: str | None, max_output_tokens: int,
                           tool_mode: str, api_mode: str, system_prompt_hash: str,
                           prompt_template_hash: str, response_schema: str,
                           retry_policy: Mapping[str, Any]) -> dict[str, Any]:
    if not provider or not model or max_output_tokens <= 0:
        raise ValueError("bounded model runtime identity required")
    if set(retry_policy) - {"transport_retries", "candidate_attempts", "backoff"}:
        raise ValueError("unknown retry policy field")
    return sealed(MODEL_RUNTIME_SCHEMA, provider=provider, model=model,
                  provider_attested_weights=False, sampling=dict(sampling),
                  reasoning_effort=reasoning_effort, max_output_tokens=max_output_tokens,
                  tool_mode=tool_mode, api_mode=api_mode,
                  system_prompt_hash=system_prompt_hash,
                  prompt_template_hash=prompt_template_hash,
                  response_schema=response_schema, retry_policy=dict(retry_policy))


def semantic_holdout_identity(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Hash evaluator semantics while excluding display labels and step ids."""
    steps = []
    for step in contract.get("steps") or []:
        steps.append({key: value for key, value in step.items()
                      if key not in {"id", "title", "label", "display_name", "description"}})
    semantic = {"targets": sorted(contract.get("targets") or []), "steps": steps}
    return sealed(HOLDOUT_SEMANTIC_SCHEMA, semantic=semantic,
                  raw_semantic_hash=_sha(semantic), cosmetic_metadata_excluded=True)


def task_identity(*, task_family: str, source_baseline: str, mutation_scope: Sequence[str],
                  objective: str, diagnosis_contract: str, evaluation_family: str,
                  inclusion_criteria: Sequence[str], source: str,
                  exposed_to_tuning: bool) -> dict[str, Any]:
    return sealed(TASK_SCHEMA, task_family=task_family, source_baseline=source_baseline,
                  mutation_scope=sorted(mutation_scope), objective=objective,
                  diagnosis_contract=diagnosis_contract, evaluation_family=evaluation_family,
                  inclusion_criteria=list(inclusion_criteria), source=source,
                  exposed_to_tuning=bool(exposed_to_tuning))


def analysis_plan(*, primary_endpoint: str, secondary_endpoints: Sequence[str],
                  estimator: str, exclusion_criteria: Sequence[str], missing_data_rule: str,
                  multiplicity_rule: str, minimum_sample_target: int,
                  pilot_separate: bool = True) -> dict[str, Any]:
    if minimum_sample_target <= 0 or not primary_endpoint:
        raise ValueError("analysis plan and sample size must be frozen")
    return sealed(ANALYSIS_PLAN_SCHEMA, primary_endpoint=primary_endpoint,
                  secondary_endpoints=list(secondary_endpoints), estimator=estimator,
                  exclusion_criteria=list(exclusion_criteria), missing_data_rule=missing_data_rule,
                  multiplicity_rule=multiplicity_rule, minimum_sample_target=minimum_sample_target,
                  pilot_separate=pilot_separate, confirmatory_data_excludes_pilot=True)


def common_baseline(*, source_revision: str, task_hash: str, utility_family_hash: str,
                    evaluator_identity: Mapping[str, Any], authority_state_hash: str,
                    model_runtime_hash: str, neutral_context_hash: str) -> dict[str, Any]:
    return sealed(COMMON_BASELINE_SCHEMA, source_revision=source_revision, task_hash=task_hash,
                  utility_family_hash=utility_family_hash,
                  evaluator_identity=dict(evaluator_identity),
                  authority_state_hash=authority_state_hash,
                  model_runtime_hash=model_runtime_hash,
                  neutral_context_hash=neutral_context_hash)


def arm_isolation(*, namespaces: Mapping[str, str], worktrees: Mapping[str, str],
                  common_baseline_hash: str) -> dict[str, Any]:
    if set(namespaces) != {"A", "B", "C"} or set(worktrees) != {"A", "B", "C"}:
        raise ValueError("A/B/C isolation surfaces required")
    if len(set(namespaces.values())) != 3 or len(set(worktrees.values())) != 3:
        raise ValueError("mutable arm surfaces must be disjoint")
    return sealed(ARM_ISOLATION_SCHEMA, namespaces=dict(namespaces), worktrees=dict(worktrees),
                  common_baseline_hash=common_baseline_hash,
                  mutable_state_intersection=[], arm_outputs_shared=False)


def randomization_plan(*, task_hashes: Sequence[str], arms: Sequence[str], algorithm: str,
                       seed_commitment: str, assignment_order: Sequence[Mapping[str, str]],
                       execution_contract_hash: str) -> dict[str, Any]:
    if set(arms) != {"A", "B", "C"} or not seed_commitment or not task_hashes:
        raise ValueError("complete A/B/C randomization required")
    if {row.get("task_hash") for row in assignment_order} - set(task_hashes):
        raise ValueError("assignment references unknown task")
    return sealed(RANDOMIZATION_SCHEMA, task_hashes=list(task_hashes), arms=list(arms),
                  algorithm=algorithm, seed_commitment=seed_commitment,
                  assignment_order=[dict(row) for row in assignment_order],
                  execution_contract_hash=execution_contract_hash,
                  frozen_before_first_provider_call=True, provider_calls_at_freeze=0)


def execution_contract(*, source_revision: str, task_set_hash: str, utility_family_hash: str,
                       model_runtime_hash: str, candidate_budget: int, provider_call_budget: int,
                       token_budget: int, wall_clock_budget_seconds: int,
                       tool_surface: Sequence[str], capabilities: Mapping[str, Any],
                       mutation_scope: Sequence[str], authority_state_hash: str,
                       evaluator_identities: Mapping[str, Any], stopping_rule: str,
                       failure_attribution_policy: str, treatment_definitions: Mapping[str, Any],
                       sham_tolerances: Mapping[str, int], randomization_scheme: str,
                       analysis_plan_hash: str, claim_ceiling: str) -> dict[str, Any]:
    budgets = (candidate_budget, provider_call_budget, token_budget, wall_clock_budget_seconds)
    if any(value <= 0 for value in budgets):
        raise ValueError("positive execution budgets required")
    return sealed(EXECUTION_CONTRACT_SCHEMA, source_revision=source_revision,
                  task_set_hash=task_set_hash, utility_family_hash=utility_family_hash,
                  model_runtime_hash=model_runtime_hash, candidate_budget=candidate_budget,
                  provider_call_budget=provider_call_budget, token_budget=token_budget,
                  wall_clock_budget_seconds=wall_clock_budget_seconds,
                  tool_surface=list(tool_surface), capabilities=dict(capabilities),
                  mutation_scope=sorted(mutation_scope), authority_state_hash=authority_state_hash,
                  evaluator_identities=dict(evaluator_identities), stopping_rule=stopping_rule,
                  failure_attribution_policy=failure_attribution_policy,
                  treatment_definitions=dict(treatment_definitions),
                  sham_tolerances=dict(sham_tolerances), randomization_scheme=randomization_scheme,
                  analysis_plan_hash=analysis_plan_hash, primary_endpoint="eta",
                  secondary_endpoints=["eta_call", "eta_cost"], claim_ceiling=claim_ceiling,
                  execution_preregistration_status="EXECUTION_FROZEN",
                  live_execution_authorized=False)


def history_shape(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    encoded = [canonical_bytes(item) for item in items]
    return {"count": len(items), "bytes": sum(map(len, encoded)),
            "token_estimate": sum((len(item) + 3) // 4 for item in encoded),
            "evidence_types": dict(Counter(str(item.get("evidence_type")) for item in items)),
            "schemas": dict(Counter(str(item.get("schema_version")) for item in items)),
            "positive": sum(item.get("channel") == "H+" for item in items),
            "constraints": sum(item.get("channel") == "H-" for item in items)}


def sham_match(applicable: Sequence[Mapping[str, Any]], sham: Sequence[Mapping[str, Any]],
               tolerances: Mapping[str, int]) -> dict[str, Any]:
    c_shape, b_shape = history_shape(applicable), history_shape(sham)
    diffs = {key: abs(int(c_shape[key]) - int(b_shape[key]))
             for key in ("count", "bytes", "token_estimate", "positive", "constraints")}
    all_inapplicable = all(item.get("applicability_disposition") == "INAPPLICABLE" for item in sham)
    all_applicable = all(item.get("applicability_disposition") == "APPLICABLE" for item in applicable)
    within = all(diffs[key] <= int(tolerances.get(key, 0)) for key in diffs)
    return sealed(SHAM_MATCH_SCHEMA, c_history_hashes=[i.get("object_hash") for i in applicable],
                  b_history_hashes=[i.get("object_hash") for i in sham],
                  c_shape=c_shape, b_shape=b_shape, differences=diffs,
                  tolerances=dict(tolerances), ordering_policy="canonical_receipt_hash",
                  all_b_inapplicable=all_inapplicable, all_c_applicable=all_applicable,
                  disposition="PASS" if within and all_inapplicable and all_applicable else "HELD")


def candidate_context(*, experiment_receipt: str, treatment_receipt: str,
                      execution_contract_receipt: str, source_revision: str,
                      utility_family_hash: str, context: Mapping[str, Any],
                      capability_manifest: Mapping[str, Any]) -> dict[str, Any]:
    exact = json.loads(json.dumps(context, sort_keys=True))
    raw = canonical_bytes(exact)
    return sealed(CANDIDATE_CONTEXT_SCHEMA, experiment_receipt=experiment_receipt,
                  treatment_receipt=treatment_receipt,
                  execution_contract_receipt=execution_contract_receipt,
                  source_revision=source_revision, utility_family_hash=utility_family_hash,
                  context_schema="cortex-gsi-candidate-input/1.0", canonical_context=exact,
                  serialized_byte_length=len(raw), token_estimate=(len(raw) + 3) // 4,
                  capability_manifest=dict(capability_manifest), context_hash=_sha(exact),
                  holdout_content_included=False)


def context_difference(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    ca, cb = a.get("canonical_context") or {}, b.get("canonical_context") or {}
    keys = sorted(set(ca) | set(cb))
    changed = [key for key in keys if ca.get(key) != cb.get(key)]
    unexpected = [key for key in changed if key not in {"applicable_constraints", "verified_improvement_evidence"}]
    return sealed(CONTEXT_DIFFERENCE_SCHEMA, left_context_hash=a.get("context_hash"),
                  right_context_hash=b.get("context_hash"), changed_fields=changed,
                  unexpected_differences=unexpected,
                  disposition="PASS" if not unexpected else "HELD")


def contamination_report(checks: Mapping[str, bool | None]) -> dict[str, Any]:
    classes = [name for name, value in checks.items() if value is False]
    unknown = [name for name, value in checks.items() if value is None]
    state = "PASS" if not classes and not unknown else ("HELD" if unknown else "FAIL")
    return sealed(CONTAMINATION_SCHEMA, checks=dict(checks), contamination_classes=classes,
                  unknown_contamination=unknown, disposition=state)


def execution_readiness(*, components: Mapping[str, Mapping[str, Any]],
                        implementation_ci: str, protocol_status: str,
                        provider_calls: int, live_authorized: bool) -> dict[str, Any]:
    required = ("execution_contract", "task_set", "model_runtime", "randomization",
                "analysis_plan", "common_baseline", "treatments", "sham_match")
    missing = [key for key in required if key not in components]
    invalid = [key for key in required if key in components and not valid(components[key])]
    checks = {"implementation_ci_known": implementation_ci in {"PASS", "FAIL"},
              "implementation_ci_pass": implementation_ci == "PASS",
              "protocol_frozen": protocol_status == "PROTOCOL_FROZEN",
              "components_complete": not missing, "components_valid": not invalid,
              "no_provider_calls": provider_calls == 0}
    hard_fail = bool(invalid or implementation_ci == "FAIL"
                     or protocol_status != "PROTOCOL_FROZEN" or provider_calls != 0)
    state = "READY" if all(checks.values()) else ("FAIL" if hard_fail else "HELD")
    return sealed(READINESS_SCHEMA, checks=checks, missing=missing, invalid=invalid,
                  empirical_readiness=state, live_execution_authorized=bool(live_authorized),
                  technical_readiness_distinct_from_authorization=True)


def execution_lock(*, protocol_hash: str, component_hashes: Mapping[str, str],
                   readiness: Mapping[str, Any]) -> dict[str, Any]:
    if readiness.get("empirical_readiness") != "READY" or not valid(readiness, READINESS_SCHEMA):
        raise ValueError("execution readiness not READY")
    required = {"execution_contract", "task_set", "utility_family", "model_runtime",
                "randomization", "analysis_plan", "common_baseline", "treatments", "sham_matches"}
    if set(component_hashes) != required or any(not value for value in component_hashes.values()):
        raise ValueError("execution lock component set incomplete")
    return sealed(EXECUTION_LOCK_SCHEMA, protocol_preregistration_hash=protocol_hash,
                  component_hashes=dict(component_hashes), readiness_hash=readiness["object_hash"],
                  locked_before_provider_call=True, provider_calls_at_lock=0,
                  live_execution_authorized=False)
