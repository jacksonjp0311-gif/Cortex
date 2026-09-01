#!/usr/bin/env python3
"""Commission the zero-call alpha.36 contract-aligned repair corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cortex.contract_aligned_repair import (  # noqa: E402
    build_contract_aligned_repair_bundle,
    commission_contract_aligned_repair_forge,
    verify_contract_aligned_repair_forge_result,
)
from cortex.open_response_calibration import HostCalibrationContractVault  # noqa: E402


def _sha(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-spec", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT
        / "benchmarks/results/v100_alpha36_contract_aligned_repair_forge.json",
    )
    arguments = parser.parse_args()
    private_path = arguments.private_spec.resolve()
    try:
        private_path.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("private aligned specifications must remain outside the repository")
    private_specs = json.loads(private_path.read_text(encoding="utf-8"))
    if not isinstance(private_specs, list):
        raise ValueError("private aligned specification must be a JSON list")

    public, private = build_contract_aligned_repair_bundle(
        secret_seed=secrets.token_hex(32),
        case_specs=private_specs,
    )
    HostCalibrationContractVault().set(str(public["corpus_hash"]), private)
    with tempfile.TemporaryDirectory(prefix="cortex-alpha36-") as parent:
        result = commission_contract_aligned_repair_forge(
            public,
            private,
            Path(parent),
        )
    result["source_commit"] = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    result["public_corpus"] = public
    result["result_hash"] = _sha(
        {key: value for key, value in result.items() if key != "result_hash"}
    )
    audit = verify_contract_aligned_repair_forge_result(result)
    if audit["valid"] is not True:
        raise SystemExit("commissioned result failed verification: " + ",".join(audit["errors"]))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "state": result["state"],
                "corpus_hash": result["corpus_hash"],
                "result_hash": result["result_hash"],
                "model_calls": result["additional_model_calls"],
                "output": str(arguments.output),
            },
            indent=2,
        )
    )
    return 0 if result["state"] == "CONTRACT_ALIGNED_REPAIR_FORGE_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
