"""Ranker training event ledger exclusion — clean rebuild path."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.ranker.model import ensure_ranker, features_from_hit, train_from_outcome
from cortex.store import Store


class RankerRebuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = ensure_home(Path(self.temp.name) / "h")
        p = Path(self.temp.name) / "r"
        p.mkdir()
        (p / "README.md").write_text("# rk\n", encoding="utf-8")
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(self.home, self.store, p, "RkHost")

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_baseline_controller_blocks_train(self) -> None:
        vecs = [
            features_from_hit(
                {"path": "README.md", "kind": "documentation", "score": 0.5, "metadata": {}},
                rank=0,
            )
        ]
        r = train_from_outcome(
            self.store,
            "RkHost",
            outcome_id="o1",
            activation_id="a1",
            status="verified",
            reward=0.8,
            verification_type="test",
            governance_mode="normal",
            feature_vectors=vecs,
            memory_controller="evidence_baseline",
        )
        self.assertFalse(r.get("trained"))
        self.assertIn("reason", r)

    def test_advanced_trains(self) -> None:
        ensure_ranker(self.store, "RkHost")
        vecs = [
            features_from_hit(
                {"path": "README.md", "kind": "documentation", "score": 0.5, "metadata": {}},
                rank=0,
            )
        ]
        r = train_from_outcome(
            self.store,
            "RkHost",
            outcome_id="o2",
            activation_id="a2",
            status="verified",
            reward=0.8,
            verification_type="test",
            governance_mode="normal",
            feature_vectors=vecs,
            memory_controller="advanced",
        )
        self.assertTrue(r.get("trained"))


if __name__ == "__main__":
    unittest.main()
