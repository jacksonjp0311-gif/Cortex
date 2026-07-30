"""Measure gate: eval-coupling ablations."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.eval_coupling import DEFAULT_CORPUS, run_eval_coupling
from cortex.governor import Governor
from cortex.store import Store


class EvalCouplingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        # Point at real engine tree so corpus path substrings exist when indexed
        self.engine = Path(__file__).resolve().parents[1]
        self.store = Store(self.home / "cortex.db")
        # Attach engine as EvalHost (read-only assimilate)
        bootstrap_repository(
            self.home, self.store, self.engine, "EvalHost", force=True
        )
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_eval_coupling_runs(self) -> None:
        # Use first 3 cases for speed
        report = run_eval_coupling(
            self.home,
            self.store,
            self.gov,
            "EvalHost",
            corpus=list(DEFAULT_CORPUS)[:3],
            limit=10,
            top_k=5,
            persist=True,
        )
        self.assertEqual(report["schema_version"], "cortex-eval-coupling/1.0")
        self.assertIn("baseline", report["ablations"])
        self.assertIn("no_spectral", report["ablations"])
        self.assertIn("no_ranker", report["ablations"])
        self.assertIn("gate", report)
        self.assertIn("recommendation", report)
        self.assertIn("winner", report)
        for mode, data in report["ablations"].items():
            self.assertIn("recall_at_k", data)


if __name__ == "__main__":
    unittest.main()
