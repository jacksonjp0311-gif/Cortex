"""Measure gate: eval-coupling ablations + hard suite."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cortex.bootstrap import bootstrap_repository
from cortex.config import ensure_home
from cortex.eval_coupling import (
    DEFAULT_CORPUS,
    EASY_CORPUS,
    HARD_CORPUS,
    resolve_corpus,
    run_eval_coupling,
)
from cortex.governor import Governor
from cortex.retrieval import (
    path_token_overlap,
    path_token_quality_boost,
    query_has_impl_markers,
)
from cortex.store import Store


class RankerDesaturateTests(unittest.TestCase):
    def test_batch_relative_scores_spread(self) -> None:
        from cortex.ranker.model import _batch_relative_scores

        # Saturated absolute logits still must produce ordered relative scores.
        rel = _batch_relative_scores([4.0, 4.05, 4.2, 3.5])
        self.assertEqual(len(rel), 4)
        self.assertGreater(rel[2], rel[0])  # 4.2 > 4.0
        self.assertGreater(rel[0], rel[3])  # 4.0 > 3.5
        self.assertTrue(all(0.0 < x < 1.0 for x in rel))


class PathTokenBoostTests(unittest.TestCase):
    def test_fusion_paths_align_with_impl_query(self) -> None:
        q = "fusion co-process fuse tick regenerate geometry mind_hash"
        self.assertTrue(query_has_impl_markers(q))
        self.assertGreater(path_token_overlap(q, "cortex/coprocess.py"), 0.0)
        self.assertGreater(path_token_overlap(q, "cortex/fuse_proxy.py"), 0.0)
        self.assertGreater(path_token_quality_boost(q, "cortex/coprocess.py"), 1.0)
        self.assertEqual(
            path_token_overlap(
                q, "examples/memory-packets/interconnect.memory.aria"
            ),
            0.0,
        )


class EvalCouplingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = ensure_home(self.base / "home")
        self.engine = Path(__file__).resolve().parents[1]
        self.store = Store(self.home / "cortex.db")
        bootstrap_repository(
            self.home, self.store, self.engine, "EvalHost", force=True
        )
        self.gov = Governor(self.home, self.store)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def test_resolve_corpus_suites(self) -> None:
        self.assertEqual(len(resolve_corpus("easy")), len(EASY_CORPUS))
        self.assertEqual(len(resolve_corpus("hard")), len(HARD_CORPUS))
        self.assertEqual(
            len(resolve_corpus("full")), len(EASY_CORPUS) + len(HARD_CORPUS)
        )
        self.assertIs(DEFAULT_CORPUS, EASY_CORPUS)

    def test_eval_coupling_runs(self) -> None:
        report = run_eval_coupling(
            self.home,
            self.store,
            self.gov,
            "EvalHost",
            corpus=list(DEFAULT_CORPUS)[:3],
            limit=10,
            top_k=5,
            persist=True,
        )
        self.assertEqual(report["schema_version"], "cortex-eval-coupling/1.1")
        self.assertIn("baseline", report["ablations"])
        self.assertIn("no_spectral", report["ablations"])
        self.assertIn("no_ranker", report["ablations"])
        self.assertIn("gate", report)
        self.assertIn("recommendation", report)
        self.assertIn("winner", report)
        self.assertIn("mrr", report["ablations"]["baseline"])
        self.assertIn("divergence_cases", report)
        for mode, data in report["ablations"].items():
            self.assertIn("recall_at_k", data)
            self.assertIn("mrr", data)

    def test_hard_suite_runs(self) -> None:
        report = run_eval_coupling(
            self.home,
            self.store,
            self.gov,
            "EvalHost",
            suite="hard",
            corpus=list(HARD_CORPUS)[:3],
            limit=10,
            top_k=5,
            persist=False,
        )
        self.assertEqual(report["suite"], "custom")  # explicit corpus
        self.assertEqual(len(report["corpus_ids"]), 3)


if __name__ == "__main__":
    unittest.main()
