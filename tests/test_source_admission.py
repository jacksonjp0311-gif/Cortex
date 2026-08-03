"""v8.2.3 source-admission field falsification tests."""

from __future__ import annotations

from cortex.source_admission import (
    _selective_choice,
    evaluate_source_admission_promotion,
    source_admission_score,
    source_trial_context_hash,
)


def _metrics(recall: float, mrr: float) -> dict[str, float]:
    return {"recall": recall, "mrr": mrr}


def test_source_admission_uses_conjunctive_hard_floors() -> None:
    eligible = source_admission_score(
        query_text="source admission module",
        path="cortex/source_admission.py",
        semantic_similarity=0.82,
        lexical_rank=1,
    )
    weak_semantic = source_admission_score(
        query_text="source admission module",
        path="cortex/source_admission.py",
        semantic_similarity=-0.80,
        lexical_rank=1,
    )
    documentation = source_admission_score(
        query_text="source admission module",
        path="docs/source_admission.md",
        semantic_similarity=0.99,
        lexical_rank=1,
    )

    assert eligible["eligible"] is True
    assert weak_semantic["eligible"] is False
    assert documentation["eligible"] is False
    assert eligible["triadic_alignment"] > weak_semantic["triadic_alignment"]


def test_source_trial_context_binds_epoch_graph_corpus_and_parameters() -> None:
    base = source_trial_context_hash(
        corpus_hash="corpus",
        body_epoch_id="epoch-a",
        graph_fingerprint="graph-a",
        parameters={"pool_size": 24},
    )
    assert base == source_trial_context_hash(
        corpus_hash="corpus",
        body_epoch_id="epoch-a",
        graph_fingerprint="graph-a",
        parameters={"pool_size": 24},
    )
    assert base != source_trial_context_hash(
        corpus_hash="corpus",
        body_epoch_id="epoch-b",
        graph_fingerprint="graph-a",
        parameters={"pool_size": 24},
    )
    assert base != source_trial_context_hash(
        corpus_hash="corpus",
        body_epoch_id="epoch-a",
        graph_fingerprint="graph-b",
        parameters={"pool_size": 24},
    )


def test_promotion_requires_three_consistent_distinct_contexts() -> None:
    rows = [
        {
            "pool_ranks": {"baseline": None, "source_reserve": 24},
            "final_ranks": {"baseline": None, "source_reserve": 4},
            "selected": {"path": "cortex/source_admission.py"},
            "fixed_cardinality": True,
            "policy_effect": False,
        }
        for _ in range(64)
    ]
    pool_arms = {
        "baseline": _metrics(0.20, 0.08),
        "source_reserve": _metrics(0.30, 0.10),
        "random_source": _metrics(0.20, 0.08),
    }
    final_arms = {
        "baseline": _metrics(0.20, 0.08),
        "source_reserve": _metrics(0.25, 0.10),
        "random_source": _metrics(0.20, 0.08),
    }
    one = evaluate_source_admission_promotion(
        rows,
        pool_arms,
        final_arms,
        replication_history=[
            {"trial_context_hash": "a", "pool_recall_delta": 0.10, "harmful_replacements": 0}
        ],
    )
    three = evaluate_source_admission_promotion(
        rows,
        pool_arms,
        final_arms,
        replication_history=[
            {"trial_context_hash": value, "pool_recall_delta": 0.10, "harmful_replacements": 0}
            for value in ("a", "b", "c")
        ],
    )

    assert one["eligible"] is False
    assert one["gates"]["replicated_three_contexts"] is False
    assert three["gates"]["replicated_three_contexts"] is True
    assert three["eligible"] is False  # selection rate is deliberately over the 0.50 cap


def test_promotion_rejects_harm_and_random_control_ties() -> None:
    rows = [
        {
            "pool_ranks": {"baseline": 2, "source_reserve": 2},
            "final_ranks": {"baseline": 2, "source_reserve": None},
            "selected": None,
            "fixed_cardinality": True,
            "policy_effect": False,
        }
        for _ in range(64)
    ]
    arms = {
        "baseline": _metrics(0.50, 0.25),
        "source_reserve": _metrics(0.50, 0.25),
        "random_source": _metrics(0.50, 0.25),
    }
    result = evaluate_source_admission_promotion(rows, arms, arms)

    assert result["eligible"] is False
    assert result["gates"]["pool_recall_lift"] is False
    assert result["gates"]["beats_random_source"] is False
    assert result["gates"]["no_harmful_replacements"] is False


def test_selective_admission_abstains_on_ambiguous_margin() -> None:
    candidates = [
        ({"path": "cortex/a.py"}, {"path": "cortex/a.py", "triadic_alignment": 0.72, "eligible": True}),
        ({"path": "cortex/b.py"}, {"path": "cortex/b.py", "triadic_alignment": 0.70, "eligible": True}),
    ]
    assert _selective_choice(candidates) is None

    decisive = [
        ({"path": "cortex/a.py"}, {"path": "cortex/a.py", "triadic_alignment": 0.78, "eligible": True}),
        ({"path": "cortex/b.py"}, {"path": "cortex/b.py", "triadic_alignment": 0.68, "eligible": True}),
    ]
    selected = _selective_choice(decisive)
    assert selected is not None
    assert selected[1]["abstained"] is False
    assert 0.0 <= selected[1]["predicted_harm_risk"] <= 1.0


def test_promotion_exposes_ranker_attribution_gate() -> None:
    rows = [
        {
            "final_ranks": {"baseline": 2, "source_reserve": 2},
            "selected": None,
            "fixed_cardinality": True,
            "policy_effect": False,
        }
        for _ in range(64)
    ]
    arms = {"baseline": _metrics(0.5, 0.25), "source_reserve": _metrics(0.5, 0.25), "random_source": _metrics(0.4, 0.2)}
    result = evaluate_source_admission_promotion(
        rows,
        arms,
        arms,
        hybrid_arms={"baseline": _metrics(0.6, 0.3), "source_reserve": _metrics(0.7, 0.35)},
    )
    assert result["gates"]["attribution_available"] is True
    assert result["ranker_stage_delta"] == -0.2
    assert result["gates"]["calibration_ready"] is False
