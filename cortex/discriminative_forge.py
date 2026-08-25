"""Deterministic, model-neutral development corpus for task calibration.

The forge creates exact-evaluator cases across multiple software-agent task
families.  Cases are calibration material and are permanently excluded from
confirmatory evidence.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any


SCHEMA_VERSION = "cortex-discriminative-forge/1.0"
VERSION = "9.8.1"
TASK_FAMILIES = (
    "repository_bug_localization",
    "multi_step_code_repair",
    "stale_state_detection",
    "api_migration",
    "architecture_reconstruction",
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _case(family: str, variant: int, prompt: str, answer: str) -> dict[str, Any]:
    material = {
        "family": family,
        "variant": int(variant),
        "difficulty_band": "development_calibration",
        "prompt": prompt,
        "evaluator": "normalized_exact_public_output",
        "expected_public_output": answer,
    }
    return {**material, "case_id": _sha(material), "answer_hash": _sha(answer)}


def build_discriminative_corpus(*, seed: str = "cortex-v981", variants_per_family: int = 4) -> dict[str, Any]:
    """Build a stable disposable corpus without provider or model semantics."""
    if variants_per_family < 2:
        raise ValueError("variants_per_family must be at least two")
    rng = random.Random(int(_sha(seed)[:16], 16))
    cases: list[dict[str, Any]] = []
    for variant in range(variants_per_family):
        modulus = rng.choice([97, 101, 127, 131])
        wrong_line = 4 + variant
        files = [f"module_{index}.py" for index in range(4)]
        target = files[(variant * 3 + 1) % len(files)]
        cases.append(_case(
            "repository_bug_localization", variant,
            f"Four modules implement x=(x*7+value) mod {modulus}. Only {target} line {wrong_line} uses *5. Return the unique defect as file:line.",
            f"{target}:{wrong_line}",
        ))

        start = rng.randrange(11, 40)
        values = [rng.randrange(2, 30) for _ in range(5 + variant)]
        expected = start
        for index, value in enumerate(values):
            expected = (expected + value * (index + 2)) % modulus
        cases.append(_case(
            "multi_step_code_repair", variant,
            f"Repair the accumulator conceptually: start={start}; for values={values}, update x=(x+value*(index+2)) mod {modulus}. Return the final decimal value.",
            str(expected),
        ))

        epoch = 6 + variant
        rows = [("m1", epoch - 1, "active"), ("m2", epoch, "active"), ("m1", epoch, "contested"), ("m3", epoch, "active"), ("m2", epoch + 1, "superseded")]
        active = sorted(identifier for identifier in {row[0] for row in rows} if next(row for row in reversed(rows) if row[0] == identifier)[1:] == (epoch, "active"))
        cases.append(_case(
            "stale_state_detection", variant,
            f"Ledger rows arrive in order {rows}. Latest row per ID wins. At current epoch {epoch}, return sorted comma-separated IDs whose latest row is exactly current and active.",
            ",".join(active) if active else "NONE",
        ))

        timeout = 20 + variant * 5
        cases.append(_case(
            "api_migration", variant,
            "Old API fetch(url, timeout, retries) became request(*, endpoint, retry_limit, timeout_ms). "
            f"Migrate fetch('/health', {timeout}, 2) and return only the new call, converting seconds to milliseconds.",
            f"request(endpoint='/health', retry_limit=2, timeout_ms={timeout * 1000})",
        ))

        dependencies = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"], "e": ["c"], "f": ["d", "e"]}
        order: list[str] = []
        remaining = set(dependencies)
        while remaining:
            ready = sorted(node for node in remaining if all(parent in order for parent in dependencies[node]))
            chosen = ready[-1] if (len(order) + variant) % 2 else ready[0]
            order.append(chosen)
            remaining.remove(chosen)
        cases.append(_case(
            "architecture_reconstruction", variant,
            f"Dependencies are {dependencies}. Repeatedly sort ready nodes; choose last when (output_position+{variant}) is odd, otherwise first. Return the concatenated order.",
            "".join(order),
        ))

    cases.sort(key=lambda row: (row["family"], row["variant"]))
    material = {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "seed_commitment": _sha(seed),
        "task_families": list(TASK_FAMILIES),
        "cases": cases,
        "development_only": True,
        "held_out": False,
        "confirmatory_eligible": False,
        "model_identity_in_ontology": False,
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }
    return {**material, "corpus_hash": _sha(material)}


def evaluate_case(case: dict[str, Any], public_output: str) -> bool:
    """Evaluate only the public answer; hidden reasoning is neither needed nor stored."""
    expected = " ".join(str(case["expected_public_output"]).strip().split())
    observed = " ".join(str(public_output).strip().split())
    return observed == expected


__all__ = ["SCHEMA_VERSION", "TASK_FAMILIES", "VERSION", "build_discriminative_corpus", "evaluate_case"]
