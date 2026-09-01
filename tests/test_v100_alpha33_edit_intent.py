"""Alpha.33 deterministic edit-intent and private-corpus closure tests."""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from cortex.coding_workspace import verify_patch_in_isolated_worktree
from cortex.edit_intent import INTENT_SCHEMA, compile_edit_intent, verify_edit_intent_compilation


class EditIntentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "module.py").write_text("def value():\n    return 0\n", encoding="utf-8")
        (self.root / "external_test.py").write_text("from module import value\nassert value() == 1\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "cortex@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Cortex Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)
        self.intent = {
            "schema_version": INTENT_SCHEMA,
            "summary": "return the declared value",
            "edits": [{"path": "module.py", "old": "    return 0\n", "new": "    return 1\n"}],
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_structured_intent_compiles_to_verifiable_exact_patch(self) -> None:
        result = compile_edit_intent(self.root, json.dumps(self.intent), allowed_targets=["module.py"])
        self.assertTrue(result["compiled_not_model_authored_diff"])
        self.assertTrue(verify_edit_intent_compilation(self.root, result)["valid"])
        proposal = result["proposal"]
        contract = {
            "schema_version": "cortex-host-verification-contract/1.0",
            "policy_id": "alpha33-test", "targets": ["module.py"],
            "steps": [{"id": "external", "argv": ["{python}", "external_test.py"], "timeout_seconds": 30}],
            "model_selected": False, "caller_selected": False, "promotion_authorized": False,
        }
        import hashlib
        contract["contract_hash"] = hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        verification = verify_patch_in_isolated_worktree(self.root, proposal, contract)
        self.assertEqual(verification["status"], "verified")
        self.assertEqual((self.root / "module.py").read_text(encoding="utf-8"), "def value():\n    return 0\n")

    def test_ambiguous_preimage_and_scope_escape_fail_closed(self) -> None:
        ambiguous = {**self.intent, "edits": [{"path": "module.py", "old": " ", "new": "  "}]}
        with self.assertRaisesRegex(ValueError, "exactly once"):
            compile_edit_intent(self.root, ambiguous, allowed_targets=["module.py"])
        escaped = {**self.intent, "edits": [{"path": "../outside.py", "old": "x", "new": "y"}]}
        with self.assertRaisesRegex(ValueError, "scope"):
            compile_edit_intent(self.root, escaped, allowed_targets=["module.py"])

    def test_unknown_fields_and_stale_preimages_do_not_compile(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown"):
            compile_edit_intent(self.root, {**self.intent, "success": True}, allowed_targets=["module.py"])
        result = compile_edit_intent(self.root, self.intent, allowed_targets=["module.py"])
        (self.root / "module.py").write_text("def value():\n    return 2\n", encoding="utf-8")
        self.assertFalse(verify_edit_intent_compilation(self.root, result)["valid"])

    def test_compilation_never_grants_authority(self) -> None:
        result = compile_edit_intent(self.root, self.intent, allowed_targets=["module.py"])
        for field in ("host_mutate_authorized", "execution_authorized", "memory_admission_authorized", "policy_effect"):
            self.assertFalse(result[field])


if __name__ == "__main__":
    unittest.main()
