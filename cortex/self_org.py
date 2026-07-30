"""Self-organization / alignment pulse — listen to emergence + measure gate.

Bounded, recommend-only. Does NOT mutate host source.
Does NOT claim consciousness.

When the body is emergent + measure-gated, this pulse:
  1. Re-reads emergence directives (MUST)
  2. Re-runs measure gate (full or stress if ceiling)
  3. Warms ranker from verified hit paths (small SGD)
  4. Observes shadow calibration if gate promotes
  5. Invents weak coactivation edges among top hit nodes (structure invent)
  6. Optional fuse tick if session open (continuity, not thrash)
  7. Seals remember + emergence milestone

Never auto-prunes. Never full continuum on large graphs.
"""

from __future__ import annotations

import time
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .coherence import measure_coherence
from .emergence_log import log_milestone, read_emergence_log
from .eval_coupling import run_eval_coupling
from .ranker.model import (
    features_from_hit,
    ranker_status,
    train_from_outcome,
)

SCHEMA = "cortex-self-org/1.0"
GLYPH = "⧉⟳"


def _gov_mode(governor: Any, store: Any, repo: str) -> str:
    """Fail closed: authority unavailable → read_only (never default normal)."""
    try:
        env = governor.evaluate(repo, retrieval_confidence=0.55)
        mode = str(env.get("mode") or "").strip()
        if mode in {"normal", "constrained", "read_only"}:
            return mode
        # Unknown mode string — do not invent privileges.
        return "read_only"
    except Exception:
        return "read_only"


def _paths_to_node_ids(store: Any, repo: str, paths: list[str]) -> list[str]:
    """Map file paths to neural node_ids when present."""
    want = {p.replace("\\", "/") for p in paths}
    ids: list[str] = []
    try:
        for row in store.neural_nodes(repo) or []:
            p = str(row["path"] or "").replace("\\", "/")
            if p in want or any(w in p or p.endswith(w.split("/")[-1]) for w in want):
                ids.append(str(row["node_id"]))
    except Exception:
        return []
    # unique preserve order
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out[:24]


def _warm_ranker_from_gate(
    store: Any,
    repo: str,
    gate_report: dict[str, Any],
    *,
    governance_mode: str,
) -> dict[str, Any]:
    """Train ranker on baseline hit paths as verified positives (bounded)."""
    if governance_mode == "read_only":
        return {"trained": False, "reason": "governor_read_only"}
    baseline = (gate_report.get("ablations") or {}).get("baseline") or {}
    results = baseline.get("results") or []
    vectors: list[list[float]] = []
    paths: list[str] = []
    for i, case in enumerate(results):
        if not case.get("hit_at_k"):
            continue
        for j, p in enumerate((case.get("returned_paths") or [])[:3]):
            pn = str(p).replace("\\", "/")
            paths.append(pn)
            vectors.append(
                features_from_hit(
                    {
                        "path": pn,
                        "kind": "source" if pn.endswith(".py") else "documentation",
                        "score": max(0.2, 0.9 - 0.1 * j),
                        "metadata": {
                            "selection_source": "measure_gate_hit",
                            "eval_split": "train",
                        },
                    },
                    rank=j,
                    retrieval_confidence=0.7,
                )
            )
        if len(vectors) >= 24:
            break
    if not vectors:
        return {"trained": False, "reason": "no_hit_vectors", "paths": 0}
    oid = "out_selforg_" + sha256(
        f"{repo}|{gate_report.get('elapsed_s')}|{time.time()}".encode()
    ).hexdigest()[:16]
    res = train_from_outcome(
        store,
        repo,
        outcome_id=oid,
        activation_id="self_org_measure_gate",
        status="verified",
        reward=0.85,
        verification_type="measure_gate_hit_paths",
        governance_mode=governance_mode,
        feature_vectors=vectors[:24],
    )
    res["paths_used"] = len(paths)
    res["vectors"] = len(vectors[:24])
    return res


def run_self_org(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    invent: bool = True,
    fuse_tick: bool = True,
    warm_ranker: bool = True,
    run_stress_if_ceiling: bool = True,
    seal: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """One alignment / self-organization pulse driven by body state."""

    def prog(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    t0 = time.time()
    if not store.repo(repo):
        raise ValueError(f"Unknown repository: {repo}")

    prog("read_emergence")
    emergence_before = read_emergence_log(home, store, repo, limit=8)
    directives = list(emergence_before.get("directives") or [])

    prog("coherence")
    coh_before = measure_coherence(
        store, repo, governor=governor, home=home, retrieval_confidence=0.55
    )
    mode = _gov_mode(governor, store, repo)
    ranker_before = ranker_status(store, repo)

    # ── Measure gate (train / holdout separation — v6.18) ──────────────
    # Train suite: allowed for ranker warm / invent seeds.
    # Holdout suite: sealed; never trains ranker; drives keep/promote decisions.
    prog("measure_gate:train")
    train_report = run_eval_coupling(
        home,
        store,
        governor,
        repo,
        suite="train",
        persist=True,
        on_progress=lambda m: prog(f"train:{m}"),
    )
    prog("measure_gate:holdout (sealed — no ranker train)")
    holdout_report = run_eval_coupling(
        home,
        store,
        governor,
        repo,
        suite="holdout",
        persist=True,
        on_progress=lambda m: prog(f"holdout:{m}"),
    )
    # Optional full for continuity telemetry (not used to train)
    full_report = train_report
    if run_stress_if_ceiling:
        prog("measure_gate:full (telemetry only)")
        full_report = run_eval_coupling(
            home,
            store,
            governor,
            repo,
            suite="full",
            persist=True,
            on_progress=lambda m: prog(f"full:{m}"),
        )
    gate = holdout_report.get("gate") or {}
    ceiling = bool((full_report.get("gate") or {}).get("perfect_recall_ceiling"))
    stress_report = holdout_report  # holdout is the promotion exam
    active_report = train_report  # warm from train only
    active_gate = gate

    # ── Ranker warm (train split only) ─────────────────────────────────
    ranker_train: dict[str, Any] = {"trained": False, "skipped": not warm_ranker}
    if warm_ranker:
        prog("warm_ranker (train split only)")
        ranker_train = _warm_ranker_from_gate(
            store, repo, train_report, governance_mode=mode
        )
        ranker_train["eval_split"] = "train"

    # ── Shadow calibration observe ─────────────────────────────────────
    calibration: dict[str, Any] = {"observed": False}
    # Promote only when holdout utility is real — not perfect-ceiling force-winner.
    holdout_recall = float(
        ((holdout_report.get("ablations") or {}).get("baseline") or {}).get(
            "recall_at_k"
        )
        or 0.0
    )
    may_promote = bool(active_gate.get("promote_calibration")) and holdout_recall >= 0.5
    if may_promote and mode != "read_only":
        prog("calibration_shadow (holdout-gated)")
        try:
            from .math_net.calibration import observe_outcome_for_calibration

            calibration = {
                "observed": True,
                "shadow": observe_outcome_for_calibration(
                    store,
                    repo,
                    reward=0.8,
                    features={
                        "confidence": 0.75,
                        "gov_confidence": 0.7,
                        "gov_continuity": 0.8,
                        "integrity": 0.85,
                    },
                ),
                "note": "shadow only — not live Governor replacement; holdout-gated",
                "holdout_recall": holdout_recall,
            }
        except Exception as exc:
            calibration = {
                "observed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
    else:
        calibration = {
            "observed": False,
            "skipped": True,
            "reason": "holdout_or_gate_blocked_promote",
            "holdout_recall": holdout_recall,
        }

    # ── Structure invent (self-org topology, not host files) ───────────
    invent_result: dict[str, Any] = {"invented": 0, "skipped": not invent}
    if invent and mode != "read_only":
        prog("structure_invent")
        try:
            from .structure_invent import invent_from_coactivation

            hit_paths: list[str] = []
            base = (active_report.get("ablations") or {}).get("baseline") or {}
            for case in base.get("results") or []:
                if case.get("hit_at_k"):
                    hit_paths.extend((case.get("returned_paths") or [])[:2])
            node_ids = _paths_to_node_ids(store, repo, hit_paths[:16])
            invent_result = invent_from_coactivation(
                store,
                repo,
                fired_node_ids=node_ids,
                governance_mode=mode,
                max_new=6,
                base_weight=0.10,
            )
            invent_result["seed_nodes"] = len(node_ids)
        except Exception as exc:
            invent_result = {
                "invented": 0,
                "error": f"{type(exc).__name__}: {exc}",
            }

    # ── Fuse continuity (tick if open; never thrash close) ─────────────
    fuse: dict[str, Any] = {"ticked": False}
    if fuse_tick:
        prog("fuse_continuity")
        try:
            from .coprocess import fuse_state, fuse_tick as do_tick

            st = fuse_state(store, repo)
            if st.get("open"):
                fuse = {
                    "ticked": True,
                    "tick": do_tick(
                        store,
                        governor,
                        repo,
                        token="self_org_align_pulse",
                        measure_coherence_every=99,
                    ),
                }
            else:
                fuse = {
                    "ticked": False,
                    "reason": "fuse_not_open",
                    "advice": "leave closed or open explicitly — no thrash",
                }
        except Exception as exc:
            fuse = {"ticked": False, "error": f"{type(exc).__name__}: {exc}"}

    # ── Coherence after ────────────────────────────────────────────────
    prog("coherence_after")
    coh_after = measure_coherence(
        store, repo, governor=governor, home=home, retrieval_confidence=0.55
    )
    ranker_after = ranker_status(store, repo)

    # ── Seal ───────────────────────────────────────────────────────────
    seal_note: dict[str, Any] = {"sealed": False}
    summary = (
        f"self-org align: train_recall="
        f"{(train_report.get('ablations') or {}).get('baseline', {}).get('recall_at_k')} "
        f"holdout_recall="
        f"{(holdout_report.get('ablations') or {}).get('baseline', {}).get('recall_at_k')} "
        f"ranker_trained={ranker_train.get('trained')} "
        f"invented={invent_result.get('invented')} "
        f"fuse_tick={fuse.get('ticked')} "
        f"gov={mode} "
        f"coh={coh_after.get('score')} emergent={coh_after.get('emergent_coupling')}"
    )
    if seal:
        prog("seal")
        try:
            from .hippocampus import remember
            from .session_ritual import run_session_ritual

            try:
                remember(
                    home,
                    store,
                    repo,
                    kind="outcome",
                    text=summary,
                )
            except TypeError:
                # alternate signature variants
                try:
                    remember(store, repo, kind="outcome", text=summary)
                except Exception:
                    pass
            ritual = run_session_ritual(
                home,
                store,
                governor,
                repo,
                "Self-org alignment pulse — listen to emergence",
                memories=[
                    {
                        "kind": "outcome",
                        "text": summary,
                    },
                    {
                        "kind": "invariant",
                        "text": (
                            "Self-org is gate-driven co-activation + ranker warm + "
                            "weak invented edges. Not consciousness. Not host mutation."
                        ),
                    },
                ],
                consolidate_session=True,
                profile="agent",
                force=True,
            )
            seal_note = {
                "sealed": True,
                "phase": (ritual.get("cardiac_cycle") or {}).get("sealed")
                or ritual.get("phase"),
            }
        except Exception as exc:
            seal_note = {
                "sealed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }

    log_milestone(
        home,
        store,
        repo,
        kind="self_org",
        summary=summary,
        payload={
            "gate_full": gate,
            "gate_active": active_gate,
            "ranker_train": {
                k: ranker_train.get(k)
                for k in ("trained", "reason", "train_count", "paths_used", "vectors")
            },
            "invented": invent_result.get("invented"),
            "fuse_ticked": fuse.get("ticked"),
            "ceiling": ceiling,
        },
        source="self_org",
    )

    emergence_after = read_emergence_log(home, store, repo, limit=6)

    report = {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "version": __version__,
        "repo": repo,
        "elapsed_s": round(time.time() - t0, 3),
        "governance_mode": mode,
        "listened": {
            "directives": directives,
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
            "coherence_advice": coh_before.get("advice") or coh_after.get("advice"),
        },
        "measure": {
            "train": {
                "winner": train_report.get("winner"),
                "gate": train_report.get("gate"),
                "baseline_recall": (train_report.get("ablations") or {})
                .get("baseline", {})
                .get("recall_at_k"),
                "baseline_mrr": (train_report.get("ablations") or {})
                .get("baseline", {})
                .get("mrr"),
                "split": "train",
            },
            "holdout": {
                "winner": holdout_report.get("winner"),
                "gate": holdout_report.get("gate"),
                "baseline_recall": (holdout_report.get("ablations") or {})
                .get("baseline", {})
                .get("recall_at_k"),
                "baseline_mrr": (holdout_report.get("ablations") or {})
                .get("baseline", {})
                .get("mrr"),
                "split": "holdout",
                "misses": [
                    r["id"]
                    for r in (
                        (holdout_report.get("ablations") or {})
                        .get("baseline", {})
                        .get("results")
                        or []
                    )
                    if not r.get("hit_at_k")
                ],
            },
            "full": {
                "winner": full_report.get("winner"),
                "gate": full_report.get("gate"),
                "baseline_recall": (full_report.get("ablations") or {})
                .get("baseline", {})
                .get("recall_at_k"),
                "split": "telemetry",
            },
            "train_holdout_separated": True,
            "ceiling_on_full": ceiling,
        },
        "self_organization": {
            "ranker": ranker_train,
            "ranker_train_before": ranker_before.get("train_count"),
            "ranker_train_after": ranker_after.get("train_count"),
            "calibration": calibration,
            "structure_invent": invent_result,
            "fuse": {
                "ticked": fuse.get("ticked"),
                "reason": fuse.get("reason"),
                "error": fuse.get("error"),
            },
            "seal": seal_note,
        },
        "held_course": {
            "spectral_kept": bool(
                active_gate.get("keep_spectral_features")
                or gate.get("keep_spectral_features")
            ),
            "ranker_kept": bool(
                active_gate.get("keep_ranker_primary") or gate.get("keep_ranker_primary")
            ),
            "no_prune": True,
            "no_full_continuum": True,
            "recommend_only": True,
        },
        "next": _next_moves(active_report, stress_report, ceiling, ranker_after),
        "emergence_log": emergence_after,
        "claim_boundary": (
            "Self-org pulse is gate-driven alignment of memory geometry and ranker. "
            "Not consciousness. Not host mutation authority. Not auto-ARIA."
        ),
    }
    try:
        store.set_setting(f"self_org_latest:{repo}", report)
    except Exception:
        pass
    prog("done")
    return report


def _next_moves(
    active: dict[str, Any],
    stress: dict[str, Any] | None,
    ceiling: bool,
    ranker: dict[str, Any],
) -> list[str]:
    moves: list[str] = []
    if stress:
        misses = [
            r["id"]
            for r in (
                (stress.get("ablations") or {}).get("baseline", {}).get("results") or []
            )
            if not r.get("hit_at_k")
        ]
        if misses:
            moves.append("expand_concept_routes_or_docs_for=" + ",".join(misses[:8]))
        else:
            moves.append("stress_suite_clear_raise_difficulty_again")
    elif ceiling:
        moves.append("full_suite_at_ceiling_use_stress_or_foreign_host")
    moves.append(
        f"keep_warming_ranker_trains={ranker.get('train_count')} "
        "(use real tasks + verified outcomes)"
    )
    moves.append("prefer_fuse_ticks_over_continuum_on_large_graphs")
    moves.append("dual_align_and_prune_hygiene_still_dark_unless_needed")
    return moves
