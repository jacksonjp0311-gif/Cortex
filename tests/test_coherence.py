"""System coherence seam wiring."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.coherence import (
    COHERENCE_THRESHOLD,
    COUPLE_DEFS,
    _couple_percolation,
    measure_coherence,
    soft_bind_fusion,
)
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.neuron import compile_interlink
from cortex.store import Store


class CoherenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "coh_host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text("# Coh\n\n## Architecture\n\nx\n", encoding="utf-8")
        (self.repo / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        (self.repo / "b.py").write_text("from a import f\n\ndef g():\n    return f()\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "CohHost")
        try:
            compile_interlink(self.store, "CohHost")
        except Exception:
            pass
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_measure_coherence_shape(self) -> None:
        c = measure_coherence(
            self.store, "CohHost", governor=self.gov, home=self.home
        )
        self.assertEqual(c["schema_version"], "cortex-coherence/1.3")
        self.assertIn("score", c)
        self.assertEqual(c["threshold"], COHERENCE_THRESHOLD)
        self.assertIn("components", c)
        self.assertIn("coupling", c)
        self.assertIn("indicators", c)
        self.assertGreaterEqual(len(c["indicators"]), 4)
        self.assertIn("component_panel", c)
        self.assertIn("emergent_coupling", c)
        self.assertIn("trend", c)
        self.assertIn("operational_coupling_index", c)
        self.assertIn("couple_percolation", c)
        self.assertIn("occupied_bonds", c["couple_percolation"])
        self.assertIn("lyapunov", c)
        self.assertIn("V", c["lyapunov"])
        self.assertIsInstance(c["above_threshold"], bool)
        # Persisted latest
        latest = self.store.get_setting("coherence_latest:CohHost", None)
        self.assertIsInstance(latest, dict)
        self.assertIn("score", latest or {})

    def test_percolation_requires_learning_operations_and_governance(self) -> None:
        def indicators(active: set[str]) -> list[dict]:
            return [
                {
                    "id": cid,
                    "left": left,
                    "right": right,
                    "active": cid in active,
                }
                for cid, left, right, _spoken in COUPLE_DEFS
            ]

        one_scalar_jump = {
            "blood_geometry", "ops_geometry", "spectral_ops", "gates_aligned"
        }
        cold_learning = _couple_percolation(
            {}, {}, indicators(one_scalar_jump), True, score=0.8
        )
        self.assertFalse(cold_learning["phase_emergent"])
        self.assertFalse(cold_learning["phase_requirements"]["learning_ready"])

        connected_two_key = one_scalar_jump | {"blood_learning"}
        warm = _couple_percolation(
            {}, {}, indicators(connected_two_key), True, score=0.8
        )
        self.assertTrue(warm["phase_emergent"])
        self.assertGreaterEqual(warm["giant_component_nodes"], 4)

    def test_soft_bind_respects_env(self) -> None:
        off = soft_bind_fusion(
            self.home, self.store, self.gov, "CohHost", force=False
        )
        # force=False and env unset → not bound
        self.assertFalse(off.get("bound") and not off.get("error"))
        on = soft_bind_fusion(
            self.home, self.store, self.gov, "CohHost", force=True
        )
        self.assertTrue(on.get("bound"))


if __name__ == "__main__":
    unittest.main()
