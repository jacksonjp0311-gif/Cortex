"""Alpha.18 bounded live frontier-model semantic calibration screen."""

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
    EVIDENCE_LIVE, register_adapter_provenance, resolve_adapter_provenance,
)
from cortex.config import cortex_home  # noqa: E402
from cortex.native_agent import CapabilityGrant, ToolRegistry  # noqa: E402
from cortex.provider_fabric import ProviderFabric  # noqa: E402
from cortex.secret_store import HostSecretStore  # noqa: E402
from cortex.semantic_calibration import (  # noqa: E402
    build_semantic_calibration_bundle, build_semantic_calibration_preflight,
    execute_live_calibration_screen, freeze_live_calibration_screen,
)
from cortex.source_experience import forge_structural_source_experience_pair  # noqa: E402
from cortex.store import Store  # noqa: E402
from cortex.will import register_will_principal  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--provider", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--register-live-boundary", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    store = Store(cortex_home() / "cortex.db")
    try:
        repository = store.repo(args.repo)
        if repository is None:
            raise ValueError("repository is not attached")
        adapter = ProviderFabric(store, HostSecretStore()).adapter(args.provider, args.model)
        provenance = resolve_adapter_provenance(store, args.repo, adapter)
        if provenance.get("evidence_class") != EVIDENCE_LIVE:
            if not args.register_live_boundary:
                raise ValueError("live adapter registration is required")
            principal_id = f"alpha18-screen-{int(time.time())}-{secrets.token_hex(4)}"
            principal_secret = secrets.token_urlsafe(32)
            register_will_principal(
                store, args.repo, principal_id,
                "Alpha.18 live semantic calibration operator", secret=principal_secret,
            )
            register_adapter_provenance(
                store, args.repo, adapter, boundary_kind="external_api",
                principal_id=principal_id, principal_secret=principal_secret,
                endpoint_descriptor={"transport": "provider_fabric_https", "provider": args.provider},
                model_family="runtime_selected_frontier",
                capability_class="general_reasoning",
            )
        pair = forge_structural_source_experience_pair(store, args.repo)
        bundle = build_semantic_calibration_bundle(secret_seed=secrets.token_hex(32))
        preflight = build_semantic_calibration_preflight(pair, bundle)
        prereg = freeze_live_calibration_screen(
            store, args.repo, preflight=preflight, bundle=bundle, adapter=adapter
        )
        plan = {
            "schema_version": "cortex-alpha18-live-screen/1.0",
            "state": "LIVE_SCREEN_FROZEN",
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "provider": args.provider,
            "model": args.model,
            "preregistration_id": prereg["preregistration_id"],
            "planned_calls": 4,
            "calls_executed": 0,
            "semantic_transfer_established": False,
        }
        if not args.execute:
            report = plan
        else:
            grant = CapabilityGrant(
                workspace_root=str(repository["path"]), allowed_tools=(),
                principal_id="alpha18_live_calibration", purpose="four-call task-only screen",
                issued_at=time.time(), expires_at=time.time() + 1800,
                max_tool_calls=0, max_total_tool_seconds=0.0,
            )
            result = execute_live_calibration_screen(
                store, args.repo, preregistration=prereg, bundle=bundle,
                adapter=adapter, tools=ToolRegistry(), grant=grant,
            )
            report = {
                **plan,
                "state": result["status"],
                "evidence_class": result["evidence_class"],
                "result_receipt_hash": result["receipt_hash"],
                "screen": result["screen"],
                "calls_executed": result["calls_executed"],
                "calibration_established": result["calibration_established"],
                "semantic_transfer_established": False,
                "authority": {
                    "host_mutate_authorized": False, "execution_authorized": False,
                    "memory_admission_authorized": False, "policy_effect": False,
                },
            }
        rendered = json.dumps(report, indent=2, ensure_ascii=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
