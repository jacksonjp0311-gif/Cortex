"""Capability + operation registry fail-closed."""

from __future__ import annotations

import unittest

from cortex.capabilities import (
    OPERATION_REGISTRY,
    issue_for_controller,
    validate_capability,
)
from cortex.controller_scope import HOST_MUTATION, check_write


class ControllerFirewallTests(unittest.TestCase):
    def test_host_mutation_never(self) -> None:
        d = check_write("advanced", HOST_MUTATION)
        self.assertFalse(d.allowed)

    def test_unknown_operation_denied(self) -> None:
        cap = issue_for_controller("R", "advanced")
        d = validate_capability(cap, repo="R", operation="not_a_real_op")
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "unknown_operation")

    def test_missing_capability_denied(self) -> None:
        d = validate_capability(None, repo="R", operation="ranker_train")
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "missing_capability")

    def test_expired_capability_denied(self) -> None:
        cap = issue_for_controller("R", "advanced", ttl_s=-1)
        d = validate_capability(cap, repo="R", operation="ranker_train")
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "capability_expired")

    def test_wrong_repo_denied(self) -> None:
        cap = issue_for_controller("A", "advanced")
        d = validate_capability(cap, repo="B", operation="ranker_train")
        self.assertFalse(d.allowed)

    def test_baseline_blocks_ranker(self) -> None:
        cap = issue_for_controller("R", "evidence_baseline")
        d = validate_capability(cap, repo="R", operation="ranker_train")
        self.assertFalse(d.allowed)

    def test_repair_allowlist(self) -> None:
        cap = issue_for_controller("R", "repair")
        d = validate_capability(cap, repo="R", operation="repair_synapse_remove")
        self.assertTrue(d.allowed)
        d2 = validate_capability(cap, repo="R", operation="foreign_emerge")
        self.assertFalse(d2.allowed)

    def test_registry_has_ranker(self) -> None:
        self.assertIn("ranker_train", OPERATION_REGISTRY)


if __name__ == "__main__":
    unittest.main()
