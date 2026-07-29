"""Glyph Canon ◈ and closed signal loop ⟲."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.activation import activate_repository
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.evolve_loop import close_signal_loop
from cortex.glyphs.canon import (
    compact_line,
    encode_state,
    expand_line,
    glyph_canon_registry,
    meta_instructions,
    optimize_glyph_set,
)
from cortex.governor import Governor
from cortex.learning.outcomes import record_outcome
from cortex.store import Store


class GlyphCanonLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "glyph-host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# Glyph Host\n\n## Architecture\n\nSignal loop and canon.\n",
            encoding="utf-8",
        )
        (self.repo / "app.py").write_text(
            "def run() -> str:\n    return 'ok'\n",
            encoding="utf-8",
        )
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "GlyphHost")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_canon_registry_and_compact_line(self) -> None:
        reg = glyph_canon_registry(optimized=True)
        self.assertEqual(reg["glyph"], "◈")
        self.assertFalse(reg["automatic_execution"])
        self.assertFalse(reg["grants_mutation_authority"])
        self.assertGreaterEqual(reg["count"], 15)
        line = compact_line(["immune_gate", "dormant", "organism_pulse", "connect_pass"])
        self.assertIn("⊛", line)
        expanded = expand_line(line)
        self.assertGreaterEqual(len(expanded), 3)
        opt = optimize_glyph_set()
        self.assertIn("signal_loop", opt)
        self.assertIn("glyph_canon", opt)

    def test_encode_state_token_thrift(self) -> None:
        state = encode_state(
            control={"ok": True, "block": False, "severity": "low"},
            governor={"mode": "normal"},
            aria={"mode": "dormant"},
            resonance={"brightness": "in_phase"},
            kernels={"dominant": "integrate"},
            loop={"closed": True, "verdict": "improved"},
        )
        self.assertTrue(state["line"])
        self.assertLess(state["estimated_tokens"], 80)
        instr = meta_instructions(state, governor_mode="normal")
        self.assertTrue(any("◈" in line or state["line"][:1] in line for line in instr))
        self.assertTrue(all(len(line) < 200 for line in instr))

    def test_signal_loop_closes_with_features(self) -> None:
        packet = activate_repository(
            self.home,
            self.store,
            self.gov,
            "GlyphHost",
            "Architecture signal loop",
            budget=500,
        )
        act_id = (packet.get("context") or {}).get("neural_interlink", {}).get(
            "activation_id"
        ) or packet.get("activation_id")
        self.assertTrue(act_id, msg=str(packet.keys()))
        # Bare outcome should attach path feature vectors
        bare = record_outcome(
            self.store,
            "GlyphHost",
            act_id,
            status="helpful",
            verification_type="unit",
            governance_mode="normal",
            skip_auto_causal=True,
        )
        self.assertGreaterEqual(bare.get("ranker_feature_vectors") or 0, 1)

        packet2 = activate_repository(
            self.home,
            self.store,
            self.gov,
            "GlyphHost",
            "Architecture signal loop close",
            budget=500,
        )
        act2 = (packet2.get("context") or {}).get("neural_interlink", {}).get(
            "activation_id"
        ) or packet2.get("activation_id")
        self.assertTrue(act2)
        looped = close_signal_loop(
            self.store,
            "GlyphHost",
            activation_id=act2,
            status="verified",
            verification_type="tests",
            task="Architecture signal loop",
            governance_mode="normal",
            probe_k=4,
        )
        self.assertEqual(looped["glyph"], "⟲")
        self.assertIn("causal", looped)
        self.assertNotIn(
            "missing_recall_pair",
            (looped.get("causal") or {}).get("confounds") or [],
        )
        self.assertIn(
            looped["causal"].get("verdict"), {"improved", "regressed", "inconclusive"}
        )
        self.assertIn("glyph_state", looped)
        self.assertGreaterEqual(looped.get("feature_vectors") or 0, 1)


if __name__ == "__main__":
    unittest.main()
