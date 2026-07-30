"""v6.24 Memory Simplex — EVIDENCE_BASELINE controller."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.eval_coupling import ABLATIONS, _run_case
from cortex.governor import Governor
from cortex.memory_simplex import (
    CONTROLLER_EVIDENCE_BASELINE,
    resolve_controller,
    simplex_lift_report,
)
from cortex.store import Store


class MemorySimplexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "sx_host"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text(
            "# Simplex\n\n## Evidence\n\nbaseline controller\n", encoding="utf-8"
        )
        (self.repo_path / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "SxHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_ablation_includes_evidence_baseline(self) -> None:
        self.assertIn("evidence_baseline", ABLATIONS)

    def test_resolve_read_only_transfers(self) -> None:
        r = resolve_controller(governance_mode="read_only")
        self.assertEqual(r["controller"], CONTROLLER_EVIDENCE_BASELINE)
        self.assertTrue(r["transfer_to_baseline"])

    def test_resolve_normal_advanced(self) -> None:
        r = resolve_controller(governance_mode="normal")
        self.assertEqual(r["controller"], "advanced")
        self.assertFalse(r["transfer_to_baseline"])

    def test_run_case_evidence_baseline(self) -> None:
        case = {
            "id": "sx_readme",
            "query": "README evidence baseline",
            "expected_substrings": ["README"],
        }
        r = _run_case(
            self.store, "SxHost", case, mode="evidence_baseline", limit=12, top_k=5
        )
        self.assertEqual(r["mode"], "evidence_baseline")
        self.assertIn("returned_paths", r)

    def test_simplex_lift_report(self) -> None:
        lift = simplex_lift_report(
            {"recall_at_k": 1.0, "mrr": 0.9},
            {"recall_at_k": 0.8, "mrr": 0.7},
        )
        self.assertTrue(lift["advanced_beats_trusted"])
        self.assertAlmostEqual(lift["lift_recall"], 0.2, places=5)


if __name__ == "__main__":
    unittest.main()
