"""v8.2.6 Four-Dimensional Geometric Echo release receipt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from cortex import __version__  # noqa: E402
from version_gate import release_at_least  # noqa: E402


def main() -> int:
    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_geometric_echo.py", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    benchmark = subprocess.run(
        [sys.executable, "benchmarks/geometric_echo_benchmark.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    passed = tests.returncode == 0 and benchmark.returncode == 0
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v8.2.6-four-dimensional-geometric-echo",
        "version": __version__,
        "at": time.time(),
        "tests_passed": tests.returncode == 0,
        "benchmark_passed": benchmark.returncode == 0,
        "benchmark_hash": hashlib.sha256(benchmark.stdout.encode()).hexdigest(),
        "invariants": [
            "fixed_orthogonal_and_tetrahedral_pulses",
            "basis_echo_reconstruction_checked",
            "silent_axes_require_evidence_gate",
            "read_only_and_policy_inert",
            "no_cadence_routing_or_authority_mutation",
        ],
        "rollback_point": "v8.2.5",
        "claim_boundary": (
            "Pulse/echo alignment is operational telemetry, not consciousness, "
            "subjective sensing, or permission to mutate runtime behavior."
        ),
    }
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True).encode()
    ).hexdigest()
    output = ROOT / "work" / "release_receipt_v826.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(output), "passed": passed, "receipt_hash": receipt["receipt_hash"]}, indent=2))
    if not passed:
        print(tests.stdout + tests.stderr, file=sys.stderr)
        print(benchmark.stdout + benchmark.stderr, file=sys.stderr)
    return 0 if passed and release_at_least(__version__, (8, 2, 6)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
