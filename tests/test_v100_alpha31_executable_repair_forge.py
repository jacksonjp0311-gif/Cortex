"""Alpha.31 answer-sealed executable repair forge adversarial tests."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from cortex.executable_repair_forge import (
    build_executable_repair_bundle,
    commission_executable_repair_forge,
    verify_executable_repair_bundle,
    verify_executable_repair_forge_result,
)


class ExecutableRepairForgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.public, self.private = build_executable_repair_bundle(secret_seed="alpha31-test-secret")

    def test_public_corpus_contains_no_tests_or_reference_patches(self) -> None:
        self.assertTrue(verify_executable_repair_bundle(self.public, self.private)["valid"])
        self.assertEqual(self.public["case_count"], 4)
        for case in self.public["cases"]:
            self.assertEqual(sorted(case["files"]), ["module.py"])
            self.assertNotIn("reference_patch", case)
            self.assertNotIn("external_test.py", case["files"])

    def test_private_evaluator_substitution_fails_identity(self) -> None:
        tampered = copy.deepcopy(self.private)
        tampered["cases"][0]["external_test"] = "raise SystemExit(0)\n"
        audit = verify_executable_repair_bundle(self.public, tampered)
        self.assertFalse(audit["valid"])
        self.assertTrue(any("identity" in error or "commitment" in error for error in audit["errors"]))

    def test_reference_preflight_measures_each_repair_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            result = commission_executable_repair_forge(self.public, self.private, Path(parent))
        self.assertEqual(result["state"], "EXECUTABLE_REPAIR_FORGE_READY")
        self.assertEqual(result["reference_repairs_measured"], 4)
        self.assertEqual(result["additional_model_calls"], 0)
        self.assertTrue(verify_executable_repair_forge_result(result)["valid"])
        self.assertTrue(all(not case["baseline_pass"] for case in result["cases"]))
        self.assertTrue(all(case["reference_candidate_pass"] for case in result["cases"]))
        self.assertTrue(all(not case["active_tree_mutated"] for case in result["cases"]))

    def test_caller_cannot_promote_a_held_or_tampered_result(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            result = commission_executable_repair_forge(self.public, self.private, Path(parent))
        forged = {**result, "general_improvement_established": True}
        self.assertFalse(verify_executable_repair_forge_result(forged)["valid"])


if __name__ == "__main__":
    unittest.main()
