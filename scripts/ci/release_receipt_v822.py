"""v8.2.2 Query-Conditioned Bridge Trials release receipt."""

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
        [sys.executable, "-m", "pytest", "tests/test_bridge_trials.py", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    benchmark = subprocess.run(
        [sys.executable, "benchmarks/query_bridge_trial_benchmark.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    passed = tests.returncode == 0 and benchmark.returncode == 0
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v8.2.2-query-conditioned-bridge-trials",
        "version": __version__,
        "at": time.time(),
        "tests_passed": tests.returncode == 0,
        "benchmark_passed": benchmark.returncode == 0,
        "benchmark_hash": hashlib.sha256(benchmark.stdout.encode()).hexdigest(),
        "invariants": [
            "fixed_cardinality_counterfactual_arms",
            "relevance_bridge_novelty_hard_floors",
            "deterministic_random_control",
            "body_epoch_and_graph_context_bound",
            "live_results_and_policy_unchanged",
        ],
        "rollback_point": "v8.2.1",
        "claim_boundary": (
            "Bridge trials measure paired shadow retrieval utility; they do not "
            "alter live routing or establish consciousness."
        ),
    }
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True).encode()
    ).hexdigest()
    output = ROOT / "work" / "release_receipt_v822.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(output), "passed": passed, "receipt_hash": receipt["receipt_hash"]}, indent=2))
    if not passed:
        print(tests.stdout + tests.stderr, file=sys.stderr)
        print(benchmark.stdout + benchmark.stderr, file=sys.stderr)
    return 0 if passed and release_at_least(__version__, (8, 2, 2)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
