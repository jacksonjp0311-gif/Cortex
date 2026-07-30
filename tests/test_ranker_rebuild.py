"""Deterministic ranker rebuild from event ledger."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.capabilities import issue_for_controller
from cortex.config import ensure_home
from cortex.ranker.model import (
    ensure_ranker,
    features_from_hit,
    model_hash,
    rebuild_ranker_from_events,
    train_from_outcome,
)
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
        self.cap = issue_for_controller("RkHost", "advanced", reason="test")

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

    def test_rebuild_deterministic(self) -> None:
        ensure_ranker(self.store, "RkHost")
        events = []
        for i, lab in enumerate([1.0, 1.0, -1.0, 1.0]):
            vecs = [
                features_from_hit(
                    {
                        "path": "README.md",
                        "kind": "documentation",
                        "score": 0.5 + 0.05 * i,
                        "metadata": {},
                    },
                    rank=i,
                )
            ]
            r = train_from_outcome(
                self.store,
                "RkHost",
                outcome_id=f"o{i}",
                activation_id=f"a{i}",
                status="verified" if lab > 0 else "failed",
                reward=0.8 * lab,
                verification_type="test",
                governance_mode="normal",
                feature_vectors=vecs,
                capability=self.cap,
            )
            self.assertTrue(r.get("trained"), r)
            events.append(r["event_id"])
        # exclude contaminated (failed) event
        bad = events[2]
        r1 = rebuild_ranker_from_events(
            self.store, "RkHost", [bad], capability=issue_for_controller("RkHost", "repair")
        )
        r2 = rebuild_ranker_from_events(
            self.store, "RkHost", [bad], capability=issue_for_controller("RkHost", "repair")
        )
        self.assertTrue(r1.get("ok"), r1)
        self.assertEqual(r1["new_model_hash"], r2["new_model_hash"])
        self.assertNotEqual(r1["old_model_hash"], r1["new_model_hash"] or "x")
        self.assertEqual(r1["events_replayed"], 3)


if __name__ == "__main__":
    unittest.main()
