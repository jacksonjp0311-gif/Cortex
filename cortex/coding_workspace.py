"""Operator-approved, repository-contained source mutation for Cortex.

The model may propose an exact unified diff.  Only the loopback operator edge
may resolve that immutable proposal, approve it, apply it, and run the fixed
verification policy.  A proposal is never mutation authority.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROPOSAL_SCHEMA = "cortex-coding-patch-proposal/1.0"
APPLICATION_SCHEMA = "cortex-coding-patch-application/1.0"
VERIFICATION_SCHEMA = "cortex-coding-patch-verification/1.0"
CONTRACT_SCHEMA = "cortex-host-verification-contract/1.0"
MAX_PATCH_BYTES = 262_144
ZERO_HASH = "0" * 64


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "MISSING"


def _contained(root: Path, relative: str) -> Path:
    if not relative or relative.startswith(("/", "\\")):
        raise ValueError("patch target must be repository-relative")
    resolved = (root.resolve() / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("patch target escapes the repository") from exc
    return resolved


def _targets(patch_text: str, root: Path) -> tuple[str, ...]:
    if not patch_text.startswith("diff --git "):
        raise ValueError("proposal must be a git unified diff")
    forbidden = ("GIT binary patch", "Binary files ", "deleted file mode", "rename from ", "rename to ")
    if any(marker in patch_text for marker in forbidden):
        raise ValueError("binary, deletion, and rename patches are not supported")
    targets: list[str] = []
    for line in patch_text.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split()
        if len(parts) != 4 or not parts[2].startswith("a/") or not parts[3].startswith("b/"):
            raise ValueError("quoted or malformed patch paths are not supported")
        left, right = parts[2][2:], parts[3][2:]
        if left != right:
            raise ValueError("patch target identity must remain stable")
        if right.startswith((".git/", ".cortex/", ".github/", "tests/", "scripts/ci/")) or right in {
            "README_STAR_HISTORY.md", "conftest.py", "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini",
        }:
            raise ValueError("patch targets a protected runtime/generated surface")
        _contained(root, right)
        targets.append(right)
    if not targets:
        raise ValueError("proposal contains no patch targets")
    if len(set(targets)) != len(targets):
        raise ValueError("proposal repeats a patch target")
    return tuple(targets)


def create_patch_proposal(root: str | Path, patch_text: str, summary: str) -> dict[str, Any]:
    workspace = Path(root).resolve()
    patch = str(patch_text or "").replace("\r\n", "\n")
    if not patch.endswith("\n"):
        patch += "\n"
    if len(patch.encode("utf-8")) > MAX_PATCH_BYTES:
        raise ValueError("patch exceeds the bounded proposal limit")
    description = str(summary or "").strip()[:500]
    if not description:
        raise ValueError("patch proposal summary is required")
    targets = _targets(patch, workspace)
    preimage_hashes = {target: _file_hash(_contained(workspace, target)) for target in targets}
    body = {
        "schema_version": PROPOSAL_SCHEMA,
        "summary": description,
        "patch": patch,
        "targets": list(targets),
        "preimage_hashes": preimage_hashes,
        "proposal_only": True,
        "operator_approval_required": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "policy_effect": False,
    }
    body["proposal_hash"] = _sha(body)
    return body


def verify_patch_proposal(root: str | Path, proposal: Mapping[str, Any]) -> dict[str, Any]:
    try:
        rebuilt = create_patch_proposal(root, str(proposal.get("patch") or ""), str(proposal.get("summary") or ""))
    except (OSError, ValueError) as exc:
        return {"valid": False, "current": False, "errors": [str(exc)]}
    identity_valid = all(proposal.get(key) == value for key, value in rebuilt.items())
    preimages = dict(rebuilt["preimage_hashes"])
    current = all(_file_hash(_contained(Path(root), target)) == digest for target, digest in preimages.items())
    errors = []
    if not identity_valid:
        errors.append("proposal_identity_invalid")
    if not current:
        errors.append("proposal_preimage_stale")
    return {"valid": identity_valid, "current": current, "errors": errors, "rebuilt": rebuilt}


def approval_challenge(session_id: str, proposal_hash: str) -> str:
    return _sha({"session_id": str(session_id), "proposal_hash": str(proposal_hash), "action": "apply"})[:16]


def _git(root: Path, arguments: list[str], patch: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        input=patch,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
        shell=False,
    )


def repository_head(root: str | Path) -> str:
    result = _git(Path(root).resolve(), ["rev-parse", "HEAD"])
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("workspace does not have a resolvable Git HEAD")
    return result.stdout.strip()


def default_verification_contract(root: str | Path, targets: list[str]) -> dict[str, Any]:
    """Build the host-owned verification policy for one proposal scope.

    The model and HTTP caller never contribute command vectors.  The tokens in
    this receipt are portable declarations; ``{python}`` resolves only at the
    host execution edge.
    """
    workspace = Path(root).resolve()
    normalized = sorted({_contained(workspace, target).relative_to(workspace).as_posix() for target in targets})
    steps: list[dict[str, Any]] = [
        {"id": "git_diff_check", "argv": ["git", "diff", "--check", "--", *normalized], "timeout_seconds": 120},
    ]
    runtime_change = any(target.startswith(("cortex/", "scripts/")) for target in normalized)
    if runtime_change:
        steps.extend([
            {"id": "compileall", "argv": ["{python}", "-m", "compileall", "-q", "cortex", "tests"], "timeout_seconds": 300},
            {"id": "repository_tests", "argv": ["{python}", "-m", "pytest", "-q"], "timeout_seconds": 1800},
        ])
    body = {
        "schema_version": CONTRACT_SCHEMA,
        "policy_id": "cortex-host-verification/default-v1",
        "targets": normalized,
        "steps": steps,
        "model_selected": False,
        "caller_selected": False,
        "promotion_authorized": False,
    }
    body["contract_hash"] = _sha(body)
    return body


def _verify_contract(contract: Mapping[str, Any], targets: list[str]) -> dict[str, Any]:
    material = {key: value for key, value in dict(contract).items() if key != "contract_hash"}
    expected = _sha(material)
    errors: list[str] = []
    if contract.get("schema_version") != CONTRACT_SCHEMA:
        errors.append("verification_contract_schema_invalid")
    if contract.get("contract_hash") != expected:
        errors.append("verification_contract_hash_invalid")
    if sorted(contract.get("targets") or []) != sorted(targets):
        errors.append("verification_contract_scope_mismatch")
    if contract.get("model_selected") is not False or contract.get("caller_selected") is not False:
        errors.append("verification_contract_authority_invalid")
    if not isinstance(contract.get("steps"), list) or not contract.get("steps"):
        errors.append("verification_contract_steps_missing")
    return {"valid": not errors, "errors": errors}


def _run_contract_step(root: Path, step: Mapping[str, Any]) -> dict[str, Any]:
    raw = step.get("argv")
    if not isinstance(raw, list) or not raw or not all(isinstance(value, str) and value for value in raw):
        return {"id": str(step.get("id") or "invalid"), "passed": False, "returncode": -1, "output": "invalid host command vector"}
    argv = [sys.executable if value == "{python}" else value for value in raw]
    started = time.perf_counter()
    try:
        result = subprocess.run(
            argv,
            cwd=root,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, min(int(step.get("timeout_seconds") or 120), 1800)),
            check=False,
            shell=False,
        )
        return {
            "id": str(step.get("id") or "step"),
            "argv": list(raw),
            "returncode": result.returncode,
            "passed": result.returncode == 0,
            "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "output": (result.stdout + result.stderr).strip()[-4000:],
        }
    except subprocess.TimeoutExpired:
        return {
            "id": str(step.get("id") or "step"),
            "argv": list(raw),
            "returncode": -1,
            "passed": False,
            "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "output": "host verification step timed out",
        }


def verify_patch_in_isolated_worktree(
    root: str | Path,
    proposal: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate an immutable proposal away from the operator's active tree."""
    workspace = Path(root).resolve()
    proposal_check = verify_patch_proposal(workspace, proposal)
    if not proposal_check["valid"] or not proposal_check["current"]:
        raise ValueError("patch proposal is invalid or stale: " + ",".join(proposal_check["errors"]))
    canonical = proposal_check["rebuilt"]
    targets = [str(value) for value in canonical["targets"]]
    numstat = _git(workspace, ["apply", "--numstat", "-"], str(canonical["patch"]))
    if numstat.returncode != 0:
        raise ValueError("git could not parse the proposed patch")
    git_targets = [line.split("\t")[-1].strip() for line in numstat.stdout.splitlines() if line.strip()]
    if sorted(git_targets) != sorted(targets):
        raise ValueError("git patch targets do not match the canonical proposal scope")
    contract_check = _verify_contract(contract, targets)
    if not contract_check["valid"]:
        raise ValueError("host verification contract invalid: " + ",".join(contract_check["errors"]))
    source_head = repository_head(workspace)

    with tempfile.TemporaryDirectory(prefix="cortex-verify-") as parent:
        candidate = Path(parent) / "candidate"
        added = _git(workspace, ["worktree", "add", "--detach", str(candidate), source_head])
        if added.returncode != 0:
            raise RuntimeError("isolated verification worktree could not be created")
        steps: list[dict[str, Any]] = []
        try:
            for target, digest in canonical["preimage_hashes"].items():
                if _file_hash(_contained(candidate, target)) != digest:
                    raise ValueError("proposal preimage does not match isolated source HEAD")
            applied = _git(candidate, ["apply", "--check", "--whitespace=error-all", "-"], str(canonical["patch"]))
            if applied.returncode != 0:
                raise ValueError("proposal does not apply to isolated source HEAD")
            applied = _git(candidate, ["apply", "--whitespace=error-all", "-"], str(canonical["patch"]))
            if applied.returncode != 0:
                raise RuntimeError("isolated proposal application failed")
            for step in contract["steps"]:
                result = _run_contract_step(candidate, step)
                steps.append(result)
                if not result["passed"]:
                    break
            postimages = {target: _file_hash(_contained(candidate, target)) for target in targets}
        finally:
            removed = _git(workspace, ["worktree", "remove", "--force", str(candidate)])
            if removed.returncode != 0:
                _git(workspace, ["worktree", "prune"])

    passed = len(steps) == len(contract["steps"]) and all(step["passed"] for step in steps)
    return {
        "schema_version": VERIFICATION_SCHEMA,
        "proposal_hash": canonical["proposal_hash"],
        "source_head": source_head,
        "contract_hash": contract["contract_hash"],
        "contract": dict(contract),
        "steps": steps,
        "postimage_hashes": postimages,
        "status": "verified" if passed else "held",
        "isolated_worktree": True,
        "active_tree_mutated": False,
        "operator_promotion_required": True,
        "host_mutate_authorized": False,
        "execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }


def apply_approved_patch(root: str | Path, proposal: Mapping[str, Any]) -> dict[str, Any]:
    workspace = Path(root).resolve()
    verification = verify_patch_proposal(workspace, proposal)
    if not verification["valid"] or not verification["current"]:
        raise ValueError("patch proposal is invalid or stale: " + ",".join(verification["errors"]))
    canonical_proposal = verification["rebuilt"]
    patch = str(canonical_proposal["patch"])
    targets = [str(value) for value in canonical_proposal["targets"]]
    numstat = _git(workspace, ["apply", "--numstat", "-"], patch)
    if numstat.returncode != 0:
        raise ValueError("git could not parse the proposed patch")
    git_targets = [line.split("\t")[-1].strip() for line in numstat.stdout.splitlines() if line.strip()]
    if sorted(git_targets) != sorted(targets):
        raise ValueError("git patch targets do not match the canonical proposal scope")
    check = _git(workspace, ["apply", "--check", "--whitespace=error-all", "-"], patch)
    if check.returncode != 0:
        raise ValueError("git apply check failed: " + (check.stderr or check.stdout).strip()[:500])
    applied = _git(workspace, ["apply", "--whitespace=error-all", "-"], patch)
    if applied.returncode != 0:
        raise RuntimeError("git apply failed after successful check")

    verification_steps: list[dict[str, Any]] = []
    try:
        diff_check = _git(workspace, ["diff", "--check", "--", *targets])
        verification_steps.append({
            "id": "git_diff_check",
            "returncode": diff_check.returncode,
            "passed": diff_check.returncode == 0,
            "output": (diff_check.stderr or diff_check.stdout).strip()[:1000],
        })
        python_targets = [str(_contained(workspace, target)) for target in targets if target.endswith(".py")]
        if python_targets:
            compiled = subprocess.run(
                [sys.executable, "-m", "py_compile", *python_targets],
                cwd=workspace,
                text=True,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
                shell=False,
            )
            verification_steps.append({
                "id": "python_compile",
                "returncode": compiled.returncode,
                "passed": compiled.returncode == 0,
                "output": (compiled.stderr or compiled.stdout).strip()[:1000],
            })
        if not all(step["passed"] for step in verification_steps):
            raise RuntimeError("post-apply verification failed")
    except Exception:
        rollback = _git(workspace, ["apply", "--reverse", "--whitespace=nowarn", "-"], patch)
        if rollback.returncode != 0:
            raise RuntimeError("verification failed and automatic rollback failed")
        raise

    return {
        "schema_version": APPLICATION_SCHEMA,
        "proposal_hash": str(canonical_proposal["proposal_hash"]),
        "targets": targets,
        "preimage_hashes": dict(canonical_proposal["preimage_hashes"]),
        "postimage_hashes": {target: _file_hash(_contained(workspace, target)) for target in targets},
        "verification_steps": verification_steps,
        "status": "applied_verified",
        "operator_approval_verified": True,
        "bounded_mutation_performed": True,
        "model_host_mutate_authorized": False,
        "model_execution_authorized": False,
        "memory_admission_authorized": False,
        "policy_effect": False,
    }


def rollback_applied_patch(root: str | Path, proposal: Mapping[str, Any]) -> None:
    workspace = Path(root).resolve()
    rollback = _git(workspace, ["apply", "--reverse", "--whitespace=nowarn", "-"], str(proposal["patch"]))
    if rollback.returncode != 0:
        raise RuntimeError("automatic rollback failed: " + (rollback.stderr or rollback.stdout).strip()[:500])


__all__ = [
    "APPLICATION_SCHEMA", "CONTRACT_SCHEMA", "PROPOSAL_SCHEMA", "VERIFICATION_SCHEMA",
    "apply_approved_patch", "approval_challenge", "create_patch_proposal",
    "default_verification_contract", "rollback_applied_patch",
    "repository_head", "verify_patch_in_isolated_worktree", "verify_patch_proposal",
]
