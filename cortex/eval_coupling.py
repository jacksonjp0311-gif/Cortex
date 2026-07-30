"""Measure gate — fixed corpus + ablations for coupling/learning claims.

v6.15: Prove whether spectral/ranker/fusion-era path lifts retrieval vs ablations.
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

SCHEMA = "cortex-eval-coupling/1.0"
GLYPH = "⌖⧉"

# Frozen built-in corpus (engine self-paths). Cases use path *substrings*.
DEFAULT_CORPUS: list[dict[str, Any]] = [
    {
        "id": "coherence_field",
        "query": "system coherence emergent coupling indicators threshold",
        "expected_substrings": ["cortex/coherence.py", "coherence"],
    },
    {
        "id": "fusion_coprocess",
        "query": "fusion co-process fuse tick regenerate geometry mind_hash",
        "expected_substrings": ["cortex/coprocess.py", "fuse_proxy", "coprocess"],
    },
    {
        "id": "spectral_math",
        "query": "spectral laplacian heat kernel lambda2 operator graph",
        "expected_substrings": ["math_net/spectral", "math_net/operator", "spectral"],
    },
    {
        "id": "emergence_log",
        "query": "emergence log must read progress coupling events",
        "expected_substrings": ["emergence_log", "cortex/emergence"],
    },
    {
        "id": "ranker_primary",
        "query": "ranker primary features ppr heat unified confidence",
        "expected_substrings": ["cortex/ranker", "ranker/model"],
    },
]

ABLATIONS: tuple[str, ...] = (
    "baseline",       # spectral enrich + ranker primary
    "no_spectral",    # ranker primary, no diffusion enrich
    "no_ranker",      # raw hybrid query order only
)


def _hit(paths: list[str], expected: list[str]) -> bool:
    paths_n = [p.replace("\\", "/") for p in paths]
    for exp in expected:
        e = exp.replace("\\", "/")
        for p in paths_n:
            if e in p or p.endswith(e) or e in p.split("/")[-1]:
                return True
    return False


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

    paths = [str(getattr(h, "path", "") or "") for h in hits[:top_k]]
    ok = _hit(paths, expected)
    return {
        "id": case.get("id"),
        "mode": mode,
        "hit_at_k": ok,
        "returned_paths": [p.replace("\\", "/") for p in paths],
        "expected_substrings": expected,
    }


def run_eval_coupling(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    corpus: list[dict[str, Any]] | None = None,
    limit: int = 12,
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
    cases = corpus or list(DEFAULT_CORPUS)
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
        by_mode[mode] = {
            "cases": len(results),
            "hits_at_k": hits,
            "recall_at_k": round(recall, 6),
            "results": results,
        }

    # Winner: highest recall; tie-break baseline
    ranked_modes = sorted(
        by_mode.items(),
        key=lambda kv: (kv[1]["recall_at_k"], 1 if kv[0] == "baseline" else 0),
        reverse=True,
    )
    winner = ranked_modes[0][0] if ranked_modes else "baseline"
    baseline_r = float((by_mode.get("baseline") or {}).get("recall_at_k") or 0.0)
    lifts = {
        mode: round(float(data["recall_at_k"]) - baseline_r, 6)
        for mode, data in by_mode.items()
        if mode != "baseline"
    }
    # Positive lift for baseline means baseline beats ablation (good)
    baseline_beats = {
        mode: baseline_r >= float(data["recall_at_k"])
        for mode, data in by_mode.items()
        if mode != "baseline"
    }
    spectral_helps = baseline_r > float(
        (by_mode.get("no_spectral") or {}).get("recall_at_k") or 0.0
    )
    ranker_helps = baseline_r > float(
        (by_mode.get("no_ranker") or {}).get("recall_at_k") or 0.0
    )

    prog("coherence_after")
    coh_after = measure_coherence(
        store, repo, governor=governor, home=home, retrieval_confidence=0.55
    )
    ranker_after = ranker_status(store, repo)

    gate = {
        "keep_spectral_features": spectral_helps or baseline_r == float(
            (by_mode.get("no_spectral") or {}).get("recall_at_k") or 0.0
        ),
        "keep_ranker_primary": ranker_helps or baseline_r == float(
            (by_mode.get("no_ranker") or {}).get("recall_at_k") or 0.0
        ),
        "baseline_is_winner": winner == "baseline",
        "promote_calibration": bool(
            coh_after.get("emergent_coupling") and winner == "baseline"
        ),
    }
    # "helps" true if baseline strictly better; "keep" if not worse
    gate["spectral_helps"] = spectral_helps
    gate["ranker_helps"] = ranker_helps
    gate["keep_spectral_features"] = baseline_r >= float(
        (by_mode.get("no_spectral") or {}).get("recall_at_k") or 0.0
    )
    gate["keep_ranker_primary"] = baseline_r >= float(
        (by_mode.get("no_ranker") or {}).get("recall_at_k") or 0.0
    )

    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "elapsed_s": round(time.time() - t0, 3),
        "top_k": top_k,
        "limit": limit,
        "corpus_ids": [c.get("id") for c in cases],
        "ablations": by_mode,
        "winner": winner,
        "lifts_vs_baseline": lifts,
        "baseline_beats_ablation": baseline_beats,
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
            "Measure gate: path-substring recall under ablations only. "
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
                    f"eval-coupling winner={winner} baseline_recall={baseline_r} "
                    f"spectral_helps={gate.get('spectral_helps')} "
                    f"ranker_helps={gate.get('ranker_helps')} "
                    f"coh={coh_after.get('score')} emergent={coh_after.get('emergent_coupling')}"
                ),
                payload={
                    "winner": winner,
                    "baseline_recall": baseline_r,
                    "gate": gate,
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
        rec.append("spectral_enrichment_helps_recall")
    if gate.get("ranker_helps"):
        rec.append("ranker_primary_helps_recall")
    if winner != "baseline":
        rec.append(f"investigate_why_{winner}_beat_baseline")
    rec.append("hold_course_if_emergent_coupling_unless_ablation_regresses")
    rec.append(
        f"baseline_recall_at_k={baseline_r}; "
        f"no_spectral={ (by_mode.get('no_spectral') or {}).get('recall_at_k') }; "
        f"no_ranker={ (by_mode.get('no_ranker') or {}).get('recall_at_k') }"
    )
    return rec
