"""Emergence log — must-read progress surface."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.coherence import measure_coherence
from cortex.config import ensure_home
from cortex.context import build_context
from cortex.emergence_log import log_milestone, read_emergence_log
from cortex.governor import Governor
from cortex.neuron import compile_interlink
from cortex.store import Store


class EmergenceLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.repo = self.base / "em_host"
        self.repo.mkdir()
        (self.repo / "README.md").write_text("# Em\n\n## Architecture\n\nx\n", encoding="utf-8")
        (self.repo / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, self.repo, "EmHost")
        try:
            compile_interlink(self.store, "EmHost")
        except Exception:
            pass
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_log_and_must_read(self) -> None:
        measure_coherence(self.store, "EmHost", governor=self.gov, home=self.home)
        log_milestone(
            self.home,
            self.store,
            "EmHost",
            summary="Test milestone for progress",
            kind="agent_note",
        )
        surface = read_emergence_log(self.home, self.store, "EmHost", limit=8)
        self.assertTrue(surface.get("must_read"))
        self.assertGreaterEqual(surface.get("event_count") or 0, 1)
        self.assertTrue(surface.get("instruction_lines"))
        self.assertTrue(any("EMERGENCE LOG" in ln for ln in surface["instruction_lines"]))
        self.assertTrue(surface.get("directives"))

    def test_context_injects_emergence_log(self) -> None:
        measure_coherence(self.store, "EmHost", governor=self.gov, home=self.home)
        ctx = build_context(
            self.home,
            self.store,
            self.gov,
            "EmHost",
            "architecture progress",
            budget=400,
        )
        self.assertIn("emergence_log", ctx)
        self.assertTrue(ctx["emergence_log"].get("must_read"))
        instr = "\n".join(ctx.get("instructions") or [])
        self.assertIn("EMERGENCE LOG", instr)
        steps = (ctx.get("agent_protocol") or {}).get("steps") or []
        self.assertTrue(any(s.get("id") == "read_emergence_log" for s in steps))
        self.assertIn("emergence_log", ctx.get("must_read") or [])


if __name__ == "__main__":
    unittest.main()
