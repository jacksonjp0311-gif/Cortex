"""Alpha.28 zero-call audit of the bridge-low live instrument."""

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
from cortex.relational_live_screen import audit_bridge_low_instrument  # noqa: E402
from cortex.store import Store  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--forge-artifact", type=Path, required=True)
    parser.add_argument("--result-receipt-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    forge = json.loads(args.forge_artifact.read_text(encoding="utf-8"))
    manifest = forge["public_corpus_manifest"]
    private = HostCalibrationContractVault().get(manifest["corpus_hash"])
    if not private:
        raise ValueError("private intermediate contracts are unavailable")
    bundle = {"manifest": manifest, "private_key": private}
    store = Store(cortex_home() / "cortex.db")
    try:
        audit = audit_bridge_low_instrument(
            store,
            args.repo,
            result_receipt_hash=args.result_receipt_hash,
            corpus_bundle=bundle,
        )
        report = {
            "schema_version": "cortex-alpha28-bridge-low-instrument-audit/1.0",
            "state": audit["state"],
            "source_commit": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "audit_receipt_hash": audit["receipt_hash"],
            "result_receipt_hash": args.result_receipt_hash,
            "historical_screen": audit["historical_screen"],
            "historical_scores_rewritten": False,
            "additional_model_calls": 0,
            "valid_json_response_count": audit["valid_json_response_count"],
            "graph_mapping_rejection_count": audit["graph_mapping_rejection_count"],
            "sufficient_proof_superset_rejection_count": audit[
                "sufficient_proof_superset_rejection_count"
            ],
            "error_counts": audit["error_counts"],
            "difficulty_interpretation_confounded": audit[
                "difficulty_interpretation_confounded"
            ],
            "baseline_difficulty_established": False,
            "semantic_transfer_established": False,
            "next_action": audit["next_action"],
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
