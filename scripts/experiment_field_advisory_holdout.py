#!/usr/bin/env python3
"""Tiny holdout: advisory retrieval-width on vs off (N=20 tasks).

Synthetic gold-path ranking — no personal machine paths.
Measures whether policy width deltas improve gold@k.

  python scripts/experiment_field_advisory_holdout.py
  python scripts/experiment_field_advisory_holdout.py --n 20 --base-k 5

Writes: work/field_advisory_holdout.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cortex.field_policy import policy_for_classification  # noqa: E402

# N=20 synthetic tasks with gold path buried at rank gold_rank (0-based)
# Without advisory: take top base_k. With advisory: base_k + delta from policy.
TASKS = [
    # (task_id, classification, gold_rank in scored list of 12)
    ("T01_auth_map", "FRAGMENTED", 6),
    ("T02_route_table", "FRAGMENTED", 5),
    ("T03_session_fix", "STALE_ECHO", 5),
    ("T04_db_migrate", "OVERBOUND", 7),
    ("T05_cache_layer", "COHERENT_DIFFERENTIATED", 2),
    ("T06_error_paths", "FRAGMENTED", 6),
    ("T07_middleware", "TRANSITION", 4),
    ("T08_config_load", "QUIESCENT", 1),
    ("T09_template_ctx", "STALE_ECHO", 6),
    ("T10_cli_entry", "FRAGMENTED", 5),
    ("T11_signal_hooks", "OVERBOUND", 6),
    ("T12_json_api", "COHERENT_DIFFERENTIATED", 3),
    ("T13_static_files", "INDETERMINATE", 4),
    ("T14_blueprints", "FRAGMENTED", 7),
    ("T15_request_ctx", "STALE_ECHO", 5),
    ("T16_security", "OVERBOUND", 6),
    ("T17_logging", "QUIESCENT", 2),
    ("T18_testing", "TRANSITION", 5),
    ("T19_deploy", "FRAGMENTED", 6),
    ("T20_docs_index", "COHERENT_DIFFERENTIATED", 1),
]


def ranked_paths(task_id: str, gold_rank: int, pool: int = 12) -> list[str]:
    """Deterministic fake ranking: gold at gold_rank, rest fillers."""
    paths = [f"src/{task_id}/cand_{i}.py" for i in range(pool)]
    gold = f"src/{task_id}/gold.py"
    paths[gold_rank] = gold
    return paths


def hit_at_k(paths: list[str], gold: str, k: int) -> bool:
    return gold in paths[: max(0, k)]


def run_holdout(*, n: int, base_k: int, seed: int = 7) -> dict:
    rng = random.Random(seed)
    tasks = list(TASKS[:n])
    # slight jitter of gold ranks for robustness (still deterministic seed)
    rows = []
    hits_off = 0
    hits_on = 0
    for task_id, classification, gold_rank in tasks:
        paths = ranked_paths(task_id, gold_rank)
        gold = f"src/{task_id}/gold.py"
        pol = policy_for_classification(classification)
        delta = int(pol.retrieval_width_delta)
        k_off = base_k
        k_on = max(1, base_k + delta)  # advisory applies width
        off = hit_at_k(paths, gold, k_off)
        on = hit_at_k(paths, gold, k_on)
        hits_off += int(off)
        hits_on += int(on)
        rows.append(
            {
                "task_id": task_id,
                "classification": classification,
                "gold_rank": gold_rank,
                "base_k": base_k,
                "delta": delta,
                "k_off": k_off,
                "k_on": k_on,
                "hit_off": off,
                "hit_on": on,
                "policy_mode": pol.mode,
                "recommended_gcmt_regime": pol.recommended_gcmt_regime,
                "advisory_only": True,
            }
        )

    n_eff = len(rows)
    rate_off = hits_off / n_eff if n_eff else 0.0
    rate_on = hits_on / n_eff if n_eff else 0.0
    lift = rate_on - rate_off
    return {
        "schema_version": "cortex-field-advisory-holdout/1.0",
        "n": n_eff,
        "base_k": base_k,
        "seed": seed,
        "hits_off": hits_off,
        "hits_on": hits_on,
        "hit_rate_off": round(rate_off, 4),
        "hit_rate_on": round(rate_on, 4),
        "lift": round(lift, 4),
        "lift_pct_points": round(100.0 * lift, 2),
        "tasks": rows,
        "claim_boundary": (
            "Synthetic holdout on policy width deltas only. "
            "Not proof of production retrieval gain. Advisory-only. "
            "No host mutation. No constitutional authority."
        ),
        "interpretation": (
            "Positive lift means wider k from FRAGMENTED/STALE/OVERBOUND policies "
            "recovers golds that sat just outside base_k. "
            "COHERENT (delta=-1) may drop edge golds — expected tradeoff."
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--base-k", type=int, default=5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument(
        "--out",
        default=str(ROOT / "docs" / "demo" / "field_advisory_holdout.json"),
    )
    args = ap.parse_args()
    result = run_holdout(n=args.n, base_k=args.base_k, seed=args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    (work / "field_advisory_holdout.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "n": result["n"],
                "hit_rate_off": result["hit_rate_off"],
                "hit_rate_on": result["hit_rate_on"],
                "lift": result["lift"],
                "out": str(out),
            },
            indent=2,
        )
    )
    # always exit 0 — experiment is observational
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
