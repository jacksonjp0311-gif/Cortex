"""Adversarial gates for isolated alpha.4 verified change circulation."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.chat_service import CortexChatService
from cortex.coding_workspace import (
    CONTRACT_SCHEMA,
    create_patch_proposal,
    default_verification_contract,
    verify_patch_in_isolated_worktree,
)
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, NativeAgentRuntime, ScriptedAgentAdapter
from cortex.secret_store import MemorySecretStore
from cortex.store import Store


def contract(targets: list[str], *, passes: bool) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": CONTRACT_SCHEMA,
        "policy_id": "test-host-policy",
        "targets": sorted(targets),
        "steps": [{
            "id": "host_decision",
            "argv": ["{python}", "-c", "raise SystemExit(0)" if passes else "raise SystemExit(7)"],
            "timeout_seconds": 30,
        }],
        "model_selected": False,
        "caller_selected": False,
        "promotion_authorized": False,
    }
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    body["contract_hash"] = hashlib.sha256(encoded).hexdigest()
    return body


class VerifiedImprovementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# Before\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.host, check=True)
        subprocess.run(["git", "config", "user.email", "cortex@example.invalid"], cwd=self.host, check=True)
        subprocess.run(["git", "config", "user.name", "Cortex Test"], cwd=self.host, check=True)
        subprocess.run(["git", "add", "."], cwd=self.host, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.host, check=True)
        home = ensure_home(self.base / "home")
        self.store = Store(home / "cortex.db")
        self.repo = "VerifiedHost"
        bootstrap_repository(home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def proposal_session(self, factory) -> tuple[CortexChatService, dict[str, object], str]:
        patch = (
            "diff --git a/README.md b/README.md\n"
            "--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-# Before\n+# After\n"
        )
        adapter = ScriptedAgentAdapter([
            {"tool_calls": [{"id": "p", "name": "workspace.propose_patch", "arguments": {"summary": "heading", "patch": patch}}], "finish_reason": "tool_calls"},
            {"public_output": "Review it.", "finish_reason": "stop"},
        ])
        run = NativeAgentRuntime(self.store, self.repo).run(
            "propose",
            adapter=adapter,
            grant=CapabilityGrant(workspace_root=str(self.host), allowed_tools=("workspace.propose_patch",)),
        )
        service = CortexChatService(
            self.store,
            self.repo,
            secrets=MemorySecretStore(),
            verification_contract_factory=factory,
        )
        chat = service.create_session({"provider": "fixture", "model_id": "fixture"})
        session_id = str(chat["session_id"])
        self.store.set_setting(f"ui:chat:last_trajectory:{session_id}", run["trajectory_receipt_hash"])
        return service, service.workspace(session_id)["proposals"][0], session_id

    def test_host_contract_verifies_in_isolation_and_is_immutable(self) -> None:
        service, proposal, session_id = self.proposal_session(lambda _root, targets: contract(targets, passes=True))
        receipt = service.verify_workspace_patch(session_id, {
            "proposal_hash": proposal["proposal_hash"],
            "approval_challenge": proposal["approval_challenge"],
            "caller_contract": contract(["README.md"], passes=False),
        })
        self.assertEqual(receipt["status"], "verified")
        self.assertTrue(receipt["isolated_worktree"])
        self.assertFalse(receipt["active_tree_mutated"])
        self.assertFalse(receipt["contract"]["model_selected"])
        self.assertFalse(receipt["contract"]["caller_selected"])
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# Before\n")
        self.assertTrue(self.store.verify_symbiotic_receipt(self.repo, receipt["receipt_hash"])["valid"])

    def test_failed_host_verification_is_held_and_cannot_promote(self) -> None:
        service, proposal, session_id = self.proposal_session(lambda _root, targets: contract(targets, passes=False))
        receipt = service.verify_workspace_patch(session_id, {
            "proposal_hash": proposal["proposal_hash"],
            "approval_challenge": proposal["approval_challenge"],
            "contract": contract(["README.md"], passes=True),
        })
        self.assertEqual(receipt["status"], "held")
        with self.assertRaisesRegex(ValueError, "does not authorize"):
            service.apply_workspace_patch(session_id, {
                "proposal_hash": proposal["proposal_hash"],
                "approval_challenge": proposal["approval_challenge"],
                "verification_receipt_hash": receipt["receipt_hash"],
            })
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# Before\n")

    def test_head_change_after_verification_blocks_promotion(self) -> None:
        service, proposal, session_id = self.proposal_session(lambda _root, targets: contract(targets, passes=True))
        receipt = service.verify_workspace_patch(session_id, {
            "proposal_hash": proposal["proposal_hash"],
            "approval_challenge": proposal["approval_challenge"],
        })
        (self.host / "other.txt").write_text("drift\n", encoding="utf-8")
        subprocess.run(["git", "add", "other.txt"], cwd=self.host, check=True)
        subprocess.run(["git", "commit", "-qm", "advance head"], cwd=self.host, check=True)
        with self.assertRaisesRegex(ValueError, "HEAD changed"):
            service.apply_workspace_patch(session_id, {
                "proposal_hash": proposal["proposal_hash"],
                "approval_challenge": proposal["approval_challenge"],
                "verification_receipt_hash": receipt["receipt_hash"],
            })
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# Before\n")

    def test_diff_header_cannot_hide_a_different_git_target(self) -> None:
        disguised = (
            "diff --git a/README.md b/README.md\n"
            "--- a/other.txt\n+++ b/other.txt\n@@ -0,0 +1 @@\n+hidden\n"
        )
        proposal = create_patch_proposal(self.host, disguised, "disguised target")
        policy = default_verification_contract(self.host, list(proposal["targets"]))
        with self.assertRaisesRegex(ValueError, "targets do not match"):
            verify_patch_in_isolated_worktree(self.host, proposal, policy)


if __name__ == "__main__":
    unittest.main()
