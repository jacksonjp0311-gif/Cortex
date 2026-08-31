"""Alpha.21 bounded live open-response task-only calibration screen."""

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
from cortex.open_response_calibration import (  # noqa: E402
    HostCalibrationContractVault,
    execute_live_open_response_screen,
    freeze_live_open_response_screen,
)
from cortex.provider_fabric import ProviderFabric  # noqa: E402
from cortex.secret_store import HostSecretStore  # noqa: E402
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--preflight-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    artifact = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    manifest = artifact["public_corpus_manifest"]
    private_key = HostCalibrationContractVault().get(manifest["corpus_hash"])
    if not private_key:
        raise ValueError("private calibration contract is unavailable from host vault")
    store = Store(cortex_home() / "cortex.db")
    try:
        repository = store.repo(args.repo)
        if repository is None:
            raise ValueError("repository is not attached")
        adapter = ProviderFabric(store, HostSecretStore()).adapter(args.provider, args.model)
        preregistration = freeze_live_open_response_screen(
            store,
            args.repo,
            preflight_receipt_hash=args.preflight_receipt_hash,
            manifest=manifest,
            private_key=private_key,
            adapter=adapter,
        )
        grant = CapabilityGrant(
            workspace_root=str(repository["path"]),
            allowed_tools=(),
            principal_id="alpha21_live_open_response",
            purpose="four-call task-only open-response screen",
            issued_at=time.time(),
            expires_at=time.time() + 1800,
            max_tool_calls=0,
            max_total_tool_seconds=0.0,
        )
        result = execute_live_open_response_screen(
            store,
            args.repo,
            preregistration=preregistration,
            manifest=manifest,
            private_key=private_key,
            adapter=adapter,
            tools=ToolRegistry(),
            grant=grant,
        )
        report = {
            "schema_version": "cortex-alpha21-live-open-response-screen/1.0",
            "state": result["status"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "provider": args.provider,
            "model": args.model,
            "corpus_hash": manifest["corpus_hash"],
            "preflight_receipt_hash": args.preflight_receipt_hash,
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
