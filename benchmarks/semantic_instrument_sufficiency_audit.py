"""Alpha.25 zero-call audit of the apparent alpha.24 difficulty floor."""

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
    audit_harder_live_semantic_screen_v2,
)
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--evaluator-artifact", type=Path, required=True)
    parser.add_argument("--result-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    evaluator_artifact = json.loads(args.evaluator_artifact.read_text(encoding="utf-8"))
    evaluator_manifest = evaluator_artifact["evaluator_manifest"]
    private_key = HostCalibrationContractVault().get(evaluator_manifest["evaluator_hash"])
    if not private_key:
        raise ValueError("private v2 evaluator is unavailable from host vault")
    evaluator_bundle = {"manifest": evaluator_manifest, "private_key": private_key}
    store = Store(cortex_home() / "cortex.db")
    try:
        audit = audit_harder_live_semantic_screen_v2(
            store,
            args.repo,
            result_receipt_hash=args.result_receipt_hash,
            evaluator_bundle=evaluator_bundle,
        )
        report = {
            "schema_version": "cortex-alpha25-semantic-instrument-sufficiency-audit/1.0",
            "state": audit["state"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "result_receipt_hash": args.result_receipt_hash,
            "audit_receipt_hash": audit["receipt_hash"],
            "case_count": audit["case_count"],
            "evidence_binding_rejection_count": audit[
                "evidence_binding_rejection_count"
            ],
            "semantic_clause_rejection_count": audit[
                "semantic_clause_rejection_count"
            ],
            "instrument_task_confound_present": audit[
                "instrument_task_confound_present"
            ],
            "historical_scores_rewritten": False,
            "additional_model_calls": 0,
            "difficulty_interpolation_ready": audit["difficulty_interpolation_ready"],
            "baseline_difficulty_established": False,
            "semantic_transfer_established": False,
            "next_action": audit["next_action"],
            "case_diagnostics": audit["case_diagnostics"],
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
