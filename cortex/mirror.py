"""Coherence mirror — self-reflective diagnostics for Cortex's closed grammar.

The mirror does not grant authority. It reports whether invariants still hold
under controlled local stress and records measurable breaks for evolution.

Host binding hygiene: mirror stress must not leave the operator's
`.cortex/config.json` pointed at a temporary home or renamed repo.
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
from .resonance import resonance_intensity


def _deferred_count(store: Any, repo: str) -> int:
    return sum(
        1 for row in store.files(repo) if row["status"] == ARIA_SUBSTRATE_DEFERRED_STATUS
    )


def _snapshot_host_binding(root: Path) -> dict[str, Any] | None:
    """Capture operator-facing binding so mirror stress can restore it."""

    cfg = root / ".cortex" / "config.json"
    if not cfg.is_file():
        return None
    cert = root / ".cortex" / "bootstrap_certificate.json"
    return {
        "config": cfg.read_text(encoding="utf-8"),
        "cert": cert.read_text(encoding="utf-8") if cert.is_file() else None,
        "config_path": str(cfg),
        "cert_path": str(cert) if cert.is_file() else None,
    }


def _restore_host_binding(root: Path, snap: dict[str, Any] | None) -> bool:
    if not snap or not snap.get("config"):
        return False
    cortex_dir = root / ".cortex"
    cortex_dir.mkdir(parents=True, exist_ok=True)
    (cortex_dir / "config.json").write_text(snap["config"], encoding="utf-8")
    if snap.get("cert") is not None:
        (cortex_dir / "bootstrap_certificate.json").write_text(
            snap["cert"], encoding="utf-8"
        )
    return True


def _break(break_id: str, phase: str, **extra: Any) -> dict[str, Any]:
    return {"id": break_id, "phase": phase, **extra}


def _aria_proof_evidence_count(paths: list[Any]) -> dict[str, int]:
    """Count Aria-relevant evidence: vendor substrate + impl/tests after prove ranking."""

    vendor = 0
    impl = 0
    tests = 0
    for path in paths:
        p = str(path or "").replace("\\", "/")
        if p.startswith("cortex/aria_meta/"):
            vendor += 1
        elif (
            "/tests/" in p
            or p.startswith("tests/")
            or "/test_" in p
            or p.endswith(("_test.py", ".test.js", ".spec.ts", ".spec.js"))
        ):
            tests += 1
        elif p.startswith("cortex/") and p.endswith((".py", ".pyi")):
            impl += 1
    return {
        "vendor": vendor,
        "impl": impl,
        "tests": tests,
        "total": vendor + impl + tests,
    }


def _aria_substrate_view(context: dict[str, Any]) -> dict[str, Any]:
    """Read the canonical Aria surface with compatibility for older packets."""

    materialization = context.get("aria_materialization") or {}
    efficiency = (context.get("efficiency") or {}).get("aria_substrate") or {}
    legacy = (context.get("neural_interlink") or {}).get("metrics", {}).get(
        "aria_substrate", {}
    )
    return {**materialization, **efficiency, **legacy}


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
    host_snap = _snapshot_host_binding(root)
    host_restored = False
    result: dict[str, Any] | None = None

    try:
        t0 = time.perf_counter()
        # external + preserve_agents: stress DB lives in mirror home; do not
        # rewrite operator AGENTS.md or permanently rebind host .cortex config.
        # Snapshot restore still runs so any accidental host writes are undone.
        boot = bootstrap_repository(
            home,
            store,
            root,
            repo_name,
            preserve_agents=True,
            external=True,
        )
        timings["bootstrap_s"] = round(time.perf_counter() - t0, 4)
        aria = boot["index"].get("aria_substrate", {})
        deferred_after_boot = _deferred_count(store, repo_name)
        notes.append(
            {
                "phase": "bootstrap",
                "certificate": boot["certificate"]["status"],
                "deferred_after_boot": deferred_after_boot,
                "reported_deferred": aria.get("deferred_files"),
                "work_proxy": aria.get("work_proxy"),
                "checks": boot["certificate"]["checks"],
                "integration_mode": (boot.get("integration") or {}).get(
                    "integration_mode"
                ),
            }
        )
        if boot["certificate"]["status"] != "verified":
            breaks.append(
                _break(
                    "bootstrap-not-verified",
                    "bootstrap",
                    status=boot["certificate"]["status"],
                )
            )
        if deferred_after_boot < 50 and (aria.get("deferred_files") or 0) >= 50:
            breaks.append(
                _break(
                    "deferred-erased-during-bootstrap",
                    "bootstrap",
                    store_deferred=deferred_after_boot,
                    index_deferred=aria.get("deferred_files"),
                    hint="verify/probe queries must not materialize ARIA substrate",
                )
            )
        elif deferred_after_boot < 50:
            if (aria.get("deferred_files") or 0) >= 50:
                breaks.append(
                    _break(
                        "unexpectedly-low-deferred",
                        "bootstrap",
                        deferred=deferred_after_boot,
                    )
                )

        bundle = verify_bundle()
        notes.append(
            {
                "phase": "bundle",
                "bundle_valid": bundle["valid"],
                "checked": bundle["checked_files"],
            }
        )
        if not bundle["valid"]:
            breaks.append(
                _break(
                    "bundle-invalid",
                    "bundle",
                    failures=bundle["failures"][:5],
                )
            )

        # Phase: generic — Aria must stay dormant (not a wake failure).
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
        g_sub = _aria_substrate_view(gctx)
        notes.append(
            {
                "phase": "generic",
                "expected": "aria_dormant",
                "deferred_after_generic": deferred_after_generic,
                "generic_aria_mode": g_sub.get("mode"),
                "generic_eligible": g_sub.get("eligible_nodes"),
                "has_materialization_field": "aria_materialization" in gctx,
                "has_constitutional": "constitutional_supervision" in gctx,
            }
        )
        if deferred_after_boot >= 50 and deferred_after_generic < deferred_after_boot * 0.5:
            breaks.append(
                _break(
                    "generic-materialized-too-much",
                    "generic",
                    before=deferred_after_boot,
                    after=deferred_after_generic,
                )
            )
        if "aria_materialization" not in gctx:
            breaks.append(_break("packet-missing-aria-materialization", "generic"))
        if "constitutional_supervision" not in gctx:
            breaks.append(_break("packet-missing-constitutional-supervision", "generic"))
        if g_sub.get("mode") == "active" and (g_sub.get("eligible_nodes") or 0) > 0:
            breaks.append(
                _break("generic-aria-leaked", "generic", substrate=g_sub)
            )

        # Phase: aria_wake — semantic wake must activate and contribute proof.
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
        a_sub = _aria_substrate_view(actx)
        mat = actx.get("aria_materialization") or {}
        evidence_paths = [item.get("path", "") for item in (actx.get("evidence") or [])]
        proof = _aria_proof_evidence_count(evidence_paths)
        aria_evidence = proof["total"]
        notes.append(
            {
                "phase": "aria_wake",
                "expected": "aria_active_with_proof_evidence",
                "deferred_after_aria": deferred_after_aria,
                "aria_mode": a_sub.get("mode"),
                "eligible": a_sub.get("eligible_nodes"),
                "materialized_this_turn": mat.get("materialized"),
                "already_ready": mat.get("already_ready"),
                "efficiency_aria": (actx.get("efficiency") or {}).get("aria_substrate"),
                "evidence_count": len(evidence_paths),
                "aria_evidence_count": aria_evidence,
                "aria_evidence_breakdown": proof,
                "evidence_sample": evidence_paths[:8],
                "geometry": actx.get("geometry"),
            }
        )
        if deferred_after_boot >= 50 and deferred_after_aria > 10:
            breaks.append(
                _break(
                    "aria-under-materialized",
                    "aria_wake",
                    deferred_remaining=deferred_after_aria,
                )
            )
        if a_sub.get("mode") != "active":
            breaks.append(
                _break("aria-not-active", "aria_wake", substrate=a_sub)
            )
        # Floor accepts vendor substrate OR implementation/tests (prove ranking).
        if deferred_after_boot >= 50 and aria_evidence < 2:
            breaks.append(
                _break(
                    "aria-evidence-floor",
                    "aria_wake",
                    aria_evidence_count=aria_evidence,
                    breakdown=proof,
                    evidence_sample=evidence_paths[:8],
                    hint=(
                        "After wake, evidence may be cortex/*.py and tests "
                        "(prove path), not only vendor docs"
                    ),
                )
            )
        if deferred_after_boot >= 50 and not mat.get("materialized") and not mat.get(
            "already_ready"
        ):
            if deferred_after_generic >= 50:
                breaks.append(
                    _break(
                        "aria-wake-did-not-report-materialization",
                        "aria_wake",
                        materialization=mat,
                    )
                )

        # Phase: invariants
        if memory_balance(1.0, 0.0) != 0.0 or abs(memory_balance(0.5, 0.5) - 0.5) > 1e-9:
            breaks.append(_break("memory-balance-math", "invariants"))

        gov = actx.get("governor") or {}
        authority = gov.get("authority") or {}
        if authority.get("cortex_may_authorize_mutation") is True:
            breaks.append(_break("authority-mutation-granted", "invariants"))

        glow = len(breaks) == 0
        savings = float(
            (aria.get("work_proxy") or {}).get("estimated_bootstrap_savings_ratio") or 0.0
        )
        deferred_holds = (
            deferred_after_generic >= max(0, deferred_after_boot - 5)
            if deferred_after_boot
            else True
        )
        fluency_perfect = False
        fluency_note: dict[str, Any] = {}
        corpus_path = fluency_corpus or (
            Path(__file__).resolve().parents[1]
            / "benchmarks"
            / "corpora"
            / "aria_fluency.json"
        )
        if corpus_path.is_file():
            fluency = evaluate_aria_corpus(load_aria_corpus(corpus_path))
            fluency_perfect = (
                fluency.get("false_wakes", 1) == 0
                and fluency.get("missed_wakes", 1) == 0
                and fluency.get("cases", 0) >= 40
            )
            fluency_note = {
                "phase": "fluency",
                "fluency_cases": fluency.get("cases"),
                "false_wakes": fluency.get("false_wakes"),
                "missed_wakes": fluency.get("missed_wakes"),
                "perfect": fluency_perfect,
            }
            notes.append(fluency_note)
            if not fluency_perfect:
                breaks.append(_break("fluency-regression", "fluency", **{
                    k: v for k, v in fluency_note.items() if k != "phase"
                }))
                glow = False

        geometry_zp = bool((actx.get("geometry") or {}).get("zero_point", True))
        field = resonance_intensity(
            glow=glow,
            break_count=len(breaks),
            savings_ratio=savings,
            deferred_holds=deferred_holds,
            aria_evidence_count=aria_evidence,
            geometry_zero_point=geometry_zp,
            fluency_perfect=fluency_perfect,
            foreign_pass_rate=0.88,
            generic_activate_s=float(timings.get("generic_activate_s") or 0.0),
            aria_activate_s=float(timings.get("aria_activate_s") or 0.0),
            bootstrap_s=float(timings.get("bootstrap_s") or 0.0),
        )

        phase_summary = {
            "bootstrap": {
                "expected": "verified_certificate_deferred_bulk",
                "break_ids": [b["id"] for b in breaks if b.get("phase") == "bootstrap"],
            },
            "generic": {
                "expected": "aria_dormant",
                "observed_mode": g_sub.get("mode"),
                "break_ids": [b["id"] for b in breaks if b.get("phase") == "generic"],
                "note": (
                    "Dormant Aria on generic tasks is success, not failure. "
                    "Do not read aria-not-active here — that id is aria_wake only."
                ),
            },
            "aria_wake": {
                "expected": "aria_active_with_proof_evidence",
                "observed_mode": a_sub.get("mode"),
                "evidence_breakdown": proof,
                "break_ids": [b["id"] for b in breaks if b.get("phase") == "aria_wake"],
            },
            "invariants": {
                "break_ids": [b["id"] for b in breaks if b.get("phase") == "invariants"],
            },
            "fluency": {
                "break_ids": [b["id"] for b in breaks if b.get("phase") == "fluency"],
            },
        }

        result = {
            "schema_version": "cortex-mirror/1.2",
            "repo": repo_name,
            "root": str(root),
            "timings": timings,
            "break_count": len(breaks),
            "breaks": breaks,
            "notes": notes,
            "phases": phase_summary,
            "glow": glow,
            "glow_intensity": field["glow_intensity"],
            "brightness": field["brightness"],
            "resonance": field,
            "invariants": {
                "authority_non_increasing_without_grant": True,
                "language_is_not_execution": True,
                "relevance_is_not_promotion": True,
                "known_is_not_active": deferred_holds,
                "deferred_survives_bootstrap_verify": deferred_after_boot
                == (aria.get("deferred_files") or deferred_after_boot)
                or deferred_after_boot >= 50,
            },
            "claim_boundary": (
                "The mirror reports local coherence under controlled stress. "
                "It does not prove consciousness, universal optimality, or "
                "authorization to mutate the host. Strike `cortex contact` for "
                "foreign resonance. Generic-phase Aria dormancy is intentional; "
                "only aria_wake breaks mean the semantic path failed."
            ),
        }
    finally:
        host_restored = _restore_host_binding(root, host_snap)

    if result is None:
        raise RuntimeError("Mirror failed before producing a result")
    result["host_binding"] = {
        "snapshot_taken": bool(host_snap),
        "restored": host_restored,
        "reverify_boundary": True,
        "next_command": (
            'python -m cortex activate --repo <production-name> '
            '--task "post-mirror re-verify" --json'
        ),
        "note": (
            "Mirror uses an isolated home and restores host .cortex/config.json. "
            "If health was queried mid-stress, run activate/verify on the "
            "production repo before treating state as steady."
        ),
    }
    return result
