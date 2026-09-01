"""Alpha.23 four-call live task-only screen using the frozen v2 evaluator."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.config import cortex_home  # noqa: E402
from cortex.native_agent import CapabilityGrant, ToolRegistry  # noqa: E402
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402
from cortex.provider_fabric import ProviderFabric  # noqa: E402
from cortex.secret_store import HostSecretStore  # noqa: E402
from cortex.semantic_causal_evaluator import (  # noqa: E402
    execute_live_semantic_screen_v2,
    freeze_live_semantic_screen_v2,
)
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--evaluator-artifact", type=Path, required=True)
    parser.add_argument("--evaluator-preflight-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    forge = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    evaluator_artifact = json.loads(args.evaluator_artifact.read_text(encoding="utf-8"))
    corpus = forge["public_corpus_manifest"]
    evaluator_manifest = evaluator_artifact["evaluator_manifest"]
    private_key = HostCalibrationContractVault().get(evaluator_manifest["evaluator_hash"])
    if not private_key:
        raise ValueError("private v2 evaluator is unavailable from host vault")
    evaluator_bundle = {"manifest": evaluator_manifest, "private_key": private_key}
    store = Store(cortex_home() / "cortex.db")
    try:
        repository = store.repo(args.repo)
        if repository is None:
            raise ValueError("repository is not attached")
        adapter = ProviderFabric(store, HostSecretStore()).adapter(args.provider, args.model)
        preregistration = freeze_live_semantic_screen_v2(
            store,
            args.repo,
            evaluator_preflight_receipt_hash=args.evaluator_preflight_receipt_hash,
            corpus_manifest=corpus,
            evaluator_bundle=evaluator_bundle,
            adapter=adapter,
        )
        grant = CapabilityGrant(
            workspace_root=str(repository["path"]),
            allowed_tools=(),
            principal_id="alpha23_live_semantic_causal",
            purpose="four-call task-only semantic causal screen",
            issued_at=time.time(),
            expires_at=time.time() + 1800,
            max_tool_calls=0,
            max_total_tool_seconds=0.0,
        )
        result = execute_live_semantic_screen_v2(
            store,
            args.repo,
            preregistration=preregistration,
            corpus_manifest=corpus,
            evaluator_bundle=evaluator_bundle,
            adapter=adapter,
            tools=ToolRegistry(),
            grant=grant,
        )
        report = {
            "schema_version": "cortex-alpha23-live-semantic-causal-screen/1.0",
            "state": result["status"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "provider": args.provider,
            "model": args.model,
            "corpus_hash": corpus["corpus_hash"],
            "evaluator_hash": evaluator_manifest["evaluator_hash"],
            "evaluator_preflight_receipt_hash": args.evaluator_preflight_receipt_hash,
            "preregistration_receipt_hash": preregistration["receipt_hash"],
            "result_receipt_hash": result["receipt_hash"],
            "planned_calls": 4,
            "calls_executed": result["calls_executed"],
            "screen": result["screen"],
            "calibration_established": result["calibration_established"],
            "semantic_transfer_established": False,
            "private_contract_persisted_in_artifact": False,
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
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
