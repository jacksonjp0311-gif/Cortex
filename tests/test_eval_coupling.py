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
    HOLDOUT_CORPUS,
    STRESS_CORPUS,
    TRAIN_CORPUS,
    resolve_corpus,
    run_eval_coupling,
)
from cortex.promote_gate import evaluate_promotion
from cortex.self_org import _gov_mode
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


class ConceptRouteTests(unittest.TestCase):
    def test_hard_paraphrases_match_modules(self) -> None:
        from cortex.concept_routes import concept_route_paths, match_concept_routes

        cases = [
            (
                "propose new coactivation topology edges from simultaneous path fire under governor gates",
                "structure_invent.py",
            ),
            (
                "randomized controlled trial arm for optional synapse weight updates only when opted in",
                "plasticity_rct.py",
            ),
            (
                "build graph adjacency operator and dual reverse-edge operator for spectral work",
                "operator.py",
            ),
            (
                "single scalar that may only decrease when immune stress rises never inflate certainty for governor",
                "uncertainty.py",
            ),
            (
                "map predicted confidence to observed hit rates and clamp drift floor after outcomes",
                "calibration.py",
            ),
            (
                "information accounting budget bits spent on retrieval and learning decisions",
                "info_account.py",
            ),
        ]
        for q, needle in cases:
            self.assertTrue(match_concept_routes(q), msg=q)
            paths = concept_route_paths(q)
            self.assertTrue(
                any(needle in p for p in paths),
                msg=f"{q} -> {paths}",
            )


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
            self.home,
            self.store,
            self.engine,
            "EvalHost",
            force=True,
            external=True,
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
        self.assertEqual(len(resolve_corpus("stress")), len(STRESS_CORPUS))
        self.assertEqual(len(resolve_corpus("train")), len(TRAIN_CORPUS))
        self.assertEqual(len(resolve_corpus("holdout")), len(HOLDOUT_CORPUS))
        self.assertIs(DEFAULT_CORPUS, EASY_CORPUS)

    def test_gov_mode_fail_closed(self) -> None:
        class Boom:
            def evaluate(self, *a: object, **k: object) -> dict:
                raise RuntimeError("nope")

        self.assertEqual(_gov_mode(Boom(), self.store, "EvalHost"), "read_only")

    def test_promotion_gate_requires_foreign(self) -> None:
        holdout = {
            "repo": "Body",
            "winner": "baseline",
            "gate": {"baseline_is_winner": True},
            "ablations": {"baseline": {"recall_at_k": 0.8}},
        }
        denied = evaluate_promotion(
            holdout_report=holdout,
            foreign_report=None,
            emergent_coupling=True,
            require_foreign=True,
        )
        self.assertFalse(denied["allow_promote"])
        foreign = {
            "repo": "Foreign",
            "winner": "baseline",
            "gate": {"baseline_is_winner": True},
            "ablations": {"baseline": {"recall_at_k": 0.6}},
        }
        ok = evaluate_promotion(
            holdout_report=holdout,
            foreign_report=foreign,
            emergent_coupling=True,
            require_foreign=True,
        )
        self.assertTrue(ok["allow_promote"])

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
