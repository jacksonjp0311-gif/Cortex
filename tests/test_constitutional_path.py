"""v7.1 legal path planning — no mutation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.constitutional_geometry import coordinate_from_bits
from cortex.constitutional_path import compile_legal_path
from cortex.epoch import ensure_current_epoch
from cortex.store import Store


class ConstitutionalPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# path\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "PathHost")
        ensure_current_epoch(self.store, "PathHost", reason="test")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_path_planning_no_mutation(self) -> None:
        n0 = self.store.db.execute(
            "SELECT COUNT(1) AS c FROM body_epochs WHERE repo=?", ("PathHost",)
        ).fetchone()["c"]
        eid0 = self.store.db.execute(
            "SELECT epoch_id FROM body_epochs WHERE repo=? ORDER BY created_at DESC LIMIT 1",
            ("PathHost",),
        ).fetchone()["epoch_id"]
        coord = coordinate_from_bits((1, 1, 1, 0))
        path = compile_legal_path(
            "promote",
            coord,
            context={"store": self.store, "repo": "PathHost"},
        )
        self.assertFalse(path["allowed"])
        self.assertIn("witness", path["missing_axes"])
        self.assertEqual(path["next_legal_step"], "COMMIT_WITNESS")
        self.assertFalse(path["mutated"])
        self.assertFalse(path["issued_capability"])
        self.assertFalse(path["promoted"])
        self.assertIn("COMMIT_WITNESS", path["text"])
        n1 = self.store.db.execute(
            "SELECT COUNT(1) AS c FROM body_epochs WHERE repo=?", ("PathHost",)
        ).fetchone()["c"]
        eid1 = self.store.db.execute(
            "SELECT epoch_id FROM body_epochs WHERE repo=? ORDER BY created_at DESC LIMIT 1",
            ("PathHost",),
        ).fetchone()["epoch_id"]
        self.assertEqual(n0, n1)
        self.assertEqual(eid0, eid1)

    def test_full_coordinate_allows_promote_path(self) -> None:
        path = compile_legal_path("promote", coordinate_from_bits((1, 1, 1, 1)))
        self.assertTrue(path["allowed"])
        self.assertFalse(path["blocked"])


if __name__ == "__main__":
    unittest.main()
