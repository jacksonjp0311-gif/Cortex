"""v8.2.4 Selective Admission and Ranker Attribution release receipt."""

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
        [sys.executable, "-m", "pytest", "tests/test_source_admission.py", "-q"],
        cwd=ROOT, capture_output=True, text=True,
    )
    benchmark = subprocess.run(
        [sys.executable, "benchmarks/selective_admission_benchmark.py"],
        cwd=ROOT, capture_output=True, text=True,
    )
    passed = tests.returncode == 0 and benchmark.returncode == 0
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v8.2.4-selective-admission-ranker-attribution",
        "version": __version__,
        "at": time.time(),
        "tests_passed": tests.returncode == 0,
        "benchmark_passed": benchmark.returncode == 0,
        "benchmark_hash": hashlib.sha256(benchmark.stdout.encode()).hexdigest(),
        "invariants": [
            "ambiguous_candidates_abstain",
            "ranker_and_candidate_stages_measured_separately",
            "risk_proxy_is_bounded_and_shadow_only",
            "three_distinct_context_replication_required",
            "live_results_and_policy_unchanged",
        ],
        "rollback_point": "v8.2.3",
        "claim_boundary": (
            "Selective admission measures shadow routing utility and ranker loss; "
            "it does not alter live routing or establish consciousness."
        ),
    }
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True).encode()
    ).hexdigest()
    output = ROOT / "work" / "release_receipt_v824.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({"path": str(output), "passed": passed, "receipt_hash": receipt["receipt_hash"]}, indent=2))
    if not passed:
        print(tests.stdout + tests.stderr, file=sys.stderr)
        print(benchmark.stdout + benchmark.stderr, file=sys.stderr)
    return 0 if passed and release_at_least(__version__, (8, 2, 4)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
