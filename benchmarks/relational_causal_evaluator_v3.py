"""Alpha.26 zero-call relational causal evaluator commissioning."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.config import cortex_home  # noqa: E402
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402
from cortex.relational_causal_evaluator import (  # noqa: E402
    build_relational_evaluator_bundle,
    freeze_relational_evaluator_v3,
    verify_relational_evaluator_bundle,
)
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--v2-evaluator-artifact", type=Path, required=True)
    parser.add_argument("--instrument-audit-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    forge = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    v2_artifact = json.loads(args.v2_evaluator_artifact.read_text(encoding="utf-8"))
    corpus = forge["public_corpus_manifest"]
    vault = HostCalibrationContractVault()
    v2_manifest = v2_artifact["evaluator_manifest"]
    v2_private = vault.get(v2_manifest["evaluator_hash"])
    if not v2_private:
        raise ValueError("private v2 evaluator is unavailable from host vault")
    v2_bundle = {"manifest": v2_manifest, "private_key": v2_private}
    v3_bundle = build_relational_evaluator_bundle(corpus)
    check = verify_relational_evaluator_bundle(v3_bundle)
    if check.get("valid") is not True:
        raise ValueError(f"relational evaluator bundle invalid: {check['errors']}")
    evaluator_hash = v3_bundle["manifest"]["evaluator_hash"]
    vault.set(evaluator_hash, v3_bundle["private_key"])
    store = Store(cortex_home() / "cortex.db")
    try:
        try:
            preflight = freeze_relational_evaluator_v3(
                store,
                args.repo,
                instrument_audit_receipt_hash=args.instrument_audit_receipt_hash,
                v2_bundle=v2_bundle,
                v3_bundle=v3_bundle,
            )
        except Exception:
            vault.delete(evaluator_hash)
            raise
        report = {
            "schema_version": "cortex-alpha26-relational-causal-evaluator/1.0",
            "state": preflight["state"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "preflight_receipt_hash": preflight["receipt_hash"],
            "source_instrument_audit_receipt_hash": args.instrument_audit_receipt_hash,
            "source_result_receipt_hash": preflight["source_result_receipt_hash"],
            "evaluator_manifest": v3_bundle["manifest"],
            "private_contract_storage": "host_os_credential_vault",
            "private_contract_persisted_in_artifact": False,
            "self_test": {
                "passed": preflight["self_test"]["passed"],
                "check_count": preflight["self_test"]["check_count"],
            },
            "historical_scores_rewritten": False,
            "planned_live_calls": 0,
            "difficulty_interpolation_ready": True,
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
        print(json.dumps(report, indent=2))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
