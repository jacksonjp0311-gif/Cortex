"""Governed coding-workspace gates for the v10 alpha lineage."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.chat_service import CortexChatService
from cortex.coding_workspace import apply_approved_patch, create_patch_proposal
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, NativeAgentRuntime, ScriptedAgentAdapter
from cortex.secret_store import MemorySecretStore
from cortex.store import Store


class CodingWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.host = self.base / "host"
        self.host.mkdir()
        (self.host / "README.md").write_text("# Before\n", encoding="utf-8")
        (self.host / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.host, check=True)
        subprocess.run(["git", "config", "user.email", "cortex@example.invalid"], cwd=self.host, check=True)
        subprocess.run(["git", "config", "user.name", "Cortex Test"], cwd=self.host, check=True)
        subprocess.run(["git", "add", "."], cwd=self.host, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.host, check=True)
        self.home = ensure_home(self.base / "home")
        self.store = Store(self.home / "cortex.db")
        self.repo = "CodingHost"
        bootstrap_repository(self.home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    @staticmethod
    def readme_patch(after: str = "# After") -> str:
        return (
            "diff --git a/README.md b/README.md\n"
            "--- a/README.md\n"
            "+++ b/README.md\n"
            "@@ -1 +1 @@\n"
            "-# Before\n"
            f"+{after}\n"
        )

    def test_proposal_tool_is_observational_until_operator_approval(self) -> None:
        patch = self.readme_patch()
        adapter = ScriptedAgentAdapter([
            {
                "tool_calls": [{
                    "id": "proposal-1",
                    "name": "workspace.propose_patch",
                    "arguments": {"summary": "Update heading", "patch": patch},
                }],
                "finish_reason": "tool_calls",
            },
            {"public_output": "Proposal awaits operator approval.", "finish_reason": "stop"},
        ])
        result = NativeAgentRuntime(self.store, self.repo).run(
            "Propose a heading update",
            adapter=adapter,
            grant=CapabilityGrant(
                workspace_root=str(self.host),
                allowed_tools=("filesystem.read", "workspace.propose_patch"),
            ),
        )
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# Before\n")
        trajectory = self.store.symbiotic_receipt(result["trajectory_receipt_hash"], repo=self.repo)
        proposal = trajectory["tool_results"][0]["output"]
        self.assertTrue(proposal["proposal_only"])
        self.assertFalse(proposal["host_mutate_authorized"])
        self.assertFalse(proposal["execution_authorized"])

    def test_canonical_review_approval_apply_and_duplicate_are_exactly_once(self) -> None:
        patch = self.readme_patch()
        adapter = ScriptedAgentAdapter([
            {
                "tool_calls": [{"id": "proposal-2", "name": "workspace.propose_patch", "arguments": {"summary": "Update heading", "patch": patch}}],
                "finish_reason": "tool_calls",
            },
            {"public_output": "Review the proposal.", "finish_reason": "stop"},
        ])
        result = NativeAgentRuntime(self.store, self.repo).run(
            "change heading",
            adapter=adapter,
            grant=CapabilityGrant(workspace_root=str(self.host), allowed_tools=("workspace.propose_patch",)),
        )
        service = CortexChatService(self.store, self.repo, secrets=MemorySecretStore())
        chat = service.create_session({"provider": "fixture", "model_id": "fixture"})
        self.store.set_setting(f"ui:chat:last_trajectory:{chat['session_id']}", result["trajectory_receipt_hash"])
        surface = service.workspace(chat["session_id"])
        self.assertEqual(surface["state"], "REVIEW_REQUIRED")
        proposal = surface["proposals"][0]
        with self.assertRaisesRegex(ValueError, "approval challenge"):
            service.apply_workspace_patch(chat["session_id"], {"proposal_hash": proposal["proposal_hash"], "approval_challenge": "wrong"})
        with self.assertRaisesRegex(ValueError, "verification receipt"):
            service.apply_workspace_patch(
                chat["session_id"],
                {"proposal_hash": proposal["proposal_hash"], "approval_challenge": proposal["approval_challenge"]},
            )
        verification = service.verify_workspace_patch(
            chat["session_id"],
            {"proposal_hash": proposal["proposal_hash"], "approval_challenge": proposal["approval_challenge"]},
        )
        self.assertEqual(verification["status"], "verified")
        self.assertTrue(verification["isolated_worktree"])
        self.assertFalse(verification["active_tree_mutated"])
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# Before\n")
        receipt = service.apply_workspace_patch(
            chat["session_id"],
            {
                "proposal_hash": proposal["proposal_hash"],
                "approval_challenge": proposal["approval_challenge"],
                "verification_receipt_hash": verification["receipt_hash"],
                "patch": "caller substitution must be ignored",
            },
        )
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# After\n")
        self.assertEqual(receipt["status"], "applied_verified")
        self.assertTrue(receipt["operator_approval_verified"])
        self.assertFalse(receipt["model_host_mutate_authorized"])
        self.assertFalse(receipt["model_execution_authorized"])
        duplicate = service.apply_workspace_patch(
            chat["session_id"],
            {
                "proposal_hash": proposal["proposal_hash"],
                "approval_challenge": proposal["approval_challenge"],
                "verification_receipt_hash": verification["receipt_hash"],
            },
        )
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# After\n")
        application = service.workspace(chat["session_id"])["proposals"][0]["application"]
        self.assertEqual(application["receipt_hash"], receipt["receipt_hash"])
        self.assertTrue(application["targets_current"])
        (self.host / "README.md").write_text("# Later drift\n", encoding="utf-8")
        self.assertFalse(service.workspace(chat["session_id"])["proposals"][0]["application"]["targets_current"])

    def test_stale_preimage_and_protected_path_fail_closed(self) -> None:
        proposal = create_patch_proposal(self.host, self.readme_patch(), "Update heading")
        tampered = {**proposal, "preimage_hashes": {}}
        with self.assertRaisesRegex(ValueError, "invalid or stale"):
            apply_approved_patch(self.host, tampered)
        (self.host / "README.md").write_text("# Drifted\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid or stale"):
            apply_approved_patch(self.host, proposal)
        protected = (
            "diff --git a/.cortex/state b/.cortex/state\n--- a/.cortex/state\n+++ b/.cortex/state\n@@ -1 +1 @@\n-a\n+b\n"
        )
        with self.assertRaisesRegex(ValueError, "protected"):
            create_patch_proposal(self.host, protected, "unsafe")
        evaluator = (
            "diff --git a/tests/test_gate.py b/tests/test_gate.py\n--- a/tests/test_gate.py\n+++ b/tests/test_gate.py\n@@ -1 +1 @@\n-a\n+b\n"
        )
        with self.assertRaisesRegex(ValueError, "protected"):
            create_patch_proposal(self.host, evaluator, "weaken evaluator")

    def test_failed_python_verification_rolls_back_source(self) -> None:
        patch = (
            "diff --git a/sample.py b/sample.py\n"
            "--- a/sample.py\n"
            "+++ b/sample.py\n"
            "@@ -1 +1 @@\n"
            "-VALUE = 1\n"
            "+def broken(:\n"
        )
        proposal = create_patch_proposal(self.host, patch, "Introduce invalid syntax")
        with self.assertRaisesRegex(RuntimeError, "post-apply verification failed"):
            apply_approved_patch(self.host, proposal)
        self.assertEqual((self.host / "sample.py").read_text(encoding="utf-8"), "VALUE = 1\n")


if __name__ == "__main__":
    unittest.main()
