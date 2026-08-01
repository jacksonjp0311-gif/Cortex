"""v7.7.2 Epoch-Atomic Temporal Boundary release receipt."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from cortex import __version__  # noqa: E402
from version_gate import release_at_least  # noqa: E402


def _fh(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def main() -> int:
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    tests = [
        "tests/test_activation_fail_closed.py",
        "tests/test_resonant_frame_integration.py",
        "tests/test_self_sensing.py",
        "tests/test_phases.py",
    ]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v7.7.2-epoch-atomic-temporal-boundary",
        "version": __version__,
        "commit": commit,
        "at": time.time(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "test_totals": {
            "exit_code": result.returncode,
            "passed": result.returncode == 0,
            "summary": [line for line in output.splitlines() if line.strip()][-10:],
            "suite": tests,
        },
        "modules": {
            "activation.py": _fh(ROOT / "cortex/activation.py"),
            "resonant_frame.py": _fh(ROOT / "cortex/resonant_frame.py"),
            "self_sensing.py": _fh(ROOT / "cortex/self_sensing.py"),
        },
        "phase_doc_hash": _fh(
            ROOT
            / "docs/intelligence/PHASE_V7.7.2_EPOCH_ATOMIC_TEMPORAL_BOUNDARY.md"
        ),
        "finalization_order": [
            "close_parent_buffer",
            "seal_final_epoch",
            "bind_final_phase",
            "seed_final_epoch_frame",
            "observe_self",
        ],
        "identity_invariant": "body_epoch_id == phase_epoch_id == frame_epoch_id",
        "claim_boundary": (
            "Temporal boundary receipts remain advisory and never authorize host "
            "mutation, constitutional state, witness, or ARIA execution."
        ),
        "rollback_point": "v7.7.1",
    }
    material = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()
    output_dir = ROOT / "work"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "release_receipt_v772.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "path": str(path),
                "receipt_hash": receipt["receipt_hash"],
                "passed": result.returncode == 0,
                "version": __version__,
            },
            indent=2,
        )
    )
    if result.returncode != 0:
        print(output[-3000:], file=sys.stderr)
    return 0 if result.returncode == 0 and release_at_least(__version__, (7, 7, 2)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
