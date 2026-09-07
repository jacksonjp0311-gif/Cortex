"""Prospective transduction policy, reconstructable receipts, and identities.

Policy is frozen before candidate generation. Receipt records what happened.
Receipt-satisfies-policy is a verifier relation, not mutation authority.
Historical v1 observations and compilations remain reconstructable as-is.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import __version__
from .coding_workspace import _file_hash, repository_head
from .edit_intent import INTENT_SCHEMA, compile_edit_intent, verify_edit_intent_compilation
from .observation_capture import OBSERVATION_SCHEMA_V12

POLICY_SCHEMA = "cortex-transduction-policy/1.0"
RECEIPT_SCHEMA = "cortex-transduction-receipt/1.0"
SUBJECT_SCHEMA = "cortex-subject-source-identity/1.0"
INSTRUMENT_SCHEMA = "cortex-instrument-implementation-identity/1.0"
SURFACE_SCHEMA = "cortex-observation-surface/1.0"
CONFORMANCE_SCHEMA = "cortex-observation-conformance/1.0"
INTENT_SCHEMA_V2 = "cortex-structured-edit-intent/2.0"
PARSER_SEMANTICS_STRICT = "strict-string-fields/2.0"
PARSER_SEMANTICS_LEGACY = "legacy-coercing/1.0"
COMPILATION_SCHEMA_V21 = "cortex-edit-intent-compilation/2.1"
REPRESENTATION_LF = "utf8-lf-exact-bytes/1.0"

FAILURE_ATTRIBUTIONS = frozenset({
    "POLICY_BINDING_FAILURE",
    "SUBJECT_SOURCE_BINDING_FAILURE",
    "INTENT_PARSE_FAILURE",
    "INTENT_TYPE_FAILURE",
    "INTENT_SCOPE_FAILURE",
    "COMPILER_BINDING_FAILURE",
    "PROPOSAL_BINDING_FAILURE",
    "REPRESENTATION_UNSUPPORTED",
    "TRANSPORT_FAILURE",
    "PATCH_APPLICATION_FAILURE",
    "PRE_EVAL_ARTIFACT_MISMATCH",
    "ENVIRONMENT_MISMATCH",
    "OBSERVATION_SURFACE_VIOLATION",
    "EVALUATOR_EXECUTION_FAILURE",
    "EVALUATOR_REJECTION",
    "POST_EVAL_ARTIFACT_MUTATION",
    "OUTPUT_LIMIT_EXCEEDED",
    "PROCESS_TIMEOUT",
    "CAPTURE_INCOMPLETE",
    "RAW_OBSERVATION_BINDING_FAILURE",
    "INSTRUMENT_UNRESOLVED",
    "CAUSAL_ATTRIBUTION_UNRESOLVED",
    "OBSERVED_CANDIDATE_PASS",
    "EVALUATOR_MUTATED_CANDIDATE",
    "TRANSDUCTION_REPRESENTATION_UNSUPPORTED",
})

_EXCEPTION_MAP = (
    ("POLICY_BINDING_FAILURE", "POLICY_BINDING_FAILURE"),
    ("SUBJECT_SOURCE_BINDING_FAILURE", "SUBJECT_SOURCE_BINDING_FAILURE"),
    ("COMPILER_BINDING_FAILURE", "COMPILER_BINDING_FAILURE"),
    ("PROPOSAL_BINDING_FAILURE", "PROPOSAL_BINDING_FAILURE"),
    ("TRANSDUCTION_REPRESENTATION_UNSUPPORTED", "REPRESENTATION_UNSUPPORTED"),
    ("PRE_EVAL_ARTIFACT_MISMATCH", "PRE_EVAL_ARTIFACT_MISMATCH"),
    ("ENVIRONMENT_MISMATCH", "ENVIRONMENT_MISMATCH"),
    ("does not apply", "PATCH_APPLICATION_FAILURE"),
    ("could not parse the proposed patch", "TRANSPORT_FAILURE"),
    ("preimage does not match", "SUBJECT_SOURCE_BINDING_FAILURE"),
    ("edit intent must", "INTENT_PARSE_FAILURE"),
    ("edit fields must be strings", "INTENT_TYPE_FAILURE"),
    ("outside the host-declared scope", "INTENT_SCOPE_FAILURE"),
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _authority() -> dict[str, Any]:
    return {
        "authority_effect": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "production_effect": False,
    }


def subject_source_identity(root: str | Path) -> dict[str, Any]:
    workspace = Path(root).resolve()
    body = {
        "schema_version": SUBJECT_SCHEMA,
        "subject_source_head": repository_head(workspace),
        "unresolved": ["dependency_lock", "untracked_working_tree"],
        **_authority(),
    }
    return {**body, "identity_hash": _sha(body)}


def instrument_implementation_identity(
    *,
    compiler_id: str = "cortex.edit-intent.deterministic-replacement.v2",
    evaluator_id: str = "cortex-host-verification/default-v1",
) -> dict[str, Any]:
    here = Path(__file__).with_name
    body = {
        "schema_version": INSTRUMENT_SCHEMA,
        "cortex_runtime_revision": __version__,
        "compiler_id": compiler_id,
        "compiler_implementation_hashes": {
            "edit_intent.py": _file_hash(here("edit_intent.py")),
            "coding_workspace.py": _file_hash(here("coding_workspace.py")),
            "transduction_policy.py": _file_hash(Path(__file__)),
            "observation_capture.py": _file_hash(here("observation_capture.py")),
        },
        "evaluator_id": evaluator_id,
        "instrument_kind": "isolated_worktree_host_subprocess",
        **_authority(),
    }
    return {**body, "identity_hash": _sha(body)}


def observation_surface_contract(
    *,
    targets: Sequence[str],
    evaluator_files: Sequence[str] = ("external_test.py",),
) -> dict[str, Any]:
    body = {
        "schema_version": SURFACE_SCHEMA,
        "permitted_reads": ["isolated_worktree"],
        "permitted_writes": ["none"],
        "evaluator_files": list(evaluator_files),
        "support_files": [],
        "temporary_surfaces": ["host-tempdir-worktree"],
        "declared_targets": sorted(targets),
        "environment_access": "inherited-process-UNKNOWN",
        "network_access": "UNKNOWN",
        "external_path_access": "UNKNOWN",
        "os_isolation": "DECLARATIVE_ONLY",
        "enforcement": {
            "worktree_file_mutation": "CHECKED",
            "network": "UNENFORCED",
            "external_paths": "UNENFORCED",
            "process_tree": "UNENFORCED",
        },
        **_authority(),
    }
    return {**body, "surface_hash": _sha(body)}


def freeze_transduction_policy(
    root: str | Path,
    *,
    policy_id: str,
    allowed_targets: Sequence[str],
    verification_contract: Mapping[str, Any],
    evaluator_id: str | None = None,
    allowed_intent_schema: str = INTENT_SCHEMA,
    parser_semantics_id: str = PARSER_SEMANTICS_STRICT,
    compiler_id: str = "cortex.edit-intent.deterministic-replacement.v2",
    representation_policy: str = REPRESENTATION_LF,
    max_stdout_bytes: int = 1_048_576,
    max_stderr_bytes: int = 1_048_576,
    timeout_seconds: int = 120,
    environment_requirements: Mapping[str, Any] | None = None,
    subject_source_head: str | None = None,
) -> dict[str, Any]:
    """Host-owned freeze. The model does not select or alter this object."""
    if verification_contract.get("model_selected") is not False or verification_contract.get("caller_selected") is not False:
        raise ValueError("POLICY_BINDING_FAILURE")
    frozen_head = subject_source_head or repository_head(root)
    instrument = instrument_implementation_identity(
        compiler_id=compiler_id,
        evaluator_id=evaluator_id or str(verification_contract.get("policy_id") or "unspecified"),
    )
    surface = observation_surface_contract(targets=allowed_targets)
    requirements = dict(environment_requirements or {"unresolved": ["dependency_state", "non_python_toolchain", "inherited_process_environment"]})
    body = {
        "schema_version": POLICY_SCHEMA,
        "policy_id": str(policy_id),
        "allowed_intent_schema": allowed_intent_schema,
        "parser_semantics_id": parser_semantics_id,
        "compiler_id": compiler_id,
        "allowed_compiler_implementation_identity": instrument["compiler_implementation_hashes"],
        "representation_policy": representation_policy,
        "target_scope": sorted({str(item) for item in allowed_targets}),
        "subject_source_head": frozen_head,
        "verification_contract_identity": verification_contract.get("contract_hash"),
        "evaluator_identity": instrument["evaluator_id"],
        "instrument_identity_hash": instrument["identity_hash"],
        "observation_policy": OBSERVATION_SCHEMA_V12,
        "observation_surface_policy": surface,
        "environment_requirements": requirements,
        "stdout_limit": int(max_stdout_bytes),
        "stderr_limit": int(max_stderr_bytes),
        "timeout_seconds": int(timeout_seconds),
        "mutation_policy": "reject_evaluator_mutation",
        "authority_ceiling": "advisory_observation_only",
        "model_selected": False,
        **_authority(),
    }
    return {**body, "policy_hash": _sha(body)}


def compile_under_policy(
    root: str | Path,
    payload: str | Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile after policy freeze. Historical v1 reconstruction stays on edit_intent.compile_edit_intent."""
    if policy.get("schema_version") != POLICY_SCHEMA or policy.get("policy_hash") != _sha(
        {key: value for key, value in policy.items() if key != "policy_hash"}
    ):
        raise ValueError("POLICY_BINDING_FAILURE")
    compilation = compile_edit_intent(
        root,
        payload,
        allowed_targets=policy["target_scope"],
        parser_semantics_id=str(policy["parser_semantics_id"]),
        allowed_intent_schema=str(policy["allowed_intent_schema"]),
    )
    if compilation.get("compiler_id") != policy["compiler_id"]:
        raise ValueError("COMPILER_BINDING_FAILURE")
    if compilation.get("parser_semantics_id") != policy["parser_semantics_id"]:
        raise ValueError("POLICY_BINDING_FAILURE")
    return compilation


def classify_exception(exc: BaseException) -> str:
    text = str(exc)
    for needle, attribution in _EXCEPTION_MAP:
        if needle in text:
            return attribution
    if isinstance(exc, ValueError):
        return "INTENT_PARSE_FAILURE"
    return "CAUSAL_ATTRIBUTION_UNRESOLVED"


def worktree_payload_hashes(root: str | Path) -> dict[str, str]:
    workspace = Path(root).resolve()
    hashes: dict[str, str] = {}
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(workspace).as_posix()
        if relative.startswith(".git/") or relative == ".git":
            continue
        hashes[relative] = _file_hash(path)
    return hashes


def surface_violations(
    before: Mapping[str, str],
    after: Mapping[str, str],
    *,
    declared_targets: Sequence[str],
    applied_postimages: Mapping[str, str],
) -> list[str]:
    """Declared targets are conserved separately. Any other mutation is a surface violation."""
    errors: list[str] = []
    allowed = set(declared_targets)
    for path, digest in after.items():
        if path in allowed:
            continue
        if before.get(path) != digest:
            errors.append(path)
    for path in before:
        if path not in allowed and path not in after:
            errors.append(path)
    for path in allowed:
        if after.get(path) != applied_postimages.get(path) and after.get(path) != before.get(path):
            continue
    return sorted(set(errors))


def inspect_observation_conformance(
    step: Mapping[str, Any],
    *,
    frozen_argv: Sequence[str] | None = None,
    contract_step: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Derived inspection. Does not mutate historical verifier identity."""
    errors: list[str] = []
    raw = step.get("raw_observation") or {}
    environment = step.get("environment") or {}
    if not isinstance(raw.get("stdout_byte_length"), int) or raw.get("stdout_byte_length", 0) < 0:
        errors.append("negative_stdout_byte_length")
    if not isinstance(raw.get("stderr_byte_length"), int) or raw.get("stderr_byte_length", 0) < 0:
        errors.append("negative_stderr_byte_length")
    if step.get("passed") and raw.get("timed_out"):
        errors.append("successful_but_timed_out_capture")
    if step.get("passed") and raw.get("capture_complete") is False:
        errors.append("successful_but_incomplete_capture")
    if raw.get("capture_complete") and (raw.get("timed_out") or raw.get("output_limit_exceeded")):
        errors.append("complete_capture_contradiction")
    if environment.get("authority_effect") is True:
        errors.append("environment_authority_leak")
    if frozen_argv is not None and list(step.get("argv") or []) != list(frozen_argv):
        errors.append("command_vector_mismatch")
    if contract_step is not None and list(step.get("argv") or []) != list(contract_step.get("argv") or []):
        errors.append("frozen_contract_command_mismatch")
    if raw.get("returncode") != step.get("returncode"):
        errors.append("RAW_OBSERVATION_BINDING_FAILURE")
    material = {
        "schema_version": CONFORMANCE_SCHEMA,
        "errors": errors,
        "valid": not errors,
        **_authority(),
    }
    return {**material, "conformance_hash": _sha(material)}


def build_transduction_receipt(
    *,
    policy: Mapping[str, Any],
    subject: Mapping[str, Any],
    compilation: Mapping[str, Any] | None,
    verification: Mapping[str, Any] | None,
    typed_outcome: str,
    failure_attribution: str | None,
) -> dict[str, Any]:
    steps = list((verification or {}).get("steps") or [])
    observations = [step.get("raw_observation") for step in steps]
    body = {
        "schema_version": RECEIPT_SCHEMA,
        "policy_hash": policy.get("policy_hash"),
        "subject_source_identity": subject,
        "intent_identity": None if compilation is None else compilation.get("intent_hash"),
        "parser_semantics_id": None if compilation is None else compilation.get("parser_semantics_id"),
        "compilation_identity": None if compilation is None else compilation.get("compilation_hash"),
        "compiler_implementation_identity": policy.get("allowed_compiler_implementation_identity"),
        "proposal_identity": None if compilation is None else compilation.get("proposal_hash"),
        "preimages": None if compilation is None else compilation.get("preimage_hashes"),
        "expected_postimages": None if compilation is None else compilation.get("postimage_hashes"),
        "applied_before_evaluator_hashes": None if verification is None else verification.get("applied_postimage_hashes"),
        "post_evaluator_hashes": None if verification is None else verification.get("postimage_hashes"),
        "verification_contract": None if verification is None else verification.get("contract_hash"),
        "evaluator_identity": policy.get("evaluator_identity"),
        "observation_identities": [
            step.get("raw_observation_hash") for step in steps if step.get("raw_observation_hash")
        ],
        "raw_observations": observations,
        "environment_identity": None if not steps else steps[0].get("environment"),
        "observation_surface": policy.get("observation_surface_policy"),
        "typed_outcome": typed_outcome,
        "failure_attribution": failure_attribution,
        **_authority(),
    }
    return {**body, "receipt_hash": _sha(body)}


def receipt_satisfies_policy(receipt: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    expected_policy = _sha({key: value for key, value in policy.items() if key != "policy_hash"})
    if policy.get("schema_version") != POLICY_SCHEMA or policy.get("policy_hash") != expected_policy:
        errors.append("POLICY_BINDING_FAILURE")
    if receipt.get("policy_hash") != policy.get("policy_hash"):
        errors.append("wrong_policy_receipt_binding")
    if receipt.get("authority_effect") is not False or policy.get("authority_effect") is not False:
        errors.append("authority_ceiling_violated")
    if receipt.get("parser_semantics_id") not in (None, policy.get("parser_semantics_id")):
        errors.append("parser_semantics_mismatch")
    compiler_id = (receipt.get("compiler_implementation_identity") or {})
    if compiler_id and compiler_id != policy.get("allowed_compiler_implementation_identity"):
        errors.append("compiler_implementation_mismatch")
    if receipt.get("evaluator_identity") not in (None, policy.get("evaluator_identity")):
        errors.append("evaluator_identity_mismatch")
    environment = receipt.get("environment_identity") or {}
    requirements = policy.get("environment_requirements") or {}
    for key in ("os_family", "architecture", "python_implementation"):
        if key in requirements and requirements[key] != environment.get(key):
            errors.append("ENVIRONMENT_MISMATCH")
    for observation in receipt.get("raw_observations") or []:
        if not observation:
            continue
        if observation.get("stdout_byte_length", 0) > policy.get("stdout_limit", 10**12):
            errors.append("OUTPUT_LIMIT_EXCEEDED")
        if observation.get("stderr_byte_length", 0) > policy.get("stderr_limit", 10**12):
            errors.append("OUTPUT_LIMIT_EXCEEDED")
        if observation.get("timed_out") and receipt.get("typed_outcome") == "PASS":
            errors.append("PROCESS_TIMEOUT")
        if observation.get("capture_complete") is False and receipt.get("typed_outcome") == "PASS":
            errors.append("CAPTURE_INCOMPLETE")
    if receipt.get("typed_outcome") == "PASS" and receipt.get("failure_attribution") not in (None, "OBSERVED_CANDIDATE_PASS"):
        errors.append("pass_with_failure_attribution")
    if receipt.get("schema_version") != RECEIPT_SCHEMA:
        errors.append("receipt_schema_invalid")
    return {"valid": not errors, "errors": errors, "authority_effect": False}


def execute_bound_transduction(
    root: str | Path,
    policy: Mapping[str, Any],
    payload: str | Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Compile and verify under a frozen policy. Never grants production effect."""
    from .coding_workspace import verify_patch_in_isolated_worktree

    subject = subject_source_identity(root)
    compilation = None
    verification = None
    try:
        if policy.get("policy_hash") != _sha({key: value for key, value in policy.items() if key != "policy_hash"}):
            raise ValueError("POLICY_BINDING_FAILURE")
        if subject["subject_source_head"] != policy.get("subject_source_head") or subject["subject_source_head"] != repository_head(root):
            raise ValueError("SUBJECT_SOURCE_BINDING_FAILURE")
        instrument = instrument_implementation_identity(
            compiler_id=str(policy["compiler_id"]),
            evaluator_id=str(policy["evaluator_identity"]),
        )
        if instrument["compiler_implementation_hashes"] != policy["allowed_compiler_implementation_identity"]:
            raise ValueError("COMPILER_BINDING_FAILURE")
        from .coding_workspace import verification_environment
        environment = verification_environment()
        requirements = policy.get("environment_requirements") or {}
        for key in ("os_family", "architecture", "python_implementation"):
            if key in requirements and requirements[key] != environment.get(key):
                raise ValueError("ENVIRONMENT_MISMATCH")
        compilation = compile_under_policy(root, payload, policy)
        if not verify_edit_intent_compilation(root, compilation)["valid"]:
            raise ValueError("COMPILER_BINDING_FAILURE")
        verification = verify_patch_in_isolated_worktree(
            root,
            compilation["proposal"],
            contract,
            compilation=compilation,
            policy=policy,
        )
        attribution = verification.get("failure_attribution")
        if verification.get("status") == "verified":
            outcome, attribution = "PASS", "OBSERVED_CANDIDATE_PASS"
        elif attribution == "OBSERVATION_SURFACE_VIOLATION":
            outcome = "FAIL"
        elif attribution:
            outcome = "HELD"
        else:
            outcome, attribution = "HELD", "EVALUATOR_REJECTION"
        receipt = build_transduction_receipt(
            policy=policy,
            subject=subject,
            compilation=compilation,
            verification=verification,
            typed_outcome=outcome,
            failure_attribution=attribution,
        )
        conformance = receipt_satisfies_policy(receipt, policy)
        if outcome == "PASS" and not conformance["valid"]:
            receipt = build_transduction_receipt(
                policy=policy,
                subject=subject,
                compilation=compilation,
                verification=verification,
                typed_outcome="HELD",
                failure_attribution=conformance["errors"][0],
            )
        return {
            "receipt": receipt,
            "verification": verification,
            "compilation": compilation,
            "conformance": receipt_satisfies_policy(receipt, policy),
            "authority_effect": False,
        }
    except (OSError, ValueError, RuntimeError) as exc:
        attribution = classify_exception(exc)
        receipt = build_transduction_receipt(
            policy=policy,
            subject=subject,
            compilation=compilation,
            verification=verification,
            typed_outcome="HELD" if attribution in {"ENVIRONMENT_MISMATCH", "INSTRUMENT_UNRESOLVED", "CAUSAL_ATTRIBUTION_UNRESOLVED"} else "FAIL",
            failure_attribution=attribution,
        )
        return {
            "receipt": receipt,
            "verification": verification,
            "compilation": compilation,
            "conformance": receipt_satisfies_policy(receipt, policy),
            "error": str(exc),
            "authority_effect": False,
        }


def attest_transduction_receipt(
    receipt: Mapping[str, Any],
    policy: Mapping[str, Any],
    root: str | Path,
    contract: Mapping[str, Any] | None = None,
    compilation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Independent attestation. Does not trust execute_bound_transduction."""
    unresolved: list[str] = []
    invalid: list[str] = []
    checked: list[str] = []

    def ok(name: str) -> None:
        checked.append(name)

    def bad(name: str) -> None:
        invalid.append(name)

    expected_receipt = _sha({key: value for key, value in receipt.items() if key != "receipt_hash"})
    (ok if receipt.get("receipt_hash") == expected_receipt else bad)("receipt_hash")
    expected_policy = _sha({key: value for key, value in policy.items() if key != "policy_hash"})
    (ok if policy.get("policy_hash") == expected_policy and receipt.get("policy_hash") == policy.get("policy_hash") else bad)("policy_hash")
    subject = receipt.get("subject_source_identity") or {}
    expected_subject = _sha({key: value for key, value in subject.items() if key != "identity_hash"})
    (ok if subject.get("identity_hash") == expected_subject else bad)("subject_identity_hash")
    try:
        head = repository_head(root)
        (ok if subject.get("subject_source_head") == head == policy.get("subject_source_head") else bad)("subject_HEAD")
    except (OSError, ValueError):
        unresolved.append("subject_HEAD")
    instrument = instrument_implementation_identity(
        compiler_id=str(policy.get("compiler_id") or ""),
        evaluator_id=str(policy.get("evaluator_identity") or ""),
    )
    (ok if instrument["compiler_implementation_hashes"] == policy.get("allowed_compiler_implementation_identity") else bad)("instrument_implementation_hashes")
    if compilation is None:
        unresolved.append("compilation_identity")
        unresolved.append("proposal_identity")
        unresolved.append("parser_semantics")
        unresolved.append("compiler_identity")
    else:
        (ok if verify_edit_intent_compilation(root, compilation)["valid"] else bad)("compilation_identity")
        (ok if compilation.get("compiler_id") == policy.get("compiler_id") else bad)("compiler_identity")
        (ok if compilation.get("parser_semantics_id") == policy.get("parser_semantics_id") else bad)("parser_semantics")
        (ok if compilation.get("proposal_hash") == receipt.get("proposal_identity") else bad)("proposal_identity")
        (ok if compilation.get("postimage_hashes") == receipt.get("expected_postimages") else bad)("expected_postimages")
    if contract is None:
        unresolved.append("verification_contract_identity")
    else:
        (ok if contract.get("contract_hash") == receipt.get("verification_contract") == policy.get("verification_contract_identity") else bad)("verification_contract_identity")
    applied = receipt.get("applied_before_evaluator_hashes")
    post = receipt.get("post_evaluator_hashes")
    expected = receipt.get("expected_postimages")
    if applied is None or post is None or expected is None:
        unresolved.append("artifact_hashes")
    else:
        (ok if applied == expected else bad)("applied_before_evaluator_hashes")
        if receipt.get("typed_outcome") == "PASS":
            (ok if post == applied else bad)("post_evaluator_hashes")
        else:
            ok("post_evaluator_hashes")
    for observation in receipt.get("raw_observations") or []:
        if not observation:
            unresolved.append("raw_observation_hashes")
            continue
        (ok if observation.get("environment_hash") == (receipt.get("environment_identity") or {}).get("environment_hash") else bad)("environment_hash")
        conformance = inspect_observation_conformance({"raw_observation": observation, "returncode": observation.get("returncode"), "passed": False, "environment": receipt.get("environment_identity") or {}})
        if not conformance["valid"] and any(item.startswith("negative") or item == "environment_authority_leak" for item in conformance["errors"]):
            bad("raw_observation_structural_conformance")
        else:
            ok("raw_observation_structural_conformance")
    if not (receipt.get("raw_observations") or []):
        unresolved.append("raw_observation_hashes")
    for field in ("authority_effect", "host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect", "production_effect"):
        (ok if receipt.get(field) is False else bad)("authority_fields")
    if receipt.get("failure_attribution") == "REASONING_FAILURE":
        bad("failure_localization")
    if invalid:
        status = "INVALID"
    elif unresolved:
        status = "PARTIALLY_ATTESTED"
    else:
        status = "ATTESTED"
    body = {
        "schema_version": "cortex-transduction-receipt-attestation/1.0",
        "status": status,
        "checked": checked,
        "invalid": invalid,
        "unresolved": unresolved,
        **_authority(),
    }
    return {**body, "attestation_hash": _sha(body)}


__all__ = [
    "COMPILATION_SCHEMA_V21",
    "FAILURE_ATTRIBUTIONS",
    "INTENT_SCHEMA_V2",
    "PARSER_SEMANTICS_LEGACY",
    "PARSER_SEMANTICS_STRICT",
    "POLICY_SCHEMA",
    "RECEIPT_SCHEMA",
    "attest_transduction_receipt",
    "compile_under_policy",
    "execute_bound_transduction",
    "freeze_transduction_policy",
    "inspect_observation_conformance",
    "instrument_implementation_identity",
    "observation_surface_contract",
    "receipt_satisfies_policy",
    "subject_source_identity",
    "worktree_payload_hashes",
]
