"""Lightweight live commissioning for the alpha.12 autonomy differential.

The runner chooses its provider/model from explicit arguments or the Cortex UI
settings. It never contains a default model identity. Execution requires an
explicit flag and is capped to two calls per frozen case.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.adapter_provenance import (  # noqa: E402
    EVIDENCE_LIVE,
    register_adapter_provenance,
    resolve_adapter_provenance,
)
from cortex.autonomy_differential import (  # noqa: E402
    create_autonomy_differential_preregistration,
    evaluate_autonomy_differential,
    randomization_seed_commitment,
    run_autonomy_differential_case,
)
from cortex.config import cortex_home  # noqa: E402
from cortex.native_agent import CapabilityGrant, ToolRegistry  # noqa: E402
from cortex.provider_fabric import ProviderFabric  # noqa: E402
from cortex.secret_store import HostSecretStore  # noqa: E402
from cortex.store import Store  # noqa: E402
from cortex.will import register_will_principal  # noqa: E402

SCHEMA = "cortex-live-autonomy-pilot/1.0"
VERSION = "10.0.0-alpha.13"
DEFAULT_CORPUS = ROOT / "benchmarks" / "corpora" / "v100_alpha13_autonomy_pilot.json"


def load_cases(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases") if isinstance(payload, dict) else None
    if not isinstance(cases, list) or len(cases) < 2:
        raise ValueError("live autonomy pilot requires at least two frozen cases")
    return [dict(case) for case in cases if isinstance(case, dict)]


def resolve_engine(
    settings: dict[str, Any], provider: str = "", model: str = ""
) -> tuple[str, str]:
    selected_provider = str(provider or settings.get("selected_provider") or "").strip()
    selected_model = str(model or settings.get("selected_model") or "").strip()
    if not selected_provider or not selected_model:
        raise ValueError("select a provider/model in Cortex or pass --provider and --model")
    return selected_provider, selected_model


def _emit(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--provider", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--seed", default="cortex-alpha13-live-pilot-v1")
    parser.add_argument("--maximum-calls", type=int, default=4)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--register-live-boundary",
        action="store_true",
        help="Host-authorize this exact provider adapter as an external API boundary.",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    cases = load_cases(args.corpus.resolve())
    required_calls = 2 * len(cases)
    if required_calls > max(0, int(args.maximum_calls)):
        raise ValueError("frozen panel exceeds --maximum-calls")

    store = Store(cortex_home() / "cortex.db")
    try:
        repository = store.repo(args.repo)
        if repository is None:
            raise ValueError("repository is not attached to Cortex")
        settings = store.get_setting(f"ui:settings:{args.repo}", {}) or {}
        provider, model = resolve_engine(
            dict(settings) if isinstance(settings, dict) else {},
            args.provider,
            args.model,
        )
        plan = {
            "schema_version": SCHEMA,
            "version": VERSION,
            "state": "LIVE_AUTONOMY_PILOT_PLANNED",
            "repo": args.repo,
            "provider": provider,
            "model": model,
            "cases": len(cases),
            "maximum_calls": int(args.maximum_calls),
            "required_calls": required_calls,
            "preregistered_power_expected": False,
            "empirical_advantage_established": False,
            "authority": {
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "memory_admission_authorized": False,
                "policy_effect": False,
            },
            "claim_boundary": (
                "Two-case live commissioning only. A successful run verifies the "
                "paired external-model path; it cannot establish Cortex advantage."
            ),
        }
        if not args.execute:
            _emit(plan, args.output)
            return 0

        fabric = ProviderFabric(store, HostSecretStore())
        adapter = fabric.adapter(provider, model)
        provenance = resolve_adapter_provenance(store, args.repo, adapter)
        if provenance.get("evidence_class") != EVIDENCE_LIVE:
            if not args.register_live_boundary:
                plan["state"] = "LIVE_ADAPTER_REGISTRATION_REQUIRED"
                _emit(plan, args.output)
                return 2
            principal_id = f"alpha13-pilot-{int(time.time())}-{secrets.token_hex(4)}"
            principal_secret = secrets.token_urlsafe(32)
            register_will_principal(
                store,
                args.repo,
                principal_id,
                "Alpha.13 live autonomy pilot operator",
                secret=principal_secret,
            )
            register_adapter_provenance(
                store,
                args.repo,
                adapter,
                boundary_kind="external_api",
                principal_id=principal_id,
                principal_secret=principal_secret,
                endpoint_descriptor={
                    "transport": "provider_fabric_https",
                    "provider": provider,
                },
                model_family="runtime_selected",
                capability_class="general_reasoning",
            )
            provenance = resolve_adapter_provenance(store, args.repo, adapter)
        if provenance.get("evidence_class") != EVIDENCE_LIVE:
            raise RuntimeError("adapter did not resolve as live empirical")

        tools = ToolRegistry()
        grant = CapabilityGrant(
            workspace_root=str(repository["path"]),
            allowed_tools=(),
            principal_id="alpha13_live_pilot",
            purpose="paired autonomy commissioning without host tools",
            issued_at=time.time(),
            expires_at=time.time() + 1800.0,
            max_tool_calls=0,
            max_total_tool_seconds=0.0,
        )
        prereg = create_autonomy_differential_preregistration(
            store,
            args.repo,
            str(repository["path"]),
            adapter=adapter,
            tools=tools,
            grant=grant,
            cases=cases,
            randomization_seed_commitment=randomization_seed_commitment(args.seed),
            minimum_effect=0.25,
            maximum_regression_rate=0.0,
            alpha=0.05,
            expected_discordance=0.50,
            target_power=0.80,
            maximum_total_tokens=4_000,
            maximum_latency_ms=180_000.0,
            maximum_cost=5.0,
        )
        completed = []
        for case in cases:
            completed.append(
                run_autonomy_differential_case(
                    store,
                    args.repo,
                    str(repository["path"]),
                    preregistration_id=str(prereg["preregistration_id"]),
                    case_id=str(case["case_id"]),
                    randomization_seed=args.seed,
                    control_adapter=adapter,
                    cortex_adapter=adapter,
                    tools=tools,
                    grant=grant,
                )
            )
        result = evaluate_autonomy_differential(
            store,
            args.repo,
            preregistration_id=str(prereg["preregistration_id"]),
            persist=True,
        )
        report = {
            **plan,
            "state": result["status"],
            "evidence_class": provenance["evidence_class"],
            "provider_attestation": provenance.get("provider_attestation"),
            "preregistration_id": prereg["preregistration_id"],
            "case_receipt_hashes": [row["receipt_hash"] for row in completed],
            "result_id": result["result_id"],
            "paired_effect": result["exact_matched_binary"]["paired_risk_difference"],
            "discordant_pairs": result["exact_matched_binary"]["discordant_pairs"],
            "exact_two_sided_p": result["exact_matched_binary"]["exact_two_sided_p"],
            "failed_gates": result["failed_gates"],
            "empirical_advantage_established": result["empirical_advantage_established"],
        }
        _emit(report, args.output)
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
