"""Counterfactual source-improvement gates for Cortex alpha.5."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.chat_service import CortexChatService
from cortex.coding_workspace import CONTRACT_SCHEMA as VERIFY_CONTRACT_SCHEMA, create_patch_proposal, verify_patch_in_isolated_worktree
from cortex.config import ensure_home
from cortex.native_agent import CapabilityGrant, NativeAgentRuntime, ScriptedAgentAdapter
from cortex.secret_store import MemorySecretStore
from cortex.source_improvement import create_source_improvement_contract, run_source_improvement_trial, verify_source_improvement_result
from cortex.store import Store


def digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verification_contract(*, passes: bool = True) -> dict[str, object]:
    body: dict[str, object] = {
        "schema_version": VERIFY_CONTRACT_SCHEMA,
        "policy_id": "alpha5-host-verifier",
        "targets": ["README.md"],
        "steps": [{
            "id": "isolated_safety",
            "argv": ["{python}", "-c", "raise SystemExit(0)" if passes else "raise SystemExit(9)"],
            "timeout_seconds": 30,
        }],
        "model_selected": False,
        "caller_selected": False,
        "promotion_authorized": False,
    }
    body["contract_hash"] = digest(body)
    return body


def patch_sensitive_contract(root: str | Path, proposal: dict[str, object], verification: dict[str, object], *, mode: str = "repair") -> dict[str, object]:
    contract = create_source_improvement_contract(root, proposal, verification)
    programs = {
        "repair": "from pathlib import Path; raise SystemExit(0 if '# After' in Path('README.md').read_text() else 1)",
        "maintenance": "raise SystemExit(0)",
        "regression": "from pathlib import Path; raise SystemExit(1 if '# After' in Path('README.md').read_text() else 0)",
    }
    contract["evaluator_steps"] = [{"id": "frozen_outcome", "argv": ["{python}", "-c", programs[mode]], "timeout_seconds": 30}]
    contract["contract_hash"] = digest({key: value for key, value in contract.items() if key != "contract_hash"})
    return contract


class SourceImprovementTests(unittest.TestCase):
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
        self.patch = "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-# Before\n+# After\n"
        self.proposal = create_patch_proposal(self.host, self.patch, "repair heading")
        verification = verify_patch_in_isolated_worktree(self.host, self.proposal, verification_contract())
        self.verification = {**verification, "kind": "coding_patch_verification", "receipt_hash": digest(verification)}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def trial(self, mode: str) -> dict[str, object]:
        contract = patch_sensitive_contract(self.host, self.proposal, self.verification, mode=mode)
        return run_source_improvement_trial(self.host, self.proposal, self.verification, contract)

    def test_paired_trial_measures_a_bounded_repair_without_mutating_active_tree(self) -> None:
        result = self.trial("repair")
        self.assertEqual(result["status"], "REPAIR_MEASURED")
        self.assertFalse(result["arms"]["baseline"]["all_host_checks_pass"])
        self.assertTrue(result["arms"]["candidate"]["all_host_checks_pass"])
        self.assertEqual(result["paired_effect"], 1)
        self.assertFalse(result["general_improvement_established"])
        self.assertFalse(result["host_mutate_authorized"])
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# Before\n")
        self.assertTrue(verify_source_improvement_result(result)["valid"])

    def test_both_pass_is_maintenance_not_improvement(self) -> None:
        result = self.trial("maintenance")
        self.assertEqual(result["status"], "VERIFIED_MAINTENANCE")
        self.assertEqual(result["paired_effect"], 0)
        self.assertFalse(result["bounded_repair_established"])

    def test_candidate_regression_is_detected_and_tamper_fails(self) -> None:
        result = self.trial("regression")
        self.assertEqual(result["status"], "REGRESSION_DETECTED")
        self.assertEqual(result["paired_effect"], -1)
        tampered = {**result, "status": "REPAIR_MEASURED"}
        self.assertFalse(verify_source_improvement_result(tampered)["valid"])


class SourceImprovementServiceTests(unittest.TestCase):
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
        self.repo = "Alpha5Host"
        bootstrap_repository(home, self.store, self.host, self.repo)

    def tearDown(self) -> None:
        self.store.close()
        self.temporary.cleanup()

    def service_and_proposal(self, mode: str = "repair") -> tuple[CortexChatService, dict[str, object], str]:
        patch = "diff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md\n@@ -1 +1 @@\n-# Before\n+# After\n"
        adapter = ScriptedAgentAdapter([
            {"tool_calls": [{"id": "p", "name": "workspace.propose_patch", "arguments": {"summary": "heading", "patch": patch}}], "finish_reason": "tool_calls"},
            {"public_output": "Review it.", "finish_reason": "stop"},
        ])
        run = NativeAgentRuntime(self.store, self.repo).run(
            "propose", adapter=adapter,
            grant=CapabilityGrant(workspace_root=str(self.host), allowed_tools=("workspace.propose_patch",)),
        )
        service = CortexChatService(
            self.store, self.repo, secrets=MemorySecretStore(),
            verification_contract_factory=lambda _root, _targets: verification_contract(),
            improvement_contract_factory=lambda root, proposal, receipt: patch_sensitive_contract(root, proposal, receipt, mode=mode),
        )
        chat = service.create_session({"provider": "fixture", "model_id": "fixture"})
        session_id = str(chat["session_id"])
        self.store.set_setting(f"ui:chat:last_trajectory:{session_id}", run["trajectory_receipt_hash"])
        return service, service.workspace(session_id)["proposals"][0], session_id

    def test_service_requires_host_trial_then_promotes_exact_measured_repair(self) -> None:
        service, proposal, session_id = self.service_and_proposal()
        verification = service.verify_workspace_patch(session_id, {
            "proposal_hash": proposal["proposal_hash"], "approval_challenge": proposal["approval_challenge"],
        })
        trial = service.run_workspace_improvement_trial(session_id, {
            "proposal_hash": proposal["proposal_hash"], "approval_challenge": proposal["approval_challenge"],
            "caller_improved": True,
        })
        self.assertEqual(trial["status"], "REPAIR_MEASURED")
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# Before\n")
        application = service.apply_workspace_patch(session_id, {
            "proposal_hash": proposal["proposal_hash"], "approval_challenge": proposal["approval_challenge"],
            "verification_receipt_hash": verification["receipt_hash"],
            "improvement_result_hash": trial["receipt_hash"],
        })
        self.assertEqual(application["change_classification"], "REPAIR_MEASURED")
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# After\n")

    def test_regression_trial_blocks_promotion(self) -> None:
        service, proposal, session_id = self.service_and_proposal("regression")
        verification = service.verify_workspace_patch(session_id, {
            "proposal_hash": proposal["proposal_hash"], "approval_challenge": proposal["approval_challenge"],
        })
        trial = service.run_workspace_improvement_trial(session_id, {
            "proposal_hash": proposal["proposal_hash"], "approval_challenge": proposal["approval_challenge"],
        })
        with self.assertRaisesRegex(ValueError, "blocks"):
            service.apply_workspace_patch(session_id, {
                "proposal_hash": proposal["proposal_hash"], "approval_challenge": proposal["approval_challenge"],
                "verification_receipt_hash": verification["receipt_hash"],
                "improvement_result_hash": trial["receipt_hash"],
            })
        self.assertEqual((self.host / "README.md").read_text(encoding="utf-8"), "# Before\n")


if __name__ == "__main__":
    unittest.main()
