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

# Stress suite: distractors + multi-concept / wrong-neighbor traps (v6.16).
# Leaves the perfect full-suite ceiling so self-org has a gradient again.
STRESS_CORPUS: list[dict[str, Any]] = [
    {
        "id": "not_plasticity_but_rct",
        "query": (
            "do not open neuron plasticity alone; need the RCT experiment arms "
            "comparing hebbian on versus off with opt-in only"
        ),
        "expected_substrings": ["plasticity_rct"],
        "suite": "stress",
    },
    {
        "id": "not_immune_but_u",
        "query": (
            "ignore immune codes; want the unified U scalar confidence inverse "
            "that governor consumes everywhere"
        ),
        "expected_substrings": ["math_net/uncertainty", "uncertainty.py"],
        "suite": "stress",
    },
    {
        "id": "not_prefetch_but_calibration",
        "query": (
            "not prefetch; shadow profile that maps scores to hit rates and "
            "clamps constitutional drift weights"
        ),
        "expected_substrings": ["math_net/calibration", "calibration.py"],
        "suite": "stress",
    },
    {
        "id": "not_eval_but_info_bits",
        "query": (
            "not evaluation corpus; information budget accounting delta-U per "
            "token promotion_score gate"
        ),
        "expected_substrings": ["info_account"],
        "suite": "stress",
    },
    {
        "id": "not_spectral_mem_but_operator",
        "query": (
            "not spectral_memory pulse; the adjacency matrix builder A_ij from "
            "synapse weights and dual reverse edges"
        ),
        "expected_substrings": ["math_net/operator", "operator.py"],
        "suite": "stress",
    },
    {
        "id": "not_coprocess_but_invent",
        "query": (
            "not fuse tick itself; invent new integrate synapses when two nodes "
            "co-fire and no edge exists yet under gates"
        ),
        "expected_substrings": ["structure_invent"],
        "suite": "stress",
    },
    {
        "id": "not_cli_but_emergence",
        "query": (
            "not the argparse surface; the durable MUST-READ progress journal "
            "with couple activations and measure_gate events"
        ),
        "expected_substrings": ["emergence_log"],
        "suite": "stress",
    },
    {
        "id": "not_packet_but_fuse_proxy",
        "query": (
            "not a memory packet json; the HTTP OpenAI-compatible proxy that "
            "forwards chat completions and auto fuse_ticks on SSE deltas"
        ),
        "expected_substrings": ["fuse_proxy"],
        "suite": "stress",
    },
]

# Train split: may feed self-org ranker warm / invent seeds (v6.18).
TRAIN_CORPUS: list[dict[str, Any]] = [
    {**c, "split": "train"} for c in (EASY_CORPUS + HARD_CORPUS[:5])
]

# Freeze id — bump when this list intentionally changes (v6.20 utility law).
HOLDOUT_FREEZE_ID = "holdout-v1-2026-07-30"

# Sealed holdout: never used for ranker warm or concept-route construction.
# Distinct phrasing from HARD/STRESS train material.
# DO NOT edit without bumping HOLDOUT_FREEZE_ID and CHANGELOG.
HOLDOUT_CORPUS: list[dict[str, Any]] = [
    {
        "id": "holdout_u_scalar",
        "query": (
            "where is the single uncertainty number built for the whole organism "
            "so certainty never gets inflated against immune stress"
        ),
        "expected_substrings": ["math_net/uncertainty", "uncertainty.py"],
        "suite": "holdout",
        "split": "holdout",
    },
    {
        "id": "holdout_adjacency_builder",
        "query": (
            "module that assembles the weighted undirected adjacency from synapse "
            "mass for spectral operators"
        ),
        "expected_substrings": ["math_net/operator", "operator.py"],
        "suite": "holdout",
        "split": "holdout",
    },
    {
        "id": "holdout_proxy_sse",
        "query": (
            "local http front that streams chat completions and fires geometry "
            "regen on each content delta"
        ),
        "expected_substrings": ["fuse_proxy"],
        "suite": "holdout",
        "split": "holdout",
    },
    {
        "id": "holdout_progress_journal",
        "query": (
            "append-only agent progress journal that must be read before work "
            "with couple activation history"
        ),
        "expected_substrings": ["emergence_log"],
        "suite": "holdout",
        "split": "holdout",
    },
    {
        "id": "holdout_cofire_edges",
        "query": (
            "gated creation of weak integrate synapses when two neural nodes "
            "fire together and lack an edge"
        ),
        "expected_substrings": ["structure_invent"],
        "suite": "holdout",
        "split": "holdout",
    },
    {
        "id": "holdout_shadow_weights",
        "query": (
            "online shadow profile nudging constitutional and governor weights "
            "from outcome rewards without live promotion"
        ),
        "expected_substrings": ["math_net/calibration", "calibration.py"],
        "suite": "holdout",
        "split": "holdout",
    },
    {
        "id": "holdout_info_budget",
        "query": (
            "delta uncertainty per log-token budget and promotion score product "
            "for information accounting"
        ),
        "expected_substrings": ["info_account"],
        "suite": "holdout",
        "split": "holdout",
    },
    {
        "id": "holdout_mesh_observe",
        "query": (
            "pulse that lists every attached repository with role coherence and "
            "ranker trains without merging identities"
        ),
        "expected_substrings": ["host_mesh"],
        "suite": "holdout",
        "split": "holdout",
    },
]

# Development transfer suite (v6.25): formerly overclaimed as sealed foreign proof.
# Vocabulary/paths are encoded in concept routes and foreign_emerge warm procedures.
# Use witness.run for sealed independent evaluation. Never train primary body ranker.
FOREIGN_TRANSFER_CORPUS: list[dict[str, Any]] = [
    {
        "id": "foreign_policy_impl",
        "query": "policy.rs enforcement rules for the governor engine",
        "expected_substrings": ["policy.rs", "src/policy"],
        "suite": "development_transfer",
        "split": "development_transfer",
    },
    {
        "id": "foreign_policy_tests",
        "query": "policy_tests.rs verify policy boundaries",
        "expected_substrings": ["policy_tests", "tests/policy"],
        "suite": "development_transfer",
        "split": "development_transfer",
    },
    {
        "id": "foreign_storage",
        "query": "storage.rs persistence for decisions and state",
        "expected_substrings": ["storage.rs", "src/storage"],
        "suite": "development_transfer",
        "split": "development_transfer",
    },
    {
        "id": "foreign_entry",
        "query": "main.rs application entrypoint wiring",
        "expected_substrings": ["main.rs", "src/main"],
        "suite": "development_transfer",
        "split": "development_transfer",
    },
    {
        "id": "foreign_server",
        "query": "server.rs http request handling",
        "expected_substrings": ["server.rs", "src/server"],
        "suite": "development_transfer",
        "split": "development_transfer",
    },
    {
        "id": "foreign_readme",
        "query": "README.md project overview for this governor",
        "expected_substrings": ["README"],
        "suite": "development_transfer",
        "split": "development_transfer",
    },
]
# Back-compat alias
DEVELOPMENT_TRANSFER_CORPUS = FOREIGN_TRANSFER_CORPUS

# Back-compat alias
DEFAULT_CORPUS = EASY_CORPUS

SUITES: dict[str, list[dict[str, Any]]] = {
    "easy": EASY_CORPUS,
    "hard": HARD_CORPUS,
    "full": EASY_CORPUS + HARD_CORPUS,
    "stress": STRESS_CORPUS,
    "train": TRAIN_CORPUS,
    "holdout": HOLDOUT_CORPUS,
    "foreign": FOREIGN_TRANSFER_CORPUS,
    "all": EASY_CORPUS + HARD_CORPUS + STRESS_CORPUS + HOLDOUT_CORPUS,
}

ABLATIONS: tuple[str, ...] = (
    "baseline",  # ADVANCED path: spectral + ranker primary + geometry residual
    "no_spectral",  # ranker primary, no diffusion enrich / residual
    "no_ranker",  # raw hybrid (still may include concept routes)
    # v6.24 Memory Simplex trusted controller — no ranker, spectral, or concept routes
    "evidence_baseline",
)


def resolve_corpus(suite: str | None = None) -> list[dict[str, Any]]:
    key = (suite or "full").strip().lower()
    if key not in SUITES:
        raise ValueError(
            f"Unknown suite {suite!r}; "
            "choose easy|hard|full|stress|train|holdout|foreign|all"
        )
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
    # Ablations start from hybrid; concept routes only when not evidence_baseline.
    if mode == "evidence_baseline":
        hits = query(
            store,
            repo,
            q,
            limit=limit,
            ranker_primary=False,
            enrich_spectral=False,
            concept_routes=False,
            memory_controller="evidence_baseline",
        )
    else:
        # Raw hybrid only — query() ranker path is off so ablations are honest.
        # Concept routes remain for advanced / no_spectral / no_ranker (IR table).
        hits = query(
            store,
            repo,
            q,
            limit=limit,
            ranker_primary=False,
            concept_routes=True,
        )
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
    elif mode in {"no_ranker", "evidence_baseline"}:
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
    ebase_r = float((by_mode.get("evidence_baseline") or {}).get("recall_at_k") or 0.0)
    ebase_mrr = float((by_mode.get("evidence_baseline") or {}).get("mrr") or 0.0)

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
    # Memory Simplex: advanced (eval "baseline") vs trusted evidence_baseline
    advanced_beats_trusted = (baseline_r, baseline_mrr) >= (ebase_r, ebase_mrr)

    # Ceiling tolerance: when all modes hit@k=1.0, tiny MRR noise must not
    # trigger REVIEW — no hit-rate regression is enough to KEEP.
    ceiling = (
        baseline_r >= 0.999
        and no_spec_r >= 0.999
        and no_rank_r >= 0.999
        and (ebase_r >= 0.999 or "evidence_baseline" not in by_mode)
    )
    mrr_eps = 0.05
    keep_spectral = (baseline_r > no_spec_r) or (
        baseline_r >= no_spec_r and baseline_mrr + mrr_eps >= no_spec_mrr
    )
    keep_ranker = (baseline_r > no_rank_r) or (
        baseline_r >= no_rank_r and baseline_mrr + mrr_eps >= no_rank_mrr
    )
    if ceiling:
        keep_spectral = True
        keep_ranker = True
        # Policy stability only — do NOT force winner for promotion (v6.18).
        winner_for_policy = "baseline"
    else:
        winner_for_policy = winner

    try:
        from .memory_simplex import simplex_lift_report

        simplex = simplex_lift_report(
            by_mode.get("baseline"), by_mode.get("evidence_baseline")
        )
    except Exception as exc:
        simplex = {
            "error": f"{type(exc).__name__}: {exc}",
            "advanced_beats_trusted": advanced_beats_trusted,
        }

    prog("coherence_after")
    coh_after = measure_coherence(
        store, repo, governor=governor, home=home, retrieval_confidence=0.55
    )
    ranker_after = ranker_status(store, repo)

    # Promotion requires true baseline win without perfect-ceiling force, and
    # non-ceiling suites preferred for utility claims (holdout/train).
    suite_name = (suite or "full").strip().lower()
    promote_ok = (
        winner == "baseline"
        and not ceiling
        and bool(coh_after.get("emergent_coupling"))
        and suite_name in {"holdout", "train", "hard", "stress", "full"}
    )
    # Holdout suite is the sealed utility exam.
    if suite_name == "holdout":
        promote_ok = (
            winner == "baseline"
            and bool(coh_after.get("emergent_coupling"))
            and baseline_r >= 0.5
        )

    gate = {
        "baseline_is_winner": winner == "baseline",
        "promote_calibration": promote_ok,
        "spectral_helps": spectral_helps,
        "ranker_helps": ranker_helps,
        "keep_spectral_features": keep_spectral,
        "keep_ranker_primary": keep_ranker,
        "perfect_recall_ceiling": ceiling,
        "winner_for_policy": winner_for_policy,
        "advanced_beats_evidence_baseline": advanced_beats_trusted,
        "eval_split": (
            "holdout"
            if suite_name == "holdout"
            else ("train" if suite_name == "train" else "mixed")
        ),
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

    from .promote_gate import HOLDOUT_FREEZE_ID as _HO_FREEZE

    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "suite": suite if corpus is None else "custom",
        "holdout_freeze_id": _HO_FREEZE if (suite or "") == "holdout" else None,
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
        "memory_simplex": simplex,
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
            "memory_simplex compares advanced path vs EVIDENCE_BASELINE trusted controller. "
            "Not universal answer quality. Not consciousness. Directs evolution."
        ),
    }

    if persist:
        try:
            if report.get("suite") == "holdout" and report.get("holdout_freeze_id"):
                from .causal import record_matched_evaluation

                def utility_metrics(mode: str) -> dict[str, Any]:
                    data = by_mode.get(mode) or {}
                    return {
                        key: data.get(key)
                        for key in ("cases", "hits_at_k", "recall_at_k", "mrr")
                    }

                report["causal_utility"] = {
                    "ranker_primary": record_matched_evaluation(
                        store,
                        repo,
                        suite="holdout",
                        freeze_id=str(report["holdout_freeze_id"]),
                        treatment_name="ranker_primary",
                        control_name="no_ranker",
                        treatment_metrics=utility_metrics("baseline"),
                        control_metrics=utility_metrics("no_ranker"),
                    ),
                    "spectral_enrichment": record_matched_evaluation(
                        store,
                        repo,
                        suite="holdout",
                        freeze_id=str(report["holdout_freeze_id"]),
                        treatment_name="spectral_enrichment",
                        control_name="no_spectral",
                        treatment_metrics=utility_metrics("baseline"),
                        control_metrics=utility_metrics("no_spectral"),
                    ),
                }
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
    if gate.get("advanced_beats_evidence_baseline"):
        rec.append("advanced_beats_EVIDENCE_BASELINE_simplex_ok")
    elif "evidence_baseline" in by_mode:
        rec.append("REVIEW_advanced_loses_to_EVIDENCE_BASELINE")
    if winner != "baseline":
        rec.append(f"investigate_why_{winner}_beat_baseline")
    rec.append("hold_course_if_emergent_coupling_unless_ablation_regresses")
    base = by_mode.get("baseline") or {}
    rec.append(
        f"baseline_recall_at_k={baseline_r} mrr={base.get('mrr')}; "
        f"no_spectral={ (by_mode.get('no_spectral') or {}).get('recall_at_k') }/"
        f"{(by_mode.get('no_spectral') or {}).get('mrr')}; "
        f"no_ranker={ (by_mode.get('no_ranker') or {}).get('recall_at_k') }/"
        f"{(by_mode.get('no_ranker') or {}).get('mrr')}; "
        f"evidence_baseline="
        f"{(by_mode.get('evidence_baseline') or {}).get('recall_at_k')}/"
        f"{(by_mode.get('evidence_baseline') or {}).get('mrr')}"
    )
    # Misses under baseline — next teach/index targets
    misses = [r["id"] for r in (base.get("results") or []) if not r.get("hit_at_k")]
    if misses:
        rec.append("misses_under_baseline=" + ",".join(str(x) for x in misses[:10]))
    return rec
