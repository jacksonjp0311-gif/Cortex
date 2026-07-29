"""Connect pass — gather metrics each connect, expand metric graph, distill to substrate.

One substrate only. Each activate/organism/breathe/ritual pass:
1. Accumulates multi-surface metrics (immune, efficiency, surprise, neural, thalamus, ARIA)
2. Expands a durable metric graph in settings + neural_ledger
3. Distills high-signal lessons into episodic memory when thresholds fire

Never grants mutation authority. Never executes ARIA plans.
"""

from __future__ import annotations

import time
from hashlib import sha256
from typing import Any

SCHEMA = "cortex-connect-pass/1.0"
GRAPH_SCHEMA = "cortex-metric-graph/1.0"
GLYPH = "⧉"  # connect / gather / co-activation — capability free
ROLLING_MAX = 32
PATH_PAIRS_MAX = 64
DISTILL_SEEN_MAX = 48


def _h(material: Any) -> str:
    import json

    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(encoded.encode("utf-8")).hexdigest()[:16]


def gather_connect_metrics(
    *,
    repo: str,
    task: str,
    session_id: str | None,
    surface: str,
    context: dict[str, Any],
    surprise: dict[str, Any] | None = None,
    organism: dict[str, Any] | None = None,
    activation: str | None = None,
    block: bool | None = None,
) -> dict[str, Any]:
    """Fold packet surfaces into one connect-pass metric vector."""

    control = context.get("control_error") or {}
    immune = control.get("immune_action") or {}
    efficiency = context.get("efficiency") or {}
    neural = context.get("neural_interlink") or {}
    n_metrics = neural.get("metrics") or {}
    thalamus = context.get("thalamus") or {}
    aria = context.get("aria_materialization") or {}
    evidence = context.get("evidence") or []
    geometry = context.get("geometry") or {}
    surprise = surprise or efficiency.get("surprise") or {}
    organism = organism or context.get("organism") or {}

    paths = [
        str(item.get("path") or "")
        for item in evidence
        if isinstance(item, dict) and item.get("path")
    ]
    paths = [p for p in paths if p][:12]

    if block is None:
        block = bool(control.get("block"))

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "task_preview": (task or "")[:160],
        "session_id": session_id,
        "surface": surface,
        "activation": activation,
        "ts": round(time.time(), 3),
        "pass_id": _h(
            {
                "repo": repo,
                "task": task,
                "t": round(time.time(), 1),
                "session": session_id,
            }
        ),
        "immune": {
            "block": block,
            "code": immune.get("code") or control.get("summary"),
            "severity": control.get("severity"),
            "must_reverify": bool(control.get("must_reverify")),
            "work_allowed": control.get("work_allowed"),
        },
        "efficiency": {
            "direct_candidates": efficiency.get("direct_candidates"),
            "nodes_considered": efficiency.get("nodes_considered"),
            "total_nodes": efficiency.get("total_nodes"),
            "node_scan_fraction": efficiency.get("node_scan_fraction"),
            "context_tokens": efficiency.get("context_tokens"),
            "context_budget_fraction": efficiency.get("context_budget_fraction"),
        },
        "surprise": {
            "refreshed": bool(surprise.get("refreshed")),
            "surprise_ratio": float(surprise.get("surprise_ratio") or 0.0),
            "files_reindexed": int(surprise.get("files_reindexed") or 0),
            "deferred_files": int(surprise.get("deferred_files") or 0),
        },
        "neural": {
            "activation_id": neural.get("activation_id"),
            "nodes_fired": n_metrics.get("nodes_fired"),
            "nodes_considered": n_metrics.get("nodes_considered"),
            "sparse_activation_ratio": n_metrics.get("sparse_activation_ratio"),
            "propagation_steps": n_metrics.get("propagation_steps"),
            "state_hash": neural.get("state_hash"),
        },
        "thalamus": {
            "available": bool(thalamus.get("available", thalamus)),
            "intent": thalamus.get("intent") or thalamus.get("classification"),
            "uncertainty": thalamus.get("uncertainty"),
            "confidence": thalamus.get("confidence"),
        },
        "aria": {
            "mode": aria.get("mode") or (efficiency.get("aria_substrate") or {}).get("mode"),
            "materialized_this_turn": bool(aria.get("materialized")),
            "already_ready": bool(aria.get("already_ready")),
            "deferred_remaining": (efficiency.get("aria_substrate") or {}).get(
                "deferred_remaining"
            ),
            "eligible_nodes": (n_metrics.get("aria_substrate") or {}).get("eligible_nodes"),
        },
        "evidence": {
            "count": len(evidence),
            "paths": paths,
        },
        "geometry_zero_point": bool(geometry.get("zero_point")),
        "organism_pulse": organism.get("pulse"),
        "organism_phase": organism.get("phase")
        or (organism.get("body") or {}).get("identity", {}).get("phase"),
        "prediction": {
            "paths": len(
                ((context.get("prediction") or {}).get("predicted_paths") or [])
            ),
            "trace_id": (context.get("prediction") or {}).get("trace_id"),
        },
        "v5": {
            "multi_res": True,
            "ranker": True,
            "hnsw": True,
            "contracts": True,
            "agents": True,
            "causal": True,
        },
        "claim_boundary": (
            "Connect metrics are local operational telemetry; not consciousness "
            "and not mutation authority."
        ),
    }


def _empty_graph(repo: str) -> dict[str, Any]:
    return {
        "schema_version": GRAPH_SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "pass_count": 0,
        "first_pass_at": None,
        "last_pass_at": None,
        "totals": {
            "block_count": 0,
            "reverify_count": 0,
            "surprise_sum": 0.0,
            "nodes_fired_sum": 0,
            "evidence_sum": 0,
            "aria_materialize_count": 0,
            "aria_active_count": 0,
            "distill_count": 0,
            "surfaces": {},
        },
        "rolling": [],
        "path_coactivation": {},
        "immune_codes": {},
        "thalamus_intents": {},
        "distilled_claim_ids": [],
        "last_pass_id": None,
    }


def load_metric_graph(store: Any, repo: str) -> dict[str, Any]:
    key = f"metric_graph:{repo}"
    raw = store.get_setting(key, None) if hasattr(store, "get_setting") else None
    if isinstance(raw, dict) and raw.get("schema_version") == GRAPH_SCHEMA:
        return raw
    return _empty_graph(repo)


def _bump(counter: dict[str, Any], key: str | None, amount: int = 1) -> None:
    if not key:
        return
    counter[key] = int(counter.get(key) or 0) + amount


def expand_metric_graph(
    graph: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, Any]:
    """Each connect expands the graph — more coactivations, codes, rolling series."""

    g = dict(graph)
    totals = dict(g.get("totals") or {})
    surfaces = dict(totals.get("surfaces") or {})
    path_co = dict(g.get("path_coactivation") or {})
    immune_codes = dict(g.get("immune_codes") or {})
    intents = dict(g.get("thalamus_intents") or {})
    rolling = list(g.get("rolling") or [])
    distilled = list(g.get("distilled_claim_ids") or [])

    g["pass_count"] = int(g.get("pass_count") or 0) + 1
    now = metrics.get("ts") or time.time()
    if not g.get("first_pass_at"):
        g["first_pass_at"] = now
    g["last_pass_at"] = now
    g["last_pass_id"] = metrics.get("pass_id")

    immune = metrics.get("immune") or {}
    surprise = metrics.get("surprise") or {}
    neural = metrics.get("neural") or {}
    aria = metrics.get("aria") or {}
    evidence = metrics.get("evidence") or {}

    if immune.get("block"):
        totals["block_count"] = int(totals.get("block_count") or 0) + 1
    if immune.get("must_reverify"):
        totals["reverify_count"] = int(totals.get("reverify_count") or 0) + 1
    totals["surprise_sum"] = float(totals.get("surprise_sum") or 0.0) + float(
        surprise.get("surprise_ratio") or 0.0
    )
    totals["nodes_fired_sum"] = int(totals.get("nodes_fired_sum") or 0) + int(
        neural.get("nodes_fired") or 0
    )
    totals["evidence_sum"] = int(totals.get("evidence_sum") or 0) + int(
        evidence.get("count") or 0
    )
    if aria.get("materialized_this_turn"):
        totals["aria_materialize_count"] = int(totals.get("aria_materialize_count") or 0) + 1
    if (aria.get("mode") or "") == "active":
        totals["aria_active_count"] = int(totals.get("aria_active_count") or 0) + 1

    surface = str(metrics.get("surface") or "activate")
    _bump(surfaces, surface)
    totals["surfaces"] = surfaces
    _bump(immune_codes, str(immune.get("code") or "unknown"))
    _bump(intents, str((metrics.get("thalamus") or {}).get("intent") or "none"))

    # Path co-activation graph: every pair of top evidence paths strengthens.
    paths = [p for p in (evidence.get("paths") or []) if p]
    for i, a in enumerate(paths):
        for b in paths[i + 1 :]:
            pair = "|".join(sorted((a, b)))
            path_co[pair] = int(path_co.get(pair) or 0) + 1
    # Cap path pairs by keeping strongest
    if len(path_co) > PATH_PAIRS_MAX:
        path_co = dict(
            sorted(path_co.items(), key=lambda kv: kv[1], reverse=True)[:PATH_PAIRS_MAX]
        )

    roll_entry = {
        "pass_id": metrics.get("pass_id"),
        "ts": now,
        "surface": surface,
        "block": bool(immune.get("block")),
        "surprise_ratio": float(surprise.get("surprise_ratio") or 0.0),
        "nodes_fired": int(neural.get("nodes_fired") or 0),
        "evidence_count": int(evidence.get("count") or 0),
        "aria_mode": aria.get("mode"),
        "immune_code": immune.get("code"),
        "sparse": neural.get("sparse_activation_ratio"),
    }
    rolling.append(roll_entry)
    rolling = rolling[-ROLLING_MAX:]

    g["totals"] = totals
    g["path_coactivation"] = path_co
    g["immune_codes"] = immune_codes
    g["thalamus_intents"] = intents
    g["rolling"] = rolling
    g["distilled_claim_ids"] = distilled[-DISTILL_SEEN_MAX:]
    g["averages"] = {
        "surprise_ratio": round(
            float(totals.get("surprise_sum") or 0.0) / max(1, g["pass_count"]), 6
        ),
        "nodes_fired": round(
            float(totals.get("nodes_fired_sum") or 0) / max(1, g["pass_count"]), 3
        ),
        "evidence_count": round(
            float(totals.get("evidence_sum") or 0) / max(1, g["pass_count"]), 3
        ),
        "block_rate": round(
            float(totals.get("block_count") or 0) / max(1, g["pass_count"]), 4
        ),
    }
    return g


def distill_candidates(
    metrics: dict[str, Any], graph: dict[str, Any]
) -> list[dict[str, str]]:
    """High-signal lessons ready to enter episodic memory (not auto-mutate)."""

    claims: list[dict[str, str]] = []
    seen = set(graph.get("distilled_claim_ids") or [])
    immune = metrics.get("immune") or {}
    surprise = metrics.get("surprise") or {}
    aria = metrics.get("aria") or {}
    neural = metrics.get("neural") or {}
    evidence = metrics.get("evidence") or {}
    pass_n = int(graph.get("pass_count") or 0)

    def add(claim_id: str, kind: str, text: str) -> None:
        if claim_id in seen:
            return
        claims.append({"id": claim_id, "kind": kind, "text": text})

    if immune.get("block"):
        code = immune.get("code") or "STOP"
        add(
            f"immune-block:{code}",
            "constraint",
            f"Connect distill: immune block {code} — diagnose only; no host mutation.",
        )
    if float(surprise.get("surprise_ratio") or 0.0) >= 0.15:
        add(
            f"surprise:{metrics.get('pass_id')}",
            "discovery",
            (
                f"Connect distill: high surprise_ratio="
                f"{float(surprise.get('surprise_ratio') or 0):.3f} "
                f"({int(surprise.get('files_reindexed') or 0)} files reindexed)."
            ),
        )
    if aria.get("materialized_this_turn"):
        add(
            f"aria-materialize:{metrics.get('pass_id')}",
            "discovery",
            "Connect distill: ARIA substrate materialized this turn (wake-gated, not executed).",
        )
    if (aria.get("mode") or "") == "active" and int(evidence.get("count") or 0) >= 2:
        add(
            "aria-active-evidence",
            "lesson",
            "Connect distill: ARIA active with multi-path evidence — treat as language region only.",
        )
    sparse = neural.get("sparse_activation_ratio")
    if sparse is not None and float(sparse) > 0 and float(sparse) < 0.05:
        add(
            "neural-sparse",
            "discovery",
            f"Connect distill: very sparse neural activation ratio={float(sparse):.4f}.",
        )
    # After several connects, surface rollup lesson once.
    if pass_n in {3, 8, 21}:
        av = graph.get("averages") or {}
        add(
            f"rollup-pass-{pass_n}",
            "lesson",
            (
                f"Connect distill rollup after {pass_n} passes: "
                f"avg_surprise={av.get('surprise_ratio')}, "
                f"block_rate={av.get('block_rate')}, "
                f"avg_evidence={av.get('evidence_count')}."
            ),
        )
    # Top coactivation pair becomes durable topology lesson.
    path_co = graph.get("path_coactivation") or {}
    if path_co:
        top_pair, top_n = max(path_co.items(), key=lambda kv: kv[1])
        if top_n >= 2:
            a, b = top_pair.split("|", 1)
            add(
                f"coact:{_h(top_pair)}",
                "discovery",
                f"Connect distill: evidence co-activation {a} ↔ {b} (n={top_n}).",
            )
    return claims


def persist_connect_pass(
    store: Any,
    repo: str,
    metrics: dict[str, Any],
    *,
    home: Any | None = None,
    auto_distill: bool = True,
    causal_every: int = 3,
    auto_decay: bool = True,
) -> dict[str, Any]:
    """Write ledger event, expand metric graph, distill, causal cadence, light decay."""

    graph = expand_metric_graph(load_metric_graph(store, repo), metrics)
    candidates = distill_candidates(metrics, graph) if auto_distill else []
    remembered: list[dict[str, Any]] = []
    distill_ids: list[str] = list(graph.get("distilled_claim_ids") or [])

    # Immune block freezes ranker (seal the gate)
    if (metrics.get("immune") or {}).get("block"):
        try:
            from .ranker.model import freeze_ranker

            freeze_ranker(store, repo, reason="immune_block_on_connect")
        except Exception:
            pass

    if auto_distill and candidates and home is not None:
        try:
            from .hippocampus import remember

            session_id = metrics.get("session_id")
            for claim in candidates:
                result = remember(
                    home,
                    store,
                    repo,
                    claim["kind"],
                    claim["text"],
                    session_id=session_id,
                )
                remembered.append(
                    {
                        "id": claim["id"],
                        "kind": claim["kind"],
                        "recorded": bool(
                            result.get("recorded") or result.get("duplicate")
                        ),
                        "duplicate": bool(result.get("duplicate")),
                    }
                )
                distill_ids.append(claim["id"])
        except Exception as exc:
            remembered.append({"error": f"{type(exc).__name__}: {exc}"})

    graph["distilled_claim_ids"] = distill_ids[-DISTILL_SEEN_MAX:]
    totals = dict(graph.get("totals") or {})
    totals["distill_count"] = int(totals.get("distill_count") or 0) + len(
        [r for r in remembered if r.get("recorded")]
    )
    graph["totals"] = totals

    try:
        store.set_setting(f"metric_graph:{repo}", graph)
    except Exception:
        pass

    causal_result: dict[str, Any] | None = None
    pass_n = int(graph.get("pass_count") or 0)
    if causal_every > 0 and pass_n > 0 and pass_n % causal_every == 0:
        try:
            from .causal.ledger import evaluate_causal_episode, open_episode

            open_episode(
                store,
                repo,
                f"connect_cadence_{pass_n}",
                treatment={
                    "kind": "connect_pass_cadence",
                    "pass_count": pass_n,
                    "block": (metrics.get("immune") or {}).get("block"),
                },
            )
            # Proxy: block rate change as soft effect (inconclusive without recall)
            av = graph.get("averages") or {}
            causal_result = evaluate_causal_episode(
                store,
                repo,
                metrics_after={"metric_graph": av, "pass_count": pass_n},
            )
            if causal_result.get("verdict") == "regressed":
                from .ranker.model import freeze_ranker

                freeze_ranker(store, repo, reason="causal_regressed")
        except Exception as exc:
            causal_result = {"error": f"{type(exc).__name__}: {exc}"}

    decay_result: dict[str, Any] | None = None
    if auto_decay and pass_n > 0 and pass_n % 5 == 0:
        try:
            from .prune import decay_unused_weights

            decay_result = decay_unused_weights(store, repo, factor=0.98)
        except Exception as exc:
            decay_result = {"error": f"{type(exc).__name__}: {exc}"}

    try:
        store.append_neural_event(
            repo,
            event_type="connect_pass",
            entity_id=metrics.get("session_id") or repo,
            payload={
                "pass_id": metrics.get("pass_id"),
                "surface": metrics.get("surface"),
                "immune_code": (metrics.get("immune") or {}).get("code"),
                "block": (metrics.get("immune") or {}).get("block"),
                "surprise_ratio": (metrics.get("surprise") or {}).get("surprise_ratio"),
                "nodes_fired": (metrics.get("neural") or {}).get("nodes_fired"),
                "sparse": (metrics.get("neural") or {}).get("sparse_activation_ratio"),
                "evidence_count": (metrics.get("evidence") or {}).get("count"),
                "aria_mode": (metrics.get("aria") or {}).get("mode"),
                "aria_materialized": (metrics.get("aria") or {}).get(
                    "materialized_this_turn"
                ),
                "prefetch_paths": (metrics.get("prediction") or {}).get("paths"),
                "organism_pulse": metrics.get("organism_pulse"),
                "pass_count": graph.get("pass_count"),
                "distilled": [c["id"] for c in candidates],
                "causal_verdict": (causal_result or {}).get("verdict"),
            },
        )
    except Exception:
        pass

    return {
        "schema_version": SCHEMA,
        "glyph": GLYPH,
        "pass_id": metrics.get("pass_id"),
        "pass_count": graph.get("pass_count"),
        "metrics": metrics,
        "metric_graph": {
            "pass_count": graph.get("pass_count"),
            "averages": graph.get("averages"),
            "totals": {
                "block_count": (graph.get("totals") or {}).get("block_count"),
                "aria_materialize_count": (graph.get("totals") or {}).get(
                    "aria_materialize_count"
                ),
                "distill_count": (graph.get("totals") or {}).get("distill_count"),
                "surfaces": (graph.get("totals") or {}).get("surfaces"),
            },
            "top_coactivations": dict(
                sorted(
                    (graph.get("path_coactivation") or {}).items(),
                    key=lambda kv: kv[1],
                    reverse=True,
                )[:5]
            ),
            "immune_codes": graph.get("immune_codes"),
        },
        "distilled": remembered,
        "causal": causal_result,
        "decay": decay_result,
        "claim_boundary": metrics.get("claim_boundary"),
    }


def record_connect_pass(
    store: Any,
    home: Any,
    *,
    repo: str,
    task: str,
    session_id: str | None,
    surface: str,
    context: dict[str, Any],
    surprise: dict[str, Any] | None = None,
    organism: dict[str, Any] | None = None,
    activation: str | None = None,
    block: bool | None = None,
    auto_distill: bool = True,
) -> dict[str, Any]:
    """Gather + persist + distill one connect pass (safe no-op on store errors)."""

    try:
        metrics = gather_connect_metrics(
            repo=repo,
            task=task,
            session_id=session_id,
            surface=surface,
            context=context,
            surprise=surprise,
            organism=organism,
            activation=activation,
            block=block,
        )
        return persist_connect_pass(
            store, repo, metrics, home=home, auto_distill=auto_distill
        )
    except Exception as exc:
        return {
            "schema_version": SCHEMA,
            "glyph": GLYPH,
            "error": f"{type(exc).__name__}: {exc}",
            "pass_count": None,
        }


def metric_graph_report(store: Any, repo: str) -> dict[str, Any]:
    """Inspect accumulated metric graph for one repository."""

    graph = load_metric_graph(store, repo)
    recent_events: list[dict[str, Any]] = []
    try:
        for event in store.neural_events(repo, limit=40):
            if event["event_type"] != "connect_pass":
                continue
            payload = event["payload"]
            if isinstance(payload, str):
                import json

                payload = json.loads(payload or "{}")
            recent_events.append(
                {
                    "sequence": event["sequence"],
                    "created_at": event["created_at"],
                    "payload": payload,
                }
            )
    except Exception:
        pass
    return {
        "schema_version": GRAPH_SCHEMA,
        "glyph": GLYPH,
        "repo": repo,
        "graph": graph,
        "recent_connect_passes": recent_events[:12],
        "claim_boundary": (
            "Metric graph is local rollup telemetry from connect passes; "
            "not universal readiness and not mutation authority."
        ),
    }
