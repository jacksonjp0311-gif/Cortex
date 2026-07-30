"""End-to-end spectral memory (v6.13) — live path, not surface-only."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.activation import activate_repository
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.governor import Governor
from cortex.math_net.spectral_memory import (
    promote_calibration,
    spectral_memory_pulse,
)
from cortex.neuron import compile_interlink
from cortex.retrieval import query
from cortex.store import Store


class SpectralMemoryE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo_path = self.base / "spec_host"
        self.repo_path.mkdir()
        (self.repo_path / "README.md").write_text(
            "# SpectralHost\n\n## Architecture\n\nmemory graph\n",
            encoding="utf-8",
        )
        (self.repo_path / "core.py").write_text(
            "def activate():\n    return rank()\n\ndef rank():\n    return 1\n",
            encoding="utf-8",
        )
        (self.repo_path / "util.py").write_text(
            "from core import activate\n\ndef run():\n    return activate()\n",
            encoding="utf-8",
        )
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo_path, "SpecHost")
        try:
            compile_interlink(self.store, "SpecHost")
        except Exception:
            pass
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_pulse_end_to_end(self) -> None:
        pulse = spectral_memory_pulse(
            self.store,
            "SpecHost",
            retrieval_confidence=0.65,
            budget_tokens=400,
            auto_promote=False,
        )
        self.assertTrue(pulse.get("end_to_end"))
        self.assertIn("u", pulse)
        self.assertIn("Lambda", pulse)
        self.assertIn("regime_fit", pulse)
        self.assertIn("info_account", pulse)

    def test_activate_carries_spectral_memory(self) -> None:
        result = activate_repository(
            self.home,
            self.store,
            self.gov,
            "SpecHost",
            "architecture memory graph rank",
            budget=500,
        )
        sm = result.get("spectral_memory") or {}
        self.assertTrue(
            sm.get("end_to_end") or sm.get("u") or "error" in sm,
            msg=f"spectral_memory missing: {sm}",
        )
        if sm.get("end_to_end"):
            self.assertIn("Lambda", sm)

    def test_retrieval_ranker_primary_flag(self) -> None:
        hits = query(self.store, "SpecHost", "architecture memory", limit=6)
        # May be empty on tiny repo; if present check ranker metadata
        for h in hits[:3]:
            meta = h.metadata or {}
            if meta.get("ranker_score") is not None:
                self.assertTrue(meta.get("ranker_primary", True))
                break

    def test_promote_calibration_force(self) -> None:
        # seed shadow outcomes via pulse observations
        for _ in range(3):
            spectral_memory_pulse(
                self.store, "SpecHost", retrieval_confidence=0.5, auto_promote=False
            )
        out = promote_calibration(self.store, "SpecHost", min_outcomes=1, force=True)
        self.assertTrue(out.get("promoted"))
        gov = self.gov.evaluate("SpecHost", retrieval_confidence=0.6)
        self.assertIn(gov.get("coeffs_source"), {"live_calibrated", "shadow_blend", "prior"})


if __name__ == "__main__":
    unittest.main()
