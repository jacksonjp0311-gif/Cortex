"""Alpha.29 zero-call deterministic relational equivalence commissioning."""

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
from cortex.relational_equivalence import (  # noqa: E402
    build_equivalence_evaluator_bundle,
    freeze_equivalence_policy,
    verify_equivalence_evaluator_bundle,
)
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--instrument-audit-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    forge = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    manifest = forge["public_corpus_manifest"]
    vault = HostCalibrationContractVault()
    source_private = vault.get(manifest["corpus_hash"])
    if not source_private:
        raise ValueError("private intermediate contracts are unavailable")
    source_bundle = {"manifest": manifest, "private_key": source_private}
    bundle = build_equivalence_evaluator_bundle(source_bundle)
    check = verify_equivalence_evaluator_bundle(bundle)
    if check.get("valid") is not True:
        raise ValueError(f"equivalence evaluator invalid: {check['errors']}")
    evaluator_hash = bundle["manifest"]["evaluator_hash"]
    vault.set(evaluator_hash, bundle["private_key"])
    store = Store(cortex_home() / "cortex.db")
    try:
        try:
            preflight = freeze_equivalence_policy(
                store,
                args.repo,
                instrument_audit_receipt_hash=args.instrument_audit_receipt_hash,
                corpus_bundle=source_bundle,
                evaluator_bundle=bundle,
            )
        except Exception:
            vault.delete(evaluator_hash)
            raise
        report = {
            "schema_version": "cortex-alpha29-relational-equivalence/1.0",
            "state": preflight["state"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "preflight_receipt_hash": preflight["receipt_hash"],
            "source_instrument_audit_receipt_hash": args.instrument_audit_receipt_hash,
            "source_result_receipt_hash": preflight["source_result_receipt_hash"],
            "evaluator_manifest": bundle["manifest"],
            "private_contract_storage": "host_os_credential_vault",
            "private_contract_persisted_in_artifact": False,
            "self_test": {
                "passed": preflight["self_test"]["passed"],
                "check_count": preflight["self_test"]["check_count"],
            },
            "post_hoc_shadow": preflight["post_hoc_shadow"],
            "post_hoc_shadow_success_count": preflight[
                "post_hoc_shadow_success_count"
            ],
            "historical_scores_rewritten": False,
            "additional_model_calls": 0,
            "ruler_building_closed": True,
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
