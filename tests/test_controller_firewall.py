"""Controller write firewall."""

from __future__ import annotations

import unittest

from cortex.controller_scope import (
    ADAPTIVE_WRITE,
    HOST_MUTATION,
    check_adaptive_op,
    check_write,
)


class ControllerFirewallTests(unittest.TestCase):
    def test_host_mutation_never(self) -> None:
        d = check_write("advanced", HOST_MUTATION)
        self.assertFalse(d.allowed)

    def test_baseline_blocks_adaptive(self) -> None:
        d = check_adaptive_op("evidence_baseline", "ranker_train")
        self.assertFalse(d.allowed)
        d2 = check_write("evidence_baseline", ADAPTIVE_WRITE, operation="structure_invent")
        self.assertFalse(d2.allowed)

    def test_advanced_allows_adaptive(self) -> None:
        d = check_adaptive_op("advanced", "structure_invent")
        self.assertTrue(d.allowed)

    def test_quarantine_blocks_adaptive(self) -> None:
        d = check_adaptive_op("quarantine", "fusion_tick")
        self.assertFalse(d.allowed)


if __name__ == "__main__":
    unittest.main()
