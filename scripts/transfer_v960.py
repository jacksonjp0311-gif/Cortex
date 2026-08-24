"""Run a strict empirical A-E transfer trial from one v9.6 circulation."""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from pathlib import Path

from cortex.adapter_provenance import (
    EVIDENCE_LIVE,
    register_adapter_provenance,
    resolve_adapter_provenance,
)
from cortex.adapters.ollama_local import DEFAULT_ENDPOINT, OllamaLocalAdapter
from cortex.competence import derive_competence_candidate, verify_competence_candidate
from cortex.competence_transfer import (
    run_cross_model_transfer_trial,
    verify_transfer_trial,
)
from cortex.evaluation import TaskEvaluationContract
from cortex.store import Store
from cortex.will import register_will_principal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Distill a bounded candidate and run strict live A-E transfer controls."
    )
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--origin-session-id", required=True)
    parser.add_argument("--origin-turn-id", type=int, default=1)
    parser.add_argument("--fresh-model", required=True)
    parser.add_argument("--fresh-model-version", required=True)
    parser.add_argument("--fresh-model-family", required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--timeout-seconds", type=float, default=240.0)
    parser.add_argument("--execute-live", action="store_true")
    return parser


def _register_if_needed(
    store: Store,
    repo: str,
    adapter: OllamaLocalAdapter,
    *,
    model_family: str,
) -> dict[str, object]:
    existing = resolve_adapter_provenance(store, repo, adapter)
    if str(existing.get("evidence_class") or "") == EVIDENCE_LIVE:
        return dict(existing)
    principal_id = f"v960-transfer-{int(time.time())}-{secrets.token_hex(4)}"
    principal_secret = secrets.token_urlsafe(48)
    register_will_principal(
        store,
        repo,
        principal_id,
        "Cortex v9.6 empirical transfer operator",
        secret=principal_secret,
    )
    registration = register_adapter_provenance(
        store,
        repo,
        adapter,
        boundary_kind="local_inference_server",
        principal_id=principal_id,
        principal_secret=principal_secret,
        endpoint_descriptor={
            "transport": "loopback_http",
            "service": "ollama",
            "path": "/api/generate",
            "model": adapter.model_id,
        },
        model_family=model_family,
        capability_class="instruction_text_generation",
    )
    principal_secret = ""
    return dict(registration)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="backslashreplace")
    args = _parser().parse_args()
    if not args.execute_live:
        print(json.dumps({"status": "EMPIRICAL_TRANSFER_NOT_EXECUTED"}, indent=2))
        return 2

    store = Store(args.home.resolve() / "cortex.db")
    try:
        if store.repo(str(args.repo)) is None:
            raise ValueError(f"Unknown repository: {args.repo}")
        candidate = derive_competence_candidate(
            store,
            str(args.repo),
            session_id=str(args.origin_session_id),
            turn_id=int(args.origin_turn_id),
            capability={
                "id": "cap.v960.verbatim-public-token",
                "procedure": (
                    "When a bounded task explicitly supplies an exact public token, "
                    "reproduce that token verbatim in public_output.text without tools."
                ),
            },
            intended_outcome={
                "id": "out.v960.exact-public-token",
                "criterion": "predeclared text_contains evaluator passes",
            },
            prerequisites=["task explicitly supplies a bounded public token"],
            applicability_conditions=["text-only response task"],
            environmental_assumptions=["provider-neutral ModelAdapter public output"],
            required_tools=[],
            failure_conditions=[
                "token omitted",
                "token altered",
                "tool or permission request substituted for the token",
            ],
            counterevidence=[
                "The originating circulation is one case only.",
                "No improvement over a fresh capable model has yet been established.",
            ],
            uncertainty=[
                "Transfer benefit may be zero because the task instruction is already explicit."
            ],
            candidate_type="successful_procedure",
            public_description="Verbatim emission of an explicitly supplied bounded public token.",
            rationale_public=(
                "Distilled only from the independently witnessed public behavior; "
                "no hidden reasoning is retained."
            ),
            persist=True,
        )
        candidate_id = str(candidate["competence_id"])
        candidate_check = verify_competence_candidate(store, str(args.repo), candidate_id)
        if candidate_check.get("valid") is not True:
            raise ValueError("distilled competence candidate failed canonical verification")

        registration_adapter = OllamaLocalAdapter(
            model_id=str(args.fresh_model),
            model_version=str(args.fresh_model_version),
            endpoint=str(args.endpoint),
            timeout_seconds=float(args.timeout_seconds),
            temperature=0.0,
            max_output_tokens=160,
            keep_alive="5m",
        )
        registration = _register_if_needed(
            store,
            str(args.repo),
            registration_adapter,
            model_family=str(args.fresh_model_family),
        )

        def factory(arm: str) -> OllamaLocalAdapter:
            return OllamaLocalAdapter(
                model_id=str(args.fresh_model),
                model_version=str(args.fresh_model_version),
                endpoint=str(args.endpoint),
                timeout_seconds=float(args.timeout_seconds),
                temperature=0.0,
                max_output_tokens=160,
                keep_alive="5m",
            )

        transfer_token = "CORTEX_TRANSFER_960"
        task = (
            f"Return the exact public token {transfer_token} in public_output.text. "
            "Do not request tools or permissions."
        )
        contract = TaskEvaluationContract(
            contract_id="cortex-v960-transfer-public-token-v1",
            task_type="text_contains",
            target_field="text",
            expected_value=transfer_token,
            evaluator_id="cortex.v960.transfer.evaluator.v1",
            version="1",
        )
        trial = run_cross_model_transfer_trial(
            store,
            str(args.repo),
            competence_id=candidate_id,
            task_contract=contract,
            adapter_factory=factory,
            task=task,
            tool_scopes=[],
            tool_budget={"token_budget": 2048, "latency_budget_ms": 240000},
            model_configuration={
                "task_instruction": task,
                "temperature": 0.0,
                "external_consequence": "public_text_observation_only",
            },
            policy={
                "min_success_gain": 0.05,
                "max_cost_ratio": 2.0,
                "min_repetitions": 1,
                "required_arms": ["A", "B", "C", "D", "E"],
                "target_portability": "unresolved",
                "utility_weights": {
                    "task_success": 1.0,
                    "abstention_quality": 0.0,
                    "counterevidence_retention": 0.0,
                    "correction_rate": 0.0,
                    "cost_penalty": 0.0,
                    "latency_penalty": 0.0,
                    "prohibited_action_penalty": 0.0,
                },
            },
            measurement_cohort_id="v960-live-local-transfer-1",
            trial_nonce=f"v960-{int(time.time())}",
            persist=True,
        )
        checked = verify_transfer_trial(store, str(args.repo), str(trial["trial_id"]))
        output = {
            "status": (
                "EMPIRICAL_TRANSFER_VERIFIED"
                if str(trial.get("portability_status") or "").startswith("empirical_")
                else "EMPIRICAL_TRANSFER_HELD"
            ),
            "competence_id": candidate_id,
            "competence_receipt_hash": candidate.get("receipt_hash"),
            "candidate_valid": candidate_check.get("valid") is True,
            "trial_id": trial.get("trial_id"),
            "trial_receipt_hash": trial.get("receipt_hash"),
            "trial_valid": checked.get("valid") is True,
            "portability_status": trial.get("portability_status"),
            "evidence_class": trial.get("evidence_class"),
            "arm_evidence_classes": trial.get("arm_evidence_classes"),
            "arm_evaluation_states": {
                arm: value.get("evaluation_state")
                for arm, value in dict(trial.get("arm_results") or {}).items()
            },
            "gains": trial.get("gains"),
            "classification_reasons": trial.get("classification_reasons"),
            "arm_errors": trial.get("arm_errors"),
            "adapter_registration_id": registration.get("registration_id"),
            "declared_minimum_gain": 0.05,
            "credentials_or_secrets_persisted": False,
            "distribution_authorized": False,
            "execution_authorized": False,
            "host_mutate_authorized": False,
            "claim_boundary": trial.get("claim_boundary"),
        }
        print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if checked.get("valid") is True else 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "EMPIRICAL_TRANSFER_HELD",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "credentials_or_secrets_persisted": False,
                    "host_mutate_authorized": False,
                    "execution_authorized": False,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
