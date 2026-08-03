"""Deterministic v8.2.7 rotation-alignment benchmark."""

from __future__ import annotations

import json
import time

from cortex.rotated_echo import rotated_echo_report


def main() -> int:
    started = time.perf_counter()
    report = rotated_echo_report({
        "state_vector": [0.6, 0.8, 0.0, 0.0],
        "active_axes": ["evidence", "geometry"],
    })
    checks = {
        "fixed_rotation_count": report.get("rotation_count") == 19,
        "aligned_subspace": report.get("status") == "aligned_subspace",
        "basis_reconstruction": all(
            item.get("reconstruction_error") == 0.0
            for item in report.get("rotations") or []
        ),
        "policy_inert": report.get("policy_effect") is False,
        "reversible_surgery": (report.get("surgery") or {}).get("reversible") is True,
    }
    receipt = {
        "schema_version": "cortex-rotated-echo-benchmark/1.0",
        "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 6),
        "checks": checks,
        "passed": all(checks.values()),
        "claim_boundary": report.get("claim_boundary"),
    }
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
