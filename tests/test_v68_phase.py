"""v6.8 phase: envelope parity, phrasebook, harness, hygiene."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.activation import activate_repository
from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.glyphs.canon import phrase, phrasebook
from cortex.governor import Governor
from cortex.hygiene import body_hygiene
from cortex.signal_harness import run_signal_harness
from cortex.store import Store


class V68PhaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "v68host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text(
            "# V68\n\n## Architecture\n\nGlyph phrasebook and harness.\n",
            encoding="utf-8",
        )
        (self.repo / "app.py").write_text(
            "def run() -> str:\n    return 'ok'\n",
            encoding="utf-8",
        )
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "V68Host")
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_phrasebook_reusable(self) -> None:
        book = phrasebook()
        self.assertGreaterEqual(book["count"], 6)
        awake = phrase("aria_awake")
        self.assertTrue(awake["line"])
        self.assertIn("keys", awake)
        self.assertFalse(book["automatic_execution"])

    def test_activate_envelope_parity(self) -> None:
        packet = activate_repository(
            self.home,
            self.store,
            self.gov,
            "V68Host",
            "glyph surface check",
            budget=400,
        )
        self.assertIn("glyph_state", packet)
        self.assertTrue(
            packet.get("glyph_line") or (packet.get("glyph_state") or {}).get("line")
        )
        self.assertIn("stream", packet)
        self.assertIn("aria_language", packet)
        lang = packet["aria_language"]
        self.assertEqual(lang.get("glyph"), "◈")
        self.assertIn("phrasebook", lang)
        self.assertFalse(lang.get("automatic_execution"))

    def test_hygiene_surface(self) -> None:
        h = body_hygiene(self.home, self.store, "V68Host")
        self.assertIn("graph", h)
        self.assertIn("advice", h)
        self.assertIn("glyph_line", h)

    def test_harness_matched_suite(self) -> None:
        # Short suite for unit speed
        families = [
            {
                "id": "t1",
                "task": "Architecture glyph harness",
                "phrase": "wake_safe",
                "status": "helpful",
                "verification": "unit-h1",
            },
            {
                "id": "t2",
                "task": "Use ARIA prove implementation",
                "phrase": "aria_awake",
                "status": "verified",
                "verification": "unit-h2",
            },
        ]
        report = run_signal_harness(
            self.home,
            self.store,
            self.gov,
            "V68Host",
            families=families,
            budget=400,
            k=4,
        )
        self.assertEqual(report["glyph"], "⟲")
        self.assertEqual(report["summary"]["ok"], 2)
        self.assertEqual(report["summary"]["missing_recall_pair"], 0)
        self.assertTrue(report["exit_criteria"]["no_missing_recall_pair_on_ok_runs"])
        self.assertTrue(report["exit_criteria"]["activate_envelope_parity"])
        for run in report["runs"]:
            self.assertTrue(run.get("ok"), run)
            self.assertIn("glyph_line", run)


if __name__ == "__main__":
    unittest.main()
