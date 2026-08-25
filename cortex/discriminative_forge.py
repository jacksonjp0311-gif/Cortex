"""Deterministic, model-neutral development corpus for task calibration.

The forge creates exact-evaluator cases across multiple software-agent task
families.  Cases are calibration material and are permanently excluded from
confirmatory evidence.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping
from typing import Any

from .information_calibration import verify_difficulty_calibration


SCHEMA_VERSION = "cortex-discriminative-forge/1.1"
VERSION = "9.8.2"
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

        epoch = 6 + variant + rng.randrange(0, 7)
        suffix = rng.randrange(10, 99)
        names = [f"m{index}_{suffix}" for index in range(1, 4)]
        rows = [(names[0], epoch - 1, "active"), (names[1], epoch, "active"), (names[0], epoch, "contested"), (names[2], epoch, "active"), (names[1], epoch + 1, "superseded")]
        active = sorted(identifier for identifier in {row[0] for row in rows} if next(row for row in reversed(rows) if row[0] == identifier)[1:] == (epoch, "active"))
        cases.append(_case(
            "stale_state_detection", variant,
            f"Ledger rows arrive in order {rows}. Latest row per ID wins. At current epoch {epoch}, return sorted comma-separated IDs whose latest row is exactly current and active.",
            ",".join(active) if active else "NONE",
        ))

        timeout = 20 + variant * 5 + rng.randrange(1, 10)
        retries = rng.randrange(1, 5)
        endpoint = f"/health/{rng.randrange(100, 999)}"
        cases.append(_case(
            "api_migration", variant,
            "Old API fetch(url, timeout, retries) became request(*, endpoint, retry_limit, timeout_ms). "
            f"Migrate fetch('{endpoint}', {timeout}, {retries}) and return only the new call, converting seconds to milliseconds.",
            f"request(endpoint='{endpoint}', retry_limit={retries}, timeout_ms={timeout * 1000})",
        ))

        tag = rng.randrange(10, 99)
        node = {name: f"{name}{tag}" for name in "abcdef"}
        dependencies = {node["a"]: [], node["b"]: [node["a"]], node["c"]: [node["a"]], node["d"]: [node["b"], node["c"]], node["e"]: [node["c"]], node["f"]: [node["d"], node["e"]]}
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


def build_difficulty_ladder_corpus(
    *,
    seed: str = "cortex-v982-development",
    maximum_level: int = 4,
    variants_per_level: int = 4,
) -> dict[str, Any]:
    """Create increasingly composed development tasks for empirical calibration."""
    if maximum_level < 1 or variants_per_level < 2:
        raise ValueError("difficulty ladder requires at least one level and two variants")
    cases: list[dict[str, Any]] = []
    for level in range(1, maximum_level + 1):
        for variant in range(variants_per_level):
            components: dict[str, list[dict[str, Any]]] = {family: [] for family in TASK_FAMILIES}
            for part in range(level):
                component_corpus = build_discriminative_corpus(
                    seed=f"{seed}:level={level}:variant={variant}:part={part}",
                    variants_per_family=max(2, variant + 2),
                )
                for family in TASK_FAMILIES:
                    family_cases = [row for row in component_corpus["cases"] if row["family"] == family]
                    components[family].append(family_cases[variant % len(family_cases)])
            for family, rows in components.items():
                prompt = " Solve each independent subcase and return answers joined by | in order. ".join(
                    f"Subcase {index + 1}: {row['prompt']}" for index, row in enumerate(rows)
                )
                answer = "|".join(str(row["expected_public_output"]) for row in rows)
                material = {
                    "family": family,
                    "difficulty_level": level,
                    "variant": variant,
                    "difficulty_mechanism": "composed_exact_subcases",
                    "component_case_ids": [row["case_id"] for row in rows],
                    "prompt": prompt,
                    "evaluator": "normalized_exact_public_output",
                    "expected_public_output": answer,
                }
                cases.append({**material, "case_id": _sha(material), "answer_hash": _sha(answer)})
    cases.sort(key=lambda row: (row["family"], row["difficulty_level"], row["variant"]))
    material = {
        "schema_version": "cortex-difficulty-ladder-corpus/1.0",
        "version": "9.8.2",
        "seed_commitment": _sha(seed),
        "task_families": list(TASK_FAMILIES),
        "maximum_level": int(maximum_level),
        "variants_per_level": int(variants_per_level),
        "cases": cases,
        "development_only": True,
        "held_out": False,
        "confirmatory_eligible": False,
        "model_identity_in_ontology": False,
    }
    return {**material, "corpus_hash": _sha(material)}


def build_held_out_bundle(
    calibration: Mapping[str, Any],
    development_corpus: Mapping[str, Any],
    *,
    secret_seed: str,
    cases_per_family: int = 8,
) -> dict[str, Any]:
    """Create a disjoint public manifest and private exact-evaluator key."""
    verification = verify_difficulty_calibration(calibration)
    if not verification["valid"]:
        raise ValueError(f"difficulty calibration is invalid: {verification['errors']}")
    selected = calibration.get("selected")
    if calibration.get("overall_state") != "pass" or not isinstance(selected, Mapping) or not selected:
        raise ValueError("every declared family must have an informative selected level")
    max_level = max(int(row["difficulty_level"]) for row in selected.values())
    generated = build_difficulty_ladder_corpus(
        seed=f"heldout:{secret_seed}", maximum_level=max_level, variants_per_level=cases_per_family
    )
    development_ids = {str(row["case_id"]) for row in development_corpus.get("cases") or []}
    chosen = [
        row for row in generated["cases"]
        if row["family"] in selected
        and int(row["difficulty_level"]) == int(selected[row["family"]]["difficulty_level"])
    ]
    if any(str(row["case_id"]) in development_ids for row in chosen):
        raise ValueError("held-out corpus overlaps development cases")
    answer_key = {str(row["case_id"]): str(row["expected_public_output"]) for row in chosen}
    public_cases = [
        {str(key): value for key, value in row.items() if str(key) != "expected_public_output"}
        for row in chosen
    ]
    key_material = {"answers": answer_key, "secret_seed_commitment": _sha(secret_seed)}
    public_material = {
        "schema_version": "cortex-heldout-corpus-seal/1.0",
        "version": "9.8.2",
        "source_calibration_hash": calibration["calibration_hash"],
        "development_corpus_hash": development_corpus.get("corpus_hash"),
        "secret_seed_commitment": _sha(secret_seed),
        "answer_key_commitment": _sha(key_material),
        "selected_levels": {str(name): str(row["difficulty_level"]) for name, row in sorted(selected.items())},
        "cases": public_cases,
        "case_count": len(public_cases),
        "held_out": True,
        "development_only": False,
        "eligible_for_preregistration": True,
        "confirmatory_evidence": False,
        "answers_present_in_public_manifest": False,
        "authority": {
            "host_mutate_authorized": False,
            "execution_authorized": False,
            "memory_admission_authorized": False,
            "policy_effect": False,
        },
    }
    manifest = {**public_material, "corpus_hash": _sha(public_material)}
    return {"manifest": manifest, "answer_key": key_material}


def verify_held_out_bundle(bundle: Mapping[str, Any]) -> dict[str, Any]:
    manifest = bundle.get("manifest")
    answer_key = bundle.get("answer_key")
    errors: list[str] = []
    if not isinstance(manifest, Mapping) or not isinstance(answer_key, Mapping):
        return {"valid": False, "state": "fail", "errors": ["bundle_shape_invalid"]}
    manifest_check = verify_held_out_manifest(manifest)
    errors.extend(manifest_check["errors"])
    if manifest.get("answer_key_commitment") != _sha(answer_key):
        errors.append("answer_key_commitment_invalid")
    public_cases = manifest.get("cases") or []
    if any("expected_public_output" in row for row in public_cases):
        errors.append("answer_leaked_into_public_manifest")
    public_ids = {str(row.get("case_id") or "") for row in public_cases}
    answer_ids = {str(key) for key in (answer_key.get("answers") or {})}
    if public_ids != answer_ids:
        errors.append("answer_key_case_binding_invalid")
    return {"valid": not errors, "state": "pass" if not errors else "fail", "errors": errors}


def verify_held_out_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Verify the public seal without revealing or requiring the private key."""
    errors: list[str] = []
    public_material = {str(key): value for key, value in manifest.items() if str(key) != "corpus_hash"}
    if manifest.get("schema_version") != "cortex-heldout-corpus-seal/1.0":
        errors.append("schema_version_invalid")
    if manifest.get("corpus_hash") != _sha(public_material):
        errors.append("corpus_hash_invalid")
    public_cases = manifest.get("cases") or []
    if any("expected_public_output" in row for row in public_cases):
        errors.append("answer_leaked_into_public_manifest")
    allowed_manifest_keys = {
        "schema_version", "version", "source_calibration_hash", "development_corpus_hash",
        "secret_seed_commitment", "answer_key_commitment", "selected_levels", "cases",
        "case_count", "held_out", "development_only", "eligible_for_preregistration",
        "confirmatory_evidence", "answers_present_in_public_manifest", "authority", "corpus_hash",
    }
    if set(str(key) for key in manifest) != allowed_manifest_keys:
        errors.append("manifest_schema_not_closed")
    allowed_case_keys = {
        "family", "difficulty_level", "variant", "difficulty_mechanism",
        "component_case_ids", "prompt", "evaluator", "case_id", "answer_hash",
    }
    if any(set(str(key) for key in row) != allowed_case_keys for row in public_cases):
        errors.append("public_case_schema_not_closed")
    if manifest.get("held_out") is not True or manifest.get("eligible_for_preregistration") is not True:
        errors.append("heldout_boundary_invalid")
    if manifest.get("confirmatory_evidence") is not False:
        errors.append("unexecuted_corpus_claim_invalid")
    return {"valid": not errors, "state": "pass" if not errors else "fail", "errors": errors}


__all__ = [
    "SCHEMA_VERSION",
    "TASK_FAMILIES",
    "VERSION",
    "build_difficulty_ladder_corpus",
    "build_discriminative_corpus",
    "build_held_out_bundle",
    "evaluate_case",
    "verify_held_out_bundle",
    "verify_held_out_manifest",
]
