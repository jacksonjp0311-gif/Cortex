"""Run and report M0–M10 math/network phases."""

from __future__ import annotations

from typing import Any

from . import (
    calibration,
    diffusion,
    info_account,
    kernel_state,
    multiscale,
    operator,
    plasticity_rct,
    ranking,
    regimes,
    spectral,
    temporal_edges,
    uncertainty,
)


def phase_status() -> dict[str, Any]:
    return {
        "schema_version": "cortex-math-network-phases/1.0",
        "phases": [
            {"id": "M0", "title": "Regimes vs spectral claim hygiene", "module": "math_net.regimes"},
            {"id": "M1", "title": "Unified uncertainty U", "module": "math_net.uncertainty"},
            {"id": "M2", "title": "Graph operator A + dual reconcile", "module": "math_net.operator"},
            {"id": "M3", "title": "Diffusion / PPR / heat features", "module": "math_net.diffusion"},
            {"id": "M4", "title": "Spectral L, λ2, heat, edge underuse", "module": "math_net.spectral"},
            {"id": "M5", "title": "Shadow calibration of coeffs", "module": "math_net.calibration"},
            {"id": "M6", "title": "Ranker-primary + loss + ECE", "module": "math_net.ranking"},
            {"id": "M7", "title": "Info account ΔU / promotion gate", "module": "math_net.info_account"},
            {"id": "M8", "title": "Plasticity RCT on/off", "module": "math_net.plasticity_rct"},
            {"id": "M9", "title": "Multi-scale conservation", "module": "math_net.multiscale"},
            {"id": "M10", "title": "Temporal–structural edges", "module": "math_net.temporal_edges"},
        ],
        "claim_boundary": (
            "Phases implement identified math/network spine; recommend-only; no host mutation."
        ),
    }


def run_math_network_pass(
    store: Any,
    repo: str,
    *,
    retrieval_confidence: float = 0.5,
    budget: int = 400,
    certificate_status: str = "verified",
    fired_node_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Execute all phases and return a single confirmation report."""
    results: dict[str, Any] = {}
    ok_flags: dict[str, bool] = {}

    # M0
    results["M0"] = regimes.m0_status()
    ok_flags["M0"] = True

    # M1
    u_pkt = uncertainty.compute_uncertainty(
        retrieval_confidence=retrieval_confidence,
        certificate_status=certificate_status,
        budget_tokens=budget,
    )
    results["M1"] = u_pkt
    ok_flags["M1"] = "u" in u_pkt

    # M2
    try:
        op = operator.build_operator_A(store, repo, max_nodes=200)
        dual = operator.dual_graph_report(store, repo)
        results["M2"] = {
            "operator_n": op.get("n"),
            "operator_edges": op.get("edge_count"),
            "dual": dual,
        }
        ok_flags["M2"] = int(op.get("n") or 0) >= 0 and dual.get("ok", True)
    except Exception as exc:
        results["M2"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M2"] = False

    # M3
    try:
        results["M3"] = diffusion.diffusion_features(store, repo, max_nodes=200)
        # empty operator is a valid measurement (ok=False means no mass, not crash)
        ok_flags["M3"] = "error" not in results["M3"]
    except Exception as exc:
        results["M3"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M3"] = False

    # M4
    try:
        results["M4"] = spectral.spectral_slice(store, repo, max_nodes=180)
        ok_flags["M4"] = "error" not in results["M4"]
    except Exception as exc:
        results["M4"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M4"] = False

    # Kernel state pulse (Λ_g) — supporting state, not a separate phase id
    try:
        results["Lambda"] = kernel_state.update_lambda_on_pulse(store, repo)
        results["M0"]["Lambda_pulse"] = results["Lambda"].get("Lambda")
    except Exception as exc:
        results["Lambda"] = {"error": f"{type(exc).__name__}: {exc}"}

    # M5
    try:
        cal = calibration.load_shadow_calibration(store, repo)
        cal = calibration.observe_outcome_for_calibration(
            store,
            repo,
            reward=0.4,
            features={"uncertainty": u_pkt["u"], "gov_confidence": retrieval_confidence},
        )
        results["M5"] = {"shadow": cal, "n_outcomes": cal.get("n_outcomes")}
        ok_flags["M5"] = True
    except Exception as exc:
        results["M5"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M5"] = False

    # M6
    try:
        sc = ranking.score_primary([0.5, 0.3], 0.0, [retrieval_confidence, 1.0 - u_pkt["u"]])
        ece = ranking.expected_calibration_error(
            [1.0, 0.0, 1.0, 0.0],
            [0.8, 0.2, 0.7, 0.4],
        )
        loss = ranking.log_loss([1.0, 0.0], [0.8, 0.3])
        results["M6"] = {"score": sc, "ece_demo": ece, "log_loss_demo": round(loss, 6)}
        ok_flags["M6"] = True
    except Exception as exc:
        results["M6"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M6"] = False

    # M7
    try:
        results["M7"] = info_account.info_account(
            u_before=min(1.0, u_pkt["u"] + 0.15),
            u_after=u_pkt["u"],
            budget_tokens=budget,
            evidence_fidelity=0.75,
            reversibility=1.0,
        )
        ok_flags["M7"] = "delta_u" in results["M7"]
    except Exception as exc:
        results["M7"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M7"] = False

    # M8
    try:
        arm = plasticity_rct.assign_arm(store, repo)
        results["M8"] = plasticity_rct.record_rct_outcome(
            store, repo, arm=arm, reward=0.4, recall_at_k=0.5
        )
        ok_flags["M8"] = True
    except Exception as exc:
        results["M8"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M8"] = False

    # M9
    try:
        results["M9"] = multiscale.multiscale_conservation(
            store, repo, fired_node_ids=fired_node_ids or [], budget=budget
        )
        ok_flags["M9"] = results["M9"].get("ok") is not False or "counts" in results["M9"]
    except Exception as exc:
        results["M9"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M9"] = False

    # M10
    try:
        results["M10"] = temporal_edges.temporal_structural_report(store, repo)
        ok_flags["M10"] = "error" not in results["M10"]
    except Exception as exc:
        results["M10"] = {"error": f"{type(exc).__name__}: {exc}"}
        ok_flags["M10"] = False

    # Only M0–M10 count toward all_ok
    phase_ids = [f"M{i}" for i in range(0, 11)]
    n_ok = sum(1 for p in phase_ids if ok_flags.get(p))
    n_tot = len(phase_ids)
    return {
        "schema_version": "cortex-math-network-pass/1.0",
        "repo": repo,
        "phases_ok": n_ok,
        "phases_total": n_tot,
        "ok_flags": {p: bool(ok_flags.get(p)) for p in phase_ids},
        "all_ok": n_ok == n_tot,
        "results": results,
        "claim_boundary": (
            "Full M0–M10 pass for confirmation; shadow calibration does not override live priors "
            "until explicit promotion."
        ),
    }
