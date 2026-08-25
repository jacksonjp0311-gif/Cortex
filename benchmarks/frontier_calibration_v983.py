"""Run the v9.8.3 center-out calibration through canonical Cortex circulation."""

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

from cortex.adapter_provenance import register_adapter_provenance
from cortex.adapters.json_subprocess import JsonSubprocessAdapter
from cortex.calibration_commissioning import commission_calibration_panel, resolve_calibration_observation
from cortex.config import cortex_home
from cortex.discriminative_forge import TASK_FAMILIES, build_difficulty_ladder_corpus
from cortex.evaluation import TaskEvaluationContract
from cortex.model_circulation import run_model_circulation
from cortex.store import Store
from cortex.symbiosis import open_symbiotic_session
from cortex.will import register_will_principal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--provider-family", required=True)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--output", type=Path, default=ROOT / "benchmarks" / "results" / "v983_frontier_calibration.json")
    args = parser.parse_args()
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
    )
    corpus = build_difficulty_ladder_corpus(
        seed="cortex-v983-frontier-development", maximum_level=4, variants_per_level=8
    )
    cases = {(row["family"], int(row["difficulty_level"]), int(row["variant"])): row for row in corpus["cases"]}
    home = cortex_home()
    store = Store(home / "cortex.db")
    principal_id = f"v983-calibration-{int(time.time())}"
    principal_secret = secrets.token_urlsafe(32)
    register_will_principal(store, args.repo, principal_id, "v9.8.3 Calibration Operator", secret=principal_secret)
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

    def execute(case):
        nonlocal calls
        contract = TaskEvaluationContract(
            contract_id=f"v983-{case['case_id']}", task_type="field_equals",
            target_field="text", expected_value=case["expected_public_output"],
            evaluator_id="cortex.v983.exact-public-output.v1",
        )
        session = open_symbiotic_session(
            store, args.repo, task=case["prompt"], provider=args.provider_family,
            model_id=args.model, capability_profile={"development_calibration": True},
            tool_scopes=(), persist=True,
        )
        result = run_model_circulation(
            store, args.repo, session, adapter=adapter, task_contract=contract,
            observed_result=None, tool_scopes=(),
            configuration={"task_instruction": case["prompt"], "calibration_case_id": case["case_id"]},
            persist=True,
        )
        observation = resolve_calibration_observation(
            store, args.repo, case, session_id=result["session_id"], turn_id=result["turn_id"]
        )
        observations.append(observation)
        calls += 1
        print(json.dumps({"call": calls, "family": case["family"], "level": case["difficulty_level"], "variant": case["variant"], "success": observation["success"], "state": observation["state"]}), flush=True)

    for family in TASK_FAMILIES:
        level = 2
        visited = set()
        while level not in visited and 1 <= level <= 4:
            visited.add(level)
            for variant in range(4):
                execute(cases[(family, level, variant)])
            family_outcomes = [row["success"] for row in observations if row["family"] == family and int(row["difficulty_level"]) == level]
            successes = sum(bool(value) for value in family_outcomes)
            if successes == 4:
                level += 1
                continue
            if successes == 0:
                level -= 1
                continue
            for variant in range(4, 8):
                execute(cases[(family, level, variant)])
            break

    receipt = commission_calibration_panel(
        corpus=corpus, observations=observations, store=store, repo=args.repo
    )
    report = {
        "schema_version": "cortex-frontier-calibration-commissioning/1.0",
        "version": "9.8.3",
        "corpus_hash": corpus["corpus_hash"],
        "adapter_registration_id": registration["registration_id"],
        "model_selection_source": "runtime_argument",
        "model_identity": {"provider_family": args.provider_family, "model_id": args.model},
        "call_count": calls,
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
