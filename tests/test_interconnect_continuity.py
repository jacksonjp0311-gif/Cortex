"""v7.0 interconnect expansion — mesh surfaces body epoch + phase."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.interconnect import mesh_dashboard, mesh_status
from cortex.store import Store


class InterconnectContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# ic\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "ICHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_mesh_includes_continuity(self) -> None:
        m = mesh_status(self.store, "ICHost", governor=self.gov, home=self.home)
        self.assertTrue(m["schema_version"].startswith("cortex-interconnect/1."))
        cont = m.get("continuity") or {}
        self.assertTrue(cont.get("body_epoch_id"), cont)
        self.assertIn(cont.get("runtime_phase"), {
            "QUIESCENT", "OBSERVE", "INDEX", "EVIDENCE_FREEZE", "ADAPT",
            "CONSOLIDATE", "WITNESS", "PROMOTE", "FEDERATE", "QUARANTINE",
            "REPAIR", "VERIFY_REPAIR", "ROLLBACK",
        })
        self.assertIn("planes", m)
        dash = mesh_dashboard(self.store, "ICHost", governor=self.gov, home=self.home)
        self.assertEqual(dash.get("body_epoch_id"), cont.get("body_epoch_id"))
        self.assertEqual(dash.get("runtime_phase"), cont.get("runtime_phase"))


if __name__ == "__main__":
    unittest.main()
