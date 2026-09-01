"""Alpha.28 bounded live bridge-low relational screen."""

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
from cortex.native_agent import CapabilityGrant, ToolRegistry  # noqa: E402
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402
from cortex.provider_fabric import ProviderFabric  # noqa: E402
from cortex.relational_live_screen import (  # noqa: E402
    execute_bridge_low_screen,
    freeze_bridge_low_screen,
    verify_bridge_low_screen,
)
from cortex.secret_store import HostSecretStore  # noqa: E402
from cortex.store import Store  # noqa: E402
from cortex.will import register_will_principal  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--provider", default="")
    parser.add_argument("--model", default="")
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--evaluator-artifact", type=Path, required=True)
    parser.add_argument("--forge-preflight-receipt-hash", required=True)
    parser.add_argument("--maximum-calls", type=int, default=4)
    parser.add_argument("--register-live-boundary", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.maximum_calls != 4:
        raise ValueError("alpha.28 requires an exact four-call ceiling")
    forge = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    evaluator = json.loads(args.evaluator_artifact.read_text(encoding="utf-8"))
    corpus_manifest = forge["public_corpus_manifest"]
    evaluator_manifest = evaluator["evaluator_manifest"]
    vault = HostCalibrationContractVault()
    corpus_private = vault.get(corpus_manifest["corpus_hash"])
    evaluator_private = vault.get(evaluator_manifest["evaluator_hash"])
    if not corpus_private or not evaluator_private:
        raise ValueError("private corpus/evaluator contracts are unavailable")
    corpus_bundle = {"manifest": corpus_manifest, "private_key": corpus_private}
    evaluator_bundle = {"manifest": evaluator_manifest, "private_key": evaluator_private}
    store = Store(cortex_home() / "cortex.db")
    try:
        repository = store.repo(args.repo)
        if repository is None:
            raise ValueError("repository is not attached")
        settings = store.get_setting(f"ui:settings:{args.repo}", {}) or {}
        provider = str(args.provider or settings.get("selected_provider") or "").strip()
        model = str(args.model or settings.get("selected_model") or "").strip()
        if not provider or not model:
            raise ValueError("select a provider/model in Cortex or pass explicit arguments")
        plan = {
            "schema_version": "cortex-alpha28-bridge-low-relational-screen/1.0",
            "state": "BRIDGE_LOW_SCREEN_PLANNED",
            "provider": provider,
            "model": model,
            "planned_calls": 4,
            "maximum_calls": 4,
            "semantic_transfer_established": False,
        }
        if not args.execute:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(plan, indent=2))
            return 0
        adapter = ProviderFabric(store, HostSecretStore()).adapter(provider, model)
        provenance = resolve_adapter_provenance(store, args.repo, adapter)
        if provenance.get("evidence_class") != EVIDENCE_LIVE:
            if not args.register_live_boundary:
                raise ValueError("live adapter registration required; rerun with --register-live-boundary")
            principal_id = f"alpha28-{int(time.time())}-{secrets.token_hex(4)}"
            principal_secret = secrets.token_urlsafe(32)
            register_will_principal(
                store,
                args.repo,
                principal_id,
                "Alpha.28 bounded relational screen operator",
                secret=principal_secret,
            )
            register_adapter_provenance(
                store,
                args.repo,
                adapter,
                boundary_kind="external_api",
                principal_id=principal_id,
                principal_secret=principal_secret,
                endpoint_descriptor={"transport": "provider_fabric_https", "provider": provider},
                model_family="runtime_selected",
                capability_class="general_reasoning",
            )
        preregistration = freeze_bridge_low_screen(
            store,
            args.repo,
            forge_preflight_receipt_hash=args.forge_preflight_receipt_hash,
            corpus_bundle=corpus_bundle,
            evaluator_bundle=evaluator_bundle,
            adapter=adapter,
        )
        grant = CapabilityGrant(
            workspace_root=str(repository["path"]),
            allowed_tools=(),
            principal_id="alpha28_bridge_low",
            purpose="exact four-call task-only bridge-low relational screen",
            issued_at=time.time(),
            expires_at=time.time() + 1800,
            max_tool_calls=0,
            max_total_tool_seconds=0.0,
        )
        result = execute_bridge_low_screen(
            store,
            args.repo,
            preregistration=preregistration,
            corpus_bundle=corpus_bundle,
            adapter=adapter,
            tools=ToolRegistry(),
            grant=grant,
        )
        audit = verify_bridge_low_screen(
            store,
            args.repo,
            result_receipt_hash=result["receipt_hash"],
            corpus_bundle=corpus_bundle,
        )
        report = {
            **plan,
            "state": result["status"] if audit["valid"] else "BRIDGE_LOW_SCREEN_HELD",
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "corpus_hash": corpus_manifest["corpus_hash"],
            "evaluator_hash": evaluator_manifest["evaluator_hash"],
            "forge_preflight_receipt_hash": args.forge_preflight_receipt_hash,
            "preregistration_receipt_hash": preregistration["receipt_hash"],
            "result_receipt_hash": result["receipt_hash"],
            "calls_executed": result["calls_executed"],
            "screen": result["screen"],
            "canonical_reconstruction": audit,
            "calibration_established": result["calibration_established"] and audit["valid"],
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
        return 0 if audit["valid"] else 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
