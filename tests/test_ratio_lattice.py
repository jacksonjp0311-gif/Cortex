"""v6.21 ratio lattice — triad, budget partition, residual pyramid."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.math_net.multiscale import multiscale_conservation
from cortex.math_net.ratio_lattice import (
    local_closure,
    partition_budgets,
    rational_ratio,
    triadic_metrics,
)
from cortex.prune import policy_preview
from cortex.ranker.model import FEATURE_NAMES, features_from_hit
from cortex.store import Store


class FakeAdjStore:
    """Minimal store for synthetic triangle graph."""

    def __init__(self, edges: list[tuple[str, str]]) -> None:
        self._edges = edges

    def neural_synapses(self, repo: str):
        out = []
        for i, (s, t) in enumerate(self._edges):
            out.append(
                {
                    "synapse_id": f"s{i}",
                    "source_id": s,
                    "target_id": t,
                    "relation": "assoc",
                    "weight": 0.5,
                    "update_count": 0,
                    "metadata": "{}",
                }
            )
        return out

    def neural_nodes(self, repo: str):
        nodes = sorted({n for e in self._edges for n in e})
        return [{"node_id": n, "path": n, "resolution": "file", "metadata": "{}"} for n in nodes]


class RatioLatticeUnitTests(unittest.TestCase):
    def test_partition_sums(self) -> None:
        for scheme in ("fib", "phi", "double_square", "flat"):
            p = partition_budgets(300, ("symbol", "file", "module"), scheme=scheme)
            self.assertEqual(p["sum_check"], 300, scheme)
            self.assertEqual(sum(p["pools"].values()), 300, scheme)
            self.assertIn("claim_boundary", p)

    def test_double_square_fine_is_third(self) -> None:
        p = partition_budgets(300, ("symbol", "file"), scheme="double_square")
        self.assertEqual(p["pools"]["symbol"], 100)
        self.assertEqual(p["pools"]["file"], 200)

    def test_flat_puts_all_on_first(self) -> None:
        p = partition_budgets(400, ("symbol", "file", "module"), scheme="flat")
        self.assertEqual(p["pools"]["symbol"], 400)
        self.assertEqual(p["pools"]["file"], 0)

    def test_rational_table(self) -> None:
        self.assertEqual(rational_ratio("double_square"), (1, 2))
        self.assertEqual(rational_ratio("quarter"), (1, 4))

    def test_triangle_closure_positive(self) -> None:
        # Complete triangle A-B-C
        store = FakeAdjStore([("A", "B"), ("B", "C"), ("C", "A")])
        m = triadic_metrics(store, "R")
        self.assertEqual(m["triangles"], 1)
        self.assertGreater(m["global_closure_T"], 0.9)
        self.assertAlmostEqual(local_closure(
            {"A": {"B", "C"}, "B": {"A", "C"}, "C": {"A", "B"}}, "A"
        ), 1.0)

    def test_path_zero_triangles(self) -> None:
        store = FakeAdjStore([("A", "B"), ("B", "C")])
        m = triadic_metrics(store, "R")
        self.assertEqual(m["triangles"], 0)
        self.assertEqual(m["global_closure_T"], 0.0)
        bridges = m["open_bridges_sample"]
        self.assertGreaterEqual(len(bridges), 1)

    def test_ranker_feature_present(self) -> None:
        self.assertIn("triadic_closure", FEATURE_NAMES)
        feats = features_from_hit(
            {"path": "a.py", "kind": "source", "score": 0.5, "metadata": {"triadic_closure": 0.8}}
        )
        idx = FEATURE_NAMES.index("triadic_closure")
        self.assertAlmostEqual(feats[idx], 0.8, places=5)


class RatioLatticeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "rl_host"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text("# RL\n\n## Arch\n\nx\n", encoding="utf-8")
        (self.repo_path / "a.py").write_text(
            "def f():\n    return g()\n\ndef g():\n    return 1\n", encoding="utf-8"
        )
        (self.repo_path / "b.py").write_text("from a import f\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "RLHost")
        try:
            from cortex.neuron import compile_interlink

            compile_interlink(self.store, "RLHost")
        except Exception:
            pass

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_triadic_metrics_on_real_graph(self) -> None:
        m = triadic_metrics(self.store, "RLHost", max_nodes=200)
        self.assertTrue(m.get("ok"))
        self.assertIn("global_closure_T", m)
        self.assertIn("claim_boundary", m)

    def test_prune_preview_triad(self) -> None:
        prev = policy_preview(self.store, "RLHost")
        self.assertIn("triad_attention", prev)
        self.assertIn("bottleneck_attention", prev)

    def test_m9_residual_pyramid(self) -> None:
        ms = multiscale_conservation(self.store, "RLHost", fired_node_ids=[], budget=50)
        self.assertIn("residual_pyramid", ms)
        rp = ms["residual_pyramid"]
        self.assertIn("path_residual", rp)
        self.assertIn("envelope_cell_ok", rp)
        self.assertIn("levels", rp)
        self.assertEqual(ms["schema_version"], "cortex-multiscale/1.1")


if __name__ == "__main__":
    unittest.main()
