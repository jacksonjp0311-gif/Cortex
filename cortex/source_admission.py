"""v8.2.3 source-admission field.

This module measures the boundary before ranking: whether query-relevant host
source enters a fixed candidate pool.  Every arm is counterfactual and operates
on copied hits; live retrieval, training, topology, and policy are untouched.
"""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import time
from typing import Any, Sequence

from .retrieval import path_token_overlap, query, support_hits


SCHEMA = "cortex-source-admission-field/1.0"
GLYPH = "⟢"
VERSION = "8.2.3"
CLAIM = (
    "Source admission is shadow-only retrieval telemetry. It does not change "
    "live results, train the ranker, mutate topology, grant authority, or "
    "establish consciousness or subjective sensing."
)
SOURCE_SUFFIXES = (".py", ".pyi", ".rs", ".go", ".java", ".js", ".jsx", ".ts", ".tsx")
DOCUMENT_PREFIXES = ("docs/", ".cortex/cards/", "examples/memory-packets/")


def _path(hit: Any) -> str:
    return str(hit.get("path") if isinstance(hit, dict) else getattr(hit, "path", "")).replace("\\", "/")


def _score(hit: Any) -> float:
    value = hit.get("score") if isinstance(hit, dict) else getattr(hit, "score", 0.0)
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _metadata(hit: Any) -> dict[str, Any]:
    value = hit.get("metadata") if isinstance(hit, dict) else getattr(hit, "metadata", {})
    return dict(value or {})


def _is_source(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        normalized.endswith(SOURCE_SUFFIXES)
        and not normalized.startswith("cortex/aria_meta/vendor/")
        and "/node_modules/" not in f"/{normalized}"
    )


def _is_document_or_card(hit: Any) -> bool:
    path = _path(hit)
    kind = str(hit.get("kind") if isinstance(hit, dict) else getattr(hit, "kind", ""))
    return path.startswith(DOCUMENT_PREFIXES) or kind in {"discovery_card", "documentation"}


def _evidence_reliability(path: str) -> float:
    normalized = path.replace("\\", "/")
    if normalized.startswith("tests/") or "/tests/" in f"/{normalized}":
        return 0.90
    if normalized.startswith("scripts/"):
        return 0.82
    if _is_source(normalized):
        return 1.0
    return 0.0


def _first_rank(paths: Sequence[str], expected: Sequence[str]) -> int | None:
    normalized = [str(path).replace("\\", "/") for path in paths]
    for index, path in enumerate(normalized):
        for target in expected:
            expected_path = str(target).replace("\\", "/")
            if expected_path in path or path.endswith(expected_path):
                return index + 1
    return None


def _percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = min(len(ordered) - 1, max(0, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]


def _corpus_hash(cases: Sequence[dict[str, Any]]) -> str:
    payload = json.dumps(list(cases), sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def source_trial_context_hash(
    *,
    corpus_hash: str,
    body_epoch_id: str | None,
    graph_fingerprint: str,
    parameters: dict[str, Any],
) -> str:
    payload = json.dumps(parameters, sort_keys=True, separators=(",", ":"))
    return sha256(
        f"{corpus_hash}|{body_epoch_id}|{graph_fingerprint}|{payload}".encode("utf-8")
    ).hexdigest()


def source_admission_score(
    *,
    query_text: str,
    path: str,
    semantic_similarity: float,
    lexical_rank: int,
    lexical_floor: float = 0.15,
    semantic_floor: float = 0.45,
    evidence_floor: float = 0.80,
    alignment_floor: float = 0.48,
) -> dict[str, Any]:
    """Compute hard-floor triadic source admission A=(L*S*E)^(1/3)."""
    rank_signal = 1.0 / math.log2(max(2, int(lexical_rank)) + 2.0)
    lexical = max(path_token_overlap(query_text, path), rank_signal)
    raw_semantic = max(-1.0, min(1.0, float(semantic_similarity)))
    # Cosine occupies [-1, 1]; map it to a unit interval before applying a
    # probability-shaped hard floor.  This calibration is representation-level
    # and independent of the frozen evaluation corpus.
    semantic = 0.5 * (raw_semantic + 1.0)
    evidence = _evidence_reliability(path)
    product = lexical * semantic * evidence
    alignment = product ** (1.0 / 3.0) if product > 0.0 else 0.0
    eligible = bool(
        lexical >= lexical_floor
        and semantic >= semantic_floor
        and evidence >= evidence_floor
        and alignment >= alignment_floor
    )
    return {
        "path": path.replace("\\", "/"),
        "lexical_alignment": round(lexical, 8),
        "raw_semantic_similarity": round(raw_semantic, 8),
        "semantic_similarity": round(semantic, 8),
        "evidence_reliability": round(evidence, 8),
        "triadic_alignment": round(alignment, 8),
        "eligible": eligible,
        "shadow_only": True,
    }


def _rescale_candidate(candidate: Any, baseline: Sequence[Any], admission: dict[str, Any]) -> Any:
    copied = deepcopy(candidate)
    baseline_scores = [_score(hit) for hit in baseline]
    tail = min(baseline_scores, default=0.0)
    ceiling = max(baseline_scores, default=max(0.01, tail))
    alignment = float(admission.get("triadic_alignment") or 0.0)
    comparable = tail + max(0.0, ceiling - tail) * min(0.35, 0.20 * alignment)
    comparable = max(tail, min(ceiling, comparable))
    metadata = {**_metadata(copied), "source_admission_shadow": dict(admission)}
    if isinstance(copied, dict):
        copied["score"] = round(comparable, 8)
        copied["metadata"] = metadata
    else:
        copied.score = round(comparable, 8)
        copied.metadata = metadata
    return copied


def _replace_tail(pool: Sequence[Any], candidate: Any | None) -> list[Any]:
    output = deepcopy(list(pool))
    if candidate is not None and output and _path(candidate) not in {_path(hit) for hit in output}:
        output[-1] = candidate
    return output


def _rerank(store: Any, repo: str, hits: Sequence[Any]) -> list[Any]:
    from .ranker.model import rerank_hits

    return rerank_hits(
        store,
        repo,
        deepcopy(list(hits)),
        retrieval_confidence=0.55,
        primary=True,
        enrich_spectral=False,
    )


def _source_candidates(
    store: Any,
    repo: str,
    query_text: str,
    baseline: Sequence[Any],
    *,
    lexical_limit: int = 200,
) -> tuple[list[dict[str, Any]], list[tuple[Any, dict[str, Any]]]]:
    baseline_paths = {_path(hit) for hit in baseline}
    lexical_rows = list(store.lexical(repo, query_text, lexical_limit, excluded_prefixes=()))
    source_ranks: dict[str, int] = {}
    for rank, row in enumerate(lexical_rows, 1):
        path = str(row["path"]).replace("\\", "/")
        if _is_source(path) and path not in source_ranks and path not in baseline_paths:
            source_ranks[path] = rank
    support = support_hits(store, repo, query_text, list(source_ranks)[:96], limit=64)
    evaluated: list[tuple[Any, dict[str, Any]]] = []
    telemetry: list[dict[str, Any]] = []
    for hit in support:
        path = _path(hit)
        admission = source_admission_score(
            query_text=query_text,
            path=path,
            semantic_similarity=float(_metadata(hit).get("semantic_similarity") or 0.0),
            lexical_rank=source_ranks.get(path, lexical_limit),
        )
        telemetry.append(admission)
        evaluated.append((hit, admission))
    evaluated.sort(
        key=lambda item: (-float(item[1]["triadic_alignment"]), str(item[1]["path"]))
    )
    telemetry.sort(key=lambda item: (-float(item["triadic_alignment"]), str(item["path"])))
    return telemetry, evaluated


def source_admission_trial(
    store: Any,
    repo: str,
    query_text: str,
    raw_hits: Sequence[Any],
    *,
    pool_size: int = 24,
    widened_size: int = 48,
    top_k: int = 5,
) -> dict[str, Any]:
    """Run matched source-admission arms for one query."""
    pool_n = max(2, int(pool_size))
    widened_n = max(pool_n, int(widened_size))
    k = max(1, int(top_k))
    baseline = list(raw_hits[:pool_n])
    widened = list(raw_hits[:widened_n])
    telemetry, evaluated = _source_candidates(store, repo, query_text, baseline)
    eligible = [(hit, item) for hit, item in evaluated if item["eligible"]]
    selected = eligible[0] if eligible else None
    source_hit = _rescale_candidate(selected[0], baseline, selected[1]) if selected else None

    random_selected = None
    if evaluated:
        seed = int(sha256(query_text.encode("utf-8")).hexdigest()[:16], 16)
        random_selected = sorted(evaluated, key=lambda item: str(item[1]["path"]))[
            random.Random(seed).randrange(len(evaluated))
        ]
    random_hit = (
        _rescale_candidate(random_selected[0], baseline, random_selected[1])
        if random_selected
        else None
    )
    source_pool = _replace_tail(baseline, source_hit)
    random_pool = _replace_tail(baseline, random_hit)
    doc_suppressed = [hit for hit in widened if not _is_document_or_card(hit)][:pool_n]
    if len(doc_suppressed) < pool_n:
        seen = {_path(hit) for hit in doc_suppressed}
        doc_suppressed.extend(
            hit for hit in widened if _path(hit) not in seen
        )
        doc_suppressed = doc_suppressed[:pool_n]

    pools = {
        "baseline": baseline,
        "widened": widened,
        "source_reserve": source_pool,
        "random_source": random_pool,
        "documentation_suppression": doc_suppressed,
    }
    ranked = {arm: _rerank(store, repo, hits) for arm, hits in pools.items()}
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "query_hash": sha256(query_text.encode("utf-8")).hexdigest(),
        "formula": "A(q,v)=(lexical_alignment*semantic_similarity*evidence_reliability)^(1/3)",
        "floors": {"lexical": 0.15, "semantic": 0.45, "evidence": 0.80, "alignment": 0.48},
        "pools": {arm: [_path(hit) for hit in hits] for arm, hits in pools.items()},
        "ranked": {arm: [_path(hit) for hit in hits[:k]] for arm, hits in ranked.items()},
        "source_candidates": telemetry[:12],
        "selected": selected[1] if selected else None,
        "random_selected": random_selected[1] if random_selected else None,
        "fixed_cardinality": len(source_pool) == len(baseline) == len(random_pool),
        "live_results_unchanged": True,
        "policy_effect": False,
        "claim_boundary": CLAIM,
    }


def _arm_metrics(rows: Sequence[dict[str, Any]], arm: str, stage: str) -> dict[str, Any]:
    ranks = [row[f"{stage}_ranks"].get(arm) for row in rows]
    n = max(1, len(rows))
    hits = sum(rank is not None for rank in ranks)
    return {
        "cases": len(rows),
        "hits": hits,
        "recall": round(hits / n, 8),
        "mrr": round(sum((1.0 / rank) if rank else 0.0 for rank in ranks) / n, 8),
    }


def evaluate_source_admission_promotion(
    rows: Sequence[dict[str, Any]],
    pool_arms: dict[str, dict[str, Any]],
    final_arms: dict[str, dict[str, Any]],
    *,
    replication_history: Sequence[dict[str, Any]] = (),
    min_cases: int = 64,
    p95_overhead_ms: float = 0.0,
) -> dict[str, Any]:
    baseline_pool = pool_arms.get("baseline") or {}
    source_pool = pool_arms.get("source_reserve") or {}
    baseline_final = final_arms.get("baseline") or {}
    source_final = final_arms.get("source_reserve") or {}
    random_final = final_arms.get("random_source") or {}
    helpful = harmful = selected = 0
    for row in rows:
        before = row["final_ranks"].get("baseline")
        after = row["final_ranks"].get("source_reserve")
        helpful += int(before is None and after is not None)
        harmful += int(before is not None and after is None)
        selected += int(bool(row.get("selected")))
    pool_delta = float(source_pool.get("recall") or 0.0) - float(baseline_pool.get("recall") or 0.0)
    final_delta = float(source_final.get("recall") or 0.0) - float(baseline_final.get("recall") or 0.0)
    mrr_delta = float(source_final.get("mrr") or 0.0) - float(baseline_final.get("mrr") or 0.0)
    contexts = {str(item.get("trial_context_hash")) for item in replication_history if item.get("trial_context_hash")}
    consistent = [
        item for item in replication_history
        if float(item.get("pool_recall_delta") or 0.0) >= 0.0
        and int(item.get("harmful_replacements") or 0) == 0
    ]
    gates = {
        "sample_ready": len(rows) >= max(1, int(min_cases)),
        "pool_recall_lift": pool_delta > 0.0,
        "final_recall_noninferior": final_delta >= 0.0,
        "final_mrr_noninferior": mrr_delta >= 0.0,
        "beats_random_source": (
            float(source_final.get("recall") or 0.0), float(source_final.get("mrr") or 0.0)
        ) > (
            float(random_final.get("recall") or 0.0), float(random_final.get("mrr") or 0.0)
        ),
        "no_harmful_replacements": harmful == 0,
        "selection_bounded": selected / max(1, len(rows)) <= 0.50,
        "latency_bounded": float(p95_overhead_ms) <= 250.0,
        "fixed_cardinality": all(bool(row.get("fixed_cardinality")) for row in rows),
        "policy_inert": all(row.get("policy_effect") is False for row in rows),
        "replicated_three_contexts": len(contexts) >= 3 and len(consistent) >= 3,
    }
    return {
        "eligible": all(gates.values()),
        "gates": gates,
        "pool_recall_delta": round(pool_delta, 8),
        "final_recall_delta": round(final_delta, 8),
        "final_mrr_delta": round(mrr_delta, 8),
        "helpful_replacements": helpful,
        "harmful_replacements": harmful,
        "selection_rate": round(selected / max(1, len(rows)), 8),
        "replication_contexts": len(contexts),
        "policy_effect": False,
    }


def _graph_fingerprint(store: Any, repo: str) -> str:
    from .math_net.ratio_lattice import build_undirected_adj

    adjacency = build_undirected_adj(store, repo, max_nodes=0)
    material = "\n".join(
        f"{node}|{'|'.join(sorted(neighbors))}" for node, neighbors in sorted(adjacency.items())
    )
    return sha256(material.encode("utf-8")).hexdigest()


def run_source_admission_suite(
    home: Path,
    store: Any,
    repo: str,
    *,
    suite: str = "bridge64",
    pool_size: int = 24,
    widened_size: int = 48,
    top_k: int = 5,
    min_cases: int = 64,
    persist: bool = True,
) -> dict[str, Any]:
    """Run the frozen 64-case source-admission experiment."""
    if suite != "bridge64":
        raise ValueError("source admission currently requires the frozen bridge64 suite")
    from .bridge_trial_corpus import BRIDGE_TRIAL_CORPUS, BRIDGE_TRIAL_FREEZE_ID
    from .epoch import current_body_epoch

    cases = list(BRIDGE_TRIAL_CORPUS)
    corpus_hash = _corpus_hash(cases)
    graph_fingerprint = _graph_fingerprint(store, repo)
    body_epoch = current_body_epoch(store, repo)
    body_epoch_id = body_epoch.epoch_id if body_epoch else None
    parameters = {
        "pool_size": int(pool_size), "widened_size": int(widened_size), "top_k": int(top_k),
        "floors": {"lexical": 0.15, "semantic": 0.45, "evidence": 0.80, "alignment": 0.48},
    }
    context_hash = source_trial_context_hash(
        corpus_hash=corpus_hash,
        body_epoch_id=body_epoch_id,
        graph_fingerprint=graph_fingerprint,
        parameters=parameters,
    )
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case in cases:
        query_text = str(case["query"])
        raw_hits = query(
            store, repo, query_text, limit=max(int(widened_size), int(pool_size)),
            ranker_primary=False, enrich_spectral=False, concept_routes=True,
        )
        started = time.perf_counter()
        trial = source_admission_trial(
            store, repo, query_text, raw_hits,
            pool_size=pool_size, widened_size=widened_size, top_k=top_k,
        )
        latencies.append((time.perf_counter() - started) * 1000.0)
        expected = [str(item) for item in case.get("expected_substrings") or []]
        rows.append({
            "id": case.get("id"),
            "query_hash": trial["query_hash"],
            "expected_substrings": expected,
            "pool_ranks": {arm: _first_rank(paths, expected) for arm, paths in trial["pools"].items()},
            "final_ranks": {arm: _first_rank(paths, expected) for arm, paths in trial["ranked"].items()},
            "selected": trial.get("selected"),
            "random_selected": trial.get("random_selected"),
            "candidate_count": len(trial.get("source_candidates") or []),
            "fixed_cardinality": trial["fixed_cardinality"],
            "policy_effect": False,
        })
    arms = ("baseline", "widened", "source_reserve", "random_source", "documentation_suppression")
    pool_arms = {arm: _arm_metrics(rows, arm, "pool") for arm in arms}
    final_arms = {arm: _arm_metrics(rows, arm, "final") for arm in arms}
    history_key = f"source_admission_history:{repo}:{BRIDGE_TRIAL_FREEZE_ID}"
    history = list(store.get_setting(history_key, []) or [])
    p95 = _percentile(latencies, 0.95)
    provisional = {
        "trial_context_hash": context_hash,
        "body_epoch_id": body_epoch_id,
        "graph_fingerprint": graph_fingerprint,
        "pool_recall_delta": round(pool_arms["source_reserve"]["recall"] - pool_arms["baseline"]["recall"], 8),
        "final_recall_delta": round(final_arms["source_reserve"]["recall"] - final_arms["baseline"]["recall"], 8),
        "harmful_replacements": sum(
            int(row["final_ranks"]["baseline"] is not None and row["final_ranks"]["source_reserve"] is None)
            for row in rows
        ),
        "created_at": round(time.time(), 3),
    }
    history = [item for item in history if item.get("trial_context_hash") != context_hash]
    evaluation_history = [*history, provisional][-8:]
    promotion = evaluate_source_admission_promotion(
        rows, pool_arms, final_arms,
        replication_history=evaluation_history,
        min_cases=min_cases,
        p95_overhead_ms=p95,
    )
    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": VERSION,
        "repo": repo,
        "suite": suite,
        "freeze_id": BRIDGE_TRIAL_FREEZE_ID,
        "corpus_hash": corpus_hash,
        "body_epoch_id": body_epoch_id,
        "graph_fingerprint": graph_fingerprint,
        "trial_context_hash": context_hash,
        "parameters": parameters,
        "case_count": len(rows),
        "candidate_stage": pool_arms,
        "final_stage": final_arms,
        "promotion": promotion,
        "latency_ms": {"admission_and_rerank_p95": round(p95, 6)},
        "replication_history": evaluation_history,
        "rows": rows,
        "live_results_unchanged": True,
        "policy_effect": False,
        "claim_boundary": CLAIM,
    }
    if persist:
        store.set_setting(history_key, evaluation_history)
        store.set_setting(f"source_admission_latest:{repo}", report)
        log_dir = Path(home) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"source-admission-{repo}-{int(time.time())}.json"
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        report["report_path"] = str(path)
    return report


__all__ = [
    "CLAIM", "GLYPH", "SCHEMA", "VERSION", "evaluate_source_admission_promotion",
    "run_source_admission_suite", "source_admission_score", "source_admission_trial",
    "source_trial_context_hash",
]
