#!/usr/bin/env python3
"""Run the exact four-call alpha.39 harder contract-aligned baseline."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.adapter_provenance import (  # noqa: E402
    EVIDENCE_LIVE,
    register_adapter_provenance,
    resolve_adapter_provenance,
)
from cortex.config import cortex_home  # noqa: E402
from cortex.harder_contract_aligned_forge import verify_harder_contract_aligned_forge  # noqa: E402
from cortex.harder_contract_aligned_screen import (  # noqa: E402
    freeze_harder_contract_aligned_screen,
    verify_harder_contract_aligned_screen,
)
from cortex.native_agent import CapabilityGrant, ToolRegistry  # noqa: E402
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402
from cortex.provider_fabric import ProviderFabric  # noqa: E402
from cortex.secret_store import HostSecretStore  # noqa: E402
from cortex.store import Store  # noqa: E402
from cortex.structured_repair_screen import execute_structured_repair_screen  # noqa: E402
from cortex.will import register_will_principal  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--forge-artifact",
        type=Path,
        default=ROOT / "benchmarks/results/v100_alpha38_harder_contract_aligned_forge.json",
    )
    parser.add_argument("--maximum-calls", type=int, default=4)
    parser.add_argument("--register-live-boundary", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "benchmarks/results/v100_alpha39_live_harder_contract_aligned_repair_screen.json",
    )
    args = parser.parse_args(argv)
    if args.maximum_calls != 4:
        raise ValueError("alpha.39 requires an exact four-call ceiling")

    harder = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    corpus_hash = str((harder.get("public_corpus") or {}).get("corpus_hash") or "")
    private = HostCalibrationContractVault().get(corpus_hash)
    if not private:
        raise ValueError("alpha.38 host-private aligned evaluator is unavailable")
    store = Store(cortex_home() / "cortex.db")
    try:
        repository = store.repo(args.repo)
        if repository is None:
            raise ValueError("repository is not attached")
        forge_audit = verify_harder_contract_aligned_forge(
            store, args.repo, harder, private_bundle=private
        )
        if forge_audit.get("valid") is not True:
            raise ValueError("canonical alpha.38 harder forge is required")
        plan = {
            "schema_version": "cortex-alpha39-live-harder-contract-aligned-repair-screen/1.0",
            "state": "HARDER_CONTRACT_ALIGNED_BASELINE_FROZEN",
            "provider": args.provider,
            "model": args.model,
            "planned_calls": 4,
            "maximum_calls": 4,
            "context_treatment": "task_only_control",
            "tools": [],
            "harder_forge_result_hash": harder["result_hash"],
            "aligned_corpus_hash": corpus_hash,
            "prior_result_receipt_hash": harder["prior_result_receipt_hash"],
            "private_specs_origin": "outside_repository",
            "semantic_treatment_projected": False,
            "semantic_transfer_established": False,
            "general_improvement_established": False,
        }
        if not args.execute:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(plan, indent=2))
            return 0

        adapter = ProviderFabric(store, HostSecretStore()).adapter(args.provider, args.model)
        provenance = resolve_adapter_provenance(store, args.repo, adapter)
        if provenance.get("evidence_class") != EVIDENCE_LIVE:
            if not args.register_live_boundary:
                raise ValueError("live adapter registration required")
            principal_id = f"alpha39-{int(time.time())}-{secrets.token_hex(4)}"
            principal_secret = secrets.token_urlsafe(32)
            register_will_principal(
                store,
                args.repo,
                principal_id,
                "Alpha.39 harder baseline operator",
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
                    "provider": args.provider,
                },
                model_family="runtime_selected_frontier",
                capability_class="structured_code_repair",
            )
        prereg = freeze_harder_contract_aligned_screen(
            store,
            args.repo,
            harder_forge=harder,
            private_bundle=private,
            adapter=adapter,
        )
        now = time.time()
        result = execute_structured_repair_screen(
            store,
            args.repo,
            preregistration=prereg,
            private_bundle=private["executable_private_bundle"],
            adapter=adapter,
            tools=ToolRegistry(),
            grant=CapabilityGrant(
                workspace_root=str(repository["path"]),
                allowed_tools=(),
                principal_id="alpha39_live_screen",
                purpose="exact four-call harder contract-aligned frontier baseline",
                issued_at=now,
                expires_at=now + 1800,
                max_tool_calls=0,
                max_total_tool_seconds=0.0,
            ),
        )
        audit = verify_harder_contract_aligned_screen(
            store,
            args.repo,
            result_receipt_hash=result["receipt_hash"],
            harder_forge=harder,
            private_bundle=private,
        )
        report = {
            **plan,
            "state": (
                "HARDER_CONTRACT_ALIGNED_BASELINE_RECONSTRUCTED"
                if audit["valid"]
                else "HARDER_CONTRACT_ALIGNED_BASELINE_HELD"
            ),
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "preregistration_receipt_hash": prereg["receipt_hash"],
            "result_receipt_hash": result["receipt_hash"],
            "calls_executed": result["calls_executed"],
            "screen": result["screen"],
            "canonical_reconstruction": audit,
            "baseline_calibrated": result["baseline_calibrated"] and audit["valid"],
            "next_action": result["next_action"],
            "private_bundle_persisted_in_artifact": False,
            "authority": {
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "memory_admission_authorized": False,
                "policy_effect": False,
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0 if audit["valid"] else 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
