"""Deterministic v8.2.4 selective admission and attribution benchmark."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.source_admission import _selective_choice  # noqa: E402


def main() -> int:
    started = time.perf_counter()
    ambiguous = [
        ({"path": "cortex/a.py"}, {"path": "cortex/a.py", "triadic_alignment": 0.72, "eligible": True}),
        ({"path": "cortex/b.py"}, {"path": "cortex/b.py", "triadic_alignment": 0.70, "eligible": True}),
    ]
    decisive = [
        ({"path": "cortex/a.py"}, {"path": "cortex/a.py", "triadic_alignment": 0.78, "eligible": True}),
        ({"path": "cortex/b.py"}, {"path": "cortex/b.py", "triadic_alignment": 0.68, "eligible": True}),
    ]
    selected = _selective_choice(decisive)
    checks = {
        "ambiguous_abstains": _selective_choice(ambiguous) is None,
        "decisive_selects": selected is not None,
        "risk_proxy_bounded": selected is not None and 0.0 <= selected[1]["predicted_harm_risk"] <= 1.0,
        "shadow_only": selected is not None and selected[1]["shadow_only"] is True,
    }
    receipt = {
        "schema_version": "cortex-selective-admission-benchmark/1.0",
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 6),
        "checks": checks,
        "passed": all(checks.values()),
        "claim_boundary": "Selective admission is counterfactual, abstention-aware, and policy-inert.",
    }
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
