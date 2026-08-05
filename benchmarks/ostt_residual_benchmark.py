"""Deterministic v8.3.1 OSTT residual receipt benchmark."""

from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.ostt import OperatorContract  # noqa: E402
from cortex.ostt.residuals import (  # noqa: E402
    REQUIRED_COMPARISON_ARMS,
    REQUIRED_COMPARISON_MODES,
    ResidualReceipt,
    residual_evidence_report,
)


def _make_receipt(
    index: int,
    mode: str = "ostt",
    *,
    arm: str = "advanced",
    case_id: str = "case-bench",
    invariant_ok: bool = True,
) -> ResidualReceipt:
    base = [1.0 + index * 0.001, 2.0 - index * 0.001]
    observed = [base[0] + 0.01, base[1] - 0.01]
    return ResidualReceipt.measure(
        operator_id="scale_two",
        input_type="Vector2",
        output_type="Vector2",
        known_output=base,
        observed_output=observed,
        uncertainty=0.1,
        uncertainty_calibrated=True,
        invariant_projection={"ok": invariant_ok, "norm_bound": "finite"},
        validation={"independent_outcome": True},
        epoch_id="epoch-bench",
        cohort_id="cohort-bench",
        coordinate_schema_digest="schema-bench",
        repository_id="repo-bench",
        repo="BenchRepo",
        case_id=case_id,
        comparison_arm=arm,
        independent_witness=True,
        approximation_mode="exact",
        comparison_mode=mode,
    )


def main() -> int:
    contract = OperatorContract(
        "scale_two",
        "Vector2",
        "Vector2",
        ("typed",),
        ("observed",),
        ("finite",),
    )
    modes = tuple(sorted(REQUIRED_COMPARISON_MODES))
    samples: list[ResidualReceipt] = []
    timings: list[float] = []
    for index in range(256):
        started = time.perf_counter()
        samples.append(
            _make_receipt(
                index,
                modes[index % len(modes)],
                arm="advanced" if index % 2 == 0 else "evidence_baseline",
            )
        )
        timings.append((time.perf_counter() - started) * 1000.0)

    # Full paired comparison matrix for the review-gate surface.
    matrix_samples = [
        _make_receipt(0, mode, arm=arm)
        for arm in sorted(REQUIRED_COMPARISON_ARMS)
        for mode in modes
    ]
    report = residual_evidence_report((contract,), matrix_samples)
    try:
        ResidualReceipt.measure(
            operator_id="scale_two",
            input_type="Vector2",
            output_type="Vector2",
            known_output=[1.0, 2.0],
            observed_output={"not_numeric": "untyped"},
            uncertainty=0.1,
            uncertainty_calibrated=True,
            invariant_projection={"ok": True},
        )
        untyped_refusal = False
    except (TypeError, ValueError):
        untyped_refusal = True

    invariant_failure = residual_evidence_report(
        (contract,),
        [
            _make_receipt(0, mode, arm=arm, invariant_ok=False)
            for arm in sorted(REQUIRED_COMPARISON_ARMS)
            for mode in modes
        ],
    )
    type_failure = residual_evidence_report(
        (contract,),
        [
            ResidualReceipt.measure(
                operator_id="scale_two",
                input_type="WrongType",
                output_type="Vector2",
                known_output=[1.0, 2.0],
                observed_output=[1.01, 2.01],
                uncertainty=0.1,
                uncertainty_calibrated=True,
                invariant_projection={"ok": True},
                epoch_id="epoch-bench",
                cohort_id="cohort-bench",
                coordinate_schema_digest="schema-bench",
                repository_id="repo-bench",
                repo="BenchRepo",
                case_id="case-bench",
                comparison_arm="advanced",
                independent_witness=True,
            )
        ],
    )
    burdens = [float(receipt.burden or 0.0) for receipt in samples]
    checks = {
        "samples_256": len(samples) == 256,
        "bound_pass": max(burdens) < 1.0,
        "review_gates_ready": report["status"] == "ready_for_review",
        "untyped_refusal": untyped_refusal,
        "invariant_failure_blocked": not invariant_failure["gates"]["invariant_projection"],
        "type_failure_blocked": not type_failure["gates"]["typed_compatibility"],
        "shadow_only": report["policy_effect"] is False
        and report["update_authorized"] is False,
    }
    receipt = {
        "schema_version": "cortex-ostt-residual-benchmark/1.0",
        "samples": len(samples),
        "burden": {
            "mean": round(statistics.mean(burdens), 8),
            "p95": round(sorted(burdens)[int(0.95 * (len(burdens) - 1))], 8),
            "max": round(max(burdens), 8),
        },
        "latency_ms": {
            "median": round(statistics.median(timings), 4),
            "p95": round(sorted(timings)[int(0.95 * (len(timings) - 1))], 4),
        },
        "review": {
            "status": report["status"],
            "ready_count": report["ready_count"],
            "gates": report["gates"],
            "policy_effect": report["policy_effect"],
            "update_authorized": report["update_authorized"],
        },
        "checks": checks,
        "claim_boundary": report["claim_boundary"],
    }
    receipt["passed"] = all(checks.values())
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
