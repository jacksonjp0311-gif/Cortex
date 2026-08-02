"""v7.0 Body Epoch determinism and compatibility."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.epoch import (
    compare_epochs,
    compute_body_epoch,
    ensure_current_epoch,
    explain_epoch_delta,
    seal_epoch_transition,
    verify_body_epoch,
)
from cortex.store import Store


class EpochTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# epoch\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "EpHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_deterministic_epoch_id(self) -> None:
        a = compute_body_epoch(self.store, "EpHost", created_at=1.0)
        b = compute_body_epoch(self.store, "EpHost", created_at=999.0)
        self.assertEqual(a.epoch_id, b.epoch_id)
        self.assertNotEqual(a.created_at, b.created_at)

    def test_seal_and_verify(self) -> None:
        ep = ensure_current_epoch(self.store, "EpHost", reason="test")
        v = verify_body_epoch(self.store, "EpHost", ep)
        self.assertTrue(v["ok"], v)
        again = seal_epoch_transition(self.store, "EpHost", reason="noop", parent=ep)
        self.assertEqual(again.epoch_id, ep.epoch_id)

    def test_compare_identical(self) -> None:
        a = compute_body_epoch(self.store, "EpHost")
        c = compare_epochs(a, a)
        self.assertTrue(c.compatible)

    def test_epoch_seal_retains_adaptive_attribution(self) -> None:
        ep = ensure_current_epoch(self.store, "EpHost", reason="attribution")
        row = self.store.db.execute(
            "SELECT metadata_json FROM body_epochs WHERE epoch_id=?", (ep.epoch_id,)
        ).fetchone()
        metadata = json.loads(row["metadata_json"])
        self.assertIn("adaptive_components", metadata)
        self.assertIn("neural_synapses", metadata["adaptive_components"])
        delta = explain_epoch_delta(self.store, "EpHost", ep, ep)
        self.assertFalse(delta["material_change"])
        self.assertEqual(delta["changed_roots"], [])
        self.assertTrue(delta["adaptive_attribution_available"])


if __name__ == "__main__":
    unittest.main()
