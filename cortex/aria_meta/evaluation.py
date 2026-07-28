"""Evaluation for native ARIA wake routing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .substrate import classify_aria_task


def load_aria_corpus(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("cases", payload)
    if not isinstance(cases, list):
        raise ValueError("ARIA evaluation corpus must contain a case list")
    return cases


def evaluate_aria_corpus(
    cases: Iterable[dict[str, Any]],
    learned_cues: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    false_wakes = 0
    missed_wakes = 0
    purpose_misses = 0
    for case in cases:
        classification = classify_aria_task(
            str(case["task"]), learned_cues
        )
        expected_mode = str(case["expected_mode"])
        expected_purposes = set(case.get("expected_purposes", []))
        actual_purposes = set(classification["purposes"])
        false_wake = expected_mode == "dormant" and classification["mode"] == "active"
        missed_wake = expected_mode == "active" and classification["mode"] == "dormant"
        purpose_miss = not expected_purposes.issubset(actual_purposes)
        false_wakes += int(false_wake)
        missed_wakes += int(missed_wake)
        purpose_misses += int(purpose_miss)
        results.append(
            {
                "id": case.get("id"),
                "task": case["task"],
                "expected_mode": expected_mode,
                "actual_mode": classification["mode"],
                "expected_purposes": sorted(expected_purposes),
                "actual_purposes": classification["purposes"],
                "passed": not (false_wake or missed_wake or purpose_miss),
                "decision_rule": classification["decision_rule"],
            }
        )
    total = len(results)
    passed = sum(result["passed"] for result in results)
    return {
        "schema_version": "cortex-aria-fluency-evaluation/1.0",
        "cases": total,
        "passed": passed,
        "pass_rate": round(passed / total, 6) if total else 0.0,
        "false_wakes": false_wakes,
        "missed_wakes": missed_wakes,
        "purpose_misses": purpose_misses,
        "results": results,
        "claim_boundary": (
            "This fixed corpus measures declared wake-routing behavior only; "
            "it does not prove general language understanding."
        ),
    }


__all__ = ["evaluate_aria_corpus", "load_aria_corpus"]
