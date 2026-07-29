"""Multi-lane continuum evolution smoke."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.continuum import run_continuum
from cortex.governor import Governor
from cortex.store import Store

ENGINE = Path(__file__).resolve().parents[1]


class ContinuumTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "continuum_host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# Continuum\n\n## Architecture\n\nlocal first\n",
            encoding="utf-8",
        )
        (self.repo / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "ContHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_continuum_all_lanes(self) -> None:
        report = run_continuum(
            self.home,
            self.store,
            self.gov,
            "ContHost",
            cycles=4,
            budget=350,
            progress=False,
            pack_dir=ENGINE / "packs" / "cortex-core-intel-v1",
        )
        self.assertEqual(report["schema_version"], "cortex-continuum/1.0")
        lanes = report["lanes"]
        for name in (
            "packs",
            "use_teach_measure",
            "cadence",
            "prune_graph",
            "stream_glyphs",
            "ops_surface",
        ):
            self.assertIn(name, lanes, msg=f"missing lane {name}")
        self.assertGreaterEqual(report["summary"]["lanes_ok"], 4)
        self.assertIn("report_path", report)
        self.assertGreaterEqual(
            int((lanes["cadence"].get("stats") or {}).get("activates") or 0), 1
        )
        self.assertTrue(lanes["ops_surface"].get("prove_surface"))


if __name__ == "__main__":
    unittest.main()
