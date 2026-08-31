"""Alpha.20 zero-call open-response latent-cause forge commissioning."""

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
from cortex.open_response_calibration import (  # noqa: E402
    HostCalibrationContractVault,
    build_open_response_latent_bundle,
    evaluate_atomic_causal_response,
    freeze_open_response_forge,
    verify_open_response_latent_bundle,
)
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--prior-result-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    store = Store(cortex_home() / "cortex.db")
    try:
        bundle = build_open_response_latent_bundle(secret_seed=secrets.token_hex(32))
        check = verify_open_response_latent_bundle(bundle)
        if check.get("valid") is not True:
            raise ValueError("generated open-response bundle failed verification")
        preflight = freeze_open_response_forge(
            store,
            args.repo,
            prior_result_receipt_hash=args.prior_result_receipt_hash,
            bundle=bundle,
        )
        manifest = bundle["manifest"]
        HostCalibrationContractVault().set(manifest["corpus_hash"], bundle["private_key"])
        private_key = bundle["private_key"]
        reference_checks = [
            evaluate_atomic_causal_response(
                private_key["contracts"][case_id],
                json.dumps(private_key["contracts"][case_id]["reference_response"]),
            )["success"]
            for case_id in preflight["initial_screen_case_ids"]
        ]
        report = {
            "schema_version": "cortex-alpha20-open-response-forge/1.0",
            "state": preflight["state"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "prior_result_receipt_hash": args.prior_result_receipt_hash,
            "preflight_receipt_hash": preflight["receipt_hash"],
            "public_corpus_manifest": manifest,
            "private_contract_storage": "host_os_credential_vault",
            "private_contract_persisted_in_artifact": False,
            "reference_evaluator_checks": {
                "case_count": len(reference_checks),
                "all_pass": all(reference_checks),
            },
            "planned_live_calls": 0,
            "calibration_established": False,
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
        print(json.dumps({key: value for key, value in report.items() if key != "public_corpus_manifest"}, indent=2))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
