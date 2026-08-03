"""v8.2.2 query-conditioned bridge trial falsification tests."""

from __future__ import annotations

from cortex.bridge_trials import (
    evaluate_bridge_trial_promotion,
    query_conditioned_bridge_trial,
    structural_trial_context_hash,
)
from cortex.bridge_trial_corpus import BRIDGE_TRIAL_CORPUS, BRIDGE_TRIAL_FREEZE_ID


def _scores() -> dict[str, dict[str, float]]:
    return {
        "bridge/c.py": {"bridge_potential": 0.9, "domain_diversity": 0.8},
        "core1/weak.py": {"bridge_potential": 0.95, "domain_diversity": 0.8},
    }


def test_bridge64_corpus_is_unique_and_frozen() -> None:
    assert BRIDGE_TRIAL_FREEZE_ID == "bridge64-v1-2026-08-02"
    assert len(BRIDGE_TRIAL_CORPUS) == 64
    assert len({case["id"] for case in BRIDGE_TRIAL_CORPUS}) == 64
    assert all(case["split"] == "sealed_bridge_holdout" for case in BRIDGE_TRIAL_CORPUS)


def test_trial_context_hash_changes_with_epoch_or_graph() -> None:
    base = structural_trial_context_hash(
        corpus_hash="corpus",
        body_epoch_id="epoch-a",
        graph_fingerprint="graph-a",
        top_k=5,
        limit=24,
    )
    changed_epoch = structural_trial_context_hash(
        corpus_hash="corpus",
        body_epoch_id="epoch-b",
        graph_fingerprint="graph-a",
        top_k=5,
        limit=24,
    )
    changed_graph = structural_trial_context_hash(
        corpus_hash="corpus",
        body_epoch_id="epoch-a",
        graph_fingerprint="graph-b",
        top_k=5,
        limit=24,
    )
    assert base != changed_epoch
    assert base != changed_graph


def test_bridge_trial_is_fixed_cardinality_and_does_not_mutate_baseline() -> None:
    hits = [
        {"path": "core1/a.py", "score": 1.0},
        {"path": "core2/b.py", "score": 0.8},
        {"path": "bridge/c.py", "score": 0.75},
        {"path": "core1/weak.py", "score": 0.2},
    ]
    before = [(hit["path"], hit["score"]) for hit in hits]
    report = query_conditioned_bridge_trial(
        "cross region connector",
        hits,
        bridge_scores=_scores(),
        adjacency={"bridge/c.py": {"other/x.py", "other/y.py"}},
        top_k=2,
        triadic_floor=0.65,
    )
    assert report["selected"]["path"] == "bridge/c.py"
    assert report["arms"]["bridge_reserve"] == ["core1/a.py", "bridge/c.py"]
    assert len(report["arms"]["bridge_reserve"]) == 2
    assert report["arms"]["annotation_only"] == report["arms"]["baseline"]
    assert report["fixed_cardinality"] is True
    assert report["policy_effect"] is False
    assert before == [(hit["path"], hit["score"]) for hit in hits]


def test_bridge_trial_rejects_structural_candidate_below_relevance_floor() -> None:
    hits = [
        {"path": "core1/a.py", "score": 1.0},
        {"path": "core2/b.py", "score": 0.8},
        {"path": "core1/weak.py", "score": 0.2},
    ]
    report = query_conditioned_bridge_trial(
        "cross region connector",
        hits,
        bridge_scores=_scores(),
        adjacency={"core1/weak.py": {"core2/b.py"}},
        top_k=2,
        triadic_floor=0.65,
    )
    assert report["selected"] is None
    assert report["arms"]["bridge_reserve"] == report["arms"]["baseline"]


def test_promotion_requires_sample_size_and_all_independent_gates() -> None:
    row = {
        "ranks": {"baseline": 2, "bridge_reserve": 1},
        "selected": {"path": "bridge/c.py"},
        "fixed_cardinality": True,
        "policy_effect": False,
    }
    arms = {
        "baseline": {"recall_at_k": 1.0, "mrr": 0.5},
        "bridge_reserve": {"recall_at_k": 1.0, "mrr": 1.0},
        "random_reserve": {"recall_at_k": 0.9, "mrr": 0.4},
    }
    small = evaluate_bridge_trial_promotion([row] * 8, arms)
    assert small["eligible"] is False
    assert small["gates"]["sample_ready"] is False

    rows = [
        {
            **row,
            "selected": {"path": "bridge/c.py"} if index < 10 else None,
        }
        for index in range(64)
    ]
    ready = evaluate_bridge_trial_promotion(
        rows,
        arms,
        p95_baseline_ms=100.0,
        p95_trial_overhead_ms=2.0,
    )
    assert ready["eligible"] is True
    assert ready["gates"]["mrr_lift_supported"] is True
    assert ready["gates"]["beats_random_control"] is True
