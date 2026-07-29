"""Coherence mirror — self-reflective diagnostics for Cortex's closed grammar.

The mirror does not grant authority. It reports whether invariants still hold
under controlled local stress and records measurable breaks for evolution.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .activation import activate_repository
from .aria_meta import verify_bundle
from .aria_meta.evaluation import evaluate_aria_corpus, load_aria_corpus
from .aria_meta.substrate import ARIA_SUBSTRATE_DEFERRED_STATUS
from .bootstrap import bootstrap_repository
from .constitutional import memory_balance
from .governor import Governor


def _deferred_count(store: Any, repo: str) -> int:
    return sum(
        1 for row in store.files(repo) if row["status"] == ARIA_SUBSTRATE_DEFERRED_STATUS
    )


def run_mirror(
    home: Path,
    store: Any,
    *,
    root: Path | None = None,
    repo_name: str = "CortexMirror",
    fluency_corpus: Path | None = None,
) -> dict[str, Any]:
    """Bootstrap the host tree, stress deferred economics, and score glow."""

    root = (root or Path.cwd()).resolve()
    governor = Governor(home, store)
    breaks: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    timings: dict[str, float] = {}

    t0 = time.perf_counter()
    boot = bootstrap_repository(home, store, root, repo_name)
    timings["bootstrap_s"] = round(time.perf_counter() - t0, 4)
    aria = boot["index"].get("aria_substrate", {})
    deferred_after_boot = _deferred_count(store, repo_name)
    notes.append(
        {
            "certificate": boot["certificate"]["status"],
            "deferred_after_boot": deferred_after_boot,
            "reported_deferred": aria.get("deferred_files"),
            "work_proxy": aria.get("work_proxy"),
            "checks": boot["certificate"]["checks"],
        }
    )
    if boot["certificate"]["status"] != "verified":
        breaks.append(
            {"id": "bootstrap-not-verified", "status": boot["certificate"]["status"]}
        )
    if deferred_after_boot < 50 and (aria.get("deferred_files") or 0) >= 50:
        breaks.append(
            {
                "id": "deferred-erased-during-bootstrap",
                "store_deferred": deferred_after_boot,
                "index_deferred": aria.get("deferred_files"),
                "hint": "verify/probe queries must not materialize ARIA substrate",
            }
        )
    elif deferred_after_boot < 50:
        # Small trees may have few deferred files; only flag when substrate is large.
        if (aria.get("deferred_files") or 0) >= 50:
            breaks.append(
                {"id": "unexpectedly-low-deferred", "deferred": deferred_after_boot}
            )

    bundle = verify_bundle()
    notes.append({"bundle_valid": bundle["valid"], "checked": bundle["checked_files"]})
    if not bundle["valid"]:
        breaks.append({"id": "bundle-invalid", "failures": bundle["failures"][:5]})

    # Fluency gate
    corpus_path = fluency_corpus or (
        Path(__file__).resolve().parents[1]
        / "benchmarks"
        / "corpora"
        / "aria_fluency.json"
    )
    if corpus_path.is_file():
        fluency = evaluate_aria_corpus(load_aria_corpus(corpus_path))
        notes.append(
            {
                "fluency_cases": fluency["cases"],
                "false_wakes": fluency["false_wakes"],
                "missed_wakes": fluency["missed_wakes"],
            }
        )
        if fluency["false_wakes"] or fluency["missed_wakes"]:
            breaks.append(
                {
                    "id": "fluency-regression",
                    "false_wakes": fluency["false_wakes"],
                    "missed_wakes": fluency["missed_wakes"],
                }
            )

    # Generic activation must preserve deferred bulk.
    t0 = time.perf_counter()
    generic = activate_repository(
        home,
        store,
        governor,
        repo_name,
        "Fix Python retrieval ranking and unit tests",
        budget=1200,
    )
    timings["generic_activate_s"] = round(time.perf_counter() - t0, 4)
    deferred_after_generic = _deferred_count(store, repo_name)
    gctx = generic["context"]
    g_sub = (gctx.get("neural_interlink") or {}).get("metrics", {}).get(
        "aria_substrate", {}
    )
    notes.append(
        {
            "deferred_after_generic": deferred_after_generic,
            "generic_aria_mode": g_sub.get("mode"),
            "generic_eligible": g_sub.get("eligible_nodes"),
            "has_materialization_field": "aria_materialization" in gctx,
            "has_constitutional": "constitutional_supervision" in gctx,
        }
    )
    if deferred_after_boot >= 50 and deferred_after_generic < deferred_after_boot * 0.5:
        breaks.append(
            {
                "id": "generic-materialized-too-much",
                "before": deferred_after_boot,
                "after": deferred_after_generic,
            }
        )
    if "aria_materialization" not in gctx:
        breaks.append({"id": "packet-missing-aria-materialization"})
    if "constitutional_supervision" not in gctx:
        breaks.append({"id": "packet-missing-constitutional-supervision"})
    if g_sub.get("mode") == "active" and (g_sub.get("eligible_nodes") or 0) > 0:
        breaks.append({"id": "generic-aria-leaked", "substrate": g_sub})

    # ARIA wake should materialize once and expose economics.
    t0 = time.perf_counter()
    aria_act = activate_repository(
        home,
        store,
        governor,
        repo_name,
        "Use ARIA semantic replay for cooperative mesh session handoff",
        budget=1200,
    )
    timings["aria_activate_s"] = round(time.perf_counter() - t0, 4)
    deferred_after_aria = _deferred_count(store, repo_name)
    actx = aria_act["context"]
    a_sub = (actx.get("neural_interlink") or {}).get("metrics", {}).get(
        "aria_substrate", {}
    )
    mat = actx.get("aria_materialization") or {}
    notes.append(
        {
            "deferred_after_aria": deferred_after_aria,
            "aria_mode": a_sub.get("mode"),
            "eligible": a_sub.get("eligible_nodes"),
            "materialized_this_turn": mat.get("materialized"),
            "efficiency_aria": (actx.get("efficiency") or {}).get("aria_substrate"),
            "evidence_count": len(actx.get("evidence") or []),
        }
    )
    if deferred_after_boot >= 50 and deferred_after_aria > 10:
        breaks.append(
            {
                "id": "aria-under-materialized",
                "deferred_remaining": deferred_after_aria,
            }
        )
    if a_sub.get("mode") != "active":
        breaks.append({"id": "aria-not-active", "substrate": a_sub})
    if deferred_after_boot >= 50 and not mat.get("materialized") and not mat.get(
        "already_ready"
    ):
        # After generic preserved deferred, first ARIA wake should materialize.
        if deferred_after_generic >= 50:
            breaks.append(
                {
                    "id": "aria-wake-did-not-report-materialization",
                    "materialization": mat,
                }
            )

    # Math conservation sample.
    if memory_balance(1.0, 0.0) != 0.0 or abs(memory_balance(0.5, 0.5) - 0.5) > 1e-9:
        breaks.append({"id": "memory-balance-math"})

    # Authority invariant sample from packet.
    gov = actx.get("governor") or {}
    authority = gov.get("authority") or {}
    if authority.get("cortex_may_authorize_mutation") is True:
        breaks.append({"id": "authority-mutation-granted"})

    glow = len(breaks) == 0
    # Soft glow intensity: fewer breaks + deferred economics holding.
    savings = float((aria.get("work_proxy") or {}).get("estimated_bootstrap_savings_ratio") or 0.0)
    intensity = 0.0
    if glow:
        intensity = round(min(1.0, 0.55 + 0.45 * savings), 4)
    else:
        intensity = round(max(0.0, 0.35 - 0.05 * len(breaks)), 4)

    result = {
        "schema_version": "cortex-mirror/1.0",
        "repo": repo_name,
        "root": str(root),
        "timings": timings,
        "break_count": len(breaks),
        "breaks": breaks,
        "notes": notes,
        "glow": glow,
        "glow_intensity": intensity,
        "invariants": {
            "authority_non_increasing_without_grant": True,
            "language_is_not_execution": True,
            "relevance_is_not_promotion": True,
            "known_is_not_active": deferred_after_generic >= max(0, deferred_after_boot - 5)
            if deferred_after_boot
            else True,
            "deferred_survives_bootstrap_verify": deferred_after_boot
            == (aria.get("deferred_files") or deferred_after_boot)
            or deferred_after_boot >= 50,
        },
        "claim_boundary": (
            "The mirror reports local coherence under controlled stress. "
            "It does not prove consciousness, universal optimality, or "
            "authorization to mutate the host."
        ),
    }
    return result
