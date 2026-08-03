"""Deterministic v8.2.5 frequency-response benchmark."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import math  # noqa: E402
from cortex.resonance_sweep import frequency_sweep_report  # noqa: E402


def _frames(n: int = 32) -> list[dict[str, object]]:
    return [
        {"metrics": {
            "mean_activity": 0.5 + 0.4 * math.sin(2 * math.pi * i / n),
            "nonrandomness": 0.5 + 0.3 * math.sin(2 * math.pi * i / n),
            "evidence_participation": 0.4 + 0.2 * math.sin(2 * math.pi * i / n),
            "memory_participation": 0.4 + 0.2 * math.sin(2 * math.pi * i / n),
            "transition_pressure": 0.5 + 0.2 * math.sin(2 * math.pi * i / n),
            "participation_entropy": 0.5 + 0.1 * math.sin(2 * math.pi * i / n),
        }}
        for i in range(n)
    ]


def main() -> int:
    started = time.perf_counter()
    report = frequency_sweep_report(_frames(), frequencies=(0.5, 1.0, 2.0))
    checks = {
        "peak_at_one_cycle": (report.get("best") or {}).get("frequency") == 1.0,
        "resonant_candidate": report.get("status") == "resonant_candidate",
        "advisory_only": report.get("advisory_only") is True,
        "policy_inert": report.get("policy_effect") is False,
    }
    receipt = {
        "schema_version": "cortex-resonance-sweep-benchmark/1.0",
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 6),
        "checks": checks,
        "passed": all(checks.values()),
        "claim_boundary": report.get("claim_boundary"),
    }
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
