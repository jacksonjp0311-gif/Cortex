"""Causal lineage graph."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.lineage import (
    ancestors_of,
    descendants_of,
    lineage_integrity_check,
    propagation_trace,
    record_artifact,
)
from cortex.store import Store


class LineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "home")
        self.repo_path = Path(self.temp.name) / "ln"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# L\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "LnHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_chain(self) -> None:
        record_artifact(
            self.store,
            "LnHost",
            artifact_id="sum1",
            artifact_type="summary",
            origin_memory_ids=["1"],
            parent_ids=["mem:1"],
        )
        record_artifact(
            self.store,
            "LnHost",
            artifact_id="syn_abc",
            artifact_type="invented_synapse",
            parent_ids=["sum1"],
            origin_memory_ids=["1"],
        )
        des = descendants_of(self.store, "LnHost", "mem:1")
        self.assertIn("sum1", des)
        self.assertIn("syn_abc", des)
        anc = ancestors_of(self.store, "LnHost", "syn_abc")
        self.assertTrue(any("sum1" in a or a == "sum1" for a in anc) or "sum1" in anc)
        tr = propagation_trace(self.store, "LnHost", ["1"])
        self.assertGreaterEqual(tr["n_descendants"], 1)
        self.assertIn("ok", lineage_integrity_check(self.store, "LnHost"))


if __name__ == "__main__":
    unittest.main()
