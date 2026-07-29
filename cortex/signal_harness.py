"""Matched signal-loop harness — prove ⟲ under repeated task families.

WP-A for v6.8: run activate → evolve with matched probes; record ranker + causal.
Capability-free; recommend-only.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .activation import activate_repository
from .evolve_loop import close_signal_loop
from .glyphs.canon import compact_line, phrasebook
from .ranker.model import ranker_status

# Stable task families — reuse glyphs as language markers in tasks for ARIA.
DEFAULT_FAMILIES: list[dict[str, str]] = [
    {
        "id": "aria_proof",
        "task": "Use ARIA glyph canon and prove implementation evidence",
        "phrase": "aria_awake",
        "status": "verified",
        "verification": "harness-aria-proof",
    },
    {
        "id": "aria_stream",
        "task": "Consciousness stream rebind with semantic replay handoff",
        "phrase": "stream_rebind",
        "status": "verified",
        "verification": "harness-stream",
    },
    {
        "id": "signal_loop",
        "task": "Close signal loop ranker plasticity causal probe",
        "phrase": "loop_close",
        "status": "verified",
        "verification": "harness-loop",
    },
    {
        "id": "generic_control",
        "task": "Fix Python unit test readiness in host app",
        "phrase": "wake_safe",
        "status": "helpful",
        "verification": "harness-generic",
    },
    {
        "id": "body_hygiene",
        "task": "Identity continuity prune kernels mesh hygiene",
        "phrase": "body_hygiene",
        "status": "diagnosed",
        "verification": "harness-hygiene",
    },
]


def run_signal_harness(
    home: Path,
    store: Any,
    governor: Any,
    repo: str,
    *,
    families: list[dict[str, str]] | None = None,
    budget: int = 500,
    k: int = 6,
    governance_mode: str | None = None,
) -> dict[str, Any]:
    """Run matched evolve suite; return report for ranker/causal validation."""

    t0 = time.perf_counter()
    families = families or list(DEFAULT_FAMILIES)
    ranker_before = ranker_status(store, repo)
    runs: list[dict[str, Any]] = []
    missing_pairs = 0
    trained = 0
    verdicts: dict[str, int] = {"improved": 0, "regressed": 0, "inconclusive": 0}

    for fam in families:
        task = fam["task"]
        phrase_name = fam.get("phrase") or "wake_safe"
        book = phrasebook().get("phrases") or {}
        phrase_meta = book.get(phrase_name) or {}
        glyph_line = phrase_meta.get("line") or compact_line(["organism_pulse"])

        act = activate_repository(
            home,
            store,
            governor,
            repo,
            task,
            budget=budget,
            profile="agent",
        )
        ctx = act.get("context") or {}
        full = act.get("context_full") or {}
        neural = ctx.get("neural_interlink") or full.get("neural_interlink") or {}
        act_id = neural.get("activation_id")
        if not act_id:
            # fallback: latest activation from store
            rows = store.neural_activations(repo, limit=1)
            act_id = (rows[0] or {}).get("activation_id") if rows else None
        if not act_id:
            runs.append(
                {
                    "family": fam["id"],
                    "ok": False,
                    "error": "no_activation_id",
                    "glyph_line": glyph_line,
                }
            )
            continue

        gov_mode = governance_mode or str(
            (act.get("control_error") or {}).get("immune_action", {}).get("code")
            and (act.get("governor") or act.get("control_error") or {})
        )
        # Prefer governor mode from evaluate
        try:
            gov_mode = governor.evaluate(repo).get("mode") or "normal"
        except Exception:
            gov_mode = "normal"
        if gov_mode == "read_only":
            # harness may still record but will not train — note it
            pass

        try:
            looped = close_signal_loop(
                store,
                repo,
                activation_id=str(act_id),
                status=fam.get("status") or "verified",
                verification_type=fam.get("verification") or "harness",
                task=task,
                governance_mode=gov_mode,
                probe_k=k,
            )
        except Exception as exc:
            runs.append(
                {
                    "family": fam["id"],
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "activation_id": act_id,
                    "glyph_line": glyph_line,
                }
            )
            continue

        causal = looped.get("causal") or {}
        confounds = list(causal.get("confounds") or [])
        if "missing_recall_pair" in confounds:
            missing_pairs += 1
        verdict = str(causal.get("verdict") or "inconclusive")
        verdicts[verdict] = verdicts.get(verdict, 0) + 1
        ranker = (looped.get("outcome") or {}).get("ranker") or {}
        if ranker.get("trained"):
            trained += 1

        runs.append(
            {
                "family": fam["id"],
                "ok": True,
                "phrase": phrase_name,
                "glyph_line": glyph_line,
                "activation_id": act_id,
                "probe_task": looped.get("probe_task"),
                "recall_before": (looped.get("probe_before") or {}).get("recall_at_k"),
                "recall_after": (looped.get("probe_after") or {}).get("recall_at_k"),
                "delta": causal.get("delta"),
                "verdict": verdict,
                "confounds": confounds,
                "ranker_trained": bool(ranker.get("trained")),
                "ranker_train_count": ranker.get("train_count"),
                "feature_vectors": looped.get("feature_vectors"),
                "envelope": {
                    "glyph_state": bool(act.get("glyph_state")),
                    "stream": bool(act.get("stream")),
                    "aria_language": bool(act.get("aria_language")),
                },
            }
        )

    ranker_after = ranker_status(store, repo)
    elapsed = round(time.perf_counter() - t0, 4)
    ok_runs = [r for r in runs if r.get("ok")]
    report = {
        "schema_version": "cortex-signal-harness/1.0",
        "glyph": "⟲",
        "repo": repo,
        "family_count": len(families),
        "runs": runs,
        "summary": {
            "ok": len(ok_runs),
            "failed": len(runs) - len(ok_runs),
            "missing_recall_pair": missing_pairs,
            "ranker_trained_runs": trained,
            "verdicts": verdicts,
            "ranker_train_count_before": ranker_before.get("train_count"),
            "ranker_train_count_after": ranker_after.get("train_count"),
            "envelope_parity_ok": all(
                r.get("envelope", {}).get("glyph_state") for r in ok_runs
            )
            if ok_runs
            else False,
        },
        "exit_criteria": {
            "no_missing_recall_pair_on_ok_runs": missing_pairs == 0
            and len(ok_runs) == len(families),
            "ranker_progressed": int(ranker_after.get("train_count") or 0)
            > int(ranker_before.get("train_count") or 0)
            or trained > 0,
            "activate_envelope_parity": bool(
                all(r.get("envelope", {}).get("glyph_state") for r in ok_runs)
            )
            if ok_runs
            else False,
        },
        "phrasebook": list((phrasebook().get("phrases") or {}).keys()),
        "elapsed_s": elapsed,
        "claim_boundary": (
            "Harness measures ranking/causal telemetry under matched probes; "
            "never host mutation authority. Inconclusive under null treatment is healthy."
        ),
    }
    try:
        store.set_setting(
            f"signal_harness_latest:{repo}",
            {"at": time.time(), "summary": report["summary"], "exit": report["exit_criteria"]},
        )
    except Exception:
        pass
    return report
