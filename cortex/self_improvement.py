"""GSI-II prospective measurement composition; no production activation.

The existing autonomy policy and receipt ledger own authority and chronology.
Source-improvement v1 is unchanged. This bounded v2 pilot accepts one candidate
per experiment and zero provider calls; a consumed holdout cannot be retried.
"""
from __future__ import annotations

import json
import math
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
    _file_hash, _git, _sha, _verify_contract, repository_head,
    run_host_verification_step, verification_environment,
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
METRICS = {"task_success": "increase", "duration_ms": "decrease", "output_bytes": "decrease"}
HARD_GATES = (
    "source", "transduction", "attestation", "invariant", "regression",
    "environment", "evaluator_integrity", "policy_scope", "holdout",
)


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
    errors = []
    if attestation["status"] == "INVALID" or (attestation["status"] != "ATTESTED" and attestation.get("invalid")):
        errors.append("ATTESTATION_FAILED")
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
    return {"valid": not errors, "errors": errors, "attestation": attestation}


def _safe_targets(targets: Sequence[str]) -> list[str]:
    result = sorted(set(targets))
    if not result:
        raise ValueError("empty candidate scope")
    for target in result:
        path = PurePosixPath(target)
        if (path.is_absolute() or ".." in path.parts or "\\" in target or ":" in target
                or path.as_posix() != target):
            raise ValueError("noncanonical target")
        if target.lower().startswith(tuple(x.lower() for x in PERMANENTLY_PROTECTED_PREFIXES)):
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


def improvement_disposition(before: Mapping[str, Any], after: Mapping[str, Any], *,
                            metric: str, epsilon: float, gates: Mapping[str, str]) -> dict[str, Any]:
    if metric not in METRICS or not math.isfinite(epsilon) or epsilon <= 0:
        raise ValueError("invalid frozen metric or epsilon")
    states = {name: gates.get(name, "UNKNOWN") for name in HARD_GATES}
    feasible = all(value == "PASS" for value in states.values())
    delta = None
    if before.get(metric) is not None and after.get(metric) is not None:
        delta = float(after[metric]) - float(before[metric])
        if METRICS[metric] == "decrease":
            delta = -delta
        if not math.isfinite(delta):
            raise ValueError("nonfinite metric")
    regression = before.get("correctness") is True and after.get("correctness") is not True
    if regression:
        states["regression"] = "FAIL"
        status = "REGRESSION_DETECTED"
    elif states.get("regression") == "FAIL":
        status = "REGRESSION_DETECTED"
    elif not feasible or delta is None:
        status = "HELD"
    elif delta >= epsilon:
        status = "REPAIR_MEASURED" if not before.get("correctness") and after.get("correctness") else "IMPROVED_WITHIN_DECLARED_WORKLOAD"
    else:
        status = "VERIFIED_MAINTENANCE"
    return _sealed("cortex-improvement-comparison/1.0", status=status,
                   primary_delta=delta, feasible=feasible, gates=states,
                   general_improvement_established=False)


class GovernedImprovement:
    """Host coordinator composing authenticated policy, Store and transduction.

    Holdout confidentiality is a callback-input boundary, not OS sandboxing.
    The host callback is trusted and receives only allowed source and dev results.
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

    def _baseline(self, contract: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
        """Unchanged arm uses the same bounded observation implementation."""
        with tempfile.TemporaryDirectory(prefix="cortex-gsi-baseline-") as temp:
            path = Path(temp) / "baseline"
            if _git(self.root, ["worktree", "add", "--detach", str(path), policy["subject_source_head"]]).returncode:
                raise RuntimeError("baseline worktree creation failed")
            try:
                pre = worktree_payload_hashes(path)
                steps = [run_host_verification_step(path, {
                    **step, "observation_schema": policy["observation_policy"],
                    "max_stdout_bytes": policy["stdout_limit"], "max_stderr_bytes": policy["stderr_limit"],
                    "timeout_seconds": min(step["timeout_seconds"], policy["timeout_seconds"]),
                }) for step in contract["steps"]]
                post = worktree_payload_hashes(path)
            finally:
                if _git(self.root, ["worktree", "remove", "--force", str(path)]).returncode:
                    raise RuntimeError("baseline worktree cleanup failed")
        sound = pre == post and _sound_steps(steps, contract)
        return _sealed("cortex-improvement-baseline/1.0", steps=steps, sound=sound,
                       preimages=pre, postimages=post,
                       metrics=metric_vector(steps, len(contract["steps"])))

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
               primary_metric: str = "task_success") -> dict[str, Any]:
        opportunity = self._resolve(opportunity_receipt, "gsi_opportunity")["object"]
        for observation in opportunity["observation_receipts"]:
            self._resolve(observation, "gsi_diagnosis_observation")
        if (opportunity["disposition"] != "ELIGIBLE" or opportunity["active_defeaters"]
                or opportunity["source_revision"] != repository_head(self.root)):
            raise ValueError("HELD: opportunity missing, stale or defeated")
        targets = self._scope(opportunity["candidate_scope"])
        if primary_metric not in METRICS or epsilon <= 0 or not math.isfinite(epsilon):
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
                      forbidden_targets=list(PERMANENTLY_PROTECTED_PREFIXES),
                      subject_identity=opportunity["subject_component_identity"],
                      contracts={"development": dict(development), "holdout": dict(holdout)},
                      transduction_policies=policies, environment=verification_environment(),
                      primary_metric=primary_metric, epsilon=epsilon, holdout_id=holdout_id,
                      policy_receipt_hash=self.policy_receipt_hash, policy_hash=self._policy()["policy_hash"],
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
        # Atomic ledger identity reserves this experiment before calling cognition.
        session = {"session_id": frozen["session_id"], "body_epoch_id": frozen["body_epoch_id"]}
        reservation = self._record("gsi_candidate_reservation", _sealed("cortex-gsi-reservation/1.0",
                                   experiment_receipt=experiment_receipt), session=session)
        if reservation.get("inserted") is not True:
            raise ValueError("experiment exhausted; no repeated holdout")
        baseline = {label: self._baseline(exp["contracts"][label], exp["transduction_policies"][label])
                    for label in ("development", "holdout")}
        consumed = self._applicable_constraints(exp)
        context = {"source": {p: (self.root / p).read_text(encoding="utf-8") for p in exp["allowed_targets"]},
                   "development_metrics": baseline["development"]["metrics"],
                   "allowed_targets": exp["allowed_targets"], "call_budget": 0,
                   "experiment_hash": exp["object_hash"],
                   "applicable_constraints": consumed}
        arms, errors = {}, []
        try:
            payload = json.loads(json.dumps(generate(json.loads(json.dumps(context)))))
            if (exp["control_surface"] != worktree_payload_hashes(self.root)
                    or repository_head(self.root) != exp["baseline_head"]):
                raise ValueError("candidate modified frozen source or evaluator")
            self._policy()
            if set(payload) - {"schema_version", "summary", "edits"}:
                raise ValueError("candidate cannot alter experiment")
            proposed_targets = [edit["path"] for edit in payload["edits"]]
            self._scope(proposed_targets)
            if set(proposed_targets) != set(exp["allowed_targets"]):
                raise ValueError("candidate scope mismatch")
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
        if len(arms) == 2:
            dev, hold = arms["development"], arms["holdout"]
            representation = all(a["receipt"].get("failure_attribution") != "REPRESENTATION_UNSUPPORTED" for a in arms.values())
            env_ok = all(
                ((a["receipt"].get("environment_identity") or {}).get("environment_hash")
                 == (exp["environment"] or {}).get("environment_hash"))
                for a in arms.values()
            )
            gates.update({
                "source": "PASS" if repository_head(self.root) == exp["baseline_head"] else "FAIL",
                "transduction": "PASS" if all(a["receipt"]["typed_outcome"] == "PASS" for a in arms.values()) else "FAIL",
                "attestation": "PASS" if all(a["inspection"]["valid"] for a in arms.values()) else "FAIL",
                "invariant": "PASS" if all(a["metrics"]["correctness"] for a in arms.values()) else "FAIL",
                "regression": "FAIL" if baseline["development"]["metrics"]["correctness"] and not dev["metrics"]["correctness"] else "PASS",
                "environment": "PASS" if env_ok else "FAIL",
                "evaluator_integrity": "PASS" if all(b["sound"] for b in baseline.values()) else "FAIL",
                "policy_scope": "PASS",
                "holdout": "PASS" if hold["metrics"]["correctness"] else "FAIL",
            })
            if not representation:
                gates["transduction"] = "FAIL"
        before = baseline["development"]["metrics"]
        after = (arms.get("development") or {}).get("metrics") or {}
        comparison = improvement_disposition(before, after, metric=exp["primary_metric"], epsilon=exp["epsilon"], gates=gates)
        obj = _sealed(RESULT_SCHEMA_V2, experiment_receipt=experiment_receipt,
                      experiment_hash=exp["object_hash"], baseline=baseline, candidates=arms,
                      comparison=comparison, errors=errors, status=comparison["status"],
                      holdout_used_for_generation=False, policy_hash=exp["policy_hash"],
                      failure_constraints_consumed=[item["constraint_hash"] for item in consumed],
                      verified_improvements_consumed=[],
                      assurance_debt=typed_assurance_debt({"source": gates["source"],
                          "transduction": gates["transduction"], "instrument": gates["attestation"],
                          "environment": gates["environment"], "experiment": "PASS",
                          "causal": "UNKNOWN", "applicability": "UNKNOWN", "replication": "NOT_TESTED"}),
                      claim_ceiling="DETERMINISTIC_CONTROLS_ONLY", promotion_count=0,
                      authority_leakage=0, cumulative_improvement_established=False)
        return self._record("gsi_trial", obj, session=session)

    def recycle(self, trial_receipt: str) -> dict[str, Any]:
        trial = self._resolve(trial_receipt, "gsi_trial")["object"]
        exp = self._resolve(trial["experiment_receipt"], "gsi_experiment")["object"]
        success = trial["comparison"]["feasible"] and trial["status"] in {"REPAIR_MEASURED", "IMPROVED_WITHIN_DECLARED_WORKLOAD"}
        schema = VERIFIED_SCHEMA if success else CONSTRAINT_SCHEMA
        obj = _sealed(schema, originating_experiment=trial["experiment_receipt"], failure_receipt=None if success else trial_receipt,
                      trial_receipt=trial_receipt, trial_hash=trial["object_hash"],
                      applicability={"source_head": exp["baseline_head"], "environment": exp["environment"]},
                      scope=exp["allowed_targets"], status="VERIFIED_WITHIN_CONTROL" if success else "HELD_CONSTRAINT",
                      before_metrics=trial["baseline"]["development"]["metrics"],
                      after_metrics=(trial["candidates"].get("development") or {}).get("metrics"),
                      measured_effect=trial["comparison"]["primary_delta"],
                      failure_classes=trial["errors"] + [a["receipt"]["failure_attribution"] for a in trial["candidates"].values() if a["receipt"]["failure_attribution"] != "OBSERVED_CANDIDATE_PASS"],
                      counterevidence=[], superseded_by=[], historical_evidence_only=True,
                      claim_ceiling="DETERMINISTIC_CONTROLS_ONLY", admission_required=True)
        return self._record("gsi_verified_improvement" if success else "gsi_constraint", obj)

    def _applicable_constraints(self, exp: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Search-space constraints only. Verified successes stay historical evidence."""
        consumed = []
        for record in self.store.symbiotic_receipts_by_kind(self.repo, "gsi_constraint"):
            obj = record.get("object") or {}
            if not self.constraint_applies(obj, environment=exp["environment"], targets=exp["allowed_targets"]):
                continue
            consumed.append({
                "constraint_hash": obj.get("object_hash"),
                "status": obj.get("status"),
                "failure_classes": obj.get("failure_classes") or [],
                "scope": obj.get("scope") or [],
            })
        return consumed

    def constraint_applies(self, constraint: Mapping[str, Any], *, environment: Mapping[str, Any],
                           targets: Sequence[str]) -> bool:
        if constraint.get("schema_version") != CONSTRAINT_SCHEMA or not _valid(constraint):
            return False
        apply = constraint.get("applicability") or {}
        env = apply.get("environment") or {}
        # Unknown applicability must not generalize.
        if not env.get("os_family") or not environment.get("os_family"):
            return False
        if env.get("os_family") != environment.get("os_family"):
            return False
        scope = set(constraint.get("scope") or [])
        if not scope or not set(targets) & scope:
            return False
        if not apply.get("source_head") or apply.get("source_head") != repository_head(self.root):
            return False
        return True

    def record_generation(self, *, parent: str, trial_receipt: str, candidate_generation: str) -> dict[str, Any]:
        trial = self._resolve(trial_receipt, "gsi_trial")["object"]
        if not parent or not candidate_generation or parent == candidate_generation:
            raise ValueError("candidate generation cannot self-verify")
        policy = self._policy()
        errors = []
        if policy.get("allow_recursive_generation") is not True:
            errors.append("recursive_generation_not_delegated")
        obj = _sealed(GENERATION_SCHEMA, parent_generation=parent, candidate_generation=candidate_generation,
                      verifier_generation=parent, trial_receipt=trial_receipt,
                      before_metrics=trial["baseline"]["development"]["metrics"],
                      after_metrics=(trial["candidates"].get("development") or {}).get("metrics"),
                      delta=trial["comparison"]["primary_delta"],
                      cumulative_delta_from_G0=None,
                      failure_constraints_consumed=list(trial.get("failure_constraints_consumed") or []),
                      verified_improvements_consumed=list(trial.get("verified_improvements_consumed") or []),
                      cumulative_improvement_established=False,
                      status="HELD" if errors else trial["status"], errors=errors)
        return self._record("gsi_generation", obj)
