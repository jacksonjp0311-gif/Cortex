"""Answer-sealed executable repair tasks for the post-semantic benchmark.

The public task contains only the defect description and buggy source.  Frozen
external tests and reference patches remain host-private.  Commissioning proves
that each evaluator distinguishes its unchanged baseline from one known repair;
it does not measure a model or authorize mutation.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .coding_workspace import CONTRACT_SCHEMA as VERIFY_SCHEMA
from .coding_workspace import create_patch_proposal, verify_patch_in_isolated_worktree
from .source_improvement import (
    create_source_improvement_contract,
    run_source_improvement_trial,
    verify_source_improvement_result,
)

PUBLIC_SCHEMA = "cortex-executable-repair-corpus/1.0"
PRIVATE_SCHEMA = "cortex-executable-repair-private/1.0"
RESULT_SCHEMA = "cortex-alpha31-executable-repair-forge/1.0"
CLAIM_BOUNDARY = (
    "A zero-call development forge with reference-patch discriminability. "
    "No model repair ability, general improvement, or mutation authority is established."
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _case_material() -> tuple[dict[str, str], ...]:
    return (
        {
            "case_id": "stale_cache_invalidation",
            "task": "Repair Catalog.rename so reads after a successful rename never return a stale cached name.",
            "source": '''class Catalog:\n    def __init__(self):\n        self.records = {"a": "amber"}\n        self._cache = {}\n\n    def read(self, key):\n        if key not in self._cache:\n            self._cache[key] = self.records[key]\n        return self._cache[key]\n\n    def rename(self, key, value):\n        self.records[key] = value\n''',
            "test": '''from module import Catalog\n\nc = Catalog()\nassert c.read("a") == "amber"\nc.rename("a", "azure")\nassert c.read("a") == "azure", "rename leaked a stale cached value"\n''',
            "patch": '''diff --git a/module.py b/module.py\n--- a/module.py\n+++ b/module.py\n@@ -10,3 +10,4 @@ class Catalog:\n \n     def rename(self, key, value):\n         self.records[key] = value\n+        self._cache.pop(key, None)\n''',
        },
        {
            "case_id": "zero_generation_guard",
            "task": "Repair SnapshotStore.apply so expected generation zero is checked rather than treated as absent.",
            "source": '''class SnapshotStore:\n    def __init__(self):\n        self.generation = 1\n        self.value = "old"\n\n    def apply(self, value, expected_generation=None):\n        if expected_generation and expected_generation != self.generation:\n            raise RuntimeError("stale generation")\n        self.value = value\n''',
            "test": '''from module import SnapshotStore\n\ns = SnapshotStore()\ntry:\n    s.apply("unsafe", expected_generation=0)\nexcept RuntimeError:\n    pass\nelse:\n    raise AssertionError("generation zero bypassed the stale-state guard")\nassert s.value == "old"\n''',
            "patch": '''diff --git a/module.py b/module.py\n--- a/module.py\n+++ b/module.py\n@@ -5,6 +5,6 @@ class SnapshotStore:\n         self.value = "old"\n \n     def apply(self, value, expected_generation=None):\n-        if expected_generation and expected_generation != self.generation:\n+        if expected_generation is not None and expected_generation != self.generation:\n             raise RuntimeError("stale generation")\n         self.value = value\n''',
        },
        {
            "case_id": "validate_before_publish",
            "task": "Repair Registry.publish so a rejected artifact is never visible in the published collection.",
            "source": '''class Registry:\n    def __init__(self):\n        self.published = []\n\n    def publish(self, artifact):\n        self.published.append(artifact)\n        if not artifact.get("verified"):\n            raise ValueError("artifact is not verified")\n''',
            "test": '''from module import Registry\n\nr = Registry()\ntry:\n    r.publish({"id": "bad", "verified": False})\nexcept ValueError:\n    pass\nelse:\n    raise AssertionError("unverified artifact was accepted")\nassert r.published == [], "rejected artifact leaked into published state"\n''',
            "patch": '''diff --git a/module.py b/module.py\n--- a/module.py\n+++ b/module.py\n@@ -3,6 +3,6 @@ class Registry:\n         self.published = []\n \n     def publish(self, artifact):\n-        self.published.append(artifact)\n         if not artifact.get("verified"):\n             raise ValueError("artifact is not verified")\n+        self.published.append(artifact)\n''',
        },
        {
            "case_id": "validity_before_dedup",
            "task": "Repair select_valid so an invalid duplicate cannot suppress a later valid record with the same id.",
            "source": '''def select_valid(records):\n    selected = []\n    seen = set()\n    for record in records:\n        key = record["id"]\n        if key in seen:\n            continue\n        seen.add(key)\n        if not record.get("valid"):\n            continue\n        selected.append(record)\n    return selected\n''',
            "test": '''from module import select_valid\n\nrecords = [\n    {"id": "x", "valid": False, "value": "bad"},\n    {"id": "x", "valid": True, "value": "good"},\n]\nassert select_valid(records) == [records[1]], "invalid-first duplicate suppressed valid evidence"\n''',
            "patch": '''diff --git a/module.py b/module.py\n--- a/module.py\n+++ b/module.py\n@@ -5,8 +5,8 @@ def select_valid(records):\n         key = record["id"]\n         if key in seen:\n             continue\n-        seen.add(key)\n         if not record.get("valid"):\n             continue\n+        seen.add(key)\n         selected.append(record)\n     return selected\n''',
        },
    )


def build_executable_repair_bundle(*, secret_seed: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a public task corpus and a separately sealable private evaluator bundle."""
    if not str(secret_seed):
        raise ValueError("a non-empty host secret seed is required")
    public_cases: list[dict[str, Any]] = []
    private_cases: list[dict[str, Any]] = []
    for raw in _case_material():
        salt = _sha({"seed": secret_seed, "case_id": raw["case_id"]})
        private_body = {"case_id": raw["case_id"], "external_test": raw["test"], "reference_patch": raw["patch"]}
        commitment = _sha({"salt": salt, "private": private_body})
        public_cases.append({
            "case_id": raw["case_id"],
            "task": raw["task"],
            "files": {"module.py": raw["source"]},
            "model_visible_files": ["TASK.md", "module.py"],
            "private_evaluator_commitment": commitment,
        })
        private_cases.append({**private_body, "salt": salt})
    public: dict[str, Any] = {
        "schema_version": PUBLIC_SCHEMA,
        "development_only": True,
        "case_count": len(public_cases),
        "cases": public_cases,
        "private_tests_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "claim_boundary": CLAIM_BOUNDARY,
    }
    public["corpus_hash"] = _sha(public)
    private: dict[str, Any] = {
        "schema_version": PRIVATE_SCHEMA,
        "corpus_hash": public["corpus_hash"],
        "cases": private_cases,
    }
    private["private_bundle_hash"] = _sha(private)
    return public, private


def verify_executable_repair_bundle(public: Mapping[str, Any], private: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    public_body = {key: value for key, value in public.items() if key != "corpus_hash"}
    private_body = {key: value for key, value in private.items() if key != "private_bundle_hash"}
    if public.get("schema_version") != PUBLIC_SCHEMA or public.get("corpus_hash") != _sha(public_body):
        errors.append("public_identity_invalid")
    if private.get("schema_version") != PRIVATE_SCHEMA or private.get("private_bundle_hash") != _sha(private_body):
        errors.append("private_identity_invalid")
    if private.get("corpus_hash") != public.get("corpus_hash"):
        errors.append("corpus_binding_invalid")
    public_cases = {str(case.get("case_id")): case for case in public.get("cases", []) if isinstance(case, Mapping)}
    private_cases = {str(case.get("case_id")): case for case in private.get("cases", []) if isinstance(case, Mapping)}
    if set(public_cases) != set(private_cases) or len(public_cases) != int(public.get("case_count") or -1):
        errors.append("case_identity_invalid")
    for case_id, case in public_cases.items():
        secret = private_cases.get(case_id, {})
        private_material = {key: secret.get(key) for key in ("case_id", "external_test", "reference_patch")}
        if case.get("private_evaluator_commitment") != _sha({"salt": secret.get("salt"), "private": private_material}):
            errors.append(f"private_commitment_invalid:{case_id}")
        if "external_test.py" in (case.get("files") or {}) or "reference_patch" in case:
            errors.append(f"private_material_disclosed:{case_id}")
    return {"valid": not errors, "errors": errors}


def _write_fixture(root: Path, case: Mapping[str, Any], private: Mapping[str, Any]) -> None:
    root.mkdir(parents=True)
    for name, content in (case.get("files") or {}).items():
        (root / str(name)).write_text(str(content), encoding="utf-8")
    (root / "TASK.md").write_text(str(case["task"]) + "\n", encoding="utf-8")
    (root / "external_test.py").write_text(str(private["external_test"]), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "cortex@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Cortex Forge"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "frozen executable task"], cwd=root, check=True)


def _verification_contract(proposal: Mapping[str, Any]) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": VERIFY_SCHEMA,
        "policy_id": "cortex-alpha31-frozen-external-test/1.0",
        "targets": list(proposal["targets"]),
        "steps": [{"id": "frozen_external_test", "argv": ["{python}", "external_test.py"], "timeout_seconds": 30}],
        "model_selected": False,
        "caller_selected": False,
        "promotion_authorized": False,
    }
    body["contract_hash"] = _sha(body)
    return body


def commission_executable_repair_forge(public: Mapping[str, Any], private: Mapping[str, Any], root: Path) -> dict[str, Any]:
    """Run deterministic baseline/reference checks without invoking a model."""
    audit = verify_executable_repair_bundle(public, private)
    if not audit["valid"]:
        raise ValueError("executable repair bundle invalid: " + ",".join(audit["errors"]))
    private_cases = {str(case["case_id"]): case for case in private["cases"]}
    cases: list[dict[str, Any]] = []
    for public_case in public["cases"]:
        case_id = str(public_case["case_id"])
        workspace = root / case_id
        secret = private_cases[case_id]
        _write_fixture(workspace, public_case, secret)
        proposal = create_patch_proposal(workspace, str(secret["reference_patch"]), "host reference repair")
        verification = verify_patch_in_isolated_worktree(workspace, proposal, _verification_contract(proposal))
        verification = {**verification, "kind": "coding_patch_verification"}
        verification["receipt_hash"] = _sha(verification)
        contract = create_source_improvement_contract(workspace, proposal, verification)
        result = run_source_improvement_trial(workspace, proposal, verification, contract)
        result_audit = verify_source_improvement_result(result)
        cases.append({
            "case_id": case_id,
            "evaluator_commitment": public_case["private_evaluator_commitment"],
            "source_head": result["source_head"],
            "baseline_pass": result["arms"]["baseline"]["all_host_checks_pass"],
            "reference_candidate_pass": result["arms"]["candidate"]["all_host_checks_pass"],
            "classification": result["status"],
            "counterfactual_result_hash": result["result_hash"],
            "canonical_result_valid": result_audit["valid"],
            "active_tree_mutated": result["active_tree_mutated"],
        })
    ready = all(
        not case["baseline_pass"] and case["reference_candidate_pass"]
        and case["classification"] == "REPAIR_MEASURED" and case["canonical_result_valid"]
        and not case["active_tree_mutated"]
        for case in cases
    )
    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        "state": "EXECUTABLE_REPAIR_FORGE_READY" if ready else "EXECUTABLE_REPAIR_FORGE_HELD",
        "corpus_hash": public["corpus_hash"],
        "case_count": len(cases),
        "cases": cases,
        "reference_repairs_measured": sum(case["classification"] == "REPAIR_MEASURED" for case in cases),
        "additional_model_calls": 0,
        "private_tests_in_model_context": False,
        "private_reference_patches_in_model_context": False,
        "private_bundle_persisted_in_artifact": False,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
        "semantic_transfer_established": False,
        "general_improvement_established": False,
        "next_action": "freeze_frontier_model_executable_repair_screen" if ready else "repair_forge",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    result["result_hash"] = _sha(result)
    return result


def verify_executable_repair_forge_result(result: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: value for key, value in result.items() if key != "result_hash"}
    if result.get("schema_version") != RESULT_SCHEMA or result.get("result_hash") != _sha(body):
        errors.append("result_identity_invalid")
    cases = result.get("cases") if isinstance(result.get("cases"), list) else []
    ready = bool(cases) and len(cases) == result.get("case_count") and all(
        case.get("baseline_pass") is False
        and case.get("reference_candidate_pass") is True
        and case.get("classification") == "REPAIR_MEASURED"
        and case.get("canonical_result_valid") is True
        and case.get("active_tree_mutated") is False
        for case in cases if isinstance(case, Mapping)
    )
    if result.get("state") != ("EXECUTABLE_REPAIR_FORGE_READY" if ready else "EXECUTABLE_REPAIR_FORGE_HELD"):
        errors.append("result_state_invalid")
    if result.get("additional_model_calls") != 0:
        errors.append("model_call_boundary_invalid")
    for field in ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect", "semantic_transfer_established", "general_improvement_established"):
        if result.get(field) is not False:
            errors.append(f"authority_or_claim_boundary_invalid:{field}")
    return {"valid": not errors, "errors": errors, "state": result.get("state")}


__all__ = [
    "PUBLIC_SCHEMA", "PRIVATE_SCHEMA", "RESULT_SCHEMA", "build_executable_repair_bundle",
    "commission_executable_repair_forge", "verify_executable_repair_bundle",
    "verify_executable_repair_forge_result",
]
