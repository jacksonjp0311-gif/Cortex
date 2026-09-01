#!/usr/bin/env python3
"""Commission the zero-call alpha.38 harder contract-aligned repair forge."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.config import cortex_home  # noqa: E402
from cortex.contract_aligned_repair import build_contract_aligned_repair_bundle  # noqa: E402
from cortex.harder_contract_aligned_forge import (  # noqa: E402
    freeze_harder_contract_aligned_forge,
    verify_harder_contract_aligned_forge,
)
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402
from cortex.store import Store  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="Cortex")
    parser.add_argument("--private-spec", type=Path, required=True)
    parser.add_argument("--prior-result-receipt-hash", required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "benchmarks/results/v100_alpha38_harder_contract_aligned_forge.json",
    )
    args = parser.parse_args()
    private_path = args.private_spec.resolve()
    try:
        private_path.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("private aligned specifications must remain outside the repository")
    specs = json.loads(private_path.read_text(encoding="utf-8"))
    if not isinstance(specs, list):
        raise ValueError("private aligned specification must be a JSON list")
    public, private = build_contract_aligned_repair_bundle(
        secret_seed=secrets.token_hex(32),
        case_specs=specs,
    )
    vault = HostCalibrationContractVault()
    vault.set(str(public["corpus_hash"]), private)
    store = Store(cortex_home() / "cortex.db")
    try:
        source_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        with tempfile.TemporaryDirectory(prefix="cortex-alpha38-") as parent:
            result = freeze_harder_contract_aligned_forge(
                store,
                args.repo,
                prior_result_receipt_hash=args.prior_result_receipt_hash,
                public_corpus=public,
                private_bundle=private,
                workspace=Path(parent),
                source_commit=source_commit,
            )
        audit = verify_harder_contract_aligned_forge(
            store,
            args.repo,
            result,
            private_bundle=private,
        )
        if audit["valid"] is not True:
            raise SystemExit("harder forge failed reconstruction: " + ",".join(audit["errors"]))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "state": result["state"],
                    "corpus_hash": public["corpus_hash"],
                    "result_hash": result["result_hash"],
                    "prior_result_receipt_hash": args.prior_result_receipt_hash,
                    "model_calls": result["additional_model_calls"],
                    "output": str(args.output),
                },
                indent=2,
            )
        )
        return 0 if result["state"] == "HARDER_CONTRACT_ALIGNED_FORGE_READY" else 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
