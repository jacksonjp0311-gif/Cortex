"""Contract-aligned external-private executable repair calibration.

The public contract names every behavior that a host-private assertion may
measure.  Hidden inputs remain private, but hidden semantics fail closed before
an evaluator can be commissioned.  This is a structural host-authored
alignment proof, not semantic entailment or model-performance evidence.
"""

from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .executable_repair_forge import (
    build_executable_repair_bundle,
    commission_executable_repair_forge,
    verify_executable_repair_bundle,
    verify_executable_repair_forge_result,
    evaluate_executable_patch,
)

PUBLIC_SCHEMA = "cortex-contract-aligned-repair-corpus/1.0"
PRIVATE_SCHEMA = "cortex-contract-aligned-repair-private/1.0"
RESULT_SCHEMA = "cortex-alpha36-contract-aligned-repair-forge/1.0"
CLAIM_BOUNDARY = (
    "Every host-private executable assertion is structurally mapped to an explicit "
    "public requirement. The mapping is host-authored and does not itself prove "
    "semantic entailment, model repair ability, or improvement. Zero model calls execute."
)


def audit_contract_aligned_controls(
    public: Mapping[str, Any], private: Mapping[str, Any],
    controls: Mapping[str, Sequence[Mapping[str, Any]]], root: Path,
) -> dict[str, Any]:
    """Challenge an evaluator using alternate allowed implementations and mutants.

    Expected labels are host judgments, not semantic proof. A passing reference
    alone cannot compensate for a rejected alternate or an accepted mutant.
    This local instrument audit does not produce empirical model evidence.
    """
    executable, secrets = executable_bundle_from_contract_aligned(public, private)
    public_cases = {case["case_id"]: case for case in executable["cases"]}
    private_cases = {case["case_id"]: case for case in secrets["cases"]}
    if not controls or set(controls) - set(public_cases):
        raise ValueError("controls require known case identities")
    # Validate the entire panel before executing any candidate program.
    for rows in controls.values():
        if (
            any(set(row) != {"control_id", "patch", "expected_pass"} for row in rows)
            or any(type(row["expected_pass"]) is not bool or not isinstance(row["patch"], str) for row in rows)
            or len({row["control_id"] for row in rows}) != len(rows)
            or len({row["patch"] for row in rows if row["expected_pass"]}) < 2
            or not any(not row["expected_pass"] for row in rows)
        ):
            raise ValueError("each panel needs two distinct allowed repairs and a negative control")
    observations = []
    for case_id, rows in controls.items():
        for row in rows:
            result = evaluate_executable_patch(
                public_cases[case_id], private_cases[case_id], row["patch"],
                root / f"control-{len(observations)}",
            )
            observations.append({
                "case_id": case_id, "control_id": row["control_id"],
                "patch_hash": _sha(row["patch"]),
                "expected_pass": row["expected_pass"],
                "observed_pass": result["candidate_pass"],
                "expectation_met": result["candidate_pass"] is row["expected_pass"],
                "evaluation_hash": result["evaluation_hash"],
            })
    report = {
        "schema_version": "cortex-evaluator-control-audit/1.0",
        "state": "CONTROL_PANEL_PASS" if all(row["expectation_met"] for row in observations) else "EVALUATOR_CHALLENGED",
        "corpus_hash": public["corpus_hash"],
        "evaluator_commitments": {case_id: public_cases[case_id]["private_evaluator_commitment"] for case_id in controls},
        "observations": observations, "additional_model_calls": 0,
        "evidence_class": "local_instrument_audit",
        "expected_labels": "host_reviewed_not_semantically_proven",
        "universal_implementation_equivalence": False,
        "semantic_transfer_established": False, "general_improvement_established": False,
        "host_mutate_authorized": False, "execution_authorized": False,
        "memory_admission_authorized": False, "policy_effect": False,
    }
    report["result_hash"] = _sha(report)
    return report


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _parse_statements(source: str, *, field: str) -> ast.Module:
    try:
        return ast.parse(source, filename=f"<{field}>", mode="exec")
    except SyntaxError as exc:
        raise ValueError(f"{field} must be valid Python") from exc


def _public_task(requirements: Sequence[Mapping[str, str]]) -> str:
    lines = [
        "Repair module.py so it satisfies every public requirement below.",
        "Preserve public signatures unless a requirement explicitly says otherwise.",
        "",
    ]
    lines.extend(f"[{item['requirement_id']}] {item['text']}" for item in requirements)
    return "\n".join(lines)


def _validate_case_spec(raw: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    required = {
        "case_id",
        "source",
        "requirements",
        "private_setup",
        "private_assertions",
        "patch",
    }
    if set(raw) != required:
        raise ValueError("each aligned case must contain exactly the required fields")
    for field in ("case_id", "source", "patch"):
        if not isinstance(raw[field], str) or not raw[field]:
            raise ValueError(f"{field} must be a non-empty string")
    if not isinstance(raw["private_setup"], str):
        raise ValueError("private_setup must be a string")

    requirements_raw = raw["requirements"]
    if not isinstance(requirements_raw, list) or not requirements_raw:
        raise ValueError("at least one public requirement is required")
    requirements: list[dict[str, str]] = []
    requirement_ids: set[str] = set()
    for item in requirements_raw:
        if not isinstance(item, Mapping) or set(item) != {"requirement_id", "text"}:
            raise ValueError("public requirements require exactly requirement_id and text")
        requirement_id = item.get("requirement_id")
        text = item.get("text")
        if not isinstance(requirement_id, str) or not requirement_id or requirement_id in requirement_ids:
            raise ValueError("public requirement IDs must be non-empty and unique")
        if not isinstance(text, str) or not text:
            raise ValueError("public requirement text must be non-empty")
        requirement_ids.add(requirement_id)
        requirements.append({"requirement_id": requirement_id, "text": text})

    setup_tree = _parse_statements(raw["private_setup"], field="private_setup")
    if any(isinstance(node, (ast.Assert, ast.Raise)) for node in ast.walk(setup_tree)):
        raise ValueError("private_setup may prepare inputs but may not contain assertions or raises")

    assertions_raw = raw["private_assertions"]
    if not isinstance(assertions_raw, list) or not assertions_raw:
        raise ValueError("at least one private assertion is required")
    assertions: list[dict[str, Any]] = []
    assertion_ids: set[str] = set()
    covered: set[str] = set()
    for item in assertions_raw:
        if not isinstance(item, Mapping) or set(item) != {"assertion_id", "requirement_ids", "code"}:
            raise ValueError("private assertions require assertion_id, requirement_ids, and code")
        assertion_id = item.get("assertion_id")
        requirement_refs = item.get("requirement_ids")
        code = item.get("code")
        if not isinstance(assertion_id, str) or not assertion_id or assertion_id in assertion_ids:
            raise ValueError("private assertion IDs must be non-empty and unique")
        if (
            not isinstance(requirement_refs, list)
            or not requirement_refs
            or any(not isinstance(ref, str) for ref in requirement_refs)
            or len(set(requirement_refs)) != len(requirement_refs)
        ):
            raise ValueError("each private assertion requires unique public requirement references")
        unknown = set(requirement_refs) - requirement_ids
        if unknown:
            raise ValueError("private assertion references an unknown public requirement")
        if not isinstance(code, str) or not code:
            raise ValueError("private assertion code must be non-empty")
        tree = _parse_statements(code, field=f"assertion:{assertion_id}")
        if not any(isinstance(node, ast.Assert) for node in ast.walk(tree)):
            raise ValueError("each private assertion must contain an explicit assert statement")
        assertion_ids.add(assertion_id)
        covered.update(requirement_refs)
        assertions.append(
            {
                "assertion_id": assertion_id,
                "requirement_ids": list(requirement_refs),
                "code": code,
            }
        )
    if covered != requirement_ids:
        raise ValueError("every public requirement must be covered by a private assertion")
    return requirements, assertions


def _external_test(setup: str, assertions: Sequence[Mapping[str, Any]]) -> str:
    chunks = [setup.rstrip(), ""]
    for assertion in assertions:
        refs = ",".join(str(value) for value in assertion["requirement_ids"])
        chunks.extend(
            (
                f"# {assertion['assertion_id']} -> {refs}",
                str(assertion["code"]).rstrip(),
                "",
            )
        )
    return "\n".join(chunks).rstrip() + "\n"


def build_contract_aligned_repair_bundle(
    *, secret_seed: str, case_specs: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build dual public/private representations with explicit requirement coverage."""
    if not secret_seed:
        raise ValueError("a non-empty host secret seed is required")
    if not case_specs:
        raise ValueError("host-private aligned case specifications are required")

    normalized: list[dict[str, Any]] = []
    executable_specs: list[dict[str, str]] = []
    for raw in case_specs:
        if not isinstance(raw, Mapping):
            raise ValueError("each aligned case must be an object")
        requirements, assertions = _validate_case_spec(raw)
        task = _public_task(requirements)
        external_test = _external_test(str(raw["private_setup"]), assertions)
        executable_specs.append(
            {
                "case_id": str(raw["case_id"]),
                "task": task,
                "source": str(raw["source"]),
                "test": external_test,
                "patch": str(raw["patch"]),
            }
        )
        normalized.append(
            {
                "case_id": str(raw["case_id"]),
                "requirements": requirements,
                "assertions": assertions,
                "private_setup": str(raw["private_setup"]),
            }
        )

    executable_public, executable_private = build_executable_repair_bundle(
        secret_seed=secret_seed,
        case_specs=executable_specs,
    )
    public_cases: list[dict[str, Any]] = []
    private_cases: list[dict[str, Any]] = []
    executable_public_by_id = {case["case_id"]: case for case in executable_public["cases"]}
    for case in normalized:
        case_id = case["case_id"]
        requirement_commitment = _sha(case["requirements"])
        alignment_body = {
            "case_id": case_id,
            "requirements": case["requirements"],
            "assertion_mappings": [
                {
                    "assertion_id": assertion["assertion_id"],
                    "requirement_ids": assertion["requirement_ids"],
                }
                for assertion in case["assertions"]
            ],
            "private_setup": case["private_setup"],
            "private_assertions": case["assertions"],
        }
        alignment_salt = _sha({"seed": secret_seed, "case_id": case_id, "kind": "alignment"})
        public_cases.append(
            {
                "case_id": case_id,
                "requirements": case["requirements"],
                "requirement_commitment": requirement_commitment,
                "assertion_count": len(case["assertions"]),
                "alignment_commitment": _sha(
                    {"salt": alignment_salt, "alignment": alignment_body}
                ),
                "executable_case": executable_public_by_id[case_id],
            }
        )
        private_cases.append(
            {
                "case_id": case_id,
                "alignment_salt": alignment_salt,
                "alignment": alignment_body,
            }
        )

    public: dict[str, Any] = {
        "schema_version": PUBLIC_SCHEMA,
        "development_only": True,
        "case_count": len(public_cases),
        "cases": public_cases,
        "executable_corpus_hash": executable_public["corpus_hash"],
        "private_assertions_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    public["corpus_hash"] = _sha(public)
    private: dict[str, Any] = {
        "schema_version": PRIVATE_SCHEMA,
        "corpus_hash": public["corpus_hash"],
        "cases": private_cases,
        "executable_private_bundle": executable_private,
    }
    private["private_bundle_hash"] = _sha(private)
    return public, private


def verify_contract_aligned_repair_bundle(
    public: Mapping[str, Any], private: Mapping[str, Any]
) -> dict[str, Any]:
    errors: list[str] = []
    public_body = {key: value for key, value in public.items() if key != "corpus_hash"}
    private_body = {key: value for key, value in private.items() if key != "private_bundle_hash"}
    if public.get("schema_version") != PUBLIC_SCHEMA or public.get("corpus_hash") != _sha(public_body):
        errors.append("public_identity_invalid")
    if private.get("schema_version") != PRIVATE_SCHEMA or private.get("private_bundle_hash") != _sha(private_body):
        errors.append("private_identity_invalid")
    if private.get("corpus_hash") != public.get("corpus_hash"):
        errors.append("corpus_binding_invalid")

    public_cases = {
        str(case.get("case_id")): case
        for case in public.get("cases", [])
        if isinstance(case, Mapping)
    }
    private_cases = {
        str(case.get("case_id")): case
        for case in private.get("cases", [])
        if isinstance(case, Mapping)
    }
    if (
        set(public_cases) != set(private_cases)
        or len(public_cases) != public.get("case_count")
        or len(public_cases) != len(public.get("cases", []))
        or len(private_cases) != len(private.get("cases", []))
    ):
        errors.append("case_identity_invalid")

    executable_public = {
        "schema_version": "cortex-executable-repair-corpus/1.0",
        "development_only": True,
        "case_count": len(public_cases),
        "cases": [case.get("executable_case") for case in public.get("cases", [])],
        "private_tests_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "claim_boundary": (
            "A zero-call development forge with reference-patch discriminability. "
            "No model repair ability, general improvement, or mutation authority is established."
        ),
    }
    executable_public["corpus_hash"] = str(public.get("executable_corpus_hash") or "")
    executable_private = private.get("executable_private_bundle") or {}
    executable_audit = verify_executable_repair_bundle(executable_public, executable_private)
    errors.extend(f"executable:{error}" for error in executable_audit["errors"])

    for case_id, case in public_cases.items():
        secret = private_cases.get(case_id, {})
        alignment = secret.get("alignment") if isinstance(secret, Mapping) else None
        if not isinstance(alignment, Mapping):
            errors.append(f"alignment_missing:{case_id}")
            continue
        if case.get("alignment_commitment") != _sha(
            {"salt": secret.get("alignment_salt"), "alignment": alignment}
        ):
            errors.append(f"alignment_commitment_invalid:{case_id}")
        requirements = alignment.get("requirements")
        assertions = alignment.get("private_assertions")
        reconstructed = {
            "case_id": case_id,
            "source": str((case.get("executable_case") or {}).get("files", {}).get("module.py", "")),
            "requirements": requirements,
            "private_setup": alignment.get("private_setup"),
            "private_assertions": assertions,
            "patch": str(
                next(
                    (
                        item.get("reference_patch", "")
                        for item in executable_private.get("cases", [])
                        if item.get("case_id") == case_id
                    ),
                    "",
                )
            ),
        }
        try:
            normalized_requirements, normalized_assertions = _validate_case_spec(reconstructed)
        except ValueError as exc:
            errors.append(f"alignment_invalid:{case_id}:{exc}")
            continue
        mappings = [
            {
                "assertion_id": assertion["assertion_id"],
                "requirement_ids": assertion["requirement_ids"],
            }
            for assertion in normalized_assertions
        ]
        if (
            case.get("requirements") != normalized_requirements
            or case.get("requirement_commitment") != _sha(normalized_requirements)
            or case.get("assertion_count") != len(normalized_assertions)
            or alignment.get("assertion_mappings") != mappings
        ):
            errors.append(f"public_private_alignment_invalid:{case_id}")
        executable_case = case.get("executable_case") or {}
        if executable_case.get("task") != _public_task(normalized_requirements):
            errors.append(f"public_task_invalid:{case_id}")
        executable_secret = next(
            (
                item
                for item in executable_private.get("cases", [])
                if item.get("case_id") == case_id
            ),
            {},
        )
        if executable_secret.get("external_test") != _external_test(
            str(alignment.get("private_setup") or ""), normalized_assertions
        ):
            errors.append(f"private_test_invalid:{case_id}")
    return {
        "valid": not errors,
        "errors": errors,
        "case_count": len(public_cases),
        "all_private_assertions_publicly_mapped": not errors,
    }


def commission_contract_aligned_repair_forge(
    public: Mapping[str, Any], private: Mapping[str, Any], root: Path
) -> dict[str, Any]:
    """Commission the aligned evaluator and reference repairs without model calls."""
    alignment_audit = verify_contract_aligned_repair_bundle(public, private)
    if alignment_audit["valid"] is not True:
        raise ValueError("contract-aligned bundle invalid: " + ",".join(alignment_audit["errors"]))
    executable_public = {
        "schema_version": "cortex-executable-repair-corpus/1.0",
        "development_only": True,
        "case_count": public["case_count"],
        "cases": [case["executable_case"] for case in public["cases"]],
        "private_tests_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "claim_boundary": (
            "A zero-call development forge with reference-patch discriminability. "
            "No model repair ability, general improvement, or mutation authority is established."
        ),
        "corpus_hash": public["executable_corpus_hash"],
    }
    executable_result = commission_executable_repair_forge(
        executable_public,
        private["executable_private_bundle"],
        root,
    )
    executable_audit = verify_executable_repair_forge_result(executable_result)
    ready = (
        executable_audit["valid"] is True
        and executable_result["state"] == "EXECUTABLE_REPAIR_FORGE_READY"
    )
    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        "state": "CONTRACT_ALIGNED_REPAIR_FORGE_READY" if ready else "CONTRACT_ALIGNED_REPAIR_FORGE_HELD",
        "corpus_hash": public["corpus_hash"],
        "executable_corpus_hash": public["executable_corpus_hash"],
        "case_count": public["case_count"],
        "requirement_count": sum(len(case["requirements"]) for case in public["cases"]),
        "assertion_count": sum(case["assertion_count"] for case in public["cases"]),
        "all_private_assertions_publicly_mapped": alignment_audit[
            "all_private_assertions_publicly_mapped"
        ],
        "all_public_requirements_covered": alignment_audit["valid"],
        "reference_repairs_measured": executable_result["reference_repairs_measured"],
        "executable_result_hash": executable_result["result_hash"],
        "additional_model_calls": 0,
        "private_assertions_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "private_bundle_persisted_in_artifact": False,
        "structural_contract_alignment_established": ready,
        "semantic_entailment_established": False,
        "baseline_calibration_established": False,
        "semantic_transfer_established": False,
        "general_improvement_established": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "next_action": "freeze_contract_aligned_baseline_screen" if ready else "repair_alignment_forge",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    result["result_hash"] = _sha(result)
    return result


def executable_bundle_from_contract_aligned(
    public: Mapping[str, Any], private: Mapping[str, Any]
) -> tuple[dict[str, Any], Mapping[str, Any]]:
    """Resolve the legacy executable projection after alignment verification."""
    audit = verify_contract_aligned_repair_bundle(public, private)
    if audit["valid"] is not True:
        raise ValueError("contract-aligned bundle invalid: " + ",".join(audit["errors"]))
    executable_public = {
        "schema_version": "cortex-executable-repair-corpus/1.0",
        "development_only": True,
        "case_count": public["case_count"],
        "cases": [case["executable_case"] for case in public["cases"]],
        "private_tests_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "claim_boundary": (
            "A zero-call development forge with reference-patch discriminability. "
            "No model repair ability, general improvement, or mutation authority is established."
        ),
        "corpus_hash": public["executable_corpus_hash"],
    }
    return executable_public, private["executable_private_bundle"]


def verify_contract_aligned_repair_forge_result(result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("schema_version") != RESULT_SCHEMA or result.get("result_hash") != _sha(body):
        errors.append("result_identity_invalid")
    ready = (
        result.get("case_count", 0) > 0
        and result.get("requirement_count", 0) > 0
        and result.get("assertion_count", 0) > 0
        and result.get("all_private_assertions_publicly_mapped") is True
        and result.get("all_public_requirements_covered") is True
        and result.get("reference_repairs_measured") == result.get("case_count")
    )
    expected = "CONTRACT_ALIGNED_REPAIR_FORGE_READY" if ready else "CONTRACT_ALIGNED_REPAIR_FORGE_HELD"
    if result.get("state") != expected:
        errors.append("result_state_invalid")
    if result.get("additional_model_calls") != 0:
        errors.append("model_call_boundary_invalid")
    for field in (
        "semantic_entailment_established",
        "baseline_calibration_established",
        "semantic_transfer_established",
        "general_improvement_established",
        "host_mutate_authorized",
        "execution_authorized",
        "memory_admission_authorized",
        "policy_effect",
    ):
        if result.get(field) is not False:
            errors.append(f"authority_or_claim_boundary_invalid:{field}")
    return {"valid": not errors, "errors": errors, "state": result.get("state")}


__all__ = [
    "PRIVATE_SCHEMA",
    "PUBLIC_SCHEMA",
    "RESULT_SCHEMA",
    "build_contract_aligned_repair_bundle",
    "commission_contract_aligned_repair_forge",
    "executable_bundle_from_contract_aligned",
    "verify_contract_aligned_repair_bundle",
    "verify_contract_aligned_repair_forge_result",
]
