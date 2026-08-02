"""Predict likely evidence paths before the agent asks. Never grants rights."""

from __future__ import annotations

import json
import math
import time
from hashlib import sha256
from typing import Any

from ..connect_pass import load_metric_graph
from ..retrieval import query


def predict_context(
    store: Any,
    repo: str,
    task: str,
    *,
    budget: int = 200,
    session_id: str | None = None,
    limit: int = 8,
    governor_mode: str = "normal",
) -> dict[str, Any]:
    """Propose paths likely useful for the task. Read-only operational plane."""

    if governor_mode == "read_only":
        return {
            "schema_version": "cortex-predict/1.0",
            "repo": repo,
            "task": task,
            "predicted_paths": [],
            "mode": "metadata_only",
            "reason": "governor_read_only",
            "claim_boundary": "Prefetch disabled under read_only; no mutation rights.",
        }

    max_paths = 4 if governor_mode == "constrained" else limit
    scores: dict[str, float] = {}

    # Seed from hybrid retrieval (no ARIA materialize here)
    try:
        hits = query(store, repo, task, limit=max_paths * 2, materialize_substrate=False)
    except Exception:
        hits = []
    for i, hit in enumerate(hits):
        path = getattr(hit, "path", None) or (hit.get("path") if isinstance(hit, dict) else None)
        if not path:
            continue
        scores[path] = scores.get(path, 0.0) + 1.0 / (1.0 + i)

    # Boost co-activated paths using specificity-normalized association.  Raw
    # counts reward popular hubs repeatedly; n/sqrt(m_a*m_b) rewards pairs that
    # are strong relative to each path's total traffic.
    graph = load_metric_graph(store, repo)
    coact = graph.get("path_coactivation") or {}
    marginal: dict[str, float] = {}
    for pair, n in coact.items():
        if "|" not in pair:
            continue
        a, b = pair.split("|", 1)
        mass = max(0.0, float(n or 0.0))
        marginal[a] = marginal.get(a, 0.0) + mass
        marginal[b] = marginal.get(b, 0.0) + mass
    seed_paths = set(scores.keys())
    for pair, n in coact.items():
        if "|" not in pair:
            continue
        a, b = pair.split("|", 1)
        mass = max(0.0, float(n or 0.0))
        denom = max(1.0, (marginal.get(a, 0.0) * marginal.get(b, 0.0)) ** 0.5)
        association = min(1.0, mass / denom)
        support = min(1.0, math.log1p(mass) / math.log(4.0))
        boost = 0.45 * association * support
        if a in seed_paths:
            scores[b] = scores.get(b, 0.0) + boost
        if b in seed_paths:
            scores[a] = scores.get(a, 0.0) + boost

    # Neural neighborhood of top seeds
    try:
        synapses = store.neural_synapses(repo)
        top = sorted(scores, key=scores.get, reverse=True)[:3]
        for syn in synapses:
            if syn["source_id"] in top and not str(syn["target_id"]).startswith("symbol:"):
                scores[syn["target_id"]] = scores.get(syn["target_id"], 0.0) + 0.1 * float(
                    syn["weight"] or 0
                )
            if syn["target_id"] in top and not str(syn["source_id"]).startswith("symbol:"):
                scores[syn["source_id"]] = scores.get(syn["source_id"], 0.0) + 0.08 * float(
                    syn["weight"] or 0
                )
    except Exception:
        pass

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:max_paths]
    # Budget gate: estimate ~80 tokens/path
    cost = 0
    selected: list[dict[str, Any]] = []
    for path, score in ranked:
        step = 80
        if cost + step > budget:
            break
        cost += step
        selected.append({"path": path, "score": round(score, 6)})

    task_hash = sha256(task.encode("utf-8")).hexdigest()[:24]
    trace_id = "pred_" + sha256(f"{repo}|{task_hash}|{time.time():.0f}".encode()).hexdigest()[:20]
    try:
        store.db.execute(
            """
            INSERT INTO prediction_traces(
              trace_id, repo, session_id, task_hash, predicted_paths_json,
              scores_json, materialize_cost, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id,
                repo,
                session_id,
                task_hash,
                json.dumps([s["path"] for s in selected]),
                json.dumps(selected),
                cost,
                time.time(),
            ),
        )
        store.db.commit()
    except Exception:
        pass

    return {
        "schema_version": "cortex-predict/1.0",
        "glyph": "⌖",
        "repo": repo,
        "task": task,
        "trace_id": trace_id,
        "predicted_paths": [s["path"] for s in selected],
        "scores": selected,
        "materialize_cost": cost,
        "budget": budget,
        "mode": "prefetch_proposal",
        "claim_boundary": (
            "Prediction proposes evidence only; never mutation authority; "
            "never auto-wakes ARIA bulk."
        ),
    }


def record_prediction_outcome(
    store: Any,
    trace_id: str,
    used_paths: list[str],
    *,
    outcome_id: str | None = None,
) -> dict[str, Any]:
    row = store.db.execute(
        "SELECT * FROM prediction_traces WHERE trace_id=?", (trace_id,)
    ).fetchone()
    if not row:
        return {"recorded": False, "reason": "trace_missing"}
    predicted = json.loads(row["predicted_paths_json"] or "[]")
    used = set(used_paths)
    used_count = sum(1 for p in predicted if p in used)
    unused = len(predicted) - used_count
    precision = used_count / max(1, len(predicted))
    store.db.execute(
        """
        INSERT OR REPLACE INTO prediction_outcomes(
          trace_id, used_count, unused_count, precision, outcome_id
        ) VALUES(?, ?, ?, ?, ?)
        """,
        (trace_id, used_count, unused, precision, outcome_id),
    )
    store.db.commit()
    return {
        "recorded": True,
        "trace_id": trace_id,
        "used_count": used_count,
        "unused_count": unused,
        "precision": round(precision, 4),
    }
