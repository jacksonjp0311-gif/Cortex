"""v8.2 Informational Interlocks release receipt."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from cortex import __version__  # noqa: E402
from version_gate import release_at_least  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"


def main() -> int:
    tests = [
        "tests/test_info_interlock.py",
        "tests/test_coherence.py",
        "tests/test_fusion_coprocess.py",
        "tests/test_ratio_lattice.py",
    ]
    test_run = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=line"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    benchmark_run = subprocess.run(
        [sys.executable, "benchmarks/informational_interlock_benchmark.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    try:
        benchmark = json.loads(benchmark_run.stdout or "{}")
    except json.JSONDecodeError:
        benchmark = {"parse_error": True}
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        commit = "unknown"
    passed = test_run.returncode == 0 and benchmark_run.returncode == 0
    output = (test_run.stdout or "") + (test_run.stderr or "")
    receipt = {
        "schema_version": "cortex-release-receipt/2.0",
        "release": "v8.2.0-informational-interlocks",
        "version": __version__,
        "commit": commit,
        "at": time.time(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "tests": {
            "passed": test_run.returncode == 0,
            "exit_code": test_run.returncode,
            "suite": tests,
            "summary": [line for line in output.splitlines() if line.strip()][-10:],
        },
        "benchmark": {
            "passed": benchmark_run.returncode == 0,
            "exit_code": benchmark_run.returncode,
            "receipt": benchmark,
            "output_hash": hashlib.sha256((benchmark_run.stdout or "").encode()).hexdigest(),
        },
        "module_hashes": {
            path.name: _hash(path)
            for path in (
                ROOT / "cortex/math_net/info_interlock.py",
                ROOT / "cortex/store.py",
                ROOT / "cortex/retrieval.py",
                ROOT / "cortex/structure_invent.py",
            )
        },
        "phase_doc_hash": _hash(
            ROOT / "docs/intelligence/PHASE_V8.2_INFORMATIONAL_INTERLOCKS.md"
        ),
        "invariants": [
            "outcomes_are_independently_bound",
            "constitutional_gate_is_hard_zero",
            "incompatible_measurement_cohorts_are_excluded",
            "compatible_adaptive_epochs_remain_auditable",
            "route_metadata_cannot_reorder",
            "complete_graph_is_release_reference",
            "interlock_policy_remains_shadow",
        ],
        "claim_boundary": (
            "v8.2 measures typed E-L-O informational organization. It does not "
            "establish consciousness, subjective sensing, or mutation authority."
        ),
        "rollback_point": "v8.1.1",
    }
    receipt["receipt_hash"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, default=str).encode()
    ).hexdigest()
    output_dir = ROOT / "work"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "release_receipt_v820.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({
        "path": str(path),
        "receipt_hash": receipt["receipt_hash"],
        "passed": passed,
        "version": __version__,
    }, indent=2))
    if not passed:
        print((output + benchmark_run.stdout + benchmark_run.stderr)[-4000:], file=sys.stderr)
    return 0 if passed and release_at_least(__version__, (8, 2, 0)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
