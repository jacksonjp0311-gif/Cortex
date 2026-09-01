"""Alpha.32 four-call frontier-model executable repair screen."""

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

from cortex.adapter_provenance import EVIDENCE_LIVE, register_adapter_provenance, resolve_adapter_provenance  # noqa: E402
from cortex.config import cortex_home  # noqa: E402
from cortex.executable_repair_screen import execute_executable_repair_screen, freeze_executable_repair_screen, verify_executable_repair_screen  # noqa: E402
from cortex.native_agent import CapabilityGrant, ToolRegistry  # noqa: E402
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402
from cortex.provider_fabric import ProviderFabric  # noqa: E402
from cortex.secret_store import HostSecretStore  # noqa: E402
from cortex.store import Store  # noqa: E402
from cortex.will import register_will_principal  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--register-live-boundary", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    forge = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    private = HostCalibrationContractVault().get(str(forge["corpus_hash"]))
    if not private:
        raise ValueError("alpha.31 private evaluator bundle is unavailable")
    plan = {
        "schema_version": "cortex-alpha32-live-executable-repair-screen/1.0",
        "state": "EXECUTABLE_REPAIR_SCREEN_FROZEN",
        "provider": args.provider,
        "model": args.model,
        "planned_calls": 4,
        "maximum_calls": 4,
        "context_treatment": "task_only_control",
        "tools": [],
        "corpus_hash": forge["corpus_hash"],
        "semantic_transfer_established": False,
        "general_improvement_established": False,
    }
    if not args.execute:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(plan, indent=2))
        return 0
    store = Store(cortex_home() / "cortex.db")
    try:
        repository = store.repo(args.repo)
        if repository is None:
            raise ValueError("repository is not attached")
        adapter = ProviderFabric(store, HostSecretStore()).adapter(args.provider, args.model)
        provenance = resolve_adapter_provenance(store, args.repo, adapter)
        if provenance.get("evidence_class") != EVIDENCE_LIVE:
            if not args.register_live_boundary:
                raise ValueError("live adapter registration required")
            principal_id = f"alpha32-{int(time.time())}-{secrets.token_hex(4)}"
            principal_secret = secrets.token_urlsafe(32)
            register_will_principal(store, args.repo, principal_id, "Alpha.32 executable repair operator", secret=principal_secret)
            register_adapter_provenance(
                store, args.repo, adapter, boundary_kind="external_api",
                principal_id=principal_id, principal_secret=principal_secret,
                endpoint_descriptor={"transport": "provider_fabric_https", "provider": args.provider},
                model_family="runtime_selected_frontier", capability_class="code_repair",
            )
        prereg = freeze_executable_repair_screen(store, args.repo, forge_artifact=forge, private_bundle=private, adapter=adapter)
        grant = CapabilityGrant(
            workspace_root=str(repository["path"]), allowed_tools=(), principal_id="alpha32_live_screen",
            purpose="exact four-call task-only executable repair screen", issued_at=time.time(),
            expires_at=time.time() + 1800, max_tool_calls=0, max_total_tool_seconds=0.0,
        )
        result = execute_executable_repair_screen(
            store, args.repo, preregistration=prereg, private_bundle=private,
            adapter=adapter, tools=ToolRegistry(), grant=grant,
        )
        audit = verify_executable_repair_screen(store, args.repo, result_receipt_hash=result["receipt_hash"])
        report = {
            **plan,
            "state": result["status"] if audit["valid"] else "EXECUTABLE_REPAIR_SCREEN_HELD",
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "preregistration_receipt_hash": prereg["receipt_hash"],
            "result_receipt_hash": result["receipt_hash"],
            "calls_executed": result["calls_executed"],
            "screen": result["screen"],
            "canonical_reconstruction": audit,
            "baseline_calibrated": result["baseline_calibrated"] and audit["valid"],
            "next_action": result["next_action"],
            "private_bundle_persisted_in_artifact": False,
            "authority": {"host_mutate_authorized": False, "execution_authorized": False, "memory_admission_authorized": False, "policy_effect": False},
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0 if audit["valid"] else 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
