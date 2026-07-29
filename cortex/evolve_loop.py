"""Close the signal loop: probe → outcome → ranker/plasticity → probe → causal.

Glyph ⟲. Recommend-only; never host.mutate.
"""

from __future__ import annotations

import time
from typing import Any

from .causal.ledger import evaluate_causal_episode, probe_recall
from .glyphs.canon import encode_state, glyph_canon_registry
from .learning.outcomes import record_outcome
from .ranker.model import feature_vectors_from_activation


def close_signal_loop(
    store: Any,
    repo: str,
    *,
    activation_id: str,
    status: str,
    verification_type: str,
    task: str | None = None,
    reward: float | None = None,
    governance_mode: str = "normal",
    verification_payload: dict[str, Any] | None = None,
    probe_k: int = 8,
) -> dict[str, Any]:
    """Full closed loop for signal intelligence.

    1. Optional causal probe (before)
    2. record_outcome → plasticity + ranker (with real path features)
    3. Optional causal probe (after)
    4. Causal evaluate with matched pair when probes ran
    5. Glyph-encoded result line
    """

    t0 = time.perf_counter()
    activation = store.neural_activation(repo, activation_id)
    if not activation:
        raise ValueError(f"Unknown activation_id for repo {repo}: {activation_id}")

    probe_task = (task or "").strip() or str(
        activation.get("task") or activation.get("query") or "signal loop probe"
    )
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    try:
        before = probe_recall(
            store, repo, probe_task, k=probe_k, slot="before", materialize_substrate=True
        )
    except Exception as exc:
        before = {"error": f"{type(exc).__name__}: {exc}", "slot": "before"}

    # Inject feature vectors for ranker via store setting consumed by record_outcome
    vectors = feature_vectors_from_activation(activation)
    store.set_setting(
        f"ranker_pending_features:{repo}:{activation_id}",
        {"vectors": vectors, "at": time.time()},
    )

    outcome = record_outcome(
        store,
        repo,
        activation_id,
        status=status,
        verification_type=verification_type,
        reward=reward,
        verification_payload={
            **(verification_payload or {}),
            "signal_loop": True,
            "probe_task": probe_task,
        },
        governance_mode=governance_mode,
        feature_vectors=vectors,
        skip_auto_causal=True,
    )

    try:
        after = probe_recall(
            store, repo, probe_task, k=probe_k, slot="after", materialize_substrate=True
        )
    except Exception as exc:
        after = {"error": f"{type(exc).__name__}: {exc}", "slot": "after"}

    causal: dict[str, Any]
    try:
        rb = None if not before or "error" in before else before.get("recall_at_k")
        ra = None if not after or "error" in after else after.get("recall_at_k")
        causal = evaluate_causal_episode(
            store,
            repo,
            recall_before=float(rb) if rb is not None else None,
            recall_after=float(ra) if ra is not None else None,
        )
    except Exception as exc:
        causal = {"error": f"{type(exc).__name__}: {exc}", "verdict": "inconclusive"}

    loop_meta = {
        "closed": True,
        "verdict": causal.get("verdict"),
        "delta": causal.get("delta"),
    }
    glyph_state = encode_state(
        control={"ok": True, "block": False},
        governor={"mode": governance_mode},
        aria={"mode": "dormant"},
        loop=loop_meta,
    )
    elapsed = round(time.perf_counter() - t0, 4)

    # Ledger note
    try:
        store.append_neural_event(
            repo,
            event_type="signal_loop_closed",
            entity_id=outcome.get("outcome_id") or activation_id,
            payload={
                "verdict": causal.get("verdict"),
                "ranker": (outcome.get("ranker") or {}).get("trained"),
                "plasticity": outcome.get("accepted_updates"),
                "glyph_line": glyph_state.get("line"),
            },
        )
    except Exception:
        pass

    return {
        "schema_version": "cortex-signal-loop/1.0",
        "glyph": "⟲",
        "repo": repo,
        "activation_id": activation_id,
        "probe_task": probe_task,
        "probe_before": before,
        "outcome": outcome,
        "probe_after": after,
        "causal": causal,
        "feature_vectors": len(vectors),
        "glyph_state": glyph_state,
        "canon": {
            "schema": glyph_canon_registry()["schema_version"],
            "glyph": "◈",
        },
        "elapsed_s": elapsed,
        "claim_boundary": (
            "Signal loop adapts internal ranker/plasticity only; "
            "causal verdicts recommend rollbacks; never host mutation rights."
        ),
    }
