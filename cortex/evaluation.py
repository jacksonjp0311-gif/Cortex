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


def evaluate_retrieval_corpus(
    store: Any,
    corpus: dict[str, Any],
    *,
    default_repo: str | None = None,
    limit: int = 8,
    top_k: int = 3,
) -> dict[str, Any]:
    """Path-recall regression: expected paths must appear in top-k hits."""

    results: list[dict[str, Any]] = []
    hits_at_k = 0
    for index, case in enumerate(corpus.get("cases") or [], 1):
        repo = str(case.get("repo") or default_repo or "")
        if not repo or not store.repo(repo):
            raise ValueError(f"Retrieval case {index} has no attached repository")
        query_text = str(case.get("query") or case.get("task") or "").strip()
        expected = [str(path) for path in case.get("expected_paths", [])]
        if not query_text or not expected:
            raise ValueError(f"Retrieval case {index} needs query and expected_paths")
        hits = query(store, repo, query_text, limit=limit)
        paths = [hit.path.replace("\\", "/") for hit in hits[:top_k]]
        expected_norm = [path.replace("\\", "/") for path in expected]
        found = any(
            any(path == exp or path.endswith(exp) or exp.endswith(path) for exp in expected_norm)
            for path in paths
        )
        if found:
            hits_at_k += 1
        results.append(
            {
                "id": case.get("id") or f"case-{index}",
                "query": query_text,
                "expected_paths": expected_norm,
                "returned_paths": paths,
                "hit_at_k": found,
            }
        )
    total = max(1, len(results))
    recall = hits_at_k / total
    return {
        "schema_version": "cortex-retrieval-eval/1.0",
        "glyph": "⌖",
        "top_k": top_k,
        "cases": len(results),
        "hits_at_k": hits_at_k,
        "recall_at_k": round(recall, 6),
        "passed": recall >= float(corpus.get("minimum_recall_at_k", 0.5)),
        "results": results,
        "claim_boundary": (
            corpus.get("claim_boundary")
            or "Path-recall regression only; not universal answer quality."
        ),
    }


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
