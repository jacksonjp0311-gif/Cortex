"""Alpha.22 zero-call semantic causal evaluator commissioning."""

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
from cortex.semantic_causal_evaluator import (  # noqa: E402
    build_semantic_evaluator_bundle,
    freeze_semantic_evaluator_v2,
    verify_semantic_evaluator_bundle,
)
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--result-receipt-hash", required=True)
    parser.add_argument("--audit-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    forge = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    corpus = forge["public_corpus_manifest"]
    vault = HostCalibrationContractVault()
    source_private_key = vault.get(corpus["corpus_hash"])
    if not source_private_key:
        raise ValueError("source private contract is unavailable from host vault")
    bundle = build_semantic_evaluator_bundle(corpus, source_private_key)
    check = verify_semantic_evaluator_bundle(bundle)
    if check.get("valid") is not True:
        raise ValueError(f"semantic evaluator bundle invalid: {check['errors']}")
    evaluator_hash = bundle["manifest"]["evaluator_hash"]
    vault.set(evaluator_hash, bundle["private_key"])
    store = Store(cortex_home() / "cortex.db")
    try:
        try:
            preflight = freeze_semantic_evaluator_v2(
                store,
                args.repo,
                audit_receipt_hash=args.audit_receipt_hash,
                source_result_receipt_hash=args.result_receipt_hash,
                bundle=bundle,
                source_private_key=source_private_key,
            )
        except Exception:
            vault.delete(evaluator_hash)
            raise
        shadow = preflight["historical_shadow"]
        report = {
            "schema_version": "cortex-alpha22-semantic-causal-evaluator/1.0",
            "state": preflight["state"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "preflight_receipt_hash": preflight["receipt_hash"],
            "source_result_receipt_hash": args.result_receipt_hash,
            "source_audit_receipt_hash": args.audit_receipt_hash,
            "evaluator_manifest": bundle["manifest"],
            "private_contract_storage": "host_os_credential_vault",
            "private_contract_persisted_in_artifact": False,
            "self_test": {
                "passed": preflight["self_test"]["passed"],
                "check_count": preflight["self_test"]["check_count"],
            },
            "historical_shadow": {
                "case_count": len(shadow),
                "pass_count": sum(row["verdict"]["success"] is True for row in shadow),
                "post_hoc_only": True,
                "scores_rewritten": False,
            },
            "planned_live_calls": 0,
            "baseline_difficulty_established": False,
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
        print(json.dumps(report, indent=2))
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
