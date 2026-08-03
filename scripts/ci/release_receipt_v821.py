"""v8.2.1 Geometric Bridge Field release receipt."""

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
    test_run = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_info_interlock.py",
            "tests/test_interconnect_continuity.py",
            "-q",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    bench_run = subprocess.run(
        [sys.executable, "benchmarks/geometric_bridge_benchmark.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    passed = test_run.returncode == 0 and bench_run.returncode == 0
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v8.2.1-geometric-bridge-field",
        "version": __version__,
        "at": time.time(),
        "tests_passed": test_run.returncode == 0,
        "benchmark_passed": bench_run.returncode == 0,
        "benchmark_hash": hashlib.sha256((bench_run.stdout or "").encode()).hexdigest(),
        "invariants": [
            "bridge_score_balances_openness_reach_diversity_nonhub",
            "bridge_metadata_is_post_ranking",
            "route_score_and_order_are_unchanged",
            "policy_effect_is_false",
        ],
        "rollback_point": "v8.2.0",
        "claim_boundary": (
            "Bridge potential is shadow structural telemetry, not proven task utility, "
            "consciousness, or mutation authority."
        ),
    }
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True).encode()
    ).hexdigest()
    output_dir = ROOT / "work"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "release_receipt_v821.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(path), "passed": passed, "receipt_hash": receipt["receipt_hash"]}, indent=2))
    if not passed:
        print((test_run.stdout or "") + (test_run.stderr or ""), file=sys.stderr)
        print((bench_run.stdout or "") + (bench_run.stderr or ""), file=sys.stderr)
    return 0 if passed and release_at_least(__version__, (8, 2, 1)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
