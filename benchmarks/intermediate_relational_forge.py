"""Alpha.27 zero-call intermediate relational task forge commissioning."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.config import cortex_home  # noqa: E402
from cortex.intermediate_relational_forge import (  # noqa: E402
    build_intermediate_relational_bundle,
    freeze_intermediate_relational_forge,
    verify_intermediate_relational_bundle,
)
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--relational-preflight-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    bundle = build_intermediate_relational_bundle(secret_seed=secrets.token_hex(32))
    check = verify_intermediate_relational_bundle(bundle)
    if check.get("valid") is not True:
        raise ValueError(f"generated intermediate bundle invalid: {check['errors']}")
    manifest = bundle["manifest"]
    vault = HostCalibrationContractVault()
    vault.set(manifest["corpus_hash"], bundle["private_key"])
    store = Store(cortex_home() / "cortex.db")
    try:
        try:
            preflight = freeze_intermediate_relational_forge(
                store,
                args.repo,
                relational_preflight_receipt_hash=args.relational_preflight_receipt_hash,
                bundle=bundle,
            )
        except Exception:
            vault.delete(manifest["corpus_hash"])
            raise
        report = {
            "schema_version": "cortex-alpha27-intermediate-relational-forge/1.0",
            "state": preflight["state"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "preflight_receipt_hash": preflight["receipt_hash"],
            "source_relational_preflight_receipt_hash": args.relational_preflight_receipt_hash,
            "public_corpus_manifest": manifest,
            "private_contract_storage": "host_os_credential_vault",
            "private_contract_persisted_in_artifact": False,
            "panel_count": 3,
            "cases_per_panel": 4,
            "planned_live_calls": 0,
            "maximum_future_calls_without_new_authority": 0,
            "historical_scores_rewritten": False,
            "evidence_policy_constant_across_bands": True,
            "baseline_difficulty_established": False,
            "semantic_transfer_established": False,
            "next_action": preflight["next_action"],
            "authority": {
                "host_mutate_authorized": False,
                "execution_authorized": False,
                "memory_admission_authorized": False,
                "policy_effect": False,
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    key: value
                    for key, value in report.items()
                    if key != "public_corpus_manifest"
                },
                indent=2,
            )
        )
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
