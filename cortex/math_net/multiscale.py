"""M9 — Multi-scale conservation inequalities under budget.

v6.21: residual pyramid (path residual / envelope–cell refuse).
"""

from __future__ import annotations

import json
from typing import Any

SCHEMA = "cortex-multiscale/1.1"

# Residual refuse threshold τ (1/4 — rational table "quarter")
RESIDUAL_TAU = 0.25


def multiscale_conservation(
    store: Any,
    repo: str,
    fired_node_ids: list[str] | None = None,
    *,
    budget: int = 400,
) -> dict[str, Any]:
    """Check that fine-scale fire aggregates coherently to file scale.

    Inequality (soft): mass_file >= sum(mass_symbol in file) * rollup_factor
    under budget truncation report distortion.

    Residual pyramid: r_ell = fine mass not explained by coarse cover;
    envelope_cell_ok when max delta_ell <= τ and orphan law holds.
    """
    fired = set(fired_node_ids or [])
    by_res: dict[str, list[dict[str, Any]]] = {"file": [], "symbol": [], "other": []}
    file_of: dict[str, str] = {}
    try:
        for row in store.neural_nodes(repo) or []:
            nid = str(row["node_id"])
            path = str(row["path"] or "")
            try:
                res = str(row["resolution"] or "file")
            except (KeyError, IndexError, TypeError):
                meta = json.loads(row["metadata"] or "{}") if "metadata" in row.keys() else {}
                res = str(meta.get("resolution") or "file")
            if res not in by_res:
                res = "other"
            entry = {"node_id": nid, "path": path, "fired": nid in fired}
            by_res[res].append(entry)
            if res == "symbol":
                file_of[nid] = path.split("::")[0] if "::" in path else path
    except Exception as exc:
        return {"schema_version": SCHEMA, "ok": False, "error": f"{type(exc).__name__}: {exc}"}

    fired_symbols = [e for e in by_res["symbol"] if e["fired"]]
    fired_files = [e for e in by_res["file"] if e["fired"]]
    covered_files = {file_of[e["node_id"]] for e in fired_symbols if e["node_id"] in file_of}
    fired_file_paths = {e["path"] for e in fired_files}
    orphans = [p for p in covered_files if p not in fired_file_paths]
    symbol_mass = len(fired_symbols)
    file_mass = len(fired_files)
    total_fired = len(fired)
    truncated = max(0, total_fired - int(budget)) if budget > 0 else 0
    covered_n = max(1, len(covered_files))
    orphan_ratio = len(orphans) / covered_n
    ok = len(orphans) <= max(1, int(0.25 * covered_n))

    gamma = 1.0
    rhs = float(symbol_mass)
    lhs_effective = float(len(covered_files) - len(orphans))
    denom = gamma * max(1.0, rhs)
    if rhs <= 0:
        delta_mass = 0.0
        inequality_holds = True
    else:
        ratio = lhs_effective / denom
        delta_mass = max(0.0, 1.0 - ratio)
        inequality_holds = ratio >= 1.0 - 1e-9 or orphan_ratio <= 0.25

    # --- Residual pyramid (v6.21) ---
    # r_symbol = symbols whose parent file not covered (orphan mass)
    # r_budget = truncated fire count under budget (rollup lie)
    r_symbol = float(len(orphans))
    r_budget = float(truncated)
    # Normalize residuals
    delta_symbol = r_symbol / max(1.0, float(symbol_mass)) if symbol_mass else 0.0
    delta_budget = r_budget / max(1.0, float(total_fired)) if total_fired else 0.0
    # Coarse residual: file mass present but not supporting any symbol fire
    unsupported_files = [
        e["path"] for e in fired_files if e["path"] not in covered_files
    ]
    r_file = float(len(unsupported_files)) if symbol_mass > 0 else 0.0
    delta_file = r_file / max(1.0, float(file_mass)) if file_mass else 0.0

    levels = [
        {
            "level": "symbol",
            "r_ell": r_symbol,
            "delta_ell": round(delta_symbol, 6),
            "mass": float(symbol_mass),
        },
        {
            "level": "file",
            "r_ell": r_file,
            "delta_ell": round(delta_file, 6),
            "mass": float(file_mass),
        },
        {
            "level": "budget",
            "r_ell": r_budget,
            "delta_ell": round(delta_budget, 6),
            "mass": float(total_fired),
        },
    ]
    path_residual = sum(abs(float(lv["r_ell"])) for lv in levels)
    max_delta = max((float(lv["delta_ell"]) for lv in levels), default=0.0)
    envelope_cell_ok = max_delta <= RESIDUAL_TAU and inequality_holds and ok

    residual_pyramid = {
        "levels": levels,
        "path_residual": round(path_residual, 6),
        "max_delta_ell": round(max_delta, 6),
        "tau": RESIDUAL_TAU,
        "envelope_cell_ok": envelope_cell_ok,
        "law": (
            "r_ell = fine mass not explained by coarse cover (unit mass); "
            "envelope_cell_ok ⇔ max(delta_ell) <= tau and orphan law holds"
        ),
        "claim_boundary": (
            "Hierarchical residual distortion under budget — not free energy, "
            "FEP ideology, or consciousness."
        ),
    }

    return {
        "schema_version": SCHEMA,
        "ok": ok and inequality_holds and envelope_cell_ok,
        "counts": {
            "fired_total": total_fired,
            "fired_symbols": symbol_mass,
            "fired_files": file_mass,
            "covered_files_from_symbols": len(covered_files),
            "orphan_symbol_parents": len(orphans),
            "budget": budget,
            "truncated_over_budget": truncated,
        },
        "inequality": {
            "name": "file_cover_of_symbol_fire",
            "holds": ok,
            "detail": "orphan_symbol_parents / covered_files <= 0.25",
        },
        "mass_conservation": {
            "gamma": gamma,
            "lhs_file_mass_effective": lhs_effective,
            "rhs_symbol_mass": rhs,
            "distortion_delta": round(delta_mass, 6),
            "orphan_ratio": round(orphan_ratio, 6),
            "holds": inequality_holds,
            "law": "sum m(file) >= gamma * sum m(symbol) under budget; delta=1-LHS/(gamma*RHS)",
            "claim_boundary": (
                "Multi-scale mass distortion is hierarchical coverage telemetry under "
                "activation budget — not thermodynamic free energy or consciousness."
            ),
        },
        "residual_pyramid": residual_pyramid,
        "orphan_sample": list(orphans)[:12],
        "claim_boundary": (
            "Soft multi-scale conservation; residual pyramid spikes when fine cell "
            "breaks coarse envelope under budget. Not host authority."
        ),
    }
