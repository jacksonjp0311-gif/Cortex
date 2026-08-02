"""v7.8.1 Truth Recovery release receipt."""

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
    tests = [
        "tests/test_self_sensing.py",
        "tests/test_binding_field.py",
        "tests/test_resonant_frame_math.py",
        "tests/test_resonant_frame_integration.py",
        "tests/test_field_policy.py",
        "tests/test_field_receipt.py",
        "tests/test_epoch.py",
    ]
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v7.8.1-truth-recovery",
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
            name: _fh(ROOT / "cortex" / name)
            for name in (
                "field_channels.py",
                "resonant_frame.py",
                "self_sensing.py",
                "binding_field.py",
                "field_policy.py",
                "epoch.py",
            )
        },
        "phase_doc_hash": _fh(
            ROOT / "docs/intelligence/PHASE_V7.8.1_TRUTH_RECOVERY.md"
        ),
        "invariants": [
            "classify_against_prior_baseline",
            "modeled_salience_is_shadow_only",
            "drift_and_transition_are_not_verified",
            "epoch_changes_are_attributable",
        ],
        "claim_boundary": (
            "Truth Recovery is advisory telemetry and grants no capability, "
            "constitutional authority, witness, host mutation, or ARIA execution."
        ),
        "rollback_point": "v7.8.0",
    }
    material = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()
    output_dir = ROOT / "work"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "release_receipt_v781.json"
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
    return 0 if result.returncode == 0 and release_at_least(__version__, (7, 8, 1)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
