"""Causal episodes: did memory changes improve future performance?"""

from __future__ import annotations

import json
import time
from hashlib import sha256
from typing import Any

from ..connect_pass import load_metric_graph
from ..ranker.model import ranker_status


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

    metrics_before = opened.get("metrics_before") or {}
    after = metrics_after or {
        "metric_graph": load_metric_graph(store, repo).get("averages") or {},
        "ranker_train_count": ranker_status(store, repo).get("train_count"),
    }
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


def causal_report(store: Any, repo: str, *, limit: int = 20) -> dict[str, Any]:
    rows = store.db.execute(
        """
        SELECT * FROM causal_episodes WHERE repo=?
        ORDER BY created_at DESC LIMIT ?
        """,
        (repo, limit),
    ).fetchall()
    episodes = []
    improved = regressed = inconclusive = 0
    for row in rows:
        v = row["verdict"]
        if v == "improved":
            improved += 1
        elif v == "regressed":
            regressed += 1
        else:
            inconclusive += 1
        episodes.append(
            {
                "episode_id": row["episode_id"],
                "task_family": row["task_family"],
                "verdict": v,
                "delta": json.loads(row["delta_json"] or "{}"),
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
