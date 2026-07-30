"""Fusion co-process: tick geometry + structure invent + self-model."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.coprocess import fuse_close, fuse_open, fuse_state, fuse_tick
from cortex.governor import Governor
from cortex.neuron import compile_interlink
from cortex.store import Store
from cortex.structure_invent import invent_from_coactivation


class FusionCoprocessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "fuse_host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text("# Fuse\n\n## Geometry\n\nx\n", encoding="utf-8")
        (self.repo / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (self.repo / "b.py").write_text("from a import f\n\ndef g():\n    return f()\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "FuseHost")
        try:
            compile_interlink(self.store, "FuseHost")
        except Exception:
            pass
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_open_tick_close(self) -> None:
        opened = fuse_open(
            self.home,
            self.store,
            self.gov,
            "FuseHost",
            task="regenerate geometry while fused",
            budget=450,
        )
        self.assertTrue(opened.get("opened"))
        self.assertIn("mind_hash", opened)
        self.assertIn("self_model", opened)

        t1 = fuse_tick(self.store, self.gov, "FuseHost", token="geometry", tokens=1)
        self.assertTrue(t1.get("ok"))
        self.assertTrue(t1.get("geometry_regenerated"))
        self.assertEqual(t1.get("tick"), 1)
        self.assertIn("injection", t1)

        t2 = fuse_tick(self.store, self.gov, "FuseHost", token=" spectral ", tokens=3)
        self.assertEqual(t2.get("tick"), 2)
        self.assertGreaterEqual(t2.get("token_count"), 4)

        st = fuse_state(self.store, "FuseHost")
        self.assertTrue(st.get("open"))
        self.assertEqual(st.get("tick"), 2)

        closed = fuse_close(self.store, "FuseHost")
        self.assertTrue(closed.get("closed"))
        st2 = fuse_state(self.store, "FuseHost")
        self.assertFalse(st2.get("open"))

    def test_structure_invent_gated(self) -> None:
        nodes = [str(r["node_id"]) for r in self.store.neural_nodes("FuseHost")[:6]]
        if len(nodes) < 2:
            self.skipTest("need neural nodes")
        out = invent_from_coactivation(
            self.store,
            "FuseHost",
            fired_node_ids=nodes,
            governance_mode="normal",
            max_new=3,
        )
        self.assertIn("invented", out)
        blocked = invent_from_coactivation(
            self.store,
            "FuseHost",
            fired_node_ids=nodes,
            governance_mode="read_only",
        )
        self.assertTrue(blocked.get("blocked"))


if __name__ == "__main__":
    unittest.main()
