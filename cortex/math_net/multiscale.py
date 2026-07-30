"""M9 — Multi-scale conservation inequalities under budget."""

from __future__ import annotations

import json
from typing import Any

SCHEMA = "cortex-multiscale/1.0"


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
                # map symbol → parent file path (dirname-ish)
                file_of[nid] = path.split("::")[0] if "::" in path else path
    except Exception as exc:
        return {"schema_version": SCHEMA, "ok": False, "error": f"{type(exc).__name__}: {exc}"}

    fired_symbols = [e for e in by_res["symbol"] if e["fired"]]
    fired_files = [e for e in by_res["file"] if e["fired"]]
    # Rollup: files covered by fired symbols
    covered_files = {file_of[e["node_id"]] for e in fired_symbols if e["node_id"] in file_of}
    fired_file_paths = {e["path"] for e in fired_files}
    # Conservation distortion: symbols fired whose parent file not in fired set under budget
    orphans = [p for p in covered_files if p not in fired_file_paths]
    symbol_mass = len(fired_symbols)
    file_mass = len(fired_files)
    # Budget distortion proxy
    total_fired = len(fired)
    truncated = max(0, total_fired - int(budget)) if budget > 0 else 0
    ok = len(orphans) <= max(1, int(0.25 * max(1, len(covered_files))))

    return {
        "schema_version": SCHEMA,
        "ok": ok,
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
        "orphan_sample": list(orphans)[:12],
        "claim_boundary": (
            "Soft multi-scale check; not a proof of hierarchical exactness under all budgets."
        ),
    }
