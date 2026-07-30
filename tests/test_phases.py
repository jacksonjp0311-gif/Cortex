"""v7.0 Runtime phase machine."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.phases import (
    ADAPT,
    OBSERVE,
    QUIESCENT,
    can_transition,
    current_phase,
    phase_allows_operation,
    transition_phase,
)
from cortex.store import Store


class PhaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# ph\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "PhHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_start_quiescent(self) -> None:
        st = current_phase(self.store, "PhHost")
        self.assertEqual(st.phase, QUIESCENT)
        self.assertTrue(st.epoch_id)

    def test_legal_and_illegal(self) -> None:
        self.assertTrue(can_transition(QUIESCENT, OBSERVE))
        self.assertFalse(can_transition(QUIESCENT, PROMOTE if False else "PROMOTE"))
        # QUIESCENT cannot go directly to PROMOTE
        self.assertFalse(can_transition(QUIESCENT, "PROMOTE"))
        r = transition_phase(self.store, "PhHost", OBSERVE, reason="test")
        self.assertTrue(r["ok"], r)
        r2 = transition_phase(self.store, "PhHost", ADAPT, reason="test")
        self.assertTrue(r2["ok"], r2)
        bad = transition_phase(self.store, "PhHost", "PROMOTE", reason="illegal")
        self.assertFalse(bad["ok"])

    def test_phase_ops(self) -> None:
        self.assertTrue(phase_allows_operation(ADAPT, "ranker_train"))
        self.assertFalse(phase_allows_operation(OBSERVE, "ranker_train"))


if __name__ == "__main__":
    unittest.main()
