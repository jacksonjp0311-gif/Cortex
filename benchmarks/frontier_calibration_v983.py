"""Run center-out task calibration through canonical Cortex circulation."""

from __future__ import annotations

import argparse
import json
import secrets
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.adapter_provenance import EVIDENCE_LIVE, register_adapter_provenance, resolve_adapter_provenance
from cortex.adapters.json_subprocess import JsonSubprocessAdapter
from cortex.calibration_commissioning import commission_calibration_panel, resolve_calibration_observation
from cortex.config import cortex_home
from cortex.discriminative_forge import (
    COUPLED_FAMILIES,
    LATENT_CAUSE_FAMILIES,
    TASK_FAMILIES,
    build_coupled_dependency_corpus,
    build_difficulty_ladder_corpus,
    build_latent_cause_corpus,
)
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import ModelAdapterError, run_model_circulation
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


def _prior_case_sessions(store: Store, repo: str) -> dict[str, tuple[str, int]]:
    """Find completed canonical calibration invocations for resumable runs."""
    found: dict[str, tuple[str, int]] = {}
    with store.transaction() as conn:
        rows = conn.execute(
            """SELECT session_id, turn_id, receipt_json, created_at
               FROM symbiotic_circulation_receipts
               WHERE repo=? AND kind='model_invocation'
               ORDER BY created_at DESC""",
            (repo,),
        ).fetchall()
    for row in rows:
        try:
            body = json.loads(row["receipt_json"])
            request = body.get("request") if isinstance(body, dict) else None
            configuration = request.get("configuration") if isinstance(request, dict) else None
            case_id = str(configuration.get("calibration_case_id") or "") if isinstance(configuration, dict) else ""
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if case_id and case_id not in found:
            found[case_id] = (str(row["session_id"]), int(row["turn_id"]))
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider-family", required=True)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--timeout-seconds", type=float, default=180.0)
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--corpus-mode", choices=("additive", "coupled", "latent"), default="additive")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results" / "v983_frontier_calibration.json")
    args = parser.parse_args()
    phase_id, phase_version = {
        "additive": ("v983", "9.8.3"),
        "coupled": ("v984", "9.8.4"),
        "latent": ("v985", "9.8.5"),
    }[args.corpus_mode]
    command = shutil.which(args.command) or args.command
    adapter = JsonSubprocessAdapter(
        command=command,
        argument_template=(
            "--model", "{model}", "--reasoning-effort", args.reasoning_effort,
            "--no-subagents", "--tools", "", "--disable-web-search",
            "--output-format", "json", "--json-schema", "{schema}", "--single", "{prompt}",
        ),
        provider_family=args.provider_family,
        model_id=args.model,
        cwd=ROOT,
        timeout_seconds=args.timeout_seconds,
        run_profile=args.corpus_mode,
    )
    if args.corpus_mode == "latent":
        corpus = build_latent_cause_corpus(
            seed="cortex-v985-latent-development", maximum_level=4, variants_per_level=8
        )
        task_families = LATENT_CAUSE_FAMILIES
        report_version = phase_version
    elif args.corpus_mode == "coupled":
        corpus = build_coupled_dependency_corpus(
            seed="cortex-v984-coupled-development", maximum_level=4, variants_per_level=8
        )
        task_families = COUPLED_FAMILIES
        report_version = phase_version
    else:
        corpus = build_difficulty_ladder_corpus(
            seed="cortex-v983-frontier-development", maximum_level=4, variants_per_level=8
        )
        task_families = TASK_FAMILIES
        report_version = phase_version
    cases = {(row["family"], int(row["difficulty_level"]), int(row["variant"])): row for row in corpus["cases"]}
    home = cortex_home()
    store = Store(home / "cortex.db")
    registration = resolve_adapter_provenance(store, args.repo, adapter)
    if registration.get("evidence_class") != EVIDENCE_LIVE:
        principal_id = f"{phase_id}-calibration-{int(time.time())}"
        principal_secret = secrets.token_urlsafe(32)
        register_will_principal(
            store, args.repo, principal_id, f"v{phase_version} Calibration Operator", secret=principal_secret
        )
        registration = register_adapter_provenance(
            store, args.repo, adapter,
            boundary_kind="local_subprocess_model",
            principal_id=principal_id,
            principal_secret=principal_secret,
            endpoint_descriptor={"transport": "host-selected-json-cli", "network_managed_by": "external_cli"},
            model_family="runtime_selected_frontier",
            capability_class="frontier_general_reasoning",
        )
        principal_secret = ""
    observations = []
    calls = 0
    reused_observations = 0
    execution_failures = []
    prior_sessions = _prior_case_sessions(store, args.repo)

    def execute(case):
        nonlocal calls, reused_observations
        prior = prior_sessions.get(str(case["case_id"]))
        if prior is not None:
            prior_observation = resolve_calibration_observation(
                store, args.repo, case, session_id=prior[0], turn_id=prior[1]
            )
            if prior_observation.get("state") == "observed":
                observations.append(prior_observation)
                reused_observations += 1
                print(json.dumps({
                    "call": calls, "family": case["family"], "level": case["difficulty_level"],
                    "variant": case["variant"], "success": prior_observation["success"],
                    "state": "reused_canonical_observation",
                }), flush=True)
                return bool(prior_observation["success"])
        contract = TaskEvaluationContract(
            contract_id=f"{phase_id}-{case['case_id']}", task_type="field_equals",
            target_field="text", expected_value=case["expected_public_output"],
            evaluator_id=f"cortex.{phase_id}.exact-public-output.v1",
        )
        session = open_symbiotic_session(
            store, args.repo, task=case["prompt"], provider=args.provider_family,
            model_id=args.model, capability_profile={"development_calibration": True},
            tool_scopes=(), persist=True,
        )
        try:
            result = run_model_circulation(
                store, args.repo, session, adapter=adapter, task_contract=contract,
                observed_result=None, tool_scopes=(),
                configuration={"task_instruction": case["prompt"], "calibration_case_id": case["case_id"]},
                persist=True,
            )
        except ModelAdapterError as exc:
            calls += 1
            failure = {
                "case_id": case["case_id"], "family": case["family"],
                "difficulty_level": case["difficulty_level"], "variant": case["variant"],
                "state": "bounded_invocation_failed", "error_class": type(exc.__cause__).__name__ if exc.__cause__ else type(exc).__name__,
                "timeout_seconds": args.timeout_seconds, "canonical_outcome_present": False,
                "counted_as_success": False, "confirmatory_eligible": False,
                "authority": {"host_mutate_authorized": False, "execution_authorized": False, "memory_admission_authorized": False, "policy_effect": False},
            }
            execution_failures.append(failure)
            print(json.dumps({"call": calls, **failure}), flush=True)
            return False
        observation = resolve_calibration_observation(
            store, args.repo, case, session_id=result["session_id"], turn_id=result["turn_id"]
        )
        observations.append(observation)
        calls += 1
        print(json.dumps({"call": calls, "family": case["family"], "level": case["difficulty_level"], "variant": case["variant"], "success": observation["success"], "state": observation["state"]}), flush=True)
        return bool(observation["success"])

    for family in task_families:
        level = 2
        visited = set()
        while level not in visited and 1 <= level <= 4:
            visited.add(level)
            family_outcomes = [execute(cases[(family, level, variant)]) for variant in range(4)]
            successes = sum(bool(value) for value in family_outcomes)
            if successes == 4:
                level += 1
                continue
            if successes == 0:
                level -= 1
                continue
            for variant in range(4, 8):
                family_outcomes.append(execute(cases[(family, level, variant)]))
            break

    receipt = commission_calibration_panel(
        corpus=corpus, observations=observations, store=store, repo=args.repo
    )
    report = {
        "schema_version": "cortex-frontier-calibration-commissioning/1.0",
        "version": report_version,
        "corpus_mode": args.corpus_mode,
        "corpus_hash": corpus["corpus_hash"],
        "adapter_registration_id": registration["registration_id"],
        "model_selection_source": "runtime_argument",
        "model_identity": {"provider_family": args.provider_family, "model_id": args.model},
        "call_count": calls,
        "reused_observation_count": reused_observations,
        "execution_failures": execution_failures,
        "execution_failure_count": len(execution_failures),
        "timeout_seconds": args.timeout_seconds,
        "commissioning": receipt,
        "observations": observations,
        "hidden_reasoning_persisted": False,
        "raw_provider_envelope_persisted": False,
        "confirmatory_eligible": False,
        "authority": {"host_mutate_authorized": False, "execution_authorized": False, "memory_admission_authorized": False, "policy_effect": False},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "calls": calls, "selected": receipt["selected"], "output": str(args.output)}, indent=2))
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
