"""Recoverable Git integration for verified Cortex campaign candidates."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .autonomous_improvement import verify_autonomy_policy
from .campaign_control import verify_control_action
from .coding_workspace import apply_approved_patch, repository_head, verify_patch_proposal
from .symbiosis import open_symbiotic_session

SCHEMA = "cortex-campaign-integration/1.0"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _closed() -> dict[str, bool]:
    return {
        "model_host_mutate_authorized": False,
        "model_execution_authorized": False,
        "memory_admission_authorized": False,
        "competence_promotion_authorized": False,
        "policy_effect": False,
    }


def _git(root: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True,
        encoding="utf-8", errors="replace", check=False, shell=False,
    )
    if check and result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip()[:500])
    return result


def _receipt(store: Any, repo: str, receipt_hash: str, kind: str) -> dict[str, Any]:
    value = store.symbiotic_receipt(receipt_hash, repo=repo)
    if not value or value.get("kind") != kind:
        raise PermissionError(f"canonical {kind} required")
    if store.verify_symbiotic_receipt(repo, receipt_hash).get("valid") is not True:
        raise PermissionError(f"canonical {kind} invalid")
    return value


def integration_request(
    campaign_id: str, action: str, *, terminal_hash: str = "",
    preparation_hash: str = "", candidate_commit: str = "",
    integration_result_hash: str = "",
) -> dict[str, str]:
    return {
        "campaign_id": str(campaign_id), "action": str(action),
        "terminal_receipt_hash": str(terminal_hash),
        "preparation_receipt_hash": str(preparation_hash),
        "candidate_commit": str(candidate_commit),
        "integration_result_hash": str(integration_result_hash),
    }


def prepare_campaign_integration(
    store: Any, repo: str, root: str | Path, *, campaign_id: str,
    terminal_receipt_hash: str, policy_receipt_hash: str, policy_secret: str,
    tournament_receipt_hash: str, trial_receipt_hash: str,
    proposal: Mapping[str, Any], action_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    """Create and pin a candidate commit without touching the active worktree."""
    workspace = Path(root).resolve()
    terminal = _receipt(store, repo, terminal_receipt_hash, "campaign_worker_terminal")
    if terminal.get("status") != "completed_boundary_return" or terminal.get("campaign_id") != campaign_id:
        raise PermissionError("completed campaign terminal required")
    policy = verify_autonomy_policy(store, repo, policy_receipt_hash, secret=policy_secret)
    if policy.get("valid") is not True:
        raise PermissionError("current signed policy required")
    tournament = _receipt(store, repo, tournament_receipt_hash, "improvement_tournament")
    if terminal.get("tournament_receipt_hash") != tournament_receipt_hash:
        raise PermissionError("terminal tournament binding invalid")
    trial = _receipt(store, repo, trial_receipt_hash, "coding_improvement_trial")
    proposal_check = verify_patch_proposal(workspace, proposal)
    if not proposal_check.get("valid") or not proposal_check.get("current"):
        raise PermissionError("current canonical proposal required")
    proposal_hash = str(proposal.get("proposal_hash") or "")
    selected = next((row for row in tournament.get("candidates") or () if row.get("proposal_hash") == proposal_hash), None)
    if tournament.get("selected_proposal_hash") != proposal_hash or not selected:
        raise PermissionError("proposal is not canonical tournament winner")
    if selected.get("trial_hash") != trial.get("result_hash"):
        raise PermissionError("winner trial binding invalid")
    request = integration_request(campaign_id, "campaign.promote", terminal_hash=terminal_receipt_hash)
    action = verify_control_action(
        store, repo, action_authorization, expected_action="campaign.promote",
        expected_request=request, consumed_kinds=("campaign_integration_preparation",),
    )
    base_head = repository_head(workspace)
    if base_head != tournament.get("source_head"):
        raise PermissionError("integration source head changed")
    with tempfile.TemporaryDirectory(prefix="cortex-candidate-") as temporary:
        candidate_root = Path(temporary) / "worktree"
        _git(workspace, ["worktree", "add", "--detach", str(candidate_root), base_head])
        try:
            application = apply_approved_patch(candidate_root, proposal)
            _git(candidate_root, ["add", "--", *application["targets"]])
            _git(candidate_root, ["commit", "-m", f"cortex candidate {campaign_id}"])
            candidate_commit = repository_head(candidate_root)
            candidate_tree = _git(
                candidate_root, ["rev-parse", f"{candidate_commit}^{{tree}}"]
            ).stdout.strip()
        finally:
            _git(workspace, ["worktree", "remove", "--force", str(candidate_root)], check=False)
    safe_id = re.sub(r"[^A-Za-z0-9._-]", "-", campaign_id)[:80]
    candidate_ref = f"refs/cortex/candidates/{safe_id}"
    _git(workspace, ["update-ref", candidate_ref, candidate_commit])
    session = open_symbiotic_session(store, repo, task="prepare campaign integration", provider="host-integration", model_id="none", capability_profile={}, tool_scopes=(), persist=True)
    return store.append_symbiotic_receipt(repo, {
        "schema_version": SCHEMA, "kind": "campaign_integration_preparation", "status": "integration_prepared",
        "session_id": session["session_id"], "turn_id": 0, "event_id": f"integration_prepare_{_sha([campaign_id, candidate_commit])[:24]}", "body_epoch_id": session["body_epoch_id"],
        "campaign_id": campaign_id, "terminal_receipt_hash": terminal_receipt_hash,
        "policy_receipt_hash": policy_receipt_hash, "tournament_receipt_hash": tournament_receipt_hash,
        "trial_receipt_hash": trial_receipt_hash, "proposal_hash": proposal_hash,
        "base_head": base_head, "recovery_anchor": base_head, "candidate_commit": candidate_commit,
        "candidate_tree": candidate_tree, "candidate_ref": candidate_ref,
        "targets": application["targets"], "preimage_hashes": application["preimage_hashes"],
        "postimage_hashes": application["postimage_hashes"],
        "action_authorization_receipt_hash": action["receipt_hash"],
        "active_worktree_mutated": False, "integration_authorized": False, **_closed(),
    })


def apply_campaign_integration(
    store: Any, repo: str, root: str | Path, *,
    preparation_receipt_hash: str,
    action_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    """Fast-forward one unchanged clean base to its pinned candidate commit."""
    workspace = Path(root).resolve()
    prepared = _receipt(
        store, repo, preparation_receipt_hash, "campaign_integration_preparation"
    )
    request = integration_request(
        str(prepared["campaign_id"]), "campaign.integrate",
        preparation_hash=preparation_receipt_hash,
        candidate_commit=str(prepared["candidate_commit"]),
    )
    action = verify_control_action(
        store, repo, action_authorization, expected_action="campaign.integrate",
        expected_request=request, consumed_kinds=("campaign_integration_result",),
    )
    if repository_head(workspace) != prepared.get("base_head"):
        raise PermissionError("active source head changed after preparation")
    if _git(workspace, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout.strip():
        raise PermissionError("active worktree must be clean")
    resolved = _git(workspace, ["rev-parse", str(prepared["candidate_ref"])]).stdout.strip()
    if resolved != prepared.get("candidate_commit"):
        raise PermissionError("candidate ref does not resolve to prepared commit")
    _git(workspace, ["merge", "--ff-only", str(prepared["candidate_commit"])])
    errors: list[str] = []
    if repository_head(workspace) != prepared.get("candidate_commit"):
        errors.append("integrated_head_mismatch")
    for target, expected in (prepared.get("postimage_hashes") or {}).items():
        path = (workspace / str(target)).resolve()
        try:
            path.relative_to(workspace)
        except ValueError:
            errors.append(f"target_outside_workspace:{target}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        if actual != expected:
            errors.append(f"postimage_mismatch:{target}")
    if _git(workspace, ["diff", "--check", f"{prepared['base_head']}..HEAD"], check=False).returncode:
        errors.append("git_diff_check_failed")
    status = "verified_complete" if not errors else "recovery_required"
    session = open_symbiotic_session(store, repo, task="apply campaign integration", provider="host-integration", model_id="none", capability_profile={}, tool_scopes=(), persist=True)
    return store.append_symbiotic_receipt(repo, {
        "schema_version": SCHEMA, "kind": "campaign_integration_result", "status": status,
        "session_id": session["session_id"], "turn_id": 0,
        "event_id": f"integration_result_{_sha([preparation_receipt_hash, status])[:24]}",
        "body_epoch_id": session["body_epoch_id"], "campaign_id": prepared["campaign_id"],
        "preparation_receipt_hash": preparation_receipt_hash,
        "base_head": prepared["base_head"], "candidate_commit": prepared["candidate_commit"],
        "integrated_head": repository_head(workspace), "verification_errors": errors,
        "action_authorization_receipt_hash": action["receipt_hash"],
        "host_integration_performed": True, "integration_verified": not errors,
        "campaign_success": False, **_closed(),
    })


def rollback_campaign_integration(
    store: Any,
    repo: str,
    root: str | Path,
    *,
    integration_result_receipt_hash: str,
    action_authorization: Mapping[str, Any],
) -> dict[str, Any]:
    """Create a reverse commit and verify the full tree against its anchor."""

    workspace = Path(root).resolve()
    integrated = _receipt(
        store, repo, integration_result_receipt_hash, "campaign_integration_result"
    )
    if integrated.get("status") not in {"verified_complete", "recovery_required"}:
        raise PermissionError("integration is not rollback eligible")
    prepared = _receipt(
        store,
        repo,
        str(integrated["preparation_receipt_hash"]),
        "campaign_integration_preparation",
    )
    request = integration_request(
        str(integrated["campaign_id"]),
        "campaign.rollback",
        preparation_hash=str(prepared["receipt_hash"]),
        candidate_commit=str(prepared["candidate_commit"]),
        integration_result_hash=integration_result_receipt_hash,
    )
    action = verify_control_action(
        store,
        repo,
        action_authorization,
        expected_action="campaign.rollback",
        expected_request=request,
        consumed_kinds=("campaign_integration_rollback",),
    )
    if repository_head(workspace) != integrated.get("integrated_head"):
        raise PermissionError("active head changed after integration")
    if _git(
        workspace, ["status", "--porcelain=v1", "--untracked-files=all"]
    ).stdout.strip():
        raise PermissionError("active worktree must be clean for rollback")
    reverted = _git(
        workspace,
        ["revert", "--no-edit", str(prepared["candidate_commit"])],
        check=False,
    )
    if reverted.returncode:
        _git(workspace, ["revert", "--abort"], check=False)
        raise RuntimeError("recovery commit failed: " + (reverted.stderr or reverted.stdout).strip()[:300])
    recovery_commit = repository_head(workspace)
    errors: list[str] = []
    for target, expected in (prepared.get("preimage_hashes") or {}).items():
        path = (workspace / str(target)).resolve()
        try:
            path.relative_to(workspace)
        except ValueError:
            errors.append(f"target_outside_workspace:{target}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        if actual != expected:
            errors.append(f"preimage_mismatch:{target}")
    anchor_tree = _git(
        workspace, ["rev-parse", f"{prepared['recovery_anchor']}^{{tree}}"]
    ).stdout.strip()
    restored_tree = _git(workspace, ["rev-parse", "HEAD^{tree}"]).stdout.strip()
    if restored_tree != anchor_tree:
        errors.append("full_tree_mismatch")
    status = "rollback_verified" if not errors else "manual_recovery_required"
    session = open_symbiotic_session(
        store,
        repo,
        task="rollback campaign integration",
        provider="host-integration",
        model_id="none",
        capability_profile={},
        tool_scopes=(),
        persist=True,
    )
    return store.append_symbiotic_receipt(
        repo,
        {
            "schema_version": SCHEMA,
            "kind": "campaign_integration_rollback",
            "status": status,
            "session_id": session["session_id"],
            "turn_id": 0,
            "event_id": f"integration_rollback_{_sha([integration_result_receipt_hash, recovery_commit])[:24]}",
            "body_epoch_id": session["body_epoch_id"],
            "campaign_id": integrated["campaign_id"],
            "integration_result_receipt_hash": integration_result_receipt_hash,
            "preparation_receipt_hash": prepared["receipt_hash"],
            "candidate_commit": prepared["candidate_commit"],
            "recovery_anchor": prepared["recovery_anchor"],
            "pre_rollback_head": integrated["integrated_head"],
            "recovery_commit": recovery_commit,
            "anchor_tree": anchor_tree,
            "restored_tree": restored_tree,
            "verification_errors": errors,
            "action_authorization_receipt_hash": action["receipt_hash"],
            "history_preserving_revert": True,
            "rollback_verified": not errors,
            "campaign_success": False,
            **_closed(),
        },
    )


__all__ = [
    "apply_campaign_integration",
    "integration_request",
    "prepare_campaign_integration",
    "rollback_campaign_integration",
]
