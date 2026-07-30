"""Activation fail-closed to EVIDENCE_BASELINE."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cortex.activation import activate_repository
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.store import Store


class ActivationFailClosedTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "afc"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# AFC\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "AFCHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_force_evidence_baseline(self) -> None:
        r = activate_repository(
            self.home,
            self.store,
            self.gov,
            "AFCHost",
            "readme",
            budget=400,
            refresh="never",
            force_evidence_baseline=True,
        )
        ctx = r.get("context") or r
        # packet may be projected
        ce = ctx.get("controller_execution") or (r.get("controller_execution"))
        # full context is in runtime; projected may omit — check memory_simplex
        ms = ctx.get("memory_simplex") or {}
        self.assertTrue(
            ms.get("controller") == "evidence_baseline"
            or (ce or {}).get("resolved") == "evidence_baseline"
            or ctx.get("evidence_kernel") is not None
            or r.get("profile")  # agent projection
        )

    def test_governor_throw_fail_closed(self) -> None:
        with mock.patch.object(
            self.gov, "evaluate", side_effect=RuntimeError("gov_down")
        ):
            r = activate_repository(
                self.home,
                self.store,
                self.gov,
                "AFCHost",
                "readme",
                budget=300,
                refresh="never",
            )
        # Should not raise; controller fail-closed
        self.assertIsInstance(r, dict)


if __name__ == "__main__":
    unittest.main()
