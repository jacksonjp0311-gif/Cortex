"""GSI-II.1 loop closure; no production activation and no provider calls.

Composes signed autonomy policy, Store receipts, TransductionPolicy, bounded
capture, independent attestation, and existing canary/apply/rollback primitives.
Source-improvement v1 and tournament promotion remain reconstructable.
"""
from __future__ import annotations

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
    verify_autonomy_policy,
)
from .coding_workspace import (
    _file_hash, _git, _sha, _verify_contract, apply_approved_patch,
    create_patch_proposal, repository_head, rollback_applied_patch,
    run_host_verification_step, verification_environment,
    verify_patch_in_isolated_worktree,
)
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
        if generation.get("status") not in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}:
            errors.append("generation_not_feasible")
        if (generation.get("delta_holdout") is None
                or float(generation["delta_holdout"]) < -float(generation.get("holdout_degradation_tolerance") or 0)):
            errors.append("holdout_regression")
        if index and _gen_index(generation.get("parent_generation") or "") != _gen_index(generations[index - 1].get("candidate_generation") or ""):
            errors.append("lineage_break")
        if index and _gen_index(generation.get("candidate_generation") or "") != (_gen_index(generation.get("parent_generation") or "") or -1) + 1:
            errors.append("nonadjacent_generation")
    mechanics = not errors
    return _sealed("cortex-cumulative-improvement-disposition/1.0", errors=errors,
                   cumulative_generation_mechanics_verified=mechanics,
                   cumulative_self_improvement_established=False,
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
                      primary_metric=primary_metric, epsilon=epsilon_dev, epsilon_dev=epsilon_dev,
                      epsilon_holdout=epsilon_holdout, holdout_degradation_tolerance=float(holdout_degradation_tolerance),
                      holdout_id=holdout_id, policy_receipt_hash=self.policy_receipt_hash,
                      policy_hash=self._policy()["policy_hash"],
                      candidate_budget=1, call_budget=0, model_provider="deterministic-host-callback",
                      stopping_rule="one_candidate_one_use", tournament_rule="feasible_then_primary",
                      canary_rule="existing_authenticated_promotion_only", rollback_rule="existing_policy_rollback",
                      holdout_used_for_generation=False, full_os_isolation="UNKNOWN",
                      control_surface=worktree_payload_hashes(self.root))
        return self._record("gsi_experiment", obj)

    def run(self, experiment_receipt: str, generate: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> dict[str, Any]:
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
        present = self._constraint_records(exp)
        consumed = [item for item in present if item["persistence"] == "APPLY"]
        improvements = self._applicable_improvements(exp)
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
            "applicable_constraints": consumed,
            "verified_improvement_evidence": improvements,
        }
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
            self._record("gsi_generated_candidate", _sealed("cortex-gsi-candidate/1.0",
                         experiment_hash=exp["object_hash"], payload=payload), session=session)
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
        constitution = {name: "UNKNOWN" for name in CONSTITUTIONAL_CHECKS}
        if len(arms) == 2:
            dev, hold = arms["development"], arms["holdout"]
            representation = all(a["receipt"].get("failure_attribution") != "REPRESENTATION_UNSUPPORTED" for a in arms.values())
            env_ok = all(((a["receipt"].get("environment_identity") or {}).get("environment_hash")
                          == (exp["environment"] or {}).get("environment_hash")) for a in arms.values())
            workload = (dev["metrics"]["correctness"] and hold["metrics"]["correctness"]
                        and dev["metrics"]["measurement_complete"] and hold["metrics"]["measurement_complete"])
            constitution.update({
                "INV-IMPROVEMENT-EVIDENCE-REQUIRED": "PASS",
                "INV-EVALUATOR-INDEPENDENCE": "PASS" if evaluator_mutation == 0 else "FAIL",
                "INV-EXPERIMENT-PRECEDENCE": "PASS",
                "INV-NONCOMPENSATORY-IMPROVEMENT": "PASS",
                "INV-HOLDOUT-NONLEAKAGE": "PASS",
                "INV-FAILURE-SCOPE": "PASS",
                "INV-GENERATION-NONSELFAUTHORIZATION": "PASS",
                "INV-CUMULATIVE-CLAIM-BOUNDARY": "PASS",
                "authority_invariance": "PASS",
                "protected_surface_integrity": "PASS",
            })
            verdict = constitutional_verdict(constitution)
            gates.update({
                "source": "PASS" if repository_head(self.root) == exp["baseline_head"] else "FAIL",
                "transduction": "PASS" if all(a["receipt"]["typed_outcome"] == "PASS" for a in arms.values()) else "FAIL",
                "attestation": combine_attestation_gates(
                    [a["inspection"]["gate"] if a["inspection"]["valid"] else "FAIL" for a in arms.values()]),
                "workload_correctness": "PASS" if workload else "FAIL",
                "constitutional_invariants": verdict["status"] if verdict["status"] != "UNKNOWN" else "FAIL",
                "regression": "FAIL" if ((baseline["development"]["metrics"]["correctness"] and not dev["metrics"]["correctness"])
                                         or (baseline["holdout"]["metrics"]["correctness"] and not hold["metrics"]["correctness"])) else "PASS",
                "environment": "PASS" if env_ok else "FAIL",
                "evaluator_integrity": "PASS" if all(b["sound"] for b in baseline.values()) else "FAIL",
                "policy_scope": "PASS",
            })
            if not representation:
                gates["transduction"] = "FAIL"
        elif errors:
            constitution["INV-EVALUATOR-INDEPENDENCE"] = "FAIL" if evaluator_mutation else "PASS"
            constitution["INV-NONCOMPENSATORY-IMPROVEMENT"] = "PASS"
            constitution["INV-HOLDOUT-NONLEAKAGE"] = "PASS"
            constitution["authority_invariance"] = "PASS"
            constitution["protected_surface_integrity"] = "FAIL" if any("protected" in item for item in errors) else "PASS"
            if policy_mutation:
                constitution["INV-EVALUATOR-INDEPENDENCE"] = "FAIL"
            verdict = constitutional_verdict(constitution)
            gates["constitutional_invariants"] = verdict["status"] if verdict["status"] != "UNKNOWN" else "FAIL"
            gates["policy_scope"] = "FAIL" if policy_mutation or any("protected" in item for item in errors) else gates["policy_scope"]
        comparison = improvement_disposition(
            baseline["development"]["metrics"], (arms.get("development") or {}).get("metrics") or {},
            metric=exp["primary_metric"], epsilon_dev=float(exp.get("epsilon_dev") or exp.get("epsilon") or 1),
            epsilon_holdout=float(exp.get("epsilon_holdout") or exp.get("epsilon") or 1),
            holdout_degradation_tolerance=float(exp.get("holdout_degradation_tolerance") or 0),
            gates=gates, before_holdout=baseline["holdout"]["metrics"],
            after_holdout=(arms.get("holdout") or {}).get("metrics") or {},
        )
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
                      constitutional=constitutional_verdict(constitution),
                      evaluator_mutation=evaluator_mutation, policy_mutation=policy_mutation,
                      assurance_debt=typed_assurance_debt({"source": gates["source"],
                          "transduction": gates["transduction"], "instrument": gates["attestation"],
                          "environment": gates["environment"], "experiment": "PASS",
                          "causal": "UNKNOWN", "applicability": "UNKNOWN", "replication": "NOT_TESTED"}),
                      claim_ceiling="DETERMINISTIC_CONTROLS_ONLY", promotion_count=0,
                      authority_leakage=0, cumulative_improvement_established=False,
                      cumulative_self_improvement_established=False,
                      cumulative_generation_mechanics_verified=False)
        return self._record("gsi_trial", obj, session=session)

    def recycle(self, trial_receipt: str) -> dict[str, Any]:
        trial = self._resolve(trial_receipt, "gsi_trial")["object"]
        exp = self._resolve(trial["experiment_receipt"], "gsi_experiment")["object"]
        success = trial["comparison"]["feasible"] and trial["status"] in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}
        schema = VERIFIED_SCHEMA if success else CONSTRAINT_SCHEMA
        payload = trial.get("candidate_payload") or {}
        predicates = []
        for edit in payload.get("edits") or []:
            predicates.append({"kind": "exact_edit", "path": edit.get("path"), "old": edit.get("old"), "new": edit.get("new")})
            if "\r" in str(edit.get("old", "")) + str(edit.get("new", "")):
                predicates.append({"kind": "representation_crlf"})
        applicability = {
            "originating_source_head": exp["baseline_head"],
            "subject_component": exp.get("subject_component"),
            "subject_component_identity": exp["subject_identity"],
            "relevant_dependency_closure": exp["subject_identity"],
            "environment": exp["environment"],
            "environment_identity": exp["environment"],
            "instrument_identity": exp.get("instrument_identity"),
            "representation_identity": exp.get("representation_identity"),
            "failure_class": (trial.get("errors") or [None])[0],
            "scope": exp["allowed_targets"],
        }
        obj = _sealed(schema, originating_experiment=trial["experiment_receipt"],
                      failure_receipt=None if success else trial_receipt,
                      trial_receipt=trial_receipt, trial_hash=trial["object_hash"],
                      applicability=applicability, scope=exp["allowed_targets"],
                      predicates=predicates,
                      status="VERIFIED_WITHIN_CONTROL" if success else "HELD_CONSTRAINT",
                      before_metrics=trial["baseline"]["development"]["metrics"],
                      after_metrics=(trial["candidates"].get("development") or {}).get("metrics"),
                      before_holdout_metrics=trial["baseline"]["holdout"]["metrics"],
                      after_holdout_metrics=(trial["candidates"].get("holdout") or {}).get("metrics"),
                      measured_effect=trial["comparison"].get("delta_dev"),
                      failure_classes=trial["errors"] + [a["receipt"]["failure_attribution"] for a in trial["candidates"].values() if a["receipt"]["failure_attribution"] != "OBSERVED_CANDIDATE_PASS"],
                      counterevidence=[], superseded_by=[], historical_evidence_only=True,
                      claim_ceiling="DETERMINISTIC_CONTROLS_ONLY", admission_required=True)
        return self._record("gsi_verified_improvement" if success else "gsi_constraint", obj)

    def _constraint_records(self, exp: Mapping[str, Any]) -> list[dict[str, Any]]:
        records = []
        subject = {p: _file_hash(self.root / p) for p in exp["allowed_targets"]}
        for record in self.store.symbiotic_receipts_by_kind(self.repo, "gsi_constraint"):
            obj = record.get("object") or {}
            persistence = self.constraint_persistence(obj, environment=exp["environment"],
                                                      targets=exp["allowed_targets"], subject_identity=subject,
                                                      instrument_identity=exp.get("instrument_identity") or {})
            records.append({
                "constraint_hash": obj.get("object_hash"), "status": obj.get("status"),
                "failure_classes": obj.get("failure_classes") or [], "scope": obj.get("scope") or [],
                "predicates": obj.get("predicates") or [], "persistence": persistence,
                "applicability": obj.get("applicability") or {},
            })
        return records

    def _applicable_improvements(self, exp: Mapping[str, Any]) -> list[dict[str, Any]]:
        consumed = []
        for record in self.store.symbiotic_receipts_by_kind(self.repo, "gsi_verified_improvement"):
            obj = record.get("object") or {}
            if obj.get("schema_version") != VERIFIED_SCHEMA or not _valid(obj):
                continue
            apply = obj.get("applicability") or {}
            env = apply.get("environment") or apply.get("environment_identity") or {}
            if env.get("os_family") != (exp.get("environment") or {}).get("os_family"):
                continue
            if not set(obj.get("scope") or []) & set(exp["allowed_targets"]):
                continue
            consumed.append({
                "improvement_hash": obj.get("object_hash"),
                "measured_effect": obj.get("measured_effect"),
                "scope": obj.get("scope"), "status": obj.get("status"),
                "historical_evidence_only": True, "active_guidance": False,
                "authority_effect": False, "admission_required": True,
            })
        return consumed

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
        identity = apply.get("subject_component_identity") or apply.get("relevant_dependency_closure") or {}
        overlapping = {path: digest for path, digest in identity.items() if path in subject_identity}
        identity_ok = bool(overlapping) and overlapping == {path: subject_identity[path] for path in overlapping}
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
        """Compose existing canary/apply/rollback. Does not replace tournament promotion."""
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
        payload = trial.get("candidate_payload")
        if not payload:
            errors.append("candidate_payload_missing")
        if errors:
            raise PermissionError("promotion held: " + ",".join(errors))
        patch = "".join(
            f"diff --git a/{edit['path']} b/{edit['path']}\n--- a/{edit['path']}\n+++ b/{edit['path']}\n@@ -1 +1 @@\n-{edit['old']}\n+{edit['new']}\n"
            for edit in payload["edits"]
        )
        proposal = create_patch_proposal(self.root, patch, str(payload.get("summary") or "gsi promote"))
        scope_errors = _policy_scope_errors(policy, proposal)
        if scope_errors:
            raise PermissionError("promotion held: " + ",".join(scope_errors))
        canary_contract = dict(exp["contracts"]["development"])
        canary_contract["steps"] = json.loads(json.dumps(list(policy.get("canary_steps") or ())))
        canary_contract["contract_hash"] = _sha({k: v for k, v in canary_contract.items() if k != "contract_hash"})
        before_head = repository_head(self.root)
        canary = verify_patch_in_isolated_worktree(self.root, proposal, canary_contract)
        rolled_back = canary.get("status") != "verified"
        application = None
        remeasurement = None
        if not rolled_back:
            application = apply_approved_patch(self.root, proposal)
            remeasurement = self.remeasure(trial["experiment_receipt"])
            if not remeasurement["workload_correctness"]:
                rollback_applied_patch(self.root, proposal)
                rolled_back = True
            else:
                _git(self.root, ["add", "-A"])
                _git(self.root, ["commit", "-qm", "gsi-promoted"])
        status = "rolled_back_remeasurement_failed" if rolled_back else "promoted_remeasured"
        obj = _sealed(PROMOTION_SCHEMA, trial_receipt=trial_receipt, experiment_receipt=trial["experiment_receipt"],
                      proposal_hash=proposal["proposal_hash"], application=application, canary=canary,
                      remeasurement=remeasurement, rolled_back=rolled_back, status=status,
                      source_revision_before=before_head, source_revision_after=repository_head(self.root),
                      host_policy_authorized=True, tournament_promotion=False)
        return self._record("gsi_promotion", obj)

    def record_generation(self, *, parent: str, trial_receipt: str, candidate_generation: str,
                          parent_receipt: str | None = None, promotion_receipt: str | None = None) -> dict[str, Any]:
        trial = self._resolve(trial_receipt, "gsi_trial")["object"]
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
        if promotion_receipt:
            promotion = self._resolve(promotion_receipt, "gsi_promotion")["object"]
        delta_dev = trial["comparison"].get("delta_dev")
        parent_cumulative = parent_obj.get("cumulative_delta_from_G0") if parent_obj else 0.0
        cumulative = None if delta_dev is None or parent_cumulative is None else float(parent_cumulative) + float(delta_dev)
        status = "HELD" if errors else trial["status"]
        obj = _sealed(GENERATION_SCHEMA, generation_id=candidate_generation, parent_generation=parent,
                      candidate_generation=candidate_generation, verifier_generation=parent,
                      trial_receipt=trial_receipt, promotion_receipt=promotion_receipt,
                      source_revision_before=(promotion or {}).get("source_revision_before") or trial.get("experiment_hash"),
                      source_revision_after=(promotion or {}).get("source_revision_after"),
                      before_dev_metrics=trial["baseline"]["development"]["metrics"],
                      after_dev_metrics=(trial["candidates"].get("development") or {}).get("metrics"),
                      before_holdout_metrics=trial["baseline"]["holdout"]["metrics"],
                      after_holdout_metrics=(trial["candidates"].get("holdout") or {}).get("metrics"),
                      delta_dev=delta_dev, delta_holdout=trial["comparison"].get("delta_holdout"),
                      holdout_degradation_tolerance=trial["comparison"].get("holdout_degradation_tolerance", 0),
                      cumulative_delta_from_G0=cumulative,
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
                      cumulative_generation_mechanics_verified=False,
                      status=status, errors=errors)
        return self._record("gsi_generation", obj)
