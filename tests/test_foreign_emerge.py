"""v6.23 foreign emerge — phase thicken API shape."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.foreign_emerge import SCHEMA, thicken_host_phase
from cortex.governor import Governor
from cortex.store import Store


class ForeignEmergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "fe_host"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# FE\n", encoding="utf-8")
        (self.repo_path / "src").mkdir()
        (self.repo_path / "src" / "policy.rs").write_text("// policy\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "FEHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_thicken_shape(self) -> None:
        r = thicken_host_phase(
            self.home,
            self.store,
            self.gov,
            "FEHost",
            fuse_ticks=1,
            target_trains=2,
            activate=False,
            path_seeds=["src/policy.rs", "README.md"],
            persist=False,
        )
        self.assertEqual(r.get("schema_version"), SCHEMA)
        self.assertIn("phase_before", r)
        self.assertIn("phase_after", r)
        self.assertIn("warm", r)
        self.assertIn("claim_boundary", r)
        after = r["phase_after"]
        self.assertIn("train_count", after)
        self.assertGreaterEqual(int(after.get("train_count") or 0), 1)


if __name__ == "__main__":
    unittest.main()
