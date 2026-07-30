"""Measure gate — fixed corpus + ablations for coupling/learning claims.

v6.15: Prove whether spectral/ranker/fusion-era path lifts retrieval vs ablations.
v6.15.1: Hard paraphrase suite + MRR so ablations can diverge (not only hit@k ceiling).
Recommend-only; does not mutate host source.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .coherence import measure_coherence
from .emergence_log import log_milestone, read_emergence_log
from .ranker.model import ranker_status, rerank_hits
from .retrieval import query

SCHEMA = "cortex-eval-coupling/1.1"
GLYPH = "⌖⧉"

# Frozen built-in corpus (engine self-paths). Cases use path *substrings*.
# Easy suite: keyword-rich queries (path boost often solves these).
EASY_CORPUS: list[dict[str, Any]] = [
    {
        "id": "coherence_field",
        "query": "system coherence emergent coupling indicators threshold",
        "expected_substrings": ["cortex/coherence.py", "coherence"],
        "suite": "easy",
    },
    {
        "id": "fusion_coprocess",
        "query": "fusion co-process fuse tick regenerate geometry mind_hash",
        "expected_substrings": ["cortex/coprocess.py", "fuse_proxy", "coprocess"],
        "suite": "easy",
    },
    {
        "id": "spectral_math",
        "query": "spectral laplacian heat kernel lambda2 operator graph",
        "expected_substrings": ["math_net/spectral", "math_net/operator", "spectral"],
        "suite": "easy",
    },
    {
        "id": "emergence_log",
        "query": "emergence log must read progress coupling events",
        "expected_substrings": ["emergence_log", "cortex/emergence"],
        "suite": "easy",
    },
    {
        "id": "ranker_primary",
        "query": "ranker primary features ppr heat unified confidence",
        "expected_substrings": ["cortex/ranker", "ranker/model"],
        "suite": "easy",
    },
]

# Hard suite: paraphrases that avoid naming the module; stricter targets.
# Designed so raw hybrid may miss while ranker/spectral reorder into top-k.
HARD_CORPUS: list[dict[str, Any]] = [
    {
        "id": "fuse_proxy_paraphrase",
        "query": (
            "openai compatible chat completions front that auto ticks "
            "geometry on each SSE content delta"
        ),
        "expected_substrings": ["cortex/fuse_proxy.py", "fuse_proxy"],
        "suite": "hard",
    },
    {
        "id": "coherence_paraphrase",
        "query": (
            "multi-seam coactivation score threshold couples blood geometry "
            "spectral learning fusion hygiene"
        ),
        "expected_substrings": ["cortex/coherence.py"],
        "suite": "hard",
    },
    {
        "id": "diffusion_paraphrase",
        "query": (
            "spread activation mass along edges with heat kernel and "
            "pagerank personalization"
        ),
        "expected_substrings": ["math_net/diffusion", "diffusion.py"],
        "suite": "hard",
    },
    {
        "id": "structure_invent_paraphrase",
        "query": (
            "propose new coactivation topology edges from simultaneous path "
            "fire under governor gates"
        ),
        "expected_substrings": ["structure_invent"],
        "suite": "hard",
    },
    {
        "id": "plasticity_rct_paraphrase",
        "query": (
            "randomized controlled trial arm for optional synapse weight "
            "updates only when opted in"
        ),
        "expected_substrings": ["plasticity_rct"],
        "suite": "hard",
    },
    {
        "id": "operator_paraphrase",
        "query": (
            "build graph adjacency operator and dual reverse-edge operator "
            "for spectral work"
        ),
        "expected_substrings": ["math_net/operator", "operator.py"],
        "suite": "hard",
    },
    {
        "id": "uncertainty_paraphrase",
        "query": (
            "single scalar that may only decrease when immune stress rises "
            "never inflate certainty for governor"
        ),
        "expected_substrings": ["math_net/uncertainty", "uncertainty.py"],
        "suite": "hard",
    },
    {
        "id": "calibration_paraphrase",
        "query": (
            "map predicted confidence to observed hit rates and clamp "
            "drift floor after outcomes"
        ),
        "expected_substrings": ["math_net/calibration", "calibration.py"],
        "suite": "hard",
    },
    {
        "id": "info_account_paraphrase",
        "query": (
            "information accounting budget bits spent on retrieval and "
            "learning decisions"
        ),
        "expected_substrings": ["info_account"],
        "suite": "hard",
    },
    {
        "id": "emergence_paraphrase",
        "query": (
            "durable progress journal agents must open first every turn "
            "for couple history"
        ),
        "expected_substrings": ["emergence_log"],
        "suite": "hard",
    },
]

# Back-compat alias
DEFAULT_CORPUS = EASY_CORPUS

SUITES: dict[str, list[dict[str, Any]]] = {
    "easy": EASY_CORPUS,
    "hard": HARD_CORPUS,
    "full": EASY_CORPUS + HARD_CORPUS,
}

ABLATIONS: tuple[str, ...] = (
    "baseline",  # spectral enrich + ranker primary + geometry residual
    "no_spectral",  # ranker primary, no diffusion enrich / residual
    "no_ranker",  # raw hybrid query order only
)


def resolve_corpus(suite: str | None = None) -> list[dict[str, Any]]:
    key = (suite or "full").strip().lower()
    if key not in SUITES:
        raise ValueError(f"Unknown suite {suite!r}; choose easy|hard|full")
    return list(SUITES[key])


def _hit(paths: list[str], expected: list[str]) -> bool:
    return _first_rank(paths, expected) is not None


def _first_rank(paths: list[str], expected: list[str]) -> int | None:
    """1-based rank of first path matching any expected substring, else None."""
    paths_n = [p.replace("\\", "/") for p in paths]
    for i, p in enumerate(paths_n):
        for exp in expected:
            e = exp.replace("\\", "/")
            if e in p or p.endswith(e) or e in p.split("/")[-1]:
                return i + 1
    return None


def _run_case(
    store: Any,
    repo: str,
    case: dict[str, Any],
    *,
    mode: str,
    limit: int,
    top_k: int,
) -> dict[str, Any]:
    q = str(case["query"])
    expected = [str(x) for x in case.get("expected_substrings") or []]
    hits = query(store, repo, q, limit=limit)
    if mode == "baseline":
        hits = rerank_hits(
            store,
            repo,
            hits,
            retrieval_confidence=0.55,
            primary=True,
            enrich_spectral=True,
        )
    elif mode == "no_spectral":
        hits = rerank_hits(
            store,
            repo,
            hits,
            retrieval_confidence=0.55,
            primary=True,
            enrich_spectral=False,
        )
    elif mode == "no_ranker":
        pass
    else:
        raise ValueError(f"unknown ablation mode: {mode}")

    paths = [str(getattr(h, "path", "") or "") for h in hits[: max(top_k, 20)]]
    rank = _first_rank(paths, expected)
    ok = rank is not None and rank <= top_k
    mrr = (1.0 / rank) if rank is not None else 0.0
    return {
        "id": case.get("id"),
        "suite": case.get("suite"),
        "mode": mode,
        "hit_at_k": ok,
        "first_hit_rank": rank,
        "mrr": round(mrr, 6),
        "returned_paths": [p.replace("\\", "/") for p in paths[:top_k]],
        "expected_substrings": expected,
    }


def run_eval_coupling(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    corpus: list[dict[str, Any]] | None = None,
    suite: str = "full",
    limit: int = 16,
    top_k: int = 5,
    ablations: tuple[str, ...] | None = None,
    persist: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Run frozen corpus under ablations; return measure-gate report."""

    def prog(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    t0 = time.time()
    cases = corpus if corpus is not None else resolve_corpus(suite)
    modes = ablations or ABLATIONS
    if not store.repo(repo):
        raise ValueError(f"Unknown repository: {repo}")

    prog("coherence_before")
    coh_before = measure_coherence(
        store, repo, governor=governor, home=home, retrieval_confidence=0.55
    )
    ranker_before = ranker_status(store, repo)

    by_mode: dict[str, Any] = {}
    for mode in modes:
        prog(f"ablation:{mode}")
        results = [
            _run_case(store, repo, case, mode=mode, limit=limit, top_k=top_k)
            for case in cases
        ]
        hits = sum(1 for r in results if r["hit_at_k"])
        n = max(1, len(results))
        recall = hits / n
        mrr_mean = sum(float(r["mrr"]) for r in results) / n
        by_mode[mode] = {
            "cases": len(results),
            "hits_at_k": hits,
            "recall_at_k": round(recall, 6),
            "mrr": round(mrr_mean, 6),
            "results": results,
        }

    # Winner: highest recall, then MRR, then prefer baseline on ties
    ranked_modes = sorted(
        by_mode.items(),
        key=lambda kv: (
            kv[1]["recall_at_k"],
            kv[1]["mrr"],
            1 if kv[0] == "baseline" else 0,
        ),
        reverse=True,
    )
    winner = ranked_modes[0][0] if ranked_modes else "baseline"
    baseline_r = float((by_mode.get("baseline") or {}).get("recall_at_k") or 0.0)
    baseline_mrr = float((by_mode.get("baseline") or {}).get("mrr") or 0.0)
    no_spec_r = float((by_mode.get("no_spectral") or {}).get("recall_at_k") or 0.0)
    no_spec_mrr = float((by_mode.get("no_spectral") or {}).get("mrr") or 0.0)
    no_rank_r = float((by_mode.get("no_ranker") or {}).get("recall_at_k") or 0.0)
    no_rank_mrr = float((by_mode.get("no_ranker") or {}).get("mrr") or 0.0)

    lifts = {
        mode: {
            "recall": round(float(data["recall_at_k"]) - baseline_r, 6),
            "mrr": round(float(data["mrr"]) - baseline_mrr, 6),
        }
        for mode, data in by_mode.items()
        if mode != "baseline"
    }
    baseline_beats = {
        mode: (baseline_r, baseline_mrr)
        >= (
            float(data["recall_at_k"]),
            float(data["mrr"]),
        )
        for mode, data in by_mode.items()
        if mode != "baseline"
    }

    # Strict lift on recall OR on mean reciprocal rank
    spectral_helps = (baseline_r > no_spec_r) or (baseline_mrr > no_spec_mrr + 1e-9)
    ranker_helps = (baseline_r > no_rank_r) or (baseline_mrr > no_rank_mrr + 1e-9)

    prog("coherence_after")
    coh_after = measure_coherence(
        store, repo, governor=governor, home=home, retrieval_confidence=0.55
    )
    ranker_after = ranker_status(store, repo)

    gate = {
        "baseline_is_winner": winner == "baseline",
        "promote_calibration": bool(
            coh_after.get("emergent_coupling") and winner == "baseline"
        ),
        "spectral_helps": spectral_helps,
        "ranker_helps": ranker_helps,
        "keep_spectral_features": (baseline_r, baseline_mrr)
        >= (no_spec_r, no_spec_mrr),
        "keep_ranker_primary": (baseline_r, baseline_mrr)
        >= (no_rank_r, no_rank_mrr),
    }

    # Per-case divergence summary (where modes disagree on hit@k or rank)
    divergence: list[dict[str, Any]] = []
    if by_mode.get("baseline"):
        ids = [r["id"] for r in by_mode["baseline"]["results"]]
        for case_id in ids:
            rows = {
                mode: next(
                    (r for r in data["results"] if r["id"] == case_id),
                    None,
                )
                for mode, data in by_mode.items()
            }
            hits_map = {m: bool(r and r["hit_at_k"]) for m, r in rows.items()}
            ranks = {m: (r or {}).get("first_hit_rank") for m, r in rows.items()}
            if len(set(hits_map.values())) > 1 or len(set(ranks.values())) > 1:
                divergence.append(
                    {
                        "id": case_id,
                        "hit_at_k": hits_map,
                        "first_hit_rank": ranks,
                    }
                )

    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "suite": suite if corpus is None else "custom",
        "elapsed_s": round(time.time() - t0, 3),
        "top_k": top_k,
        "limit": limit,
        "corpus_ids": [c.get("id") for c in cases],
        "ablations": by_mode,
        "winner": winner,
        "lifts_vs_baseline": lifts,
        "baseline_beats_ablation": baseline_beats,
        "divergence_cases": divergence,
        "gate": gate,
        "coherence_before": {
            "score": coh_before.get("score"),
            "emergent_coupling": coh_before.get("emergent_coupling"),
            "active_indicator_ids": coh_before.get("active_indicator_ids"),
        },
        "coherence_after": {
            "score": coh_after.get("score"),
            "emergent_coupling": coh_after.get("emergent_coupling"),
            "active_indicator_ids": coh_after.get("active_indicator_ids"),
        },
        "ranker": {
            "train_before": ranker_before.get("train_count"),
            "train_after": ranker_after.get("train_count"),
        },
        "recommendation": _recommendation(gate, winner, baseline_r, by_mode),
        "claim_boundary": (
            "Measure gate: path-substring recall@k + MRR under ablations only. "
            "Not universal answer quality. Not consciousness. Directs evolution."
        ),
    }

    if persist:
        try:
            store.set_setting(f"eval_coupling_latest:{repo}", report)
            log_dir = Path(home) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            path = log_dir / f"eval-coupling-{repo}-{int(time.time())}.json"
            import json

            path.write_text(
                json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
            )
            report["report_path"] = str(path)
        except Exception as exc:
            report["persist_error"] = f"{type(exc).__name__}: {exc}"
        try:
            log_milestone(
                home,
                store,
                repo,
                kind="measure_gate",
                summary=(
                    f"eval-coupling suite={report.get('suite')} winner={winner} "
                    f"baseline_recall={baseline_r} baseline_mrr={baseline_mrr} "
                    f"spectral_helps={gate.get('spectral_helps')} "
                    f"ranker_helps={gate.get('ranker_helps')} "
                    f"coh={coh_after.get('score')} emergent={coh_after.get('emergent_coupling')}"
                ),
                payload={
                    "winner": winner,
                    "suite": report.get("suite"),
                    "baseline_recall": baseline_r,
                    "baseline_mrr": baseline_mrr,
                    "gate": gate,
                    "divergence_n": len(divergence),
                    "recommendation": report["recommendation"],
                },
                source="eval_coupling",
            )
            report["emergence_log"] = read_emergence_log(home, store, repo, limit=6)
        except Exception as exc:
            report["emergence_error"] = f"{type(exc).__name__}: {exc}"

    prog("done")
    return report


def _recommendation(
    gate: dict[str, Any],
    winner: str,
    baseline_r: float,
    by_mode: dict[str, Any],
) -> list[str]:
    rec: list[str] = []
    if gate.get("baseline_is_winner") and gate.get("keep_spectral_features"):
        rec.append("KEEP_spectral_features_in_ranker")
    elif not gate.get("keep_spectral_features"):
        rec.append("REVIEW_spectral_features_no_lift")
    if gate.get("keep_ranker_primary"):
        rec.append("KEEP_ranker_primary")
    else:
        rec.append("REVIEW_ranker_primary_no_lift")
    if gate.get("spectral_helps"):
        rec.append("spectral_enrichment_helps_recall_or_mrr")
    if gate.get("ranker_helps"):
        rec.append("ranker_primary_helps_recall_or_mrr")
    if winner != "baseline":
        rec.append(f"investigate_why_{winner}_beat_baseline")
    rec.append("hold_course_if_emergent_coupling_unless_ablation_regresses")
    base = by_mode.get("baseline") or {}
    rec.append(
        f"baseline_recall_at_k={baseline_r} mrr={base.get('mrr')}; "
        f"no_spectral={ (by_mode.get('no_spectral') or {}).get('recall_at_k') }/"
        f"{(by_mode.get('no_spectral') or {}).get('mrr')}; "
        f"no_ranker={ (by_mode.get('no_ranker') or {}).get('recall_at_k') }/"
        f"{(by_mode.get('no_ranker') or {}).get('mrr')}"
    )
    # Misses under baseline — next teach/index targets
    misses = [r["id"] for r in (base.get("results") or []) if not r.get("hit_at_k")]
    if misses:
        rec.append("misses_under_baseline=" + ",".join(str(x) for x in misses[:10]))
    return rec
