"""Causal episodes: did memory changes improve future performance?"""

from __future__ import annotations

import json
import time
from hashlib import sha256
from typing import Any

from ..connect_pass import load_metric_graph
from ..ranker.model import ranker_status


def _is_proof_path(path: str, kind: str = "", metadata: dict[str, Any] | None = None) -> bool:
    p = (path or "").replace("\\", "/")
    meta = metadata or {}
    if meta.get("prove_implementation") or meta.get("selection_source") in {
        "implementation_proof",
        "implementation_test_proof",
        "aria_evidence_floor",
        "aria_substrate",
    }:
        return True
    if (
        "/tests/" in p
        or p.startswith("tests/")
        or "/test_" in p
        or p.endswith(("_test.py", ".test.js", ".spec.ts", ".spec.js"))
        or kind == "test"
    ):
        return True
    if (
        p.startswith("cortex/")
        and p.endswith((".py", ".pyi"))
        and "aria_meta/vendor" not in p
    ):
        return True
    return False


def probe_recall(
    store: Any,
    repo: str,
    task: str,
    *,
    k: int = 8,
    materialize_substrate: bool = True,
    slot: str = "before",
) -> dict[str, Any]:
    """Measure a single recall@k snapshot for a matched before/after pair.

    Stores the score on the open causal episode (or opens one). Use twice —
    once before a change (`slot=before`) and once after (`slot=after`) — then
    call evaluate_causal_episode so the verdict is not missing_recall_pair.
    """

    from ..retrieval import query

    hits = query(
        store,
        repo,
        task,
        limit=k,
        materialize_substrate=materialize_substrate,
        prove_implementation=True,
    )
    proof_hits = sum(
        1
        for h in hits
        if _is_proof_path(h.path, h.kind, h.metadata if isinstance(h.metadata, dict) else {})
    )
    card_hits = sum(1 for h in hits if h.kind == "discovery_card")
    vendor_doc_hits = sum(
        1
        for h in hits
        if "aria_meta/vendor" in h.path.replace("\\", "/")
        and (
            "/docs/" in h.path.replace("\\", "/")
            or h.path.replace("\\", "/").endswith(".md")
        )
    )
    score = round(proof_hits / max(1, len(hits) or k), 6)
    opened = store.get_setting(f"causal_open:{repo}", None)
    if not isinstance(opened, dict) or opened.get("closed"):
        open_episode(
            store,
            repo,
            task_family=f"recall_probe:{task[:80]}",
            treatment={"probe_task": task, "k": k},
        )
        opened = store.get_setting(f"causal_open:{repo}", {}) or {}
    key = "recall_before" if slot != "after" else "recall_after"
    metrics_key = "metrics_before" if slot != "after" else "metrics_after_probe"
    opened = dict(opened)
    opened[key] = score
    metrics = dict(opened.get(metrics_key) or {})
    metrics["recall_at_k"] = score
    metrics["probe"] = {
        "task": task,
        "k": k,
        "hits": len(hits),
        "proof_hits": proof_hits,
        "card_hits": card_hits,
        "vendor_doc_hits": vendor_doc_hits,
        "paths": [h.path for h in hits[:k]],
    }
    opened[metrics_key] = metrics
    store.set_setting(f"causal_open:{repo}", opened)
    return {
        "schema_version": "cortex-causal-probe/1.0",
        "repo": repo,
        "slot": "before" if slot != "after" else "after",
        "task": task,
        "k": k,
        "recall_at_k": score,
        "proof_hits": proof_hits,
        "card_hits": card_hits,
        "vendor_doc_hits": vendor_doc_hits,
        "hit_paths": [h.path for h in hits[:k]],
        "episode_id": opened.get("episode_id"),
        "claim_boundary": (
            "Probe measures proof-bearing hit share, not host correctness. "
            "A matched before/after pair is required for causal verdicts."
        ),
    }


def _fingerprint(store: Any, repo: str) -> str:
    graph = load_metric_graph(store, repo)
    ranker = ranker_status(store, repo)
    nodes = store.db.execute(
        "SELECT COUNT(*) AS c FROM neural_nodes WHERE repo=?", (repo,)
    ).fetchone()["c"]
    synapses = store.db.execute(
        "SELECT COUNT(*) AS c FROM neural_synapses WHERE repo=?", (repo,)
    ).fetchone()["c"]
    material = {
        "pass_count": graph.get("pass_count"),
        "averages": graph.get("averages"),
        "ranker_train": ranker.get("train_count"),
        "nodes": nodes,
        "synapses": synapses,
    }
    return sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def open_episode(
    store: Any,
    repo: str,
    task_family: str,
    *,
    treatment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    episode_id = "ep_" + sha256(
        f"{repo}|{task_family}|{time.time()}".encode()
    ).hexdigest()[:20]
    baseline = _fingerprint(store, repo)
    metrics_before = {
        "metric_graph": load_metric_graph(store, repo).get("averages") or {},
        "ranker_train_count": ranker_status(store, repo).get("train_count"),
    }
    store.set_setting(
        f"causal_open:{repo}",
        {
            "episode_id": episode_id,
            "task_family": task_family,
            "baseline": baseline,
            "metrics_before": metrics_before,
            "treatment": treatment or {},
            "opened_at": time.time(),
        },
    )
    return {
        "opened": True,
        "episode_id": episode_id,
        "baseline_fingerprint": baseline,
        "claim_boundary": "Causal episode tracks memory effects; not host rights.",
    }


def evaluate_causal_episode(
    store: Any,
    repo: str,
    *,
    metrics_after: dict[str, Any] | None = None,
    recall_before: float | None = None,
    recall_after: float | None = None,
) -> dict[str, Any]:
    opened = store.get_setting(f"causal_open:{repo}", None)
    if not isinstance(opened, dict):
        # Auto-open a synthetic episode
        opened = open_episode(store, repo, "ad_hoc")
        opened = store.get_setting(f"causal_open:{repo}", opened)

    metrics_before = dict(opened.get("metrics_before") or {})
    after = metrics_after or {
        "metric_graph": load_metric_graph(store, repo).get("averages") or {},
        "ranker_train_count": ranker_status(store, repo).get("train_count"),
    }
    after = dict(after)
    # Prefer explicit CLI floats, then probe slots stored on the open episode.
    if recall_before is None and opened.get("recall_before") is not None:
        recall_before = float(opened["recall_before"])
    if recall_after is None and opened.get("recall_after") is not None:
        recall_after = float(opened["recall_after"])
    probe_after = opened.get("metrics_after_probe") or {}
    if recall_after is None and probe_after.get("recall_at_k") is not None:
        recall_after = float(probe_after["recall_at_k"])
    if recall_before is not None:
        metrics_before = {**metrics_before, "recall_at_k": recall_before}
    if recall_after is not None:
        after = {**after, "recall_at_k": recall_after}

    delta: dict[str, Any] = {}
    confounds: list[str] = []
    rb = metrics_before.get("recall_at_k")
    ra = after.get("recall_at_k")
    if rb is not None and ra is not None:
        delta["recall_at_k"] = round(float(ra) - float(rb), 6)
    else:
        confounds.append("missing_recall_pair")
        confounds.append(
            "hint:run_causal_probe_before_and_after — "
            "python -m cortex causal probe --repo REPO --task \"...\" "
            "then probe again with --slot after, then evaluate"
        )

    bb = (metrics_before.get("metric_graph") or {}).get("block_rate")
    ba = (after.get("metric_graph") or {}).get("block_rate")
    if bb is not None and ba is not None:
        delta["block_rate"] = round(float(ba) - float(bb), 6)

    verdict = "inconclusive"
    if "recall_at_k" in delta:
        if delta["recall_at_k"] > 0.02:
            verdict = "improved"
        elif delta["recall_at_k"] < -0.02:
            verdict = "regressed"
        else:
            verdict = "inconclusive"
            confounds.append("effect_below_threshold")

    episode_id = opened.get("episode_id") or "ep_unknown"
    now = time.time()
    store.db.execute(
        """
        INSERT OR REPLACE INTO causal_episodes(
          episode_id, repo, task_family, baseline_fingerprint, treatment_json,
          metrics_before_json, metrics_after_json, delta_json, verdict,
          confounds_json, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            episode_id,
            repo,
            opened.get("task_family") or "ad_hoc",
            opened.get("baseline") or _fingerprint(store, repo),
            json.dumps(opened.get("treatment") or {}),
            json.dumps(metrics_before),
            json.dumps(after),
            json.dumps(delta),
            verdict,
            json.dumps(confounds),
            now,
        ),
    )
    links = []
    if "recall_at_k" in delta:
        store.db.execute(
            """
            INSERT OR REPLACE INTO causal_links(
              episode_id, cause_kind, cause_id, effect_metric, effect_delta
            ) VALUES(?, ?, ?, ?, ?)
            """,
            (
                episode_id,
                "memory_state",
                opened.get("baseline") or "baseline",
                "recall_at_k",
                float(delta["recall_at_k"]),
            ),
        )
        links.append("recall_at_k")
    store.db.commit()
    try:
        store.append_neural_event(
            repo,
            event_type="causal_episode",
            entity_id=episode_id,
            payload={"verdict": verdict, "delta": delta, "confounds": confounds},
        )
    except Exception:
        pass
    # Clear open episode
    try:
        store.set_setting(f"causal_open:{repo}", {"closed": True, "episode_id": episode_id})
    except Exception:
        pass
    return {
        "schema_version": "cortex-causal/1.0",
        "episode_id": episode_id,
        "verdict": verdict,
        "delta": delta,
        "confounds": confounds,
        "links": links,
        "claim_boundary": (
            "Causal verdicts recommend ranker/plasticity rollback candidates only; "
            "they never authorize host mutation."
        ),
    }


def record_matched_evaluation(
    store: Any,
    repo: str,
    *,
    suite: str,
    freeze_id: str,
    treatment_name: str,
    control_name: str,
    treatment_metrics: dict[str, Any],
    control_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Record a sealed within-suite retrieval ablation as local causal evidence.

    This is stronger than an unmatched cadence proxy and weaker than a live task
    outcome.  The boundary is persisted with the episode so reports cannot erase
    that distinction.
    """

    if not freeze_id or suite != "holdout":
        return {"recorded": False, "reason": "sealed_holdout_required"}
    delta: dict[str, float] = {}
    for metric in ("recall_at_k", "mrr"):
        before = control_metrics.get(metric)
        after = treatment_metrics.get(metric)
        if before is not None and after is not None:
            delta[metric] = round(float(after) - float(before), 6)
    recall_delta = float(delta.get("recall_at_k") or 0.0)
    mrr_delta = float(delta.get("mrr") or 0.0)
    if recall_delta > 0.02 or (abs(recall_delta) <= 0.02 and mrr_delta > 0.005):
        verdict = "improved"
    elif recall_delta < -0.02 or (abs(recall_delta) <= 0.02 and mrr_delta < -0.005):
        verdict = "regressed"
    else:
        verdict = "inconclusive"
    confounds = ["sealed_ablation_not_live_task_outcome"]
    if verdict == "inconclusive":
        confounds.append("effect_below_threshold")
    identity = {
        "repo": repo,
        "suite": suite,
        "freeze_id": freeze_id,
        "treatment": treatment_name,
        "control": control_name,
    }
    episode_id = "ep_eval_" + sha256(
        json.dumps(identity, sort_keys=True).encode()
    ).hexdigest()[:20]
    treatment = {
        "kind": "sealed_retrieval_ablation",
        "suite": suite,
        "freeze_id": freeze_id,
        "treatment": treatment_name,
        "control": control_name,
        "verification_type": "sealed_holdout_ablation",
    }
    now = time.time()
    store.db.execute(
        """
        INSERT OR REPLACE INTO causal_episodes(
          episode_id, repo, task_family, baseline_fingerprint, treatment_json,
          metrics_before_json, metrics_after_json, delta_json, verdict,
          confounds_json, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            episode_id,
            repo,
            f"eval_coupling:{treatment_name}",
            freeze_id,
            json.dumps(treatment, sort_keys=True),
            json.dumps(control_metrics, sort_keys=True),
            json.dumps(treatment_metrics, sort_keys=True),
            json.dumps(delta, sort_keys=True),
            verdict,
            json.dumps(confounds),
            now,
        ),
    )
    for metric, effect in delta.items():
        store.db.execute(
            """
            INSERT OR REPLACE INTO causal_links(
              episode_id, cause_kind, cause_id, effect_metric, effect_delta
            ) VALUES(?, ?, ?, ?, ?)
            """,
            (
                episode_id,
                "sealed_retrieval_ablation",
                treatment_name,
                metric,
                float(effect),
            ),
        )
    store.db.commit()
    receipt_hash = sha256(
        json.dumps(
            {**identity, "delta": delta, "verdict": verdict},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return {
        "recorded": True,
        "episode_id": episode_id,
        "verdict": verdict,
        "delta": delta,
        "confounds": confounds,
        "receipt_hash": receipt_hash,
        "evidence_class": "sealed_holdout_ablation",
        "claim_boundary": (
            "Matched ablation supports local retrieval-component utility only; "
            "it is not a live task outcome or universal causal proof."
        ),
    }


def causal_report(store: Any, repo: str, *, limit: int = 20) -> dict[str, Any]:
    rows = store.db.execute(
        """
        SELECT * FROM causal_episodes WHERE repo=?
        ORDER BY created_at DESC LIMIT ?
        """,
        (repo, limit),
    ).fetchall()
    episodes = []
    improved = regressed = inconclusive = paired_verified = unmatched = 0
    for row in rows:
        v = row["verdict"]
        if v == "improved":
            improved += 1
        elif v == "regressed":
            regressed += 1
        else:
            inconclusive += 1
        treatment = json.loads(row["treatment_json"] or "{}")
        confounds = json.loads(row["confounds_json"] or "[]")
        if treatment.get("verification_type") == "sealed_holdout_ablation":
            paired_verified += 1
        if "missing_recall_pair" in confounds:
            unmatched += 1
        episodes.append(
            {
                "episode_id": row["episode_id"],
                "task_family": row["task_family"],
                "verdict": v,
                "delta": json.loads(row["delta_json"] or "{}"),
                "verification_type": treatment.get("verification_type"),
                "confounds": confounds,
                "created_at": row["created_at"],
            }
        )
    return {
        "schema_version": "cortex-causal-report/1.0",
        "repo": repo,
        "counts": {
            "improved": improved,
            "regressed": regressed,
            "inconclusive": inconclusive,
            "paired_verified": paired_verified,
            "unmatched": unmatched,
            "total": len(episodes),
        },
        "episodes": episodes,
        "recommendation": (
            "consider_ranker_rollback"
            if regressed > improved and regressed > 0
            else "hold_course"
        ),
        "claim_boundary": "Causal report is local telemetry; not production proof.",
    }
