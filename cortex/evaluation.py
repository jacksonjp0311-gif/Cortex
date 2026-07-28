"""Repository-native replay and GCMT failure-case evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from .neuron import activate_interlink
from .retrieval import query


def load_corpus(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        payload = {"schema_version": "1.0", "cases": payload}
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("Evaluation corpus must contain a cases list")
    return payload


def _rank(paths: list[str], expected: set[str]) -> int | None:
    for index, path in enumerate(paths, 1):
        if path in expected:
            return index
    return None


def _metrics(results: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    eligible = [item for item in results if item["expected_paths"]]
    ranks = [item[mode]["rank"] for item in eligible]
    found = [rank for rank in ranks if rank is not None]
    recall = len(found) / max(1, len(eligible))
    mrr = mean([1.0 / rank if rank else 0.0 for rank in ranks]) if ranks else 0.0
    boundary_cases = [item for item in results if item["forbidden_paths"]]
    boundary_errors = sum(bool(item[mode]["forbidden_fired"]) for item in boundary_cases)
    abstention_cases = [item for item in results if item["should_abstain"]]
    abstention_correct = sum(item[mode]["abstained"] for item in abstention_cases)
    return {
        "cases": len(results),
        "recall_at_node_budget": round(recall, 6),
        "mean_reciprocal_rank": round(mrr, 6),
        "boundary_separation": round(
            1.0 - boundary_errors / max(1, len(boundary_cases)), 6
        ),
        "abstention_accuracy": round(
            abstention_correct / max(1, len(abstention_cases)), 6
        ),
    }


def evaluate_corpus(
    store: Any,
    corpus: dict[str, Any],
    *,
    default_repo: str | None = None,
    limit: int = 24,
    semantic_scan_limit: int = 5000,
) -> dict[str, Any]:
    """Compare structural priors with learned weights on identical replay cases."""
    results: list[dict[str, Any]] = []
    for index, case in enumerate(corpus["cases"], 1):
        repo = str(case.get("repo") or default_repo or "")
        if not repo or not store.repo(repo):
            raise ValueError(f"Case {index} has no attached repository")
        task = str(case.get("task") or case.get("query") or "").strip()
        if not task:
            raise ValueError(f"Case {index} has no task")
        expected = {str(path) for path in case.get("expected_paths", [])}
        forbidden = {str(path) for path in case.get("forbidden_paths", [])}
        should_abstain = bool(case.get("should_abstain", False))
        hits = query(
            store,
            repo,
            task,
            limit=limit,
            semantic_scan_limit=semantic_scan_limit,
        )
        confidence = max(
            (float(hit.metadata.get("semantic_similarity", 0.0)) for hit in hits),
            default=0.0,
        )
        modes: dict[str, Any] = {}
        for mode in ("base", "learned"):
            packet = activate_interlink(
                store,
                repo,
                task,
                hits,
                weight_mode=mode,
                record=False,
                plasticity_enabled=False,
                governance_mode="read_only",
            )
            fired = list(packet.fired_paths)
            modes[mode] = {
                "rank": _rank(fired, expected),
                "fired_paths": fired,
                "forbidden_fired": sorted(forbidden.intersection(fired)),
                "abstained": not hits or confidence < float(case.get("abstain_below", 0.05)),
                "state_hash": packet.state_hash,
            }
        results.append(
            {
                "case_id": str(case.get("id") or f"case-{index}"),
                "category": str(case.get("category") or "source_recall"),
                "repo": repo,
                "task": task,
                "expected_paths": sorted(expected),
                "forbidden_paths": sorted(forbidden),
                "should_abstain": should_abstain,
                "retrieval_confidence": round(confidence, 6),
                **modes,
            }
        )
    base = _metrics(results, "base")
    learned = _metrics(results, "learned")
    improved = sum(
        1
        for item in results
        if item["learned"]["rank"]
        and (
            not item["base"]["rank"]
            or item["learned"]["rank"] < item["base"]["rank"]
        )
    )
    regressed = sum(
        1
        for item in results
        if item["base"]["rank"]
        and (
            not item["learned"]["rank"]
            or item["learned"]["rank"] > item["base"]["rank"]
        )
    )
    return {
        "schema_version": "cortex-evaluation/1.0",
        "corpus": {
            "name": corpus.get("name", "unnamed"),
            "version": corpus.get("version", "1.0"),
            "cases": len(results),
        },
        "baseline": base,
        "learned": learned,
        "delta": {
            "recall": round(
                learned["recall_at_node_budget"] - base["recall_at_node_budget"], 6
            ),
            "mean_reciprocal_rank": round(
                learned["mean_reciprocal_rank"] - base["mean_reciprocal_rank"], 6
            ),
            "improved_cases": improved,
            "regressed_cases": regressed,
        },
        "gate": {
            "no_retrieval_regression": (
                learned["recall_at_node_budget"] >= base["recall_at_node_budget"]
                and learned["mean_reciprocal_rank"] >= base["mean_reciprocal_rank"]
            ),
            "boundary_preserved": learned["boundary_separation"] >= base["boundary_separation"],
            "promotion_ready": bool(results) and regressed == 0,
        },
        "results": results,
        "claim_class": "benchmark_evidence",
        "claim_boundary": (
            "Results apply only to this declared corpus and configuration; "
            "they are not universal answer-quality evidence."
        ),
    }
