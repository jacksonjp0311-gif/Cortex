"""v8.2.2 query-conditioned geometric bridge trials.

The trial lane is counterfactual and fixed-cardinality.  It never changes the
live query result, ranker, graph, or policy.  A bridge candidate must jointly
satisfy relevance, structural bridge potential, and neighborhood novelty.
"""

from __future__ import annotations

from hashlib import sha256
import math
from pathlib import Path
import random
import time
from typing import Any, Sequence

from .math_net.info_interlock import bridge_deconcentration_report
from .math_net.ratio_lattice import build_undirected_adj


SCHEMA = "cortex-query-bridge-trial/1.0"
GLYPH = "⟐"
CLAIM = (
    "Query-conditioned bridge trials are paired shadow retrieval experiments. "
    "They do not alter live ranking, train the ranker, mutate topology, grant "
    "authority, or establish consciousness."
)


def _path(hit: Any) -> str:
    return str(hit.get("path") if isinstance(hit, dict) else getattr(hit, "path", ""))


def _score(hit: Any) -> float:
    value = hit.get("score") if isinstance(hit, dict) else getattr(hit, "score", 0.0)
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _region(path: str) -> str:
    parts = str(path).replace("\\", "/").strip("/").split("/")
    if not parts or not parts[0]:
        return "unknown"
    if parts[0].startswith("symbol:"):
        return "symbol"
    if len(parts) >= 3 and "." not in parts[1]:
        return "/".join(parts[:2])
    return parts[0]


def _first_rank(paths: Sequence[str], expected: Sequence[str]) -> int | None:
    normalized = [str(path).replace("\\", "/") for path in paths]
    for index, path in enumerate(normalized):
        for target in expected:
            exp = str(target).replace("\\", "/")
            if exp in path or path.endswith(exp) or exp in path.split("/")[-1]:
                return index + 1
    return None


def _replace_tail(paths: Sequence[str], candidate: str | None) -> list[str]:
    output = list(paths)
    if candidate and output and candidate not in output:
        output[-1] = candidate
    return output


def query_conditioned_bridge_trial(
    query_text: str,
    hits: Sequence[Any],
    *,
    bridge_scores: dict[str, dict[str, Any]],
    adjacency: dict[str, set[str]] | None = None,
    top_k: int = 5,
    relevance_floor_ratio: float = 0.72,
    bridge_floor: float = 0.65,
    novelty_floor: float = 0.25,
    triadic_floor: float = 0.80,
) -> dict[str, Any]:
    """Build fixed-cardinality bridge and random-control counterfactuals."""
    k = max(1, int(top_k))
    baseline_hits = list(hits[:k])
    baseline_paths = [_path(hit) for hit in baseline_hits]
    if not baseline_hits:
        return {
            "schema_version": SCHEMA,
            "glyph": GLYPH,
            "query_hash": sha256(query_text.encode("utf-8")).hexdigest(),
            "arms": {"baseline": [], "annotation_only": [], "bridge_reserve": [], "random_reserve": []},
            "selected": None,
            "random_selected": None,
            "policy_effect": False,
            "claim_boundary": CLAIM,
        }

    baseline_regions = {_region(path) for path in baseline_paths}
    top_score = max(abs(_score(hit)) for hit in baseline_hits) or 1.0
    tail_score = _score(baseline_hits[-1])
    raw_floor = tail_score * max(0.0, float(relevance_floor_ratio))
    candidates: list[dict[str, Any]] = []
    random_pool: list[dict[str, Any]] = []
    adj = adjacency or {}

    for hit in hits[k:]:
        path = _path(hit)
        if not path or path in baseline_paths:
            continue
        raw_score = _score(hit)
        relevance = max(0.0, min(1.0, raw_score / top_score))
        bridge = bridge_scores.get(path) or {}
        bridge_potential = max(0.0, min(1.0, float(bridge.get("bridge_potential") or 0.0)))
        region_novel = 1.0 if _region(path) not in baseline_regions else 0.0
        neighbor_regions = {_region(neighbor) for neighbor in adj.get(path, set())}
        neighbor_novel = (
            len(neighbor_regions - baseline_regions) / len(neighbor_regions)
            if neighbor_regions
            else float(bridge.get("domain_diversity") or 0.0)
        )
        novelty = max(0.0, min(1.0, 0.5 * region_novel + 0.5 * neighbor_novel))
        triad = (
            relevance * bridge_potential * novelty
        ) ** (1.0 / 3.0) if relevance * bridge_potential * novelty > 0.0 else 0.0
        item = {
            "path": path,
            "raw_score": round(raw_score, 8),
            "relevance": round(relevance, 8),
            "bridge_potential": round(bridge_potential, 8),
            "novelty": round(novelty, 8),
            "triadic_alignment": round(triad, 8),
            "eligible": bool(
                raw_score >= raw_floor
                and bridge_potential >= bridge_floor
                and novelty >= novelty_floor
                and triad >= triadic_floor
            ),
            "shadow_only": True,
        }
        if raw_score >= raw_floor and novelty >= novelty_floor:
            random_pool.append(item)
        if item["eligible"]:
            candidates.append(item)

    candidates.sort(
        key=lambda item: (-float(item["triadic_alignment"]), str(item["path"]))
    )
    selected = candidates[0] if candidates else None
    random_selected = None
    if random_pool:
        ordered_random = sorted(random_pool, key=lambda item: str(item["path"]))
        seed = int(sha256(query_text.encode("utf-8")).hexdigest()[:16], 16)
        random_selected = ordered_random[random.Random(seed).randrange(len(ordered_random))]

    bridge_path = str(selected["path"]) if selected else None
    random_path = str(random_selected["path"]) if random_selected else None
    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "query_hash": sha256(query_text.encode("utf-8")).hexdigest(),
        "formula": "T(q,v)=(relevance*bridge_potential*novelty)^(1/3)",
        "floors": {
            "relevance_tail_ratio": float(relevance_floor_ratio),
            "bridge_potential": float(bridge_floor),
            "novelty": float(novelty_floor),
            "triadic_alignment": float(triadic_floor),
        },
        "arms": {
            "baseline": baseline_paths,
            "annotation_only": list(baseline_paths),
            "bridge_reserve": _replace_tail(baseline_paths, bridge_path),
            "random_reserve": _replace_tail(baseline_paths, random_path),
        },
        "candidate_count": len(candidates),
        "selected": selected,
        "random_selected": random_selected,
        "fixed_cardinality": all(
            len(paths) == len(baseline_paths)
            for paths in (
                _replace_tail(baseline_paths, bridge_path),
                _replace_tail(baseline_paths, random_path),
            )
        ),
        "live_results_unchanged": True,
        "policy_effect": False,
        "claim_boundary": CLAIM,
    }


def _percentile(values: Sequence[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = min(len(ordered) - 1, max(0, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]


def _paired_bootstrap_ci(
    values: Sequence[float], *, seed_material: str, rounds: int = 1000
) -> list[float]:
    if not values:
        return [0.0, 0.0]
    rng = random.Random(int(sha256(seed_material.encode("utf-8")).hexdigest()[:16], 16))
    n = len(values)
    samples = [
        sum(float(values[rng.randrange(n)]) for _ in range(n)) / n
        for _ in range(max(200, int(rounds)))
    ]
    samples.sort()
    return [round(_percentile(samples, 0.025), 8), round(_percentile(samples, 0.975), 8)]


def structural_trial_context_hash(
    *,
    corpus_hash: str,
    body_epoch_id: str | None,
    graph_fingerprint: str,
    top_k: int,
    limit: int,
) -> str:
    """Bind one trial to its corpus, body, complete graph, and retrieval budget."""
    return sha256(
        f"{corpus_hash}|{body_epoch_id}|{graph_fingerprint}|{top_k}|{limit}".encode(
            "utf-8"
        )
    ).hexdigest()


def _arm_metrics(rows: Sequence[dict[str, Any]], arm: str) -> dict[str, Any]:
    ranks = [row["ranks"].get(arm) for row in rows]
    n = max(1, len(rows))
    hits = sum(rank is not None for rank in ranks)
    reciprocal = [(1.0 / rank) if rank else 0.0 for rank in ranks]
    ndcg = [(1.0 / math.log2(rank + 1.0)) if rank else 0.0 for rank in ranks]
    return {
        "cases": len(rows),
        "hits_at_k": hits,
        "recall_at_k": round(hits / n, 8),
        "mrr": round(sum(reciprocal) / n, 8),
        "ndcg": round(sum(ndcg) / n, 8),
    }


def evaluate_bridge_trial_promotion(
    rows: Sequence[dict[str, Any]],
    arms: dict[str, dict[str, Any]],
    *,
    min_cases: int = 64,
    p95_baseline_ms: float = 0.0,
    p95_trial_overhead_ms: float = 0.0,
) -> dict[str, Any]:
    baseline = arms.get("baseline") or {}
    bridge = arms.get("bridge_reserve") or {}
    random_arm = arms.get("random_reserve") or {}
    n = len(rows)
    recall_delta = float(bridge.get("recall_at_k") or 0.0) - float(
        baseline.get("recall_at_k") or 0.0
    )
    mrr_delta = float(bridge.get("mrr") or 0.0) - float(baseline.get("mrr") or 0.0)
    recall_pairs: list[float] = []
    mrr_pairs: list[float] = []
    harmful = 0
    helpful = 0
    selected = 0
    for row in rows:
        base_rank = row["ranks"].get("baseline")
        bridge_rank = row["ranks"].get("bridge_reserve")
        recall_pairs.append(float(bridge_rank is not None) - float(base_rank is not None))
        mrr_pairs.append((1.0 / bridge_rank if bridge_rank else 0.0) - (1.0 / base_rank if base_rank else 0.0))
        harmful += int(base_rank is not None and bridge_rank is None)
        helpful += int(base_rank is None and bridge_rank is not None)
        selected += int(bool(row.get("selected")))
    recall_ci = _paired_bootstrap_ci(recall_pairs, seed_material="bridge-recall")
    mrr_ci = _paired_bootstrap_ci(mrr_pairs, seed_material="bridge-mrr")
    selection_rate = selected / max(1, n)
    latency_budget = max(10.0, 0.15 * max(0.0, p95_baseline_ms))
    gates = {
        "sample_ready": n >= max(1, int(min_cases)),
        "recall_noninferior": recall_delta >= -0.01 and recall_ci[0] >= -0.02,
        "mrr_lift_supported": mrr_delta > 0.0 and mrr_ci[0] > 0.0,
        "beats_random_control": (
            float(bridge.get("recall_at_k") or 0.0),
            float(bridge.get("mrr") or 0.0),
        ) > (
            float(random_arm.get("recall_at_k") or 0.0),
            float(random_arm.get("mrr") or 0.0),
        ),
        "no_harmful_replacements": harmful == 0,
        "selection_bounded": 0.05 <= selection_rate <= 0.35,
        "latency_bounded": p95_trial_overhead_ms <= latency_budget,
        "fixed_cardinality": all(bool(row.get("fixed_cardinality")) for row in rows),
        "policy_inert": all(row.get("policy_effect") is False for row in rows),
    }
    return {
        "eligible": all(gates.values()),
        "gates": gates,
        "minimum_cases": int(min_cases),
        "selection_rate": round(selection_rate, 8),
        "helpful_replacements": helpful,
        "harmful_replacements": harmful,
        "bridge_vs_baseline": {
            "recall_delta": round(recall_delta, 8),
            "recall_delta_ci95": recall_ci,
            "mrr_delta": round(mrr_delta, 8),
            "mrr_delta_ci95": mrr_ci,
        },
        "latency_budget_ms": round(latency_budget, 8),
        "policy_effect": False,
    }


def run_bridge_trial_suite(
    home: Path,
    store: Any,
    repo: str,
    *,
    suite: str = "all",
    limit: int = 24,
    top_k: int = 5,
    min_cases: int = 64,
    persist: bool = True,
) -> dict[str, Any]:
    """Run matched baseline/bridge/random arms on a frozen retrieval corpus."""
    from .eval_coupling import resolve_corpus
    from .retrieval import query

    freeze_id = None
    if suite == "bridge64":
        from .bridge_trial_corpus import BRIDGE_TRIAL_CORPUS, BRIDGE_TRIAL_FREEZE_ID

        cases = list(BRIDGE_TRIAL_CORPUS)
        freeze_id = BRIDGE_TRIAL_FREEZE_ID
    else:
        cases = resolve_corpus(suite)
    graph_started = time.perf_counter()
    bridge_report = bridge_deconcentration_report(store, repo, limit=4096)
    adjacency = build_undirected_adj(store, repo, max_nodes=0)
    graph_fingerprint = sha256(
        "\n".join(
            f"{node}|{'|'.join(sorted(neighbors))}"
            for node, neighbors in sorted(adjacency.items())
        ).encode("utf-8")
    ).hexdigest()
    from .epoch import current_body_epoch

    body_epoch = current_body_epoch(store, repo)
    body_epoch_id = body_epoch.epoch_id if body_epoch else None
    graph_ms = (time.perf_counter() - graph_started) * 1000.0
    bridge_scores = {
        str(item["path"]): item for item in bridge_report.get("candidates", [])
    }
    rows: list[dict[str, Any]] = []
    query_latencies: list[float] = []
    trial_latencies: list[float] = []
    for case in cases:
        q = str(case["query"])
        started = time.perf_counter()
        hits = query(store, repo, q, limit=max(int(limit), int(top_k) + 8))
        query_latencies.append((time.perf_counter() - started) * 1000.0)
        trial_started = time.perf_counter()
        trial = query_conditioned_bridge_trial(
            q,
            hits,
            bridge_scores=bridge_scores,
            adjacency=adjacency,
            top_k=top_k,
        )
        trial_latencies.append((time.perf_counter() - trial_started) * 1000.0)
        expected = [str(item) for item in case.get("expected_substrings") or []]
        ranks = {
            arm: _first_rank(paths, expected)
            for arm, paths in trial["arms"].items()
        }
        rows.append(
            {
                "id": case.get("id"),
                "query_hash": trial["query_hash"],
                "expected_substrings": expected,
                "arms": trial["arms"],
                "ranks": ranks,
                "selected": trial.get("selected"),
                "random_selected": trial.get("random_selected"),
                "fixed_cardinality": trial["fixed_cardinality"],
                "policy_effect": False,
            }
        )
    arm_metrics = {
        arm: _arm_metrics(rows, arm)
        for arm in ("baseline", "annotation_only", "bridge_reserve", "random_reserve")
    }
    p95_query = _percentile(query_latencies, 0.95)
    p95_trial = _percentile(trial_latencies, 0.95)
    promotion = evaluate_bridge_trial_promotion(
        rows,
        arm_metrics,
        min_cases=min_cases,
        p95_baseline_ms=p95_query,
        p95_trial_overhead_ms=p95_trial,
    )
    corpus_hash = sha256(
        "|".join(str(case.get("id")) for case in cases).encode("utf-8")
    ).hexdigest()
    trial_context_hash = structural_trial_context_hash(
        corpus_hash=corpus_hash,
        body_epoch_id=body_epoch_id,
        graph_fingerprint=graph_fingerprint,
        top_k=top_k,
        limit=limit,
    )
    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": "8.2.2",
        "repo": repo,
        "suite": suite,
        "freeze_id": freeze_id,
        "corpus_hash": corpus_hash,
        "body_epoch_id": body_epoch_id,
        "graph_fingerprint": graph_fingerprint,
        "trial_context_hash": trial_context_hash,
        "case_count": len(rows),
        "top_k": int(top_k),
        "arms": arm_metrics,
        "promotion": promotion,
        "latency_ms": {
            "graph_refresh": round(graph_ms, 6),
            "query_p95": round(p95_query, 6),
            "trial_overhead_p95": round(p95_trial, 6),
        },
        "rows": rows,
        "live_results_unchanged": True,
        "policy_effect": False,
        "claim_boundary": CLAIM,
    }
    if persist:
        store.set_setting(f"bridge_trial_latest:{repo}", report)
        log_dir = Path(home) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / f"bridge-trial-{repo}-{int(time.time())}.json"
        import json

        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        report["report_path"] = str(path)
    return report


__all__ = [
    "CLAIM",
    "GLYPH",
    "SCHEMA",
    "evaluate_bridge_trial_promotion",
    "query_conditioned_bridge_trial",
    "run_bridge_trial_suite",
    "structural_trial_context_hash",
]
