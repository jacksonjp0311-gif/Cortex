"""v6.10 prune policies and graph census."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.hygiene import body_hygiene
from cortex.prune import graph_census, policy_preview, prune_graph
from cortex.store import Store


class PrunePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "phost"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# P\n\n## Architecture\n\nx\n")
        (self.repo_path / "a.py").write_text("def f():\n    return 1\n")
        (self.repo_path / "b.py").write_text("from a import f\n")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "PHost")
        # Soften some integrate edges for policy differentiation
        for row in self.store.neural_synapses("PHost"):
            meta = json.loads(row["metadata"] or "{}")
            meta["kernel_class"] = "integrate"
            self.store.db.execute(
                "UPDATE neural_synapses SET weight=?, update_count=0, metadata=? WHERE repo=? AND synapse_id=?",
                (0.07, json.dumps(meta), "PHost", row["synapse_id"]),
            )
        self.store.db.commit()

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_policies_and_preview(self) -> None:
        safe = prune_graph(self.store, "PHost", policy="safe", dry_run=True)
        soft = prune_graph(self.store, "PHost", policy="integrate_soft", dry_run=True)
        self.assertGreaterEqual(soft["would_prune"], safe["would_prune"])
        self.assertGreater(soft["would_prune"], 0)
        prev = policy_preview(self.store, "PHost")
        self.assertIn("integrate_soft", prev["policies"])
        self.assertEqual(
            prev["policies"]["integrate_soft"]["would_prune"], soft["would_prune"]
        )
        hy = body_hygiene(self.home, self.store, "PHost")
        self.assertIn("prune_preview", hy)
        self.assertTrue(
            any("integrate_soft" in a or "hold" in a for a in hy.get("advice") or [])
            or hy.get("recommended_prune_policy")
        )

    def test_aggressive_needs_authorize(self) -> None:
        r = prune_graph(self.store, "PHost", policy="aggressive", dry_run=False)
        self.assertEqual(r.get("error"), "aggressive_requires_authorize")

    def test_census(self) -> None:
        c = graph_census(self.store, "PHost")
        self.assertGreater(c["synapses"]["total"], 0)
        self.assertIn("by_kernel_class", c["synapses"])
        self.assertIn("prune_preview", c)


if __name__ == "__main__":
    unittest.main()
