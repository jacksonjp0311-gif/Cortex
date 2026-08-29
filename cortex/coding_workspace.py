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
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PROPOSAL_SCHEMA = "cortex-coding-patch-proposal/1.0"
APPLICATION_SCHEMA = "cortex-coding-patch-application/1.0"
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
        if right.startswith((".git/", ".cortex/")) or right in {"README_STAR_HISTORY.md"}:
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
    "APPLICATION_SCHEMA", "PROPOSAL_SCHEMA", "apply_approved_patch",
    "approval_challenge", "create_patch_proposal", "rollback_applied_patch",
    "verify_patch_proposal",
]
