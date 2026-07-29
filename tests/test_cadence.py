"""Cadence automation smoke (few cycles)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.cadence import run_cadence
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.packs import install_pack
from cortex.store import Store

ENGINE = Path(__file__).resolve().parents[1]


class CadenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "cadhost"
        self.repo.mkdir()
        (self.repo / "README.md").write_text("# Cad\n\n## Architecture\n\nx\n", encoding="utf-8")
        (self.repo / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "CadHost")
        self.gov = Governor(self.home, self.store)
        install_pack(ENGINE / "packs" / "cortex-core-intel-v1", self.home, force=True)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_cadence_few_cycles(self) -> None:
        report = run_cadence(
            self.home,
            self.store,
            self.gov,
            "CadHost",
            cycles=5,
            budget=350,
            evolve_every=2,
            seal_every=5,
            hygiene_every=2,
        )
        self.assertEqual(report["cycles"], 5)
        self.assertGreaterEqual(report["stats"]["activates"], 5)
        self.assertGreaterEqual(report["stats"]["evolves"], 1)
        self.assertIn("report_path", report)


if __name__ == "__main__":
    unittest.main()
