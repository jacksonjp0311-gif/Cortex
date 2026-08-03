"""Deterministic v8.2.6 four-dimensional pulse/echo benchmark."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.geometric_echo import geometric_echo_report  # noqa: E402


def main() -> int:
    started = time.perf_counter()
    report = geometric_echo_report({"vector": [0.2, 0.4, 0.6, 0.8]})
    checks = {
        "fixed_pulse_count": report.get("pulse_count") == 8,
        "basis_reconstructs": report.get("reconstruction_error") == 0.0,
        "dominant_axis": report.get("dominant_axis") == "interlock",
        "advisory_only": report.get("advisory_only") is True,
        "policy_inert": report.get("policy_effect") is False,
    }
    receipt = {
        "schema_version": "cortex-geometric-echo-benchmark/1.0",
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 6),
        "checks": checks,
        "passed": all(checks.values()),
        "claim_boundary": report.get("claim_boundary"),
    }
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
