"""v7.0 Continuity snapshot and epoch-bound capabilities."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.capabilities import issue_for_controller, validate_epoch_capability
from cortex.config import ensure_home
from cortex.continuity import continuity_report, snapshot_continuity
from cortex.epoch import ensure_current_epoch
from cortex.store import Store


class ContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# c\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "CHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_snapshot_planes(self) -> None:
        from cortex.epoch import ensure_current_epoch

        ensure_current_epoch(self.store, "CHost", reason="test_setup")
        s = snapshot_continuity(self.store, "CHost")
        d = s.to_dict()
        self.assertIn("body_epoch", d)
        self.assertIn("runtime_phase", d)
        self.assertIn("evidence_plane", d)
        self.assertIn("forbidden_flows", d)
        r = continuity_report(self.store, "CHost")
        self.assertTrue(r.get("epoch_verified", {}).get("ok"))
        self.assertTrue(r.get("observe_only"))

    def test_capability_epoch_mismatch(self) -> None:
        ep = ensure_current_epoch(self.store, "CHost")
        cap = issue_for_controller("CHost", "advanced", store=self.store)
        ok = validate_epoch_capability(
            cap,
            repo="CHost",
            operation="ranker_train",
            body_epoch_id=ep.epoch_id,
            evidence_root_hash=ep.evidence_root_hash,
            constitutional_config_hash=ep.constitutional_config_hash,
        )
        self.assertTrue(ok.allowed, ok)
        bad = validate_epoch_capability(
            cap,
            repo="CHost",
            operation="ranker_train",
            body_epoch_id="not-the-epoch",
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(bad.reason, "capability_epoch_mismatch")

    def test_same_repo_influence_and_mesh_report(self) -> None:
        from cortex.continuity import epoch_compatible_influence, mesh_continuity_report
        from cortex.epoch import ensure_current_epoch

        ensure_current_epoch(self.store, "CHost", reason="test_setup")
        inf = epoch_compatible_influence("CHost", "CHost", self.store)
        self.assertTrue(inf["allowed"], inf)
        mesh = mesh_continuity_report(self.store, repos=["CHost"])
        self.assertEqual(mesh["host_count"], 1)
        self.assertTrue(mesh.get("version_aligned"))


if __name__ == "__main__":
    unittest.main()
