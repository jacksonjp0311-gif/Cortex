"""Immunity scan / quarantine / plan."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.immunity import open_wound, plan_repair, quarantine_from_wound, scan_wounds
from cortex.lineage import record_artifact
from cortex.quarantine import is_quarantined
from cortex.store import Store


class ImmunityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "home")
        self.repo_path = Path(self.temp.name) / "im"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# I\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "ImHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_poison_trace_quarantine(self) -> None:
        record_artifact(
            self.store,
            "ImHost",
            artifact_id="poison_mem",
            artifact_type="episode",
            origin_memory_ids=["99"],
            parent_ids=["mem:99"],
        )
        record_artifact(
            self.store,
            "ImHost",
            artifact_id="syn_poison",
            artifact_type="invented_synapse",
            parent_ids=["poison_mem"],
            origin_memory_ids=["99"],
        )
        w = open_wound(
            self.store,
            "ImHost",
            kind="poisoned_memory",
            origin_ids=["poison_mem"],
            summary="test poison",
            severity="high",
        )
        q = quarantine_from_wound(
            self.store, "ImHost", wound_id=w["wound_id"], reason="test"
        )
        self.assertTrue(q.get("envelope_id"))
        self.assertTrue(is_quarantined(self.store, "ImHost", "syn_poison"))
        plan = plan_repair(self.store, "ImHost", w["wound_id"])
        self.assertIn("plan_id", plan)
        sc = scan_wounds(self.store, "ImHost")
        self.assertIn("open_wounds", sc)


if __name__ == "__main__":
    unittest.main()
