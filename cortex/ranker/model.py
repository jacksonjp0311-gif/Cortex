"""Linear online ranker trained only on verified outcomes under Governor."""

from __future__ import annotations

import json
import math
import time
from hashlib import sha256
from typing import Any

SCHEMA = "cortex-ranker/1.0"
MODEL_ID = "linear_v1"

FEATURE_NAMES: tuple[str, ...] = (
    "thalamus_lane",
    "fts_rank",
    "vector_sim",
    "neural_support",
    "path_depth",
    "is_test",
    "is_doc",
    "is_source",
    "resolution_symbol",
    "retrieval_confidence",
    "surprise_ratio",
    "immune_block",
    "aria_deferred",
    "prior_score",
    "recency",
    "evidence_kind_card",
)


def _clip(v: float, lo: float = -2.0, hi: float = 2.0) -> float:
    return max(lo, min(hi, float(v)))


def default_weights() -> list[float]:
    # Hand-tuned seed approximating v3 fusion priorities.
    w = [0.0] * len(FEATURE_NAMES)
    mapping = {
        "thalamus_lane": 0.35,
        "fts_rank": 0.40,
        "vector_sim": 0.45,
        "neural_support": 0.30,
        "is_source": 0.15,
        "is_test": 0.12,
        "prior_score": 0.50,
        "retrieval_confidence": 0.10,
        "path_depth": -0.05,
        "immune_block": -0.20,
        "aria_deferred": -0.15,
    }
    for i, name in enumerate(FEATURE_NAMES):
        w[i] = mapping.get(name, 0.0)
    return w


def ensure_ranker(store: Any, repo: str) -> dict[str, Any]:
    row = store.db.execute(
        "SELECT * FROM ranker_models WHERE repo=? AND model_id=?",
        (repo, MODEL_ID),
    ).fetchone()
    now = time.time()
    if row:
        return {
            "model_id": row["model_id"],
            "schema_version": row["schema_version"],
            "weights": json.loads(row["weights_json"]),
            "bias": float(row["bias"]),
            "train_count": int(row["train_count"]),
            "feature_names": json.loads(row["feature_names_json"]),
        }
    weights = default_weights()
    store.db.execute(
        """
        INSERT INTO ranker_models(
          repo, model_id, schema_version, feature_names_json, weights_json,
          bias, train_count, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            repo,
            MODEL_ID,
            SCHEMA,
            json.dumps(list(FEATURE_NAMES)),
            json.dumps(weights),
            0.0,
            now,
            now,
        ),
    )
    store.db.commit()
    return {
        "model_id": MODEL_ID,
        "schema_version": SCHEMA,
        "weights": weights,
        "bias": 0.0,
        "train_count": 0,
        "feature_names": list(FEATURE_NAMES),
    }


def features_from_hit(
    hit: Any,
    *,
    rank: int = 0,
    retrieval_confidence: float = 0.0,
    surprise_ratio: float = 0.0,
    immune_block: bool = False,
    neural_support: bool = False,
    thalamus_lane: float = 0.5,
) -> list[float]:
    path = ""
    kind = ""
    score = 0.0
    meta: dict[str, Any] = {}
    if isinstance(hit, dict):
        path = str(hit.get("path") or "")
        kind = str(hit.get("kind") or "")
        score = float(hit.get("score") or 0.0)
        meta = hit.get("metadata") or {}
    else:
        path = str(getattr(hit, "path", "") or "")
        kind = str(getattr(hit, "kind", "") or "")
        score = float(getattr(hit, "score", 0.0) or 0.0)
        meta = getattr(hit, "metadata", None) or {}
    path_n = path.replace("\\", "/")
    depth = path_n.count("/")
    is_test = 1.0 if ("test" in path_n.lower() or kind == "test") else 0.0
    is_doc = 1.0 if (kind in {"documentation", "doc"} or path_n.endswith(".md")) else 0.0
    is_source = 1.0 if kind in {"source", "code", ""} and not is_test and not is_doc else 0.0
    vec_sim = float(meta.get("semantic_similarity") or meta.get("vector_sim") or 0.0)
    fts = 1.0 / (1.0 + rank)
    feats = {
        "thalamus_lane": thalamus_lane,
        "fts_rank": fts,
        "vector_sim": vec_sim,
        "neural_support": 1.0 if neural_support else 0.0,
        "path_depth": min(1.0, depth / 8.0),
        "is_test": is_test,
        "is_doc": is_doc,
        "is_source": is_source,
        "resolution_symbol": 1.0 if str(meta.get("resolution")) == "symbol" else 0.0,
        "retrieval_confidence": retrieval_confidence,
        "surprise_ratio": surprise_ratio,
        "immune_block": 1.0 if immune_block else 0.0,
        "aria_deferred": 1.0 if "aria_meta/vendor" in path_n else 0.0,
        "prior_score": min(1.0, max(0.0, score)),
        "recency": float(meta.get("recency") or 0.5),
        "evidence_kind_card": 1.0 if kind == "discovery_card" else 0.0,
    }
    return [_clip(feats[name], -1.0, 1.0) for name in FEATURE_NAMES]


def score_features(model: dict[str, Any], features: list[float]) -> float:
    weights = model.get("weights") or default_weights()
    bias = float(model.get("bias") or 0.0)
    n = min(len(weights), len(features))
    z = bias + sum(float(weights[i]) * float(features[i]) for i in range(n))
    # Squash to 0..1
    return 1.0 / (1.0 + math.exp(-_clip(z, -8.0, 8.0)))


def rerank_hits(
    store: Any,
    repo: str,
    hits: list[Any],
    *,
    retrieval_confidence: float = 0.0,
    surprise_ratio: float = 0.0,
    immune_block: bool = False,
) -> list[Any]:
    if not hits:
        return hits
    model = ensure_ranker(store, repo)
    scored: list[tuple[float, Any]] = []
    for i, hit in enumerate(hits):
        feats = features_from_hit(
            hit,
            rank=i,
            retrieval_confidence=retrieval_confidence,
            surprise_ratio=surprise_ratio,
            immune_block=immune_block,
        )
        s = score_features(model, feats)
        # Blend with original score for stability
        prior = 0.0
        if isinstance(hit, dict):
            prior = float(hit.get("score") or 0.0)
            hit = {**hit, "ranker_score": round(s, 6)}
        else:
            prior = float(getattr(hit, "score", 0.0) or 0.0)
            try:
                hit.metadata = {**(hit.metadata or {}), "ranker_score": round(s, 6)}
            except Exception:
                pass
        scored.append((0.55 * s + 0.45 * min(1.0, prior), hit))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in scored]


def train_from_outcome(
    store: Any,
    repo: str,
    *,
    outcome_id: str,
    activation_id: str,
    status: str,
    reward: float,
    verification_type: str,
    governance_mode: str = "read_only",
    feature_vectors: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Online SGD update. Only verified/helpful with non-read_only may train."""

    if governance_mode == "read_only":
        return {"trained": False, "reason": "governor_read_only"}
    if status not in {"verified", "helpful", "failed", "unsafe", "irrelevant"}:
        return {"trained": False, "reason": "status_not_trainable"}
    if status == "unsafe":
        return {"trained": False, "reason": "unsafe_freezes_ranker"}

    model = ensure_ranker(store, repo)
    label = 1.0 if status in {"verified", "helpful"} else -1.0
    if status == "irrelevant":
        label = -0.5
    lr = 0.05 if governance_mode == "normal" else 0.02
    vectors = feature_vectors or [features_from_hit({"score": abs(reward), "path": "outcome"})]
    weights = list(model["weights"])
    bias = float(model["bias"])
    for feats in vectors:
        pred = score_features({"weights": weights, "bias": bias}, feats)
        # logistic loss gradient toward label mapped 0/1
        y = 1.0 if label > 0 else 0.0
        err = pred - y
        for i in range(min(len(weights), len(feats))):
            weights[i] = _clip(weights[i] - lr * err * feats[i], -3.0, 3.0)
        bias = _clip(bias - lr * err, -2.0, 2.0)

    # L2 light decay
    for i in range(len(weights)):
        weights[i] *= 0.999

    now = time.time()
    example_id = "rex_" + sha256(f"{outcome_id}|{activation_id}".encode()).hexdigest()[:20]
    store.db.execute(
        """
        INSERT OR REPLACE INTO ranker_examples(
          example_id, repo, outcome_id, activation_id, feature_vector_json,
          label, verification_type, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            example_id,
            repo,
            outcome_id,
            activation_id,
            json.dumps(vectors[0] if vectors else []),
            label,
            verification_type,
            now,
        ),
    )
    store.db.execute(
        """
        UPDATE ranker_models SET weights_json=?, bias=?, train_count=train_count+1,
          last_outcome_id=?, updated_at=?
        WHERE repo=? AND model_id=?
        """,
        (json.dumps(weights), bias, outcome_id, now, repo, MODEL_ID),
    )
    store.db.commit()
    try:
        store.append_neural_event(
            repo,
            event_type="ranker_trained",
            entity_id=MODEL_ID,
            payload={
                "outcome_id": outcome_id,
                "status": status,
                "label": label,
                "train_count": int(model["train_count"]) + 1,
            },
        )
    except Exception:
        pass
    return {
        "trained": True,
        "model_id": MODEL_ID,
        "label": label,
        "train_count": int(model["train_count"]) + 1,
        "claim_boundary": "Ranker learns ranking only; never mutation authority.",
    }


def ranker_status(store: Any, repo: str) -> dict[str, Any]:
    model = ensure_ranker(store, repo)
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "model_id": model["model_id"],
        "train_count": model["train_count"],
        "feature_count": len(model["feature_names"]),
        "bias": model["bias"],
        "claim_boundary": "Ranker status is operational telemetry; not host rights.",
    }
