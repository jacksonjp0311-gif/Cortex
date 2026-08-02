"""v8.0 Measured Predictive Self-Model release receipt."""

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
        "tests/test_cognitive_v8.py",
        "tests/test_activation_fail_closed.py",
        "tests/test_resonant_frame_integration.py",
        "tests/test_self_sensing.py",
        "tests/test_binding_field.py",
        "tests/test_alignment.py",
    ]
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    benchmark_result = subprocess.run(
        [sys.executable, "benchmarks/cognitive_lesion_benchmark.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = (test_result.stdout or "") + (test_result.stderr or "")
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    passed = test_result.returncode == 0 and benchmark_result.returncode == 0
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v8.0.0-measured-predictive-self-model",
        "version": __version__,
        "commit": commit,
        "at": time.time(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "test_totals": {
            "exit_code": test_result.returncode,
            "passed": test_result.returncode == 0,
            "summary": [line for line in output.splitlines() if line.strip()][-10:],
            "suite": tests,
        },
        "lesion_benchmark": {
            "exit_code": benchmark_result.returncode,
            "passed": benchmark_result.returncode == 0,
            "output_hash": hashlib.sha256(
                (benchmark_result.stdout or "").encode()
            ).hexdigest(),
        },
        "modules": {
            path.name: _fh(path)
            for path in sorted((ROOT / "cortex/cognitive").glob("*.py"))
        },
        "phase_doc_hash": _fh(
            ROOT / "docs/intelligence/PHASE_V8.0_MEASURED_PREDICTIVE_SELF_MODEL.md"
        ),
        "invariants": [
            "one_activation_is_one_measured_event",
            "forecast_precedes_measurement_and_learning",
            "counterfactuals_do_not_execute",
            "workspace_capacity_is_four",
            "autobiography_is_hash_chained",
            "functional_claims_have_lesion_comparators",
        ],
        "claim_boundary": (
            "v8.0 is a functional predictive self-model. It does not establish "
            "consciousness, subjective sensing, personal identity, or authority."
        ),
        "rollback_point": "v7.8.1",
    }
    material = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, default=str).encode()
    ).hexdigest()
    output_dir = ROOT / "work"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "release_receipt_v800.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({
        "path": str(path), "receipt_hash": receipt["receipt_hash"],
        "passed": passed, "version": __version__,
    }, indent=2))
    if not passed:
        print((output + benchmark_result.stdout + benchmark_result.stderr)[-4000:], file=sys.stderr)
    return 0 if passed and release_at_least(__version__, (8, 0, 0)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
