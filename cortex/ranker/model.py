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
    # v6.1 spectral / closed-loop features
    "prefetch_hit",
    "hnsw_lane",
    "coact_strength",
    "kernel_retain",
    "kernel_integrate",
    # M3/M4 graph features
    "ppr",
    "heat",
    "degree_centrality",
    "lambda2_gap",
    # M1 uncertainty
    "unified_confidence",
)


def _clip(v: float, lo: float = -2.0, hi: float = 2.0) -> float:
    return max(lo, min(hi, float(v)))


# Softmax / sigmoid temperature: >1 de-saturates so small feature deltas reorder.
SCORE_TEMPERATURE = 2.5


def default_weights() -> list[float]:
    # Hand-tuned seed approximating v3 fusion priorities.
    # v6.15.1: stronger spectral mass, slightly softer fts_rank so PPR/heat can move order.
    w = [0.0] * len(FEATURE_NAMES)
    mapping = {
        "thalamus_lane": 0.35,
        "fts_rank": 0.28,
        "vector_sim": 0.40,
        "neural_support": 0.28,
        "is_source": 0.15,
        "is_test": 0.12,
        "prior_score": 0.45,
        "retrieval_confidence": 0.10,
        "path_depth": -0.05,
        "immune_block": -0.20,
        "aria_deferred": -0.15,
        "prefetch_hit": 0.20,
        "hnsw_lane": 0.15,
        "coact_strength": 0.18,
        "kernel_retain": 0.12,
        "kernel_integrate": 0.08,
        "ppr": 0.38,
        "heat": 0.32,
        "degree_centrality": 0.12,
        "lambda2_gap": 0.08,
        "unified_confidence": 0.12,
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
        names = json.loads(row["feature_names_json"])
        weights = json.loads(row["weights_json"])
        defaults = default_weights()
        dirty = False
        # Pad/truncate if feature schema evolved (v6.1)
        if len(weights) < len(FEATURE_NAMES):
            weights = list(weights) + defaults[len(weights) :]
            names = list(FEATURE_NAMES)
            dirty = True
        # Floor spectral weights so de-saturated scoring can reorder (v6.15.1).
        # Never shrink trained weights; only lift undersized ppr/heat toward defaults.
        for feat in ("ppr", "heat", "degree_centrality", "lambda2_gap"):
            try:
                idx = FEATURE_NAMES.index(feat)
            except ValueError:
                continue
            if idx < len(weights) and float(weights[idx]) < float(defaults[idx]):
                weights[idx] = float(defaults[idx])
                dirty = True
        if dirty:
            names = list(FEATURE_NAMES)
            store.db.execute(
                """
                UPDATE ranker_models SET feature_names_json=?, weights_json=?, updated_at=?
                WHERE repo=? AND model_id=?
                """,
                (json.dumps(names), json.dumps(weights), now, repo, MODEL_ID),
            )
            store.db.commit()
        return {
            "model_id": row["model_id"],
            "schema_version": row["schema_version"],
            "weights": weights,
            "bias": float(row["bias"]),
            "train_count": int(row["train_count"]),
            "feature_names": names,
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
    prefetch_hit: bool = False,
    coact_strength: float = 0.0,
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
    hnsw = 1.0 if str(meta.get("source") or meta.get("selection_source") or "") == "hnsw_v1" else 0.0
    if meta.get("hnsw_lane"):
        hnsw = 1.0
    kernel = str(meta.get("kernel_class") or meta.get("retention_regime") or "")
    if not kernel and kind == "discovery_card":
        kernel = "retain"
    # M3/M4/M1 end-to-end: diffusion + unified confidence from metadata when present
    ppr = float(meta.get("ppr") or 0.0)
    heat = float(meta.get("heat") or 0.0)
    deg_c = float(meta.get("degree_centrality") or 0.0)
    lam_gap = float(meta.get("lambda2_gap") or meta.get("lambda2") or 0.0)
    # squash lambda2 into 0..1-ish
    if lam_gap > 1.0:
        lam_gap = min(1.0, lam_gap / 10.0)
    u_conf = float(
        meta.get("unified_confidence")
        if meta.get("unified_confidence") is not None
        else retrieval_confidence
    )
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
        "prefetch_hit": 1.0 if prefetch_hit or meta.get("prefetch_hit") else 0.0,
        "hnsw_lane": hnsw,
        "coact_strength": _clip(float(coact_strength or meta.get("coact_strength") or 0.0), 0.0, 1.0),
        "kernel_retain": 1.0 if kernel == "retain" else 0.0,
        "kernel_integrate": 1.0 if kernel == "integrate" else 0.0,
        "ppr": _clip(ppr, 0.0, 1.0),
        "heat": _clip(heat, 0.0, 1.0),
        "degree_centrality": _clip(deg_c, 0.0, 1.0),
        "lambda2_gap": _clip(lam_gap, 0.0, 1.0),
        "unified_confidence": _clip(u_conf, 0.0, 1.0),
    }
    return [_clip(feats[name], -1.0, 1.0) for name in FEATURE_NAMES]


def logit_score(model: dict[str, Any], features: list[float]) -> float:
    """Linear score z (pre-sigmoid) for de-saturated ranking."""
    weights = model.get("weights") or default_weights()
    bias = float(model.get("bias") or 0.0)
    n = min(len(weights), len(features))
    return bias + sum(float(weights[i]) * float(features[i]) for i in range(n))


def score_features(model: dict[str, Any], features: list[float]) -> float:
    """Absolute 0..1 score with temperature (de-saturated vs unit sigmoid)."""
    z = logit_score(model, features)
    t = max(0.5, float(SCORE_TEMPERATURE))
    return 1.0 / (1.0 + math.exp(-_clip(z / t, -8.0, 8.0)))


def _batch_relative_scores(logits: list[float]) -> list[float]:
    """Map logits to 0..1 within the candidate batch (z-score + soft sigmoid).

    Absolute sigmoid saturates near 1.0 for all hits; relative scores let
    small spectral feature deltas reorder candidates honestly.
    """
    if not logits:
        return []
    if len(logits) == 1:
        return [0.5]
    mean = sum(logits) / len(logits)
    var = sum((z - mean) ** 2 for z in logits) / len(logits)
    std = math.sqrt(var) if var > 1e-12 else 1.0
    # Floor std so tiny noise does not explode; still preserves order.
    std = max(std, 0.35)
    t = max(0.5, float(SCORE_TEMPERATURE))
    out: list[float] = []
    for z in logits:
        rel = (z - mean) / std
        out.append(1.0 / (1.0 + math.exp(-_clip(rel / t, -8.0, 8.0))))
    return out


def rerank_hits(
    store: Any,
    repo: str,
    hits: list[Any],
    *,
    retrieval_confidence: float = 0.0,
    surprise_ratio: float = 0.0,
    immune_block: bool = False,
    primary: bool = True,
    enrich_spectral: bool = True,
) -> list[Any]:
    """Ranker-primary path (v6.13): model score dominates; heuristics are prior features.

    primary=True → final = 0.82 * P(model) + 0.18 * prior (was 0.55/0.45).
    enrich_spectral=True → attach PPR/heat into metadata before features.
    v6.15.1: batch-relative de-saturated model scores so spectral features can reorder.
    """
    if not hits:
        return hits
    if enrich_spectral:
        try:
            from ..math_net.spectral_memory import enrich_hits_with_diffusion

            # Hit objects may be Hit dataclasses — convert path via metadata inject
            enrich_hits_with_diffusion(store, repo, hits)
        except Exception:
            pass
    # Stamp unified confidence for features
    try:
        from ..math_net.uncertainty import compute_uncertainty

        u_pkt = compute_uncertainty(retrieval_confidence=retrieval_confidence)
        u_conf = float(u_pkt.get("confidence") or retrieval_confidence)
    except Exception:
        u_conf = retrieval_confidence

    model = ensure_ranker(store, repo)
    prepared: list[tuple[float, float, Any]] = []
    for i, hit in enumerate(hits):
        if isinstance(hit, dict):
            meta = dict(hit.get("metadata") or {})
            meta["unified_confidence"] = u_conf
            hit = {**hit, "metadata": meta}
        else:
            try:
                md = dict(getattr(hit, "metadata", None) or {})
                md["unified_confidence"] = u_conf
                hit.metadata = md
            except Exception:
                pass
        feats = features_from_hit(
            hit,
            rank=i,
            retrieval_confidence=retrieval_confidence,
            surprise_ratio=surprise_ratio,
            immune_block=immune_block,
        )
        z = logit_score(model, feats)
        prior = 0.0
        if isinstance(hit, dict):
            prior = float(hit.get("score") or 0.0)
        else:
            prior = float(getattr(hit, "score", 0.0) or 0.0)
        prepared.append((z, prior, hit))

    rel_scores = _batch_relative_scores([z for z, _, _ in prepared])
    scored: list[tuple[float, Any]] = []
    for (z, prior, hit), s_rel in zip(prepared, rel_scores):
        s_abs = 1.0 / (
            1.0
            + math.exp(
                -_clip(z / max(0.5, float(SCORE_TEMPERATURE)), -8.0, 8.0)
            )
        )
        if isinstance(hit, dict):
            hit = {
                **hit,
                "ranker_score": round(s_rel, 6),
                "ranker_logit": round(z, 6),
                "ranker_score_abs": round(s_abs, 6),
                "ranker_primary": bool(primary),
                "ranker_desaturated": True,
            }
        else:
            try:
                hit.metadata = {
                    **(hit.metadata or {}),
                    "ranker_score": round(s_rel, 6),
                    "ranker_logit": round(z, 6),
                    "ranker_score_abs": round(s_abs, 6),
                    "ranker_primary": bool(primary),
                    "ranker_desaturated": True,
                }
            except Exception:
                pass
        prior_c = min(1.0, max(0.0, prior))
        # De-saturated model scores need enough prior mass so exact hybrid matches
        # (authoritative headings, path boosts) survive reordering.
        if primary:
            final = 0.68 * s_rel + 0.32 * prior_c
        else:
            final = 0.50 * s_rel + 0.50 * prior_c
        scored.append((final, hit))
    scored.sort(key=lambda x: x[0], reverse=True)

    def _prior_of(hit: Any) -> float:
        if isinstance(hit, dict):
            return float(hit.get("score") or 0.0)
        return float(getattr(hit, "score", 0.0) or 0.0)

    # Soft pin: if hybrid clearly prefers one hit (exact phrase / authoritative),
    # do not let de-saturated model scores bury it below #1.
    if len(scored) > 1:
        best_prior_idx = max(range(len(scored)), key=lambda i: _prior_of(scored[i][1]))
        p_best = _prior_of(scored[best_prior_idx][1])
        p_top = _prior_of(scored[0][1])
        if best_prior_idx > 0 and p_best >= p_top * 1.05 and p_best > 0.0:
            item = scored.pop(best_prior_idx)
            scored.insert(0, item)
    return [h for _, h in scored]


def feature_vectors_from_activation(activation: dict[str, Any]) -> list[list[float]]:
    """Build ranker training vectors from fired activation paths (signal loop)."""

    vectors: list[list[float]] = []
    records = activation.get("records") or []
    paths: list[str] = []
    for rec in records:
        if not isinstance(rec, dict) or not rec.get("fired"):
            continue
        path = rec.get("path") or (rec.get("payload") or {}).get("path")
        if path:
            paths.append(str(path))
    for path in list(activation.get("support_paths") or []) + list(
        activation.get("fired_paths") or []
    ):
        if path and str(path) not in paths:
            paths.append(str(path))
    for i, path in enumerate(paths[:16]):
        p = path.replace("\\", "/")
        kind = "test" if ("test" in p.lower() or "/tests/" in p) else "source"
        if p.endswith(".md"):
            kind = "documentation"
        meta: dict[str, Any] = {}
        if p.startswith("cortex/") and p.endswith(".py"):
            meta["selection_source"] = "implementation_proof"
            meta["prove_implementation"] = True
        vectors.append(
            features_from_hit(
                {
                    "path": p,
                    "kind": kind,
                    "score": max(0.1, 1.0 - i * 0.05),
                    "metadata": meta,
                },
                rank=i,
            )
        )
    if not vectors:
        try:
            vectors.append(
                features_from_hit({"path": "outcome", "score": 0.5, "kind": "source"})
            )
        except Exception:
            # Schema-safe zero vector if feature extraction fails
            vectors.append([0.0] * len(FEATURE_NAMES))
    return vectors


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
        store.set_setting(
            f"ranker_frozen:{repo}",
            {"frozen": True, "reason": "unsafe_outcome", "at": time.time()},
        )
        return {"trained": False, "reason": "unsafe_freezes_ranker", "frozen": True}
    frozen = store.get_setting(f"ranker_frozen:{repo}", {}) or {}
    if frozen.get("frozen"):
        return {"trained": False, "reason": "ranker_frozen", "frozen": True}

    model = ensure_ranker(store, repo)
    label = 1.0 if status in {"verified", "helpful"} else -1.0
    if status == "irrelevant":
        label = -0.5
    base_lr = 0.05 if governance_mode == "normal" else 0.02
    # Fisher-scaled LR (v6.20): step ∝ 1/(1+I_ii) when examples exist.
    fisher = ranker_fisher_diag(store, repo)
    fisher_map = {
        str(r["feature"]): float(r["I_ii"])
        for r in (fisher.get("fisher_diag_top") or [])
        if isinstance(r, dict) and r.get("feature") is not None
    }
    names = list(model.get("feature_names") or FEATURE_NAMES)
    vectors = feature_vectors or [features_from_hit({"score": abs(reward), "path": "outcome"})]
    weights = list(model["weights"])
    bias = float(model["bias"])
    for feats in vectors:
        pred = score_features({"weights": weights, "bias": bias}, feats)
        # logistic loss gradient toward label mapped 0/1
        y = 1.0 if label > 0 else 0.0
        err = pred - y
        for i in range(min(len(weights), len(feats))):
            fname = names[i] if i < len(names) else str(i)
            i_ii = float(fisher_map.get(fname, 0.0))
            lr_i = base_lr / (1.0 + i_ii)
            weights[i] = _clip(weights[i] - lr_i * err * feats[i], -3.0, 3.0)
        bias = _clip(bias - base_lr * err, -2.0, 2.0)

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


def ranker_fisher_diag(store: Any, repo: str, *, limit: int = 64) -> dict[str, Any]:
    """Diagonal Fisher proxy from logged ranker examples (v6.19).

    I_ii ≈ mean[ p(1-p) x_i^2 ] with p = current model score on example features.
    Used to scale learning confidence / shadow promotion — not host authority.
    """
    model = ensure_ranker(store, repo)
    names = list(model.get("feature_names") or FEATURE_NAMES)
    acc = [0.0] * len(names)
    n = 0
    try:
        rows = store.db.execute(
            """
            SELECT feature_vector_json FROM ranker_examples
            WHERE repo=? ORDER BY rowid DESC LIMIT ?
            """,
            (repo, max(1, int(limit))),
        ).fetchall()
    except Exception:
        rows = []
    for row in rows or []:
        try:
            feats = json.loads(row["feature_vector_json"] or "[]")
        except Exception:
            continue
        if not feats:
            continue
        p = score_features(model, feats)
        p = max(1e-6, min(1.0 - 1e-6, float(p)))
        w = p * (1.0 - p)
        for i in range(min(len(names), len(feats))):
            x = float(feats[i])
            acc[i] += w * x * x
        n += 1
    if n <= 0:
        return {
            "ok": False,
            "n_examples": 0,
            "claim_boundary": "No ranker_examples yet; Fisher undefined.",
        }
    diag = [round(a / n, 8) for a in acc]
    top = sorted(
        [{"feature": names[i], "I_ii": diag[i]} for i in range(len(names))],
        key=lambda r: r["I_ii"],
        reverse=True,
    )[:8]
    identified = sum(1 for d in diag if d >= 0.02)
    return {
        "ok": True,
        "n_examples": n,
        "fisher_diag_top": top,
        "identified_features": identified,
        "feature_count": len(names),
        "claim_boundary": (
            "Diagonal Fisher proxy on logged outcomes — information geometry light. "
            "Telemetry for calibration confidence, not consciousness or host rights."
        ),
    }


def ranker_status(store: Any, repo: str) -> dict[str, Any]:
    model = ensure_ranker(store, repo)
    frozen = store.get_setting(f"ranker_frozen:{repo}", {}) or {}
    fisher = ranker_fisher_diag(store, repo)
    return {
        "schema_version": SCHEMA,
        "repo": repo,
        "model_id": model["model_id"],
        "train_count": model["train_count"],
        "feature_count": len(model["feature_names"]),
        "bias": model["bias"],
        "frozen": bool(frozen.get("frozen")),
        "freeze_reason": frozen.get("reason"),
        "fisher": fisher,
        "claim_boundary": "Ranker status is operational telemetry; not host rights.",
    }


def freeze_ranker(store: Any, repo: str, *, reason: str = "manual") -> dict[str, Any]:
    store.set_setting(
        f"ranker_frozen:{repo}",
        {"frozen": True, "reason": reason, "at": time.time()},
    )
    return {"frozen": True, "repo": repo, "reason": reason}


def unfreeze_ranker(store: Any, repo: str) -> dict[str, Any]:
    store.set_setting(
        f"ranker_frozen:{repo}",
        {"frozen": False, "reason": "unfrozen", "at": time.time()},
    )
    return {"frozen": False, "repo": repo}


def snapshot_ranker(store: Any, repo: str) -> dict[str, Any]:
    """Operational snapshot for GCMT promote of ranker weights."""

    model = ensure_ranker(store, repo)
    return {
        "schema_version": "cortex-ranker-snapshot/1.0",
        "model_id": model["model_id"],
        "weights": model["weights"],
        "bias": model["bias"],
        "train_count": model["train_count"],
        "feature_names": model["feature_names"],
        "claim_boundary": "Snapshot is promotable canonical candidate only under GCMT.",
    }


def apply_ranker_snapshot(store: Any, repo: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Restore weights from a promoted/rolled-back snapshot (operational plane)."""

    weights = snapshot.get("weights")
    if not isinstance(weights, list):
        return {"applied": False, "reason": "invalid_snapshot"}
    bias = float(snapshot.get("bias") or 0.0)
    names = snapshot.get("feature_names") or list(FEATURE_NAMES)
    now = time.time()
    ensure_ranker(store, repo)
    store.db.execute(
        """
        UPDATE ranker_models SET weights_json=?, bias=?, feature_names_json=?, updated_at=?
        WHERE repo=? AND model_id=?
        """,
        (json.dumps(weights), bias, json.dumps(names), now, repo, MODEL_ID),
    )
    store.db.commit()
    return {"applied": True, "model_id": MODEL_ID, "train_count": snapshot.get("train_count")}


def promote_ranker_snapshot(
    store: Any,
    repo: str,
    *,
    promotion_authorized: bool = False,
) -> dict[str, Any]:
    """Promote current ranker into canonical via GCMT-style receipt when authorized."""

    if not promotion_authorized:
        return {
            "promoted": False,
            "reason": "promotion_not_authorized",
            "claim_boundary": "Human/host must authorize; ranker never self-promotes.",
        }
    frozen = store.get_setting(f"ranker_frozen:{repo}", {}) or {}
    if frozen.get("frozen"):
        return {"promoted": False, "reason": "ranker_frozen"}
    snap = snapshot_ranker(store, repo)
    from hashlib import sha256

    receipt_id = "rr_" + sha256(f"{repo}|ranker|{time.time()}".encode()).hexdigest()[:20]
    # Store as canonical_states via store API if available
    try:
        store.promote_canonical_state(
            repo,
            receipt_id=receipt_id,
            state_key="ranker:linear_v1",
            candidate=snap,
            evidence=[{"path": "cortex/ranker/model.py", "content_hash": "ranker_snapshot"}],
            verification={"repeatable": True, "bounded": True},
            authority={
                "promotion_authorized": True,
                "level": 3,
                "immune_block": False,
            },
        )
        promoted = True
        detail = {"receipt_id": receipt_id}
    except Exception:
        # Fallback: settings-backed retain snapshot
        store.set_setting(f"ranker_canonical:{repo}", {**snap, "receipt_id": receipt_id})
        promoted = True
        detail = {"receipt_id": receipt_id, "via": "settings_fallback"}
    try:
        store.append_neural_event(
            repo,
            event_type="ranker_promoted",
            entity_id=MODEL_ID,
            payload=detail,
        )
    except Exception:
        pass
    return {"promoted": promoted, **detail, "snapshot": snap}


def rollback_ranker_snapshot(store: Any, repo: str) -> dict[str, Any]:
    """Restore last canonical ranker snapshot if present."""

    canon = store.get_setting(f"ranker_canonical:{repo}", None)
    if not isinstance(canon, dict) or not canon.get("weights"):
        # try canonical_states table
        try:
            row = store.canonical_state(repo, "ranker:linear_v1")
            if row:
                canon = json.loads(row["value_json"])
        except Exception:
            canon = None
    if not isinstance(canon, dict) or not canon.get("weights"):
        return {"rolled_back": False, "reason": "no_canonical_snapshot"}
    applied = apply_ranker_snapshot(store, repo, canon)
    return {"rolled_back": bool(applied.get("applied")), **applied}
